import argparse
import os
from pathlib import Path

import mlflow
import optuna
import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from common import build_model, git_commit, raw_md5

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "params.yaml"


def suggest(trial: optuna.Trial, seed: int) -> dict:
    """The search space."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
        "max_depth": trial.suggest_categorical("max_depth", [10, 15, 20, 30, None]),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
        "random_seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_trials", type=int)
    args = parser.parse_args()

    cfg = yaml.safe_load(PARAMS.read_text())
    tune = cfg["tune"]
    n_trials = args.n_trials or tune["n_trials"]

    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "adult-income"))
    mlflow.set_system_metrics_sampling_interval(1)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    train = pd.read_csv(ROOT / "data/processed/train.csv")
    fit, val = train_test_split(train, test_size=tune["val_size"], random_state=tune["seed"],
                                stratify=train["target"])
    x_fit, y_fit = fit.drop("target", axis=1), fit["target"]
    x_val, y_val = val.drop("target", axis=1), val["target"]
    cat_cols = x_fit.select_dtypes("object").columns.tolist()

    def objective(trial: optuna.Trial) -> float:
        params = suggest(trial, tune["seed"])
        with mlflow.start_run(run_name=f"trial-{trial.number:02d}", nested=True):
            mlflow.log_params(params)
            mlflow.set_tag("optuna_trial", trial.number)
            model = build_model(params, cat_cols).fit(x_fit, y_fit)
            proba = model.predict_proba(x_val)[:, 1]
            f1 = f1_score(y_val, proba >= 0.5)
            mlflow.log_metrics({
                "val_f1": f1,
                "val_accuracy": accuracy_score(y_val, proba >= 0.5),
                "val_roc_auc": roc_auc_score(y_val, proba),
            })
        print(f"trial {trial.number:2d}: val_f1={f1:.4f} {params}")
        return f1

    with mlflow.start_run(run_name=f"hpo-optuna-{n_trials}trials", log_system_metrics=True) as parent:
        mlflow.log_params({"n_trials": n_trials, "val_size": tune["val_size"], "seed": tune["seed"],
                           "sampler": "TPESampler", "objective": "val_f1"})
        mlflow.set_tags({"git_commit": git_commit(), "dvc_raw_md5": raw_md5(), "hpo": "optuna"})
        mlflow.log_input(mlflow.data.from_pandas(train, source="data/processed/train.csv",
                                                 targets="target", name="train"), context="tuning")

        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.TPESampler(seed=tune["seed"]))
        study.optimize(objective, n_trials=n_trials)

        best = {**study.best_params, "random_seed": tune["seed"]}
        mlflow.log_params({f"best_{k}": v for k, v in best.items()})
        mlflow.log_metric("best_val_f1", study.best_value)
        mlflow.log_text(study.trials_dataframe().to_csv(index=False), "optuna_trials.csv")
        print(f"\nparent run {parent.info.run_id}: best val_f1={study.best_value:.4f}")
        print("paste into params.yaml -> train, then run dvc repro:")
        print(yaml.safe_dump(best, sort_keys=False))


if __name__ == "__main__":
    main()

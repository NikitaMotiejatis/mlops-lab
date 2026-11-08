import argparse
import os
import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from common import build_model, git_commit, none_or, raw_md5

ROOT = Path(__file__).resolve().parents[1]

warnings.filterwarnings("ignore", message="class_weight presets")
warnings.filterwarnings("ignore", message="Some inputs do not have OOB scores")


def oob_metrics(rf, y_train: pd.Series) -> dict:
    """Metrics on the rows each tree did NOT see (free validation, test set untouched)."""
    proba = rf.oob_decision_function_[:, 1]
    seen = ~np.isnan(proba)                   # with very few trees a row may never be out-of-bag
    y, p = y_train.to_numpy()[seen], proba[seen]
    return {
        "oob_accuracy": accuracy_score(y, p >= 0.5),
        "oob_f1": f1_score(y, p >= 0.5),
        "oob_roc_auc": roc_auc_score(y, p),
    }


def main() -> None:
    params = yaml.safe_load((ROOT / "params.yaml").read_text())["train"]
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int)
    parser.add_argument("--max_depth", type=none_or(int))
    parser.add_argument("--min_samples_leaf", type=int)
    parser.add_argument("--class_weight", type=none_or(str))
    parser.add_argument("--random_seed", type=int)
    for key, value in vars(parser.parse_args()).items():
        if value is not None:
            params[key] = value
    step = params.pop("step_trees", 25)

    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "adult-income"))
    mlflow.set_system_metrics_sampling_interval(1)

    train = pd.read_csv(ROOT / "data/processed/train.csv")
    test = pd.read_csv(ROOT / "data/processed/test.csv")
    x_train, y_train = train.drop("target", axis=1), train["target"]
    x_test, y_test = test.drop("target", axis=1), test["target"]
    cat_cols = x_train.select_dtypes("object").columns.tolist()

    model = build_model(params, cat_cols, n_estimators=step)
    model.set_params(rf__warm_start=True, rf__oob_score=True)   # grow in steps, score OOB

    run_name = f"rf-n{params['n_estimators']}-d{params['max_depth']}-l{params['min_samples_leaf']}"
    with mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        mlflow.log_params({**params, "step_trees": step})          # config, incl. the seed
        mlflow.set_tags({                                           # join keys to Git and DVC
            "git_commit": git_commit(),
            "dvc_raw_md5": raw_md5(),
            "random_seed": params["random_seed"],
            "model_family": "RandomForestClassifier",
            "dataset": "scikit-learn/adult-census-income",
        })
        mlflow.log_input(                                           # data provenance (name + digest)
            mlflow.data.from_pandas(train, source="data/processed/train.csv",
                                    targets="target", name="train"),
            context="training",
        )
        mlflow.log_input(
            mlflow.data.from_pandas(test, source="data/processed/test.csv",
                                    targets="target", name="test"),
            context="evaluation",
        )

        sizes = list(range(step, params["n_estimators"], step)) + [params["n_estimators"]]
        for n_trees in sizes:                                       # metrics per step
            model.set_params(rf__n_estimators=n_trees)
            model.fit(x_train, y_train)
            m = oob_metrics(model.named_steps["rf"], y_train)
            mlflow.log_metrics(m, step=n_trees)
            print(f"trees={n_trees:4d} oob_f1={m['oob_f1']:.4f} oob_auc={m['oob_roc_auc']:.4f}")

        model.set_params(rf__warm_start=False)
        preds = model.predict(x_test)
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds)                                # F1 of the >50K class
        auc = roc_auc_score(y_test, model.predict_proba(x_test)[:, 1])

        info = mlflow.sklearn.log_model(                            # model + environment files
            model, name="model", input_example=x_train.head(3),
            skops_trusted_types=["sklearn.tree._tree.Tree"],        # RF trees we trained ourselves
        )
        mlflow.log_metrics({"accuracy": acc, "f1": f1, "roc_auc": auc},
                           model_id=info.model_id)                  # metric <-> model link

        (ROOT / "models").mkdir(exist_ok=True)
        joblib.dump(model, ROOT / "models/model.pkl")
        (ROOT / "models/run_id.txt").write_text(run.info.run_id + "\n")
        print(f"run_id={run.info.run_id} model_id={info.model_id} accuracy={acc:.4f} f1={f1:.4f}")


if __name__ == "__main__":
    main()

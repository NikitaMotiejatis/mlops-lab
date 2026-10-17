import argparse
import hashlib
import os
import subprocess
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/adult.csv"


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return os.environ.get("GIT_COMMIT", "unknown")    # Docker image: set at build time


def raw_md5() -> str:
    """md5 of the raw dataset - same value as in data/raw/adult.csv.dvc and dvc.lock."""
    try:
        return yaml.safe_load((ROOT / "data/raw/adult.csv.dvc").read_text())["outs"][0]["md5"]
    except Exception:
        return hashlib.md5(RAW.read_bytes()).hexdigest() if RAW.exists() else "untracked"


def none_or(cast):
    return lambda v: None if v in (None, "None", "null") else cast(v)


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

    mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "adult-income"))

    train = pd.read_csv(ROOT / "data/processed/train.csv")
    test = pd.read_csv(ROOT / "data/processed/test.csv")
    x_train, y_train = train.drop("target", axis=1), train["target"]
    x_test, y_test = test.drop("target", axis=1), test["target"]
    cat_cols = x_train.select_dtypes("object").columns.tolist()

    model = Pipeline([
        ("encode", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)],
            remainder="passthrough",                          # numeric columns as they are
        )),
        ("rf", RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            class_weight=params["class_weight"],
            random_state=params["random_seed"],
            n_jobs=-1,
        )),
    ])

    run_name = f"rf-n{params['n_estimators']}-d{params['max_depth']}-l{params['min_samples_leaf']}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)                                   # config, incl. the seed
        mlflow.set_tags({                                           # join keys to Git and DVC
            "git_commit": git_commit(),
            "dvc_raw_md5": raw_md5(),
            "model_family": "RandomForestClassifier",
            "dataset": "scikit-learn/adult-census-income",
        })
        mlflow.log_input(                                           # data provenance (name + digest)
            mlflow.data.from_pandas(
                train, source="data/processed/train.csv", targets="target", name="train"
            ),
            context="training",
        )

        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds)                                # F1 of the >50K class

        info = mlflow.sklearn.log_model(                            # model + environment files
            model, name="model", input_example=x_train.head(3),
            skops_trusted_types=["sklearn.tree._tree.Tree"],        # RF trees we trained ourselves
        )
        mlflow.log_metric("accuracy", acc, model_id=info.model_id)  # metric <-> model link
        mlflow.log_metric("f1", f1, model_id=info.model_id)

        (ROOT / "models").mkdir(exist_ok=True)
        joblib.dump(model, ROOT / "models/model.pkl")
        (ROOT / "models/run_id.txt").write_text(run.info.run_id + "\n")
        print(f"run_id={run.info.run_id} model_id={info.model_id} accuracy={acc:.4f} f1={f1:.4f}")


if __name__ == "__main__":
    main()

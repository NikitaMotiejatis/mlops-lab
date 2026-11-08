import hashlib
import os
import subprocess
from pathlib import Path

import yaml
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
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
    """MLflow/CLI give strings: 'None'/'null' must become None again (max_depth, class_weight)."""
    return lambda v: None if v in (None, "None", "null") else cast(v)


def build_model(params: dict, cat_cols: list[str], n_estimators: int | None = None) -> Pipeline:
    """One-hot encoder + random forest in one Pipeline, so the saved model accepts raw rows."""
    return Pipeline([
        ("encode", ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)],
            remainder="passthrough",                          # numeric columns as they are
        )),
        ("rf", RandomForestClassifier(
            n_estimators=n_estimators or params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            class_weight=params["class_weight"],
            random_state=params["random_seed"],
            n_jobs=-1,
        )),
    ])
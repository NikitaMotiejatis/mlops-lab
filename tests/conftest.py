import numpy as np
import pandas as pd
import pytest

CATEGORIES = {
    "workclass": ["Private", "Self-emp-not-inc", "missing"],
    "marital.status": ["Married-civ-spouse", "Never-married", "Divorced"],
    "occupation": ["Exec-managerial", "Craft-repair", "Sales"],
    "relationship": ["Husband", "Not-in-family", "Own-child"],
    "race": ["White", "Black"],
    "sex": ["Male", "Female"],
    "native.country": ["United-States", "Mexico"],
}


@pytest.fixture(scope="session")
def fake_data() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame({
        "age": rng.integers(17, 90, n),
        "workclass": rng.choice(CATEGORIES["workclass"], n),
        "education.num": rng.integers(1, 17, n),
        "marital.status": rng.choice(CATEGORIES["marital.status"], n),
        "occupation": rng.choice(CATEGORIES["occupation"], n),
        "relationship": rng.choice(CATEGORIES["relationship"], n),
        "race": rng.choice(CATEGORIES["race"], n),
        "sex": rng.choice(CATEGORIES["sex"], n),
        "capital.gain": rng.integers(0, 5000, n),
        "capital.loss": rng.integers(0, 500, n),
        "hours.per.week": rng.integers(10, 80, n),
        "native.country": rng.choice(CATEGORIES["native.country"], n),
    })
    df["target"] = ((df["education.num"] > 10) & (df["age"] > 30)).astype(int)
    return df


@pytest.fixture(scope="session")
def params() -> dict:
    return {"n_estimators": 10, "max_depth": 5, "min_samples_leaf": 1,
            "class_weight": None, "random_seed": 42}


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory, fake_data, params):
    """A model saved in MLflow format, like the one the API loads from the registry."""
    import mlflow.sklearn

    from common import build_model

    x, y = fake_data.drop("target", axis=1), fake_data["target"]
    model = build_model(params, x.select_dtypes("object").columns.tolist()).fit(x, y)
    path = tmp_path_factory.mktemp("model") / "model"
    mlflow.sklearn.save_model(model, str(path), skops_trusted_types=["sklearn.tree._tree.Tree"])
    return path

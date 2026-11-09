import numpy as np

from common import build_model, none_or


def test_pipeline_accepts_raw_rows_and_unknown_categories(fake_data, params):
    x, y = fake_data.drop("target", axis=1), fake_data["target"]
    model = build_model(params, x.select_dtypes("object").columns.tolist()).fit(x, y)
    row = x.head(1).copy()
    row["occupation"] = "Never-seen-before"          # handle_unknown="ignore" -> no crash
    proba = model.predict_proba(row)
    assert proba.shape == (1, 2)
    assert 0.0 <= proba[0, 1] <= 1.0


def test_same_seed_same_model(fake_data, params):
    x, y = fake_data.drop("target", axis=1), fake_data["target"]
    cats = x.select_dtypes("object").columns.tolist()
    a = build_model(params, cats).fit(x, y).predict_proba(x)
    b = build_model(params, cats).fit(x, y).predict_proba(x)
    # n_jobs=-1: trees are summed in parallel, so only float rounding (~1e-16) may differ
    assert np.allclose(a, b, rtol=0, atol=1e-12)


def test_none_or_turns_mlflow_strings_back_into_none():
    assert none_or(int)("None") is None
    assert none_or(int)("null") is None
    assert none_or(int)("7") == 7
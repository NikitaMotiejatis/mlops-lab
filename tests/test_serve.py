import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "docs/example.json").read_text())


@pytest.fixture()
def client(model_dir, monkeypatch):
    monkeypatch.setenv("MODEL_URI", str(model_dir))
    from src.serve import app
    with TestClient(app) as c:          # `with` runs the startup (model loading)
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict(client):
    r = client.post("/predict", json=EXAMPLE)
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in (0, 1)
    assert 0.0 <= body["probability"] <= 1.0
    assert body["label"] == (">50K" if body["prediction"] else "<=50K")


def test_predict_rejects_missing_field(client):
    bad = {k: v for k, v in EXAMPLE.items() if k != "age"}
    assert client.post("/predict", json=bad).status_code == 422


def test_predict_rejects_out_of_range(client):
    assert client.post("/predict", json={**EXAMPLE, "age": 5}).status_code == 422


def test_predict_rejects_unknown_field(client):
    assert client.post("/predict", json={**EXAMPLE, "email": "a@b.lt"}).status_code == 422

import os
from contextlib import asynccontextmanager

import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI
from mlflow import MlflowClient
from pydantic import BaseModel, ConfigDict, Field

STATE: dict = {}


def load_model():
    """Resolve the alias to a version ONCE, then load exactly that version."""
    if os.environ.get("MODEL_URI"):                      # tests only: a local model directory
        uri = os.environ["MODEL_URI"]
        info = {"uri": uri, "version": "local"}
    else:
        name = os.environ.get("MODEL_NAME", "adult-income")
        alias = os.environ.get("MODEL_ALIAS", "champion")
        mv = MlflowClient().get_model_version_by_alias(name, alias)
        uri = f"models:/{name}/{mv.version}"
        info = {"name": name, "alias": alias, "version": mv.version, "run_id": mv.run_id}
    model = mlflow.sklearn.load_model(uri)
    # n_jobs=-1 starts a thread pool for every single-row request -> slower; 1 thread per request
    model.named_steps["rf"].n_jobs = int(os.environ.get("PREDICT_N_JOBS", "1"))
    return model, info


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["model"], STATE["info"] = load_model()      # the pod is not Ready until this finishes
    yield


app = FastAPI(title="Adult income API", lifespan=lifespan)


class Person(BaseModel):
    """One row of the Adult dataset (same column names, dots included)."""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    age: int = Field(ge=17, le=100)
    workclass: str
    education_num: int = Field(alias="education.num", ge=1, le=16)
    marital_status: str = Field(alias="marital.status")
    occupation: str
    relationship: str
    race: str
    sex: str
    capital_gain: int = Field(alias="capital.gain", ge=0)
    capital_loss: int = Field(alias="capital.loss", ge=0)
    hours_per_week: int = Field(alias="hours.per.week", ge=1, le=99)
    native_country: str = Field(alias="native.country")


@app.get("/health")
def health():
    return {"status": "ok", "model": STATE["info"], "image_commit": os.environ.get("GIT_COMMIT", "dev")}


@app.post("/predict")
async def predict(person: Person):
    # `async def` = requests run one after another on the event loop. A plain `def` would run
    # them in parallel threads that fight over the GIL: measured 2x lower throughput.
    # More throughput = more pods (replicas), each with its own process.
    model = STATE["model"]
    row = pd.DataFrame([person.model_dump(by_alias=True)])[list(model.feature_names_in_)]
    proba = float(model.predict_proba(row)[0, 1])
    pred = int(proba > 0.5)                 # same rule as model.predict(), without a 2nd pass
    return {
        "prediction": pred,
        "label": ">50K" if pred else "<=50K",
        "probability": round(proba, 4),
        "model_version": STATE["info"]["version"],
    }

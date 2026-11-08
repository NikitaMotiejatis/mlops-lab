import argparse
import os
import sys

import mlflow
from mlflow import MlflowClient

NAME = os.environ.get("MODEL_NAME", "adult-income")


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def register(client: MlflowClient, run_id: str, alias: str) -> str:
    """Register the run's model once (idempotent) and point `alias` at it."""
    existing = client.search_model_versions(f"name='{NAME}' and run_id='{run_id}'")
    if existing:
        version = existing[0].version
        log(f"run {run_id} is already {NAME} v{version}")
    else:
        run = client.get_run(run_id)
        model_id = run.outputs.model_outputs[0].model_id        # MLflow 3 LoggedModel (m-...)
        version = mlflow.register_model(f"models:/{model_id}", NAME).version
        client.set_model_version_tag(NAME, version, "git_commit", run.data.tags.get("git_commit", "?"))
        for key in ("accuracy", "f1", "roc_auc"):
            if key in run.data.metrics:
                client.set_model_version_tag(NAME, version, key, f"{run.data.metrics[key]:.4f}")
        log(f"registered {NAME} v{version} from run {run_id}")
    client.set_registered_model_alias(NAME, alias, version)
    log(f"{NAME}@{alias} -> v{version}")
    return version


def promote(client: MlflowClient, version: str, alias: str) -> str:
    try:
        old = client.get_model_version_by_alias(NAME, alias).version
    except Exception:
        old = "none"
    client.set_registered_model_alias(NAME, alias, version)
    log(f"{NAME}@{alias}: v{old} -> v{version}")
    return version


def show(client: MlflowClient, alias: str) -> None:
    mv = client.get_model_version_by_alias(NAME, alias)
    print(f"{NAME}@{alias} = v{mv.version}  run_id={mv.run_id}  tags={mv.tags}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("register")
    p.add_argument("--run-id", required=True)
    p.add_argument("--alias", default="candidate")
    p = sub.add_parser("promote")
    p.add_argument("--version", required=True)
    p.add_argument("--alias", default="champion")
    p = sub.add_parser("show")
    p.add_argument("--alias", default="champion")
    args = parser.parse_args()

    client = MlflowClient()
    if args.cmd == "register":
        print(f"version={register(client, args.run_id, args.alias)}")
    elif args.cmd == "promote":
        print(f"version={promote(client, args.version, args.alias)}")
    else:
        show(client, args.alias)


if __name__ == "__main__":
    main()

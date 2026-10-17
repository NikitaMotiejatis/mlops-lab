import json
from pathlib import Path

import joblib
import mlflow
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    model = joblib.load(ROOT / "models/model.pkl")
    test = pd.read_csv(ROOT / "data/processed/test.csv")
    x, y = test.drop("target", axis=1), test["target"]
    preds = model.predict(x)
    proba = model.predict_proba(x)[:, 1]
    metrics = {
        "accuracy": accuracy_score(y, preds),
        "f1": f1_score(y, preds),
        "precision": precision_score(y, preds),
        "recall": recall_score(y, preds),
        "roc_auc": roc_auc_score(y, proba),
    }
    out = json.dumps(metrics, indent=2) + "\n"
    (ROOT / "metrics.json").write_text(out)
    print(out)

    run_id_file = ROOT / "models/run_id.txt"
    if run_id_file.exists():                       # attach to the training run
        try:
            run_id = run_id_file.read_text().strip()
            client = mlflow.MlflowClient()
            for key, value in metrics.items():
                client.log_metric(run_id, f"eval/{key}", value)
        except Exception as exc:                   # server may be unreachable
            print(f"warning: eval metrics not attached ({exc})")


if __name__ == "__main__":
    main()

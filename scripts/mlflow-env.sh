#!/usr/bin/env bash
# MLflow login for CURRENT terminal, read from the cluster Secret (nothing written to disk):
#   eval "$(bash scripts/mlflow-env.sh)"      # exports MLFLOW_TRACKING_URI/USERNAME/PASSWORD
#   bash scripts/mlflow-env.sh --admin        # admin login for the browser
set -euo pipefail
CTX=${KUBE_CONTEXT:-kind-mlops-u1}
get() { kubectl --context "$CTX" -n mlops-u1 get secret "$1" -o jsonpath="{.data.$2}" | base64 -d; }

if [ "${1:-}" = "--admin" ]; then
  echo "user:     admin"
  echo "password: $(get mlflow-auth 'basic_auth\.ini' | sed -n 's/^admin_password = //p')"
  exit 0
fi
echo "export MLFLOW_TRACKING_URI=${MLFLOW_HOST_URI:-http://localhost:5000}"
echo "export MLFLOW_TRACKING_USERNAME=$(get mlflow-client MLFLOW_TRACKING_USERNAME)"
echo "export MLFLOW_TRACKING_PASSWORD=$(get mlflow-client MLFLOW_TRACKING_PASSWORD)"

#!/usr/bin/env bash
# Bring up the local kind cluster with MLflow (login required) + PostgreSQL from zero. Safe to re-run.
#   bash scripts/cluster-up.sh
# All passwords are random, live only in Kubernetes Secrets and are never written to Git.
set -euo pipefail
cd "$(dirname "$0")/.."
CLUSTER=${CLUSTER:-mlops-u1}
NS=mlops-u1
MLFLOW_IMAGE=mlflow-server:v3.15.2-pg-auth
k() { kubectl -n "$NS" "$@"; }

# 1. cluster (k8s/kind-config.yaml = cluster as code)
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --config k8s/kind-config.yaml --name "$CLUSTER"
kubectl config use-context "kind-$CLUSTER"

# 2. MLflow server image: built locally, copied into the kind node (no registry needed)
docker build -f docker/Dockerfile.mlflow -t "$MLFLOW_IMAGE" .
kind load docker-image "$MLFLOW_IMAGE" --name "$CLUSTER"

# 3. namespace + DB credentials, then PostgreSQL
kubectl apply -f k8s/namespace.yaml
k get secret mlflow-db >/dev/null 2>&1 || k create secret generic mlflow-db \
  --from-literal=POSTGRES_USER=mlflow \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=POSTGRES_DB=mlflow
kubectl apply -f k8s/postgres.yaml
k rollout status deploy/postgres --timeout=180s

# 4. MLflow login (basic-auth): users live in their own database "mlflow_auth"
k exec deploy/postgres -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
  "SELECT 1 FROM pg_database WHERE datname = '"'mlflow_auth'"'" | grep -q 1 \
  || psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE DATABASE mlflow_auth"'
if ! k get secret mlflow-auth >/dev/null 2>&1; then
  DB_PW=$(k get secret mlflow-db -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)
  k create secret generic mlflow-auth \
    --from-literal=MLFLOW_FLASK_SERVER_SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=basic_auth.ini="[mlflow]
default_permission = EDIT
database_uri = postgresql://mlflow:${DB_PW}@postgres:5432/mlflow_auth
admin_username = admin
admin_password = $(openssl rand -hex 16)
authorization_function = mlflow.server.auth:authenticate_request_basic_auth"
fi

# 5. MLflow server
kubectl apply -f k8s/mlflow.yaml
k rollout status deploy/mlflow --timeout=300s

# 6. machine user "mlops-ci" for the training Job, the API and CI -> Secret mlflow-client
CI_PW=$(k get secret mlflow-client -o jsonpath='{.data.MLFLOW_TRACKING_PASSWORD}' 2>/dev/null | base64 -d || true)
if [ -z "$CI_PW" ]; then
  CI_PW=$(openssl rand -hex 16)
  # runs inside the MLflow pod: reads the admin login from the mounted ini, new password from stdin
  printf '%s' "$CI_PW" | k exec -i deploy/mlflow -- python -c '
import base64, configparser, json, os, sys, urllib.error, urllib.request
cfg = configparser.ConfigParser(); cfg.read(os.environ["MLFLOW_AUTH_CONFIG_PATH"]); a = cfg["mlflow"]
token = base64.b64encode((a["admin_username"] + ":" + a["admin_password"]).encode()).decode()
user, password = sys.argv[1], sys.stdin.read()
def call(method, path):
    req = urllib.request.Request("http://localhost:5000/api/2.0/mlflow/users/" + path, method=method,
                                 data=json.dumps({"username": user, "password": password}).encode(),
                                 headers={"Authorization": "Basic " + token, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)
try:
    call("POST", "create"); print("created MLflow user", user)
except urllib.error.HTTPError as e:
    if e.code != 400: raise
    call("PATCH", "update-password"); print("updated password of MLflow user", user)
' mlops-ci
  k delete secret mlflow-client --ignore-not-found
  k create secret generic mlflow-client \
    --from-literal=MLFLOW_TRACKING_URI=http://mlflow.mlops-u1.svc:5000 \
    --from-literal=MLFLOW_TRACKING_USERNAME=mlops-ci \
    --from-literal=MLFLOW_TRACKING_PASSWORD="$CI_PW"
fi

kubectl get all,pvc -n "$NS"
echo "MLflow UI: http://localhost:5000   login: bash scripts/mlflow-env.sh --admin"
echo "Terminal:  eval \"\$(bash scripts/mlflow-env.sh)\""

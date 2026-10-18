#!/usr/bin/env bash
# Bring up the local kind cluster with MLflow + PostgreSQL from zero. Safe to re-run.
#   bash scripts/cluster-up.sh
set -euo pipefail
cd "$(dirname "$0")/.."
CLUSTER=${CLUSTER:-mlops-u1}
NS=mlops-u1
MLFLOW_IMAGE=mlflow-server:v3.15.2-pg

# 1. cluster (k8s/kind-config.yaml = cluster as code)
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --config k8s/kind-config.yaml --name "$CLUSTER"
kubectl config use-context "kind-$CLUSTER"

# 2. MLflow server image: built locally, copied into the kind node (no registry needed)
docker build -f docker/Dockerfile.mlflow -t "$MLFLOW_IMAGE" .
kind load docker-image "$MLFLOW_IMAGE" --name "$CLUSTER"

# 3. namespace + DB credentials (random password, created once, never in Git)
kubectl apply -f k8s/namespace.yaml
kubectl get secret mlflow-db -n "$NS" >/dev/null 2>&1 || kubectl create secret generic mlflow-db -n "$NS" \
  --from-literal=POSTGRES_USER=mlflow \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  --from-literal=POSTGRES_DB=mlflow

# 4. PostgreSQL, then MLflow
kubectl apply -f k8s/postgres.yaml -f k8s/mlflow.yaml
kubectl rollout status deploy/postgres -n "$NS" --timeout=180s
kubectl rollout status deploy/mlflow -n "$NS" --timeout=300s
kubectl get all,pvc -n "$NS"
echo "MLflow UI: http://localhost:5000   (export MLFLOW_TRACKING_URI=http://localhost:5000)"

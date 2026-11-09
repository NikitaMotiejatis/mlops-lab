#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
CTX=${KUBE_CONTEXT:-kind-mlops-u1}
k() { kubectl --context "$CTX" -n mlops-u1 "$@"; }

VERSION=$(sed -nE 's/.*mlops\/model-version: "([0-9]+)".*/\1/p' k8s/inference.yaml)
IMAGE=$(sed -nE 's/^ *image: (.*mlops-lab-serve:.*)$/\1/p' k8s/inference.yaml)
echo "deploying $IMAGE with adult-income v$VERSION"

python scripts/registry.py promote --version "$VERSION" --alias champion
kubectl --context "$CTX" apply -f k8s/inference.yaml
k rollout status deploy/adult-api --timeout=300s
if ! k exec -i deploy/adult-api -- python - "$VERSION" < scripts/smoke_test.py; then
  echo "pods still serve an older version (manifest unchanged) -> restarting them"
  k rollout restart deploy/adult-api
  k rollout status deploy/adult-api --timeout=300s
  k exec -i deploy/adult-api -- python - "$VERSION" < scripts/smoke_test.py
fi

#!/usr/bin/env bash
# Run one training Job in the cluster and wait for it.
set -euo pipefail
cd "$(dirname "$0")/.."
CTX=${KUBE_CONTEXT:-kind-mlops-u1}
k() { kubectl --context "$CTX" -n mlops-u1 "$@"; }

if [ -z "${KEEP_CM:-}" ]; then
  k create configmap train-params --from-file=params.yaml --dry-run=client -o yaml | k apply -f -
fi
JOB=$(k create -f k8s/train-job.yaml -o name)
echo "started $JOB"
for _ in $(seq 1 180); do
  STATUS=$(k get "$JOB" -o jsonpath='{.status.succeeded}/{.status.failed}')
  case "$STATUS" in
    1/*) break ;;
    */1) k logs "$JOB" --tail=30; echo "FAILED: $JOB"; exit 1 ;;
  esac
  sleep 5
done
k logs "$JOB" | grep -E "trees=|run_id=|View run" || true
k get "$JOB"

#!/usr/bin/env bash
# Roll back a deployment made by CD: revert its "cd: deploy ..." commit in Git, then deploy.sh.
# The reverted manifest brings back the previous image tag AND the previous model version.
#   bash scripts/rollback.sh <sha of the cd: deploy commit>
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -eq 1 ] || { echo "usage: $0 <cd-deploy-commit>"; exit 1; }
git diff --quiet && git diff --cached --quiet || { echo "commit or stash your changes first"; exit 1; }

git pull --ff-only
git revert --no-commit "$1"
git commit -m "rollback: undo $(git rev-parse --short "$1") [skip ci]"
git push
bash scripts/deploy.sh
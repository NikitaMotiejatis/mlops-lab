import argparse
import json
import os
import sys
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", default="metrics.json")
    parser.add_argument("--params", default="params.yaml")
    parser.add_argument("--metric")
    parser.add_argument("--threshold", type=float)
    args = parser.parse_args()

    gate = yaml.safe_load(Path(args.params).read_text())["gate"]
    metric = args.metric or gate["metric"]
    threshold = args.threshold if args.threshold is not None else float(gate["threshold"])
    value = json.loads(Path(args.metrics).read_text()).get(metric)

    if value is None:
        verdict, ok = f"FAIL: '{metric}' missing in {args.metrics}", False
    elif value < threshold:
        verdict, ok = f"FAIL: {metric}={value:.4f} < {threshold}", False
    else:
        verdict, ok = f"PASS: {metric}={value:.4f} >= {threshold}", True
    print(verdict)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")     # shown on the Actions run page
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Quality gate\n\n{'✅' if ok else '❌'} {verdict}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

import json
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "scripts/check_gate.py"


def run_gate(tmp_path, f1: float, threshold: float) -> int:
    (tmp_path / "metrics.json").write_text(json.dumps({"f1": f1}))
    (tmp_path / "params.yaml").write_text(f"gate:\n  metric: f1\n  threshold: {threshold}\n")
    return subprocess.run([sys.executable, str(GATE), "--metrics", str(tmp_path / "metrics.json"),
                           "--params", str(tmp_path / "params.yaml")]).returncode


def test_gate_passes_good_model(tmp_path):
    assert run_gate(tmp_path, f1=0.70, threshold=0.65) == 0


def test_gate_blocks_bad_model(tmp_path):
    assert run_gate(tmp_path, f1=0.40, threshold=0.65) == 1


def test_gate_blocks_missing_metric(tmp_path):
    (tmp_path / "metrics.json").write_text("{}")
    (tmp_path / "params.yaml").write_text("gate:\n  metric: f1\n  threshold: 0.5\n")
    code = subprocess.run([sys.executable, str(GATE), "--metrics", str(tmp_path / "metrics.json"),
                           "--params", str(tmp_path / "params.yaml")]).returncode
    assert code == 1

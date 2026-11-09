import json
import sys
import urllib.request

BASE = "http://localhost:8080"
EXAMPLE = {"age": 45, "workclass": "Private", "education.num": 13, "marital.status": "Married-civ-spouse",
           "occupation": "Exec-managerial", "relationship": "Husband", "race": "White", "sex": "Male",
           "capital.gain": 0, "capital.loss": 0, "hours.per.week": 50, "native.country": "United-States"}

health = json.loads(urllib.request.urlopen(f"{BASE}/health", timeout=5).read())
req = urllib.request.Request(f"{BASE}/predict", data=json.dumps(EXAMPLE).encode(),
                             headers={"Content-Type": "application/json"})
pred = json.loads(urllib.request.urlopen(req, timeout=5).read())
print(f"health: {health}\npredict: {pred}")
if health["model"]["version"] != sys.argv[1]:
    sys.exit(f"SMOKE FAIL: serving v{health['model']['version']}, expected v{sys.argv[1]}")
print(f"SMOKE OK: v{sys.argv[1]} answers /predict")

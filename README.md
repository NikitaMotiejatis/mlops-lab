# mlops-u1 — Adult Census pajamų klasifikatorius + MLflow Kubernetes klasteryje

U1 užduotis (MLOps, VU MIF 2026). DVC pipeline’as (prepare → train → evaluate), mokymo Docker vaizdas GHCR,
savas MLflow Tracking Server (PostgreSQL + artefaktų PVC) lokaliame `kind` klasteryje.

## Reikalavimai
Docker, kind v0.33.0, kubectl v1.37, Python 3.12, (trivy, gh — vaizdo publikavimui).

## Paleidimas nuo nulio
```bash
git clone https://github.com/NikitaMotiejatis/mlops-lab.git && cd mlops-lab
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
dvc pull || python src/download_data.py      # duomenys (tas pats md5: c214b838...)

bash scripts/cluster-up.sh                   # kind klasteris + PostgreSQL + MLflow (~1 min)
export MLFLOW_TRACKING_URI=http://localhost:5000
dvc repro                                    # pipeline'as -> run'as klasterio MLflow
```

## Portai ir prisijungimai
| Kas | Adresas | Prisijungimas |
|---|---|---|
| MLflow UI / API | http://localhost:5000 (NodePort 30500 → kind `extraPortMappings`) | be autentifikacijos |
| PostgreSQL | tik klasterio viduje `postgres.mlops-u1.svc:5432` | Secret `mlflow-db` (sugeneruojamas `cluster-up.sh`) |

Atsarginis variantas: `kubectl port-forward -n mlops-u1 svc/mlflow 5000:5000`.

## Kur žiūrėti rezultatus
- MLflow UI → eksperimentas **adult-income** (run’ai, metrikos, modeliai).
- `metrics.json`, `dvc metrics diff`, `dvc params diff`.
- Docker vaizdas: `ghcr.io/nikitamotiejatis/mlops-u1-train:sha-b31d81c2`; dydis ir Trivy — `docs/image-size.md`, `docs/trivy-train.txt`.

## Eksperimentai ir reprodukcija
```bash
# pakeiskite params.yaml -> dvc repro -> git commit params.yaml dvc.lock metrics.json models/run_id.txt
time python reproduce.py <run_id>            # < 2 min, Δaccuracy ≤ 0,005
docker run --rm --network host -e MLFLOW_TRACKING_URI=http://localhost:5000 ghcr.io/nikitamotiejatis/mlops-u1-train:sha-b31d81c2
```

## Struktūra
`src/` kodas · `docker/` Dockerfile’ai · `k8s/` klasterio konfigūracija ir manifestai · `docs/` reikalavimai, ataskaitos · `scripts/` paleidimas

## Sustabdymas
`kind delete cluster --name mlops-u1` (dėmesio: ištrina ir PVC duomenis).

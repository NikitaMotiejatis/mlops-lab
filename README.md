# mlops-lab — Adult Census pajamų klasifikatorius: MLflow, registras, Job, API ir CI/CD Kubernetes klasteryje

![ml-pipeline](https://github.com/NikitaMotiejatis/mlops-lab/actions/workflows/ml-pipeline.yml/badge.svg)

U1 + U2 užduotys (MLOps, VU MIF 2026). DVC pipeline’as, savas MLflow serveris (PostgreSQL + artefaktų PVC, prisijungimas)
lokaliame `kind` klasteryje, modelių registras, mokymo Job, FastAPI inferencijos API ir GitHub Actions CI/CD su kokybės vartu.

## Reikalavimai
Docker, kind v0.33.0, kubectl v1.37, Python 3.12, gh; CD daliai — GitHub self-hosted runner’is su žyme `mlops-kind`.

## Paleidimas nuo nulio
```bash
git clone https://github.com/NikitaMotiejatis/mlops-lab.git && cd mlops-lab
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
dvc pull || python src/download_data.py

bash scripts/cluster-up.sh                   # kind + PostgreSQL + MLflow su prisijungimu (~2 min)
eval "$(bash scripts/mlflow-env.sh)"         # MLflow prisijungimas šiam terminalui (iš Secret)
dvc repro                                    # mokymas -> run'as klasterio MLflow
python scripts/registry.py register --run-id "$(cat models/run_id.txt)"
python scripts/registry.py promote --version 1
```

## Mokymas
- Hiperparametrų paieška: `python src/tune.py` (Optuna, įdėtiniai run’ai). Geriausius parametrus perkelkite į `params.yaml`.
- Mokymas klasteryje: `bash scripts/train-job.sh` (Job; parametrai — ConfigMap `train-params`, prisijungimas — Secret `mlflow-client`).

## Inferencijos API
```bash
bash scripts/deploy.sh                       # @champion -> versija iš k8s/inference.yaml, rollout, smoke testas
kubectl port-forward -n mlops-u1 svc/adult-api 8080:80
curl localhost:8080/health
curl -X POST localhost:8080/predict -H 'Content-Type: application/json' -d @docs/example.json
```

## CI/CD
`.github/workflows/ml-pipeline.yml`: lint → test → `dvc repro` (self-hosted runner’is) → kokybės vartas (`params.yaml → gate`)
→ GHCR `mlops-lab-train/serve:sha-<commit>` → manifesto commit + `scripts/deploy.sh`.
Rollback: `bash scripts/rollback.sh <cd: deploy commit>`.

## Portai ir prisijungimai
| Kas | Adresas | Prisijungimas |
|---|---|---|
| MLflow UI / API | http://localhost:5000 | `bash scripts/mlflow-env.sh --admin` (naršyklei), `mlops-ci` (programoms, Secret `mlflow-client`) |
| Inferencijos API | `kubectl port-forward -n mlops-u1 svc/adult-api 8080:80` | be prisijungimo |
| PostgreSQL | tik klasterio viduje `postgres.mlops-u1.svc:5432` | Secret `mlflow-db` |

## Kur žiūrėti rezultatus
- MLflow → **adult-income**: run’ai, HPO medis (`hpo-optuna-…`), Models → `adult-income` (`@champion`, `@candidate`).
- GitHub → Actions → `ml-pipeline`. Matavimai: `docs/load-test.md`; ataskaita: `docs/u2-report.md`; reikalavimai: `docs/requirements.md`.

## Struktūra
`src/` kodas · `docker/` Dockerfile’ai · `k8s/` klasterio konfigūracija ir manifestai · `docs/` reikalavimai, ataskaitos · `scripts/` paleidimas · `tests/` unit testai

## Sustabdymas
`kind delete cluster --name mlops-u1` (dėmesio: ištrina ir PVC duomenis).

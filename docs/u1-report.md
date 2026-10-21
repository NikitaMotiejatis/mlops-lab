# U1 ataskaita

## Kas padaryta
- Repo struktūra, `docs/requirements.md` v1.0 → v1.1 (4 FR, 10 NFR su KPI, tarp jų reprodukcijos NFR-06).
- DVC pipeline’as (3 stage’ai), lokalus DVC remote, 3+ MLflow run’ai klasterio serveryje, `reproduce.py` (18 s, Δ = 0).
- Mokymo vaizdas `ghcr.io/nikitamotiejatis/mlops-u1-train:sha-b31d81c2` (~626 MB, 0 CRITICAL, UID 1000).
- `kind` klasteris, namespace `mlops-u1`: MLflow (Deployment + NodePort Service + artefaktų PVC) + PostgreSQL (Deployment + Service + PVC); Secret per `kubectl create secret`.

## Kas neveikė / problemos ir sprendimai
- gh autentifikacijos problemos, dėl pasenusios versijos iš ubuntu bibleotekos. 
- `mlflow-skinny` vaizde: `No module named 'skops'` → pridėtas `skops==0.16.0`.
- skops 0.16 `UntrustedTypesFoundException` (`sklearn.tree._tree.Tree`) → `skops_trusted_types` prie `log_model`; skops versija užfiksuota abiejuose requirements failuose.
- Oficialus MLflow vaizdas be PostgreSQL tvarkyklės → `docker/Dockerfile.mlflow` su `psycopg2-binary`.
- MLflow Pod `OOMKilled` (1,6 GiB) dėl MLflow 3.15 job runner’io → `MLFLOW_SERVER_ENABLE_JOB_EXECUTION=false` (~500 MiB).

## Kiek laiko užtruko
| Dalis | Laikas |
|---|---|
| Skaitymas, Mokymasis| 3h |
| Įrankiai + repo + DVC | 2 h |
| Pipeline kodas | 2 h |
| Docker + GHCR + Trivy | 2 h |
| Klasteris + MLflow | ~2 h |
| Dokumentacija | 1.5 h |
| **Iš viso** | **12.5 h** |

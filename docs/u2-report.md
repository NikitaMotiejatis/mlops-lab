# U2 ataskaita

## Architektūra
Push į `main` → GitHub Actions: lint + testai (GitHub) → `dvc repro` self-hosted runner’yje (run’as klasterio MLflow,
modelis registruojamas `@candidate`) → kokybės vartas (`f1 ≥ 0,65` iš `metrics.json`) → `mlops-lab-train/serve:sha-<commit>` į GHCR →
bot’o commit’as (`k8s/inference.yaml`: vaizdo tag’as + `mlops/model-version`) → `scripts/deploy.sh` (`@champion` → versija,
`kubectl apply`, rollout, smoke testas).

API (2 replikos) startuodamas įkelia `models:/adult-income@champion`; vaizde modelio nėra.
Mokymo Job: parametrai — ConfigMap `train-params`, prisijungimas — Secret `mlflow-client`. MLflow su basic-auth.

## Kas padaryta (pagal reikalavimus)
- R1: OOB metrikos kas 25 medžius (`step`), sistemos metrikos, `train`/`test` su digest, `git_commit`, `random_seed`; Optuna 10 bandymų įdėtiniais run’ais (41 s).
- R2: registras `adult-income` (v1–v5), alias’ai `@candidate` → `@champion`; servisas kraunasi pagal alias’ą.
- R3: Job `train-lfqx9` Completed per 65 s; parametrai per ConfigMap, prisijungimas per Secret.
- R4: FastAPI Deployment + Service, `/health`, `/predict`; p95 212 ms, kai 10 lygiagrečių klientų.
- R5/R6: workflow su 6 job’ais (lint, test, train, gate, build-push, deploy); žalias, raudonas ir rollback paleidimai žemiau.
- R7: `requirements.md` v1.6, NFR-21..26 išmatuoti.

## Matavimai
| Rodiklis | Reikšmė |
|---|---|
| p95 / p50 (2 replikos, 10 lygiagrečių) | 212,4 / 111,9 ms |
| Pralaidumas | 85,9 req/s |
| Modelio artefaktas / serving vaizdas | 27,1 MB / 627 MB |
| Job / deploy job / rollback | 65 s / 64 s / ~30 s |
| CI/CD nuo push iki deploy | 5 min 33 s |

Detaliau: `docs/load-test.md`.

## Kokybės vartas ir rollback (įrodymai)
| Paleidimas | Commit | Rezultatas | `@champion` prieš → po |
|---|---|---|---|
| Žalias (Optuna parametrai) | `e48de9e` | deploy `3bcb7f8`, f1 = 0,678 | v3 → v4 |
| Raudonas (`max_depth: 2`) | `ca78a81` | vartas: f1 = 0,121 < 0,65; build/deploy praleisti | v4 → v4 (nepakito) |
| Rollback | `0639704` (revert `3bcb7f8`) | abu pod’ai su v3 per ~30 s | v4 → v3 |

Rollback priežastis: Optuna parametrai (v4) teste davė mažesnį f1 (0,678) nei ankstesnis modelis v3 (0,681).
Kubernetes panaudojo seną v3 ReplicaSet, todėl naujo vaizdo traukti nereikėjo.

Actions paleidimai:
- žalias — https://github.com/NikitaMotiejatis/mlops-lab/actions/runs/42694541291
- raudonas — https://github.com/NikitaMotiejatis/mlops-lab/actions/runs/42696642191

## Kas neveikė / problemos ir sprendimai
- Pradinis MLflow be prisijungimo → nebuvo ką dėti į Secret → basic-auth (`Flask-WTF` trūko oficialiame vaizde).
- `n_jobs=-1` serviše: 65 ms → `n_jobs=1`: 21 ms; `def` → `async def`: 2× pralaidumas (GIL).

## Kiek laiko užtruko
| Dalis | Laikas |
|---|---|
| Skaitymas ir Pasiruošimas | 5h |
| Sekimas + HPO + registras | ~4h |
| Job + API + matavimai | ~3h |
| CI/CD | ~2h |
| Dokumentacija | 1.5h |
| **Iš viso** | **15.5** |

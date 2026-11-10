# Pajamų klasifikavimo platforma (Adult Census) — Reikalavimai

Versija: 1.6 | Data: 2026-11-10 | Autorius: Nikita Motiejaitis

## 1. Projekto apimtis
### 1.1 Problemos aprašymas
Pagal JAV 1994 m. surašymo duomenis (Hugging Face `scikit-learn/adult-census-income`, CC0, 32 561 eil.)
nuspėti, ar asmens metinės pajamos > 50K USD. Tikslas — ne SOTA modelis, o atkartojamas MLOps srautas:
DVC pipeline’as, MLflow serveris su registru, mokymo Job ir inferencijos API lokaliame Kubernetes klasteryje,
CI/CD su kokybės vartu.

### 1.2 Stakeholderiai
| Stakeholderis | Interesas | Prioritetas |
|---|---|---|
| ML inžinierius (studentas) | Atkartojami eksperimentai, vienas tracking serveris | Aukštas |
| Dėstytojas (vertintojas) | Paleidimas nuo nulio pagal README, atsekamumas | Aukštas |
| Inferencijos API (U2) | Modelis registre su alias’u `@champion`, signatūra ir aplinka | Vidutinis |

## 2. Funkciniai reikalavimai (FR)
| ID | Reikalavimas | Prioritetas |
|---|---|---|
| FR-01 | `dvc repro` vykdo prepare → train → evaluate ir sukuria `metrics.json` | Must |
| FR-02 | Kiekvienas mokymas registruoja run’ą **klasterio** MLflow: parametrai, metrikos, modelis, duomenų digest, žymos `git_commit` ir `dvc_raw_md5` | Must |
| FR-03 | `python reproduce.py <run_id>` atkuria istorinį run’ą (kodas, duomenys, parametrai) | Must |
| FR-04 | Mokymo Docker vaizdas, paleistas su `MLFLOW_TRACKING_URI`, atlieka visą pipeline’ą ir užregistruoja run’ą | Should |
| FR-05 | `python src/tune.py` atlieka hiperparametrų paiešką (Optuna, ≥5 bandymų) kaip įdėtinius MLflow run’us | Must |
| FR-06 | Modelis registruojamas `adult-income`; produkcija = alias `@champion`, kandidatas = `@candidate` | Must |
| FR-07 | Mokymas paleidžiamas kaip Kubernetes Job (parametrai — ConfigMap, prisijungimas — Secret) | Must |
| FR-08 | API `/health` ir `/predict`; modelis kraunamas iš `models:/adult-income@champion` | Must |

## 3. Nefunkciniai reikalavimai (NFR)
### 3.1 Modelio ir mokymo NFR (v1.0)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-01 | Kokybė | Klasių atskyrimas | ROC-AUC ≥ 0,88 (test) | `metrics.json` | 0,907–0,913 |
| NFR-02 | Kokybė | Mažumos klasės (>50K) aptikimas | F1 ≥ 0,65 | `metrics.json` | exp1 0,644 (nepasiekta) → exp3 0,681 |
| NFR-03 | Našumas | Viso pipeline’o trukmė CPU | `dvc repro` ≤ 60 s | `time dvc repro` | ~15 s |
| NFR-04 | Saugumas | Vaizdas be kritinių CVE, ne root | 0 CRITICAL (Trivy), UID ≠ 0 | `docs/trivy-train.txt`, `docker run … id` | 0 CRITICAL / UID 1000 |
| NFR-05 | Dydis | Mokymo vaizdo dydis | ≤ 700 MB (disk) | `docker images` | ~626 MB |

### 3.2 Eksperimentų sekimo, atkartojamumo ir infrastruktūros NFR (v1.1)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-06 | **Atkartojamumas** | Istorinis run’as atkuriamas `reproduce.py` | < 2 min, Δaccuracy ≤ 0,005 | `time python reproduce.py <id>` | 18 s, Δ = 0 |
| NFR-07 | Atsekamumas | Run’ai turi `git_commit` + `dvc_raw_md5` | 100 % run’ų | MLflow UI / `search_runs` | 100 % |
| NFR-08 | Atsekamumas | `dvc_raw_md5` = md5 iš `adult.csv.dvc` | 100 % run’ų | palyginimas | sutampa |
| NFR-09 | Patvarumas | MLflow duomenys išlieka perkūrus Pod’us | 0 prarastų run’ų/artefaktų | `kubectl delete pod …` + UI | 0 |
| NFR-10 | Ištekliai | MLflow Pod atmintis | ≤ 1 GiB (limit) | `memory.current` cgroup | ~500 MiB |

### 3.3 Mokymo sekimo NFR (v1.2)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-11 | Atsekamumas | Mokymo run’e: parametrai, metrikos per žingsnius, sistemos metrikos, 2 duomenų rinkiniai su digest, `git_commit`, `random_seed`, modelio aplinka | 100 % run’ų | MLflow UI | 100 % |
| NFR-12 | Eksperimentai | HPO paieška su įdėtiniais run’ais | ≥ 5 bandymai, ≤ 2 min | MLflow: `hpo-optuna-10trials` trukmė | 10 bandymų, 41 s |

### 3.4 Registro NFR (v1.3)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-13 | Atsekamumas | Kiekviena registro versija turi `git_commit`, `accuracy`, `f1`, `roc_auc` žymas | 100 % versijų | `registry.py show` | 100 % (v1–v5) |

### 3.5 Klasterio NFR (v1.4)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-14 | Našumas | Mokymo Job trukmė | ≤ 2 min | `kubectl get job` | 65 s |
| NFR-15 | Saugumas | MLflow be prisijungimo neprieinamas; slaptažodžių nėra Git’e | 401 be prisijungimo; 0 slaptažodžių Git istorijoje | `curl`; Secret reikšmių paieška `git log -p --all` | 401 / 0 |
| NFR-16 | Prieinamumas | API diegimas be prastovos | ≥ 2 replikos, `maxUnavailable: 0` | `k8s/inference.yaml`, `kubectl rollout status` | 2 / 0 |

### 3.6 CI/CD NFR (v1.5)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-17 | Kokybė | Kokybės vartas blokuoja blogą modelį | `f1 ≥ 0,65` (`params.yaml → gate`) | raudonas CI paleidimas | blokuota: f1 = 0,121 |
| NFR-18 | Patikimumas | Grąžinimas į ankstesnę versiją | ≤ 5 min | rollback commit → abu pod’ai Ready | ~30 s |
| NFR-19 | Greitis | CI/CD trukmė nuo push iki deploy | ≤ 15 min | GitHub Actions | 5 min 33 s |
| NFR-20 | Saugumas | Vaizdai GHCR su `sha-<commit>`, ne `latest`; 0 CRITICAL | 100 % | `k8s/*.yaml`, `docs/trivy-serve.txt` | 100 % / 0 CRITICAL |

### 3.7 Inferencijos NFR (v1.6) — išmatuota (`docs/load-test.md`)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-21 | Vėlinimas | `/predict` p95, 10 lygiagrečių klientų, 2 replikos | ≤ 300 ms | `scripts/load_test.py` klasteryje | 212,4 ms |
| NFR-22 | Vėlinimas | `/predict` p95, viena užklausa | ≤ 50 ms | `load_test.py -c 1` | 31,4 ms |
| NFR-23 | Pralaidumas | `/predict` užklausų per sekundę (2 replikos) | ≥ 50 req/s | `load_test.py` | 85,9 req/s |
| NFR-24 | Dydis | Modelio artefaktas (`model.skops`) | ≤ 50 MB | MLflow artefaktas | 27,1 MB |
| NFR-25 | Dydis | Inferencijos vaizdas | ≤ 700 MB | `docker images` | 627 MB |
| NFR-26 | Ištekliai | API pod’o atmintis | ≤ 512 MiB | cgroup `memory.current` | ~262 MiB |

## 4. Prielaidos ir apribojimai
- Lokalus `kind` klasteris (1 node), CPU; DVC remote — lokalus katalogas `~/dvcstore-u1`.
- Duomenys fiksuoti HF revizija `fbeef6ec0e6fd88a5028b94683144000a6b380d5`.
- MLflow su basic-auth (vartotojai `admin`, `mlops-ci`), GitHub self-hosted runner’is tame pačiame kompiuteryje.

## 5. Žinomos rizikos
| Rizika | Tikimybė | Poveikis | Mitigacija |
|---|---|---|---|
| `kind delete cluster` ištrina PV | Vidutinė | Aukštas | run’ų metaduomenys atkuriami per `reproduce.py`; U2 — atsarginė kopija |
| Lokalus DVC remote nepasiekiamas kitame kompiuteryje | Aukšta | Žemas | `python src/download_data.py` duoda tuos pačius baitus (tas pats md5) |
| Klasių disbalansas (24 % >50K) | — | Vidutinis | F1/recall KPI, `class_weight` hiperparametras |
| Self-hosted runner’is vieša repo | Vidutinė | Aukštas | fork PR reikalauja patvirtinimo; runner’is paleidžiamas tik kai reikia |
| Runner’is išjungtas — CD laukia eilėje | Aukšta | Žemas | lint/test veikia GitHub’e; deploy rankiniu būdu per `scripts/deploy.sh` |

## 6. Keitimo istorija
| Versija | Data | Autorius | Pakeitimai |
|---|---|---|---|
| 1.0 | 2026-10-17 | N. Motiejaitis | Problema, FR-01..04, NFR-01..05 |
| 1.1 | 2026-10-18 | N. Motiejaitis | MLflow klasteryje + DVC: NFR-06..10 (atkartojamumas, atsekamumas, patvarumas) |
| 1.2 | 2026-11-09 | N. Motiejaitis | Mokymo sekimas (step, sistemos metrikos), Optuna HPO: FR-05, NFR-11..12 |
| 1.3 | 2026-11-09 | N. Motiejaitis | Model Registry, `@champion`: FR-06, NFR-13 |
| 1.4 | 2026-11-09 | N. Motiejaitis | Mokymo Job, API, MLflow prisijungimas: FR-07..08, NFR-14..16 |
| 1.5 | 2026-11-09 | N. Motiejaitis | CI/CD, kokybės vartas, rollback: NFR-17..20 |
| 1.6 | 2026-11-10 | N. Motiejaitis | Inferencijos NFR su išmatuotomis reikšmėmis: NFR-21..26 |

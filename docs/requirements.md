# Pajamų klasifikavimo platforma (Adult Census) — Reikalavimai

Versija: 1.1 | Data: 2026-10-18 | Autorius: Nikita Motiejaitis

## 1. Projekto apimtis
### 1.1 Problemos aprašymas
Pagal JAV 1994 m. surašymo duomenis (Hugging Face `scikit-learn/adult-census-income`, CC0, 32 561 eil.)
nuspėti, ar asmens metinės pajamos > 50K USD. Tikslas — ne SOTA modelis, o atkartojamas MLOps srautas:
DVC pipeline’as, MLflow serveris lokaliame Kubernetes klasteryje, versijuotas Docker vaizdas.

### 1.2 Stakeholderiai
| Stakeholderis | Interesas | Prioritetas |
|---|---|---|
| ML inžinierius (studentas) | Atkartojami eksperimentai, vienas tracking serveris | Aukštas |
| Dėstytojas (vertintojas) | Paleidimas nuo nulio pagal README, atsekamumas | Aukštas |
| Būsimas inferencijos servisas (U2) | Modelis su signatūra ir aplinka MLflow | Vidutinis |

## 2. Funkciniai reikalavimai (FR)
| ID | Reikalavimas | Prioritetas |
|---|---|---|
| FR-01 | `dvc repro` vykdo prepare → train → evaluate ir sukuria `metrics.json` | Must |
| FR-02 | Kiekvienas mokymas registruoja run’ą **klasterio** MLflow: parametrai, metrikos, modelis, duomenų digest, žymos `git_commit` ir `dvc_raw_md5` | Must |
| FR-03 | `python reproduce.py <run_id>` atkuria istorinį run’ą (kodas, duomenys, parametrai) | Must |
| FR-04 | Mokymo Docker vaizdas, paleistas su `MLFLOW_TRACKING_URI`, atlieka visą pipeline’ą ir užregistruoja run’ą | Should |

## 3. Nefunkciniai reikalavimai (NFR)
### 3.1 Modelio ir mokymo NFR (v1.0)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-01 | Kokybė | Klasių atskyrimas | ROC-AUC ≥ 0,88 (test) | `metrics.json` | 0,907–0,913 |
| NFR-02 | Kokybė | Mažumos klasės (>50K) aptikimas | F1 ≥ 0,65 | `metrics.json` | exp1 0,644 (nepasiekta) → exp3 0,681 |
| NFR-03 | Našumas | Viso pipeline’o trukmė CPU | `dvc repro` ≤ 60 s | `time dvc repro` | ~15 s |
| NFR-04 | Saugumas | Vaizdas be kritinių CVE, ne root | 0 CRITICAL (Trivy), UID ≠ 0 | `docs/trivy-train.txt`, `docker run … id` | <n> / 1000 |
| NFR-05 | Dydis | Mokymo vaizdo dydis | ≤ 700 MB (disk) | `docker images` | ~626 MB |

### 3.2 Eksperimentų sekimo, atkartojamumo ir infrastruktūros NFR (v1.1)
| ID | Kategorija | Reikalavimas | KPI | Kaip matuojama | Faktas |
|---|---|---|---|---|---|
| NFR-06 | **Atkartojamumas** | Istorinis run’as atkuriamas `reproduce.py` | < 2 min, Δaccuracy ≤ 0,005 | `time python reproduce.py <id>` | 18 s, Δ = 0 |
| NFR-07 | Atsekamumas | Run’ai turi `git_commit` + `dvc_raw_md5` | 100 % run’ų | MLflow UI / `search_runs` | 100 % |
| NFR-08 | Atsekamumas | `dvc_raw_md5` = md5 iš `adult.csv.dvc` | 100 % run’ų | palyginimas | sutampa |
| NFR-09 | Patvarumas | MLflow duomenys išlieka perkūrus Pod’us | 0 prarastų run’ų/artefaktų | `kubectl delete pod …` + UI | 0 |
| NFR-10 | Ištekliai | MLflow Pod atmintis | ≤ 1 GiB (limit) | `memory.current` cgroup | ~500 MiB |

## 4. Prielaidos ir apribojimai
- Lokalus `kind` klasteris (1 node), CPU; DVC remote — lokalus katalogas `~/dvcstore-u1`.
- Duomenys fiksuoti HF revizija `fbeef6ec0e6fd88a5028b94683144000a6b380d5`.

## 5. Žinomos rizikos
| Rizika | Tikimybė | Poveikis | Mitigacija |
|---|---|---|---|
| `kind delete cluster` ištrina PV | Vidutinė | Aukštas | run’ų metaduomenys atkuriami per `reproduce.py`; U2 — atsarginė kopija |
| Lokalus DVC remote nepasiekiamas kitame kompiuteryje | Aukšta | Žemas | `python src/download_data.py` duoda tuos pačius baitus (tas pats md5) |
| Klasių disbalansas (24 % >50K) | — | Vidutinis | F1/recall KPI, `class_weight` hiperparametras |

## 6. Keitimo istorija
| Versija | Data | Autorius | Pakeitimai |
|---|---|---|---|
| 1.0 | 2026-10-17 | N. Motiejaitis | Problema, FR-01..04, NFR-01..05 |
| 1.1 | 2026-10-18 | N. Motiejaitis | MLflow klasteryje + DVC: NFR-06..10 (atkartojamumas, atsekamumas, patvarumas) |

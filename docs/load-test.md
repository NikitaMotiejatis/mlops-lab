# Inferencijos apkrovos testas (U2-R4, U2-R7)

Užklausa: `docs/example.json`, `POST /predict`.
Modelis: `adult-income` v1 (`@champion`, run `bebf51e6`), vaizdas `ghcr.io/nikitamotiejatis/mlops-lab-serve:sha-833722d5`, 2 replikos, CPU limit 1.

| Scenarijus | Užklausų | Lygiagrečių | p50 | p95 | p99 | Pralaidumas | Klaidų |
|---|---|---|---|---|---|---|---|
| Klasterio viduje → Service → 2 pod’ai | 1000 | 10 | 111,9 ms | **212,4 ms** | 225,6 ms | **85,9 req/s** | 0 |
| Klasterio viduje → Service → 2 pod’ai | 1000 | 50 | 571,1 ms | 787,3 ms | 831,7 ms | 85,6 req/s | 0 |
| port-forward → 1 pod’as | 1000 | 10 | 229,0 ms | 259,9 ms | 282,6 ms | 43,0 req/s | 0 |
| port-forward → 1 pod’as, po vieną | 300 | 1 | 25,4 ms | 31,4 ms | — | 38,0 req/s | 0 |

- Modelio artefaktas `model.skops`: 27,1 MB; pod’o atmintis: ~262 MiB (abu pod’ai; limit 1 GiB).
- Viena užklausa ≈ 21 ms CPU (300 medžių); `n_jobs=1` vietoj `-1` — 3× greičiau; `async def` — 2× didesnis pralaidumas.
- Vienas pod’as su 1 CPU apdoroja ~43 req/s (≈ 23 ms užklausai). 2 replikos duoda 85,9 req/s, t. y. pralaidumas auga beveik tiesiškai su replikų skaičiumi.
- Esant 10 lygiagrečių užklausų, servisas jau išnaudoja visą CPU: padidinus iki 50, pralaidumas nepakinta (85,6 req/s), o p95 išauga nuo 212 iki 787 ms, nes užklausos tik ilgiau laukia eilėje. Daugiau pralaidumo — daugiau replikų.


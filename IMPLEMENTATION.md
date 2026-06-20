# Implementačný denník

## 2026-06-20 — Míľnik 1: projektová kostra

- Rozsah: FastAPI/Jinja aplikácia, konfigurácia ciest, healthcheck, Python 3.12 Docker image a Docker Compose pre port 8081.
- Zmenené subsystémy: aplikácia, runtime konfigurácia, kontajner, základ testov.
- Rozhodnutia: perzistentné dáta sú pod `/data`; OpenAI kľúč bude čítaný výhradne zo súboru `/run/secrets/openai_api_key`.
- Známe obmedzenia: úložisko, generovanie a finálny vizuál ešte nie sú implementované.
- Testy:
  - `.venv/bin/python -m py_compile app/*.py tests/*.py` — úspech.
  - `.venv/bin/pytest -q` — 2 testy úspešné.
  - `docker build -t omalovanky:milestone-1 .` — úspešný Python 3.12 image.
- Commit: `Scaffold FastAPI application`.
- Zostáva: katalóg a prompt, worker a SQLite, export, UI, E2E a GitHub Actions.

## 2026-06-20 — Míľnik 2: katalóg, validácia a prompt

- Rozsah: stabilný katalóg svetov, akcií a 15 postáv vrátane šiestich postáv z Cars; Pydantic validácia a serverový prompt pre deti 3–5 rokov.
- Zmenené subsystémy: katalóg, API schémy, prompt builder, verejný endpoint `/api/catalog`.
- Rozhodnutia: zadanie vyžaduje 1–4 unikátne postavy a explicitne zvolené svety; vlastná veta iba spresňuje scénu a má maximálne 300 znakov.
- Známe obmedzenia: model môže konkrétne chránené postavy občas vizuálne interpretovať nepresne; UI preto neskôr ponúkne opakovanie.
- Testy:
  - `.venv/bin/python -m py_compile app/*.py tests/*.py` — úspech.
  - `.venv/bin/pytest -q` — 9 testov úspešných.
- Commit: `Add character catalog and prompt validation`.
- Zostáva: worker a SQLite, export, UI, E2E a GitHub Actions.

## 2026-06-20 — Míľnik 3: OpenAI klient, SQLite a worker

- Rozsah: perzistentné generovacie úlohy, transakčné obmedzenie jednej aktívnej úlohy, background worker, obnova po reštarte a OpenAI Image API klient.
- Zmenené subsystémy: SQLite úložisko, image provider, worker, `POST/GET /api/generations`.
- Rozhodnutia: produkčný klient používa `gpt-image-2`, kvalitu `medium`, PNG, nepriehľadné pozadie a rozmer 1024×1440 alebo 1440×1024; testy používajú injektovaný fake provider.
- Známe obmedzenia: v tomto míľniku worker uchová iba zdrojový PNG; tlačová úprava a PDF pribudnú v ďalšom.
- Testy:
  - `.venv/bin/python -m py_compile app/*.py tests/*.py` — úspech.
  - `.venv/bin/pytest -q` — 13 testov úspešných vrátane súbehu, workera a obnovy po reštarte.
- Commit: `Implement generation queue and OpenAI provider`.
- Zostáva: tlačové spracovanie, história, UI, E2E a GitHub Actions.

## 2026-06-20 — Míľnik 4: PNG, PDF, tlač a retencia

- Rozsah: čistá čiernobiela A4 rasterizácia pri 300 DPI, A4 PDF, download/print endpointy, posledných 20 výsledkov a odstránenie starších súborov.
- Zmenené subsystémy: Pillow/ReportLab processor, worker dokončovanie, úložisko, súborové endpointy a print šablóna.
- Rozhodnutia: PNG má 2480×3508 px na výšku alebo 3508×2480 px na šírku; PDF používa 12 mm bezpečný okraj.
- Známe obmedzenia: prahovanie je zámerne agresívne pre čistú omaľovánku; veľmi jemné sivé detaily sa odstránia.
- Testy:
  - `.venv/bin/python -m py_compile app/*.py tests/*.py` — úspech.
  - `.venv/bin/pytest -q` — 16 testov úspešných.
  - Prvý integračný beh odhalil príliš rýchly polling v teste; test bol opravený na časový deadline zhodný s produkčným správaním.
- Commit: `Add printable outputs and retention`.
- Zostáva: finálne UI, E2E, vizuálna QA a GitHub Actions.

## 2026-06-20 — Míľnik 5: responzívne používateľské rozhranie

- Rozsah: kompletný tablet-first builder, loading stav, výsledková obrazovka, opakovanie, download/tlač akcie a pás posledných omaľovánok.
- Zmenené subsystémy: Jinja šablóna, CSS design systém, JavaScript stav a API klient, generované kategóriové assety.
- Rozhodnutia: vizuálne náhľady svetov sú originálne generické ilustrácie bez log; presné názvy chránených postáv ostávajú v textových voľbách a serverovom prompte.
- Známe obmedzenia: jednotlivé pomenované postavy používajú konzistentné symbolické avatary, nie oficiálne artworky.
- Testy:
  - `.venv/bin/python -m py_compile app/*.py tests/*.py` — úspech.
  - `.venv/bin/pytest -q` — 16 testov úspešných.
  - Playwright QA na 1449×1086 a 390×844 — správny titulok/H1, selected stavy postavy, automatický výber sveta, prepnutie orientácie a žiadny horizontálny overflow.
  - Konzola po doplnení faviconu bez warningov a chýb.
  - In-app Browser fallback: pripojenie zlyhalo na chýbajúcej sandbox metadáte; vizuálna kontrola preto použila samostatný Playwright runtime.
- Commit: `Build responsive coloring generator UI`.
- Zostáva: browser fidelity iterácia, E2E, CI, GHCR workflow a deployment dokumentácia.

## 2026-06-20 — Míľnik 6: E2E, CI a Raspberry Pi deployment

- Rozsah: plný browser tok cez fake provider, mobilný overflow test, release gate, CI, ARM64 GHCR publikovanie a prevádzkový README.
- Zmenené subsystémy: Playwright E2E, test fixture, shell release gate, GitHub Actions a dokumentácia.
- Rozhodnutia: oficiálne OpenAI SDK podporuje pre GPT Image portrét `1024×1536` a landscape `1536×1024`; následný processor oba formáty normalizuje na presné A4.
- Známe obmedzenia: živý OpenAI request nie je súčasťou automatických testov, aby CI nemíňalo kredit ani nepotrebovalo produkčný secret.
- Testy:
  - `./scripts/check.sh` — úspech: 16 unit/integration testov, 2 Playwright E2E testy a Docker build.
  - E2E overilo builder → generovanie → výsledok → PNG/PDF/tlač akcie → história a mobilný viewport 390×844 bez horizontálneho overflow.
  - Vizuálna QA na 1449×1086 porovnala schválený builder aj výsledkový koncept s implementáciou.
  - Opravené počas fidelity iterácie: príliš vysoké desktopové kategórie, chýbajúci favicon, miniatúrna kresba spôsobená `thumbnail()` a roztiahnutá jediná karta histórie.
  - Above-the-fold copy sa zhoduje so schváleným konceptom; jediná zámerná odchýlka je znak `+` medzi názvami kombinovaných postáv.
  - `docker-compose.yml` prešiel príkazom `docker-compose config` vo verzii 5.1.3; oba GitHub Actions workflowy prešli YAML parserom.
- Commit: `Add E2E CI and Raspberry Pi deployment`.
- Zostáva: finálne porovnanie screenshotov, push a kontrola pracovného stromu.

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

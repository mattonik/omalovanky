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

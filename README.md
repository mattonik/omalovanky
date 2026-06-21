# Čarovné omaľovánky

Súkromný rodinný generátor jednoduchých čiernobielych omaľovánok pre deti vo veku 3–5 rokov. Aplikácia kombinuje princezné, jednorožce, záchranárske šteniatka, postavy z Cars aj K-pop Demon Hunters, vytvorí čistý A4 PNG/PDF a uchová všetky výsledky na disku.

## Funkcie

- 1–4 postavy v jednej scéne
- orientácia A4 na výšku aj na šírku
- vlastný opis scény do 300 znakov
- OpenAI Image API (`gpt-image-2`, stredná kvalita)
- čistý čiernobiely PNG pri 300 DPI a A4 PDF
- tlač priamo z prehliadača
- všetky vygenerované omaľovánky sú uložené na disku, v zozname sa zobrazuje posledných 20
- download čiernobielej aj plnofarebnej verzie
- tlač bez vzoru aj „omaľovánka so vzorom“ s malým farebným náhľadom v rohu
- jedna aktívna generovacia úloha, obnova po reštarte
- responzívne ovládanie pre tablet, mobil a desktop

## Lokálny vývoj

Vyžaduje Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
uvicorn app.main:app --reload --port 8081
```

Otvorte `http://localhost:8081`. Pri lokálnom spustení bez Dockeru nastavte API kľúč ako environment premennú:

```bash
OPENAI_API_KEY="sk-..." \
  uvicorn app.main:app --reload --port 8081
```

## Testy

```bash
pytest -m "not e2e"
RUN_E2E=1 pytest -m e2e
./scripts/check.sh
```

E2E testy používajú lokálny fake provider a nemíňajú OpenAI kredit.

## Docker Compose

```bash
docker compose up -d --build
```

Predvolená adresa je `http://localhost:8081`. Nastavenia možno uložiť do `.env`:

```dotenv
OPENAI_API_KEY=sk-...
OMALOVANKY_PORT=8081
OMALOVANKY_DATA_DIR=/srv/appdata/omalovanky
```

Databáza a obrázky sú uložené v `OMALOVANKY_DATA_DIR`. Compose odovzdá `OPENAI_API_KEY` kontajneru priamo z `.env` alebo zo secret environment poľa vášho Compose pluginu. Kľúč nie je uložený v Git repozitári ani databáze; `.env` je v `.gitignore` a `.dockerignore`.

Pri nasadení cez webový Compose plugin vložte obsah `docker-compose.yml` a do jeho Environment/secret env časti pridajte:

```dotenv
OPENAI_API_KEY=sk-...
OMALOVANKY_DATA_DIR=/srv/appdata/omalovanky
OMALOVANKY_PORT=8081
```

Pre OpenMediaVault Docker Compose plugin je pripravený samostatný príklad, ktorý používa rovnaký `.env` štýl pre prenos `OPENAI_API_KEY`:

- [`deploy/omv/compose.yml`](deploy/omv/compose.yml) – YAML určený priamo do poľa **File**
- [`deploy/omv/environment.example`](deploy/omv/environment.example) – obsah poľa **Environment**
- [`deploy/omv/README.md`](deploy/omv/README.md) – presný postup Pull, Up, healthcheck a aktualizácia

## Raspberry Pi a Tailscale

GitHub Actions publikuje ARM64 image do `ghcr.io/mattonik/omalovanky`.

```bash
docker pull ghcr.io/mattonik/omalovanky:latest
docker compose up -d
```

Ak je Raspberry Pi pripojené do Tailscale, aplikácia bude dostupná na:

```text
http://<tailscale-hostname>:8081
```

Port nie je potrebné publikovať do internetu. Obmedzte prístup firewallom na domácu sieť/Tailscale.

Aktualizácia:

```bash
docker compose pull
docker compose up -d
docker image prune -f
```

## API

- `GET /healthz`
- `GET /api/catalog`
- `POST /api/generations`
- `GET /api/generations/{id}`
- `GET /api/colorings?limit=20`
- `GET /colorings/{id}.png`
- `GET /colorings/{id}/color.png`
- `GET /colorings/{id}.pdf`
- `GET /colorings/{id}/print`
- `GET /colorings/{id}/print-pattern`

Príklad zadania:

```json
{
  "worlds": ["cars"],
  "characters": ["lightning-mcqueen", "mater"],
  "action": "racing",
  "custom_idea": "pretekajú spolu po širokej ceste",
  "orientation": "landscape"
}
```

## Prevádzkové poznámky

- Generovanie je platená externá operácia; aplikácia povoľuje iba jednu aktívnu úlohu.
- Presné postavy nemusia byť pri každom AI pokuse dokonale konzistentné. UI preto ponúka opakovanie.
- `IMPLEMENTATION.md` obsahuje chronologický denník implementácie a testov.
- Projekt je licencovaný pod GPL‑3.0.

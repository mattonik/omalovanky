# OpenMediaVault Docker Compose plugin

Táto konfigurácia je určená na vloženie priamo do formulára **Services → Compose → Files** v OpenMediaVault.

## 1. Vytvorenie Compose súboru

1. V OMV otvorte **Services → Compose → Files**.
2. Kliknite na **Add**.
3. Ako názov zadajte `omalovanky`.
4. Do poľa **File** vložte obsah súboru `compose.yml` z tohto adresára.
5. Zapnite **Show environment file**.
6. Do poľa **Environment** vložte:

```dotenv
OPENAI_API_KEY=sk-...
OMALOVANKY_DATA_DIR=/srv/appdata/omalovanky
OMALOVANKY_PORT=8081
TZ=Europe/Bratislava
```

Pole s API kľúčom použite ako secret environment, ak to vaša verzia OMV Compose pluginu ponúka. Kľúč nevkladajte priamo do Compose YAML.

## 2. Priečinok s dátami

Na Raspberry Pi musí existovať adresár z `OMALOVANKY_DATA_DIR`:

```bash
sudo mkdir -p /srv/appdata/omalovanky
```

Obsahuje SQLite databázu a všetky vygenerované omaľovánky aj farebné vzory. Pri aktualizácii alebo znovuvytvorení kontajnera zostane zachovaný.

## 3. Spustenie

1. Uložte Compose súbor.
2. Vyberte `omalovanky`.
3. Kliknite na **Pull**, aby OMV stiahlo `ghcr.io/mattonik/omalovanky:latest`.
4. Kliknite na **Up**.
5. Počkajte, kým bude kontajner `healthy`.

Aplikácia bude dostupná na:

```text
http://<IP-adresa-Raspberry-Pi>:8081
http://<Tailscale-hostname>:8081
```

Ak zmeníte `OMALOVANKY_PORT`, použite v URL zvolený port.

## 4. Kontrola

Healthcheck:

```text
http://<Tailscale-hostname>:8081/healthz
```

Očakávaný výsledok obsahuje:

```json
{
  "status": "ok",
  "database_parent_ready": true,
  "colorings_dir_ready": true,
  "openai_api_key_present": true,
  "worker_alive": true
}
```

Ak je `openai_api_key_present` hodnota `false`, skontrolujte názov premennej `OPENAI_API_KEY` v poli Environment.

## 5. Aktualizácia

V OMV Compose plugine:

1. vyberte `omalovanky`,
2. kliknite na **Pull**,
3. potom **Up** alebo **Recreate**.

`pull_policy: always` zabezpečí kontrolu najnovšieho `latest` image aj pri opätovnom nasadení.

## Zálohovanie

Zálohujte celý adresár:

```text
/srv/appdata/omalovanky
```

API kľúč patrí do OMV Environment/secret env konfigurácie, nie do zálohy dát aplikácie.

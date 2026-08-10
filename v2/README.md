# Carlo (Domček Bot 2.0)

Tento adresár je izolovaným priestorom pre novú verziu aplikácie.

## Stav

Lokálna implementácia E0–E11 je po záverečnom audite dokončená. API, Discord
proces, worker, React administrácia a PostgreSQL bežia v izolovanom staging
prostredí; worker zostáva výhradne v bezpečnom režime `shadow`. E12 čaká na
HTTPS, vzdialený CI a podpísaný browser UAT. Produkčný cutover E13 a
stabilizácia E14 neboli vykonané.

Aktuálny stav a stop-ship hranice sú v koreňovom `STATUS.md`. Používateľská,
prevádzková a technická dokumentácia má index v `docs/README.md`.

## Lokálne spustenie

Požiadavkou je Docker s Compose. Existujúce staging credentials musia zostať v koreňovom ignorovanom adresári `secrets/` pod názvami `bot-token` a `animatori-504814-9c7b8298f7f4.json`.

```bash
cd v2
make dev
```

Prvý beh vytvorí ignorovaný `v2/.env` podľa bezpečného vzoru a nový lokálny session secret. Potom zostaví a spustí PostgreSQL, aplikuje migrácie a spustí API, bota, worker aj frontend. Web je na `http://localhost:5173`, API na `http://localhost:8000` a API dokumentácia na `http://localhost:8000/api/docs`.

INFO obrázky sa po uploade spracujú a ukladajú do trvalého Compose volume `media-data`. Lokálne sú dostupné cez API; pri verejnom nasadení musí `PUBLIC_MEDIA_BASE_URL` smerovať na HTTPS adresu dostupnú Discordu. Frontend si pri štarte zosúladí závislosti v cache volume s aktuálnym lock súborom, takže zmena balíkov nevyžaduje ručné mazanie volume.

Procesy sa zastavia pomocou:

```bash
cd v2
make down
```

Kontroly kvality po lokálnej inštalácii závislostí spustí `make check`. Jednotlivé skupiny sú dostupné ako `make backend-check`, `make frontend-check` a `make secret-check`.

## Health endpointy

- `GET /health/live` odpovedá, ak žije API proces; nezávisí od PostgreSQL.
- `GET /health/ready` odpovedá `200`, iba ak je pripravená databáza, inak `503`.

## Záloha a skúška obnovy

Zo zložky `v2/` vytvorí `scripts/backup_postgres.sh CIEL` privátny PostgreSQL
custom dump, archív nahraných INFO obrázkov a SHA-256 manifest. Skript
`scripts/restore_postgres_rehearsal.sh DUMP NOVA_DB --confirm CREATE:NOVA_DB`
obnovuje výhradne do novej, ešte neexistujúcej databázy; existujúci cieľ nikdy
neprepisuje. Po skúške treba testovaciu databázu odstrániť až po zaznamenaní
výsledku podľa prevádzkového checklistu.

## Hranica voči legacy

Počas vývoja novej verzie zostávajú tieto produkčné legacy súbory v koreňovom adresári bez presúvania a bez refaktoringu pre potreby v2:

- `bot.py`,
- `config.py`,
- `utils.py`,
- `oznamy_db.py`,
- `migrate_db.py`,
- `cogs/`,
- `requirements.txt`,
- `thoughts.txt`,
- `oznamy.db` v lokálnom runtime.

Nová verzia nebude importovať legacy moduly. Migrácia údajov sa vykoná samostatným nástrojom v etape E10.

## Štruktúra

```text
v2/
  backend/
  frontend/
  deploy/
  docker/
  scripts/
  compose.yaml
  compose.production.yaml
  Makefile
```

Riadiace dokumenty projektu zostávajú v koreňovom adresári:

- `ZADANIE.md`,
- `PLAN_IMPLEMENTACIE.md`,
- `STATUS.md`.

Dokumentácia odovzdania:

- `docs/POUZIVATELSKY_MANUAL.md`,
- `docs/PREVADZKOVY_MANUAL_ZLYHANE_PUBLIKOVANIE.md`,
- `docs/TECHNICKA_ARCHITEKTURA.md`,
- `docs/ZNAME_OBMEDZENIA.md`.

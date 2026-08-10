# Kontrolná brána E1

## Kritériá

- [x] API, bot, worker a frontend sa spustia jedným zdokumentovaným postupom.
- [x] `/health/live` potvrdí živý API proces aj bez pripravenosti databázy.
- [x] `/health/ready` vráti úspech s dostupnou databázou a `503` s nedostupnou databázou.
- [x] API, bot aj worker používajú spoločnú typovanú konfiguráciu a databázový modul.
- [x] Prvá Alembic migrácia sa aplikuje na čistý PostgreSQL.
- [x] Backend formátovanie, lint, typová kontrola a testy prejdú.
- [x] Frontend formátovanie, lint, typová kontrola, testy a build prejdú.
- [x] CI definícia pokrýva backend, frontend, migrácie a kontrolu tajomstiev.
- [x] Legacy produkčný kód zostal nedotknutý.

## Overenie

- `docker compose up -d --build` zostavil a spustil PostgreSQL 18.4, baseline migráciu, API, Discord proces, worker a frontend.
- Bot sa pripojil ako aplikácia `1535771583841439765` výhradne ku staging guild `1535774834955391047`; v E1 neregistruje produktové príkazy.
- Worker opakovane zapísal heartbeat s `product_jobs_enabled=false`.
- Liveness vrátil `200` pri dostupnej aj zastavenej databáze; readiness vrátil `200` pri zdravej databáze a `503` pri zastavenej.
- Baseline migrácia sa aplikovala na čistú hlavnú aj čistú testovaciu databázu.
- Backend: 24 súborov správne naformátovaných, Ruff bez nálezov, mypy bez nálezov v 23 súboroch a 8 testov úspešných.
- Frontend: Prettier, ESLint, TypeScript, 2 testy a produkčný Vite build úspešné; npm audit hlási 0 známych zraniteľností.
- Simulovaná čistá kópia bez `.git`, credentials, `.env`, cache, virtuálneho prostredia a `node_modules` úspešne zopakovala inštaláciu z lock súborov, backendové a frontendové kontroly, migráciu, testy, secret scan a Compose validáciu.
- GitHub Actions workflow nebol odoslaný na vzdialený runner, pretože zmeny zatiaľ nie sú commitnuté ani pushnuté; jeho lokálny ekvivalent na čistej kópii prešiel.
- `git diff --name-only` uvádza z pôvodne sledovaných súborov iba `.gitignore`; legacy aplikačný kód nebol zmenený.

## Aktuálny výsledok

**Brána E1: SPLNENÁ.**

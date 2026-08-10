# Backend Carla (Domček Bot 2.0)

Jeden Python balík poskytuje tri samostatné procesy:

- `domcek-api` – FastAPI, Discord OAuth/session, RBAC, editor, nastavenia,
  história, recovery a prevádzkové API,
- `domcek-bot` – Discord Gateway, štyri guild-scoped príkazy, reakcie a
  persistentné archivačné interakcie,
- `domcek-worker` – Google Calendar sync, scheduler, shadow capture,
  publikovanie, heartbeat a recovery.

Všetky procesy používajú spoločnú typovanú konfiguráciu, aplikačné služby,
štruktúrované logovanie a PostgreSQL. Lokálny runtime musí do uzavretia E12
zostať v `PUBLICATION_EXECUTION_MODE=shadow`.

## Lokálne príkazy

Spúšťajú sa z `v2/backend`:

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Bežný vývoj celého systému je dokumentovaný v nadradenom `v2/README.md`.
Architektúra a recovery sú zdokumentované v `docs/TECHNICKA_ARCHITEKTURA.md`
a `docs/PREVADZKOVY_MANUAL_ZLYHANE_PUBLIKOVANIE.md`.

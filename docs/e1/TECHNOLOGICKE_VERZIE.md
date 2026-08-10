# Technologické verzie Domček Bot 2.0

- **Rozhodnuté:** 9. august 2026
- **Rozsah:** etapa E1 a základ ďalších etáp

## Runtime

| Komponent | Uzamknutá verzia | Politika |
|---|---:|---|
| Python | `3.13.14` | podporovaná maintenance vetva; projekt vyžaduje `>=3.13,<3.14` |
| Node.js | `24.18.0` | LTS vetva Krypton |
| PostgreSQL | `18.4` | aktuálna podporovaná minor verzia vetvy 18 |
| uv | `0.11.19` | rovnaká verzia lokálne a v CI |

## Uzamykanie závislostí

- Backend používa `pyproject.toml` a commitovaný `uv.lock`.
- Frontend používa `package.json` a commitovaný `package-lock.json`.
- CI používa iba uzamknuté závislosti (`uv sync --locked`, `npm ci`).
- Upgrade závislosti je samostatná kontrolovaná zmena s testami a aktualizáciou `STATUS.md`.
- Kontajnerové obrazy majú uzamknutú major/minor runtime verziu; pred produkciou sa doplní digest pinning.

## Zdôvodnenie

Python 3.13 zostáva v aktívnej bugfix podpore a poskytuje konzervatívnejšiu kompatibilitu integračných knižníc než novší lokálne dostupný Python 3.14. Node.js 24 je LTS, zatiaľ čo Node.js 26 je v čase rozhodnutia vetva Current. PostgreSQL 18 je podporovaná vetva s plánovanou podporou do novembra 2030.

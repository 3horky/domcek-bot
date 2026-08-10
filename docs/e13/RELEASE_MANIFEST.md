# E13 – release manifest

Pred cutoverom vyplniť a schváliť jeden nemenný manifest. Tag bez digestu nie
je dostatočný.

| Položka | Schválená hodnota |
|---|---|
| Git commit | čaká |
| Release ID / `APP_VERSION` | čaká |
| Backend image + SHA-256 digest | čaká |
| Frontend image + SHA-256 digest | čaká |
| PostgreSQL image + SHA-256 digest | čaká |
| Caddy image + SHA-256 digest | čaká |
| Alembic head | `e4c28f5619ad` |
| CI run | čaká |
| Secret scan | čaká |
| E12 gate schválil | čaká |
| Cutover schválil | čaká |
| Plánovaný čas Europe/Bratislava | čaká |
| Finálna legacy SQLite/config záloha + SHA-256 | čaká |
| PostgreSQL/media restore rehearsal | čaká |
| Overenie Discord hierarchy/oprávnení | čaká |
| Overenie Google read-only prístupu | čaká |
| Schválený najbližší slot/kanál/hash draftu | čaká |
| Rollback operátor | čaká |

Pred použitím image sa digest nezávisle overí:

```bash
docker buildx imagetools inspect IMAGE@sha256:DIGEST
```

Manifest sa po nasadení nemení. Oprava dostane nový release ID a nové digesty.

Workflow `Carlo v2 release images` publikuje backend a frontend pre AMD64 aj
ARM64 do GHCR iba po manuálnom spustení alebo `carlo-v2-*` tagu. Do GitHub
summary zapíše oba výsledné digesty; nič nenasadzuje a nemení produkciu.

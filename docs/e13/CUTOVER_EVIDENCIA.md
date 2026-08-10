# E13 – evidencia produkčného cutoveru

Tento dokument sa vyplní počas jediného schváleného cutover okna. „OK“ bez
času, operátora a konkrétneho dôkazu nie je platné potvrdenie. Pri prvom
neúspešnom stop bode sa ďalšie kroky nevykonávajú a zaznamená sa rozhodnutie o
rollbacku.

## Identita okna

| Položka | Hodnota |
|---|---|
| Release ID / commit | čaká |
| Začiatok okna Europe/Bratislava | čaká |
| Zodpovedný operátor | čaká |
| Prítomný Admin | čaká |
| Rollback operátor | čaká |
| Najbližší schválený publikačný slot | čaká |

## Vykonávací záznam

| Krok | Čas | Operátor | Výsledok | Dôkaz / poznámka |
|---:|---|---|---|---|
| 1 | čaká | čaká | čaká | read-only okno oznámené |
| 2 | čaká | čaká | čaká | legacy slot a stav |
| 3 | čaká | čaká | čaká | jediný legacy scheduler zastavený |
| 4 | čaká | čaká | čaká | SQLite/config SHA-256 manifest |
| 5 | čaká | čaká | čaká | paused preflight |
| 6 | čaká | čaká | čaká | štyri image digesty |
| 7 | čaká | čaká | čaká | DB + Alembic `e4c28f5619ad` |
| 8 | čaká | čaká | čaká | HTTPS + API readiness |
| 9 | čaká | čaká | čaká | dry-run/import report a počty |
| 10 | čaká | čaká | čaká | post-import backup/restore dôkaz |
| 11 | čaká | čaká | čaká | OAuth/roly/nastavenia/draft |
| 12 | čaká | čaká | čaká | bot/guild/oprávnenia |
| 13 | čaká | čaká | čaká | command sync vrátený na false |
| 14 | čaká | čaká | čaká | paused worker/full sync/draft |
| 15 | čaká | čaká | čaká | Admin schválil slot/kanál/hash |
| 16 | čaká | čaká | čaká | live preflight + iba worker recreate |
| 17 | čaká | čaká | čaká | live heartbeat/freshness/incidenty/slot |
| 18 | čaká | čaká | čaká | okno ukončené, legacy obnoviteľný |

## Konečné rozhodnutie

- Cutover úspešný alebo rollback: čaká
- Dôvod rozhodnutia: čaká
- Čas rozhodnutia: čaká
- Admin podpis: čaká
- Technický podpis: čaká
- Odkaz na incident pri rollbacku: čaká

Ak Carlo pred rollbackom vytvoril externý Discord účinok, zapíšu sa všetky run
a message ID. Pri neistote sa publikovanie neopakuje automaticky.

# Dátový model a invarianty E2

## Zásady

- Interné entity používajú UUID; Discord snowflake identifikátory používajú `BIGINT` a doménovú validáciu kladného 63-bitového rozsahu.
- Všetky okamihy sú `TIMESTAMPTZ`; produktové plánovanie vždy explicitne používa `Europe/Bratislava`.
- Celodenné udalosti používajú samostatné lokálne `DATE` hranice s exkluzívnym koncom. Časované udalosti používajú samostatné UTC okamihy. Databázový check nedovolí miešať oba tvary.
- Verejný popis rozlišuje dedenie, vlastný text a zámerne prázdny obsah.
- Mäkké odstránenie zachová historické referencie. Publikačné položky navyše nesú vlastný nemenný snapshot verejného výstupu.
- Stavové hodnoty sú textové s databázovými check constraints. Umožňujú čitateľné dáta a kontrolovaný budúci upgrade bez PostgreSQL enum migrácií.
- JSONB sa používa iba pre polymorfný auditný obraz `before`/`after`; produktové entity nemajú univerzálne JSON úložisko.

## Entity

| Skupina | Tabuľky | Dôležité invarianty |
|---|---|---|
| Server | `guild_config` | jeden záznam na guild, deň 0–6, explicitné pásmo a lokálny čas |
| Kalendár | `calendar_source`, `external_event` | viac zdrojov na guild, unikátny provider/calendar, globálne unikátny source key |
| Redakcia | `event_override`, `event_series_override` | tri stavy popisu, inclusion rozhodnutie, optimistická verzia |
| Ručný obsah | `manual_event`, `info_announcement` | mäkké odstránenie, korektné časové/dátumové rozsahy |
| Publikovanie | `publication_run`, `publication_item`, `publication_message` | unikátny slot na guild, globálny idempotency key, zoradené snapshoty a správy |
| Discord operácie | `channel_archive_request`, `reaction_config`, `reaction_config_channel` | stavový model archivácie a normalizovaný zoznam kanálov reakcií |
| Web a prevádzka | `web_session`, `integration_task`, `audit_log` | hashované relácie, deduplikované úlohy a audit v rovnakej transakcii ako zmena |

## Časové pravidlá

- Týždenný harmonogram je definovaný lokálnym dňom, časom a IANA pásmom.
- Neexistujúci lokálny čas pri jarnom DST prechode sa deterministicky posunie na prvú existujúcu minútu.
- Dvojznačný lokálny čas pri jesennom DST prechode použije prvý výskyt (`fold=0`).
- Publikačné okno má lokálne hranice `[termín, termín + 14 kalendárnych dní)`, takže zachová rovnaký lokálny čas aj cez DST.
- Prekryv viacdňovej udalosti používa polootvorené intervaly; dotyk presne na konci okna sa nezahŕňa.

## Mazanie a história

- Obsahové entity sa bežne deaktivujú alebo mäkko odstránia.
- Zdrojová udalosť sa fyzicky neodstráni, ak má redakčnú alebo publikačnú históriu.
- Publikačný run vlastní svoje snapshot položky a Discord správy; tie sa pri odstránení runu odstránia iba v testovacom/administratívnom fyzickom cleanup toku.
- Audit odkazuje na objekt logickým typom a ID, aby zostal čitateľný aj po mäkkom odstránení zdroja.

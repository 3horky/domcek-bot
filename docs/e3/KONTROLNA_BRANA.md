# Kontrolná brána E3

## Kritériá

- [x] Použitý je iba read-only Calendar scope a credential neopúšťa backend.
- [x] Provider-neutrálny port neimportuje Google ani HTTP implementáciu.
- [x] Google adaptér podporuje metadata kalendára, stránkovanie, full a incremental dotazy.
- [x] Retry je ohraničený a `410 Gone` vyvolá bezpečný full-sync fallback.
- [x] Časované, celodenné, viacdňové, zrušené a opakované udalosti sa normalizujú bez neplatného DB tvaru.
- [x] Presunutý výskyt zachová provider identitu, pôvodný začiatok, series key a interné UUID.
- [x] Full sync označí chýbajúce udalosti až po úspechu všetkých strán.
- [x] Incremental sync nemení udalosti, ktoré Google neposlal.
- [x] Redakčné override zostane po full aj incremental update naviazané na rovnaké external event UUID.
- [x] `stop carlo` sa deteguje iba ako riadiaca veta, raw popis sa zachová a verejný kandidát ju neobsahuje.
- [x] Stav synchronizácie a čerstvosť cache majú testy pre úspech, warning, blocking stav a chybu.
- [x] Full a incremental sync prejdú nad oboma izolovanými testovacími kalendármi.
- [x] Statické kontroly, migrácie, automatizované testy, secret scan a Compose runtime prejdú.
- [x] `STATUS.md` zodpovedá reálnemu stavu a legacy produkčný kód zostal nedotknutý.

## Dôkazy uzavretia

- Google service account používa jediný scope `calendar.readonly`; credential je čítaný zo serverového read-only mountu a composition factory odmietne chýbajúcu cestu.
- Automatizované scenáre overujú percent-encoded calendar ID, efektívny `accessRole`, obnovu tokenu po `401`, bezpečné `403`, retry po `429`, expirovaný token `410`, stránkovanie a strict payload parsing.
- PostgreSQL scenáre overujú atómový viacstránkový full sync, incremental zmeny a zrušenia, missing soft-delete až po úspechu, rollback pri chybe ďalšej strany, zachovanie tokenu a query fingerprint fallback.
- Opakovaný full sync zachová interné UUID a override. Nečakaná zmena `series_key` pri upravenom výskyte vyvolá moderátorské upozornenie bez straty dát.
- Parser rozpozná case-insensitive samostatnú riadiacu vetu aj v reálnom Google HTML tvare, zachová raw popis a riadiaci text neprenesie do verejného kandidáta.
- Opt-in read-only live test prešiel nad primary aj secondary kalendárom: overil prístup, minimálne štyri primary strany, full → incremental → opakovaný full tok, celodenné a recurring fixtures aj zachovanie override.
- E3 migrácia `e219fe464c61` prešla downgrade/upgrade cyklom a `alembic check` potvrdil nulový drift.
- Finálna sada: 64 backendových testov, samostatný live test, Ruff format/lint, prísny mypy nad 51 súbormi, 2 frontendové testy, frontend lint/typecheck/build, secret scan, Compose validácia a `git diff --check`.
- Locked Compose rebuild nainštaloval Google závislosti, migrátor skončil s kódom 0, databáza a API sú healthy, worker a staging bot bežia a frontend odpovedá.

## Aktuálny výsledok

**Brána E3: SPLNENÁ.**

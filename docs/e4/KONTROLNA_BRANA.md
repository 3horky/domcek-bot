# Kontrolná brána E4

## Kritériá

- [x] Composer je čistý, serializovateľný a nezávislý od FastAPI, Discordu, ORM a hodín procesu.
- [x] Najbližší nespracovaný slot a 14-dňové okno fungujú cez oba DST prechody.
- [x] Timed, all-day a viacdňové externé aj manuálne udalosti používajú rovnaký výber.
- [x] Instance a series override priority vrátane `INTENTIONALLY_EMPTY` majú tabuľkové testy.
- [x] `stop carlo`, force include a force exclude vytvoria správny editor aj verejný model.
- [x] Google popis je predvolene vypnutý a pri zapnutí neobsahuje riadiacu vetu.
- [x] INFO platnosť je lokálna a inkluzívna; expirované záznamy sa iba vynechajú.
- [x] Triedenie je stabilné aj po náhodnom premiešaní vstupov a podporuje viac kalendárov.
- [x] Slovenské dni, day emoji a timed/all-day/multi-day formáty sú centralizované a otestované.
- [x] Redakčný obsah nemôže vytvoriť nechcenú Discord zmienku.
- [x] Každá message part spĺňa aktuálne Discord limity, everyone je práve raz a seen target je jednoznačný.
- [x] Fixný fixture vytvára bajtovo rovnaký kanonický JSON snapshot.
- [x] Statické kontroly, automatizované testy, secret scan, Compose runtime a `STATUS.md` prejdú.

## Aktuálny výsledok

**Brána E4: SPLNENÁ.**

## Overenie

- Ruff format/lint a prísny mypy prešli nad celým backendom.
- Prešlo 88 automatizovaných backendových testov; jediný preskočený test je
  samostatne spúšťaný read-only Google live scenár z E3.
- Frontend Prettier, ESLint, TypeScript, 2 testy a produkčný build prešli.
- `alembic check` nenašiel drift, secret scan a `git diff --check` prešli.
- Locked Compose rebuild skončil úspešne; databáza a API sú healthy, worker
  beží, bot je pripojený k staging guild a frontend aj readiness vracajú `200`.

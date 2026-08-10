# Kontrolná brána E2

## Kritériá

- [x] Všetky entity z plánu E2 majú explicitný ORM model a migrovanú tabuľku.
- [x] Unikátne kľúče, cudzie kľúče, check constraints a požadované indexy sú overené na PostgreSQL.
- [x] Hodnotové objekty identifikátorov, stavov, termínu a 14-dňového okna majú unit testy vrátane DST.
- [x] Časované a celodenné udalosti nemožno uložiť v neplatnom alebo zmiešanom tvare.
- [x] Mäkké odstránenie zachová historické referencie a publikačný snapshot.
- [x] Optimistická verzia zabráni tichému prepísaniu override záznamu.
- [x] Repozitáre a Unit of Work držia doménovú zmenu a audit v jednej transakcii.
- [x] Migrácia prejde od prázdnej databázy cez E1 až po E2 a downgrade/upgrade je opakovateľný.
- [x] API endpointy neimportujú ORM modely ani PostgreSQL adaptéry.
- [x] Backendové formátovanie, lint, mypy a všetky testy prejdú.
- [x] Legacy produkčný kód zostal nedotknutý.

## Aktuálny výsledok

**Brána E2: SPLNENÁ.**

Overenie 9. augusta 2026:

- ORM metadata aj PostgreSQL obsahujú všetkých 16 E2 tabuliek,
- Alembic prešiel od prázdneho stavu po E2, downgrade na E1 a opakovaný upgrade; `alembic check` hlási nulový drift,
- Ruff, prísny mypy a 32 backendových testov prešli,
- frontendové formátovanie, lint, typová kontrola, 2 testy a produkčný build prešli,
- rebuiltnutý Compose stack má zdravú databázu a API, migrátor skončil s kódom 0, worker beží a bot je pripojený iba k staging serveru,
- secret scan, Compose validácia, `git diff --check` a kontrola legacy hranice prešli.

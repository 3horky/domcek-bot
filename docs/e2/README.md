# Etapa E2 – doménový a databázový základ

E2 zavádza normalizovanú PostgreSQL schému, čisté doménové hodnoty a transakčnú perzistenčnú vrstvu, na ktorej budú stáť Google synchronizácia, editor aj publikovanie.

## Dokumenty

- [Dátový model a invarianty](./DATOVY_MODEL.md)
- [Kontrolná brána E2](./KONTROLNA_BRANA.md)

## Hranica etapy

E2 nevolá Google ani Discord API a nepridáva administračné endpointy. Overuje, že všetky budúce prípady použitia majú stabilnú reprezentáciu, cudzie kľúče, indexy, stavové hodnoty a transakčné hranice.

## Implementačné výstupy

- čisté doménové hodnoty sú v `v2/backend/src/domcek_bot/domain/`,
- perzistenčne neutrálne záznamy a repository kontrakty sú v `application/`,
- 16 normalizovaných SQLAlchemy modelov, PostgreSQL adaptéry a Unit of Work sú v `infrastructure/`,
- fyzickú schému vytvára Alembic revízia `d5941a2a82ff`,
- databázové testy overujú constraints, indexy, transakčný audit, optimistický konflikt a nemennú publikačnú históriu,
- architektonický test bráni API a aplikačnej vrstve importovať ORM alebo PostgreSQL adaptéry.

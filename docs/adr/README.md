# Architecture Decision Records

Tento adresár obsahuje záväzné architektonické rozhodnutia Domček Bot 2.0.

## Pravidlá

- ADR opisuje kontext, rozhodnutie, dôsledky a zamietnuté alternatívy.
- Prijaté ADR sa spätne neprepisuje tak, aby sa stratila história rozhodnutia.
- Ak sa rozhodnutie zmení, vytvorí sa nové ADR, ktoré pôvodné označí ako nahradené.
- Každá zmena stavu ADR sa zapíše do `STATUS.md`.
- Zdrojom produktových požiadaviek zostáva `ZADANIE.md`; ADR ho nesmie rozšíriť o nové používateľské oprávnenia.

## Index

| ADR | Rozhodnutie | Stav |
|---|---|---|
| [0001](./0001-modularny-monolit-a-procesy.md) | Modulárny monolit a tri procesy | prijaté |
| [0002](./0002-postgresql-a-perzistencia.md) | PostgreSQL a perzistencia | prijaté |
| [0003](./0003-discord-oauth-a-relacie.md) | Discord OAuth a serverové relácie | prijaté |
| [0004](./0004-google-calendar-autentifikacia.md) | Google Calendar autentifikácia | prijaté |
| [0005](./0005-idempotencia-publikovania.md) | Idempotencia a zotavenie publikovania | prijaté |
| [0006](./0006-frontendova-architektura.md) | React/TypeScript frontend | prijaté |
| [0007](./0007-prevadzkove-nasadenie.md) | Kontajnerové nasadenie na jednom hostiteľovi | prijaté s overením infraštruktúry pred produkciou |

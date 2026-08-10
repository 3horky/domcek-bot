# Dokumentácia Carla

Tento adresár je vstupným bodom pre dokumentáciu novej verzie Domček bota.
Autoritatívny rozsah je v koreňovom `ZADANIE.md`, postup v
`PLAN_IMPLEMENTACIE.md` a aktuálny stav vždy v `STATUS.md`.

## Pre používateľov

- [Používateľský manuál](./POUZIVATELSKY_MANUAL.md) – každodenná práca Admina,
  Team Moda a SDB / FMA,
- [Známe obmedzenia](./ZNAME_OBMEDZENIA.md) – hranice prvej verzie a otvorené
  predprodukčné dôkazy.

## Pre prevádzku

- [Riešenie zlyhaného publikovania](./PREVADZKOVY_MANUAL_ZLYHANE_PUBLIKOVANIE.md),
- [produkčná konfigurácia](./e13/PRODUCTION_CONFIG.md),
- [zálohovacia politika](./e13/BACKUP_POLICY.md),
- [cutover](./e13/CUTOVER.md) a [rollback](./e13/ROLLBACK.md),
- [stabilizačné cykly](./e14/STABILIZACNE_CYKLY.md) a
  [vyradenie legacy](./e14/LEGACY_RETIREMENT.md).

## Pre vývoj a údržbu

- [Technická architektúra](./TECHNICKA_ARCHITEKTURA.md),
- [architektonické rozhodnutia](./adr/README.md),
- [dátový model](./e2/DATOVY_MODEL.md),
- [autorizačná matica](./e5/AUTORIZACNA_MATICA.md),
- [testovacia matica](./e11/TESTOVACIA_MATICA.md).

Každá etapa E0–E14 má vlastný adresár alebo kontrolnú bránu. Brána môže byť
označená ako splnená iba vtedy, keď obsahuje skutočný test, runtime dôkaz alebo
výslovne podpísaný externý výsledok.

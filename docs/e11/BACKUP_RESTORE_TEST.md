# E11 – praktická skúška zálohy a obnovy

## Rozsah

- zdroj: lokálna vývojová PostgreSQL databáza Compose projektu `v2`,
- formát: PostgreSQL custom dump s `--no-owner --no-acl`,
- doplnok: gzip archív perzistentného adresára INFO médií,
- integrita: SHA-256 manifest oboch súborov,
- cieľ obnovy: nová izolovaná databáza `carlo_e11_restore_20260810`.

## Prvé overenie 10. augusta 2026

- databázový dump aj mediálny archív boli neprázdne,
- oba SHA-256 kontrolné súčty prešli,
- mediálny archív bol čitateľný a obsahoval koreň `media/`,
- `pg_restore --exit-on-error` skončil úspešne,
- obnovená databáza obsahovala 18 public tabuliek,
- obnovená Alembic verzia bola `2c7f9d8b31a0`,
- kontrolné počty `guild_config|calendar_source|external_event|publication_run|audit_log`
  boli v zdroji aj cieli zhodne `1|0|0|0|3`,
- po zaznamenaní dôkazu bola iba novovytvorená skúšobná databáza odstránená;
  zdrojová databáza a vytvorený dump zostali bez zmeny.

Dočasné záložné súbory nie sú súčasťou repozitára. Produkčná retenčná politika,
šifrované off-site úložisko a pravidelný automatický harmonogram sú definované
v `docs/e13/BACKUP_POLICY.md`; aktivujú sa až na schválenom produkčnom hoste.

## Opakované overenie po záverečnom audite

Po pridaní prevádzkovej diagnostiky a finálnych migrácií bola skúška zopakovaná
nad aktuálnou shadow databázou:

- databázový dump aj mediálny archív boli neprázdne a oba SHA-256 súčty prešli,
- mediálny archív bol čitateľný a obsahoval koreň `media/`,
- obnova do novej izolovanej databázy
  `carlo_e11_restore_audit_20260810` prešla s `pg_restore --exit-on-error`,
- obnovená databáza mala Alembic head `d7a4cb1268ef`, 20 public tabuliek
  vrátane `alembic_version`, teda 19 aplikačných tabuliek,
- kontrolné počty
  `guild_config|calendar_source|external_event|publication_run|audit_log|runtime_heartbeat`
  boli v zdroji aj cieli zhodne `1|2|17|0|6|2`,
- po porovnaní bola odstránená iba skúšobná databáza a dočasný backup adresár;
  zdrojová shadow databáza zostala nedotknutá.

## Aktuálny head `e4c28f5619ad`

Po výslovnom schválení používateľom bola 10. augusta 2026 zopakovaná celá
praktická skúška aj na aktuálnom heade:

- vytvorený PostgreSQL custom dump aj archív médií boli neprázdne,
- oba súbory prešli kontrolou podľa vytvoreného SHA-256 manifestu,
- dump bol obnovený s `pg_restore --exit-on-error` do novej izolovanej databázy
  `carlo_e11_restore_e4c28f5619ad`,
- obnovená databáza mala 20 public tabuliek a Alembic verziu
  `e4c28f5619ad`,
- kontrolné počty
  `guild_config|calendar_source|external_event|publication_run|audit_log|runtime_heartbeat|shadow_publication`
  boli v zdroji aj cieli zhodne `1|2|17|0|6|4|1`,
- po úspešnom porovnaní bola odstránená výhradne skúšobná databáza; následný
  dotaz potvrdil nulový počet databáz s týmto názvom,
- tri dočasné záložné artefakty a ich izolovaný adresár boli po zaznamenaní
  výsledku odstránené. Nie sú obnoviteľné z tohto adresára; zdrojová databáza,
  médiá ani repozitár sa tým nezmenili.

Aktuálny custom-dump/media/SHA-256/restore dôkaz je tým splnený. Samostatný
migračný downgrade/upgrade a `alembic check` zostávajú doplnkovým dôkazom
nulového driftu.

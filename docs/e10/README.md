# Etapa E10 – migrácia legacy údajov

Migračný nástroj je dostupný ako `domcek-migrate-legacy` alebo modul
`python -m domcek_bot.migration.legacy`. Zdrojovú SQLite databázu vždy otvára v
read-only immutable režime a pred importom overí, že sa jej SHA-256 počas práce
nezmenilo.

## Bezpečnostný model

- Dry run je predvolený; zápis vyžaduje `--apply`.
- Cieľ sa zadáva explicitným PostgreSQL URL a názov databázy sa musí presne
  zopakovať cez `--confirm-target`.
- Aktívna nespárovaná legacy udalosť sa importuje iba s
  `--approve-unmatched`.
- Jednoznačný Google kandidát sa nikdy nespáruje iba odhadom: report ho označí
  `review_google_match` a používateľ ho schváli mapou `legacy_id -> event UUID`.
- Import používa stabilné UUIDv5 a `ON CONFLICT`, takže opakovanie nevytvorí
  kópie.
- Pôvodný súbor sa počas skúšok pripája do kontajnera `:ro`; nástroj navyše
  používa SQLite `mode=ro&immutable=1` a `PRAGMA query_only`.

## Produkčný vzor

```text
domcek-migrate-legacy \
  --source /read-only-backup/oznamy.db \
  --as-of YYYY-MM-DD \
  --guild-id DISCORD_GUILD_ID \
  --actor-user-id ADMIN_DISCORD_ID \
  --target-database-url postgresql+asyncpg://.../carlo \
  --json-report migration.json \
  --markdown-report migration.md
```

Po kontrole reportu sa pridá `--apply --confirm-target carlo`; podľa reportu aj
`--approve-unmatched`, `--approved-matches approvals.json` a
`--apply-settings`. Produkčný cutover musí používať finálnu zálohu, nie živý
menený SQLite súbor.

## Skutočná inventarizácia

Zdroj `oznamy.db` z 10. augusta 2026 má SHA-256
`5ef992e08ae66fecad23764b0dcd5bb0c709fa399c15de1c1d299bd514481c02` a obsahuje
dva záznamy: jednu legacy udalosť a jeden INFO oznam. Oba sú k referenčnému dňu
expirované a preto sa zachovajú ako neaktívna história. Nenašli sa poškodené
dátumy, neplatné URL ani duplicity. Čas konca legacy udalosti v starej schéme
neexistoval, preto report transparentne uvádza konzervatívny odhad 60 minút.

Pôvodné `error_notification_users` nemajú priamy ekvivalent: Carlo používa
nakonfigurovaný moderátorský kanál. Hodnota preto zostáva v reporte ako
`unsupported`, nie je potichu zahodená ani nesprávne mapovaná.

Kontrolný výsledok je v [KONTROLNA_BRANA.md](./KONTROLNA_BRANA.md).

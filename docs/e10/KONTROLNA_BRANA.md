# Kontrolná brána E10

## Kritériá

- [x] Legacy SQLite bola inventarizovaná bez zápisu a so SHA-256 kontrolou.
- [x] Report obsahuje počty aktívnych, budúcich, expirovaných, neplatných a duplicitných záznamov aj pôvodné nastavenia.
- [x] INFO, udalosti, rozvrh, emoji a auto-reaction kanály majú explicitné mapovanie.
- [x] Budúce udalosti sa konzervatívne párujú podľa normalizovaného názvu a presného lokálneho času; zhoda vyžaduje schválenie.
- [x] Nástroj má predvolený dry run, JSON aj Markdown výstup, stabilné kľúče, cieľové potvrdenie a transakčný import.
- [x] Dva dry runy nad skutočným zdrojom vytvorili bajtovo rovnaký report.
- [x] Prvý import do čistej izolovanej PostgreSQL vytvoril presne jeden neaktívny manuálny a jeden neaktívny INFO záznam.
- [x] Okamžité zopakovanie importu nevytvorilo žiadny záznam ani zmenu nastavení navyše.
- [x] Po zmazaní a novom vytvorení skúšobnej databázy vznikol bajtovo rovnaký report a rovnaké počty.
- [x] Zdrojová SQLite zostala po skúškach s nezmeneným SHA-256.
- [x] Unit, integračné a úplné regresné testy prešli.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Dôkazy

- [Prvý dry run](./dry-run.json) a [druhý dry run](./dry-run-2.json) sú
  bajtovo zhodné.
- [Prvá migračná skúška](./import-trial-1.json) a
  [skúška po znovuvytvorení DB](./import-trial-2.json) sú bajtovo zhodné.
- [Opakovaný import](./import-trial-1-repeat.json) uvádza `inserted_info = 0`,
  `inserted_manual = 0`, `settings_changed = 0` a `skipped_existing = 2`.
- Databázový kontrolný výpis po importe bol `1|1|2|1`: manuálne udalosti,
  INFO oznamy, auditné záznamy a auto-reaction kanály.
- Izolovaná databáza `domcek_e10_trial` bola po skúške odstránená; zdrojový
  `oznamy.db` odstránený ani zmenený nebol.

## Výsledok

**Brána E10: SPLNENÁ.** Úplná regresná sada má 140 úspešných backendových testov
a jeden zámerný opt-in Google Calendar skip; Ruff, prísny mypy nad 74 zdrojmi,
11 frontendových testov, TypeScript, ESLint aj produkčný build prešli.

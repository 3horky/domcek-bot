# E13 – vykonávací cutover runbook

## Stop podmienky pred začiatkom

- E12 kontrolná brána nie je podpísaná.
- Nie je vyplnený `RELEASE_MANIFEST.md`.
- Nie je aktuálna a obnovou overená PostgreSQL záloha.
- Chýba finálna SQLite záloha legacy bota.
- Najbližší publikačný slot alebo zodpovednosť zaň je nejednoznačná.
- Nie je prítomný Admin oprávnený potvrdiť draft a OAuth.

## Postup

Každý krok označiť časom, operátorom a výsledkom. Pri chybe sa nepokračuje.

1. Oznámiť krátke read-only okno a pozastaviť legacy redakčné zmeny.
2. Zapísať presný stav najbližšieho legacy publikačného termínu.
3. Zastaviť iba legacy scheduler a overiť, že nebeží druhá inštancia.
4. Vytvoriť finálnu SQLite/config zálohu a SHA-256 manifest.
5. Spustiť preflight z `PRODUCTION_CONFIG.md`; worker musí byť presne `paused`.
6. Stiahnuť presné image digesty z release manifestu.
7. Spustiť iba `db` a jednorazový `migrate`; potvrdiť Alembic head
   `e4c28f5619ad`.
8. Spustiť API, frontend a proxy; potvrdiť HTTPS a `/health/ready`.
9. Vykonať finálny dry-run a potom import legacy údajov; porovnať report.
10. Vytvoriť post-import PostgreSQL/media backup, overiť SHA-256 a obnoviť ho
    do novej izolovanej databázy. Porovnať Alembic head a kontrolné počty;
    odstrániť iba skúšobnú databázu po zaznamenaní dôkazu.
11. Admin overí OAuth, roly, nastavenia a najbližší draft cez web.
12. Spustiť bot proces, overiť gateway, granulárne oprávnenia a Compose stav
    `healthy` s práve jednou aktívnou inštanciou.
13. Raz povoliť/uskutočniť riadenú synchronizáciu guild príkazov, potom ju
    znovu nastaviť na `false`.
14. Spustiť worker ešte v `paused`, vykonať full Calendar sync a porovnať draft.
15. Admin explicitne schváli konkrétny slot, cieľový kanál a obsah.
16. Až po implementácii a zelenej bráne `UX5-07` a `UX7-07` odstrániť
    dočasnú fail-closed validáciu v `config.py` a zmeniť
    `PUBLICATION_EXECUTION_MODE=live`. Spustiť validátor s
    `--allow-live` a znovu vytvoriť iba worker.
17. Potvrdiť worker log režimu `live`, Compose stav `healthy`, práve jednu
    aktívnu inštanciu, Calendar freshness, nulový rozpracovaný incident a
    jednoznačný nasledujúci slot.
18. Ukončiť read-only okno; legacy scheduler zostáva vypnutý, ale obnoviteľný.

## Bezprostredné overenie

- HTTPS stránka, API readiness a OAuth fungujú.
- Bot je pripojený iba k správnemu guild.
- Worker beží práve raz a v logu je `live`.
- Najbližší draft má očakávané okno, kanál, počet správ a hash.
- `publication_run` neobsahuje nečakaný alebo duplicitný slot.
- Moderátorský test alert dorazí bez secrets alebo tracebacku.

E13 sa uzavrie až po jednom úspešnom kontrolovanom drafte a všetkých vyššie
uvedených potvrdeniach. Prvé tri skutočné publikácie patria do E14 dohľadu.
Časy, operátori, výsledky a odkazy na dôkazy sa zapisujú do
`CUTOVER_EVIDENCIA.md`.

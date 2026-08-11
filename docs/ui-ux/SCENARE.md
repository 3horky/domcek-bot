# Scenáre a fixtures UI/UX auditu

Toto je spoločný vstup pre UX0–UX10. Testovacie dáta sú provider-neutrálne a externé účinky nahrádza browser mock alebo izolovaný staging.

## Roly a oprávnenia

| Profil         | Hlavné možnosti                                       | Povinné negatívne overenie                      |
| -------------- | ----------------------------------------------------- | ----------------------------------------------- |
| Admin          | celý web, nastavenia, roly, audit, ručné publikovanie | žiadna akcia nesmie obísť čerstvé oprávnenie    |
| Team Mod       | redakcia a kanály                                     | nevidí Nastavenia, Audit ani ručné publikovanie |
| SDB / FMA      | prehľad a ručné publikovanie                          | nevidí ostatnú administráciu                    |
| bez oprávnenia | prihlasovacia alebo zamietnutá obrazovka              | nevidí chránené dáta ani akcie                  |

Browser fixture používa profily `admin`, `team_mod`, `publisher` a `none` v `e2e/carlo.spec.ts`. Serverové autorizačné testy zostávajú samostatnou bezpečnostnou hranicou.

## Route a primárna úloha

| Route                    | Primárna úloha                                       | Primárne roly              | Povinné stavy                                                |
| ------------------------ | ---------------------------------------------------- | -------------------------- | ------------------------------------------------------------ |
| `/`                      | pochopiť najbližšie zverejnenie, prípadne publikovať | Admin, SDB / FMA, Team Mod | pripravené, upozornenie, bez dát, API chyba, busy            |
| `/oznamy`                | upraviť celý budúci balík a porovnať Discord náhľad  | Admin, Team Mod            | calendar/manual/INFO, vylúčené, dlhý balík, konflikt, chyba  |
| `/historia`              | overiť skutočný výsledok publikovania                | oprávnený správca          | empty, úspech, zlyhanie, neistý stav                         |
| `/audit`                 | dohľadať zmenu a aktéra                              | Admin                      | empty, filtre, dlhé dáta, API chyba                          |
| `/stav`                  | zistiť, či Carlo vyžaduje zásah                      | oprávnený správca          | healthy, degraded, stale, API chyba                          |
| `/kanaly`                | vytvoriť alebo archivovať kanál                      | Admin, Team Mod            | empty archív, žiadosť, modal, Discord chyba, forbidden       |
| `/roly`                  | nájsť človeka a zmeniť Carlo oprávnenie              | Admin                      | idle, loading, bez výsledku, chyba, potvrdenie, busy         |
| `/reakcie`               | nastaviť a bezpečne vyskúšať tri reakčné pravidlá    | Admin                      | loading, error, disabled, dirty, nedostupné emoji, test busy |
| `/nastavenia`            | meniť trvalé pravidlá publikovania a kalendáre       | Admin                      | prvé spustenie, dirty, konflikt, relácia, sync chyba         |
| `/login` a neznáma route | prihlásiť sa alebo nájsť ďalší krok                  | všetci                     | denied, expired, 404                                         |

## Dátové fixtures

- bežná časovaná a viacdňová/celodenná udalosť,
- recurring výskyt s instance aj series override,
- vylúčená udalosť `stop carlo`,
- manuálna udalosť a INFO oznam s obrázkom,
- nulový a 60-položkový balík,
- žiadny kalendár, jeden zdravý a viac zdrojov s čiastočným zlyhaním,
- dostupné aj nedostupné serverové emoji,
- člen s avatarom, bez avataru, bez výsledku a zlyhané vyhľadávanie,
- nulový, jeden a viacnásobný výber rolí/kanálov,
- úspech, 401/403, konflikt, sieťová chyba a oneskorená odpoveď.

## Viewporty a dôkaz

- Primárny desktop: `1440 × 1000`; široký desktop: `1920 × 1080`; kompaktný desktop: `1024 × 768`.
- Sekundárny mobil: Playwright Pixel 7; navyše nízky viewport a 200 % zoom v relevantnej etape.
- Playwright ukladá trace a screenshot pri zlyhaní. Schválené referenčné screenshoty patria do `docs/ui-ux/evidence/<etapa>/`; generované testové artefakty sa necommitujú.
- Každá etapa eviduje scenár, viewport, rolu, dátový stav a výsledok v `AUDIT_MATICA.md`.

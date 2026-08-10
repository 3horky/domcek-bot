# E11 – testovacia a stop-ship matica

## Automatizované vrstvy

| Oblasť | Dôkaz | Stav |
|---|---|---|
| čas, DST, 14 dní, overlap, INFO inkluzivita | `test_domain_time.py`, composer testy | prešlo |
| stop carlo, Google policy, instance/series override | Calendar, composer a editor integračné testy | prešlo |
| deterministické radenie a Discord limity | composer snapshot a batching testy | prešlo |
| OAuth, session, CSRF, CORS, rate limit, logout | `test_auth.py`, session repository | prešlo |
| serverová RBAC a guild izolácia | API matica, editor, settings, história | prešlo |
| XSS/mention vstupy | React text rendering, mention neutralizácia a payload testy | prešlo |
| thumbnail/URL SSRF vstupy | neglobálne IPv4/IPv6 odmietnuté; server URL nenačítava | prešlo |
| Calendar full/incremental/410/failure | sync integračné a adapter unit testy | prešlo |
| publikovanie/retry/uncertain/reconcile/recovery | publication engine integračné testy | prešlo |
| dva workery a rovnaký slot | paralelný PostgreSQL scheduler test | prešlo |
| runtime heartbeat a kontajnerové zdravie | fresh/stale/duplicate/state/mode integračné testy a Compose smoke | prešlo |
| Discord Gateway výpadok a nečíselná latencia | `test_runtime_latency_is_safe_for_disconnected_gateway`, runtime reconnect smoke | prešlo |
| audit atomicky so zmenou | persistence a aplikačné integračné testy | prešlo |
| kanál, archivácia, roly a posledný Admin | channel/settings integračné testy | prešlo |
| upload rastera a metadata/decompression ochrana | media unit testy | prešlo |
| migrácie | downgrade/upgrade/check na dev aj test DB | prešlo |
| backup/restore | current-head custom dump, SHA-256, 20 public tabuliek, zhodných 7 kontrolných počtov | prešlo |

Aktuálny úplný výsledok po druhom audite: **188 úspešných backendových testov**,
jeden zámerný opt-in Google live skip, Ruff a prísny mypy nad 136 zdrojmi;
**13 úspešných Vitest testov**, Prettier, TypeScript, ESLint, produkčný Vite
build a **34 úspešných Playwright behov** (17 desktop + 17 mobile).
Samostatný full-stack projekt navyše prešiel **2 úspešnými Playwright behmi**
(desktop + mobile) cez skutočné FastAPI a PostgreSQL.

## Minimálnych 14 webových scenárov zo zadania

Scenáre 1–14 majú doménové/API pokrytie a samostatný Playwright používateľský
tok v `v2/frontend/e2e/carlo.spec.ts`. Každý scenár beží v desktop Chromium
1440 × 1000 aj v mobilnom profile Pixel 7. Browser vrstva používa deterministické
mock HTTP hranice; nenahrádza PostgreSQL/Discord integračnú sadu, ale overuje
skutočný React routing, formuláre, modaly, rolové zobrazenie a responzívny tok.
Archivačný scenár vykonáva žiadosť Team Moda aj následné schválenie Adminom po
reloadnutí roly; rolový scenár vykonáva udelenie aj odobratie Team Mod roly.

Oddelený `playwright.fullstack.config.ts` spúšťa izolovaný testovací API server,
ktorý odmietne inú databázu než `*_test`. Desktop aj Pixel 7 cez reálne API
uložia redakčnú úpravu Calendar udalosti, reloadnú stránku a novým API čítaním
potvrdia PostgreSQL perzistenciu. Global teardown zastaví iba presne filtrovaný
one-off E2E server a vyčistí testovaciu DB; následná kontrola potvrdila počty
`0|0|0|0` pre guild, event, session a override a prázdny port 4180.

Navyše sa automatizovane overuje 60-položkový balík bez horizontálneho
pretečenia, klávesnicový skip-link, návrat fokusu po zatvorení modalu a
`prefers-reduced-motion`. Browser behy odhalili a následne potvrdili opravu
návratu fokusu aj jednoznačné prepojenie formulárových labelov. Podpísaná
ľudská vizuálna kontrola, 200 % zoom a reálne staging účty
zostávajú pravdivo otvorené v E12 UAT.

## Prevádzkové skúšky

- samostatné restarty API, frontendu, workera a bota prešli,
- API readiness pri vypnutej DB vrátila 503 a po návrate DB bez restartu 200,
- bot po restarte obnovil Gateway session a štyri staging príkazy,
- worker po restarte vykonal recovery a ďalší scheduler poll,
- DB-backed healthcheck vyžaduje presne jednu čerstvú `connected` bot inštanciu
  a jednu `running` worker inštanciu v zhodnom publikačnom režime; lokálny
  pozitívny smoke vrátil oba procesy `healthy` a 1-sekundový stale limit
  korektne vrátil nezdravý stav,
- Calendar/intro/Discord čiastočné chyby sú injektované kontrolovanými adaptérmi,
- záloha a obnova sú prakticky overené v `BACKUP_RESTORE_TEST.md`.

## Stop-ship stav

Druhý audit otvoril a implementácia opravila priečne publikačné, recovery,
autorizačné, migračné, shadow-reporting, CI a browserové medzery. Lokálna
regresia, migrácie, current-head restore, exact-source image, shadow runtime aj
mockovaný a full-stack browser dôkaz sú zelené. Ľudský staging UAT a vzdialený
CI zostávajú externé dôkazy E12.

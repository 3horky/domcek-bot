# Kontrolná brána E11

## Stav: LOKÁLNE SPLNENÁ, ČAKÁ EXTERNÝ CI A E12 UAT

Druhý audit našiel lokálne stop-ship medzery, ktoré predchádzajúca regresia
nepokrývala. Všetky boli opravené pred aktiváciou `live`; po poslednom
prevádzkovom a staging hardeningu sa úplná backendová, frontendová aj browserová
sada zopakovala.

## Kritériá

- [x] Kritické doménové hranice a stavové prechody majú unit testy.
- [x] PostgreSQL, Calendar, Discord adaptéry, OAuth, roly, archivácia a recovery majú integračné testy.
- [x] Bezpečnostná matica pokrýva CSRF, OAuth state, session/logout, RBAC, mentions, URL/SSRF a posledného Admina.
- [x] Dva súčasné workery nevytvoria dvojité odoslanie ani chybu celého pollu.
- [x] Každý proces sa samostatne reštartuje a DB výpadok má správny degraded/recovery stav.
- [x] Bot a worker majú databázový Compose healthcheck, ktorý zlyhá pri stale
  heartbeate, duplicite, nesprávnom stave alebo nesúlade worker režimu.
- [x] Gateway/DNS výpadok s nečíselnou Discord latenciou nezastaví heartbeat;
  runtime po reconnecte znovu dosiahne stav `healthy`.
- [x] PostgreSQL a médiá majú prakticky overenú zálohu a obnovu na predchádzajúcom
  heade `d7a4cb1268ef`; nová migrácia samostatne prešla downgrade/upgrade.
- [x] Praktická backup/restore rehearsal bola zopakovaná aj priamo zo snapshotu
  na aktuálnom heade `e4c28f5619ad`.
- [x] Po auditovaných opravách prebehla nová úplná regresia, migračný cyklus,
  runtime restart a dôkaz nulového driftu.
- [x] Exact-source produkčný backend image bol znovu zostavený po Gateway
  heartbeat oprave a image smoke potvrdil opravu, healthcheck entry point,
  neprivilegovaného používateľa aj zúžený obsah scripts.
- [ ] Pripravený CI workflow prešiel na vzdialenom runneri po schválenom
  commitnutí a pushnutí aktuálneho stromu.
- [x] Všetkých 14 browser acceptance scenárov a doplnkové overflow,
  keyboard/focus a reduced-motion kontroly prešli v desktopovom aj mobilnom
  Chromiu nad deterministicky mockovanou HTTP hranicou.
- [x] Browser tok bol vykonaný aj full-stack proti izolovanému API/PostgreSQL,
  alebo bol ako ekvivalent podpísaný reálny staging UAT.
- [ ] Ľudská mobilná/desktop vizuálna, 200 % zoom a rolová staging UAT bola
  podpísaná podľa E12 checklistu.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Výsledok

**Brána E11: LOKÁLNA ČASŤ SPLNENÁ; EXTERNÉ PODMIENKY ZOSTÁVAJÚ OTVORENÉ.**

Auditované opravy aj automatizovaná browserová vrstva sú implementované. Nový
beh potvrdil 188 backendových testov, 13 Vitest testov, 34 Playwright behov,
statické kontroly, preflight testy, migračný cyklus na head `e4c28f5619ad`,
nulový drift a zdravý shadow runtime s nulou live runov. Praktická obnova
aktuálneho snapshotu prešla na zhodnej Alembic verzii, 20 public tabuľkách a
zhodných počtoch siedmich kontrolovaných oblastí. Exact-source produkčný
Backend image bol po poslednej Gateway heartbeat oprave znovu zostavený
kanonickým Dockerfile a smoke-testovaný; frontend ostáva aktuálny a prešiel
`nginx -t` aj reálnou kontrolou bezpečnostných hlavičiek pre HTML, health a 404
odpoveď.
Samostatný full-stack Playwright tok
prešiel 2/2 na desktope a mobile cez skutočné FastAPI a PostgreSQL vrátane
uloženia, reloadu, nového API čítania a overeného nulového cleanupu. Keďže strom
nie je commitnutý ani pushnutý, vzdialený CI a ľudský staging UAT zostávajú
externé podmienky E12. Produkčný cutover je dovtedy zakázaný.

Záverečný prevádzkový rez navyše prešiel prísnym mypy nad 136 zdrojmi,
pozitívnym aj negatívnym runtime healthcheck smoke. Aktuálny lokálny Compose
hlási presne jeden bot aj worker ako `healthy`; worker zostáva v `shadow`.

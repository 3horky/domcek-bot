# Technická architektúra Carla

## 1. Tvar systému

Carlo je modulárny monolit s jedným Python balíkom a troma samostatnými
procesmi nad spoločnou PostgreSQL databázou:

- **API** – FastAPI, Discord OAuth2, relácie, CSRF, RBAC a verzované JSON API,
- **bot** – Discord Gateway, slash príkazy, persistentné interakcie, reakcie a
  prenos externých účinkov do aplikačných služieb,
- **worker** – Calendar synchronizácia, scheduler, shadow capture, publikovanie
  a recovery,
- **frontend** – React/TypeScript SPA so shadcn/Base UI komponentmi,
- **PostgreSQL** – jediný autoritatívny stav a koordinačná vrstva.

Procesy nezdieľajú pamäť. Všetky rozhodnutia, idempotencia, lease-y, zámky a
recovery body, ktoré musia prežiť reštart, sú v databáze.

## 2. Vrstvy backendu

Balík `v2/backend/src/domcek_bot` je rozdelený na:

- `domain` – hodnotové objekty, enumy, časové a publikačné pravidlá bez I/O,
- `application` – use cases, porty, autorizácia, transakčné hranice a audit,
- `infrastructure` – SQLAlchemy/PostgreSQL, Google Calendar, Discord, médiá a
  generátor úvodu,
- `api`, `bot`, `worker` – vstupné adaptéry a composition roots.

Web, Discord príkazy a scheduler nesmú implementovať vlastnú kópiu doménového
rozhodnutia. Volajú spoločné aplikačné služby.

## 3. Hlavné dátové toky

### 3.1 Calendar synchronizácia

1. Worker načíta aktívne `calendar_source` pre guild.
2. Google adaptér používa výhradne `calendar.readonly`, stránkovanie a
   ohraničený retry.
3. Full alebo incremental sync normalizuje výskyty do `external_event`.
4. Udalosti sa párujú stabilnou occurrence/series identitou; redakčné override
   ostávajú oddelené a synchronizácia ich neprepisuje.
5. Cursor sa uloží až v rovnakej úspešnej transakcii ako udalosti.
6. Pred due snapshotom scheduler vždy vynúti finálny sync všetkých aktívnych
   zdrojov. Zlyhanie defaultne blokuje publikovanie.

### 3.2 Draft a redakcia

`PublicationDraftService` v jednej konzistentnej DB transakcii načíta
konfiguráciu, kalendárové výskyty, instance/series override, manuálne udalosti a
platné INFO. Čistý composer potom:

- vypočíta polootvorené 14-dňové okno v nakonfigurovanom pásme,
- aplikuje `stop carlo`, force include/exclude a popisovú prioritu,
- stabilne zoradí timed, all-day, viacdňové, manuálne a INFO položky,
- vytvorí slovenské formátovanie, day emoji a mesačné farby,
- rozdelí výsledok podľa Discord limitov,
- vloží `@everyone` práve raz a označí jedinú finálnu správu pre seen.

Composer je bez externých účinkov a má kanonickú JSON serializáciu/hash. Webový
náhľad, manuálne potvrdenie, shadow capture a publisher používajú ten istý
draft.

### 3.3 Publikovanie

1. Scheduler alebo manuálny use case získa zámok pre `(guild, scheduled_for)`.
2. Pred Discord volaním sa uloží nemenný `publication_run`, položky a presný
   `publication_message` plán vrátane úvodu a allowed mentions.
3. Správy sa posielajú sekvenčne a každé potvrdené Discord ID sa hneď uloží.
4. Transient chyba môže použiť ohraničený retry. Neistý externý účinok sa
   automaticky neopakuje.
5. Seen sa pridá iba finálnej úspešnej správe; jeho chyba je warning.
6. Úspešný manuálny run vybaví rovnaký slot. Neúspešný slot nepreskočí.

Krátko platný HMAC token ručného potvrdenia je viazaný na guild, používateľa,
slot a hash presného náhľadu. Potvrdenie pri zmenenom drafte zlyhá namiesto
odoslania iného obsahu.

### 3.4 Recovery

Worker pri štarte obnovuje bezpečne opakovateľné publikačné runy. Pri neistom
Discord účinku vytvorí `publication_incident` a čaká na Admin reconcile:
prepojenie existujúceho message ID alebo potvrdenie, že správa nevznikla.

Archivácia používa stavový tok `pending → approved → archiving → archived` s
`rejected`, `failed` a expiráciou. Recovery porovná reálny Discord názov a
kategóriu; už aplikovaný účinok iba potvrdí, inak vykoná idempotentný krok.

## 4. Dáta a konzistencia

Aktuálna schéma má 19 aplikačných tabuliek plus `alembic_version`. Dátový model
je podrobne popísaný v `docs/e2/DATOVY_MODEL.md`. Kľúčové mechanizmy:

- unikátny slot publikácie pre guild,
- optimistické verzie redakčných a konfiguračných záznamov,
- PostgreSQL row/advisory locks pre scheduler, sync, archiváciu a posledného
  Admina,
- nemenný publikačný snapshot,
- stabilné migračné a integračné idempotency keys,
- guild-scoped repository dotazy a audit.

## 5. Bezpečnosť

- Discord OAuth2 state, serverová relácia, HttpOnly/Secure/SameSite cookies,
  rotácia session a CSRF pri každej mutácii,
- povolený CORS origin a necachovanie citlivých odpovedí,
- capability RBAC v každom use case a čerstvé Discord role pri citlivých
  operáciách,
- guild ID a actor sa nikdy nepreberajú ako dôveryhodné autorizačné údaje z
  klienta,
- live validácia Discord objektu, guild a typu pred uložením alebo účinkom,
- kontrola role hierarchy, `manage_roles` a serializovaná ochrana posledného
  Admina,
- neutralizácia nechcených zmienok a explicitné `allowed_mentions`,
- INFO upload validuje typ, rozmery, dekódovaný raster a bezpečne reenkóduje na
  WebP,
- secrets sú iba v serverových mountoch/env; problem responses ani audit ich
  neobsahujú.

## 6. Pozorovateľnosť

API poskytuje minimálne liveness/readiness. Autorizovaný operations summary
agreguje:

- čerstvosť bota a workera vrátane `paused|shadow|live`,
- stav všetkých Calendar zdrojov,
- najbližší slot,
- úspešné, neúspešné, rozpracované a preskočené publikácie,
- posledné integračné úlohy a bezpečné error codes.

Bot a worker zapisujú perzistentné heartbeat-y. Moderátorské alerty obsahujú
korelačné ID a odkaz do webu, nie traceback alebo obsah tajomstiev.

## 7. Nasadenie a záloha

Lokálny vývoj používa `v2/compose.yaml`; produkčný model
`v2/compose.production.yaml`, Caddy HTTPS a nemenné backend/frontend image
digesty. `PUBLICATION_EXECUTION_MODE` má fail-safe default `paused`; staging
používa `shadow` a `live` sa povoľuje až explicitným cutover krokom.

Záloha obsahuje PostgreSQL custom dump, INFO médiá a SHA-256 manifest.
Produkčný wrapper podporuje explicitný Compose/env súbor, lokálnu retenciu,
denný systemd timer a povinný šifrovaný off-site prenos. Restore skript odmietne
prepísať existujúcu databázu.

## 8. Migrácie a vydanie

Alembic head je `e4c28f5619ad`. Legacy SQLite migrátor má dry-run, strojový aj
ľudský report, stabilné kľúče, konzervatívne párovanie a explicitné potvrdenie
cieľa. Produkčný cutover je samostatný autorizovaný proces; zostavenie image ani
príprava runbooku ho neaktivuje.

## 9. Testovacia stratégia

Automatizovaná sada pokrýva doménu, PostgreSQL, Calendar, OAuth/RBAC/API,
Discord adaptéry, recovery, migráciu a React pracovné toky. Aktuálny lokálny
dôkaz je 154 úspešných backendových testov, jeden opt-in live Google skip a 12
frontendových testov so statickými kontrolami a buildom. Browserový rolový,
responzívny a accessibility UAT a vzdialený CI sú explicitné otvorené E12
dôkazy, nie predstierané automatizované pokrytie.

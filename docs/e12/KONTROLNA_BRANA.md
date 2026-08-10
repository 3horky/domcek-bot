# Kontrolná brána E12

## Stav: OTVORENÁ

Technická staging a shadow implementácia je funkčná a fail-safe. Používateľ
11. augusta 2026 výslovne prijal riadený rehearsal dôkaz ako ekvivalent dvoch
odlišných shadow slotov. Brána zostáva otvorená pre HTTPS staging, vzdialený CI
a podpísaný browser UAT oprávnených rolí.

## Splnené

- [x] samostatná staging Discord aplikácia, guild, role, kanály a emoji,
- [x] samostatný read-only Google service account a dva testovacie kalendáre,
- [x] samostatná PostgreSQL databáza v lokálnom staging Compose,
- [x] explicitný režim `paused|shadow|live` s fail-safe defaultom `paused`,
- [x] staging worker v `shadow`, bez schedulera, recovery a Discord odoslania,
- [x] samostatná história shadow draftov, ktorá nekoliduje so živými runmi,
- [x] opakované pozorovanie jedného reálneho slotu s kanonickým hashom,
- [x] dva odlišné read-only rehearsal sloty nad synchronizovanými fixtures,
- [x] používateľ prijal oba rehearsal sloty ako E12 ekvivalent dvoch odlišných
  týždenných shadow cyklov; čerstvé opakovanie zachovalo oba hashe,
- [x] zachovanie redakčnej úpravy tej istej udalosti v oboch draftoch,
- [x] recurrence, `stop carlo`, Google description policy, viac kalendárov,
  viacdňové udalosti, hranice okna a delenie správ,
- [x] nulový počet živých `publication_run` počas shadow/rehearsal overenia,
- [x] finálny Calendar sync pred due snapshotom a bezpečný default blokujúci
  implicitné použitie stale cache,
- [x] čerstvé heartbeat-y bota/workera, worker v režime `shadow` a nulový počet
  otvorených publikačných incidentov po finálnom rebuilde,
- [x] úplná regresia: 188 backendových testov, 1 korektne preskočený opt-in
  Google live test, 13 Vitest testov, 34 mockovaných a 2 full-stack Playwright
  behov, statické kontroly a produkčný Vite build,
- [x] UAT checklist pre Admin, Team Mod, SDB/FMA, mobil a accessibility.
- [x] AC-01–AC-33 majú explicitnú mapu na automatizovaný, staging alebo UAT
  dôkaz v `AKCEPTACNE_KRITERIA.md`; AC-21 zostáva otvorené pre ľudský podpis.

## Otvorené – stop-ship pre E13 cutover

- [ ] staging web cez produkčne podobný reverse proxy a HTTPS doménu,
- [ ] schválený commit/push nového stromu a zelený vzdialený CI beh bez výnimiek,
- [ ] Admin podpísal všetky relevantné body `UAT_CHECKLIST.md`,
- [ ] Team Mod podpísal svoju oprávnenostnú a obsahovú časť,
- [ ] SDB/FMA podpísal preview a dvojkrokový publish do staging kanála,
- [ ] desktop, tablet, mobil, 200 % zoom a klávesnicová accessibility kontrola,
- [ ] všetky akceptačné kritériá zadania majú test, staging dôkaz alebo UAT podpis.

Kým je táto brána otvorená, `PUBLICATION_EXECUTION_MODE=live` sa nesmie zapnúť
a produkčný cutover sa nesmie vykonať.

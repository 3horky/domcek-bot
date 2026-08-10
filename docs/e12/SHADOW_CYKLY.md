# E12 – evidencia tieňových cyklov

## Aktuálny reálny shadow slot

| Slot | Stav | Pozorovania | Obsah | Discord účinok |
|---|---|---:|---:|---|
| 10. 8. 2026 20:00 Europe/Bratislava | rozpracovaný | najmenej 6 | 2 položky / 1 správa | žiadny; `publication_run = 0` |

Prvé pozorovanie vzniklo pred pripojením Calendar zdrojov. Následne boli cez
auditovanú SettingsService pridané oba E0 testovacie kalendáre a worker vykonal
read-only full sync 17 + 1 výskytov. Synchronizované fixtures začínajú
25. októbra 2026, preto sa augustový 14-dňový draft správne nezmenil a jeho
SHA-256 zostal `c6d0aa4d0eb1bb46981a3b82d757de6de1b430c7863a97db30542ce8495c63ec`.

## Brána dvoch cyklov

- [ ] prvý odlišný týždenný slot zachytený a porovnaný,
- [ ] druhý odlišný týždenný slot zachytený a porovnaný,
- [x] používateľ 11. augusta 2026 výslovne prijal dva nižšie uvedené read-only
  rehearsal sloty ako ekvivalent dvoch odlišných týždenných shadow cyklov,
- [x] rovnaká udalosť v prekryve zachovala redakčnú úpravu v rehearsal,
- [x] `stop carlo`, recurrence a Google description policy overené v rehearsal,
- [x] ani jeden shadow capture nevytvoril živý `publication_run`,
- [x] worker je explicitne v režime `shadow`.

Najmenej šesť pozorovaní rovnakého slotu nie je nepravdivo započítaných ako dva
publikačné cykly. Alternatívna brána je splnená výslovným používateľským
prijatím októbrového a novembrového rehearsal dôkazu; dva nezačiarknuté body
vyššie pravdivo ukazujú, že nejde o dva reálne kalendárne behy workera.

## Read-only rehearsal dvoch odlišných slotov

Nástroj `scripts/rehearse_shadow_cycles.py` zostavil nad synchronizovaným
staging snapshotom dva odlišné termíny bez zápisu do shadow/live tabuliek a bez
Discord volania:

| Referenčný čas | Publikačný slot | Verejný obsah | Správy | SHA-256 |
|---|---|---:|---:|---|
| 25. 10. 2026 18:00 UTC | 26. 10. 2026 20:00 Europe/Bratislava | 11 položiek | 2 | `5ec6b91fd7e50dff314e6f5db0b192c445f830fcc5cfd5531b5a53888a2ca7b4` |
| 1. 11. 2026 18:00 UTC | 2. 11. 2026 20:00 Europe/Bratislava | 6 položiek | 1 | `493c809f17d49feaaa98ed557ec25468ec365420f4ae6f472ae4a8b41a8f7eee` |

Rehearsal potvrdila:

- stabilné zoradenie udalostí z dvoch kalendárov podľa času a priority,
- timed, celodenné aj viacdňové zobrazenie vrátane prekryvu okna,
- presunutý recurring výskyt v oboch prekrývajúcich sa draftoch,
- vyradenie `stop carlo` udalosti z verejného obsahu pri zachovaní v editore,
- predvolenú politiku bez automatického publikovania Google popisu,
- deterministické delenie 11 položiek na dve Discord správy,
- bezpečné upozornenie pri udalosti bez názvu.

Auditovaný staging krok uložil konkrétnemu presunutému recurring výskytu
`3b885715-27e7-4d02-8e8a-a71b82dbb573` redakčný popis:

> E12: tento redakčný popis musí zostať v oboch prekrývajúcich sa týždenných
> draftoch.

Opakovaný read-only rehearsal vrátil presne tento popis v slote 26. októbra aj
2. novembra. Dôkaz potvrdzuje produktové pravidlo, že úprava konkrétneho
výskytu sa zachová pri jeho druhom oznámení. Zmena bola vykonaná cez rovnakú
aplikačnú službu, autorizáciu, optimistickú verziu a audit ako webový editor;
nevznikol pritom žiadny živý publikačný run ani Discord správa.

## Akceptačné rozhodnutie

Dňa 11. augusta 2026 používateľ v projektovej konverzácii výslovne uviedol:
„prijímam rehearsal ako E12 dôkaz“. Bezprostredne potom bol read-only nástroj
znovu spustený nad aktuálnym stromom a lokálnou staging databázou. Vrátil oba
pôvodné SHA-256 hashe, 11/6 verejných položiek, 2/1 správ a rovnaký redakčný
popis prekryvnej udalosti. Následná DB kontrola potvrdila
`publication_run = 0`, worker `running` v režime `shadow` a bot `connected`.

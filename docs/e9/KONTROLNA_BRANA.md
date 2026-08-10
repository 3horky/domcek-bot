# Kontrolná brána E9

## Kritériá

- [x] Admin vie bezpečne čítať a verzovane meniť publikačný rozvrh, cieľové Discord objekty a obsahové predvoľby.
- [x] Admin vie pridať, upraviť, aktivovať a synchronizovať jeden alebo viac Google kalendárov vrátane priority a sync stavu.
- [x] Webová a Discord tvorba či archivácia kanála používajú rovnakú aplikačnú službu a rovnaké auditné akcie.
- [x] Kanálový formulár podporuje emoji, zodpovednú osobu, ďalších členov, roly a náhľad výsledného prístupu.
- [x] Archivácia používa explicitné potvrdenie a upozorňuje na synchronizáciu oprávnení s archívnou kategóriou.
- [x] Správa Team Mod a Admin rolí overuje `Manage Roles`, hierarchy, opätovne načíta stav a chráni posledného Admina.
- [x] Seen, auto-reaction a mention-reaction sú oddelené, podporujú Unicode aj dostupné serverové emoji a test v zvolenom kanáli.
- [x] Uložená reakčná konfigurácia skutočne riadi publisher aj Discord Gateway runtime.
- [x] Ručné publikovanie vo webe používa dvojkrokový E7 tok a kanonický Discord náhľad.
- [x] Team Mod vidí iba kanálové pracovisko; Admin celý priestor a neoprávnený používateľ API neobíde.
- [x] Statické, integračné, migračné a frontendové kontroly prešli.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Výsledok

**Brána E9: SPLNENÁ.**

Backend prešiel Ruff formátovaním a lintom, prísnym mypy nad 72 zdrojovými
súbormi, 135 testami s jedným zámerným opt-in Google Calendar skipom a
downgrade/upgrade/`alembic check` cyklom revízie `c82175ef7904`. Frontend po
doplnení kanonického náhľadu ručného publish potvrdenia prešiel TypeScript
kontrolou, ESLintom, 11 Vitest testami a produkčným buildom.

Živý read-only Discord smoke test načítal staging adresár štyroch textových
kanálov, štyroch kategórií, šiestich rolí a dvoch emoji. V tejto relácii nebol
dostupný pripojený browser, preto dokument nepredstiera screenshotovú vizuálnu
QA; tá patrí do E11/UAT. Doménová zhoda webu a Discordu je vynútená spoločnými
službami `ChannelManagementService` a `ManualPublicationService`, nie iba
porovnaním dvoch nezávislých implementácií.

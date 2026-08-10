# Kontrolná brána E7

## Kritériá

- [x] Úvod má verzovaný generátor, sanitizáciu a deterministický slovenský fallback.
- [x] Snapshot runu, položiek a plánov správ vznikne pred prvým Discord volaním.
- [x] Viacdielne publikovanie je sekvenčné, idempotentné a odolné voči rate limitu.
- [x] Pád medzi správami pokračuje od prvej nepotvrdenej správy bez duplikácie.
- [x] Neistý externý účinok vytvorí incident a vyžaduje reconcile.
- [x] Seen emoji sa pridá až na poslednú správu a jeho chyba je iba warning.
- [x] Scheduler rešpektuje lock, grace period a povinný finálny Calendar sync
  tesne pred snapshotom; núdzová cache vyžaduje explicitný Admin opt-in.
- [x] Ručný trigger má dvojkrokové potvrdenie viazané na používateľa, expiráciu
  a hash presného zobrazeného draftu vrátane generovaného úvodu.
- [x] Admin aj SDB / FMA používajú rovnaký publish use case; Team Mod publikovať nemôže.
- [x] Úspešný manuálny run spôsobí preskočenie práve príslušného automatického termínu.
- [x] Moderátorské incidenty neobsahujú tajný traceback a nesú korelačné ID.
- [x] Unit, integračné, migračné a locked-runtime scenáre E7 prešli.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Aktuálny výsledok

**Brána E7: SPLNENÁ.**

Snapshot, sekvenčný publisher, bezpečné retry/reconcile, scheduler, ručný
dvojkrokový trigger aj recovery sú implementované a pokryté úplnou regresiou.
E11 navyše overil skutočný súbeh dvoch scheduler inštancií: vznikol jeden run a
jedno externé odoslanie; druhý worker dostal bezpečný stav
`publication_in_progress`. Reálny dvojcyklový shadow/UAT dôkaz patrí podľa plánu
do E12 a nie je spätne vydávaný za E7 automatizovaný test.

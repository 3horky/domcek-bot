# Kontrolná brána E8

## Kritériá

- [x] Guild-scoped príkazy sa registrujú riadeným staging krokom.
- [x] Náhľad je dostupný Team Mod, SDB/FMA a Adminovi a nikdy nevytvorí everyone ping.
- [x] Ručné publikovanie má používateľsky viazané, expirované dvojkrokové potvrdenie.
- [x] Súbežný publish trigger nevytvorí druhý run ani duplicitné správy.
- [x] Vytvorenie kanála používa emoji, UserSelect/RoleSelect, zodpovednú osobu, preview a spoločný use case.
- [x] Archivácia má persistentné rozhodnutie, jednorazový DB prechod a opätovnú Admin autorizáciu; Admin používa osobitné päťminútové priame potvrdenie.
- [x] Cudzí alebo expirovaný klik nevykoná operáciu.
- [x] Zachované všeobecné interakcie sú samostatne konfigurovateľné a bezpečne logované.
- [x] Unit, integračné a staging testy prejdú.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Aktuálny výsledok

**Brána E8: SPLNENÁ.**

Staging bot úspešne synchronizoval štyri guild-scoped príkazy a pripojil sa ku
Gateway. Aplikačné a integračné testy pokrývajú používateľsky viazaný a
expirovaný publish token, súbežný termín, idempotentné vytvorenie kanála,
Admin-only compare-and-set archivačné rozhodnutie a opakovaný klik. Preview
explicitne používa nulové allowed mentions. Dlhšie operácie odkladajú ephemeral
odpoveď, aby neprepadol Discord interaction deadline. Plná backendová sada pri
uzavretí brány mala 130 úspešných testov a jeden zámerný opt-in live Calendar
skip; statické kontroly a migračný cyklus prešli.

Následný úplný audit zadania doplnil emoji do názvu projektového kanála,
automatický prístup pre zodpovednú osobu a priame Admin potvrdenie archivácie.
Zrušené alebo expirované priame potvrdenie žiadosť bezpečne uzavrie. Regresná
sada po doplnení má 135 úspešných testov a jeden zámerný opt-in Calendar skip.

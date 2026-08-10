# Etapa E9 – webová správa Discordu a nastavení

E9 zjednocuje publikačný rozvrh, Google kalendáre, kanály, roly a reakcie v
jednom responzívnom pracovisku `/nastavenia`. Web neimplementuje druhú kópiu
doménových pravidiel: tvorba a archivácia kanála používajú tie isté aplikačné
služby ako Discord príkazy, publikovanie ten istý E7 use case a runtime reakcie
čítajú tú istú uloženú konfiguráciu.

Admin môže meniť celý priestor. Team Mod vidí iba kanálové operácie. Snowflake
ID sa cez JSON prenášajú ako text, každá mutácia vyžaduje reláciu, CSRF a čerstvé
rolové rozhodnutie a citlivé zmeny majú audit aj používateľské potvrdenie.

## Kontrolná brána

Výsledok a dôkazy sú v [KONTROLNA_BRANA.md](./KONTROLNA_BRANA.md).

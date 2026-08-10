# Etapa E8 – Discord príkazy a interakcie

Discord je v E8 tenká interakčná vrstva nad rovnakými aplikačnými use cases,
ktoré používa web a worker. Handler nikdy nerozhoduje iba podľa viditeľnosti
príkazu; pri každom použití znovu načíta konfiguráciu a overí aktuálne roly.

Vývojové príkazy sa synchronizujú iba do izolovaného staging guild. Globálna
produkčná synchronizácia bude samostatný deployment krok.

## Kontrolná brána

Aktuálny stav a dôkazy sú v [KONTROLNA_BRANA.md](./KONTROLNA_BRANA.md).

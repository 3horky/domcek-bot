# Etapa E3 – integrácia Google Kalendára

E3 pripája read-only Google Calendar zdroj k stabilnej E2 doméne. Integrácia je rozdelená na provider-neutrálny aplikačný port, Google HTTP/OAuth adaptér, normalizáciu udalostí a transakčnú synchronizačnú službu.

## Dokumenty

- [Synchronizačné invarianty](./SYNCHRONIZACNE_INVARIANTY.md)
- [Kontrolná brána E3](./KONTROLNA_BRANA.md)

## Hranica etapy

E3 načítava a lokálne synchronizuje udalosti. Nezostavuje publikačný balík, nepublikuje do Discordu a nepridáva nechránený verejný endpoint. Aplikačná operácia na overenie pripojenia bude pripravená pre autorizované API v E5.

## Live overenie

Live test je zámerne opt-in, je voči Google Kalendáru iba read-only a zapisuje iba
do lokálnej testovacej databázy. Spúšťa sa s
`RUN_LIVE_GOOGLE_CALENDAR_TESTS=1`; calendar ID a credential cesta sa preberajú
z lokálneho prostredia a do testovacieho výstupu sa nevypisujú.

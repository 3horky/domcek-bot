# ADR-0006: Frontendová architektúra

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Webová administrácia obsahuje bohatý editor, optimistické konflikty, Discord preview, responzívne zoznamy, nastavenia, históriu a roly. Server-renderované formuláre bez klientského stavu by tento rozsah komplikovali, no frontend nesmie duplikovať doménové pravidlá.

## Rozhodnutie

Frontend bude samostatná React + TypeScript aplikácia buildovaná moderným build nástrojom typu Vite.

Pravidlá:

- API kontrakty budú typované a verzované.
- Server zostáva autoritatívny pre validáciu, oprávnenia, composer a Discord limity.
- Frontend môže poskytovať okamžitú pomocnú validáciu, ale odosiela verziu objektu a spracuje serverový konflikt.
- Discord preview sa vykreslí zo serverom pripraveného preview modelu.
- Dizajn použije tokeny a prístupné UI primitives.
- Každá primárna funkcia bude testovaná na mobile aj desktope.
- Serverové relácie sa používajú cez HttpOnly cookie; frontend neskladuje OAuth ani bot token.
- Loading, empty, stale, conflict, forbidden a error stavy sú prvotriedne obrazovky.

## Základné členenie

- app shell a routing,
- features podľa doménových use cases,
- zdieľané prístupné komponenty,
- samostatná typovaná API vrstva,
- query/cache vrstva,
- E2E testy cez Playwright.

## Dôsledky

Pozitívne:

- kvalitný interaktívny editor,
- silné typovanie používateľských tokov,
- jednoduchšie responzívne komponenty a E2E testy.

Negatívne:

- samostatný frontend build a dependency lifecycle,
- potreba synchronizovať API kontrakty,
- riziko vloženia logiky do frontendu, ktoré sa musí kontrolovať review pravidlami.

## Zamietnuté alternatívy

- Čisté serverové šablóny: menej vhodné pre komplexný editor a konflikty.
- No-code administračný nástroj: nedostatočná kontrola Discord preview, OAuth a domény.
- Dva samostatné preview implementácie: riziko odlišného webového a Discord výsledku.

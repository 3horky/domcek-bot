# ADR-0001: Modulárny monolit a tri procesy

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Nová verzia obsahuje webové API, Discord Gateway klienta, plánované synchronizácie a publikačné úlohy. Tieto časti majú rozdielny životný cyklus, ale používajú rovnaké doménové pravidlá.

Samostatné mikroslužby by pri jednom Discord serveri zvýšili prevádzkovú a integračnú zložitosť. Jeden spoločný proces by naopak spojil HTTP požiadavky, Gateway a dlhšie pracovné úlohy tak, že zlyhanie alebo blokovanie jednej časti môže ovplyvniť ostatné.

## Rozhodnutie

Domček Bot 2.0 bude modulárny monolit v jednom repozitári a jednom backend balíku, spúšťaný ako tri samostatné procesy:

1. `api` – webové API, OAuth a sessions,
2. `bot` – Discord Gateway, príkazy a listenery,
3. `worker` – Calendar sync, scheduler, publikovanie a retry.

Procesy budú používať:

- spoločnú doménovú vrstvu,
- spoločnú aplikačnú vrstvu,
- spoločné rozhrania integračných adaptérov,
- jednu PostgreSQL databázu,
- rovnaký balík konfigurácie a logovania.

Nová verzia bude počas implementácie izolovaná v adresári `v2/`. Legacy súbory zostanú v koreňovom adresári bez presunu až do stabilizácie novej verzie.

## Povinné hranice

- HTTP route nesmie obsahovať publikačné alebo kanálové doménové pravidlá.
- Discord command handler nesmie implementovať paralelnú verziu use case.
- Worker nesmie obchádzať aplikačné služby priamymi SQL zmenami stavov.
- Doménová vrstva nesmie importovať webový framework, `discord.py`, Google SDK ani ORM modely.
- Komunikácia medzi procesmi prebieha cez databázový stav a pracovné záznamy, nie cez nezdokumentované súbory.

## Dôsledky

Pozitívne:

- jedna implementácia pravidiel,
- samostatné reštarty procesov,
- jednoduchšie testovanie,
- jednoduchší deployment než mikroslužby,
- možnosť neskôr oddeliť modul bez prepisu domény.

Negatívne:

- treba dôsledne strážiť modulové hranice,
- viac procesov musí používať kompatibilnú verziu schémy,
- koordinácia workera vyžaduje databázové zámky.

## Zamietnuté alternatívy

- Jeden proces pre web, Gateway aj scheduler: slabšia izolácia zlyhaní.
- Samostatné mikroslužby s vlastnými databázami: neprimeraná zložitosť.
- Priamy overhaul legacy modulov: riziko narušenia produkčného bota počas vývoja.

# Invarianty publication composeru E4

## Čistota a determinizmus

- Výsledok závisí iba od explicitného vstupného snapshotu a verzie composeru.
- Composer nečíta databázu, hodiny procesu, Google ani Discord.
- Rovnaký vstup vytvorí bajtovo rovnakú kanonickú JSON reprezentáciu.
- Poradie nikdy nezávisí od poradia databázového alebo sieťového výsledku.

## Termín a okno

- Najbližší termín sa počíta v nakonfigurovanom IANA pásme; predvolené je
  `Europe/Bratislava`, pondelok 20:00.
- Spracované slot keys sa preskakujú po jednotlivých týždňoch bez zmeny histórie.
- Okno je `[slot, slot + 14 lokálnych kalendárnych dní)` a zdieľa ho
  editor, preview aj publisher.

## Obsah a dedenie

- Instance inclusion rozhodnutie má prednosť pred `stop carlo`; bez instance
  rozhodnutia sa riadiaca veta vyhodnotí pred automatickým zaradením.
- Titulok: instance override → najnovší účinný series override → Google
  titulok → bezpečný slovenský fallback.
- Popis: instance stav → najnovší účinný series stav → očistený Google
  popis iba pri zapnutej globálnej politike → bez popisu.
- `INTENTIONALLY_EMPTY` zastaví dedenie. Vylúčené Calendar udalosti zostanú
  v redakčnom modeli, ale nie vo verejných embedoch.
- Minulé publication snapshoty composer nikdy nemení.

## Triedenie a formátovanie

- INFO položky sú pred eventami; ich poradie je stabilné.
- Eventy sa triedia podľa lokálneho dňa, celodennosti, začiatku, priority
  zdroja, normalizovaného titulku a interného ID.
- Slovenský deň, day emoji a text času vznikajú v jednom backendovom
  formátovači.
- Používateľské Discord zmienky sa neutralizujú bez zmeny uloženého zdroja.

## Discord message plan

- Obsah správy má najviac 2000 znakov, správa najviac 10 embedov a ich
  spoločný text najviac 6000 znakov.
- Embed title má najviac 256, description 4096 a author name 256 znakov.
- Položka prekračujúca vlastný embed limit sa odmietne pred publikovaním;
  nedelí sa spôsobom, ktorý by menil jej význam.
- Riadené `@everyone` je iba v prvej správe a iba táto správa povoľuje
  everyone mention. Posledná správa je jednoznačne označená pre seen reakciu.
- Každá časť má deterministický kľúč a nonce s limitom 25 znakov.

Limity boli pri začatí E4 overené v oficiálnom Discord Message Resource.

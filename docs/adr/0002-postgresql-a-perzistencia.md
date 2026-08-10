# ADR-0002: PostgreSQL a perzistencia

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Legacy bot používa lokálnu SQLite databázu a synchrónne operácie. Nová verzia bude mať súčasne API, bot a worker proces, audit, optimistické zamykanie a stavový model publikácií.

SQLite nie je vhodný ako spoločné produkčné úložisko viacerých procesov s požiadavkou na robustné zámky a recovery.

## Rozhodnutie

Produkčným databázovým systémom bude PostgreSQL.

Backend použije:

- SQLAlchemy s asynchrónnym PostgreSQL driverom,
- Alembic pre všetky zmeny schémy,
- explicitné transakčné hranice v aplikačnej vrstve,
- cudzie kľúče, unikátne obmedzenia a indexy,
- optimistické verzie editovateľných záznamov,
- transakčné alebo advisory locks pre publikačné termíny.

ORM modely sú infraštruktúrny detail. Doménové entity a API kontrakty nebudú priamo ORM objektmi.

SQLite možno použiť iba v izolovaných jednotkových testoch, ktoré nepotrebujú PostgreSQL správanie. Integračné testy zámkov, migrácií a transakcií musia používať PostgreSQL.

## Pravidlá migrácií

- Aplikácia nesmie v produkcii sama vytvárať alebo meniť tabuľky pri štarte.
- Migrácia sa spúšťa ako samostatný deployment krok.
- Proces sa nespustí proti nepodporovanej schéme.
- Deštruktívna zmena používa expand/migrate/contract postup.
- Každá migrácia má upgrade a zdokumentovaný rollback alebo vysvetlenie, prečo návrat vyžaduje obnovu zálohy.

## Dôsledky

Pozitívne:

- spoľahlivé transakcie a súbeh,
- vhodné zámky pre idempotenciu,
- lepšie indexovanie a audit,
- možnosť oddeliť procesy alebo hostiteľov.

Negatívne:

- ďalšia prevádzkovaná služba,
- povinné zálohovanie a migrácie,
- lokálny vývoj potrebuje kontajner alebo lokálny PostgreSQL.

## Zamietnuté alternatívy

- SQLite v produkcii: nedostatočné pre navrhnutý súbeh.
- Dokumentová databáza: slabšia vhodnosť pre transakčné vzťahy a audit.
- Oddelená databáza pre každý proces: zbytočná distribuovaná konzistencia.

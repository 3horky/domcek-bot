# ADR-0004: Google Calendar autentifikácia

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Bot potrebuje iba čítať udalosti z jedného štandardného kalendára, s možnosťou pridať ďalšie kalendáre. Nemá zapisovať do Google Kalendára ani konať v mene bežných používateľov.

## Rozhodnutie

Integrácia použije service account a read-only Google Calendar scope.

Každý zdrojový kalendár sa explicitne zdieľa s e-mailovou adresou service accountu. Domain-wide delegation sa nebude používať, pokiaľ budúci potvrdený prípad použitia nebude vyžadovať prístup naprieč používateľmi organizácie.

Pravidlá:

- service account credential je tajomstvo uložené mimo repozitára,
- web zobrazuje iba stav pripojenia a identitu kalendára, nie credential,
- každý calendar source má samostatný sync token a stav,
- základná implementácia podporuje viac zdrojov aj pri jednom nakonfigurovanom kalendári,
- scope zostane read-only,
- credential sa nebude logovať ani ukladať do auditu,
- test, staging a produkcia použijú oddelené projekty alebo minimálne oddelené service accounts a kalendáre.

## Synchronizačné zásady

- Prvý úspešný beh vykoná full sync.
- Ďalšie behy používajú inkrementálny sync token.
- Neplatný token vyvolá bezpečný nový full sync.
- Token sa uloží až po spracovaní všetkých strán.
- Zrušené udalosti sa spracujú, nie potichu ignorujú.

## Dôsledky

Pozitívne:

- minimálne oprávnenie,
- bez interaktívneho obnovovania súhlasu používateľa,
- jednoduché pridanie druhého explicitne zdieľaného kalendára.

Negatívne:

- vlastník kalendára musí vykonať zdieľanie,
- credential vyžaduje bezpečnú rotáciu,
- testovacie prostredie potrebuje vlastný kalendár.

## Zamietnuté alternatívy

- Používateľský OAuth token: zbytočný refresh lifecycle pre serverovú automatizáciu.
- Plný Calendar scope: širšie oprávnenie než je potrebné.
- Domain-wide delegation: neprimerane silné oprávnenie pre jeden zdieľaný kalendár.

# Etapa E7 – publikačný engine a plánovač

E7 mení kanonický náhľad z E4 na bezpečne publikovateľný, nemenný snapshot.
Obsah sa pred prvým externým účinkom uloží, jednotlivé Discord správy sa
odosielajú sekvenčne a každý potvrdený účinok sa zapisuje samostatne.

## Implementačné invarianty

- jeden guild a termín má najviac jeden `publication_run`,
- snapshot sa po začatí publikovania nemení podľa neskorších redakčných úprav,
- `@everyone` je povolené iba v prvej správe a iba explicitným allowed mention,
- známe Discord message ID sa nikdy neposiela znovu,
- neistý výsledok externého volania sa automaticky neopakuje,
- chyba seen emoji nezmení úspešnú textovú publikáciu na neúspešnú,
- manuálne a automatické publikovanie používajú rovnaký aplikačný use case,
- úspešný manuálny run vybaví iba termín, ktorý používateľ potvrdil.

## Kontrolná brána

Aktuálny stav a dôkazy sa zapisujú do
[KONTROLNA_BRANA.md](./KONTROLNA_BRANA.md).

# Synchronizačné invarianty E3

## Prístup a hranice

- Google credential používa iba scope `https://www.googleapis.com/auth/calendar.readonly`.
- Service account pristupuje iba ku kalendárom, ktoré mu boli explicitne zdieľané; domain-wide delegation sa nepoužíva.
- Credential zostáva v serverovom read-only secret mount a jeho obsah, access token ani sync token sa nelogujú.
- Aplikačná vrstva pozná iba `CalendarClient` port a provider-neutrálne dátové kontrakty.

## Full sync

- Dotaz používa `singleEvents=true` a `showDeleted=true`, aby dostal expandované výskyty aj zrušenia.
- Bezpečný horizont je konfigurovateľný a zahŕňa aj nedávnu minulosť pre viacdňové a presunuté udalosti.
- Všetky strany sa načítajú pred databázovou aplikáciou. `nextSyncToken` sa prijme iba z poslednej strany.
- Chýbajúce lokálne udalosti sa označia ako odstránené až v rovnakej transakcii ako úspešné uloženie všetkých prijatých udalostí a nového tokenu.
- Zlyhaný alebo neúplný full sync nemení platný predchádzajúci token ani nemaže udalosti.

## Incremental sync

- Inkrementálny dotaz používa posledný uložený token a rovnaké kompatibilné parametre na každej strane.
- Odtlačok parametrov je uložený spolu s tokenom. Pri zmene parametrov sa vykoná full sync.
- `410 Gone` nespôsobí fyzické vymazanie lokálneho obsahu; služba bezpečne zopakuje operáciu ako full sync a až po jeho úspechu označí chýbajúce záznamy.
- Inkrementálny sync upraví iba prijaté udalosti a zrušenia. Neprijaté záznamy nemení.

## Identita a opakovanie

- Google `event.id` je stabilná provider identita konkrétneho expandovaného výskytu a tvorí základ `EventSourceKey` spolu s providerom a calendar ID.
- `recurringEventId` sa mapuje na stabilný `RecurringSeriesKey`.
- `originalStartTime` sa uchováva ako kanonický kľúč výskytu aj pri jeho presunutí.
- Synchronizácia aktualizuje existujúci `external_event` na mieste a nemení jeho interné UUID, preto zostanú zachované `event_override` a historické referencie.
- Ak sa pri existujúcom redakčnom override zmení `series_key` rovnakého provider výskytu, nové zdrojové dáta a interné UUID sa zachovajú, ale vznikne explicitné moderátorské upozornenie na kontrolu nejednoznačnej identity.
- Neznáme zrušenie bez bezpečne normalizovateľného času sa neukladá ako nová udalosť; existujúci záznam s rovnakým provider event ID sa označí ako zrušený.

## Čas a obsah

- Časované hodnoty sa validujú ako offset-aware RFC3339 a ukladajú sa ako okamihy.
- Celodenné hodnoty sa ukladajú ako lokálne dátumy s exkluzívnym koncom.
- Raw Google popis sa zachová pre editor.
- Samostatná, case-insensitive riadiaca veta `stop carlo` sa deteguje ako vlastný riadok alebo posledná veta za interpunkciou, vrátane Google HTML wrapperov, a odstraňuje iba z kandidáta verejného textu; výskyt vnútri bežnej vety sa nepovažuje za príkaz, okolné HTML formátovanie sa zachová a raw zdrojový popis sa nemení.

## Chyby, retry a čerstvosť

- Dočasné sieťové chyby a HTTP `429`, `500`, `502`, `503`, `504` používajú ohraničený exponenciálny retry.
- Autentifikačné a prístupové chyby sa neopakujú bezhlavo a neodhaľujú odpoveď ani credential.
- Stav zdroja rozlišuje pokus, úspech a poslednú bezpečnú chybu.
- Čerstvosť lokálnej kópie rozlišuje `fresh`, `stale_warning` a `unsafe`; nikdy nesmie odvodiť bezpečnosť iba z času procesu.

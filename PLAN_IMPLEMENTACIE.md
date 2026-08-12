# Plán kompletnej implementácie Carla (Domček Bot 2.0)

## 1. Účel plánu

Tento dokument rozkladá požiadavky zo súboru [ZADANIE.md](./ZADANIE.md) na realizovateľné implementačné etapy, pracovné balíky, závislosti, kontrolné body a akceptačné výstupy.

Plán je zostavený pre vývoj novej verzie vedľa pôvodného bota. Pôvodný bot zostane počas vývoja nedotknutý a prevádzkyschopný až do riadeného produkčného prechodu.

Hlavným cieľom nie je iba dodať jednotlivé obrazovky a príkazy, ale vybudovať jeden konzistentný systém, v ktorom:

- Google Kalendár je spoľahlivým zdrojom udalostí,
- redakčné úpravy sa nestrácajú,
- web, Discord príkazy a plánovač používajú rovnaké pravidlá,
- publikovanie je auditovateľné a odolné proti duplicitám,
- každá citlivá operácia je autorizovaná na serveri,
- nová verzia môže byť bezpečne otestovaná a nasadená bez dvojitého publikovania.

---

# 2. Stratégia dodávky

## 2.1 Základný princíp

Implementácia bude prebiehať po vertikálnych a overiteľných etapách. Každá etapa musí skončiť funkčným výstupom, testami a splnenou kontrolnou bránou. Kritické doménové pravidlá sa implementujú pred finálnym používateľským rozhraním.

Vývoj sa nebude robiť priamym prepisovaním existujúcich modulov. Nová verzia dostane samostatnú štruktúru, vlastnú databázovú schému a vlastné spúšťacie body. Staré a nové riešenie sa spoja iba kontrolovaným migračným nástrojom.

## 2.2 Poradie priorít

Pri konfliktoch sa použije toto poradie:

1. bezpečnosť a správnosť oprávnení,
2. zabránenie duplicitnému alebo nesprávnemu publikovaniu,
3. správnosť udalostí, dátumov a časových pásiem,
4. zachovanie redakčných úprav a histórie,
5. použiteľnosť administrácie,
6. vizuálne zdokonalenie,
7. doplnkové pohodlie a optimalizácie.

## 2.3 Priebežné pravidlá kvality

Počas všetkých etáp platí:

- po každej materiálnej zmene aktualizovať [`STATUS.md`](./STATUS.md) podľa nemenného pravidla v zadaní,
- každá zmena databázovej schémy vznikne ako verzovaná migrácia,
- každé nové doménové pravidlo dostane automatizovaný test,
- externé integrácie budú za adaptérmi a v testoch nahraditeľné,
- citlivé operácie budú auditované od prvého momentu, keď ich možno vykonať,
- webové API nebude dôverovať oprávneniam vypočítaným iba vo frontende,
- žiadny proces nebude používať implicitné lokálne časové pásmo,
- žiadna fáza nebude považovaná za hotovú iba preto, že funguje pri ideálnom scenári.

---

# 3. Cieľová architektúra

## 3.1 Architektonický model

Odporúčaný je modulárny monolit v jednom repozitári, nasadzovaný ako tri samostatné procesy nad spoločnou PostgreSQL databázou:

```text
                    ┌────────────────────┐
                    │ Webový prehliadač │
                    └─────────┬──────────┘
                              │ HTTPS
                    ┌─────────▼──────────┐
                    │ Web API + OAuth    │
                    └─────────┬──────────┘
                              │
┌─────────────────┐   ┌───────▼────────┐   ┌──────────────────┐
│ Discord Gateway │◄─►│ Aplikačné a    │◄─►│ PostgreSQL       │
│ a príkazy       │   │ doménové služby│   │ + audit/história│
└─────────────────┘   └───────▲────────┘   └──────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │ Worker/plánovač   │
                    └──────┬───────┬────┘
                           │       │
                  ┌────────▼─┐   ┌─▼────────────────┐
                  │ Google   │   │ Discord REST +  │
                  │ Calendar │   │ generovanie úvodu│
                  └──────────┘   └──────────────────┘
```

Procesy:

- **API proces** obsluhuje webovú administráciu, OAuth a autorizované operácie.
- **Bot proces** udržiava Discord Gateway spojenie, reaguje na príkazy a správy.
- **Worker proces** synchronizuje kalendáre, pripravuje termíny, vykonáva publikovanie a opakované pokusy.

Všetky tri procesy importujú rovnaké aplikačné služby. Neexistuje samostatná „webová“ a „Discord“ verzia publikačnej alebo kanálovej logiky.

## 3.2 Navrhovaný technologický základ

| Oblasť            | Navrhované riešenie                                         | Dôvod                                                             |
| ----------------- | ----------------------------------------------------------- | ----------------------------------------------------------------- |
| Backend           | Python, asynchrónny webový framework typu FastAPI           | Nadväzuje na existujúci Python ekosystém a poskytuje typované API |
| Discord           | `discord.py`                                                | Zachováva overený model pôvodného bota                            |
| Databáza          | PostgreSQL                                                  | Transakcie, zámky, súbeh procesov, spoľahlivé migrácie            |
| Databázová vrstva | SQLAlchemy s asynchrónnym driverom                          | Oddelenie domény od SQL a testovateľné repozitáre                 |
| Migrácie          | Alembic                                                     | Verzionovanie schémy a kontrolovaný rollout                       |
| Frontend          | React + TypeScript                                          | Vhodné pre bohatý editor, živý náhľad a responzívnu administráciu |
| Build frontendu   | Vite alebo ekvivalent                                       | Rýchly lokálny vývoj a jednoduchý produkčný build                 |
| Formuláre         | Typovaný formulárový a validačný model                      | Konzistentné chyby a kontrola súbehu                              |
| Frontend API stav | Query/cache vrstva s invalidáciou                           | Synchronizácia editora, refetch a chybové stavy                   |
| Backend testy     | pytest                                                      | Jednotkové a integračné testy                                     |
| Web E2E testy     | Playwright                                                  | Reálne používateľské scenáre a responzívne testy                  |
| Lokálny vývoj     | Docker Compose                                              | Opakovateľný PostgreSQL a procesy bez ručného nastavovania        |
| Produkcia         | Kontajnerizované procesy alebo ekvivalentný process manager | Oddelené reštarty, health checks a logy                           |

Konkrétne podporované verzie sa uzamknú pri vytvorení projektu a budú sa aktualizovať kontrolovane. Plán zámerne neviaže produkt na konkrétne číslo verzie ešte pred založením novej aplikačnej kostry.

## 3.3 Navrhovaná štruktúra repozitára

```text
backend/
  app/
    domain/             # entity, hodnotové objekty, čisté pravidlá
    application/        # prípady použitia a transakčné služby
    repositories/       # rozhrania úložísk
    integrations/
      discord/
      google_calendar/
      intro_generator/
    infrastructure/     # DB, konfigurácia, logovanie, health checks
    api/                # HTTP endpointy, OAuth, sessions
    bot/                # Discord príkazy, listenery a komponenty
    worker/             # plánovač, sync a publikačné úlohy
  migrations/
  tests/
frontend/
  src/
    app/
    pages/
    features/
    components/
    api/
    styles/
  tests/
scripts/
  migration/
  operations/
docs/
legacy/                 # iba ak sa pôvodný kód neskôr fyzicky presunie
```

## 3.4 Konzistencia a zamykanie

PostgreSQL bude zdrojom pravdy pre stav publikačných termínov. Pre jeden termín sa použije:

- unikátne databázové obmedzenie,
- transakčný prechod stavov,
- databázový alebo advisory lock,
- deterministický idempotency key.

PostgreSQL poskytuje aplikačne definované advisory locks, ktoré sú vhodné na koordinovanie jednej logickej úlohy medzi procesmi. Implementácia však musí používať zámok spolu s unikátnymi obmedzeniami a stavovým modelom, nie ako jedinú ochranu. Pozri [oficiálnu dokumentáciu PostgreSQL k zámkom](https://www.postgresql.org/docs/current/explicit-locking.html).

## 3.5 Externé integračné predpoklady

- Google Calendar API podporuje úplnú a následnú inkrementálnu synchronizáciu pomocou `syncToken`; strata alebo expirácia tokenu vyžaduje nový full sync. Pozri [Google Calendar – Synchronize resources efficiently](https://developers.google.com/workspace/calendar/api/guides/sync).
- Konkrétny výskyt opakovanej udalosti možno identifikovať pomocou údajov ako `recurringEventId` a `originalStartTime`. Pozri [Google Calendar Events resource](https://developers.google.com/workspace/calendar/api/v3/reference/events).
- Discord správa podporuje najviac 10 embedov a súčet textu embedov má vlastný limit. Kompozícia preto musí obsah deliť. Pozri [Discord Message Resource](https://docs.discord.com/developers/resources/message).
- `@everyone` sa musí nachádzať v texte a zároveň byť explicitne povolené cez `allowed_mentions`; ostatné zmienky budú vypnuté.
- Discord rate limity sa nesmú hardcodovať a musí ich obsluhovať použitá knižnica alebo HTTP adaptér podľa odpovedí API. Pozri [Discord Rate Limits](https://docs.discord.com/developers/topics/rate-limits).
- Viditeľnosť Discord príkazov môže byť obmedzená v Discorde, ale aplikačný backend musí vždy vykonať vlastnú kontrolu rolí. Pozri [Discord Application Commands](https://docs.discord.com/developers/interactions/application-commands).

---

# 4. Stavové modely, ktoré treba navrhnúť ako prvé

## 4.1 Publikačný termín

Navrhnúť explicitný stavový automat:

```text
PLANNED
  ├─► COMPOSING
  │     ├─► READY
  │     └─► FAILED_RETRYABLE / FAILED_FINAL
  ├─► PUBLISHING
  │     ├─► PUBLISHED_AUTO
  │     ├─► PUBLISHED_MANUAL
  │     ├─► PARTIALLY_PUBLISHED
  │     └─► FAILED_RETRYABLE / FAILED_FINAL
  └─► SKIPPED_BY_MANUAL_RUN
```

Presné povolené prechody sa implementujú v doménovej službe. Stav nemožno ľubovoľne meniť všeobecným databázovým endpointom.

## 4.2 Archivácia kanála

```text
REQUESTED ─► APPROVED ─► ARCHIVING ─► ARCHIVED
     │             │             └─► FAILED
     ├─► REJECTED
     └─► EXPIRED
```

Admin pri priamej archivácii vytvorí záznam už v stave `APPROVED`, aby aj okamžitá operácia mala rovnakú auditnú stopu.

## 4.3 Synchronizácia kalendára

```text
NEVER_SYNCED ─► SYNCING ─► HEALTHY
                    │         │
                    └─────────┴─► STALE / ERROR
```

Stav musí obsahovať posledný úspešný sync, posledný pokus, typ chyby a informáciu, či je cache ešte použiteľná na publikovanie.

## 4.4 Redakčná hodnota

Popis udalosti musí rozlišovať minimálne:

```text
INHERIT_GLOBAL_POLICY
CUSTOM_VALUE
INTENTIONALLY_EMPTY
```

Zaradenie udalosti musí rozlišovať:

```text
AUTO
FORCE_INCLUDE
FORCE_EXCLUDE
```

Tieto hodnoty sa nesmú nahradiť nejednoznačnou kombináciou `NULL`, prázdneho textu a booleanov bez centralizovaného významu.

---

# 5. Etapa 0 – príprava projektu a rozhodnutí

## 5.1 Cieľ

Vytvoriť bezpečný priestor pre novú verziu a uzavrieť technické rozhodnutia, ktoré ovplyvňujú všetky ďalšie etapy.

## 5.2 Úlohy

- Založiť samostatnú vývojovú vetvu alebo dlhodobo oddelený adresár novej verzie.
- Zdokumentovať, ktoré pôvodné súbory zostávajú počas vývoja produkčné.
- Vytvoriť technické rozhodnutia vo forme ADR pre:
  - modulárny monolit a tri procesy,
  - PostgreSQL,
  - spôsob Discord OAuth relácií,
  - spôsob Google autentifikácie,
  - idempotenciu publikovania,
  - architektúru frontendu,
  - prevádzkové nasadenie.
- Získať alebo pripraviť:
  - testovaciu Discord aplikáciu a testovací server,
  - testovací Google Cloud projekt,
  - testovací kalendár,
  - oddelené testovacie emoji, kanály, roly a kategórie.
- Potvrdiť stabilné Discord ID pre roly Admin, Team Mod a SDB / FMA.
- Potvrdiť produkčný moderátorský kanál a cieľový kanál oznamov.
- Vytvoriť bezpečný zoznam potrebných tajomstiev a ich vlastníkov.
- Pripraviť reprezentatívne testovacie udalosti:
  - časovanú,
  - celodennú,
  - viacdňovú,
  - opakovanú,
  - presunutý výskyt,
  - zrušený výskyt,
  - udalosť s Google popisom,
  - udalosť so `stop carlo`,
  - udalosti na hraniciach 14-dňového okna a zmeny času.

## 5.3 Výstupy

- schválené ADR,
- dostupné testovacie prostredia,
- matica tajomstiev a konfigurácií,
- sada testovacích kalendárových scenárov,
- rozhodnutie o produkčnom spôsobe nasadenia.

## 5.4 Kontrolná brána E0

Etapa je hotová, keď vývoj a testovanie nemusia používať produkčný Discord server, produkčný bot token ani produkčný Google kalendár.

---

# 6. Etapa 1 – aplikačná kostra a vývojové prostredie

## 6.1 Cieľ

Vytvoriť spustiteľnú kostru API, bota, workera a frontendu so spoločnou konfiguráciou a automatizovanou kontrolou kvality.

## 6.2 Backend

- Založiť Python balík novej aplikácie.
- Zaviesť jednotný formát konfigurácie prostredia.
- Validovať konfiguráciu pri štarte a zlyhať s jasnou chybou pri chýbajúcom tajomstve.
- Pridať API proces so základným `/health/live` a `/health/ready`.
- Pridať bot proces, ktorý sa pripojí k testovaciemu Discordu bez produkčných príkazov.
- Pridať worker proces s bezpečným prázdnym pracovným cyklom.
- Zaviesť štruktúrované logovanie a korelačné ID.
- Zaviesť jednotné mapovanie interných chýb na používateľské odpovede.

## 6.3 Databáza a migrácie

- Pridať PostgreSQL do lokálneho prostredia.
- Nakonfigurovať databázový connection pool pre API, bota a worker.
- Založiť Alembic a prvú prázdnu migráciu.
- Pripraviť transakčný wrapper pre aplikačné prípady použitia.
- Pridať testovaciu databázu vytváranú pre integračné testy.

## 6.4 Frontend

- Založiť TypeScript frontend.
- Pridať routing, globálne chybové rozhranie a základnú stránku stavu.
- Zaviesť dizajnové tokeny pre farby, typografiu, rozostupy, radius a tiene.
- Pridať základný responzívny layout a navigáciu.
- Pridať klienta webového API s typovanými odpoveďami.

## 6.5 Kvalita a automatizácia

- Formátovanie, linting a statická typová kontrola backendu.
- Linting, formátovanie a TypeScript kontrola frontendu.
- Backend a frontend test command.
- CI pipeline pre každý návrh zmeny.
- Kontrola databázových migrácií.
- Kontrola, že do repozitára neboli pridané tajomstvá.

## 6.6 Kontrolná brána E1

- Všetky tri backend procesy a frontend sa spustia jedným zdokumentovaným postupom.
- Health check rozlíši živý proces od nepripravenej databázy.
- CI prejde na čistej kópii repozitára.
- Produkčný kód pôvodného bota nebol zmenený.

---

# 7. Etapa 2 – doménový a databázový základ

## 7.1 Cieľ

Implementovať dátový model a čisté pravidlá, na ktorých budú neskôr stáť kalendár, web aj Discord.

## 7.2 Databázové entity

Implementovať migrácie a modely minimálne pre:

- `guild_config`,
- `calendar_source`,
- `external_event`,
- `event_override`,
- `event_series_override`,
- `manual_event`,
- `info_announcement`,
- `publication_run`,
- `publication_item`,
- `publication_message`,
- `channel_archive_request`,
- `reaction_config`,
- webové relácie,
- `audit_log`,
- stav integračných úloh.

## 7.3 Obmedzenia a indexy

- Unikátny zdrojový kľúč kalendárovej udalosti.
- Unikátny publikačný termín pre server.
- Unikátny idempotency key externých operácií.
- Index na čas udalosti a aktívny stav.
- Index na účinnosť pravidiel opakovanej série.
- Index na platnosť INFO oznamov.
- Index na stav a plánovaný čas publikačných behov.
- Index na čakajúce archivácie.
- Cudzie kľúče a pravidlá mäkkého odstránenia.

## 7.4 Hodnotové objekty

Implementovať a otestovať:

- `GuildId`, `RoleId`, `ChannelId`,
- `EventSourceKey`,
- `RecurringSeriesKey`,
- lokálny publikačný termín,
- 14-dňové publikačné okno,
- stav vlastného popisu,
- rozhodnutie o zaradení,
- stav publikácie,
- stav archivácie.

## 7.5 Repozitáre a transakcie

- Definovať rozhrania repozitárov v aplikačnej vrstve.
- Implementovať PostgreSQL adaptéry.
- Zakázať priamy prístup API endpointov k ORM modelom.
- Zabezpečiť, že audit a doménová zmena vzniknú v jednej databázovej transakcii.

## 7.6 Testy

- Migrácia prázdnej databázy od nuly.
- Upgrade cez všetky migrácie.
- Unikátne obmedzenia a konflikty.
- Mäkké odstránenie a historické referencie.
- Optimistická verzia redakčnej úpravy.
- Výpočty `Europe/Bratislava`, vrátane DST.

## 7.7 Kontrolná brána E2

Dátový model musí vedieť reprezentovať každý akceptačný scenár zo zadania bez pridávania dočasných JSON polí alebo obchádzania vzťahov.

---

# 8. Etapa 3 – integrácia Google Kalendára

## 8.1 Cieľ

Spoľahlivo synchronizovať jeden kalendár a súčasne zachovať model pripravený na viac zdrojov.

## 8.2 Autentifikácia

- Použiť iba potrebný read-only Calendar scope.
- Pre jeden organizačný kalendár preferovať service account, ktorému je konkrétny kalendár explicitne zdieľaný.
- Nepoužívať domain-wide delegation, ak nie je potrebný prístup k údajom viacerých používateľov.
- Uložiť tajomstvo mimo databázových verejných nastavení a mimo frontendu.
- Vytvoriť kontrolný endpoint „overiť pripojenie“ bez zverejnenia citlivých údajov.

Google odporúča voliť najmenší potrebný OAuth scope a rozlišuje explicitné zdieľanie zdroja so service accountom od domain-wide delegation. Pozri [Google Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth) a [Google Workspace credentials](https://developers.google.com/workspace/guides/create-credentials).

## 8.3 Plná synchronizácia

- Načítať všetky potrebné udalosti v bezpečnom časovom horizonte.
- Spracovať stránkovanie.
- Expandovať výskyty opakovaných udalostí pre potrebné obdobie.
- Uložiť Google event ID, recurring event ID, original start time, ETag a status.
- Normalizovať časované a celodenné hodnoty.
- Zachovať pôvodné časové pásmo a vypočítať bratislavské zobrazenie.
- Označiť chýbajúce udalosti ako odstránené až po úspešnom dokončení full syncu.
- Uložiť nový sync token až po úspešnom spracovaní všetkých strán.

## 8.4 Inkrementálna synchronizácia

- Načítať zmeny pomocou uloženého sync tokenu.
- Dodržať povinné rovnaké parametre synchronizačného dotazu.
- Spracovať zrušené a odstránené udalosti.
- Pri neplatnom sync tokene bezpečne prejsť na full sync.
- Nevymazať redakčné úpravy pri aktualizácii zdrojovej udalosti.
- Aktualizovať stav synchronizácie až po transakčnom uložení.

## 8.5 Opakované udalosti

- Definovať stabilný kľúč konkrétneho výskytu.
- Definovať stabilný kľúč série.
- Overiť presunutý výskyt, vynechaný výskyt a zrušený výskyt.
- Overiť, že úprava konkrétneho výskytu zostane pripojená po bežnom syncu.
- Overiť správanie pri zmene recurrence pravidla v Google Kalendári.
- Pri nejednoznačnej zmene vytvoriť administrátorské upozornenie namiesto tichého pripojenia úpravy k nesprávnej udalosti.

## 8.6 `stop carlo`

- Implementovať samostatný parser riadiacej frázy.
- Porovnávať bez ohľadu na veľkosť písmen.
- Nikdy nepreniesť riadiacu frázu do verejného popisu.
- Zachovať raw zdrojový popis pre administrátorský editor.
- Vypočítať dôvod automatického vylúčenia bez zmeny zdrojových dát.

## 8.7 Obnova a čerstvosť

- Zaviesť retry s exponenciálnym oneskorením a limitom.
- Zaznamenať posledný pokus a posledný úspech.
- Implementovať konfigurovateľný maximálny vek cache.
- Rozlíšiť warning „stará cache“ od blocking error „publikovanie nie je bezpečné“.
- Poslať blokujúcu chybu do kanála `moderátori`.

## 8.8 Kontrolná brána E3

Na testovacom kalendári musí opakovane prejsť full sync, incremental sync, zrušenie, presun a zmena série bez straty redakčných cudzích kľúčov.

---

# 9. Etapa 4 – kompozícia publikačného balíka

## 9.1 Cieľ

Vytvoriť čistú, deterministickú službu, ktorá zo snapshotu údajov zostaví presný výsledok nezávisle od webu a Discordu.

## 9.2 Výpočet najbližšieho termínu

- Predvolene pondelok 20:00.
- Adminom nastaviteľný deň a čas.
- Výpočet v `Europe/Bratislava`.
- Korektné správanie pri DST.
- Stabilný identifikátor termínu odvodený od servera a lokálneho plánovaného času.
- Už publikovaný alebo ručne vybavený termín sa nepovažuje za najbližší nespracovaný.

## 9.3 Výber podľa 14-dňového okna

- Použiť interval `[termín, termín + 14 dní)`.
- Zahrnúť viacdňovú udalosť, ktorá sa prekrýva s oknom.
- Správne zaradiť celodenné udalosti podľa lokálnych dátumov.
- Rovnaká funkcia sa použije pre webový editor, Discord preview a publikovanie.

## 9.4 Rozhodnutie o zaradení

Implementovať prioritu:

```text
instance FORCE_INCLUDE/FORCE_EXCLUDE
> stop carlo
> automatické zaradenie
```

Vylúčené udalosti budú súčasťou redakčného modelu editora, nie výsledného publikačného modelu.

## 9.5 Rozlíšenie titulku a popisu

Titulok:

```text
instance override
> účinný series override
> Google title
> fallback
```

Popis:

```text
instance override
> účinný series override
> Google description, iba ak je globálne povolený
> bez popisu
```

Stav `INTENTIONALLY_EMPTY` zastaví ďalšie dedenie.

## 9.6 Opakované série

- Vybrať najnovšie series pravidlo účinné pre daný výskyt.
- Výnimka konkrétneho výskytu má prednosť.
- Nové series pravidlo nemení minulé snapshoty.
- Editor musí dostať informáciu o zdroji každej finálnej hodnoty.
- Výpočet musí byť čistý a pokrytý tabuľkovými testami.

## 9.7 INFO a manuálne udalosti

- INFO vybrať podľa inkluzívnych lokálnych dátumov platnosti.
- Expirované INFO nevkladať, ale nevymazávať.
- Manuálne udalosti vyberať rovnakým časovým pravidlom ako externé udalosti.
- Zjednotiť oba druhy udalostí do spoločného výstupného modelu bez straty pôvodu.

## 9.8 Triedenie

- INFO pred eventami.
- Celodenné eventy pred časovanými v rámci dňa.
- Eventy podľa začiatku.
- Pri zhode podľa priority kalendára, titulku a stabilného ID.
- Testovať deterministickosť pri náhodnom poradí vstupov.

## 9.9 Formátovanie

- Zachovať vizuálny štýl pôvodného event embed modelu.
- Automaticky odvodiť slovenský deň a day emoji.
- Centralizovať texty pre časovanú, celodennú a viacdňovú udalosť.
- Validovať limity titulku, popisu, autora a celkového embedu.
- Bezpečne neutralizovať Discord zmienky v redakčnom obsahu.
- Vytvoriť frontendovo nezávislý serializovateľný `PublicationDraft`.

## 9.10 Delenie správ

- Vytvoriť plán správ ešte pred volaním Discordu.
- Rešpektovať 10 embedov a 6000 znakov embedov na správu.
- Rešpektovať 2000 znakov textového obsahu.
- `@everyone` zaradiť iba do prvej správy.
- Záverečnú seen výzvu zaradiť do jednoznačne poslednej správy.
- Pre každý plánovaný message part vytvoriť deterministický kľúč a nonce.

## 9.11 Kontrolná brána E4

Z fixných vstupných fixtures musí composer vždy vytvoriť rovnaký serializovaný balík a nesmie vytvoriť žiadnu správu prekračujúcu Discord limity.

---

# 10. Etapa 5 – autentifikácia, autorizácia a webové API

## 10.1 Discord OAuth2

- Zaregistrovať presné callback URL pre lokálne, staging a produkčné prostredie.
- Použiť scope potrebný na identitu a overenie členstva.
- Overiť `state`, návratovú URL a OAuth chyby.
- Po prihlásení načítať aktuálne členstvo a roly na serveri.
- Založiť serverovú reláciu; OAuth access token neposielať klientskemu JavaScriptu.
- Bezpečne obnovovať alebo ukončiť reláciu pri expirácii.
- Implementovať odhlásenie a zrušenie session.

## 10.2 Autorizačná služba

- Roly identifikovať Discord ID.
- Implementovať centralizovanú maticu Admin, Team Mod, SDB / FMA.
- Kontrolovať rolu pri každom use case, nie iba route skupine.
- Pre citlivú operáciu obnoviť roly z Discordu alebo použiť krátko platnú overenú cache.
- Odmietnuť používateľa, ktorý už nie je členom servera.
- Zapisovať zamietnuté citlivé pokusy bez ukladania zbytočných osobných údajov.

## 10.3 Bezpečnostný základ API

- Secure, HttpOnly a primerané SameSite cookies.
- CSRF ochrana pre meniace operácie.
- Presný CORS allowlist.
- Rate limit pre prihlasovanie a citlivé mutácie.
- Serverová validácia a normalizované chyby.
- Bezpečnostné hlavičky.
- Sanitizácia a escaping používateľského obsahu.
- Ochrana pred open redirect.
- Žiadne tajomstvá ani tracebacky v používateľských odpovediach.

## 10.4 API kontrakty

Implementovať verzované endpointy pre:

- session a aktuálneho používateľa,
- dashboard,
- najbližší publikačný termín,
- draft a preview,
- úpravu konkrétnej udalosti,
- úpravu série od výskytu,
- include/exclude rozhodnutie,
- manuálne udalosti,
- INFO oznamy,
- publikačnú históriu,
- ručné publikovanie,
- kalendárové zdroje a sync,
- nastavenia publikovania,
- nastavenia reakcií,
- kanálové operácie,
- čakajúce archivácie,
- správu povolených rolí,
- audit a health stav.

## 10.5 Súbežné úpravy

- Každý editovateľný objekt vráti verziu alebo ETag.
- Mutácia vyžaduje očakávanú verziu.
- Konflikt vráti HTTP conflict odpoveď s aktuálnymi údajmi.
- Frontend ponúkne obnovenie a vedomé zopakovanie zmeny.

## 10.6 Audit

- Definovať katalóg auditných udalostí.
- Zachytiť actor Discord ID, akciu, objekt, before/after, výsledok a korelačné ID.
- Citlivé tajomstvá a session hodnoty nikdy nevkladať do auditu.
- Auditný endpoint sprístupniť iba Adminovi, Team Modovi iba povolený podvýber.

## 10.7 Kontrolná brána E5

API testy musia dokázať, že Team Mod, SDB / FMA, Admin a neoprávnený člen dostanú pre každý use case presne povolený výsledok aj pri priamom volaní endpointu.

---

# 11. Etapa 6 – návrh a implementácia webovej administrácie

## 11.1 UX návrh pred implementáciou

- Vytvoriť informačnú architektúru a route mapu.
- Vytvoriť low-fidelity wireframes desktopu a mobilu.
- Vytvoriť high-fidelity návrh kľúčových obrazoviek.
- Definovať typografiu, farby, stavy a komponenty.
- Overiť návrh s reálnym Admin a Team Mod používateľom.
- Osobitne otestovať editor na mobile, nie iba dashboard.

## 11.2 Dizajnový systém

Implementovať znovupoužiteľné komponenty:

- app shell a navigáciu,
- tlačidlá a icon buttons,
- textové, dátumové a časové polia,
- selectory používateľov, rolí, kanálov a emoji,
- karty udalostí,
- status badge,
- prázdny stav,
- skeleton/loading stav,
- inline chybu a globálnu chybu,
- modal a confirmation dialog,
- toast iba pre doplnkovú spätnú väzbu,
- responzívnu tabuľku/kartový zoznam,
- Discord preview komponent.

## 11.3 Dashboard

- Najbližší termín a 14-dňové okno.
- Stav automatického publikovania.
- Posledný kalendárový sync a stale warning.
- Počty eventov, INFO a vylúčených udalostí.
- Posledná publikácia.
- Aktívne chyby.
- Čakajúce archivácie.
- Rýchle akcie podľa role používateľa.

## 11.4 Editor oznamov

- Implementovať jeden spoločný Redakčný pult pre Google, manuálne a INFO položky namiesto troch oddelených pracovísk.
- Na desktope súčasne zobraziť zdrojové filtre, jednotný zoznam a Discord náhľad; na menšom displeji zachovať rovnaký tok bez nekonečného prepínania rout.
- Počet najbližšieho prehľadu odvodiť od celého publikačného balíka a počty jednotlivých zdrojov pomenovať tak, aby ich nula nepôsobila ako prázdny celý balík.
- Zobraziť položky v publikovanom poradí.
- Zobraziť pôvod udalosti a dôvod vylúčenia.
- Zobraziť zdrojový a výsledný titulok/popís.
- Pri novom popise predvyplniť Google popis bez automatického uloženia.
- Umožniť `INHERIT`, `CUSTOM` a `INTENTIONALLY_EMPTY`.
- Pri recurring udalosti ponúknuť „iba tento“ a „tento a budúce“.
- Pri zdedenej series hodnote jasne ukázať jej rozsah.
- Adminovi umožniť force include/exclude.
- Vylúčené udalosti ponechať v oddelenej, ale viditeľnej sekcii.
- Ukladať položky individuálne.
- Spracovať version conflict bez straty rozpísaného textu.
- Zobraziť verný Discord preview.
- Náhľad renderovať ako reálny Discord kanál Carla vrátane rozdelenia správ, mention, embedov, thumbnailov a cieľovej reakcie, nie ako alternatívnu záložku obsahu.
- Zachovať pôvodnú mesačnú dvojpaletu v kanonickom modeli: jemná farba pre INFO a sýta farba pre kalendárové/manuálne udalosti.
- Na veľkom monitore neobmedzovať Redakčný pult dashboardovou maximálnou šírkou; pracovné stĺpce majú využiť dostupnú šírku aj výšku.
- Na širokom desktope udržať celý spodný okraj pultu vo viewporte a rolovať dlhé položky iba vo vnútorných paneloch.
- Otvárať editor kliknutím na hlavnú plochu záznamu aj explicitným tlačidlom „Upraviť“; veľký cieľ musí fungovať myšou aj klávesnicou.

## 11.5 Manuálne udalosti a INFO

- Zdieľaný riadkový zoznam a zdrojové filtre priamo v Redakčnom pulte; samostatné navigačné routy iba spätne presmerujú na spoločné pracovisko.
- Vytvorenie a úprava s live validáciou.
- Preview výslednej karty.
- Mäkké odstránenie/deaktivácia s potvrdením.
- Inkluzívne zobrazenie posledného dňa INFO.
- Kontrola thumbnailu a fallback.
- Priamy multipart upload JPEG/PNG/WebP do 8 MB, serverové overenie obsahu, odstránenie metadát, zmenšenie a jednotný WebP výstup v trvalom blob úložisku.
- Centrovaný Base UI modal pre vytvorenie a úpravu namiesto bočného editora; sticky akcie a bezpečný scroll na mobile.
- Viacdennú celodennú udalosť všade zobrazovať ako inkluzívny rozsah prvého až posledného dňa, hoci databázový koniec zostáva exkluzívny.

## 11.6 Publikácie

- História behov a ich stavov.
- Detail nemenného snapshotu.
- Odkazy na Discord správy.
- Zobrazenie čiastočného zlyhania po jednotlivých správach.
- Admin/SDB-FMA ručné publikovanie s dvojkrokovým potvrdením.
- Samostatná, výrazne chránená operácia núteného republish pre Admina.

## 11.7 Kanály a archivácie

- Formulár vytvorenia kanála s preview oprávnení.
- Výber členov a rolí.
- Čakajúce žiadosti.
- Detail dôvodu, žiadateľa a časového limitu.
- Admin schválenie/zamietnutie.
- Varovanie o synchronizácii oprávnení s archívnou kategóriou.

## 11.8 Roly a nastavenia

- Vyhľadanie člena servera.
- Pridanie/odobratie Team Mod a Admin.
- Ochrana posledného Admina.
- Kontrola Discord role hierarchy.
- Publikačný deň a čas s preview najbližšieho termínu.
- Google description default.
- Cieľové kanály.
- Generovaný úvod a fallback stav.
- Seen a auto-reaction emoji.
- Test emoji.
- Kalendárové zdroje a manuálny sync.

## 11.9 Prístupnosť a responzivita

- Klávesnicová navigácia.
- Viditeľný focus.
- Sémantické názvy a labely.
- Kontrast WCAG AA.
- Oznamovanie asynchrónnych výsledkov asistívnym technológiám.
- Testy na 360, 768, 1024 a 1440 px.
- Žiadna kritická funkcia iba na hover.
- Žiadna povinná horizontálne posúvaná desktopová tabuľka na mobile.

### 11.9.1 Automatizované vynucovanie UI/UX štandardu

Tento balík je naplánovaný, ale zatiaľ nie je systematicky implementovaný:

- Stylelint zakáže hex farby mimo tokenov a zdokumentovaného allowlistu.
- `eslint-plugin-jsx-a11y` a doplnková statická kontrola pokryjú labels, názvy ikonových akcií, klávesnicové handlery a zakázaný natívny viacnásobný select.
- Dokumentačný test overí označenie každého bodu kapitol 19 a 20 `UI_UX_STANDARDY.md` ako **[BLOKUJE]** alebo **[BACKLOG]**.
- Playwright projekty pokryjú primárny desktop a sekundárny mobil; Axe sa spustí na reprezentatívnych routach a stavoch.
- Browser testy overia celý klávesnicový tok, návrat fokusu, dvojklik/idempotenciu, konflikt, výpadok siete, expiráciu relácie a kanonickú zhodu náhľadu.
- CI bude blokovať nové alebo zhoršené porušenia; existujúci dlh sa smie oddeliť iba do evidovaného backlogu s ID a etapou.
- Zavedenie sa riadi `UI_UX_DESTILAT.md`, kapitolou 24 `UI_UX_STANDARDY.md` a etapou UX0 v `PLAN_UI_UX_AUDITU.md`.

## 11.10 Kontrolná brána E6

Reálny Admin a Team Mod musia bez vysvetľovania dokončiť editor, INFO oznam, manuálnu udalosť a archiváciu na desktope aj mobile. Kritické accessibility testy musia prejsť automaticky aj manuálne.

---

# 12. Etapa 7 – publikačný engine a plánovač

## 12.1 Generovanie úvodu

- Vytvoriť adaptér pre existujúci generatívny model.
- Definovať verziu promptu a ukladať ju k výsledku.
- Vytvoriť deterministický slovenský fallback.
- Sanitizovať výstup.
- Odstrániť alebo neutralizovať všetky nepovolené zmienky.
- `@everyone` vložiť aplikačne presne raz, nespoliehať sa na model.
- Nastaviť explicitné `allowed_mentions` iba pre everyone v prvej správe a prázdne pre ostatné správy.

## 12.2 Vytvorenie snapshotu

- Pred externým odoslaním uložiť nemenný `publication_run` a `publication_items`.
- Uložiť vygenerovaný úvod, fallback informáciu a plán správ.
- Po vytvorení snapshotu nepremiešavať obsah s neskoršími editmi.
- Nové zmeny po začiatku publikovania patria až ďalšiemu draftu.

## 12.3 Odosielanie

- Pre každú plánovanú Discord správu vytvoriť `publication_message`.
- Posielať sekvenčne v stabilnom poradí.
- Po každej správe uložiť Discord message ID.
- Použiť deterministický nonce tam, kde ho Discord endpoint podporuje.
- Rešpektovať rate limit odpovede a retry intervaly.
- Seen emoji pridať po úspešnom odoslaní finálnej správy.
- Chybu emoji zapísať ako warning, nie zlyhanie textovej publikácie.

## 12.4 Zotavenie z pádu

- Pri štarte workeru nájsť zaseknuté `COMPOSING` a `PUBLISHING` behy.
- Rozlíšiť bezpečne opakovateľnú časť od neistého externého účinku.
- Pri známom message ID pokračovať ďalšou časťou.
- Pri neistote nepokračovať automaticky do rizikovej duplicity; vytvoriť moderátorský incident s nástrojom na reconcile.
- Implementovať Admin akcie „označiť existujúcu správu“ a „bezpečne pokračovať“, ak budú potrebné pre recovery.

## 12.5 Scheduler

- Worker pravidelne materializuje najbližšie publikačné termíny.
- Pre due termín získa DB lock.
- Overí stav a čerstvosť kalendára.
- Spustí kompozíciu a publikovanie.
- Po reštarte dobehne zmeškaný termín podľa definovanej grace period.
- Termín mimo grace period nepublikuje bez Admin rozhodnutia.
- Všetky rozhodnutia zaznamená.

### 12.5.1 Ochranná lehota pred zverejnením

**Stav k 12. augustu 2026:** normatívny kontrakt je hotový, runtime stavový
automat ešte nie. Konfigurácia odmieta bežný režim `live`, kým táto podkapitola
a stavovo bezpečné Undo z 14.1/14.2 nemajú zelené integračné a staging dôkazy.
Brána nemá konfiguračný bypass; po dokončení sa odstráni vedomou, testovanou
zmenou kódu.

- Nastaviteľná lehota je 0–300 sekúnd, predvolene 30; hodnota 0 ju vypne.
- Po vytvorení nemenného snapshotu ostáva run trvácne v stave čakania a ešte nevytvorí verejnú správu ani `@everyone`.
- Ručný tok zobrazí countdown, verný náhľad, „Zastaviť“ a „Zverejniť teraz“.
- Automatický tok odošle dočasnú bežnú DM všetkým čerstvo načítaným Adminom a ďalším príjemcom z Nastavení.
- Oprávnený príjemca môže počas lehoty použiť tlačidlo alebo normalizovanú DM `stop`; zastavenie a prechod do publikovania sú atómové a idempotentné.
- Zlyhanie DM nezastaví publikovanie, ale vytvorí moderátorské upozornenie; dočasná DM sa po rozhodnutí odstráni, ak je dostupná.
- Reštart nesmie skrátiť lehotu, zdvojiť odoslanie ani stratiť stop; neskorý stop vráti pravdivý terminálny výsledok.

## 12.6 Ručný trigger

- API a Discord príkaz volajú rovnaký use case.
- Oprávnenie: Admin alebo SDB / FMA.
- Vyberie najbližší nespracovaný termín.
- Vráti termín, kanál, počty a preview na potvrdenie.
- Potvrdenie používa krátko platný, používateľsky viazaný token.
- Úspešný run označí termín ako manuálne vybavený.
- Scheduler tento jeden termín preskočí.
- Zlyhaný run ho za vybavený neoznačí.

## 12.7 Moderátorské upozornenia

Do kanála `moderátori` posielať:

- zlyhaný alebo zastaraný Calendar sync,
- blokované publikovanie,
- čiastočné publikovanie,
- vyčerpané retry,
- zlyhanú kanálovú alebo rolovú operáciu,
- upozornenie pred blížiacim sa publikovaním, ak zostane požadované,
- recovery výsledok.

Každé upozornenie má obsahovať korelačné ID a odkaz do webovej administrácie, nie tajný traceback.

## 12.8 Kontrolná brána E7

V stagingu musí prejsť automatický aj ručný run, vrátane viac než desiatich udalostí, zlyhania generátora úvodu, rate limit retry, pádu medzi správami a preskočenia nasledujúceho plánovaného termínu.

---

# 13. Etapa 8 – Discord príkazy a interakcie

## 13.1 Registrácia príkazov

- Počas vývoja používať guild-scoped príkazy testovacieho servera.
- Produkčné príkazy synchronizovať riadeným deployment krokom, nie pri každom reconnecte.
- Nastaviť predvolené Discord oprávnenia ako UX vrstvu.
- Každý handler vykoná aj vlastnú aplikačnú autorizáciu.

## 13.2 Vytvorenie kanála

- Príkaz otvorí interaktívny flow s natívnym UserSelect a RoleSelect.
- Umožní viac používateľov a povolených rolí.
- Pred potvrdením zobrazí názov, kategóriu a výsledné prístupy.
- Potvrdenie viazať na pôvodného používateľa.
- Použiť idempotency key interakcie.
- Výsledok a zlyhanie zobraziť ephemeral.
- Rovnaký use case sprístupniť webu.

## 13.3 Archivácia

- Príkaz automaticky použije aktuálny kanál a aktuálny dátum.
- Team Mod zadá dôvod a vytvorí DB žiadosť.
- Do `moderátori` sa odošle karta s persistentnými tlačidlami Schváliť/Zamietnuť.
- `custom_id` obsahuje iba bezpečný identifikátor žiadosti, nie autorizačné rozhodnutie.
- Callback načíta konkrétnu žiadosť a znovu overí Admin rolu.
- Jedno rozhodnutie je transakčne jednorazové.
- Pri schválení sa kanál presunie, premenuje a synchronizuje s archívnou kategóriou.
- Admin pri priamom použití prejde potvrdením a potom rovnakou archivačnou službou.

## 13.4 Náhľad oznamov

- Povolený Team Mod, SDB / FMA a Admin.
- Zobraziť najbližší termín a časové okno.
- Obsah rozdeliť podľa Discord limitov.
- Náhľad poslať ephemeral alebo cez bezpečný odkaz do webu.
- Jasne označiť, že nejde o publikáciu a neobsahuje funkčný everyone ping.

## 13.5 Ručné publikovanie

- Povolený iba Admin a SDB / FMA.
- Dvojkrokové potvrdenie.
- Tlačidlo viazané na používateľa a krátku expiráciu.
- Pri paralelnom pokuse zobraziť existujúci run, nie vytvoriť nový.
- Po úspechu uviesť, ktorý plánovaný termín bude preskočený.

## 13.6 Všeobecné interakcie

- Zachovať náhodný status z `thoughts.txt` alebo jeho nového spravovateľného zdroja.
- Zachovať odpoveď na súkromnú správu, ak je funkcia stále zapnutá.
- Zachovať reakciu pri označení bota ako samostatne konfigurovateľnú funkciu.
- Zachovať automatické reakcie vo vybraných kanáloch.
- Chyby reakcií zaznamenať bez zahltenia logov.

## 13.7 Kontrolná brána E8

Simulované cudzie kliknutie, expirované tlačidlo, jedna reakcia pri viacerých archiváciách a súbežný publish trigger nesmú vykonať neoprávnenú ani duplicitnú operáciu.

---

# 14. Etapa 9 – webová správa kanálov, rolí a reakcií

## 14.1 Kanály

- Načítať iba povolené kategórie a textové kanály.
- Zobraziť členov a roly s vyhľadávaním.
- Preview permission overwrites.
- Vytvorenie cez spoločnú službu.
- Archivácia a rozhodovanie cez spoločnú službu.
- Odkaz na vytvorený alebo archivovaný kanál.
- Časovo neobmedzené Undo overí aktuálny stav: nový kanál presne odstráni iba ak je prázdny a nezmenený, inak ponúkne archiváciu; archiváciu obnoví iba z platného snapshotu.

## 14.2 Roly

- Načítať člena zo servera a jeho aktuálne roly.
- Povoliť iba Team Mod a Admin operácie.
- SDB / FMA sa používa na autorizáciu publikovania, ale jeho správa nie je súčasťou požadovaného základného role editora, pokiaľ sa zadanie neskôr nerozšíri.
- Pred zmenou overiť hierarchy a `manage_roles`.
- Zakázať odobratie posledného Admina spravujúceho aplikáciu.
- Po zmene znova načítať stav z Discordu.
- Auditovať úspech aj relevantné zlyhanie.
- Časovo neobmedzené Undo vráti rolu iba pri nezmenenom relevantnom stave, čerstvom oprávnení a zachovaní ochrany posledného Admina.

## 14.3 Reakcie

- Samostatný seen emoji toggle a hodnota.
- Samostatný auto-reaction toggle, emoji a zoznam kanálov.
- Samostatný mention-reaction toggle a emoji.
- Vyhľadať serverové emoji a podporiť Unicode.
- Testovacia reakcia v zvolenom kanáli.
- Zobraziť nedostupné uložené emoji.
- Neplatnú zmenu neuložiť ako aktívnu.

## 14.4 Publikovanie a kalendáre

- Spoločná sekcia Nastavenia bez roztrieštenia do technických obrazoviek.
- Výber jedného alebo viacerých Google kalendárov, aktivácia, priorita a stav poslednej synchronizácie.
- Publikačný deň, čas, časové pásmo, cieľový Discord kanál a náhľad nasledujúceho termínu.
- Predvolené používanie Google popisov a jasný opis jeho dopadu na nové oznamy.
- Nastavenie automatického úvodu, seen reakcie a súvisiacich fallbackov.
- Nastavenie ochrannej lehoty a ďalších príjemcov dočasnej DM; aktuálni Admini sú príjemcami vždy.
- Položku Nastavenia nezobrazovať v navigácii, kým príslušné služby a API nemajú funkčné čítanie, zápis, autorizáciu a audit.

## 14.5 Kontrolná brána E9

Každá operácia z webu a jej Discord ekvivalent musia vytvoriť rovnaký doménový výsledok a rovnaký auditný typ.

---

# 15. Etapa 10 – migrácia údajov

## 15.1 Inventarizácia

- Vytvoriť read-only export pôvodnej SQLite databázy.
- Zistiť počty aktívnych, budúcich a expirovaných záznamov.
- Identifikovať poškodené dátumy, duplicitné oznamy a neplatné URL.
- Zaznamenať pôvodné settings.

## 15.2 Migračné mapovanie

- INFO oznamy mapovať na `info_announcement`.
- Budúce ručné eventy najprv skúsiť spárovať s Google udalosťou.
- Párovanie vykonať konzervatívne podľa dátumu, času a normalizovaného názvu.
- Automaticky spárovať iba jednoznačné výsledky.
- Nejednoznačné výsledky zaradiť do review reportu.
- Nespárované udalosti importovať ako `manual_event` po schválení.
- Pôvodný text spárovanej udalosti previesť na instance override iba po potvrdení rozdielu.
- Emoji a auto-reaction kanály previesť do novej konfigurácie.
- Názvy rolí nahradiť overenými Discord ID.

## 15.3 Migračný nástroj

- `--dry-run` bez zápisu.
- Strojovo čitateľný aj ľudský report.
- Stabilné migračné kľúče.
- Opakované spustenie bez duplicít.
- Transakcia alebo bezpečné dávky.
- Explicitné potvrdenie cieľovej databázy.
- Žiadna implicitná práca s produkčným súborom.

## 15.4 Migračná skúška

- Obnoviť kópiu produkčnej SQLite do izolovaného prostredia.
- Spustiť dry run.
- Manuálne vyhodnotiť sporné eventy.
- Spustiť import do staging PostgreSQL.
- Porovnať počty a reprezentatívne náhľady.
- Zmazať staging DB a celý proces zopakovať.

## 15.5 Kontrolná brána E10

Dve po sebe vykonané migračné skúšky musia vytvoriť rovnaký report a druhý import nesmie založiť duplicity.

---

# 16. Etapa 11 – komplexné testovanie a hardening

## 16.1 Jednotkové testy

Dokončiť maticu zo zadania, najmä:

- hranice 14 dní,
- inkluzívny koniec INFO,
- DST,
- viacdňové prekrytie,
- stop carlo a force include,
- Google description default,
- instance a series override,
- deterministické triedenie,
- batching limitov,
- oprávnenia,
- stavové prechody a skip.

## 16.2 Integračné testy

- PostgreSQL transakcie a locks.
- Calendar full/incremental sync.
- Discord message adaptér.
- OAuth callback a session.
- Role hierarchy.
- Persistent archive buttons.
- Worker recovery.
- Audit atomicky so zmenou.

## 16.3 End-to-end testy

- Všetkých 14 scenárov zo zadania.
- Desktop aj mobil.
- Team Mod, SDB / FMA, Admin a neoprávnený používateľ.
- Reload stránky počas editácie.
- Konflikt dvoch editorov.
- Ručné publikovanie a následný plánovaný čas.
- Zlyhanie Google a generátora úvodu.

## 16.4 Bezpečnostné testy

- CSRF.
- XSS v názve a popise.
- Discord mention injection.
- OAuth state a open redirect.
- Priamy access na Admin endpoint.
- Cudzie alebo expirované potvrdenie.
- SSRF cez thumbnail URL/proxy.
- Session fixation a logout.
- Únik tajomstiev v logoch a chybách.
- Ochrana posledného Admina.

## 16.5 Prevádzkové testy

- Reštart každého procesu samostatne.
- Výpadok DB.
- Výpadok Discord Gateway.
- Výpadok Calendar API.
- Výpadok intro generatora.
- Pád uprostred publikovania.
- Dve súčasné worker inštancie.
- Obnova zo zálohy.

## 16.6 Vizuálna QA

- Všetky hlavné stránky v definovaných šírkach.
- Dlhé slovenské názvy a popisy.
- Prázdne a chybové stavy.
- Veľký počet udalostí.
- Veľký počet kalendárov a kanálov.
- Focus, kontrast, zoom a reduced motion.

## 16.7 Kontrolná brána E11

Nesmie zostať otvorená chyba s možnosťou neoprávnenej zmeny, dvojitého publikovania, straty úprav, nesprávneho času alebo nezotaviteľného čiastočného publikovania.

---

# 17. Etapa 12 – staging, tieňová prevádzka a akceptácia

## 17.1 Staging

- Samostatná Discord aplikácia a server.
- Samostatný Google Cloud projekt a kalendár.
- Samostatná PostgreSQL databáza.
- Produkčne podobný reverse proxy a HTTPS.
- Oddelené tajomstvá.

## 17.2 Tieňová prevádzka

Počas najmenej dvoch publikačných cyklov:

- nový bot synchronizuje produkčný kalendár read-only alebo jeho bezpečnú kópiu,
- zostavuje drafty,
- neposiela ich do produkčného oznamového kanála,
- výstup sa porovnáva s očakávaným manuálnym výsledkom,
- sleduje sa druhé zobrazenie rovnakej udalosti a zachovanie úpravy,
- overí sa stop carlo, recurrence a Google description policy.

## 17.3 Používateľská akceptácia

Admin a Team Mod vykonajú pripravený checklist:

- prihlásenie,
- editor,
- opakovaná udalosť,
- INFO,
- manuálna udalosť,
- preview,
- kanál,
- archivácia,
- reakcie,
- roly,
- história,
- mobilné použitie.

SDB / FMA vykoná preview a ručný publish flow bez prístupu k ostatnej administrácii.

## 17.4 Kontrolná brána E12

Všetky akceptačné kritériá zo zadania sú označené ako splnené s odkazom na test, staging dôkaz alebo podpísaný UAT výsledok.

---

# 18. Etapa 13 – produkčné nasadenie a cutover

## 18.1 Pred nasadením

- Schváliť release commit a nemenné image artefakty.
- Zálohovať pôvodnú SQLite databázu a konfiguráciu.
- Overiť obnovu novej PostgreSQL zálohy.
- Vytvoriť produkčné tajomstvá.
- Overiť Discord role hierarchy a oprávnenia bota.
- Overiť zdieľanie Google kalendára.
- Vybrať čas mimo publikačného okna.
- Informovať Adminov o krátkom read-only okne.
- Pripraviť rollback checklist.

## 18.2 Cutover postup

1. Pozastaviť úpravy v starej verzii.
2. Zastaviť starý plánovač a potvrdiť, že nebeží druhá inštancia.
3. Vytvoriť finálnu zálohu SQLite.
4. Spustiť finálny dry run migrácie.
5. Spustiť import do produkčného PostgreSQL.
6. Overiť migračný report.
7. Spustiť API a web v obmedzenom Admin režime.
8. Overiť OAuth, roly, kalendár, draft a nastavenia.
9. Spustiť bot proces s produkčným tokenom.
10. Synchronizovať príkazy riadeným krokom.
11. Spustiť worker s automatickým publikovaním ešte pozastaveným.
12. Vykonať full Calendar sync.
13. Admin skontroluje najbližší draft.
14. Aktivovať automatický rozvrh.
15. Potvrdiť health checks a moderátorské upozornenia.
16. Ukončiť read-only okno.

## 18.3 Rollback podmienky

Rollback spustiť pri:

- nesprávnej migrácii aktívnych oznamov,
- nefunkčnom OAuth pre Admina,
- chybnom výpočte najbližšieho termínu,
- nefunkčnom Calendar syncu bez použiteľnej cache,
- nedostatočných Discord oprávneniach,
- riziku duplicitného publikovania.

Rollback:

1. vypnúť nový worker,
2. zastaviť nový bot proces,
3. ponechať novú DB na diagnostiku bez ďalších zápisov,
4. obnoviť starého bota s pôvodnou SQLite zálohou,
5. overiť presný stav najbližšieho publikovania,
6. zdokumentovať incident a nové dáta vzniknuté počas okna.

## 18.4 Kontrolná brána E13

Produkcia je aktívna až po potvrdení jedného úspešného kontrolovaného draftu, všetkých health checkov a jednoznačného stavu nasledujúceho publikačného termínu.

---

# 19. Etapa 14 – stabilizácia a ukončenie starej verzie

## 19.1 Stabilizačné obdobie

Počas prvých troch publikačných cyklov:

- Admin skontroluje draft pred termínom,
- vývojár sleduje sync a publish metriky,
- každý run sa porovná so snapshotom,
- kontrolujú sa opakované udalosti z predchádzajúceho týždňa,
- kontroluje sa iba jedna everyone zmienka,
- kontroluje sa seen emoji a moderátorský kanál,
- incidenty sa riešia prioritne.

## 19.2 Ukončenie legacy

Po stabilizačnom období:

- odobrať starému procesu možnosť štartu,
- bezpečne archivovať pôvodnú SQLite a zdrojový release,
- označiť pôvodnú konfiguráciu ako nepoužívanú,
- aktualizovať používateľský a prevádzkový manuál,
- odstrániť zastarané produkčné tajomstvá,
- ponechať migračný report a rollback zálohu podľa retenčnej politiky.

## 19.3 Post-implementation review

- Vyhodnotiť incidenty a manuálne zásahy.
- Zmerať čas potrebný na týždennú redakciu oproti pôvodnému botovi.
- Vyhodnotiť použiteľnosť na mobile.
- Spísať technický dlh a nepovinné rozšírenia.
- Určiť vlastníka pravidelnej aktualizácie závislostí a testu obnovy.

---

# 20. Závislosti medzi etapami

| Etapa                      | Priama závislosť                 | Môže čiastočne bežať paralelne s          |
| -------------------------- | -------------------------------- | ----------------------------------------- |
| E0 Príprava                | zadanie                          | ničím                                     |
| E1 Kostra                  | E0                               | UX prieskum                               |
| E2 Doména a DB             | E1                               | prvé wireframes                           |
| E3 Google Calendar         | E2                               | OAuth základ                              |
| E4 Composer                | E2, fixtures z E3                | API auth, UX návrh                        |
| E5 API a autorizácia       | E1, E2                           | E3, E4                                    |
| E6 Web                     | E5 kontrakty, E4 draft model     | publikačný engine                         |
| E7 Publikovanie            | E3, E4, E2                       | webové stránky                            |
| E8 Discord príkazy         | E5 autorizácia, aplikačné služby | neskorá E6                                |
| E9 Web kanály/roly/reakcie | E5, služby E8                    | E7                                        |
| E10 Migrácia               | stabilná E2 schéma, E3 matching  | E6–E9                                     |
| E11 Hardening              | všetky funkčné etapy             | priebežne od E1                           |
| E12 Staging/UAT            | E10, E11                         | dokumentácia                              |
| E13 Produkcia              | E12                              | ničím                                     |
| E14 Stabilizácia           | E13                              | nepovinné backlog položky až po stabilite |

Kritická cesta je:

```text
E0 → E1 → E2 → E3 → E4 → E7 → E11 → E12 → E13 → E14
```

Webový dizajn a frontend možno rozvíjať paralelne po stabilizovaní draft modelu a API kontraktov.

---

# 21. Odporúčané pracovné prúdy

Ak na projekte pracuje viac ľudí, rozdelenie môže byť:

## Prúd A – doména a dáta

- PostgreSQL,
- migrácie,
- composer,
- recurrence a overrides,
- audit,
- migračný nástroj.

## Prúd B – integrácie a Discord

- Calendar sync,
- Discord adapter,
- scheduler,
- publish recovery,
- príkazy,
- channel/role operácie.

## Prúd C – web a UX

- OAuth flow,
- webové API kontrakty v spolupráci s backendom,
- dizajnový systém,
- editor,
- dashboard a administračné stránky,
- E2E a accessibility.

Spoločné integračné body musia mať vopred dohodnuté typované kontrakty. Paralelný vývoj nesmie vytvoriť duplicitné doménové pravidlá vo frontende.

---

# 22. Orientačný odhad rozsahu

Odhad slúži na plánovanie kapacity, nie ako pevný termín. Predpokladá jedného skúseného full-stack vývojára, pripravené prístupy a bez zásadnej zmeny zadania.

| Oblasť                                 |     Orientačný rozsah |
| -------------------------------------- | --------------------: |
| Príprava, ADR a prostredie             |        4–7 človekodní |
| Kostra, CI, PostgreSQL a migrácie      |       6–10 človekodní |
| Doménový model a composer              |      10–16 človekodní |
| Google Calendar sync a recurrence      |       8–14 človekodní |
| OAuth, API, RBAC a audit               |       8–13 človekodní |
| Webový dizajn a administrácia          |      15–24 človekodní |
| Publikovanie, scheduler a recovery     |      10–16 človekodní |
| Discord príkazy, kanály, roly, reakcie |       8–13 človekodní |
| Migrácia údajov                        |        5–9 človekodní |
| Hardening, E2E, security a staging     |      10–18 človekodní |
| Cutover, dokumentácia a stabilizácia   |        5–9 človekodní |
| **Spolu**                              | **89–149 človekodní** |

Pre jedného človeka ide realisticky o niekoľkomesačný projekt. Menší tím môže skrátiť kalendárny čas paralelizáciou webu, integrácií a domény, nie však lineárne, pretože kritická cesta a integračné brány zostávajú.

Odhad treba spresniť po E0 a po prototypoch recurrence synchronizácie, publikačného recovery a mobilného editora.

---

# 23. Riadenie backlogu

Odporúčané epic skupiny:

- `FND` – foundation a CI,
- `DATA` – databáza a migrácie,
- `GCAL` – Google Calendar,
- `COMP` – composer a formátovanie,
- `AUTH` – OAuth a RBAC,
- `WEB` – webová administrácia,
- `PUB` – publikovanie a scheduler,
- `BOT` – Discord príkazy a listenery,
- `CHAN` – kanály a archivácie,
- `ROLE` – roly,
- `REACT` – seen a automatické reakcie,
- `MIG` – migrácia legacy údajov,
- `OBS` – logy, health, alerty a zálohy,
- `QA` – E2E, security, accessibility a resilience,
- `REL` – staging, cutover a stabilizácia.

Každá backlog položka musí obsahovať:

- používateľský alebo prevádzkový výsledok,
- oprávnené roly,
- validačné pravidlá,
- auditný dopad,
- chybové scenáre,
- testy,
- väzbu na kapitolu zadania,
- definíciu hotového výsledku.

---

# 24. Definícia hotovej funkcie

Funkcia je hotová iba vtedy, keď:

- je aktuálny stav funkcie, vykonané testy a nasledujúci krok zapísaný v `STATUS.md`,
- je implementovaná cez spoločnú aplikačnú službu,
- má serverovú autorizáciu,
- má serverovú validáciu,
- vytvára audit, ak je citlivá,
- má jednotkové testy doménových pravidiel,
- má integračný test externého alebo databázového účinku,
- má používateľsky zrozumiteľný loading, success a error stav,
- funguje na mobile aj desktope, ak má webové UI,
- neprekračuje Discord limity, ak vytvára Discord obsah,
- má logy bez tajomstiev,
- je zdokumentovaná,
- prešla code review,
- prešla CI bez výnimiek a vypnutých testov.

---

# 25. Definícia hotovej kompletnej implementácie

Kompletná implementácia je hotová až po splnení všetkých nasledujúcich bodov:

1. Všetky akceptačné kritériá zo zadania sú preukázateľne splnené.
2. Automatický dvojtýždňový balík funguje bez redakčného zásahu.
3. Google synchronizácia je inkrementálna, obnoviteľná a monitorovaná.
4. Instance aj series overrides fungujú bez zmeny histórie.
5. Webová administrácia je použiteľná pre všetky tri oprávnené roly.
6. Ručné aj automatické publikovanie je chránené proti bežným duplicitám.
7. Čiastočné publikovanie má zdokumentovaný a otestovaný recovery postup.
8. Discord príkazy obsahujú iba schválený rozsah.
9. Archivácia je viazaná na konkrétnu žiadosť.
10. Kanálové a rolové operácie rešpektujú Discord oprávnenia a hierarchiu.
11. Migrácia je opakovateľná a overená na kópii produkčných údajov.
12. Záloha a obnova PostgreSQL boli prakticky otestované.
13. Staging absolvoval najmenej dva tieňové publikačné cykly.
14. Produkčný cutover má pripravený rollback.
15. Prvé tri produkčné publikačné cykly prešli stabilizačnou kontrolou.
16. Pôvodný bot bol vyradený až po potvrdení stability novej verzie.

---

# 26. Prvé konkrétne implementačné kroky

Po schválení tohto plánu sa začne týmto poradím:

1. vytvoriť ADR pre cieľovú architektúru a nasadenie,
2. založiť testovaciu Discord aplikáciu a Google projekt,
3. vytvoriť novú adresárovú kostru bez zásahu do legacy runtime,
4. spustiť PostgreSQL a prvú migráciu,
5. implementovať časové a identifikačné hodnotové objekty,
6. vytvoriť Calendar fixtures vrátane recurrence a `stop carlo`,
7. implementovať `external_event`, instance override a series override,
8. implementovať full a incremental Calendar sync,
9. implementovať čistý publication composer,
10. až nad stabilným composerom uzavrieť API kontrakt editora a začať finálny frontend.

Toto poradie minimalizuje riziko, že sa elegantné webové rozhranie postaví nad nesprávnym modelom udalostí alebo nejasnou publikačnou logikou.

---

# 27. Matica trasovania hlavných požiadaviek

| Požiadavka                                        | Primárna etapa | Overenie                                 |
| ------------------------------------------------- | -------------- | ---------------------------------------- |
| Automatický import Google udalostí                | E3             | Calendar integračné testy a shadow sync  |
| Štandardne jeden, architektonicky viac kalendárov | E2, E3         | Dva zdroje v staging fixtures            |
| Konfigurovateľný deň a čas, default Po 20:00      | E4, E6, E7     | DST/unit test a web E2E                  |
| Dvojtýždňové okno                                 | E4             | Hraničné unit testy                      |
| Automatické day emoji a formátovanie              | E4             | Snapshot testy composeru                 |
| Google popis predvolene vypnutý                   | E4, E6         | Policy unit test a editor E2E            |
| Predvyplnenie redakcie Google popisom             | E6             | Formulárový E2E test                     |
| Trvalá úprava konkrétnej udalosti                 | E2, E4         | Sync + composer integračný test          |
| Úprava recurring série od výskytu                 | E2, E3, E4, E6 | Series/instance matica testov            |
| `stop carlo`                                      | E3, E4, E6     | Parser, force-include a E2E test         |
| Manuálne udalosti                                 | E2, E4, E6     | CRUD + composer E2E                      |
| INFO s thumbnailom a expiráciou                   | E2, E4, E6     | Inkluzívna platnosť a image failure test |
| Generovaný úvod                                   | E7             | Model success/fallback test              |
| Presne jedno `@everyone`                          | E4, E7         | Payload integračný test                  |
| Ručný publish a skip termínu                      | E7, E8         | Scheduler E2E                            |
| Admin a SDB / FMA publish                         | E5, E7, E8     | RBAC matica                              |
| Webová administrácia                              | E5, E6, E9     | UAT, Playwright a accessibility          |
| Discord preview                                   | E8             | Command integračný test                  |
| Vytvorenie kanála                                 | E8, E9         | Permission overwrite test                |
| Bezpečná archivácia                               | E8, E9         | Viac paralelných žiadostí                |
| Správa Team Mod/Admin                             | E9             | Role hierarchy E2E                       |
| Seen a auto-reaction emoji                        | E9             | Emoji validation a test reaction         |
| Moderátorské upozornenia                          | E3, E7, E8     | Failure injection test                   |
| Audit a história                                  | E2, E5, E7     | Transakčný integračný test               |
| Migrácia legacy                                   | E10            | Dvojitý dry run a staging import         |
| Bezpečný cutover                                  | E12, E13       | UAT a rollback rehearsal                 |

---

# 28. Register hlavných rizík

| Riziko                                                | Dopad                                   | Preventívne opatrenie                                                   | Reakcia                                                     |
| ----------------------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------- |
| Nesprávna identita recurring výskytu                  | Úprava sa pripojí k nesprávnej udalosti | Google fixtures, stabilný zložený kľúč, konzervatívne matching pravidlá | Zastaviť automatické priradenie a vytvoriť review incident  |
| Pád po odoslaní Discord správy a pred uložením ID     | Možná duplicita                         | Snapshot, message part stav, nonce, sekvenčné ukladanie                 | Reconcile obrazovka; nepublikovať neistú časť automaticky   |
| Súbeh dvoch workerov                                  | Dvojité publikovanie                    | DB unique constraint, transakčný/advisory lock                          | Jeden run odmietnuť a auditovať konflikt                    |
| Zastaraný Calendar sync                               | Neaktuálne oznamy                       | Max cache age, pre-publish sync, health stav                            | Blokovať publish a upozorniť `moderátori`                   |
| Zmena alebo zrušenie udalosti tesne pred publikovaním | Nesprávny draft                         | Finálny sync pred snapshotom                                            | Publikovať až zo snapshotu po úspešnom syncu                |
| Chyba time zone alebo DST                             | Nesprávny termín/okno                   | IANA timezone, centralizovaný časový modul, DST testy                   | Pozastaviť scheduler, opraviť termín administrátorsky       |
| Discord role hierarchy neumožní zmenu                 | Neúspešná moderácia                     | Preflight kontrola a staging konfigurácia                               | Zrozumiteľný error a moderátorský alert                     |
| Neoprávnený priamy API request                        | Bezpečnostný incident                   | Server RBAC pri každom use case, CSRF, session security                 | Zamietnuť, auditovať, invalidovať podozrivú session         |
| User content vytvorí nechcenú zmienku                 | Nechcené upozornenia                    | Sanitizácia a explicitné allowed_mentions                               | Zablokovať draft alebo zmienku neutralizovať                |
| Thumbnail URL zneužije internú sieť                   | SSRF                                    | URL policy, DNS/IP kontrola, izolovaná proxy                            | Odmietnuť obrázok, pokračovať bez thumbnailu                |
| AI úvod zlyhá alebo vytvorí nevhodný text             | Publikácia bez vhodného úvodu           | Verzionovaný prompt, sanitizácia, deterministic fallback                | Použiť fallback a zaznamenať warning                        |
| Legacy event sa nesprávne spáruje s Google eventom    | Strata alebo chybná redakcia            | Iba jednoznačné auto-match, review report                               | Importovať ako manuálny event alebo ručne potvrdiť override |
| Starý a nový bot bežia súčasne                        | Duplicitné správy a reakcie             | Cutover checklist, jediný token owner, vypnutie legacy scheduleru       | Okamžite vypnúť nový worker alebo legacy proces podľa stavu |
| Webový editor je na mobile príliš komplikovaný        | Nízka adopcia                           | Mobile-first wireframe, test s reálnymi používateľmi                    | Upraviť flow pred E6 gate, nie po produkcii                 |
| Rozsah sa počas vývoja nekontrolovane rozšíri         | Nedokončená kritická cesta              | Väzba backlogu na zadanie, oddelený post-v1 backlog                     | Zmenu zaradiť až po dopadovej analýze a schválení           |
| Závislosť alebo externé API sa zmení                  | Výpadok integrácie                      | Zamknuté verzie, adapter testy, sledovanie changelogov                  | Kontrolovaný upgrade v stagingu                             |

---

# 29. Riadenie postupu a zmien rozsahu

## 29.1 Stavový report etapy

Každá etapa má mať krátky report obsahujúci:

- dokončené výstupy,
- nesplnené body kontrolnej brány,
- nové riziká,
- zmeny oproti zadaniu,
- výsledky testov,
- rozhodnutie pokračovať alebo etapu opraviť.

## 29.2 Demonštrácie

Odporúčané povinné demonštrácie:

- po E3 živý Calendar sync s recurrence,
- po E4 rovnaký draft pre web a Discord payload,
- po E6 kompletný mobilný editor,
- po E7 automatický a ručný publish recovery,
- po E9 kompletná webová administrácia,
- po E10 migrovaný staging obsah,
- po E12 výsledok tieňových cyklov.

## 29.3 Zmena rozsahu

Nová požiadavka musí pred zaradením uviesť:

- produktový prínos,
- dotknuté etapy a dátové modely,
- bezpečnostný a migračný dopad,
- nové testy,
- dopad na kritickú cestu,
- či ide o podmienku prvej verzie alebo následný backlog.

Zmena nesmie potichu rozšíriť oprávnenia, publikovaný obsah alebo externý účinok existujúcej funkcie.

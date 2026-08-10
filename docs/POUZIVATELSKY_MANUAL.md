# Používateľský manuál Carla

Carlo pripravuje týždenný prehľad udalostí na najbližších 14 dní. Udalosti
načíta z pripojených Google kalendárov, automaticky ich zoradí, naformátuje a v
nastavenom dni a čase publikuje na Discord. Redakčný zásah je voliteľný.

## Roly

| Rola | Čo môže robiť |
|---|---|
| Team Mod | prezerať draft, upravovať kalendárové udalosti, manuálne udalosti a INFO, vytvárať kanály a žiadať o archiváciu |
| SDB / FMA | prezerať draft a vykonať dvojkrokové ručné publikovanie |
| Admin | všetko vyššie, nastavenia, kalendáre, roly, reakcie, schvaľovanie archivácie, recovery a úplný audit |

Používateľ s viacerými rolami dostane zjednotené oprávnenia. Bežný člen sa do
administrácie neprihlási. Oprávnenie vždy znovu overuje server; skrytá položka
menu nie je bezpečnostným mechanizmom.

## Prihlásenie a navigácia

1. Otvorte HTTPS adresu administrácie a zvoľte prihlásenie cez Discord.
2. Discord musí potvrdiť účet, ktorý je členom správneho servera a má jednu z
   podporovaných rolí.
3. V hornej časti je účet a odhlásenie. Hlavná navigácia obsahuje Prehľad,
   Redakčný pult, Históriu publikácií a Stav systému. Audit a Nastavenia sa
   zobrazia iba rolám, ktoré ich môžu používať.

## Prehľad

Prehľad odpovedá na tri základné otázky: kedy sa bude najbližšie publikovať,
aké 14-dňové okno sa použije a koľko položiek alebo upozornení draft obsahuje.
Tlačidlo do Redakčného pultu otvorí presne najbližší plánovaný balík.

## Redakčný pult

Pult zobrazuje kalendárové, manuálne aj INFO položky na jednom pracovisku a
vedľa nich kanonický Discord náhľad. Zdrojové filtre iba filtrujú zoznam;
nemenia obsah publikácie.

### Kalendárová udalosť

Kliknite na ľubovoľnú hlavnú plochu záznamu alebo na „Upraviť“.

- Titulok aj popis sú voliteľné. Prázdna redakčná hodnota znamená, že Carlo
  použije aktuálne zdrojové pravidlo.
- Ak Google udalosť obsahuje popis, editor ho ponúkne ako počiatočný text novej
  úpravy. Samotné otvorenie formulára nič neuloží.
- Pri opakovanej udalosti vyberte buď iba tento výskyt, alebo tento a všetky
  budúce výskyty.
- Admin môže konkrétny výskyt vylúčiť alebo zaradiť. Udalosť s textom
  `stop carlo` je predvolene vylúčená, ale zostáva viditeľná a Admin ju môže
  zaradiť.
- Ak záznam medzičasom zmenil iný editor, Carlo odmietne prepísanie a vyžiada
  nové načítanie aktuálnej verzie.

Uložená úprava sa viaže na stabilnú identitu výskytu alebo série, preto prežije
ďalšiu synchronizáciu aj druhé oznámenie tej istej udalosti o týždeň neskôr.

### Manuálna udalosť

V pultoch zvoľte pridanie manuálnej udalosti. Vyplňte názov, voliteľný popis a
buď presný začiatok/koniec, alebo prvý a posledný deň celodennej udalosti.
Viacdňová celodenná udalosť sa zobrazuje ako celý inkluzívny rozsah. Carlo ju
zaradí medzi kalendárové udalosti podľa rovnakých pravidiel času.

### INFO oznam

INFO oznam má titulok, text, inkluzívny posledný deň platnosti a voliteľný
obrázok. Obrázok nahrajte priamo zo zariadenia; Carlo ho overí, bezpečne
spracuje a ukáže náhľad. Expirovaný INFO sa už nepublikuje, ale zostáva v
histórii údajov.

## Discord náhľad

Náhľad používa rovnaký kanonický draft ako publisher: rovnaké poradie,
formátovanie, mesačné farby, delenie správ, úvod, `@everyone` a finálny seen
cieľ. Pri bežnom redakčnom náhľade nevzniká skutočný ping ani Discord správa.

## Ručné publikovanie

Ručne publikovať môže iba Admin alebo SDB / FMA.

1. V Nastaveniach alebo príkazom `/publikovat` si pripravte náhľad najbližšieho
   nespracovaného termínu.
2. Skontrolujte termín, cieľový kanál, počet položiek a presný obsah.
3. Potvrďte krátko platným, používateľsky viazaným potvrdením.

Úspešné ručné publikovanie vybaví práve tento termín a scheduler ho už
nezopakuje. Neúspešný alebo neistý pokus termín automaticky nepreskočí a jeho
stav treba skontrolovať v Histórii.

## História publikácií a recovery

História oddeľuje tieňové drafty bez Discord účinku od skutočných publikácií.
Pri každom reálnom rune ukazuje nemenný obsah, pokusy, správy a odkazy na
Discord.

Ak sa pri správe zobrazí neistý stav, iba Admin môže po kontrole cieľového
Discord kanála zvoliť jednu z možností:

- „Prepojiť existujúcu správu“ a zadať jej Discord ID, ak správa vznikla,
- rozbaliť „Správa na Discorde nevznikla“ a potvrdiť opätovné odoslanie danej
  časti, ak v kanáli skutočne nie je.

Nikdy nepotvrdzujte druhú možnosť iba podľa webového stavu; najprv fyzicky
skontrolujte Discord kanál.

## Kanály a archivácia

Team Mod alebo Admin môže v Nastaveniach vytvoriť súkromný projektový kanál,
vybrať povolenú kategóriu, zodpovednú osobu, ďalších členov a roly. Náhľad pred
potvrdením ukáže výsledné prístupy; `@everyone` kanál neuvidí.

Žiadosť o archiváciu vytvorte pre existujúci kanál a uveďte dôvod. Admin ju
schváli alebo zamietne vo webe alebo persistentným tlačidlom v kanáli
moderátorov. Po schválení Carlo kanál premiestni, premenuje a zosynchronizuje s
oprávneniami archívnej kategórie. Rozpracovanú archiváciu možno v Nastaveniach
bezpečne obnoviť bez vytvorenia druhej operácie.

## Roly

Admin vyberie člena a udelí alebo odoberie iba aplikačné roly Team Mod a Admin.
Carlo pred zmenou overí Discord hierarchy aj oprávnenie bota a po zmene načíta
skutočný stav z Discordu. Posledného Admina spravujúceho aplikáciu nemožno
odobrať.

## Reakcie

Admin samostatne nastavuje:

- seen reakciu na poslednej správe prehľadu,
- reakciu pri označení Carla,
- automatickú reakciu a zoznam kanálov.

Každá voľba podporuje Unicode alebo dostupné serverové emoji. Pred uložením ju
možno vyskúšať v zvolenom kanáli. Chyba seen reakcie neznamená, že textová
publikácia zlyhala; História na to upozorní samostatne.

## Kalendáre a publikačný rozvrh

Admin môže pridať viac read-only Google kalendárov, meniť ich aktivitu a
prioritu a sledovať poslednú synchronizáciu. V spoločných Nastaveniach určuje
deň, čas, časové pásmo, cieľový kanál, moderátorský kanál, kategórie a politiku
Google popisov. Predvolený termín je pondelok o 20:00 v
`Europe/Bratislava`.

Voľbu „Núdzovo použiť posledné dáta kalendára“ zapínajte iba vedome. Pri
zlyhaní povinnej finálnej synchronizácie Carlo štandardne publikovanie
zablokuje. Táto voľba dovolí použiť iba ešte bezpečne čerstvú cache a vytvorí
audit aj moderátorské upozornenie.

## Discord príkazy

- `/nahlad` – bezpečný ephemeral náhľad bez funkčného everyone pingu,
- `/publikovat` – dvojkrokové ručné publikovanie pre Admina a SDB / FMA,
- `/kanal` – interaktívne vytvorenie súkromného projektového kanála,
- `/archivovat` – žiadosť o archiváciu aktuálneho kanála.

Príkaz vždy použije aktuálne Discord roly; samotná viditeľnosť príkazu
negarantuje oprávnenie na operáciu.

## Stav systému a audit

Stav systému zobrazuje pripojenie bota, worker a jeho režim, Calendar zdroje,
najbližší termín, publikačné metriky a posledné integračné úlohy. Pri hlásení
problému uveďte korelačné ID, nie tajomstvá ani celé interné logy.

Audit zaznamenáva citlivé zmeny. Team Mod vidí redakčné, kanálové a archivačné
operácie v povolenom rozsahu; Admin vidí úplný audit svojho servera.

# Zadanie: Carlo (nová verzia Domček bota)

## 1. Účel dokumentu

Tento dokument definuje produktové, funkčné a technické zadanie úplne novej verzie Discord bota Domček. Nová verzia nemá byť iba úpravou existujúceho kódu, ale jeho premysleným nahradením riešením, ktoré:

- automaticky pripravuje týždenný prehľad udalostí z Google Kalendára,
- umožňuje administrátorom upraviť výsledný obsah bez povinnej manuálnej prípravy,
- zachováva úpravy udalosti aj medzi dvoma po sebe nasledujúcimi týždennými publikovaniami,
- oddeľuje bežné Discord príkazy od administrácie,
- poskytuje elegantné, responzívne a bezpečné webové administračné rozhranie,
- spoľahlivo plánuje a publikuje oznamy bez duplicít,
- odstraňuje známe nedostatky pôvodného riešenia v oprávneniach, práci s dátumami, validácii, archivácii, chybových stavoch a prevádzke.

Dokument má slúžiť ako podklad pre návrh architektúry, odhad prác, implementáciu, testovanie a akceptáciu výsledného riešenia.

## 1.1 Nemenné pravidlo kontinuity – `STATUS.md`

Počas celej implementácie musí súbor [`STATUS.md`](./STATUS.md) vždy pravdivo odrážať aktuálny stav aplikácie a projektu.

Toto je absolútne nemenné pravidlo implementácie:

- každé pridanie, úprava, odstránenie, migrácia, rozhodnutie, test, oprava, zistený problém alebo zmena smerovania, ktorá vznikne v rámci implementácie, musí byť v tom istom pracovnom kroku premietnutá do `STATUS.md`,
- žiadna implementačná úloha sa nepovažuje za dokončenú, kým nie je zodpovedajúcim spôsobom aktualizovaný `STATUS.md`,
- `STATUS.md` musí rozlišovať dokončené, rozpracované, nezačaté a blokované práce a nesmie označovať plánovaný alebo iba čiastočne overený výsledok ako hotový,
- `STATUS.md` musí obsahovať posledné vykonané zmeny, aktuálnu etapu, najbližšie konkrétne kroky, otvorené problémy, blokátory, vykonané overenia a relevantný stav pracovného stromu,
- po kompaktovaní alebo strate predchádzajúceho konverzačného kontextu je prvým povinným krokom prečítať `ZADANIE.md`, `PLAN_IMPLEMENTACIE.md` a `STATUS.md`; až potom možno pokračovať v práci,
- pri rozpore medzi pamäťou konverzácie a aktuálnym obsahom repozitára sa musí najprv overiť skutočný stav súborov a následne opraviť `STATUS.md`,
- pravidlo nemožno počas implementácie odstrániť, oslabiť, obísť ani dočasne ignorovať.

Aktualizácia `STATUS.md` je súčasťou definície hotového výsledku každej jednotlivej úlohy, každej etapy aj celej implementácie.

---

## 2. Produktový cieľ

Primárnym cieľom je odstrániť potrebu každý týždeň ručne prepisovať udalosti z kalendára do Discord oznamov.

Za normálnych okolností musí bot vedieť vykonať celý proces bez zásahu používateľa:

1. načítať udalosti z určeného Google Kalendára,
2. vybrať udalosti patriace do nasledujúceho dvojtýždňového obdobia,
3. správne ich zoradiť,
4. vytvoriť názvy, dátumy, časy, označenia dní a vizuálne formátovanie,
5. doplniť uložené redakčné úpravy,
6. zahrnúť platné manuálne udalosti a informačné oznamy,
7. zostaviť presný náhľad výslednej publikácie,
8. v nakonfigurovaný deň a čas prehľad automaticky zverejniť,
9. uložiť históriu toho, čo bolo skutočne publikované,
10. upozorniť oprávnené osoby, ak publikovanie nie je možné bezpečne dokončiť.

Používateľský zásah má byť voliteľnou redakčnou nadstavbou, nie podmienkou fungovania systému.

---

## 3. Základné pojmy

### 3.1 Kalendárová udalosť

Udalosť načítaná z nakonfigurovaného Google Kalendára. Google Kalendár je autoritatívnym zdrojom jej dátumu, času, celodenného charakteru, stavu a základného názvu.

### 3.2 Redakčná úprava udalosti

Trvalo uložená používateľská úprava titulku alebo popisu kalendárovej udalosti. Môže patriť konkrétnemu výskytu alebo tomuto a všetkým budúcim výskytom opakovanej série. Nie je novou kópiou udalosti a nemení údaje v Google Kalendári.

### 3.3 Manuálna udalosť

Udalosť vytvorená vo webovej administrácii, ktorá sa nenachádza v Google Kalendári. V dvojtýždňovom prehľade sa správa rovnako ako kalendárová udalosť.

### 3.4 INFO oznam

Ručne vytvorený informačný oznam bez povinnej väzby na konkrétny čas udalosti. Má vlastné obdobie platnosti a môže obsahovať thumbnail a odkaz.

### 3.5 Publikačný termín

Konkrétny plánovaný okamih týždenného zverejnenia. Deň aj čas sú konfigurovateľné; predvolená hodnota je pondelok o 20:00 v časovom pásme `Europe/Bratislava`.

### 3.6 Publikačný balík

Presná zostava úvodu, INFO oznamov, udalostí a záverečnej výzvy, ktorá patrí jednému publikačnému termínu.

### 3.7 Náhľad najbližších oznamov

Aktuálne vypočítaná podoba publikačného balíka patriaceho najbližšiemu ešte nespracovanému publikačnému termínu. Náhľad musí zodpovedať tomu, čo by systém pri nezmenených vstupoch zverejnil.

---

## 4. Rozsah novej verzie

Nová verzia musí obsahovať najmenej tieto funkčné celky:

1. integráciu s Google Kalendárom,
2. automatické zostavenie dvojtýždňového prehľadu,
3. redakčný editor oznamov vo webovej administrácii,
4. správu manuálnych udalostí,
5. správu INFO oznamov,
6. spoľahlivé plánované a ručné publikovanie,
7. Discord náhľad najbližších oznamov,
8. vytváranie a archivovanie Discord kanálov,
9. správu rolí Team Mod a Admin a podporu publikačného oprávnenia roly SDB / FMA,
10. nastavenie automatických reakcií a seen emoji,
11. autentifikáciu a autorizáciu webovej administrácie,
12. históriu publikácií a audit administrátorských zmien,
13. upozornenia na zlyhania a prevádzkový stav,
14. migráciu relevantných údajov z pôvodnej verzie,
15. automatizované testy a dokumentované nasadenie.

---

# 5. Automatický model oznamov

## 5.1 Publikačný harmonogram

Deň v týždni aj čas publikovania musia byť konfigurovateľné vo webovej administrácii. Predvolený harmonogram je každý pondelok o 20:00.

Zmena harmonogramu ovplyvní budúce publikačné termíny. Už úspešne spracovaný termín a história publikácií sa spätne nemenia. Rozhranie musí pred uložením zmeny jasne ukázať nový najbližší termín.

Všetky plánovacie a dátumové operácie musia explicitne používať časové pásmo `Europe/Bratislava` a správne zohľadňovať prechod medzi letným a zimným časom. Čas servera alebo databázy nesmie implicitne určovať produktové správanie.

Každý publikačný termín musí mať vlastný stabilný identifikátor a stav, napríklad:

- pripravovaný,
- publikovanie prebieha,
- úspešne publikovaný automaticky,
- úspešne publikovaný ručne,
- preskočený z dôvodu predchádzajúceho ručného publikovania,
- zlyhaný,
- čakajúci na opakovanie.

## 5.2 Dvojtýždňové publikačné okno

Prehľad obsahuje udalosti v najbližších 14 dňoch vzhľadom na publikačný termín.

Normatívna definícia okna je:

```text
[publikačný termín, publikačný termín + 14 dní)
```

Začiatok je zahrnutý a koniec nie je zahrnutý. Porovnanie sa vykonáva v časovom pásme `Europe/Bratislava`.

Pri celodenných udalostiach sa používa lokálny kalendárny dátum. Celodenná udalosť sa zahrnie, ak sa aspoň jej začiatok nachádza v publikačnom okne. Viacdňové udalosti, ktoré začali pred začiatkom okna, ale stále počas okna trvajú, musia byť zahrnuté tiež.

Hranice okna musia byť implementované jedným spoločným pravidlom používaným náhľadom, webovým editorom, automatickým publikovaním aj ručným publikovaním.

## 5.3 Zdrojové kalendáre

Štandardná konfigurácia používa jeden Google kalendár. Dátový model, integračná vrstva a webová administrácia však musia umožniť nakonfigurovať aj viac Google kalendárov bez zmeny základnej architektúry. Pre každý zdroj sa eviduje najmenej:

- stabilný identifikátor kalendára,
- zobrazovaný názov,
- aktívny/neaktívny stav,
- prípadné poradie alebo priorita,
- informácia o poslednej úspešnej synchronizácii,
- informácia o poslednej chybe synchronizácie.

Prvá verzia môže používať samostatný Google účet alebo service account, ktorému vlastník kalendára poskytne prístup. Prihlasovacie údaje nesmú byť dostupné v prehliadači ani uložené v zdrojovom kóde.

## 5.4 Synchronizácia s Google Kalendárom

Systém musí:

- pravidelne synchronizovať potrebné budúce udalosti,
- synchronizovať udalosti pri otvorení editora alebo umožniť oprávnenému používateľovi vyvolať obnovenie,
- bezprostredne pred publikovaním vykonať poslednú kontrolnú synchronizáciu,
- podporovať stránkovanie výsledkov Google Calendar API,
- korektne spracovať zrušené a odstránené udalosti,
- korektne spracovať aktualizáciu času, názvu alebo popisu udalosti,
- korektne spracovať opakované udalosti a ich jednotlivé výskyty,
- odolávať dočasným chybám pomocou časovo obmedzených opakovaných pokusov,
- zaznamenať čas a výsledok každej synchronizácie.

Odporúčané je používať prírastkovú synchronizáciu pomocou synchronizačného tokenu poskytovateľa. Úplná synchronizácia musí byť dostupná ako opravný mechanizmus pri strate alebo expirácii tokenu.

## 5.5 Identita udalosti

Redakčné úpravy sa nesmú viazať na názov ani čas udalosti. Tie sa môžu v kalendári meniť.

Každá kalendárová udalosť musí byť identifikovaná stabilným zloženým kľúčom zahŕňajúcim minimálne:

- zdrojového poskytovateľa,
- identifikátor kalendára,
- identifikátor udalosti od poskytovateľa,
- pri opakovanej udalosti identitu konkrétneho výskytu, ak ju poskytovateľ vyžaduje.

Ak sa tá istá konkrétna udalosť objaví v dvoch po sebe nasledujúcich dvojtýždňových prehľadoch, musí mať v oboch rovnakú internú identitu. Uložený vlastný titulok a popis sa preto automaticky použijú aj pri druhom publikovaní.

Presunutie udalosti na iný čas nesmie samo osebe zrušiť jej redakčné úpravy, pokiaľ Google zachová identitu udalosti.

## 5.6 Výber udalostí

Do prehľadu sa zahŕňajú aktívne udalosti zo zapnutých kalendárov, ktoré časovo patria do publikačného okna.

Vylúčiť sa musia minimálne:

- zrušené udalosti,
- odstránené udalosti,
- neplatné alebo neúplné záznamy, ktoré nie je možné bezpečne zobraziť.

Pri udalosti bez názvu sa použije jasne definovaný náhradný názov a v administrácii sa zobrazí upozornenie.

Kalendárovú udalosť možno z publikácie vylúčiť dvoma spôsobmi:

1. administrátor ju vo webovom editore explicitne označí ako nezahrnutú,
2. zdrojový popis udalosti v Google Kalendári obsahuje riadiacu frázu `stop carlo`.

Fráza `stop carlo` sa vyhodnocuje bez ohľadu na veľkosť písmen ako samostatná riadiaca fráza. Vo výslednom verejnom popise sa nikdy nezobrazuje.

Aj automaticky vylúčená udalosť zostáva viditeľná vo webovom editore. Musí byť jasne označená dôvodom vylúčenia. Administrátor pri nej môže upraviť verejný titulok alebo popis a použiť akciu „Zaradiť napriek `stop carlo`“.

Priorita rozhodnutí je:

```text
explicitné ručné zaradenie/vylúčenie administrátorom
> automatické vylúčenie pomocou „stop carlo“
> štandardné zaradenie podľa kalendára a publikačného okna
```

Redakčná úprava textu sama osebe nemení zdrojový popis ani automaticky neodstraňuje príznak `stop carlo`; zaradenie napriek tomuto príznaku musí byť explicitné a auditované.

## 5.7 Automaticky odvodené údaje

Bot musí z údajov udalosti automaticky odvodiť:

- deň v týždni v slovenčine,
- príslušné day emoji alebo ikonu,
- lokálny dátum,
- lokálny čas,
- informáciu, že ide o celodennú udalosť,
- časový rozsah pri udalosti s koncom,
- formát viacdňovej udalosti,
- správne poradie medzi ostatnými udalosťami.

Používateľ nesmie ručne zadávať deň v týždni ani formátovaný dátum kalendárovej udalosti.

Vizuálny štýl má zachovať doterajší model event oznamu: dátum a čas sa zobrazujú v hornej autorovej časti embed karty spolu s ikonou dňa, pod nimi je titulok a voliteľný popis. Jednodňová časovaná udalosť používa formát zodpovedajúci doterajšiemu `DD.MM. // HH:MM`; celodenná udalosť zobrazí dátum bez času a viacdňová udalosť zrozumiteľný rozsah začiatku a konca v rovnakej vizuálnej logike. Presné slovenské texty sa centralizujú v spoločnom formátovači.

## 5.8 Triedenie

Poradie publikačného balíka je:

1. platné INFO oznamy,
2. udalosti zoradené vzostupne podľa začiatku,
3. pri rovnakom začiatku podľa konfigurovateľnej priority kalendára,
4. následne stabilne podľa titulku a interného identifikátora.

Celodenné udalosti daného dňa sa zobrazia pred časovanými udalosťami toho istého dňa, ak produktové nastavenie neurčí inak.

Triedenie musí byť deterministické: rovnaké vstupné údaje musia vždy vytvoriť rovnaké poradie.

---

# 6. Redakčné úpravy kalendárových udalostí

## 6.1 Rozsah povolených úprav

Oprávnený používateľ môže vo webovom editore zmeniť:

- verejný titulok udalosti,
- verejný popis udalosti.

Explicitné vylúčenie udalosti alebo jej zaradenie napriek `stop carlo` je rozhodnutie vyhradené Adminovi. Team Mod môže vykonávať obsahové redakčné úpravy, ale nemôže meniť toto publikačné rozhodnutie.

Nemôže týmto editorom meniť dátum, čas ani stav kalendárovej udalosti. Tieto údaje patria Google Kalendáru. Ak je potrebné zmeniť čas, musí sa zmeniť v kalendári.

Editor musí jasne rozlišovať:

- pôvodný titulok a popis z Google Kalendára,
- aktuálne použitý verejný titulok a popis,
- informáciu, že ide o vlastnú redakčnú úpravu.

## 6.2 Priorita údajov

Pre titulok platí:

```text
vlastný redakčný titulok > titulok z Google Kalendára > bezpečný náhradný titulok
```

Predvolene sa automaticky publikuje iba titulok udalosti a prípadný vlastný redakčný popis. Zdrojový popis z Google Kalendára sa bez ďalšieho nastavenia automaticky nepublikuje.

Administrátor môže v globálnom nastavení zapnúť automatické používanie popisov z Google Kalendára. Pre výsledný popis potom platí:

```text
vlastný redakčný popis
> popis z Google Kalendára, ak je jeho publikovanie globálne povolené
> žiadny popis
```

Bez ohľadu na globálne nastavenie musí editor pri začatí redakčnej úpravy predvyplniť textové pole popisom z Google Kalendára, ak existuje. Samotné otvorenie formulára alebo jeho zrušenie nesmie vytvoriť redakčnú úpravu. Zdrojový popis sa stane vlastným redakčným popisom až po vedomom uložení používateľom.

Vlastný titulok alebo popis je voliteľný a ukladá sa samostatne od zdrojových údajov. Používateľ musí vedieť vlastnú úpravu odstrániť a vrátiť sa k automatickému správaniu.

Prázdny vlastný popis a neexistujúca vlastná hodnota nesmú byť technicky zameniteľné. Systém musí vedieť rozlíšiť:

- „zdedi globálne správanie pre popis z kalendára“,
- „použi vlastný redakčný popis“,
- „zámerne publikuj bez popisu“.

## 6.3 Trvanie úprav

Úpravy sa ukladajú k identite udalosti, nie k jednému publikačnému termínu. Zostávajú platné:

- pri opakovanom zobrazení editora,
- pri opätovnej synchronizácii,
- pri druhom týždennom publikovaní tej istej udalosti,
- pri zmene základného názvu alebo času v Google Kalendári,
- po reštarte aplikácie.

Publikačná história si zároveň musí uchovať presný titulok a popis použitý v každej už zverejnenej správe. Neskoršia úprava nesmie spätne meniť históriu.

## 6.4 Opakované udalosti a rozsah úpravy

Predvolená redakčná úprava sa viaže iba na konkrétny výskyt opakovanej udalosti.

Ak Google udalosť patrí do opakovanej série, editor musí pri ukladaní ponúknuť rozsah zmeny:

- iba tento výskyt,
- tento a všetky budúce výskyty série.

Ak používateľ zvolí všetky budúce výskyty, systém vytvorí pravidlo série s účinnosťou od upravovaného výskytu. Minulé publikované výskyty a ich história sa nemenia.

Ak už udalosť používa redakčnú hodnotu zdedenú zo série a používateľ ju mení, editor musí znovu ponúknuť rozhodnutie:

- zmeniť iba tento výskyt a vytvoriť výnimku,
- zmeniť tento a všetky nasledujúce výskyty od daného dátumu.

Priorita redakčných hodnôt opakovanej udalosti je:

```text
úprava konkrétneho výskytu
> najnovšie účinné pravidlo série
> automatická hodnota podľa globálnych nastavení
```

Rozsah možno zvoliť samostatne pre zmenené redakčné údaje. Rozhranie musí pred uložením jednoznačne uviesť, koľkých budúcich známych výskytov sa zmena dotkne. Zmeny titulku aj popisu musia podporovať rovnaký mechanizmus.

## 6.5 Súbeh zmien

Ak tú istú udalosť upravujú dvaja používatelia, systém nesmie bez upozornenia prepísať novšiu zmenu staršími údajmi. Má použiť optimistické zamykanie alebo ekvivalentnú kontrolu verzie.

Pri konflikte musí webové rozhranie používateľovi zobraziť aktuálnu hodnotu a umožniť mu rozhodnúť sa, či úpravu zopakuje.

Každá zmena sa zaznamená do auditu s pôvodnou a novou hodnotou.

---

# 7. Manuálne udalosti

## 7.1 Účel

Webová administrácia musí umožniť vytvoriť udalosť, ktorá nie je v Google Kalendári, ale má sa zaradiť medzi automatické udalosti.

## 7.2 Povinné a voliteľné údaje

Manuálna udalosť obsahuje najmenej:

- titulok,
- začiatok,
- voliteľný koniec,
- príznak celodennej udalosti,
- voliteľný popis,
- voliteľný odkaz,
- aktívny/neaktívny stav,
- autora a časy vytvorenia a poslednej zmeny.

Deň v týždni, formátovaný dátum a day emoji sa odvádzajú automaticky rovnako ako pri kalendárovej udalosti.

## 7.3 Zaraďovanie a opakovanie

Manuálna udalosť sa zaradí do každého publikačného balíka, ktorého dvojtýždňové okno ju obsahuje. Ak sa preto objaví v dvoch týždňoch, použije sa ten istý uložený obsah bez vytvorenia kópie.

Po skončení udalosti sa prestane objavovať v budúcich balíkoch, ale zostane dostupná v histórii publikácií a audite.

## 7.4 Správa

Používateľ musí vedieť manuálnu udalosť:

- vytvoriť,
- upraviť,
- deaktivovať,
- odstrániť s potvrdením, ak ešte nebola publikovaná.

Pri už publikovanej udalosti sa preferuje deaktivácia alebo mäkké odstránenie, aby zostala zachovaná história.

---

# 8. INFO oznamy

## 8.1 Zachovaná funkcionalita

INFO oznamy sa nenačítavajú z Google Kalendára. Vytvárajú sa výhradne vo webovej administrácii.

INFO oznam obsahuje:

- titulok,
- popis,
- voliteľný odkaz,
- voliteľný obrázok alebo thumbnail,
- začiatok platnosti,
- koniec platnosti,
- aktívny/neaktívny stav,
- autora a časové údaje zmien.

## 8.2 Platnosť

Platnosť sa vyhodnocuje podľa kalendárnych dátumov v `Europe/Bratislava`. Koncový deň je zahrnutý celý. Oznam s koncom platnosti `8. 8. 2026` je platný až do konca tohto lokálneho dňa.

Expirovaný INFO oznam sa nesmie automaticky fyzicky vymazať. Má sa označiť ako expirovaný a zostať dostupný pre históriu a prípadnú obnovu.

## 8.3 Obrázky

Používateľ nepridáva adresu obrázka. Obrázok nahrá priamo v editore INFO oznamu potiahnutím alebo výberom súboru a ihneď vidí spracovaný náhľad. Existujúci obrázok môže nahradiť alebo odobrať.

Server musí overiť skutočný obsah súboru, odmietnuť nepodporované a animované formáty, odstrániť metadáta, opraviť orientáciu, primerane zmenšiť rozmery a uložiť výsledok vo formáte vhodnom pre web aj Discord. Povolené vstupy sú JPEG, PNG a WebP do 8 MB. SVG sa neprijíma.

Spracovaný obrázok sa ukladá do trvalého serverového úložiska pod náhodne vytvoreným názvom. Jeho verejná adresa musí byť dostupná Discordu. Nefunkčný obrázok nesmie zablokovať publikovanie celého balíka.

Ak sa používa proxy služba pre náhľady, musí byť konfigurovateľná, monitorovaná a nesmie umožňovať zneužitie na neoprávnený prístup k interným sieťovým adresám.

---

# 9. Editor najbližších oznamov

## 9.1 Základné správanie

Po otvorení editora používateľ uvidí presne ten obsah, ktorý patrí najbližšiemu ešte nespracovanému publikačnému termínu podľa aktuálne nastaveného dňa a času.

Editor musí zobraziť:

- dátum a čas plánovaného publikovania,
- začiatok a koniec dvojtýždňového okna,
- čas poslednej synchronizácie s Google Kalendárom,
- prípadné upozornenie na neaktuálne alebo neúplné údaje,
- platné INFO oznamy,
- kalendárové udalosti,
- manuálne udalosti,
- ich finálne poradie,
- verný vizuálny náhľad Discord publikácie.

## 9.2 Operácie v editore

Pri kalendárovej udalosti možno:

- pridať alebo upraviť verejný titulok,
- pridať alebo upraviť verejný popis,
- zrušiť vlastnú hodnotu a vrátiť sa k automatickému správaniu,
- zvoliť rozsah úpravy opakovanej udalosti,
- ak je používateľ Admin, explicitne ju vylúčiť z publikácie,
- ak je používateľ Admin, explicitne ju zaradiť napriek zdrojovej fráze `stop carlo`.

V editore musí byť zároveň možné:

- vytvoriť manuálnu udalosť,
- upraviť manuálnu udalosť,
- vytvoriť alebo upraviť INFO oznam,
- obnoviť údaje z kalendára,
- otvoriť plný náhľad,
- spustiť ručné publikovanie s potvrdením.

Uloženie jednej úpravy nesmie vyžadovať opätovné vyplnenie alebo uloženie celého balíka.

## 9.3 Vernosť náhľadu

Webový náhľad musí používať rovnaké pravidlá a rovnaký výsledný zobrazovací model ako Discord publikovanie. Nemajú existovať dve nezávislé implementácie formátovania.

Náhľad nesmie dopĺňať vymyslený názov, popis kanála ani iný obsah, ktorý Carlo
v skutočnosti nepublikuje. Zachová sa pôvodná mesačná farebná paleta: INFO
embedy používajú jemný odtieň mesiaca a kalendárové aj manuálne udalosti jeho
sýty odtieň. Farba je súčasťou kanonického publikačného modelu, nie iba
dekorácia webového náhľadu.

Náhľad musí upozorniť na limity Discordu, príliš dlhý text, neplatný odkaz alebo chýbajúci obrázok ešte pred publikovaním.

---

# 10. Publikovanie

## 10.1 Automatické publikovanie

V nastavenom týždennom termíne systém:

1. získa distribuovaný alebo databázový zámok pre daný publikačný termín,
2. overí, že termín ešte nebol vybavený,
3. vykoná poslednú synchronizáciu Google Kalendára,
4. zostaví publikačný balík,
5. uloží nemenný snapshot balíka,
6. odošle obsah do nakonfigurovaného Discord kanála,
7. uloží identifikátory všetkých odoslaných správ,
8. pridá seen emoji na určenú záverečnú správu,
9. až po úplnom úspechu označí termín ako publikovaný.

Ak proces zlyhá uprostred odosielania, musí poznať už odoslané časti a nesmie pri opakovaní bezhlavo zdvojiť celý obsah. Stav musí umožniť bezpečné dokončenie, riadené opakovanie alebo administrátorské rozhodnutie.

## 10.2 Ručné publikovanie a preskočenie termínu

Ručné publikovanie cez Discord príkaz alebo webovú administráciu publikuje balík patriaci najbližšiemu ešte nespracovanému publikačnému termínu.

Po úspešnom ručnom publikovaní sa tento konkrétny termín označí ako vybavený ručne. Keď nastane jeho pôvodný nakonfigurovaný čas, automatická úloha ho rozpozná a nič ďalšie neodošle.

Ručné publikovanie:

- môže vykonať iba Admin alebo člen roly `SDB / FMA`,
- nevypína budúci týždenný rozvrh,
- nepreskakuje viac ako jeden najbližší termín,
- pri zlyhaní neoznačí termín za vybavený,
- vyžaduje zobrazenie cieľového termínu, kanála a náhľadu,
- vyžaduje explicitné potvrdenie oprávneného používateľa,
- musí byť idempotentné voči opakovanému kliknutiu alebo opakovanému príkazu.

Ak je termín už publikovaný, systém nesmie vytvoriť duplicitu obyčajným opakovaním. Prípadné nútené opätovné publikovanie musí byť oddelená administrátorská operácia s výrazným upozornením a auditom.

## 10.3 Rozdelenie do Discord správ

Systém nesmie predpokladať, že sa celý balík zmestí do jednej správy alebo desiatich embedov.

Musí:

- rešpektovať aktuálne limity Discord API,
- rozdeliť obsah do viacerých správ,
- zachovať poradie,
- použiť `@everyone` presne raz v úvode úspešnej publikácie,
- pridať seen emoji iba na jasne určenú záverečnú správu,
- uložiť všetky identifikátory odoslaných správ.

## 10.4 Úvod a záver

Publikácia musí zachovať automaticky generovaný úvod a podporovať konfigurovateľnú záverečnú výzvu na potvrdenie prečítania. Úvod osloví komunitu pomocou `@everyone`.

Pre generovanie úvodu jazykovým modelom platí:

- existuje deterministická náhradná šablóna,
- zlyhanie generovania nezablokuje udalosti,
- vygenerovaný text sa uloží do snapshotu publikácie,
- používateľ v náhľade vie rozlíšiť pracovný a finálny úvod,
- okrem riadeného `@everyone` nesmie generovaný text vytvárať ďalšie Discord zmienky,
- povolené zmienky sa riadia explicitným zoznamom, nie náhodným textom modelu.

Použitie jazykového modelu zostáva súčasťou finálneho publikačného toku, ale nie je závislosťou samotného načítania, editovania a formátovania udalostí.

## 10.5 Nedostupnosť Google Kalendára

Pri dočasnej nedostupnosti možno použiť poslednú úspešne synchronizovanú lokálnu kópiu iba vtedy, ak je mladšia než konfigurovateľný bezpečnostný limit a administrátor vopred povolil takýto režim.

Ak nie sú dostupné dostatočne čerstvé údaje:

- publikovanie sa nesmie označiť za úspešné,
- oprávnené osoby dostanú upozornenie,
- systém vykoná obmedzené opakované pokusy,
- vo webovej administrácii bude viditeľný chybový stav a možnosť nápravy.

---

# 11. Discord príkazy

Discord príkazy majú zostať úmyselne obmedzené na každodenné operácie. Kompletná konfigurácia a redakčná administrácia nepatria do Discord príkazov.

## 11.1 Povinné príkazy

### Vytvorenie kanála

Príkaz vytvorí súkromný textový kanál a umožní zadať:

- názov,
- emoji,
- používateľov,
- voliteľné roly.

Musí používať natívny Discord výber používateľov a rolí, nie parsovanie textových označení. Pred vytvorením zobrazí alebo jednoznačne potvrdí výsledné oprávnenia.

### Archivácia kanála

Príkaz sa používa v archivovanom kanáli a prijíma dôvod archivácie. Dátum má doplniť bot automaticky; používateľ ho nemá písať ručne.

Administrátor môže archivovať priamo. Team Mod vytvorí schvaľovaciu žiadosť. Každá žiadosť musí byť jednoznačne viazaná na:

- server,
- kanál,
- žiadateľa,
- konkrétnu schvaľovaciu správu alebo databázový záznam,
- stav a čas platnosti.

Schválenie jednej žiadosti nesmie ovplyvniť inú žiadosť. Musí existovať explicitné schválenie aj zamietnutie.

### Náhľad najbližších oznamov

Príkaz zobrazí náhľad balíka pre najbližší publikačný termín. Pri väčšom obsahu ho bezpečne rozdelí alebo poskytne súkromný odkaz do webovej administrácie.

Náhľad nesmie byť verejný. Zobraziť ho môže iba používateľ s oprávnením na náhľad podľa autorizačnej matice; samotné oprávnenie na náhľad neudeľuje právo ručne publikovať.

### Ručné zverejnenie

Príkaz spustí ručné publikovanie podľa pravidiel v kapitole 10.2. Musí zobrazovať jednoznačné potvrdenie a výsledok. Potvrdenie môže vykonať iba používateľ, ktorý operáciu spustil, prípadne iný administrátor s explicitne zaznamenaným prevzatím operácie.

## 11.2 Odstránené administračné príkazy

Do Discordu nepatria samostatné príkazy na:

- vytváranie a úpravu INFO oznamov,
- úpravu titulkov a popisov udalostí,
- nastavenie harmonogramu,
- nastavenie emoji,
- správu kanálov automatických reakcií,
- nastavenie moderátorského kanála a kategórií upozornení,
- konfiguráciu Google Kalendára,
- udeľovanie rolí.

Tieto operácie sa vykonávajú vo webovej administrácii.

## 11.3 Oprávnenia príkazov

Oprávnenia musia byť kontrolované v aplikačnom kóde podľa stabilných identifikátorov rolí. Nastavenie viditeľnosti príkazov v Discorde je doplnková ochrana, nie jediná ochrana.

Každé tlačidlo, formulár a potvrdenie musí znovu overiť oprávnenie a identitu používateľa v čase vykonania operácie.

---

# 12. Webová administrácia

## 12.1 Všeobecné požiadavky

Webová administrácia musí byť:

- vizuálne elegantná a konzistentná,
- prehľadná aj pre menej technického používateľa,
- plne responzívna pre počítač, tablet aj mobil,
- ovládateľná klávesnicou,
- prístupná podľa WCAG 2.1 AA v relevantnom rozsahu,
- použiteľná bez horizontálneho posúvania pri bežných mobilných šírkach,
- vybavená jasnými stavmi načítania, úspechu, chyby a prázdneho obsahu,
- chránená pred neúmyselnými deštruktívnymi operáciami,
- konzistentná v slovenskom jazyku.

Rozhranie nesmie používateľovi zobrazovať interné identifikátory ako hlavný spôsob navigácie. Má používať názvy, dátumy, mená a zrozumiteľné stavy.

Redakčný pult využíva dostupný pracovný priestor veľkého monitora a nesmie byť
obmedzený rovnakou úzkou maximálnou šírkou ako bežný dashboard. Na širokom
desktope sa primerane rozšíria zoznam aj Discord náhľad a pracovná plocha využije
aj dostupnú výšku, ale jej spodný okraj musí zostať viditeľný bez rolovania celej
stránky. Dlhý obsah sa roluje vo vnútornom zozname alebo náhľade. Pri zmenšení
sa panely plynulo skladajú podľa wireframov.

Kliknutie na hlavnú obsahovú plochu upraviteľného záznamu otvorí rovnaký editor
ako tlačidlo „Upraviť“. Celý tento cieľ musí byť dostupný aj klávesnicou, mať
zrozumiteľný prístupný názov a viditeľný fokus. Tlačidlo „Upraviť“ zostáva
zachované kvôli jednoznačnému objaveniu funkcie.

Vytváranie a redakcia oznamov a manuálnych udalostí prebiehajú v sústredenom centrovanom modálnom okne, nie v bočnom paneli. Modal musí mať na menších displejoch bezpečne rolovateľný obsah, stále dostupné akcie, správne riadenie fokusu a zabrániť interakcii s obsahom pod ním.

## 12.2 Odporúčaná informačná architektúra

### Dashboard

Dashboard zobrazuje najmenej:

- najbližší publikačný termín,
- stav automatického publikovania,
- počet udalostí a INFO oznamov v najbližšom balíku,
- čas poslednej úspešnej synchronizácie,
- prípadné chyby alebo upozornenia,
- poslednú úspešnú publikáciu,
- čakajúce žiadosti o archiváciu,
- rýchly vstup do editora a náhľadu.

### Redakčný pult

Redakčný pult je jediné primárne pracovisko na prípravu oznamov. Kalendárové udalosti, manuálne udalosti a INFO oznamy nesmú pôsobiť ako tri oddelené administrácie, medzi ktorými musí používateľ neustále prepínať.

Na desktope má pracovisko charakter sústredenej pracovnej aplikácie a súčasne zobrazuje:

- zrozumiteľne pomenované zdroje a filtre obsahu,
- spoločný zoznam položiek z najbližšieho prehľadu,
- zdroj, termín a publikačný stav každej položky,
- úpravy všetkých podporovaných typov obsahu z toho istého pracoviska,
- verný výsledok správ tak, ako ich odošle Carlo do Discordu.

Počet položiek v najbližšom prehľade musí zahŕňať všetky zdroje. Samostatný počet Google udalostí je iba filtrom zdroja a nesmie sa prezentovať spôsobom, ktorý by vytváral dojem, že celý prehľad je prázdny. Prázdne stavy musia výslovne vysvetliť, ktorého zdroja sa týkajú.

Samostatné routy pre manuálne udalosti a INFO oznamy nie sú súčasťou primárnej navigácie. Ich pôvodné adresy môžu zostať iba ako spätné presmerovanie na Redakčný pult. Vytváranie a úprava oboch typov používa rovnaký spoločný vzor zoznamu a centrovaných modálnych editorov; INFO oznam sa vizuálne neoddeľuje svojvoľným kartovým layoutom.

Verný Discord náhľad je vždy odvodený z kanonického publikačného draftu. Zobrazuje členenie na správy, obsah, `@everyone`, embed titulky, popisy, day emoji/author sekciu, odkazy, thumbnail, cieľovú seen reakciu a identitu bota **Carlo** v podobe blízkej reálnemu Discord kanálu. Nejde o alternatívny editor ani samostatnú záložku.

Celodenná udalosť trvajúca viac dní sa v spoločnom zozname aj Discord náhľade zobrazuje ako inkluzívny rozsah prvého až posledného dňa. Interný exkluzívny koncový dátum sa používateľovi nesmie ukázať ani nesmie spôsobiť zobrazenie viacdennej udalosti ako jednodňovej.

### História publikácií

Pre každý beh zobrazuje:

- publikačný termín,
- skutočný čas,
- automatický alebo ručný spôsob,
- používateľa, ktorý publikovanie vyvolal,
- stav,
- snapshot obsahu,
- identifikátory alebo odkazy na Discord správy,
- prípadnú chybu a počet pokusov.

### Kanály

Umožňuje:

- vytvoriť súkromný kanál,
- vybrať používateľov a roly,
- zobraziť výsledné oprávnenia,
- iniciovať archiváciu,
- schváliť alebo zamietnuť čakajúcu archiváciu,
- zobraziť históriu operácií.

### Používatelia a oprávnenia

Umožňuje oprávnenému administrátorovi:

- prideliť alebo odobrať rolu Team Mod,
- prideliť alebo odobrať rolu Admin,
- vyhľadať člena servera,
- vidieť aktuálne relevantné roly,
- potvrdiť citlivú zmenu,
- zobraziť výsledok synchronizácie s Discordom.

Systém nesmie dovoliť odstrániť posledného spravovateľného administrátora ani vykonať zmenu, na ktorú bot podľa hierarchie Discord rolí nemá právo.

### Automatické reakcie a seen emoji

Umožňuje:

- vybrať seen emoji používané pod oznamami,
- zapnúť alebo vypnúť seen reakciu,
- vybrať kanály, v ktorých bot automaticky reaguje na každú správu,
- samostatne zapnúť reakciu pri označení bota,
- otestovať vybrané emoji,
- zobraziť nedostupné alebo odstránené emoji a vykonať nápravu.

### Nastavenia publikovania

Umožňuje:

- nastaviť deň a čas,
- zapnúť alebo pozastaviť automatické publikovanie,
- vybrať cieľový Discord kanál,
- zobraziť, že každá publikácia používa riadené oslovenie `@everyone`,
- zapnúť alebo vypnúť predvolené publikovanie zdrojových popisov z Google Kalendára,
- nastaviť úvod a záver,
- nastaviť moderátorský kanál pre prevádzkové upozornenia,
- zobraziť jednoznačné časové pásmo,
- ručne publikovať najbližší balík.

### Integrácie

Zobrazuje:

- nakonfigurované Google kalendáre,
- stav pripojenia,
- poslednú synchronizáciu,
- možnosť kontrolnej synchronizácie,
- chyby a odporúčaný postup nápravy.

### Audit

Zobrazuje filtrovatelný zoznam dôležitých zmien a operácií.

## 12.3 Responzívne správanie

Minimálne sa musia otestovať šírky približne:

- 360 px,
- 768 px,
- 1024 px,
- 1440 px.

Tabuľky sa na mobiloch nesmú iba zmenšiť do nečitateľnej podoby. Majú sa transformovať na karty, prioritizované stĺpce alebo ovládateľný detail.

Všetky primárne operácie musia byť použiteľné dotykom a ovládacie prvky musia mať primeranú veľkosť.

---

# 13. Autentifikácia a autorizácia webu

## 13.1 Prihlásenie

Preferované prihlásenie je Discord OAuth2. Po prihlásení systém overí:

- identitu používateľa,
- jeho členstvo na nakonfigurovanom Discord serveri,
- jeho aktuálne roly,
- stav účtu a platnosť relácie.

Discord token bota ani Google prihlasovacie údaje sa nikdy neposielajú do prehliadača.

## 13.2 Roly

Minimálny model oprávnení:

| Operácia | Team Mod | SDB / FMA | Admin |
|---|---:|---:|---:|
| Zobraziť najbližšie oznamy | áno | áno | áno |
| Upraviť titulok a popis udalosti | áno | nie | áno |
| Spravovať manuálne udalosti | áno | nie | áno |
| Spravovať INFO oznamy | áno | nie | áno |
| Vytvoriť kanál | áno | nie | áno |
| Požiadať o archiváciu | áno | nie | áno |
| Schváliť archiváciu | nie | nie | áno |
| Ručne publikovať | nie | áno | áno |
| Meniť harmonogram a integrácie | nie | nie | áno |
| Meniť automatické reakcie | nie | nie | áno |
| Udeľovať Team Mod | nie | nie | áno |
| Udeľovať Admin | nie | nie | áno, s dodatočným potvrdením |
| Zobraziť audit | obmedzene | nie | áno |

Rola `SDB / FMA` je špecializovaná publikačná rola. Sama osebe neposkytuje všeobecnú administráciu ani redakčné práva; umožňuje zobraziť najbližší balík a ručne ho publikovať.

Matica musí byť centralizovaná v autorizačnej vrstve. Kontroly sa vykonávajú na serveri pri každej operácii; skrytie tlačidla vo webovom rozhraní nie je bezpečnostná kontrola.

## 13.3 Bezpečnostné požiadavky

Webová administrácia musí používať:

- HTTPS,
- bezpečné `HttpOnly`, `Secure` a primerané `SameSite` cookies,
- ochranu proti CSRF,
- ochranu proti XSS a bezpečné zobrazovanie používateľského obsahu,
- kontrolu povolených presmerovaní OAuth,
- obmedzenie frekvencie citlivých operácií,
- expiráciu relácie a možnosť odhlásenia,
- bezpečnú prácu s tajomstvami,
- serverovú validáciu všetkých vstupov,
- audit citlivých operácií.

---

# 14. Správa Discord kanálov cez web

Webové operácie nad kanálmi musia používať rovnakú aplikačnú službu ako Discord príkazy. Logika vytvorenia alebo archivácie sa nesmie implementovať dvakrát.

Pri vytvorení kanála web umožní vybrať:

- kategóriu z povoleného zoznamu,
- názov a emoji,
- členov,
- roly,
- vlastníka alebo zodpovednú osobu.

Pred potvrdením zobrazí výsledné oprávnenia. Po vytvorení zobrazí odkaz na kanál.

Archivácia musí:

- používať automaticky odvodený dátum,
- zachovať pôvodný názov v metadátach,
- uložiť dôvod a iniciátora,
- presunúť kanál do nakonfigurovanej archívnej kategórie a synchronizovať jeho oprávnenia s touto kategóriou rovnako ako v pôvodnom riešení,
- pred potvrdením upozorniť, že individuálne oprávnenia kanála budú nahradené oprávneniami archívnej kategórie,
- evidovať schválenie alebo zamietnutie.

---

# 15. Správa Discord rolí

Webová administrácia umožní spravovať iba explicitne povolené roly Team Mod a Admin. Nesmie poskytovať všeobecný editor všetkých Discord oprávnení.

Pri každej zmene systém overí:

- že cieľový používateľ je členom servera,
- že cieľová rola existuje,
- že bot má právo rolu spravovať,
- že hierarchia rolí zmenu povoľuje,
- že konajúci administrátor má požadované oprávnenie,
- že zmena neodstráni poslednú osobu schopnú spravovať systém.

Operácia musí byť auditovaná a výsledok overený spätným načítaním aktuálnych rolí z Discordu.

Roly sa v konfigurácii identifikujú stabilným Discord ID, nie názvom.

---

# 16. Automatické reakcie a seen emoji

Je potrebné oddeliť najmenej tri samostatné nastavenia:

1. emoji potvrdzujúce prečítanie oznamov,
2. automatickú reakciu na správy vo vybraných kanáloch,
3. reakciu pri označení bota.

Každá funkcia musí mať vlastný prepínač. Emoji môže byť rovnaké, ale konfigurácia nesmie vynucovať ich nerozlíšiteľnosť.

Pri vlastnom serverovom emoji systém overí:

- že emoji existuje,
- že ho bot vidí,
- že ho môže použiť v cieľovom serveri,
- že má v cieľovom kanáli právo pridávať reakcie.

Chyba reakcie nemá zablokovať publikovanie, ale musí byť zaznamenaná a viditeľná v stave publikácie.

---

# 17. Navrhovaný dátový model

Presný model sa môže počas technického návrhu upraviť, musí však pokrývať minimálne tieto entity:

## 17.1 `guild_config`

- Discord guild ID,
- ID rolí Admin, Team Mod a SDB / FMA,
- ID cieľového kanála oznamov,
- ID príkazového a moderátorského kanála,
- ID pracovnej a archívnej kategórie,
- časové pásmo,
- publikačný deň a čas,
- stav automatického publikovania,
- nastavenie predvoleného publikovania Google popisov,
- nastavenia generovaného úvodu, riadeného `@everyone` a záveru.

## 17.2 `calendar_source`

- interné ID,
- guild ID,
- provider,
- Google calendar ID,
- názov,
- priorita,
- aktívny stav,
- synchronizačný token,
- čas a stav poslednej synchronizácie.

## 17.3 `external_event`

- interné ID,
- zdrojový kľúč udalosti,
- calendar source ID,
- provider event ID,
- identita výskytu opakovanej udalosti,
- stabilný identifikátor opakovanej série,
- pôvodný začiatok konkrétneho výskytu,
- pôvodný názov a popis,
- začiatok a koniec,
- časové pásmo,
- celodenný príznak,
- stav udalosti,
- verzia alebo ETag,
- čas poslednej synchronizácie,
- mäkké odstránenie.

Na zdrojový kľúč musí existovať unikátne obmedzenie.

## 17.4 `event_override`

- external event ID,
- vlastný titulok,
- stav vlastného popisu vrátane rozlíšenia „zdediť“ a „zámerne prázdny“,
- vlastný popis,
- rozhodnutie o zaradení s hodnotami „automaticky“, „vždy zaradiť“ alebo „vždy vylúčiť“,
- verzia pre kontrolu súbehu,
- autor a čas zmeny.

## 17.5 `event_series_override`

- stabilný identifikátor opakovanej série,
- začiatok účinnosti od konkrétneho výskytu,
- vlastný titulok a/alebo popis,
- stav vlastného popisu,
- verzia,
- autor a čas zmeny.

Viac pravidiel jednej série musí byť zoraditeľných podľa začiatku účinnosti. Pre konkrétny výskyt sa použije najnovšie pravidlo, ktorého účinnosť už nastala, pokiaľ ho neprebije výnimka v `event_override`.

## 17.6 `manual_event`

- guild ID,
- titulok a popis,
- začiatok a koniec,
- časové pásmo,
- celodenný príznak,
- odkaz,
- stav,
- autor a časové údaje,
- mäkké odstránenie.

## 17.7 `info_announcement`

- guild ID,
- titulok a popis,
- odkaz,
- obrázok,
- platnosť od a do,
- stav,
- autor a časové údaje,
- mäkké odstránenie.

## 17.8 `publication_run`

- guild ID,
- stabilný identifikátor publikačného termínu,
- plánovaný čas,
- skutočný začiatok a koniec,
- automatický alebo ručný spôsob,
- iniciátor,
- stav,
- pokus,
- idempotency key,
- chyba,
- identifikátory Discord správ.

Na kombináciu servera a publikačného termínu musí existovať unikátne obmedzenie pre štandardné publikovanie.

## 17.9 `publication_item`

Nemenný snapshot položky v konkrétnej publikácii:

- publication run ID,
- typ položky,
- zdrojové ID,
- poradie,
- finálny titulok,
- finálny popis,
- finálne dátumy, odkazy, obrázky a vizuálne údaje.

## 17.10 `channel_archive_request`

- guild ID,
- channel ID,
- žiadateľ,
- dôvod,
- stav,
- schvaľovateľ,
- Discord message ID,
- časy vytvorenia, expirácie a rozhodnutia.

## 17.11 `reaction_config`

- guild ID,
- seen emoji,
- auto-reaction emoji,
- prepínače funkcií,
- zoznam cieľových kanálov.

## 17.12 `audit_log`

- guild ID,
- používateľ,
- typ akcie,
- typ a identifikátor objektu,
- pôvodná hodnota,
- nová hodnota,
- výsledok,
- čas,
- korelačný identifikátor požiadavky.

Pre produkčné nasadenie s webom, plánovačom a Discord procesom sa odporúča PostgreSQL. SQLite možno ponechať pre lokálny vývoj a automatizované testy, ak aplikačná vrstva zachová kompatibilné správanie.

---

# 18. Architektonické požiadavky

## 18.1 Jedna doménová logika

Discord príkazy, webové rozhranie a plánovač musia používať spoločné aplikačné služby pre:

- zostavenie publikačného balíka,
- publikovanie,
- vytvorenie kanála,
- archiváciu,
- správu oprávnení,
- audit.

Web ani Discord vrstva nesmú obsahovať vlastnú paralelnú implementáciu týchto pravidiel.

## 18.2 Oddelenie vrstiev

Odporúčané členenie:

- doménový model a pravidlá,
- aplikačné služby a prípady použitia,
- integračná vrstva Google a Discord,
- perzistenčná vrstva,
- webové API,
- webové používateľské rozhranie,
- plánovač a pracovné úlohy.

Konkrétny framework webu sa zvolí v technickom návrhu. Voľba musí podporovať bezpečné OAuth prihlásenie, serverovú autorizáciu, responzívny frontend, automatizované testovanie a prevádzkové monitorovanie.

## 18.3 Súbeh a idempotencia

Všetky operácie s externým účinkom musia mať ochranu proti opakovaniu, najmä:

- publikovanie,
- vytvorenie kanála,
- archivácia,
- schválenie žiadosti,
- zmena role.

Opakované odoslanie HTTP požiadavky, dvojklik alebo paralelné spracovanie nesmie bez upozornenia vytvoriť duplicitný výsledok.

## 18.4 Validácia

Validácia sa vykonáva na serveri a musí pokrývať:

- dátumy a časové pásma,
- URL,
- dĺžkové limity Discordu,
- povolené typy obrázkov,
- existenciu Discord objektov,
- dostupnosť emoji,
- oprávnenia a hierarchiu rolí,
- časové poradie začiatku a konca,
- konfliktné úpravy.

---

# 19. Audit a história

Auditovať sa musia minimálne:

- zmeny redakčných titulkov a popisov,
- zmeny rozsahu úprav opakovaných udalostí,
- ručné zaradenie alebo vylúčenie kalendárovej udalosti,
- vytvorenie, úprava a deaktivácia manuálnej udalosti,
- vytvorenie, úprava a deaktivácia INFO oznamu,
- zmeny publikačného rozvrhu,
- ručné publikovanie,
- neúspešné a opakované publikovanie,
- vytvorenie a archivácia kanála,
- schválenie alebo zamietnutie archivácie,
- udelenie a odobratie rolí,
- zmeny reakcií a integrácií.

Publikačná história je nemenný záznam skutočného výstupu. Audit nie je náhradou za publikačný snapshot.

---

# 20. Chybové stavy a upozornenia

Systém musí rozlišovať najmenej:

- chybu synchronizácie kalendára,
- neplatné alebo zastarané kalendárové údaje,
- chybu zostavenia balíka,
- chybu Discord oprávnení,
- čiastočné publikovanie,
- chybu pridania reakcie,
- chybu vytvorenia alebo archivácie kanála,
- chybu zmeny role,
- internú neočakávanú chybu.

Prevádzkové upozornenia, chyby synchronizácie, chyby publikovania, potrebné zásahy a pripomienky k publikovaniu sa posielajú do nakonfigurovaného Discord kanála `moderátori`. Jednotlivé kategórie upozornení musia byť vizuálne rozlíšené a samostatne zapínateľné, hoci používajú rovnaký cieľový kanál.

Používateľ, ktorý operáciu vyvolal, musí vždy dostať zrozumiteľný výsledok aj v prípade, že nie je nakonfigurovaný žiadny technický príjemca chýb.

Technické detaily sa zobrazujú v administrácii oprávneným osobám, nie bežným používateľom. Logy nesmú obsahovať tokeny, OAuth tajomstvá ani iné citlivé údaje.

---

# 21. Nefunkčné požiadavky

## 21.1 Spoľahlivosť

- Bežný reštart nesmie stratiť redakčné úpravy ani stav publikačného termínu.
- Opakované spustenie nesmie založiť duplicitné plánovacie slučky.
- Publikovanie musí mať bezpečný stavový model a možnosť zotavenia.
- Zlyhanie obrázka alebo reakcie nesmie zablokovať hlavný text oznamov.

## 21.2 Výkon

- Dashboard a editor majú pri bežnej záťaži reagovať bez citeľného čakania.
- Volania Google a Discord API sa nemajú vykonávať zbytočne pri každom vykreslení komponentu.
- Dlhšie externé operácie majú zobrazovať priebeh alebo stav spracovania.
- Synchrónne databázové alebo sieťové operácie nesmú blokovať hlavnú Discord slučku.

## 21.3 Pozorovateľnosť

Riešenie musí poskytovať:

- štruktúrované logy,
- korelačné identifikátory,
- zdravotný stav aplikácie,
- stav pripojenia k Discordu,
- stav Google integrácie,
- metriky úspešných a neúspešných publikácií,
- prehľad posledných plánovaných úloh.

## 21.4 Zálohovanie

Produkčné údaje musia byť pravidelne zálohované. Musí existovať zdokumentovaný postup obnovy a aspoň raz overený test obnovy.

## 21.5 Kompatibilita

Webová administrácia musí podporovať aktuálne stabilné verzie hlavných prehliadačov. Discord funkcie musia rešpektovať aktuálne limity a odporúčania Discord API.

---

# 22. Testovanie

## 22.1 Jednotkové testy

Povinné sú testy minimálne pre:

- výpočet najbližšieho publikačného termínu,
- dvojtýždňové okno,
- prechod letného a zimného času,
- posledný deň platnosti INFO oznamu,
- triedenie celodenných a časovaných udalostí,
- stabilnú identitu udalosti,
- prioritu redakčných úprav,
- predvolené vypnutie a administrátorské zapnutie Google popisov,
- vylúčenie pomocou `stop carlo` a ručné prepísanie tohto rozhodnutia,
- úpravu jedného výskytu a pravidlo pre tento a budúce výskyty série,
- opakované zaradenie tej istej udalosti,
- idempotenciu publikovania,
- rozhodovanie o preskočení termínu,
- autorizačnú maticu.

## 22.2 Integračné testy

Povinné sú testy pre:

- synchronizáciu Google udalostí vrátane stránkovania a opakovaných udalostí,
- zrušenie a presunutie udalosti,
- zostavenie Discord správ pri prekročení limitu embedov,
- čiastočné zlyhanie publikovania a bezpečné opakovanie,
- vytvorenie kanála s výslednými oprávneniami,
- jednoznačné schválenie konkrétnej archivácie,
- zmenu Discord role,
- OAuth prihlásenie a serverovú autorizáciu.

Externé služby majú byť v automatizovaných testoch nahradené kontrolovanými testovacími adaptérmi.

## 22.3 End-to-end testy webu

Minimálne scenáre:

1. Admin sa prihlási a otvorí najbližší balík.
2. Team Mod upraví popis kalendárovej udalosti.
3. Úprava zostane zachovaná po obnovení kalendára.
4. Tá istá udalosť použije úpravu aj v ďalšom týždni.
5. Používateľ vytvorí manuálnu udalosť.
6. Používateľ vytvorí INFO oznam s expiráciou.
7. Admin ručne publikuje a najbližší nakonfigurovaný beh sa preskočí.
8. Admin vytvorí súkromný kanál.
9. Team Mod požiada o archiváciu a Admin schváli správnu žiadosť.
10. Admin udelí a odoberie povolenú rolu.
11. Neoprávnený používateľ nemôže vykonať administrátorskú operáciu ani priamym API volaním.
12. Udalosť s `stop carlo` je v editore viditeľná, ale nie je v náhľade publikácie, kým ju Admin explicitne nezaradí.
13. Úprava jedného výskytu série neovplyvní ďalší výskyt; voľba „tento a všetky budúce“ ovplyvní iba príslušné nasledujúce výskyty.
14. Používateľ s rolou SDB / FMA môže balík zobraziť a ručne publikovať, ale nemá ostatné administračné oprávnenia.

## 22.4 Vizuálne a prístupnostné testy

Kľúčové stránky sa overia na definovaných šírkach, v svetlom aj prípadnom tmavom režime a pri zväčšení textu. Kontroluje sa kontrast, klávesnicová navigácia, focus stav, popisy formulárov a použiteľnosť chybových hlásení.

---

# 23. Migrácia z pôvodnej verzie

Migrácia musí zachovať relevantné existujúce údaje, najmä:

- aktívne a budúce INFO oznamy,
- ich titulky, popisy, odkazy, obrázky a platnosť,
- nastavené reakčné emoji,
- zoznam kanálov automatických reakcií,
- publikačný kanál a serverové kategórie,
- identifikátor moderátorského kanála pre nové prevádzkové upozornenia.

Pôvodné ručne vytvorené event oznamy sa musia analyzovať. Podľa výsledku sa:

- spárujú s Google udalosťou a ich obsah sa prevedie na redakčnú úpravu, alebo
- importujú ako manuálne udalosti.

Migrácia musí byť:

- opakovateľná bez vytvárania duplicít,
- najprv dostupná v režime náhľadu,
- vybavená reportom úspešných, preskočených a problematických záznamov,
- vykonaná so zálohou pôvodných údajov,
- reverzibilná minimálne návratom k zálohe počas migračného okna.

Prechod na novú verziu musí zabrániť tomu, aby starý a nový plánovač publikovali súčasne.

---

# 24. Akceptačné kritériá

Riešenie možno považovať za funkčne akceptované, ak platí všetko nasledujúce:

1. Bez akéhokoľvek redakčného zásahu vytvorí správne zoradený prehľad udalostí z najbližších 14 dní.
2. Deň, dátum, čas a day emoji sa určujú automaticky a správne.
3. Úprava titulku alebo popisu kalendárovej udalosti pretrvá synchronizáciu aj reštart.
4. Tá istá udalosť použije uloženú úpravu v oboch týždenných publikáciách.
5. Zrušenie vlastnej úpravy obnoví aktuálnu hodnotu z Google Kalendára.
6. Manuálna udalosť sa správne zaradí podľa času.
7. Platný INFO oznam sa zobrazí a expirovaný sa nezobrazí, pričom zostane v histórii.
8. Webový editor zobrazuje obsah najbližšieho publikačného termínu.
9. Webový náhľad a Discord výstup používajú rovnaké pravidlá formátovania.
10. Automatické publikovanie v nakonfigurovanom týždennom termíne prebehne najviac raz.
11. Úspešné ručné publikovanie preskočí práve jeden najbližší automatický termín.
12. Neúspešné ručné publikovanie termín nepreskočí.
13. Väčší počet oznamov sa bezpečne rozdelí do viacerých Discord správ.
14. Team Mod nemôže vykonať operáciu vyhradenú Adminovi.
15. Neoprávnený používateľ nemôže obísť oprávnenie priamym volaním webového API ani interakciou s cudzím tlačidlom.
16. Jedna schvaľovacia reakcia alebo webové potvrdenie archivuje iba príslušný kanál.
17. Roly sa spravujú podľa Discord ID a s rešpektovaním hierarchie rolí.
18. Seen emoji a automatické reakcie sa dajú konfigurovať a otestovať vo webovej administrácii.
19. Používateľ vždy dostane zrozumiteľný výsledok operácie aj pri chybe.
20. Všetky citlivé administrátorské zmeny sú dohľadateľné v audite.
21. Rozhranie je plne použiteľné na mobile, tablete aj počítači.
22. Automatizované testy pokrývajú kritické dátumové, autorizačné a publikačné scenáre.
23. Existuje zdokumentovaný spôsob nasadenia, zálohy, obnovy a riešenia zlyhaného publikovania.
24. Predvolený harmonogram je pondelok o 20:00, pričom Admin môže zmeniť deň aj čas.
25. Zdrojový Google popis sa predvolene nepublikuje; Admin vie toto správanie globálne zapnúť.
26. Editor pri pridávaní redakčného popisu predvyplní dostupný Google popis bez jeho automatického uloženia.
27. `@everyone` sa v každej úspešnej publikácii použije práve raz.
28. Automaticky generovaný úvod má funkčný náhradný text pri nedostupnosti modelu.
29. Udalosť s `stop carlo` sa automaticky vylúči, zostane viditeľná v administrácii a Admin ju môže explicitne zaradiť.
30. Úpravy opakovanej udalosti správne rozlišujú konkrétny výskyt a tento plus všetky budúce výskyty.
31. Ručné publikovanie môže vykonať iba Admin alebo SDB / FMA.
32. Archivovaný kanál prevezme oprávnenia archívnej kategórie.
33. Prevádzkové upozornenia sa zobrazujú v nakonfigurovanom moderátorskom kanáli.

---

# 25. Potvrdené produktové rozhodnutia

Nasledujúce rozhodnutia sú záväznou súčasťou zadania:

1. Publikačný deň aj čas sú konfigurovateľné. Predvolená hodnota je pondelok o 20:00 v `Europe/Bratislava`.
2. Štandardne sa používa jeden Google kalendár, architektúra však podporuje viac zdrojových kalendárov.
3. Predvolene sa publikuje titulok a voliteľný redakčný popis, nie zdrojový Google popis. Admin môže automatické publikovanie Google popisov globálne zapnúť. Editor vždy ponúkne dostupný Google popis ako predvolený text novej redakčnej úpravy.
4. Udalosti zachovajú doterajší vizuálny štýl event kariet s dátumom/časom a day emoji v hornej časti; celodenné a viacdňové udalosti ho primerane rozšíria bez zavedenia odlišného dizajnu.
5. Ručne publikovať môže iba Admin alebo používateľ s rolou SDB / FMA. Team Mod toto oprávnenie nemá iba z titulu svojej role.
6. Automaticky generovaný úvod zostáva zachovaný a má deterministický náhradný text.
7. Každá publikácia používa `@everyone`, technicky povolené práve raz.
8. Kalendárovú udalosť možno ručne vylúčiť vo webovej administrácii. Zdrojová fráza `stop carlo` ju vylúči automaticky, ale udalosť zostane v administrácii a Admin ju môže znovu zaradiť.
9. Redakčná úprava sa predvolene viaže na konkrétny výskyt opakovanej udalosti. Editor umožňuje jedným rozhodnutím aplikovať zmenu na tento a všetky budúce výskyty a pri neskoršej zmene znovu zvoliť medzi výnimkou a novým pravidlom odteraz.
10. Archivácia zachová doterajší model: kanál sa presunie do archívnej kategórie a synchronizuje s jej oprávneniami.
11. Prevádzkové upozornenia smerujú do Discord kanála `moderátori`.
12. Webová administrácia má moderný, elegantný, responzívny a ľahko čitateľný vizuálny štýl podľa požiadaviek kapitoly 12. Konkrétne logo, farby a komponentový dizajn sa určia v samostatnom vizuálnom návrhu bez zmeny funkčného rozsahu.

---

# 26. Mimo povinného rozsahu prvej verzie

Ak nebude dohodnuté inak, do povinného minima nepatrí:

- všeobecná správa všetkých Discord rolí a oprávnení,
- editovanie Google Kalendára z webovej administrácie,
- verejný portál pre bežných členov,
- podpora ľubovoľného počtu nesúvisiacich Discord serverov ako komerčný multitenant produkt,
- analytika správania jednotlivých členov nad rámec Discord reakcií,
- automatické rozhodovanie jazykového modelu o tom, ktoré udalosti sa majú publikovať,
- natívna mobilná aplikácia.

Architektúra však nemá zbytočne znemožniť budúce rozšírenie.

---

# 27. Požadované výstupy implementácie

Dodávka novej verzie má obsahovať:

1. zdrojový kód Discord bota,
2. zdrojový kód webovej administrácie,
3. databázové migrácie,
4. integračnú vrstvu Google Kalendára,
5. automatizované testy,
6. migračný nástroj zo starej verzie,
7. vzor konfigurácie bez tajomstiev,
8. návod na lokálny vývoj,
9. návod na produkčné nasadenie,
10. postup zálohy a obnovy,
11. prevádzkový návod pre zlyhané publikovanie,
12. používateľský návod pre Team Mod a Admin,
13. technickú dokumentáciu architektúry a dátového modelu,
14. zoznam známych obmedzení.

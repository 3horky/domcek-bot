# UI a UX štandardy aplikácie Carlo

| Vlastnosť             | Hodnota                                                                    |
| --------------------- | -------------------------------------------------------------------------- |
| Stav                  | záväzný projektový štandard                                                |
| Rozsah                | webová administrácia Carlo a jej používateľské toky                        |
| Vlastník              | produktový a frontendový návrh projektu Carlo                              |
| Posledná aktualizácia | 11. august 2026                                                            |
| Súvisiace dokumenty   | `ZADANIE.md`, `PLAN_IMPLEMENTACIE.md`, `PLAN_UI_UX_AUDITU.md`, `STATUS.md` |

## 1. Účel a záväznosť dokumentu

Tento dokument je normatívnym štandardom používateľského rozhrania a používateľskej skúsenosti webovej administrácie Carlo. Jeho cieľom je zabezpečiť, aby aplikácia zostala aj pri ďalšom rozširovaní:

- moderná bez podliehania krátkodobým vizuálnym trendom,
- zrozumiteľná pre ľudí bez technických znalostí,
- rýchla a prirodzená pri každodennej práci,
- vizuálne a behaviorálne konzistentná,
- responzívna od mobilu po veľký pracovný monitor,
- prístupná a ovládateľná bez myši,
- bezpečná pri citlivých alebo nezvratných operáciách,
- pravdivá voči skutočnému stavu Carla, Google Kalendára a Discordu.

Štandard platí pre všetky existujúce aj budúce stránky, modaly, formuláre, komponenty, texty, systémové stavy a používateľské toky. Platí rovnako pre návrh, implementáciu, code review, automatizované testovanie aj používateľskú akceptáciu.

Pri požiadavkách sa používajú tieto výrazy:

- **MUSÍ / NESMIE** – záväzné pravidlo bez voľnej interpretácie,
- **MÁ / NEMÁ** – silné odporúčanie; výnimka potrebuje písomné zdôvodnenie,
- **MÔŽE** – dovolená možnosť, ak nenaruší ostatné pravidlá.

Funkčný a produktový rozsah určuje [`ZADANIE.md`](./ZADANIE.md). Technické etapy určuje [`PLAN_IMPLEMENTACIE.md`](./PLAN_IMPLEMENTACIE.md). Tento dokument je autoritatívny pre spôsob, akým sa funkcie organizujú, pomenúvajú, zobrazujú a ovládajú. Pri konflikte sa najprv zachová produktová pravda zo zadania a následne sa nájde riešenie, ktoré spĺňa tento štandard; konflikt sa nesmie potichu obísť.

## 2. Produktová skúsenosť, ktorú Carlo vytvára

Carlo nie je technická konzola. Je to pokojné pracovné prostredie pre ľudí, ktorí pripravujú oznamy a spravujú vybrané časti komunitného Discord servera. Rozhranie má pôsobiť dôveryhodne, ľudsky a kompetentne. Používateľ má vždy rozumieť:

1. kde sa nachádza,
2. čo na tomto mieste môže urobiť,
3. aké údaje práve vidí,
4. čo sa stane po vykonaní akcie,
5. či sa akcia podarila,
6. čo má urobiť, ak sa nepodarila.

Dobré rozhranie Carla sa nemeria počtom viditeľných možností. Meria sa tým, ako málo neistoty, prepínania a opravovania potrebuje používateľ na dokončenie reálnej úlohy.

## 3. Základné dizajnové princípy

### 3.1 Úloha pred dátovým modelom

Stránky a ovládacie prvky sa organizujú podľa toho, čo chce človek dosiahnuť, nie podľa interných tabuliek, API služieb alebo Discord objektov.

Správne sú napríklad úlohy „Vytvoriť nový kanál“, „Archivovať kanál“ a „Pripraviť najbližšie oznamy“. Nesprávne sú vstupy typu „Spustiť create-channel request“, „Obnoviť draft“ bez vysvetlenia alebo zoznam interných identifikátorov.

### 3.2 Najprv podstatné, potom podrobnosti

Na prvý pohľad sa zobrazí len to, čo používateľ potrebuje na pochopenie a začatie úlohy. Voliteľné a pokročilé voľby sa odhaľujú postupne, v logickom mieste a so zachovaním kontextu.

Postupné odhaľovanie nesmie skrývať informáciu potrebnú na bezpečné rozhodnutie. Rozbaľovací riadok musí vyzerať ako ovládací prvok, mať ikonu, názov, prípadný súhrn výberu a šípku signalizujúcu stav.

### 3.3 Jedna úloha má jedno prirodzené pracovisko

Používateľ nesmie upravovať tú istú výslednú vec na viacerých nesúvisiacich stránkach. Kalendárové udalosti, manuálne udalosti a INFO oznamy preto patria do spoločného Redakčného pultu. Nastavenia obsahujú trvalé pravidlá systému, nie každodenné pracovné operácie.

Nová samostatná stránka vznikne iba vtedy, ak má vlastnú jasnú používateľskú úlohu, potrebuje samostatný kontext alebo by v existujúcom pracovisku vytvorila neprimeranú zložitosť.

### 3.4 Bežný jazyk pred technickým jazykom

Rozhranie používa prirodzenú slovenčinu. Technické pojmy sa zobrazujú iba vtedy, keď ich používateľ potrebuje na vykonanie práce. Interné ID, názvy stavov z databázy, názvy endpointov, idempotency kľúče, stack trace alebo surové odpovede služieb nepatria do hlavného rozhrania.

Technická diagnostika môže byť dostupná oprávneným ľuďom v sekundárnom detaile, nikdy však nesmie nahradiť zrozumiteľné vysvetlenie.

### 3.5 Viditeľný kontext a pravdivý stav

Každé číslo, stav a prázdna plocha musí jasne hovoriť, čo opisuje. „0 udalostí z Google Kalendára“ sa nesmie tváriť ako „0 položiek v ozname“, ak oznam obsahuje manuálnu alebo INFO položku.

Náhľad musí zodpovedať tomu, čo Carlo skutočne odošle. Úspešná hláška sa zobrazí až po potvrdenom úspechu. Rozhranie nesmie predstierať, že dáta sú aktuálne, ak synchronizácia zlyhala alebo je zastaraná.

### 3.6 Bezpečie bez zbytočného brzdenia

Bežné vratné operácie majú byť rýchle. Potvrdenie sa vyžaduje pri deštruktívnej, citlivej, nezvratnej alebo externe viditeľnej akcii, nie pri každom uložení.

Používateľ musí pred potvrdením rozumieť dôsledku: čo sa zmení, kde sa to prejaví a či sa to dá vrátiť. Dvojité odoslanie sa technicky aj vizuálne zablokuje.

### 3.7 Konzistentnosť pred originalitou

Rovnaký význam má mať rovnaký vzhľad, umiestnenie, názov a správanie. Nový lokálny komponent sa nevytvára len preto, že na jednej stránke pôsobí zaujímavejšie. Ak už existuje vhodný spoločný vzor, musí sa použiť.

### 3.8 Prístupnosť a responzivita sú súčasť návrhu

Mobilný, klávesnicový a prístupný variant sa nenavrhuje dodatočne. Každý komponent musí mať od začiatku definované správanie pre úzky priestor, dotyk, klávesnicu, zväčšenie a asistenčné technológie.

## 4. Používatelia, roly a oprávnenia

### 4.1 Návrh pre skutočné roly

Rozhranie musí byť overené najmenej pre roly Admin, Team Mod a SDB / FMA. Každá rola má vidieť navigáciu a akcie zodpovedajúce svojim schopnostiam.

- Nedostupná celá pracovná oblasť sa v navigácii nezobrazuje.
- Ak je informácia užitočná, ale akcia nie je povolená, informácia môže zostať viditeľná a akcia musí jasne vysvetliť obmedzenie.
- Rozhranie nesmie ponúknuť akciu, o ktorej už vopred vie, že ju používateľ nemôže vykonať.
- Skrytie alebo deaktivácia vo webovom rozhraní nikdy nenahrádza serverové overenie oprávnenia.
- Pri citlivej akcii sa oprávnenie kontroluje znova v okamihu potvrdenia.

### 4.2 Identita používateľa

Pri práci s ľuďmi sa primárne zobrazuje avatar a zobrazované meno. Discord meno je sekundárna pomôcka na rozlíšenie. Interné Discord ID sa nezobrazuje ako bežná identita.

Ak avatar nie je dostupný, použije sa stabilný a dôstojný fallback s iniciálou. Rozhranie nesmie pri pomalom načítaní avatarov meniť výšku riadkov alebo posúvať obsah.

## 5. Informačná architektúra

### 5.1 Hlavná navigácia

Navigácia je usporiadaná podľa mentálneho modelu používateľa:

| Oblasť         | Primárne stránky                            | Účel                                                         |
| -------------- | ------------------------------------------- | ------------------------------------------------------------ |
| Publikovanie   | Prehľad, Redakčný pult, História publikácií | príprava, kontrola a história oznamov                        |
| Správa obsahu  | Audit                                       | dohľadanie dôležitých zmien                                  |
| Správa servera | Kanály, Roly, Reakcie, Nastavenia           | vykonávanie serverových úloh a nastavenie trvalých pravidiel |
| Diagnostika    | Stav systému                                | zrozumiteľný prevádzkový stav a náprava problémov            |

Poradie hlavných položiek sa nemení bez dôvodu podloženého používateľským výskumom. Názvy v navigácii musia zodpovedať nadpisom stránok. Aktívna stránka musí byť zreteľná vizuálne aj programovo.

### 5.2 Čo patrí do Nastavení

Do Nastavení patria len pravidlá, ktoré pretrvávajú a ovplyvňujú budúce správanie systému:

- harmonogram a cieľ publikovania,
- texty a pravidlá publikovania,
- moderátorský kanál,
- pravidlá umiestnenia nových a archivovaných kanálov,
- pripojené Google kalendáre a synchronizácia.

Vytváranie kanála, archivácia, správa rolí, úprava obsahu a výber automatických reakcií sú pracovné úlohy a majú vlastné stránky. Nastavenia nesmú byť skladiskom funkcií, ktoré nemajú inde miesto.

### 5.3 Hĺbka navigácie

Bežná úloha má byť dosiahnuteľná z hlavnej navigácie jedným výberom a začateľná bez ďalšieho hľadania. Aplikácia nemá vytvárať hlboké hierarchie stránok. Detail alebo editor sa podľa povahy úlohy otvorí:

- v modale, ak používateľ zostáva v kontexte zoznamu,
- na samostatnej stránke, ak ide o dlhý viacfázový tok alebo potrebuje zdieľateľnú adresu,
- v popoveri, ak ide o krátky výber s nízkym rizikom.

## 6. Typy stránok

Každá stránka sa má vedome zaradiť do jedného z nasledujúcich typov. Miešanie viacerých typov bez jasnej hierarchie vytvára chaos.

### 6.1 Prehľadová stránka

Prehľad odpovedá na otázky „Čo sa bude diať?“, „Je všetko v poriadku?“ a „Čo si vyžaduje moju pozornosť?“.

Musí obsahovať:

- jednoznačný najbližší termín a stav automatického publikovania,
- celkový obsah najbližšieho balíka s jasným rozlíšením zdrojov,
- čerstvosť synchronizácie,
- poslednú publikáciu,
- čakajúce úlohy alebo problémy,
- jednu jasnú cestu k najpravdepodobnejšej ďalšej akcii.

Prehľad nie je kolekcia nesúvisiacich metrík. Každá karta alebo sekcia musí pomáhať rozhodnúť sa alebo konať. Nula bez kontextu, technický heartbeat alebo surový počet záznamov sa nezobrazujú ako hlavná metrika.

### 6.2 Pracovná plocha

Redakčný pult je pracovná plocha. Na širokom monitore smie využívať väčšiu časť šírky a výšky než bežná stránka. Panely majú zmysluplný pomer, spodná hrana pracoviska zostáva vo viewporte a dlhý zoznam či náhľad sa roluje vnútri.

Pracovná plocha nesmie pôsobiť ako malá karta stratená uprostred prázdnej stránky ani ako panel vyšší než obrazovka, ktorého ovládanie zmizne pod spodným okrajom.

### 6.3 Stránka správy objektov

Kanály, Roly a Reakcie sú stránky správy objektov. Majú:

- jednoduchý úvod vysvetľujúci výsledok,
- zreteľné hlavné úlohy,
- prehľad existujúcich alebo čakajúcich položiek,
- prirodzený prázdny stav,
- editáciu v konzistentnom modale alebo detaile.

Nemajú trvalo otvorený komplikovaný formulár vedľa zoznamu, ak používateľ formulár väčšinu času nepotrebuje.

### 6.4 Nastavenia

Nastavenia sa členia podľa oblastí, nie podľa technických služieb. Každá oblasť obsahuje stručné vysvetlenie dopadu, formulár a lokálne uloženie. Dlhá stránka musí mať zrozumiteľnú orientáciu; záložky sa používajú iba pre rovnocenné oblasti, nie na skrytie krokov jednej úlohy.

Neuložené zmeny musia byť rozpoznateľné. Ak by odchod spôsobil stratu väčšieho množstva práce, aplikácia upozorní používateľa. Po uložení sa potvrdí presne, ktorá oblasť bola uložená.

### 6.5 História, audit a stav systému

Tieto stránky slúžia na dohľadanie a vysvetlenie, nie na vystavenie technických dát.

- Najdôležitejšia informácia je čitateľná bez otvorenia detailu.
- Filtre používajú ľudské názvy a dajú sa jednoducho zrušiť.
- Časy sú zobrazené v `Europe/Bratislava` a ich význam je pomenovaný.
- Stav obsahuje dopad na používateľa a odporúčaný ďalší krok.
- Technické podrobnosti sú zbalené v sekundárnom detaile s možnosťou bezpečného kopírovania.

### 6.6 Prihlásenie, zamietnutie prístupu a neočakávaná chyba

Samostatné systémové obrazovky majú zachovať značku Carlo, krátky zrozumiteľný nadpis, vysvetlenie a jednu relevantnú ďalšiu akciu. Používateľ nesmie ako hlavný obsah dostať JSON, nečitateľné kódovanie, stack trace alebo samotný HTTP status.

## 7. Globálne rozloženie a responzivita

### 7.1 Aplikačný rámec

Aplikácia používa stabilný rámec:

- horná lišta s identitou Carla a prihláseného používateľa,
- bočná navigácia na dostatočne širokej obrazovke,
- spodná alebo inak ergonomická mobilná navigácia na úzkej obrazovke,
- hlavný obsah so správnym landmarkom a preskočiteľnou navigáciou.

Horná lišta a navigácia majú používateľovi pomáhať orientovať sa, nie súťažiť s obsahom. Preskočovací odkaz sa zobrazuje iba pri klávesnicovom fokuse a po zatvorení modalu nesmie zostať vizuálne prilepený na stránke.

### 7.2 Šírka obsahu

Bežné čítacie a nastavovacie stránky používajú obmedzenú maximálnu šírku, aby text a formuláre neboli príliš rozťahané. Pracovné plochy môžu použiť široký variant.

- Textový odsek má mať spravidla najviac 60 až 70 znakov na riadok.
- Formulárové pole nemá byť širšie, než vyžaduje očakávaná hodnota.
- Široká obrazovka sa nevyužíva zväčšovaním prázdnych kariet, ale vhodným rozdelením pracovného priestoru.
- Obsah nesmie byť bezdôvodne uzavretý v malom centrálnom paneli.

### 7.3 Behaviorálne breakpointy

Breakpoint sa určuje podľa momentu, keď obsah prestáva byť pohodlne použiteľný, nie podľa konkrétnej značky zariadenia. Povinne sa overujú minimálne šírky približne 360, 768, 1024 a 1440 px. Pre široké pracovisko sa overuje aj 1920 px.

Na užšej obrazovke sa má:

- viacstĺpcové rozloženie skladať podľa priority úloh,
- text tlačidiel zachovať, ak ikona sama nie je jednoznačná,
- tabuľka zmeniť na prioritizované riadky, karty alebo detail,
- sekundárny obsah presunúť pod primárny, nie ho iba zmenšiť,
- akčný panel zostať dostupný bez zakrytia systémovou lištou,
- modal zmeniť na bezpečne rolovateľný takmer celoplošný formát.

Horizontálne rolovanie celej stránky je zakázané od šírky 320 px. Horizontálny posun špecializovaného dátového prvku je prípustný iba ako posledná možnosť a musí mať viditeľnú indikáciu.

### 7.4 Výška a rolovanie

Stránka má mať jeden prirodzený hlavný scroll. Vnorené rolovanie sa používa iba v pracovných plochách, náhľadoch alebo dlhých modalových zoznamoch, kde zachováva dôležitý kontext.

Ak sa použije vnorené rolovanie:

- jeho hranice musia byť vizuálne zrozumiteľné,
- používateľ nesmie uviaznuť medzi dvoma scrollmi,
- fokusovaná položka sa musí dostať do viditeľnej oblasti,
- spodné akcie zostanú dostupné,
- na mobilnom zariadení sa musí overiť správanie s otvorenou klávesnicou.

### 7.5 Dotyk a zväčšenie

Primárne dotykové ciele majú mať aspoň 44 × 44 px. Kompaktné desktopové ikonové akcie môžu mať 36 × 36 px iba vtedy, ak majú dostatočné rozostupy a na dotykovom layoute sa zväčšia. Klikateľný riadok nesmie obsahovať malé konfliktné ciele bez jasného oddelenia.

Rozhranie musí zostať použiteľné pri 200 % zväčšení. Obsah sa má preliať a preskladať, nie odrezať.

## 8. Vizuálny jazyk

### 8.1 Zásada vizuálnej hierarchie

Na jednej obrazovke má byť zrejmé poradie:

1. názov a účel stránky,
2. najdôležitejší stav alebo úloha,
3. hlavný obsah,
4. sekundárne vysvetlenia a metadáta,
5. diagnostické podrobnosti.

Hierarchia sa vytvára kombináciou umiestnenia, veľkosti, medzier, farby a váhy písma. Tieň, rámik alebo farebné pozadie sa nepoužijú na každú sekciu naraz.

### 8.2 Typografia

Primárne písmo je Geist Variable s vhodným systémovým fallbackom. Typografia má byť pokojná, dobre čitateľná a úsporná.

- Na stránke je práve jeden nadpis `h1`.
- Úrovne nadpisov sa nepreskakujú kvôli vzhľadu.
- Hlavný nadpis je výrazný, ale nie marketingovo prehnaný.
- Bežný text má pohodlnú výšku riadku približne 1,45 až 1,6.
- Pomocný text nesmie byť taký malý alebo bledý, že sa stane dekoráciou.
- Celé vety sa nepíšu veľkými písmenami.
- Čísla, dátumy a časy sa používajú konzistentne a bez zbytočne technického formátu.

Veľkosti sa vyberajú zo spoločnej typografickej škály. Jednorazové lokálne veľkosti bez pomenovaného významu sa nepridávajú.

### 8.3 Farby a význam

Aktuálny vizuálny základ používa tieto sémantické tokeny:

| Token                        | Aktuálny charakter           | Použitie                      |
| ---------------------------- | ---------------------------- | ----------------------------- |
| `--canvas`                   | svetlá jemne zelenosivá      | pozadie aplikácie             |
| `--surface` / `--card`       | biela                        | obsahové povrchy              |
| `--ink` / `--foreground`     | tmavá zelenočierna           | primárny text                 |
| `--ink-muted`                | tlmená sivá so zeleným tónom | sekundárny text               |
| `--line` / `--border`        | jemná sivá                   | deliace línie a okraje        |
| `--brand`                    | zelená                       | primárna akcia a aktívny stav |
| `--brand-strong`             | tmavšia zelená               | hover a dôraz                 |
| `--brand-soft`               | svetlá zelená                | vybraný alebo podporný povrch |
| `--warning`                  | teplá oranžovohnedá          | upozornenie                   |
| `--danger` / `--destructive` | červená                      | chyba a deštruktívna akcia    |

Opakované farby sa nesmú zapisovať ako náhodné lokálne hex hodnoty. Najprv sa použije existujúci sémantický token; nový token vznikne iba pre nový opakovateľný význam.

Farba nikdy nesmie byť jediným nositeľom informácie. Stav dopĺňa text, ikona, tvar alebo umiestnenie. Kontrast textu a ovládacích prvkov musí spĺňať WCAG AA.

INFO oznamy a udalosti si v Discord náhľade zachovávajú odlišné farebné rodiny podľa kanonického composer modelu. Ich farba nie je dekoratívna zámennosť, ale pomáha rozlíšiť typ obsahu. Paleta náhľadu sa nemení nezávisle od skutočne publikovaných správ.

### 8.4 Medzery

Základom je štvorpixelový rytmus. Odporúčaná škála je 4, 8, 12, 16, 24, 32 a 48 px.

- Vzdialenosť medzi labelom a jeho poľom je menšia než vzdialenosť medzi dvoma poliami.
- Súvisiace prvky sú bližšie pri sebe než nesúvisiace sekcie.
- Vnútorný padding podobných kariet a modalov je rovnaký.
- Veľké prázdne plochy musia mať funkčný význam; nesmú vznikať iba nevhodným `max-width`.

### 8.5 Rohy, okraje a tiene

Zaoblenie vyjadruje hierarchiu:

- menšie ovládacie prvky používajú mierne zaoblenie,
- karty a obsahové panely používajú stredné zaoblenie,
- modaly môžu mať o stupeň výraznejšie zaoblenie.

Okraj je predvolený spôsob oddelenia povrchov. Tieň sa používa jemne na zdvihnuté prvky, modal alebo dôležitý panel. Silné tiene a kombinácia viacerých efektov sú zakázané.

### 8.6 Ikony

Primárna ikonová sada je Lucide. Ikony majú mať konzistentnú hrúbku a veľkosť v rámci jedného kontextu.

- Dekoratívna ikona má `aria-hidden="true"`.
- Ikonové tlačidlo má prístupný názov a tooltip.
- Ikona nenahrádza text pri neznámej alebo kritickej akcii.
- Rovnaká ikona sa nepoužíva pre dva odlišné významy v tom istom pracovisku.
- Emoji sa používajú tam, kde sú súčasťou Discord obsahu alebo významu, nie ako náhodná náhrada systémových ikon.

### 8.7 Téma a režimy zobrazenia

Podporovaný vizuálny režim musí byť dokončený v celej aplikácii. Carlo v súčasnosti používa svetlú tému. Tmavá téma sa nesmie pridať iba pre časť stránok alebo ako automatická inverzia farieb; pred jej uvedením musí mať úplnú sadu sémantických tokenov, kontrastné overenie, Discord náhľad, stavy komponentov a browser testy.

Farba systémových formulárov, scrollbarov a prehliadačových prvkov má zodpovedať podporovanej téme. Systémová preferencia nesmie vytvoriť nečitateľnú kombináciu, ktorú aplikácia sama nepodporuje.

## 9. Obsahový dizajn a jazyk

### 9.1 Tón Carla

Carlo komunikuje pokojne, stručne a priamo. Nie je chladný, hravý za každú cenu ani mentorsky technický. Text má pôsobiť ako pomoc kompetentného kolegu.

Používa sa spisovná a prirodzená slovenčina. Anglický alebo technický termín sa ponechá iba vtedy, ak je to zaužívaný názov služby alebo by preklad znižoval zrozumiteľnosť, napríklad Discord či Google Kalendár.

### 9.2 Názvy akcií

Tlačidlo pomenúva výsledok pomocou slovesa a predmetu:

- „Vytvoriť kanál“ namiesto „Potvrdiť“,
- „Uložiť zmeny“ namiesto „OK“,
- „Publikovať teraz“ namiesto „Triggernúť“,
- „Načítať udalosti znova“ alebo presnejšie vysvetlenie namiesto nejasného „Obnoviť draft“.

Rovnaká akcia má mať všade rovnaký názov. Text tlačidla sa nesmie meniť len kvôli vizuálnej pestrosti.

### 9.3 Nadpisy a pomocný text

Nadpis pomenúva objekt alebo úlohu. Podnadpis jednou až dvoma vetami vysvetlí účel a dopad, nie internú implementáciu.

Pomocný text sa pridáva iba vtedy, ak odpovedá na reálnu otázku používateľa. Zbytočné vysvetlenie samozrejmosti, technický pôvod dát alebo text bez vplyvu na rozhodnutie sa odstráni.

### 9.4 Formulárové texty

- Label je krátky názov údaja a zostáva viditeľný aj po vyplnení.
- Placeholder ukazuje príklad alebo formát; nikdy nenahrádza label.
- Voliteľnosť sa označuje slovom „voliteľné“, nie hviezdičkou bez vysvetlenia.
- Povinnosť sa oznamuje konzistentne a nie pri každom poli iným spôsobom.
- Pomocný text vysvetlí dôsledok alebo obmedzenie pred odoslaním.
- Počítadlo znakov sa zobrazuje iba tam, kde používateľovi pomáha rešpektovať reálny limit.

### 9.5 Chyby

Chybová správa má tri časti podľa potreby:

1. čo sa nepodarilo,
2. čo to znamená pre používateľa,
3. čo môže urobiť ďalej.

Príklad: „Kanál sa nepodarilo vytvoriť. Na Discorde sa nič nezmenilo. Skontrolujte oprávnenia Carla alebo to skúste znova.“

Zakázané sú samotné texty „Invalid request“, „403“, „Unknown error“ alebo surový JSON. Korelačné ID môže byť v zbalených diagnostických detailoch s tlačidlom na kopírovanie.

### 9.6 Dátumy, časy a počty

- Časy sa zobrazujú v `Europe/Bratislava`, ak nie je výslovne uvedené inak.
- Pri relatívnom čase sa podľa významu doplní presný čas, napríklad „pred 12 minútami · 19:48“.
- Celodenný viacdenný rozsah je používateľsky inkluzívny.
- Termín „dnes“ alebo „zajtra“ sa nepoužíva bez dátumu tam, kde môže stránka zostať otvorená dlhšie.
- Počty sa formulujú prirodzene alebo sa používajú neutrálne označenia, ktoré sa negramaticky nelámu.

## 10. Komponentové štandardy

### 10.1 Znovupoužitie komponentov

Pred vytvorením nového prvku sa musí overiť, či už existuje vhodný komponent v spoločnej UI vrstve alebo vyšší doménový komponent. Základom sú komponenty Base UI a spoločné shadcn-style primitíva, nie ad hoc napodobneniny v CSS jednej stránky.

Spoločný komponent má riešiť správanie, prístupnosť a stavy. Stránka dodáva obsah a doménový kontext. Ak dva prvky vyzerajú rovnako, ale správajú sa odlišne, treba rozdiel vedome pomenovať alebo ich zjednotiť.

### 10.2 Tlačidlá

Používajú sa tieto významové úrovne:

| Variant              | Použitie                                         |
| -------------------- | ------------------------------------------------ |
| Primárny             | hlavná bezpečná akcia aktuálneho kroku           |
| Sekundárny / outline | alternatívna alebo podporná akcia                |
| Ghost                | nízky dôraz, lokálna nástrojová akcia            |
| Destructive          | odstránenie alebo nebezpečná zmena               |
| Link                 | navigačná textová akcia, nie odoslanie formulára |

V jednom akčnom bloku má byť spravidla jedno primárne tlačidlo. Deštruktívne tlačidlo nesmie vizuálne vyzerať ako bezpečné primárne tlačidlo.

Tlačidlo musí mať stavy default, hover, active, focus-visible, disabled a loading. Pri loading stave:

- zachová približne svoju šírku,
- nedovolí opakované odoslanie,
- oznámi prebiehajúcu činnosť,
- nestratí zrozumiteľný názov akcie.

Zakázané je deaktivovať tlačidlo bez vysvetlenia, ak dôvod nie je z formulára zrejmý.

### 10.3 Klikateľné riadky a karty

Riadok sa používa pre položky rovnakej kolekcie, ktoré sa skenujú alebo porovnávajú. Karta sa používa pre samostatný súhrn, úlohu alebo výrazne odlišný obsah. Rovnaké entity sa na susedných stránkach nesmú svojvoľne raz zobraziť ako karty a raz ako iný vizuálny systém.

Ak kliknutie na riadok otvára detail alebo editor:

- celý hlavný obsah riadka je klikateľný,
- riadok je fokusovateľný a aktivovateľný klávesmi Enter a podľa konvencie Space,
- má viditeľný hover a focus stav,
- zostáva v ňom explicitné tlačidlo „Upraviť“ pre objaviteľnosť,
- vnorené akcie nezapnú zároveň akciu riadka.

### 10.4 Formuláre

Formulár má sledovať prirodzené poradie rozhodnutí. Povinné údaje sú prvé, voliteľné možnosti sa odhaľujú neskôr. Súvisiace polia sa zoskupujú pod stručným nadpisom.

- Každé pole má programovo prepojený label.
- Chyba sa zobrazí pri poli a súhrnná chyba pri formulári len vtedy, ak je to potrebné.
- Validácia počas písania nesmie trestať používateľa za nedokončenú hodnotu.
- Pri odoslaní sa fokus presunie na prvú chybu alebo na zrozumiteľný chybový súhrn.
- Zadané hodnoty sa po chybe nestratia.
- Automatická úprava vstupu musí byť predvídateľná a viditeľná.
- Serverová normalizácia musí zodpovedať správaniu vo webovom formulári.
- Uloženie musí byť idempotentné voči dvojkliku alebo opakovaniu požiadavky.

Názov Discord kanála je vzorom dobrej živej normalizácie: slovenská diakritika sa zachová, písmená sa zmenia na malé a medzery či nepovolené symboly sa počas písania premenia na pomlčku. Composition input sa nesmie poškodiť.

### 10.5 Výber ľudí

Výber ľudí musí fungovať ako priebežné vyhľadávanie:

- výsledky sa objavujú počas písania bez tlačidla „Hľadať“,
- dopyt je debounceovaný a zastarané odpovede sa ignorujú alebo zrušia,
- výsledok zobrazuje avatar, zobrazované meno a Discord meno,
- už zvolený človek sa nezvolí duplicitne,
- vybrané osoby sa zobrazia ako čitateľné čipy primerané avataru,
- každý čip sa dá odstrániť klávesnicou aj myšou,
- viacnásobný výber sa dá vrátiť na nulu,
- po výbere alebo odstránení sa dopyt a výsledky vyčistia a fokus sa vráti do vyhľadávania,
- stavy „píšte aspoň…“, „hľadám“, „bez výsledku“ a chyba sú rozlíšené.

Natívny viacnásobný select nie je prípustný pre ľudí.

### 10.6 Výber rolí, kanálov a skupín

Viacnásobný výber rolí a kanálov používa rovnaký mentálny model ako výber ľudí: filtrovanie, zreteľný výber, odstrániteľné čipy alebo zaškrtávacie riadky a možnosť „Zrušiť výber“.

- Používateľ sa musí vedieť vrátiť k nule vybraných položiek.
- Po zbalení sekcie zostáva v názve viditeľný počet vybraných položiek.
- Zakázaná položka musí mať zrozumiteľný dôvod, nie iba sivý stav.
- Pri roliach sa jasne odlíši rola od konkrétneho človeka.
- Pri kanáloch sa zobrazí typ a kategória iba vtedy, ak pomáhajú rozhodnúť.
- Natívny `<select multiple>` sa nepoužíva.

### 10.7 Rozbaľovacie sekcie

Všetky disclosure riadky v rovnakom formulári musia mať rovnakú výšku, padding, typografiu, stav pozadia, umiestnenie ikony a šípky.

Riadok obsahuje:

1. významovú ikonu,
2. stručný názov,
3. voliteľný súhrn, napríklad počet vybraných skupín,
4. šípku, ktorá sa pri otvorení otočí,
5. rozbalený obsah s vlastným paddingom a vizuálnym ohraničením.

Samostatný podnadpis opakujúci názov rozbaľovacieho riadka sa nepridáva. Celý riadok je klikateľný a má `aria-expanded`.

### 10.8 Záložky

Záložky sa používajú pre rovnocenné pohľady alebo kategórie, medzi ktorými používateľ vedome prepína. Nepoužívajú sa:

- na oddelenie obsahu od náhľadu toho istého výsledku,
- ako náhrada krokov formulára,
- na skrytie kritického stavu,
- ak používateľ potrebuje porovnávať oba obsahy súčasne.

Aktívna záložka musí byť viditeľná, programovo označená a po reloadnutí alebo deep linku predvídateľná.

### 10.9 Modaly

Modal sa používa pre sústredenú úlohu, ktorá patrí do kontextu aktuálnej stránky a po dokončení používateľa prirodzene vráti späť. Vytvorenie kanála, archivácia a redakcia položky sú vhodné modálne úlohy.

Modal musí:

- byť centrovaný na desktope,
- mať jednoznačný názov a voliteľný stručný popis,
- zachytiť fokus a po zatvorení ho vrátiť na presný spúšťač,
- umožniť bezpečné zatvorenie tlačidlom a klávesom Escape, ak sa práve nevykonáva kritická operácia,
- zablokovať interakciu s pozadím,
- mať obsah rolovateľný bez straty hlavičky alebo spodných akcií,
- na mobile rešpektovať viewport, systémové okraje a otvorenú klávesnicu,
- mať v päte sekundárnu akciu vľavo alebo pred primárnou podľa poradia čítania a primárnu akciu na konci.

Modal sa nepoužíva pre dlhý viacstránkový proces, rozsiahle porovnávanie alebo obsah, ktorý potrebuje vlastnú adresu.

### 10.10 Potvrdzovacie dialógy

Potvrdenie je povinné pri publikovaní, zmene citlivej roly, schválení archivácie a iných externe viditeľných alebo ťažko vratných akciách.

Dialóg musí pomenovať konkrétny objekt a dôsledok. Primárna deštruktívna akcia má presný názov, nie „Áno“. Bezpečná akcia „Zrušiť“ má dostať po otvorení rozumný predvolený fokus, ak by Enter na nebezpečnej akcii predstavoval riziko.

### 10.11 Popovery, tooltipy a výber emoji

Tooltip vysvetľuje ikonovú akciu alebo krátky pojem. Nesmie obsahovať jediný prístup k dôležitej funkcii a musí byť dostupný aj fokusom.

Popover je vhodný na kompaktný výber, napríklad katalóg emoji. Výber emoji musí:

- ponúknuť niekoľko kontextových návrhov, ktoré sa dynamicky menia podľa názvu,
- mať poslednú zreteľnú akciu na otvorenie celého katalógu,
- v katalógu ponúknuť všetky podporované emoji, nie svojvoľne obmedzený zoznam,
- mať kvalitné vyhľadávanie podľa slovenských aj bežných názvov,
- správne spracovať „bez výsledku“, vyčistenie a návrat fokusu,
- nevysvetľovať interný pôvod emoji, ak to používateľ nepotrebuje.

### 10.12 Prepínače, checkboxy a rádio voľby

- Switch sa používa pre okamžite zrozumiteľný zapnutý/vypnutý stav.
- Checkbox sa používa pre nezávislé voľby alebo potvrdenie podmienky.
- Rádio voľba sa používa, keď je povolená práve jedna z malého počtu možností.
- K dispozícii musí byť textový label; samotná poloha alebo farba nestačí.
- Ak zmena switchu vykonáva okamžitú externú operáciu, musí to byť z textu jasné a musí mať stav ukladania aj chyby.

### 10.13 Status badge

Badge je krátky sekundárny indikátor, nie náhrada vysvetlenia. Používa konzistentné slová, napríklad „Pripravené“, „Čaká na schválenie“, „Publikované“, „Vylúčené“, „Chyba“.

Interné enum hodnoty sa mapujú na ľudský text. Každý stav má rovnakú farbu a názov na všetkých stránkach.

### 10.14 Nahrávanie obrázkov

INFO obrázky sa nahrávajú priamo. Upload musí obsahovať:

- zrozumiteľnú drop zónu aj klasické tlačidlo výberu súboru,
- informáciu o podporovaných typoch a limite pred výberom,
- náhľad obrázka,
- priebeh nahrávania pri citeľnom čakaní,
- možnosť obrázok nahradiť alebo odstrániť,
- lokálnu chybu bez straty ostatného formulára,
- bezpečné spracovanie nevhodného alebo poškodeného súboru.

Prázdne URL pole nesmie byť hlavný spôsob pridania obrázka.

### 10.15 Vyhľadávanie, filtre a radenie

Vyhľadávanie sa používa, keď používateľ pozná aspoň časť názvu alebo identity. Filter zužuje výsledky podľa známej vlastnosti. Radenie mení poradie bez zmeny množiny. Tieto tri funkcie sa nesmú miešať do jedného nejasného ovládacieho prvku.

- Aktívny filter musí byť viditeľný aj po zatvorení ovládania.
- Všetky filtre sa dajú zrušiť jednou jasnou akciou, ak ich môže byť viac.
- Počet výsledkov musí hovoriť, či opisuje všetky dáta alebo filtrovaný pohľad.
- Stav bez výsledkov po filtrovaní sa odlišuje od skutočne prázdneho zoznamu.
- Textové vyhľadávanie zachováva dopyt pri otvorení detailu a návrate, ak je to užitočné.
- Radenie má ľudský názov, viditeľný smer a stabilné sekundárne poradie.
- Aplikácia nesmie automaticky preusporiadať používateľom spravované poradie, ak na to nemá výslovné a zrozumiteľné pravidlo.

### 10.16 Tabuľky a dlhé zoznamy

Tabuľka sa používa iba vtedy, keď používateľ potrebuje porovnávať viac položiek podľa rovnakých stĺpcov. Ak je primárnou úlohou prečítať súhrn a konať nad jednou položkou, vhodnejší je riadkový zoznam.

- Stĺpce sú zoradené podľa používateľskej dôležitosti, nie podľa dátového modelu.
- Primárna identita zostáva viditeľná a nepresúva sa za technické metadáta.
- Akcie sú pomenované alebo majú prístupný názov a tooltip.
- Na mobile sa menej dôležité stĺpce presunú do detailu; text sa nesmie stlačiť do nečitateľných pásov.
- Paginácia zachová filtre a má zrozumiteľný rozsah výsledkov.
- Priebežné načítavanie nesmie spôsobiť stratu pozície ani preskočenie fokusu.
- Hromadná akcia sa objaví až po výbere, zobrazuje počet položiek a dá sa bezpečne zrušiť.

## 11. Systém stavov a spätnej väzby

Každá dátová oblasť musí mať navrhnuté minimálne stavy načítava sa, načítané, prázdne, chyba, bez oprávnenia a zastarané dáta. Formulár navyše potrebuje neuložené zmeny, ukladá sa, úspech, validačnú chybu, konflikt a externé zlyhanie.

### 11.1 Načítanie

- Pri prvom načítaní sa používa skeleton podobný výslednému layoutu alebo pokojný lokálny loader.
- Už načítaný obsah sa pri tichom obnovení zbytočne nemaže.
- Celá stránka sa nezablokuje kvôli jednej nezávislej sekcii.
- Po približne jednej sekunde má byť zrejmé, že aplikácia pracuje.
- Dlhšia operácia oznámi, čo sa vykonáva; falošný percentuálny progress sa nepoužíva.

### 11.2 Prázdny stav

Prázdny stav obsahuje:

1. čo je prázdne,
2. či je to normálne alebo problém,
3. čo môže používateľ urobiť.

Musí byť presne ohraničený. Ak filter „Google Kalendár“ nemá výsledky, text nesmie tvrdiť, že najbližší oznam nemá žiadny obsah. Prázdny stav nemá byť veľká dekoratívna karta, ak postačí krátka pokojná správa v kontexte zoznamu.

### 11.3 Úspech

Úspech sa oznamuje pri mieste akcie a cez primeraný `aria-live` región. Text pomenúva výsledok. Dočasný toast je vhodný pre jednoduchú operáciu; trvalejší nový stav na stránke musí úspech aj sám dokazovať.

Úspešná hláška nesmie zakryť ďalšiu potrebnú akciu ani zmiznúť skôr, než ju možno prečítať.

### 11.4 Chyba a zotavenie

Rozlišujú sa:

- chyba jedného poľa,
- chyba celej požiadavky,
- nedostupnosť externej služby,
- konflikt so zmenou iného používateľa,
- strata oprávnenia,
- čiastočný úspech,
- nejasný výsledok externej operácie.

Pri konflikte aplikácia nesmie potichu prepísať novšie údaje. Ukáže, čo sa zmenilo, a ponúkne znovunačítanie alebo vedomé zlúčenie. Pri nejasnom výsledku Discord operácie sa nesmie tvrdiť ani úspech, ani bezpečné zlyhanie; používateľ dostane stav a postup overenia.

### 11.5 Zastarané dáta

Ak obsah vychádza zo starej cache alebo posledná synchronizácia zlyhala, musí to byť viditeľné pri príslušnom obsahu. Zobrazí sa čas posledného úspechu, dopad a možnosť nápravy. Historický úspech sa nesmie prezentovať ako aktuálne zdravie.

### 11.6 Optimistické zmeny

Optimistická aktualizácia je prípustná iba pri ľahko vratnej operácii s nízkym rizikom. Publikovanie, vytvorenie kanála, archivácia a zmena rolí musia počkať na potvrdený výsledok. Ak sa optimistická zmena nepodarí, musí sa spoľahlivo vrátiť a vysvetliť.

## 12. Interakcie a pohyb

### 12.1 Odozva

Každý stlačiteľný prvok reaguje okamžite vizuálnym stavom. Prechod hover/focus/otvorenie má byť spravidla 120 až 250 ms. Pohyb podporuje pochopenie vzťahu, nie dekoráciu.

### 12.2 Fokus

Viditeľný `focus-visible` stav je povinný a nesmie byť odstránený bez náhrady. Poradie fokusu sleduje vizuálne a významové poradie. Po dynamickej operácii sa fokus presunie len vtedy, ak to pomáha pokračovať:

- po otvorení modalu na názov alebo prvé pole,
- po chybe na chybový súhrn alebo prvé neplatné pole,
- po zatvorení modalu na jeho spúšťač,
- po pridaní alebo odstránení osoby späť do vyhľadávania,
- po odstránení položky na logického suseda alebo nadpis zoznamu.

### 12.3 Redukovaný pohyb

Pri `prefers-reduced-motion` sa odstránia alebo zásadne skrátia neesenciálne animácie. Obsah nesmie byť dostupný iba po animácii, hoveri alebo geste.

## 13. Doménové štandardy jednotlivých oblastí

### 13.1 Redakčný pult

Redakčný pult je jedno pracovisko pre všetok obsah najbližšej publikácie.

Musí:

- zobrazovať spoločný chronologický zoznam kalendárových, manuálnych a INFO položiek,
- jasne označiť zdroj bez vizuálneho rozbitia na tri aplikácie,
- uvádzať celkový počet položiek a oddelené počty iba ako filtre,
- ponechať vylúčenú udalosť viditeľnú s dôvodom a cestou na opätovné zaradenie,
- otvoriť editor kliknutím na riadok aj tlačidlom „Upraviť“,
- zobrazovať viacdenné celodenné udalosti ako inkluzívny rozsah,
- zachovať redakčné úpravy konkrétneho výskytu alebo série podľa zvoleného rozsahu,
- ukazovať verný náhľad kanonického publikačného draftu,
- umožniť dokončiť bežnú úpravu bez prepínania routy.

Filter mení pohľad na spoločný obsah, nie význam celkových metrík. Po zrušení filtra sa používateľ vráti k celému prehľadu bez straty rozpracovanej bezpečne uloženej práce.

### 13.2 Discord náhľad

Náhľad je dôveryhodná simulácia výstupu, nie marketingová karta ani druhý editor.

- Zobrazuje identitu bota Carlo a štruktúru správ podobnú reálnemu Discord kanálu.
- Obsahuje presný úvod, `@everyone`, embedy, titulky, popisy, day emoji/author časť, odkazy, thumbnails a plánovanú seen reakciu.
- Rešpektuje Discord delenie na viac správ a limity.
- Používa rovnaký kanonický composer ako publikovanie.
- Nepridáva vymyslený názov alebo popis kanála, ktorý sa nepublikuje.
- Nie je schovaný v záložke „Discord preview“ vedľa alternatívnej záložky „Obsah“, ak používateľ potrebuje sledovať úpravu a výsledok naraz.
- INFO a udalosti používajú zachované odlišné farebné palety.
- Na mobile môže byť pod zoznamom alebo v jasne dostupnom režime, ale nesmie sa zmeniť na nepresnú zjednodušenú reprezentáciu.

### 13.3 Kanály

Stránka Kanály komunikuje hlavné úlohy, nie Discord permission model.

Tvorba kanála musí:

- predvoliť bezpečné umiestnenie podľa Nastavení,
- neponúknuť archívnu kategóriu ani kategóriu s hlasovými/stage kanálmi,
- vysvetliť umiestnenie jednou vetou a umožniť ho zmeniť cez konzistentný disclosure riadok,
- normalizovať názov počas písania bez poškodenia diakritiky,
- navrhovať štyri kontextové emoji a ponúknuť úplný vyhľadateľný katalóg,
- používať kvalitné výbery vedúcich, členov a rolí,
- zobrazovať počet vybraných skupín aj po zbalení,
- pred vytvorením zrozumiteľne zhrnúť výsledok.

Po vytvorení sa kanál v kategórii zoradí abecedne iba vtedy, ak bola kategória abecedne zoradená už predtým. Rozhranie nemá sľubovať zmenu poradia, ak sa pôvodné poradie zachováva.

Archivácia má mať rovnocennú vizuálnu starostlivosť ako tvorba. Musí vysvetliť, že žiadosť sama osebe ešte kanál nemení, ukázať čakajúci stav a pri schválení pomenovať dopad.

### 13.4 Roly

Správa rolí musí byť orientovaná na človeka, nie na zoznam Discord ID.

- Člen sa vyhľadáva interaktívne s avatarom a identitou.
- Aktuálne relevantné roly sú jasne označené.
- Zmena Admin alebo Team Mod roly má explicitné potvrdenie s menom osoby a dôsledkom.
- Systém vysvetlí hierarchické obmedzenie a nesmie ponúkať falošnú úspešnosť.
- Ochrana posledného spravovateľného Admina sa komunikuje ľudským textom.

### 13.5 Reakcie

Stránka Reakcie spája výber emoji, výber kanálov a možnosť bezpečného testu.

- Aktívne emoji sa zobrazí vizuálne aj textom.
- Nedostupné vlastné emoji je označené ako problém s postupom nápravy.
- Výber kanálov podporuje vyhľadávanie, viacnásobný výber a vyčistenie na nulu.
- Test emoji jasne povie, kam bude reakcia odoslaná a či ide o reálnu externú akciu.
- Automatická reakcia pri zmienke a reakcie vo vybraných kanáloch sú oddelené pravidlá s jasným dopadom.

### 13.6 Nastavenia publikovania a kalendáre

Nastavenia musia zobrazovať aktuálnu hodnotu, dopad zmeny a stav uloženia.

- Deň, čas a časové pásmo tvoria jednu logickú skupinu.
- Cieľový kanál sa vyberá podľa názvu a kategórie.
- Riadené použitie `@everyone` je vysvetlená vlastnosť publikácie, nie klamlivo vypínateľná voľba.
- Pravidlá Google popisu zrozumiteľne rozlišujú zdrojový a redakčný popis.
- Každý kalendár má názov, stav, poslednú úspešnú synchronizáciu a konkrétnu chybu.
- Celkový stav integrácie nesmie byť zelený, ak niektorý aktívny zdroj nikdy neuspel alebo je zastaraný.
- Ručná synchronizácia má stav priebehu a po dokončení povie, čo sa aktualizovalo.

## 14. Prístupnosť

Minimálnym cieľom je WCAG 2.1 AA; nové komponenty sa majú posudzovať aj podľa relevantných zlepšení WCAG 2.2 AA.

### 14.1 Klávesnica

Všetky funkcie musia byť ovládateľné klávesnicou bez časového tlaku. Povinne sa overuje:

- preskočenie navigácie,
- logické poradie Tab a Shift+Tab,
- otvorenie a zatvorenie menu, popoverov a modalov,
- aktivácia tlačidiel a klikateľných riadkov,
- výber a odstránenie čipov,
- práca s dynamickými výsledkami vyhľadávania,
- fokus po úspechu, chybe, odstránení a zatvorení.

### 14.2 Sémantika a čítačky obrazovky

- Používajú sa natívne HTML prvky a landmarky vždy, keď je to možné.
- Každá stránka má logickú štruktúru nadpisov.
- Polia majú labels, chyby sú prepojené cez `aria-describedby` alebo ekvivalent.
- Aktívny stav, rozbalenie, výber a neplatnosť sú programovo vyjadrené.
- Dynamické výsledky a stav operácie používajú primerané live regióny bez zahltenia.
- Dekoratívne obrázky majú prázdny `alt`; významové obrázky majú stručný alternatívny text.
- Tooltip nesmie byť jediný zdroj dôležitej informácie.

### 14.3 Kontrast a nefarebné signály

Text, fokus, hranice polí a stavové prvky musia dosahovať primeraný kontrast. Chyba, úspech, výber alebo stav nesmie byť vyjadrený iba červenou, zelenou či zmenou odtieňa.

### 14.4 Reflow, zoom a pohyb

Pri 200 % zoome zostávajú všetky akcie dostupné a text sa neprekrýva. Pri úzkom viewporte sa obsah preleje bez horizontálneho rolovania stránky. `prefers-reduced-motion` sa rešpektuje.

## 15. Dôvera, bezpečnosť a ochrana údajov v UX

- Tajomstvá, bot tokeny, OAuth tokeny a servisné credentials sa nikdy nezobrazujú v prehliadači.
- Interné ID sa používajú iba v sekundárnej diagnostike, ak sú potrebné na podporu.
- Citlivá operácia zobrazuje konkrétny cieľ a dôsledok pred potvrdením.
- Rozhranie nesmie tvrdiť úspech pred serverovým potvrdením.
- Pri nejasnom výsledku sa zobrazí neutrálne „Výsledok overujeme“ alebo zodpovedajúci incident stav.
- Používateľské vstupy a názvy externých objektov sa zobrazujú bezpečne bez interpretácie ako HTML.
- Odkaz smerujúci mimo Carla má byť z kontextu rozpoznateľný.
- Odhlásenie, vypršanie relácie a strata role majú zrozumiteľný tok bez straty informácie o tom, čo sa nepodarilo uložiť.

## 16. Výkon a vnímaná rýchlosť

Používateľ má dostať vizuálnu odozvu do 100 ms od interakcie. Bežná lokálna zmena má pôsobiť okamžite. Ak operácia trvá približne viac než jednu sekundu, zobrazí sa stav práce; pri dlhšej operácii sa vysvetlí jej fáza alebo možnosť bezpečne pokračovať inde.

- Routy sa načítavajú oddelene a zobrazujú zmysluplný fallback.
- Vyhľadávanie ľudí, rolí, kanálov a emoji je debounceované podľa zdroja dát.
- Zastarané odpovede nesmú prepísať novší dopyt.
- Obrázky sa zobrazujú v primeranej veľkosti a nespôsobujú layout shift.
- Znovunačítanie jednej sekcie nemá vymazať celú stránku.
- Veľké zoznamy sa stránkujú alebo virtualizujú až podľa reálneho objemu, nie preventívne na úkor použiteľnosti.

## 17. Zakázané antipatterny

Nasledujúce riešenia sú výslovne neprípustné, pretože už viedli alebo pravdepodobne povedú k nejasnému rozhraniu:

- formulár natlačený trvalo v bočnom stĺpci bez priestoru a kontextu,
- malý pracovný panel stratený na veľkom monitore,
- pracovisko vyššie než viewport s nedostupným spodkom,
- tri oddelené administrácie pre obsah jedného oznamu,
- samostatné záložky „Obsah“ a „Discord preview“, ak majú byť videné naraz,
- vizuálne nepresný náhľad s vymyslenými textami alebo inou štruktúrou než výsledný Discord,
- samostatná nulová metrika prezentovaná ako nulový celkový obsah,
- odlišný kartový layout pre INFO bez doménového dôvodu,
- technické názvy akcií ako „trigger“, „draft refresh“, enum alebo endpoint,
- surový JSON ako chybová stránka,
- natívny viacnásobný select vyžadujúci Ctrl/Cmd,
- výber, ktorý sa nedá vrátiť na nulu,
- vyhľadávanie, pri ktorom po výbere zostane starý dopyt aj výsledky,
- čip menší než jeho avatar alebo s nestabilnou výškou,
- disclosure bez šípky, súhrnu a zreteľnej klikateľnosti,
- rôzne disclosure riadky s odlišnou výškou a štruktúrou v tom istom formulári,
- textové pole „použiť iný symbol“ namiesto kvalitného emoji pickera,
- obmedzený náhodný zoznam emoji bez úplného vyhľadateľného katalógu,
- pomocný text vysvetľujúci technické detaily bez úžitku,
- zakázanie medzery alebo diakritiky namiesto prirodzenej živej normalizácie,
- klikateľnosť alebo dôležitá informácia dostupná iba hoverom,
- deaktivované tlačidlo bez zrozumiteľného dôvodu,
- modal bez návratu fokusu alebo s odrezanou pätou,
- preskočovací odkaz viditeľne uviaznutý po zatvorení modalu,
- farba ako jediný indikátor stavu,
- horizontálny scroll celej mobilnej stránky,
- lokálne hardcoded farby, spacing a komponenty kopírujúce existujúci systém,
- potvrdenie každej triviálnej akcie alebo naopak chýbajúce potvrdenie citlivej akcie,
- falošný úspech pred dokončením operácie na Discorde alebo v Kalendári.

## 18. Proces návrhu a zmeny

### 18.1 Pred implementáciou

Pri každej novej alebo významne menenej funkcii sa musí odpovedať:

1. Kto funkciu používa a na akú úlohu?
2. Do ktorej existujúcej oblasti a typu stránky patrí?
3. Dá sa použiť existujúci komponent alebo vzor?
4. Aká je hlavná akcia a aký je bezpečný návrat?
5. Aké sú všetky dátové a systémové stavy?
6. Čo sa stane na 360 px, 768 px, 1024 px, 1440 px a pri 200 % zoome?
7. Ako sa tok dokončí klávesnicou?
8. Aké oprávnenia a externé dôsledky má akcia?
9. Aký text potrebuje netechnický používateľ na správne rozhodnutie?
10. Ako sa dokáže, že náhľad alebo stav je pravdivý?

Pri zložitejšej zmene sa pred kódom pripraví jednoduchý tok, wireframe alebo prototyp. Má riešiť hierarchiu a správanie, nie iba farby.

### 18.2 Počas implementácie

- Použijú sa spoločné tokeny a komponenty.
- Implementujú sa všetky stavy, nie iba ideálny úspech.
- Responzívne správanie sa overuje priebežne.
- Prístupnosť sa rieši v komponente, nie dodatočným patchom stránky.
- Mikrotext sa kontroluje v reálnom kontexte a so slovenskými dlhými hodnotami.
- `STATUS.md` sa aktualizuje v tom istom pracovnom kroku.

### 18.3 Dizajnová výnimka

Výnimka zo štandardu musí obsahovať:

- pravidlo, od ktorého sa odchyľuje,
- používateľský alebo technický dôvod,
- posúdené alternatívy,
- dopad na prístupnosť a konzistentnosť,
- vlastníka rozhodnutia,
- dátum a podmienku budúceho prehodnotenia.

„Na tejto stránke to vyzeralo lepšie“ nie je dostatočný dôvod.

## 19. Povinná kontrola kvality

### 19.1 Kontrolný zoznam návrhu

- [ ] Stránka má jednu jasnú hlavnú úlohu alebo zrozumiteľne zoradené úlohy.
- [ ] Názov, podnadpis, čísla a prázdne stavy presne opisujú svoj rozsah.
- [ ] Funkcia je na správnom mieste informačnej architektúry.
- [ ] Primárna akcia je zrejmá bez prečítania celej stránky.
- [ ] Pokročilé možnosti sú odhalené postupne a objaviteľne.
- [ ] Rozhranie používa netechnickú slovenčinu.
- [ ] Nevznikol duplicitný vizuálny alebo behaviorálny vzor.
- [ ] Citlivé dôsledky sú vysvetlené pred potvrdením.

### 19.2 Kontrolný zoznam stavov

- [ ] Načítanie má primeraný skeleton alebo lokálny stav.
- [ ] Prázdny stav pomenúva presný zdroj alebo filter.
- [ ] Úspech zodpovedá potvrdenému výsledku.
- [ ] Validačné chyby sú pri poliach a nestrácajú vstup.
- [ ] Sieťová alebo externá chyba obsahuje možnosť nápravy.
- [ ] Konflikt neprepíše novšie údaje potichu.
- [ ] Bez oprávnenia sa zobrazí zrozumiteľný výsledok.
- [ ] Zastarané dáta ukazujú vek a dopad.
- [ ] Čiastočný alebo nejasný výsledok sa netvári ako úplný úspech.

### 19.3 Kontrolný zoznam responzivity

- [ ] 360 px: bez horizontálneho scrollu stránky, všetky akcie dotykovo dostupné.
- [ ] 768 px: hierarchia zostáva jasná a obsah nie je iba zmenšený desktop.
- [ ] 1024 px: panely majú primerané pomery a text sa neláme nečitateľne.
- [ ] 1440 px: obsah využíva priestor bez nadmerne dlhých riadkov.
- [ ] 1920 px pri pracovných plochách: pracovisko nie je stratené v strede.
- [ ] Nízky viewport: modal a pracovná plocha neodrežú spodné akcie.
- [ ] 200 % zoom: obsah sa preleje a zostane ovládateľný.
- [ ] Mobilná klávesnica: aktívne pole a akcie zostávajú dosiahnuteľné.

### 19.4 Kontrolný zoznam prístupnosti

- [ ] Stránka má jeden `h1` a správnu hierarchiu nadpisov.
- [ ] Všetky polia majú labels a chyby sú programovo prepojené.
- [ ] Celý tok sa dá dokončiť klávesnicou.
- [ ] Fokus je vždy viditeľný a po modale/dynamickej zmene sa vracia logicky.
- [ ] Ikonové tlačidlá majú prístupné názvy a tooltipy.
- [ ] Stav nie je vyjadrený iba farbou.
- [ ] Kontrast spĺňa WCAG AA.
- [ ] Live regióny oznamujú dôležité asynchrónne zmeny bez zahltenia.
- [ ] `prefers-reduced-motion` je rešpektované.
- [ ] Dotykové ciele a rozostupy sú primerané.

### 19.5 Kontrolný zoznam obsahu

- [ ] Text je po slovensky, stručný a bez interného žargónu.
- [ ] Tlačidlá pomenúvajú konkrétny výsledok.
- [ ] Pomocný text odpovedá na reálnu otázku.
- [ ] Chyba vysvetľuje problém, dopad a ďalší krok.
- [ ] Dátumy a časy sú jednoznačné.
- [ ] Slovenská diakritika, dlhé mená a dlhšie reálne názvy nerozbijú layout.
- [ ] Terminológia je rovnaká v navigácii, nadpisoch, formulároch aj notifikáciách.

### 19.6 Kontrolný zoznam testovania

- [ ] Prešli formát, lint, TypeScript a produkčný build.
- [ ] Komponentové testy pokrývajú kritické interakcie a stavy.
- [ ] Browser test pokrýva hlavný tok na desktope aj mobile.
- [ ] Kritická operácia má test dvojkliku/idempotencie a zlyhania.
- [ ] Overil sa návrat fokusu, klávesnicová cesta a prístupné názvy.
- [ ] Vizuálne sa skontrolovali reálne renderované obrazovky, nie iba DOM assertions.
- [ ] Overili sa všetky relevantné roly a zakázané akcie.
- [ ] Pri externom náhľade sa porovnala vernosť s reálnym výsledkom.

## 20. Definition of Done pre UI/UX zmenu

UI/UX zmena sa nepovažuje za dokončenú, kým:

1. spĺňa konkrétnu používateľskú úlohu bez zbytočného prepínania,
2. používa správnu informačnú architektúru a spoločné komponenty,
3. má hotové načítanie, prázdny stav, úspech, chybu a oprávnenia,
4. funguje s klávesnicou, fokusom a čítačkou obrazovky v relevantnom rozsahu,
5. je overená na povinných šírkach a pri 200 % zoome,
6. obsahuje zrozumiteľnú slovenskú mikrocopy,
7. neukazuje internú implementáciu ako hlavný obsah,
8. bezpečne spracúva dvojklik, konflikt a externé zlyhanie,
9. má primerané automatizované a vizuálne testy,
10. neporušuje žiadny antipattern z kapitoly 17,
11. zodpovedajúca zmena a jej overenie sú pravdivo zapísané v `STATUS.md`.

Splnenie iba funkčného happy path nie je hotový používateľský výsledok.

## 21. Šablóna pre návrh novej stránky alebo toku

Pri väčšej funkcii sa odporúča vyplniť tento stručný návrhový záznam:

```text
Názov:
Používateľské roly:
Hlavná úloha:
Očakávaný výsledok:
Miesto v navigácii:
Typ stránky:
Hlavná akcia:
Sekundárne akcie:
Potrebné dáta a ich čerstvosť:
Stavy: loading / empty / success / validation / conflict / external error / forbidden
Citlivé dôsledky:
Použité spoločné komponenty:
Desktopové správanie:
Mobilné správanie:
Klávesnicový a fokusový tok:
Automatizované testy:
Manuálne a vizuálne overenie:
Prípadná zdokumentovaná výnimka:
```

## 22. Súčasná terminológia

| Používať                              | Nepoužívať ako hlavný text | Poznámka                                   |
| ------------------------------------- | -------------------------- | ------------------------------------------ |
| Prehľad                               | Dashboard, metrics         | názov hlavnej orientačnej stránky          |
| Redakčný pult                         | Editor draftov             | spoločné pracovisko obsahu                 |
| Najbližšie oznamy / najbližší prehľad | Current draft payload      | podľa konkrétneho kontextu                 |
| Publikovať teraz                      | Trigger publication        | externá citlivá akcia                      |
| Načítať udalosti znova                | Refresh draft              | text musí vysvetliť skutočný výsledok      |
| Kanál                                 | Channel                    | výnimkou je používateľský názov z Discordu |
| Vedúci                                | Owner ID                   | identita sa zobrazuje menom a avatarom     |
| Skupiny s prístupom                   | Permission role IDs        | v zbalenom riadku ukázať počet             |
| Čaká na schválenie                    | pending                    | konzistentný používateľský stav            |
| Nepodarilo sa…                        | Error 500 / exception      | doplniť dopad a nápravu                    |
| Carlo                                 | Domček Bot v2              | používateľský názov produktu               |

Terminologická tabuľka sa priebežne rozširuje, keď pribudne nový opakovateľný pojem. Nový text musí najprv hľadať existujúci termín.

## 23. Správa a dlhodobá konzistentnosť štandardu

Tento dokument sa musí aktualizovať, keď:

- používateľské testovanie odhalí opakovaný problém alebo lepší všeobecný vzor,
- vznikne nový spoločný komponent alebo typ stránky,
- zmení sa vizuálny token, terminológia alebo navigácia,
- zmena WCAG alebo cieľových zariadení ovplyvní požiadavky,
- vedomá výnimka prerastie do opakovateľného pravidla.

Jednorazová vizuálna úprava konkrétnej stránky nemá automaticky meniť štandard. Najprv sa musí určiť, či ide o lokálnu potrebu alebo všeobecný vzor. Ak je vzor všeobecný, upraví sa tento dokument, spoločná implementácia a relevantné testy v jednom koordinovanom kroku.

V každom review UI zmeny sa musí položiť otázka: „Ak by sa tento vzor zopakoval na ďalších piatich stránkach, bola by aplikácia stále jednoduchšia a konzistentnejšia?“ Ak odpoveď nie je jednoznačne áno, riešenie sa má prehodnotiť.

Systematická kontrola existujúcej aplikácie a poradie nápravných etáp sa riadia dokumentom [`PLAN_UI_UX_AUDITU.md`](./PLAN_UI_UX_AUDITU.md). Tento plán neurčuje nižší kvalitatívny štandard; prevádza požiadavky tohto dokumentu na auditné dôkazy, priority, implementačné rezy a kontrolné brány.

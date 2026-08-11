# Plán UI/UX auditu a nápravy aplikácie Carlo

| Vlastnosť             | Hodnota                         |
| --------------------- | ------------------------------- |
| Stav                  | pripravený na realizáciu        |
| Rozsah                | celá webová administrácia Carlo |
| Prvé oblasti          | Reakcie → Roly → Nastavenia     |
| Vstupný index         | `UI_UX_DESTILAT.md`             |
| Normatívny základ     | `UI_UX_STANDARDY.md`            |
| Funkčný základ        | `ZADANIE.md`                    |
| Posledná aktualizácia | 12. august 2026                 |

## 1. Cieľ plánu

Cieľom nie je iba vizuálne „učesať“ existujúce stránky. Cieľom je systematicky nájsť a odstrániť všetky miesta, kde aktuálna aplikácia odporuje UI/UX štandardom, a vytvoriť proces, ktorý zabráni návratu rovnakých problémov.

Výsledkom má byť aplikácia, v ktorej:

- každá stránka zodpovedá jasnej používateľskej úlohe,
- používateľ rozumie aktuálnemu stavu aj dôsledku každej akcie,
- rovnaké prvky vyzerajú a správajú sa rovnako,
- žiadna kritická funkcia nie je navrhnutá iba pre ideálny úspech,
- primárny desktop, podporovaný mobil, klávesnica a rôzne roly dostávajú bezpečnú skúsenosť s vedome určenými prioritami,
- automatizované testy chránia funkčnosť aj dôležité UX pravidlá,
- každé zistenie, rozhodnutie, oprava a overenie zostáva dohľadateľné.

## 2. Základný spôsob práce

Každá oblasť prejde rovnakým uzavretým cyklom:

1. **Povinné načítanie pravidiel** – prečítať celý `UI_UX_DESTILAT.md`, potom celé kapitoly 1, 19, 20, 24 a všetky doménovo relevantné kapitoly `UI_UX_STANDARDY.md`.
2. **Inventarizácia úloh** – čo chce používateľ na stránke skutočne dosiahnuť.
3. **Audit skutočného rozhrania** – primárny desktop, sekundárne viewporty, klávesnica, roly a systémové stavy.
4. **Porovnanie so štandardom** – každé zistenie sa viaže na konkrétnu kapitolu, dostane závažnosť aj nezávislé označenie **[BLOKUJE]** alebo **[BACKLOG]**.
5. **Návrh cieľového toku** – hierarchia, stavy, mikrotexty a responzívne správanie pred úpravou CSS.
6. **Implementácia po ucelených rezoch** – správanie, vzhľad, backend kontrakt a testy sa menia spolu.
7. **Automatická, vizuálna a interakčná kontrola** – použiť zavedený lint/test; chýbajúci mechanizmus nahradiť explicitným manuálnym dôkazom a evidovať jeho implementáciu.
8. **Regresia a kontrolná brána** – uzavrieť všetky body **[BLOKUJE]**; každý odložený **[BACKLOG]** musí mať ID, dopad a etapu.
9. **Aktualizácia dokumentácie** – auditná matica, rozhodnutia a `STATUS.md` sa aktualizujú v tom istom kroku.

Oprava sa nesmie uzavrieť iba preto, že nový layout vyzerá lepšie na jednom screenshote. Musí byť lepší aj pri reálnych dátach, dlhom texte, chybe, pomalej odpovedi, úzkom viewporte a klávesnicovom ovládaní.

## 3. Auditná evidencia

### 3.1 Auditná matica

Na začiatku realizácie vznikne `docs/ui-ux/AUDIT_MATICA.md`. Každé zistenie bude mať jeden riadok s týmito údajmi:

| Pole              | Význam                                            |
| ----------------- | ------------------------------------------------- |
| ID                | stabilný identifikátor, napríklad `UX-REA-001`    |
| Oblasť a úloha    | stránka a používateľský cieľ                      |
| Štandard          | konkrétna kapitola `UI_UX_STANDARDY.md`           |
| Závažnosť         | P0, P1 alebo P2                                   |
| Dopad na dodanie  | **[BLOKUJE]** alebo **[BACKLOG]**                 |
| Stav súladu       | spĺňa / čiastočne spĺňa / nespĺňa / nevzťahuje sa |
| Dôkaz             | screenshot, video, test, DOM alebo zdrojový odkaz |
| Dopad             | čo problém spôsobuje používateľovi                |
| Cieľové správanie | stručný návrh nápravy                             |
| Akceptácia        | merateľná podmienka dokončenia                    |
| Vynútenie         | lint / automatizovaný test / ľudský úsudok        |
| Test              | automatizované a manuálne overenie                |
| Plánovaná etapa   | povinná pri každom **[BACKLOG]**                  |
| Stav opravy       | otvorené / navrhnuté / implementované / overené   |

Matica nesmie byť iba checklist s odškrtnutým „OK“. Každé nesplnené pravidlo potrebuje dôkaz, dopad a akceptačné kritérium.

### 3.2 Závažnosť zistení

#### P0 – kritické

P0 je problém, ktorý môže:

- vykonať inú externú akciu, než používateľ očakáva,
- zobraziť falošný úspech alebo zavádzajúci náhľad,
- spôsobiť stratu práce alebo nebezpečnú zmenu oprávnení,
- znemožniť kritickú úlohu na podporovanom zariadení alebo s klávesnicou,
- sprístupniť citlivú funkciu nesprávnej role,
- nechať používateľa bez bezpečnej cesty na zotavenie.

P0 sa opravuje pred vizuálnym polishom danej oblasti. Závažnosť opisuje silu dopadu; o bráne dodania rozhoduje samostatné označenie podľa kapitoly 1 štandardu. P0 bude spravidla **[BLOKUJE]**, ale obe polia sa vždy vypĺňajú osobitne.

#### P1 – významné

P1 výrazne zvyšuje neistotu, čas alebo chybovosť. Patrí sem nejasná hierarchia, chýbajúci loading/empty/error/dirty stav, nekonzistentný výber, nefunkčný mobilný alebo klávesnicový tok, nevysvetlená deaktivovaná akcia a neprimerane technická komunikácia.

#### P2 – konzistentnosť a polish

P2 zahŕňa spacing, typografické odchýlky, nejednotné ikony, mikrocopy a jemné responzívne alebo pohybové nedostatky, ktoré neblokujú pochopenie úlohy. P2 sa opravuje v tej istej oblasti, ale nesmie odsúvať P0 a P1.

### 3.3 Povinné auditné pohľady

| Rozmer alebo kontext | Povinný dôvod                                         |
| -------------------- | ----------------------------------------------------- |
| 360 px               | úzky mobil, dotykové ciele, reflow                    |
| 768 px               | tablet a prechod medzi mobilným a desktopovým modelom |
| 1024 px              | kompaktný desktop/tablet landscape                    |
| 1440 px              | bežný desktop                                         |
| 1920 px              | využitie veľkého monitora pri pracovných plochách     |
| nízky viewport       | dostupnosť spodných akcií a modalov                   |
| 200 % zoom           | WCAG reflow a čitateľnosť                             |
| reduced motion       | neblokujúce animácie                                  |
| klávesnica bez myši  | poradie, fokus, dialógy, výbery                       |

Podľa oprávnení sa kontroluje Admin, Team Mod, SDB / FMA a používateľ bez prístupu. Stránky určené iba Adminovi potrebujú aj priamy pokus otvoriť route bez oprávnenia.

### 3.4 Povinné dátové stavy

Pre každú relevantnú stránku sa pripravia fixtures pre:

- prvé načítanie a pomalú odpoveď,
- úspešné načítanie a prázdny obsah,
- čiastočné alebo zastarané dáta,
- validačnú chybu,
- API, Google alebo Discord chybu,
- konflikt alebo zmenu dát mimo stránky,
- stratu oprávnenia,
- dlhé slovenské názvy a veľa položiek,
- nedostupný externý objekt,
- neuložené zmeny,
- prvé spustenie bez nastavení, kalendára a histórie,
- stratu siete a vypršanie relácie uprostred vyplneného formulára,
- ochrannú lehotu publikovania a podmienene bezpečné Undo.

## 4. Východiskové zistenia z aktuálneho kódu

Tieto body sú pracovné hypotézy pre prvý vizuálny audit. Nie sú náhradou kontroly reálne vykreslených stránok, ale určujú, čo treba overiť ako prvé.

### 4.1 Reakcie

- Tri pravidlá používajú technickú kombináciu switchu, voľby typu emoji, textového vstupu a natívneho selectu serverových emoji.
- Switch pri jednotlivom pravidle nemá vlastný zrozumiteľný prístupný názov.
- Bežné emoji sa zadáva ako voľný text; serverové emoji sa ukazuje názvom bez kvalitného vizuálneho výberu.
- Testovacie tlačidlá používajú konfiguráciu uloženú na serveri, nie neuložené hodnoty, ktoré používateľ práve vidí. Výsledok testu preto môže byť zavádzajúci.
- Názvy „Test seen“, „Test označenia“ a „Test automatickej“ nie sú prirodzené ani úplné.
- Deaktivované testovacie akcie nevysvetľujú dôvod a testovanie je oddelené od príslušného pravidla.
- Pre uloženie a testovanie Reakcií momentálne chýba plnohodnotný browser E2E scenár.
- Chybové načítanie môže skončiť s chybovou hláškou a súčasne trvalým loading stavom.

### 4.2 Roly

- Vyhľadávanie používa placeholder, ale nemá trvalo viditeľný label ani úplný combobox model ako spoločný výber ľudí.
- Počas nového dopytu môžu do príchodu odpovede zostať viditeľné staré výsledky.
- Úspešná správa nepomenúva človeka, ktorému sa oprávnenie zmenilo.
- Potvrdzovacia akcia používa všeobecné „Potvrdiť zmenu“ namiesto presného výsledku.
- Text o `Manage Roles` a poradí rolí je technickejší, než potrebuje bežný Admin.
- Chyba vyhľadávania sa zobrazuje globálne a nemá vlastný lokálny recovery stav.
- Chýbajú browser scenáre pre Admin rolu, posledného Admina, Discord hierarchiu, chybu, mobil a klávesnicu.
- Chybové načítanie zdieľa riziko nekonečného loading stavu s Reakciami.

### 4.3 Nastavenia

- Stránka správne obsahuje Publikovanie a Kalendáre, ale v publikačných nastaveniach zostala pracovná operácia ručného publikovania. Tá patrí k prehľadu/publikovaniu, nie medzi trvalé nastavenia.
- Formulár nemá explicitný dirty stav, ochranu pred stratou zmien ani porovnanie uložených a rozpracovaných hodnôt.
- „Obnoviť údaje“ môže aktualizovať rodičovské dáta bez spoľahlivého resetu lokálneho draftu.
- Jedno tlačidlo Uložiť je v bočnej karte, hoci mení aj nastavenia vo viacerých kartách ľavého stĺpca.
- Riziková voľba použitia staršej kalendárovej cache potrebuje silnejší kontext a bezpečné potvrdenie.
- Niektoré texty používajú sync, recovery a retry namiesto používateľského dopadu.
- Časové pásmo je voľný text napriek presne definovanému produktovému modelu.
- Pridanie kalendára je trvalo otvorený bočný formulár a úprava sa rozbaľuje v riadku; oba vzory treba preveriť voči pravidlu sústredeného modalu.
- Číselná „priorita“ kalendára odhaľuje implementačný mechanizmus namiesto prirodzeného poradia zdrojov.
- Aktivačný switch kalendára počas operácie nie je zreteľne uzamknutý.
- Pri priamom otvorení route bez schopnosti spravovať nastavenia môže vzniknúť prázdne pracovisko namiesto zamietnutia prístupu.
- Pre ukladanie, kalendáre, dirty stav, konflikty, chyby a mobil chýba samostatné browser E2E pokrytie.

## 5. Poradie realizačných etáp

| Etapa | Oblasť                                              | Dôvod poradia                                            |
| ----- | --------------------------------------------------- | -------------------------------------------------------- |
| UX0   | auditná infraštruktúra a minimálne spoločné základy | porovnateľný audit a menej duplicity                     |
| UX1   | Reakcie                                             | zavádzajúci test neuloženej hodnoty a technický formulár |
| UX2   | Roly                                                | citlivá zmena oprávnení                                  |
| UX3   | Nastavenia                                          | dirty stav, rizikové voľby a kalendárové toky            |
| UX4   | aplikačný rámec a spoločné systémové stavy          | rozšírenie overených vzorov naprieč aplikáciou           |
| UX5   | Prehľad                                             | hlavná orientačná stránka                                |
| UX6   | Redakčný pult a Discord náhľad                      | najdôležitejšie pracovisko produktu                      |
| UX7   | Kanály                                              | štandardizačný a regresný audit po nedávnych revíziách   |
| UX8   | História publikácií a Audit                         | dohľadateľnosť, filtre a mobilné zoznamy                 |
| UX9   | Stav systému a systémové obrazovky                  | recovery, dôvera a zrozumiteľnosť problémov              |
| UX10  | finálna konzistencia a regresia                     | uzavretie matice a celoproduktové overenie               |

## 6. UX0 – auditná infraštruktúra a spoločné základy

UX0 nie je redesign celej aplikácie. Vytvorí iba minimum potrebné na bezpečnú a merateľnú prácu.

### 6.1 Výstupy

- vytvoriť auditnú maticu a adresárovú štruktúru dôkazov,
- spísať route, roly, primárne úlohy a zodpovedajúce fixtures,
- pripraviť konzistentný spôsob screenshotov pre povinné viewporty,
- pridať testovacie helpery pre loading, empty, API error, forbidden a dlhé dáta,
- zaviesť Stylelint zákaz hex farieb mimo tokenov a zdokumentovaného allowlistu,
- zaviesť `eslint-plugin-jsx-a11y` a kontrolu zakázaných viacnásobných selectov,
- zaviesť Playwright + Axe základ pre hlavný tok, návrat fokusu a dvojklik,
- zaviesť kontrolu označení **[BLOKUJE]** / **[BACKLOG]** v kapitolách 19 a 20,
- zmerať hardcoded farby, lokálne tlačidlá a duplicitné stavové vzory,
- určiť spoločný komponent pre page header, lokálny loading/error/empty stav a notice,
- zabezpečiť správnu alert sémantiku chyby a status sémantiku úspechu,
- definovať spoločný mechanizmus dirty stavu a ochrany rozpracovaného formulára,
- nemeniť naraz vizuál nesúvisiacich stránok.

### 6.2 Kontrolná brána UX0

- Každá etapa má pripravenú auditnú sekciu a dôkazové scenáre.
- Browser testy vedia spustiť desktopový aj mobilný projekt s požadovanými stavmi.
- Lint, Axe, dvojklik a návrat fokusu majú spustiteľný mechanizmus alebo otvorený blokujúci záznam; samotné tvrdenie o manuálnej kontrole nestačí.
- Spoločné stavové komponenty majú izolovaný test alebo pilotné použitie.
- Existujúci test suite zostáva zelený.

## 7. UX1 – Reakcie

### 7.1 Cieľ používateľského modelu

Používateľ nemá nastavovať technický „typ emoji“. Spravuje tri zrozumiteľné pravidlá:

1. reakciu pod zverejneným prehľadom,
2. reakciu, keď niekto označí Carla,
3. reakciu na nové správy vo vybraných kanáloch.

Každé pravidlo na jednom mieste odpovedá, či je zapnuté, aké emoji používa, kde alebo kedy sa použije, či má neuložené zmeny a ako ho bezpečne vyskúšať.

### 7.2 Návrhové a implementačné úlohy

- Prepracovať technické karty na konzistentné pravidlá s názvom, ukážkou emoji, stavom a krátkym dopadom.
- Nahradiť voľný Unicode text a serverový select jedným kvalitným emoji pickerom pre bežné aj serverové emoji.
- Vizuálne označiť nedostupné serverové emoji a ponúknuť recovery.
- Dať každému switchu viditeľný aj programový label.
- Vypnuté pravidlo stíšiť bez straty čitateľnosti.
- Pre automatické kanály použiť spoločný `ChannelMultiPicker`, počet výberov a návrat na nulu.
- Presunúť test k pravidlu alebo vytvoriť jednoznačný tok, v ktorom je jasné, čo sa testuje.
- Zabezpečiť, aby test používal hodnotu, ktorú používateľ práve vidí. Preferované je poslať explicitne validované draft emoji do testovacieho endpointu; alternatíva musí pred testom vyžiadať uloženie a jasne to komunikovať.
- Pred externým testom ukázať kanál a skutočnosť, že Carlo odošle testovaciu správu.
- Zobraziť busy stav konkrétneho pravidla, zabrániť dvojkliku a vysvetliť deaktivovanú akciu.
- Zaviesť dirty stav, presné uloženie, úspech, chybu a ochranu pred odchodom.
- Opraviť loading/error vetvu tak, aby chyba nikdy nevyzerala ako nekonečné načítanie.

### 7.3 Povinné testy

- Admin vidí tri pravidlá s uloženým stavom.
- Zmení každé emoji cez picker, uloží a po reloade vidí rovnakú hodnotu.
- Test pred uložením použije práve viditeľnú hodnotu alebo explicitne vyžaduje uloženie.
- Test ukáže cieľový kanál, pošle jednu správu a pri dvojkliku nevytvorí duplicitu.
- Nedostupné serverové emoji má jasný recovery tok.
- Kanály sa dajú filtrovať, vybrať, odstrániť aj vyčistiť na nulu.
- Loading, API chyba, Discord chyba a forbidden majú vlastný výsledok.
- Tok funguje klávesnicou a live región oznámi zmenu.
- Desktop, mobil, nízky viewport a 200 % zoom nemajú odrezané akcie.

### 7.4 Kontrolná brána UX1

- Testované emoji nemôže byť iné než hodnota, ktorú používateľ považuje za testovanú.
- Všetky tri pravidlá používajú jeden vizuálny a interakčný model.
- Reakcie majú desktopový aj mobilný browser E2E scenár.
- Všetky zistenia **[BLOKUJE]** sú overené ako opravené a každý **[BACKLOG]** je evidovaný.

## 8. UX2 – Roly

### 8.1 Cieľ používateľského modelu

Admin vyhľadá konkrétneho človeka, pochopí jeho aktuálne oprávnenia a vedome mu udelí alebo odoberie Team Mod či Admin bez potreby poznať Discord hierarchiu.

### 8.2 Návrhové a implementačné úlohy

- Použiť spoločný model vyhľadávania ľudí s viditeľným labelom, combobox sémantikou, avatarmi a Discord menom.
- Pri zmene dopytu odstrániť alebo označiť zastarané výsledky.
- Rozlíšiť „začnite písať“, „vyhľadávam“, „bez výsledku“ a „vyhľadávanie zlyhalo“ priamo vo výsledkoch.
- Zabezpečiť čitateľnú identitu a oprávnenia na desktop aj mobile.
- Nahradiť všeobecné potvrdenie presným názvom „Udeliť Team Mod“, „Odobrať Admin“ a podobne.
- V potvrdení pomenovať človeka, rolu a dôsledok; odobratie Admina je deštruktívne.
- Zachovať busy stav na konkrétnom človeku a role a zabrániť paralelnému dvojkliku.
- V úspechu aj chybe pomenovať človeka a rolu.
- Preložiť `Manage Roles` a hierarchiu na používateľský význam.
- Posledného Admina a rolu nad Carlom vysvetliť konkrétnym recovery krokom.
- Overiť stratu Admin oprávnenia medzi otvorením a potvrdením.
- Opraviť loading/error vetvu a priamy forbidden vstup.

### 8.3 Povinné testy

- Živé vyhľadávanie, zrušenie starého requestu a správny fokus.
- Viac ľudí s podobným menom a dlhými slovenskými menami.
- Udelenie a odobratie Team Mod aj Admin.
- Zákaz odobratia posledného Admina s návodom na nápravu.
- Discord hierarchy/permission chyba bez falošného úspechu.
- Čerstvé overenie role používateľa pri potvrdení.
- Dvojklik nevytvorí dve operácie.
- Klávesnicový tok cez vyhľadávanie a dialóg s návratom fokusu.
- Mobil zachová identitu aj obe roly bez horizontálneho scrollu.

### 8.4 Kontrolná brána UX2

- Citlivá zmena je vždy viazaná na osobu, rolu a dôsledok.
- Posledný Admin a Discord hierarchia majú použiteľný recovery tok.
- Neexistuje placeholder-only pole ani neoznačený switch.
- Roly majú desktopový a mobilný browser E2E vrátane chyby.

## 9. UX3 – Nastavenia

### 9.1 Cieľ informačnej architektúry

Nastavenia obsahujú iba trvalé pravidlá Publikovania a Kalendáre. Ručné publikovanie sa odstráni z Nastavení. Jeho primárnym webovým miestom zostane Prehľad alebo iné jasné publikačné pracovisko s najbližším balíkom a dôsledkom preskočenia termínu.

### 9.2 Publikačné nastavenia

- Zoskupiť deň, čas a časové pásmo s náhľadom najbližšieho termínu.
- Časové pásmo zmeniť na bezpečne pevné alebo riadený výber podporovaných hodnôt.
- Oddeliť obsahové pravidlá, Discord miesta, pravidlá umiestnenia a upozornenia jasnou hierarchiou.
- Zjednotiť channel/category výbery so spoločnými Discord pickermi, kde natívny select nestačí.
- Prepísať sync/recovery/retry texty na dopad a odporúčanú činnosť.
- Núdzovú cache výnimku označiť ako rizikovú, vysvetliť čerstvosť a pri zapnutí potvrdiť.
- Zachovať `@everyone` ako povinnú informatívnu vlastnosť, nie switch.
- Pridať ochrannú lehotu 0–300 sekúnd s predvolenými 30 sekundami a výber ďalších príjemcov dočasnej DM popri aktuálnych Adminoch.
- Vysvetliť, že zlyhanie DM publikovanie nezastaví, ale vytvorí moderátorské upozornenie.
- Zaviesť dirty indikátor, jasný rozsah uloženia a ochranu pred stratou práce.
- Pri „Obnoviť údaje“ rozlíšiť tiché načítanie, zahodenie zmien a konflikt.
- Na mobile ponechať akcie dostupné v kontexte príslušných sekcií.

### 9.3 Kalendáre

- Pri každom zdroji ukázať názov, aktívny stav, čerstvosť úspechu a konkrétny problém.
- Celkové zdravie nesmie byť pozitívne, ak aktívny kalendár nikdy neuspel alebo je zastaraný.
- Pridanie aj úpravu presunúť do konzistentného centrovaného modalu.
- Google Calendar ID doplniť príkladom, návodom a validačnou chybou pri poli.
- Nahradiť surové číslo priority prirodzeným poradím zdrojov s klávesnicovou alternatívou.
- Aktivačný switch počas operácie uzamknúť a pri chybe vrátiť do potvrdeného stavu.
- Synchronizáciu navrhnúť ako lokálnu akciu s presným výsledkom.
- Zobraziť never synced, syncing, success, stale a failed stav.
- Ošetriť odstránený alebo neprístupný kalendár bez straty diagnostického kontextu.

### 9.4 Oprávnenia a testy

- Admin vidí obe oblasti a môže ich meniť.
- Používateľ bez `manage_settings` nemá navigáciu a pri priamej route dostane zrozumiteľný forbidden stav.
- Testovať uloženie každej skupiny, reload, dirty odchod, konflikt, núdzovú cache výnimku, ochrannú lehotu a príjemcov DM, pridanie/úpravu/aktiváciu/sync/radenie kalendára, stale/failure, mobil, nízky viewport a 200 % zoom.

### 9.5 Kontrolná brána UX3

- Nastavenia obsahujú iba trvalé pravidlá.
- Používateľ vždy vie, či má neuložené zmeny a čo uloží.
- Obnovenie nemôže ponechať starý draft ani potichu zahodiť prácu.
- Kalendárový stav je pravdivý pre každý aktívny zdroj.
- Publikovanie aj Kalendáre majú desktop/mobile/error browser scenáre.

## 10. UX4 – aplikačný rámec a spoločné systémové stavy

Po prvých troch etapách sa osvedčené vzory zjednotia naprieč aplikáciou:

- page header, názov, popis a obnovovacia akcia,
- loading skeleton a lokálne loading indikátory,
- empty, error, forbidden, stale a partial stav,
- success status a error alert s focusom,
- dirty guard a formulárová päta,
- Discord pickery a emoji picker,
- modaly a potvrdzovacie dialógy,
- route-level oprávnenie,
- hardcoded farby, spacingy a duplicitné tlačidlá,
- topbar, sidebar, mobilná navigácia, skip link a route loader,
- prvé spustenie v poradí Discord miesta → voliteľný kalendár → harmonogram → preview,
- zachovanie formulára pri strate siete a relácie bez automatického opätovného odoslania.

Táto etapa nesmie svojvoľne prefarbiť dokončené stránky. Spoločný komponent sa prevezme iba po overení akceptovaného správania.

## 11. UX5 – Prehľad

Audit preverí:

- odpovede „čo sa zverejní“, „kedy“ a „je všetko v poriadku“,
- pravdivý celkový počet a rozlíšenie zdrojov,
- čerstvosť kalendárov a poslednú publikáciu,
- prioritizáciu problémov a čakajúcich archivácií,
- jednoznačný vstup do Redakčného pultu,
- správne umiestnené ručné publikovanie s náhľadom,
- ochrannú lehotu: odpočet, „Zastaviť“, „Zverejniť teraz“, žiadny verejný účinok pred koncom a pravdivý výsledok neskorého zastavenia,
- odstránenie metrík bez rozhodovacej hodnoty,
- prvé spustenie bez histórie, kalendára a uložených nastavení,
- mobile/zoom a roly SDB / FMA vs. Admin.

## 12. UX6 – Redakčný pult a Discord náhľad

Audit preverí:

- spoločný chronologický obsah všetkých zdrojov,
- filtre a počty bez zavádzajúcich núl,
- klikateľné a klávesnicové riadky,
- inkluzívne viacdenné udalosti,
- vylúčené položky s recovery tokom,
- centrované editory kalendárových, manuálnych a INFO položiek,
- upload obrázka vrátane chyby a náhrady,
- konflikt zmien a rozsah recurring úpravy,
- využitie 1440/1920 px bez strateného či privysokého pracoviska,
- vnútorné rolovanie bez scroll pasce,
- kanonický Discord náhľad bez vymysleného obsahu,
- palety INFO/udalosti, limity, delenie správ a seen reakciu,
- veľký balík, mobil a nízky viewport.

Ako konkrétne regresné hypotézy sa overí, či sa nevrátil trvalý bočný formulár, pracovisko stratené na širokom monitore alebo vyššie než viewport, tri oddelené administrácie obsahu, záložky oddeľujúce obsah od Discord náhľadu, nulová čiastková metrika vydávaná za celok a odlišný kartový layout INFO bez doménového dôvodu.

## 13. UX7 – Kanály

Kanály už prešli používateľskými revíziami, preto sa najprv vykoná regresný audit. Kontroluje sa:

- jasnosť tvorby a archivácie,
- rovnaký disclosure model umiestnenia a skupín,
- normalizácia názvu s diakritikou a composition inputom,
- dynamické štyri emoji a úplný katalóg,
- focus po výbere/odstránení ľudí,
- vyčistenie dopytu a výsledkov po výbere človeka a primeranú veľkosť čipu voči avataru,
- návrat rolí a skupín na nulu,
- zákaz archívu a voice/stage kategórií,
- podmienené abecedné radenie,
- modal, mobilná klávesnica, sticky akcie a návrat fokusu,
- čakajúca archivácia a Admin rozhodnutie,
- double-click, nejasný externý výsledok a recovery.

Regresné hypotézy zahŕňajú disclosure bez šípky alebo súhrnu, rozdielne disclosure riadky v jednom formulári, textové pole „použiť iný symbol“, obmedzený emoji katalóg, blokovanie medzier či diakritiky namiesto živej normalizácie a preskočovací odkaz uviaznutý po zatvorení modalu.

Undo sa overí osobitne: rola iba pri nezmenenom stave a čerstvom oprávnení, archivácia iba s platným snapshotom a vytvorený kanál presným odstránením len keď zostal prázdny a nezmenený; inak sa ponúkne archivácia. Návrat nemá časový limit, ale nikdy nesmie obísť aktuálne predpoklady.

Ak stránka pravidlo spĺňa, nemení sa iba kvôli vizuálnej uniformite.

## 14. UX8 – História publikácií a Audit

Audit preverí ľudské názvy a stavy, filtre a ich zrušenie, automatický vs. ručný beh, detail snapshotu, odkazy na Discord, partial/uncertain/retry/recovery dopad, ochranu opakovania správy, sekundárne technické detaily, mobilnú transformáciu a stránkovanie so zachovaním filtrov.

## 15. UX9 – Stav systému a systémové obrazovky

Audit preverí používateľský dopad namiesto technických heartbeatov, zdravie každého zdroja, čerstvosť a recovery, degradáciu a stale dáta, prihlásenie a zamietnutie bez JSON, expirovanú reláciu, Error Boundary, 404, korelačné ID iba v detaile, klávesnicu a mobil.

## 16. UX10 – finálna konzistencia a uzavretie

### 16.1 Celoproduktové kontroly

- prejsť celý `UI_UX_STANDARDY.md` a uzavrieť auditnú maticu,
- porovnať rovnaké komponenty medzi stránkami,
- zjednotiť terminológiu a odstrániť neúmyselný žargón,
- overiť všetky route v relevantných rolách,
- spustiť screenshot comparison na povinných viewportoch,
- vykonať klávesnicovú cestu cez každú hlavnú úlohu,
- vykonať automatický accessibility scan a manuálnu kontrolu,
- overiť kontrast, reduced motion, 200 % zoom a dlhé dáta,
- skontrolovať horizontálny scroll,
- uzavrieť všetky zistenia **[BLOKUJE]** s dôkazom,
- každému otvorenému **[BACKLOG]** priradiť ID, dopad a plánovanú etapu,
- pred väčším UI vydaním vykonať a zdokumentovať 20–30-minútový vlastný pozorovací scenár.

### 16.2 Finálna kontrolná brána

Audit je uzavretý iba vtedy, keď:

1. všetky zistenia **[BLOKUJE]** sú implementované a overené,
2. každý otvorený **[BACKLOG]** má ID, dopad, dôkaz a plánovanú etapu,
3. žiadna hlavná úloha nemá iba happy-path test,
4. každá route má relevantné loading, empty/error a forbidden správanie,
5. browser test primárneho desktopu je zelený a sekundárne profily majú evidovaný výsledok,
6. vlastný pozorovací scenár potvrdí prvé tri oblasti aj kľúčové pracoviská,
7. štandard, auditná matica, evidencia a `STATUS.md` zodpovedajú realite,
8. celý repository CI je zelený,
9. režim `live` nebol kvôli UI práci svojvoľne zapnutý.

## 17. Definition of Done každej etapy

Etapa sa nepovažuje za dokončenú, kým:

- má uzavretú auditnú maticu pre svoj rozsah,
- cieľový tok bol navrhnutý pred detailným polishom,
- všetky body **[BLOKUJE]** sú opravené a každý **[BACKLOG]** má plánovanú etapu,
- relevantné systémové stavy sú implementované,
- zmena funguje pre všetky oprávnené roly,
- citlivé akcie overujú oprávnenie a zabraňujú dvojkliku,
- primárny desktop je blokujúco overený; mobil, nízky viewport, 200 % zoom a reduced motion majú výsledok a prípadný backlog,
- tok sa dá dokončiť klávesnicou a fokus je predvídateľný,
- browser E2E obsahuje úspech aj významnú chybu,
- vizuálna kontrola používa reálny render a realistické dáta,
- frontendové a relevantné backendové kontroly sú zelené,
- `STATUS.md` obsahuje zmenu, testy a otvorené body,
- commit je dohľadateľný a vzdialený CI je zelený.

## 18. Pravidlá rozsahu a rozhodovania

- Funkcia sa nemení iba kvôli estetike. Ak backend bráni pravdivému UX, upraví sa s frontendovým tokom a testami.
- Nevykoná sa veľký redesign viacerých oblastí naraz. Každá etapa zostane samostatne overiteľná.
- Spoločný komponent nevzniká abstraktne „pre budúcnosť“, ale po identifikovaní opakovanej potreby alebo ako nutná prístupnostná infraštruktúra.
- Už používateľsky prijaté riešenie sa nemení bez konkrétneho zistenia voči štandardu.
- Kritické produktové rozhodnutie, ktoré nemožno bezpečne odvodiť, sa predloží používateľovi s odporúčaním a dopadmi.
- Bežné rozhodnutia v medziach štandardu neblokujú pokračovanie medzi etapami.
- `STATUS.md` sa aktualizuje priebežne; auditná matica ho nenahrádza.

## 19. Najbližší konkrétny postup

Po schválení plánu sa začne UX0 v minimálnom rozsahu a bezprostredne UX1 – Reakcie:

1. vytvoriť auditnú maticu a fixtures pre Reakcie,
2. zachytiť desktop/mobile/keyboard baseline,
3. potvrdiť P0 problém testovania uloženej namiesto viditeľnej hodnoty,
4. navrhnúť model troch pravidiel a jednotného emoji pickera,
5. upraviť API kontrakt, frontend a testy v jednom reze,
6. uzavrieť vizuálnu a funkčnú bránu UX1,
7. pokračovať na UX2 – Roly a UX3 – Nastavenia.

Prvý implementačný krok nesmie začať plošným prepisovaním CSS. Začne dôkazom problému, cieľovým tokom a akceptačnými kritériami.

## 20. Autonómny priechod UX0–UX10

### 20.1 Prevádzkový režim

Etapy UX0 až UX10 sa vykonajú bez priebežného vyžadovania používateľských rozhodnutí. Agent používa v tomto poradí:

1. explicitné produktové rozhodnutia v `ZADANIE.md`,
2. celý `UI_UX_DESTILAT.md` a príslušné celé kapitoly `UI_UX_STANDARDY.md`,
3. existujúce prijaté správanie a spoločné komponenty,
4. najbezpečnejší vratný predpoklad s najmenším rozsahom.

Neistota, ktorá nebráni bezpečnej implementácii, sa zapíše do `docs/ui-ux/ODLOZENE_ROZHODNUTIA.md` s odporúčaním a pokračuje sa ďalej. Otázky sa zoskupia až do záverečného odovzdania. Neprítomnosť používateľa nie je dôvodom zastaviť inú nezávislú etapu.

### 20.2 Jediná výnimka pre okamžitú otázku

Otázka sa položí okamžite iba vtedy, ak súčasne platí, že:

- odpoveď nemožno odvodiť z autoritatívnych dokumentov ani existujúceho prijatého správania,
- bezpečný vratný variant neexistuje,
- odklad by zablokoval všetku ďalšiu zmysluplnú prácu,
- nesprávny predpoklad by mohol spôsobiť stratu dát, nezvratný externý účinok, porušenie oprávnení alebo zásadnú zmenu produktového významu.

Ak je blokovaná iba jedna vetva, označí sa a pokračuje sa ostatnými etapami. Produkčný režim `live`, reálne publikovanie, mazanie existujúcich dát, cutover ani zmena externých oprávnení nie sú týmto autonómnym režimom autorizované.

### 20.3 Uzavretý cyklus každej etapy

Každá etapa vykoná bez preskakovania:

1. načítanie povinných pravidiel a inventarizáciu route, úloh, rolí a stavov,
2. baseline skutočného renderu a existujúcich automatických testov,
3. zápis nálezov s ID, dôkazom, P0/P1/P2, **[BLOKUJE]** alebo **[BACKLOG]** a mechanizmom vynútenia,
4. návrh najmenšieho uceleného cieľového toku,
5. implementáciu vrátane potrebného backend kontraktu a systémových stavov,
6. cielené testy, celý relevantný frontend/backend suite a renderovanú kontrolu,
7. aktualizáciu auditnej matice, odložených rozhodnutí a `STATUS.md`,
8. samostatný commit, push na `origin/main` a overenie vzdialeného CI pred prechodom na ďalšiu etapu.

Neúspešná kontrola sa opravuje v tej istej etape. Existujúci **[BACKLOG]** sa smie preniesť iba s konkrétnou cieľovou etapou; nový alebo zhoršený bod **[BLOKUJE]** sa neprenáša.

### 20.4 Nočná kontinuita a záverečné odovzdanie

Autoritatívny priebežný stav je vždy v `STATUS.md` a `docs/ui-ux/AUDIT_MATICA.md`. Po kompaktovaní kontextu sa najprv načítajú tieto dva súbory, destilát a aktuálna etapa tohto plánu. Záver obsahuje:

- výsledok každej etapy UX0–UX10 a odkazy na dôkazy,
- zoznam commitov a CI behov,
- všetky zostávajúce **[BACKLOG]** body,
- jediný zoskupený zoznam odložených otázok,
- jasné oddelenie automaticky overeného výsledku od ľudského pozorovania alebo produkčného kroku, ktorý agent nemôže pravdivo predstierať.

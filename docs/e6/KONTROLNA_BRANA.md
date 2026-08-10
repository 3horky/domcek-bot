# Kontrolná brána E6

## Kritériá

- [x] Informačná architektúra a route mapa zodpovedajú capability matici.
- [x] Discord login, session bootstrap, odhlásenie a 401 návrat fungujú.
- [x] Dashboard prioritne zobrazuje najbližší termín a stav draftu.
- [x] Editor používa kanonický draft a má verný viac-správový Discord preview.
- [x] Instance a series edit majú zrozumiteľný version-conflict tok.
- [x] Manuálne udalosti a INFO oznamy majú funkčný CRUD vrátane deaktivácie.
- [x] INFO obrázky sa priamo uploadujú, serverovo validujú/spracujú a zobrazujú ako uložený náhľad.
- [x] Všetky obsahové editory používajú centrovaný responzívny Base UI modal namiesto bočného panelu.
- [x] Kalendárové, manuálne a INFO položky sa spravujú v jednom Redakčnom pulte so spoločným zoznamom, filtrami a trvalo dostupným Discord náhľadom.
- [x] Viacdenné celodenné manuálne udalosti sa zobrazujú ako celý inkluzívny rozsah.
- [x] Redakčný pult využíva veľký monitor samostatným responzívnym limitom a výškou viewportu bez zúženia na dashboardový kontajner.
- [x] Spodok širokého Redakčného pultu zostáva vo viewporte; zoznam a náhľad majú vlastný vnútorný scroll.
- [x] Editor záznamu možno otvoriť veľkým klikateľným riadkom aj explicitným tlačidlom a veľký cieľ je ovládateľný klávesnicou.
- [x] Discord náhľad nepridáva vymyslený popis kanála a používa kanonickú pôvodnú mesačnú dvojpaletu INFO/udalostí.
- [x] Audit rešpektuje serverový rolový podvýber.
- [x] Desktop a mobil majú implementované loading, empty, error a retry stavy bez povinnej mobilnej tabuľky.
- [x] Kritické ovládacie prvky majú klávesnicový prístup, viditeľný focus,
  sémantické názvy a kontrast; detailné ladenie zostáva súčasťou priebežnej QA.
- [x] Prettier, ESLint, TypeScript, testy, produkčný build a runtime prejdú.
- [x] `STATUS.md` zodpovedá skutočnému výsledku.

## Aktuálny výsledok

**Brána E6: SPLNENÁ.**

Funkčný E6 rozsah je implementovaný a lokálne overený. Automatizované kontroly
zahŕňajú 119 backendových testov, 10 frontendových testov, statické kontroly,
produkčný build a locked Compose runtime. Používateľ 9. augusta 2026 prijal
aktuálny stav slovami „nateraz to je fajn“ a rozhodol, že ďalšie vizuálne a
accessibility dolaďovanie bude pokračovať neskôr bez blokovania E7. Po
používateľskej spätnej väzbe bol pôvodný vlastný
vzhľad nahradený shadcn/UI s Base UI, editorové drawery centrovanými modalmi a
INFO URL pole priamym bezpečne spracovaným uploadom; bez UAT/accessibility
kontroly sa brána neoznačí ako splnená.

Druhá používateľská kontrola odhalila nejasnú informačnú hierarchiu dashboardu,
zbytočné záložky medzi obsahom a Discord preview a nestabilnú dátumovú sekciu
celodennej manuálnej udalosti. Dashboard teraz odpovedá iba na „kedy, čo a či
treba zasiahnuť“, obsah s preview sú zobrazené spolu a dátumové polia majú
samostatnú jednotnú sekciu. Automatizované kontroly po korekcii zostávajú
zelené; používateľská a accessibility akceptácia zostáva otvorená.

Tretia používateľská kontrola odkryla zásadný problém roztrieštenia jedného
obsahového balíka medzi kalendárovú, manuálnu a INFO administráciu. Tie sú teraz
zjednotené v desktope podobnom Redakčnom pulte: zdroje a filtre sú vľavo,
spoločný zoznam uprostred a náhľad reálneho Discord kanála vpravo. Pôvodné
samostatné adresy presmerujú na pult, tvorba a úprava oboch vlastných typov
obsahu ostáva dostupná priamo z neho. Terminológia bola spresnená a nejasné
„Obnoviť draft“ nahradilo „Načítať aktuálne údaje“. Bot aj web nesú meno Carlo.

Štvrtá kontrola odstránila posledný výrazný problém širokého desktopu: Redakčný
pult sa už nestráca v úzkom centrovanom kontajneri, ale využíva pracovnú šírku
a výšku monitora. Discord hlavička neobsahuje vymyslený popis kanála a farby
embedov sú súčasťou composer modelu `e4-v2`; INFO používa jemný a udalosti sýty
odtieň pôvodnej mesačnej palety. Nastavenia sa nepridávajú ako nefunkčný
placeholder a zostávajú potvrdeným rozsahom E7–E9.

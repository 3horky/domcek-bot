# UI/UX destilát aplikácie Carlo

Toto je povinný vstupný index pre návrh, implementáciu aj audit. **Najprv prečítaj celý tento destilát.** Potom vždy otvor celé kapitoly 1, 19, 20 a 24 v [`UI_UX_STANDARDY.md`](./UI_UX_STANDARDY.md) a celé kapitoly relevantné pre menený tok. Destilát nenahrádza normatívny štandard a náhodný výsek zo štandardu nestačí.

## Dve nezávislé osi

- **MUSÍ / NESMIE**, **MÁ / NEMÁ**, **MÔŽE** určujú silu pravidla.
- **[BLOKUJE]** určuje, že nález bráni dokončeniu; **[BACKLOG]** dovoľuje odklad iba s ID, dopadom a etapou nápravy.
- Blokuje všetko, čo môže klamať, stratiť prácu, vykonať nesprávny externý zásah, obísť oprávnenie či idempotenciu alebo zneprístupniť hlavný tok klávesnicou. Kvalitatívne zhoršenie bez klamstva či škody patrí do backlogu. Kontext môže backlogový typ nálezu povýšiť na blokujúci.

Presné pravidlo: [kapitola 1](./UI_UX_STANDARDY.md#1-účel-a-záväznosť-dokumentu). Kontrolné označenia: [kapitola 19](./UI_UX_STANDARDY.md#19-povinná-kontrola-kvality). Brána hotového výsledku: [kapitola 20](./UI_UX_STANDARDY.md#20-definition-of-done-pre-uiux-zmenu).

## Desať pravidiel, ktoré chránia dôveru

1. Stav, počet, náhľad aj úspech musia hovoriť pravdu o skutočnom rozsahu a externom výsledku. ([3.5](./UI_UX_STANDARDY.md#35-viditeľný-kontext-a-pravdivý-stav), [11](./UI_UX_STANDARDY.md#11-systém-stavov-a-spätnej-väzby))
2. Citlivá akcia ukáže cieľ a dôsledok, čerstvo overí oprávnenie a pri dvojkliku vytvorí najviac jeden účinok. ([3.6](./UI_UX_STANDARDY.md#36-bezpečie-bez-zbytočného-brzdenia), [4](./UI_UX_STANDARDY.md#4-používatelia-roly-a-oprávnenia))
3. Preview používa rovnaký kanonický výsledok ako publikovanie; nič si nevymýšľa ani nezjednodušuje. ([13.2](./UI_UX_STANDARDY.md#132-discord-náhľad))
4. Konflikt, neistý výsledok, strata siete ani relácie nesmú potichu prepísať, odoslať alebo zahodiť prácu. ([11.4](./UI_UX_STANDARDY.md#114-chyba-a-zotavenie), [11.7](./UI_UX_STANDARDY.md#117-strata-spojenia-a-vypršanie-relácie-počas-formulára), [15](./UI_UX_STANDARDY.md#15-dôvera-bezpečnosť-a-ochrana-údajov-v-ux))
5. Hlavný tok musí fungovať klávesnicou s viditeľným a logickým fokusom. ([12.2](./UI_UX_STANDARDY.md#122-fokus), [14](./UI_UX_STANDARDY.md#14-prístupnosť))
6. Undo sa ponúkne iba pri presnom, idempotentnom a stavovo bezpečnom návrate; inak sa použije potvrdenie alebo bezpečná alternatíva. ([10.10](./UI_UX_STANDARDY.md#1010-potvrdzovacie-dialógy))
7. Ochranná lehota publikovania nevytvorí verejnú správu pred koncom, je atómová a bezpečná po reštarte. ([13.7](./UI_UX_STANDARDY.md#137-ochranná-lehota-publikovania-a-vratné-serverové-operácie))
8. Funkcie sa organizujú podľa úloh používateľa; jedna výsledná vec má jedno prirodzené pracovisko. ([3.1–3.3](./UI_UX_STANDARDY.md#31-úloha-pred-dátovým-modelom), [5](./UI_UX_STANDARDY.md#5-informačná-architektúra))
9. Text je prirodzená slovenčina; technický model, ID, enum a JSON nie sú hlavné rozhranie. ([3.4](./UI_UX_STANDARDY.md#34-bežný-jazyk-pred-technickým-jazykom), [9](./UI_UX_STANDARDY.md#9-obsahový-dizajn-a-jazyk), [22](./UI_UX_STANDARDY.md#22-súčasná-terminológia))
10. `STATUS.md` musí v tom istom kroku pravdivo zachytiť zmenu, dôkaz aj zostávajúcu medzeru. ([18.2](./UI_UX_STANDARDY.md#182-počas-implementácie), [20](./UI_UX_STANDARDY.md#20-definition-of-done-pre-uiux-zmenu))

## Produktový a layoutový model

- Carlo je pokojné pracovné prostredie, nie technická konzola. Každá stránka vysvetlí miesto, možnosti, dáta, dôsledok, výsledok a nápravu. ([2](./UI_UX_STANDARDY.md#2-produktová-skúsenosť-ktorú-carlo-vytvára))
- Prehľad pomáha rozhodnúť sa; pracovná plocha využíva priestor; správa objektov má čistý zoznam a konzistentný editor; Nastavenia obsahujú trvalé pravidlá. ([6](./UI_UX_STANDARDY.md#6-typy-stránok))
- Prvé spustenie vedie cez Discord miesta, voliteľný kalendár, harmonogram a preview. Carlo funguje aj bez kalendára. ([6.7](./UI_UX_STANDARDY.md#67-prvé-spustenie))
- Primárny profil je zatiaľ desktop/notebook, referencia 1440 px; 1024 a 1920 px sa tiež overujú. Mobil je podporovaný sekundárny profil. ([7](./UI_UX_STANDARDY.md#7-globálne-rozloženie-a-responzivita))
- Vizuál používa spoločné tokeny, typografiu, farby s významom, pokojné rozostupy a minimum súťažiacich povrchov. ([8](./UI_UX_STANDARDY.md#8-vizuálny-jazyk))

## Komponenty a domény

- Použi existujúci spoločný komponent. Tlačidlo pomenúva výsledok, klikateľný riadok má jasný hover/focus, formulár zachová vstup a výber sa dá vyčistiť na nulu. ([10.1–10.7](./UI_UX_STANDARDY.md#101-znovupoužitie-komponentov))
- Modal zachytí a vráti fokus, bezpečne roluje a nestratí pätu; tooltip nie je jediná cesta k funkcii. ([10.9](./UI_UX_STANDARDY.md#109-modaly), [10.11](./UI_UX_STANDARDY.md#1011-popovery-tooltipy-a-výber-emoji))
- Upload, filtre, tabuľky a zoznamy musia mať úplné stavy a nesmú stratiť kontext. ([10.14–10.16](./UI_UX_STANDARDY.md#1014-nahrávanie-obrázkov))
- Redakčný pult, Discord náhľad, Kanály, Roly, Reakcie a Nastavenia majú vlastné doménové pravidlá. Pred zásahom prečítaj celú [kapitolu 13](./UI_UX_STANDARDY.md#13-doménové-štandardy-jednotlivých-oblastí).
- Zakázané sú nadčasové vzory z [kapitoly 17](./UI_UX_STANDARDY.md#17-zakázané-antipatterny); konkrétne dnešné nálezy patria do [`PLAN_UI_UX_AUDITU.md`](./PLAN_UI_UX_AUDITU.md).

## Ako sa pravidlá overujú

- Cieľový lint: Stylelint na hex farby mimo tokenov, `eslint-plugin-jsx-a11y`, kontroly zakázaných prvkov a označení checklistov.
- Cieľové testy: Playwright + Axe, klávesnica a návrat fokusu, dvojklik/idempotencia, konflikty a relácia, vernosť preview, ochranná lehota a stavovo bezpečné Undo.
- Človek posudzuje hierarchiu, jazyk, rovnováhu, objaviteľnosť a kvalitatívnu vernosť na renderovanej obrazovke. Pred väčším UI vydaním vlastník absolvuje pevný 20–30-minútový scenár a nálezy zaeviduje. ([18.4](./UI_UX_STANDARDY.md#184-spätná-väzba-v-jednočlennom-projekte))

**Tieto mechanizmy zatiaľ nie sú systematicky implementované.** Presný cieľ a prechodné pravidlo sú v [kapitole 24](./UI_UX_STANDARDY.md#24-vynucovanie-štandardu); implementácia patrí do [`PLAN_IMPLEMENTACIE.md`](./PLAN_IMPLEMENTACIE.md). Kým brány nevzniknú, audit musí každý bod overiť a zaevidovať manuálne.

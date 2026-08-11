# Auditná matica UI/UX

## UX0 – auditná infraštruktúra

| ID     | Etapa | Oblasť a úloha                           | Štandard   | Závažnosť | Dodanie | Stav súladu                 | Dôkaz                   | Dopad                                                | Cieľové správanie                                                  | Akceptácia                                   | Vynútenie | Plánovaná etapa    | Stav opravy  |
| ------ | ----- | ---------------------------------------- | ---------- | --------- | ------- | --------------------------- | ----------------------- | ---------------------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------- | --------- | ------------------ | ------------ |
| UX0-01 | UX0   | systematické vynucovanie pravidiel       | 19, 20, 24 | P0        | BLOKUJE | opravené                    | `npm run lint`          | pravidlo bez kontroly postupne zanikne               | lint kontroluje a11y, farby, multiple select a priority checklistu | všetky tri lint vrstvy prejdú                | lint      | UX0                | hotovo       |
| UX0-02 | UX0   | mobilné odhlásenie bez prístupného mena  | 10.2, 14   | P0        | BLOKUJE | opravené                    | Axe desktop/mobile      | používateľ čítačky nerozoznal akciu                  | ikonová akcia má stabilný programový názov                         | Axe bez `button-name`                        | test      | UX0                | hotovo       |
| UX0-03 | UX0   | nepomenované prepínače a listbox Reakcií | 10.7, 14   | P0        | BLOKUJE | opravené                    | Axe `/reakcie`          | hlavný tok nebol zrozumiteľný asistívnej technológii | každý switch a výsledkový zoznam má významový názov                | Axe bez `aria-*-name`                        | test      | UX0                | hotovo       |
| UX0-04 | UX0   | nedostatočný kontrast sekundárneho textu | 8.3, 14    | P1        | BACKLOG | opravené                    | Axe šesť hlavných route | časť textu bola pod WCAG AA                          | významové textové tokeny a Discord preview dosahujú AA             | Axe bez `color-contrast`                     | test      | UX0                | hotovo       |
| UX0-05 | UX0   | hardcoded farby                          | 8.2, 24.1  | P1        | BACKLOG | otvorené, uzamknuté         | baseline `241 + 26`     | budúce zmeny by ďalej trieštili paletu               | nový dlh nevznikne, legacy klesá po etapách                        | lint zlyhá pri zvýšení baseline              | lint      | UX4, UX6, UX10     | backlog      |
| UX0-06 | UX0   | duplicitné lokálne page stavy            | 10.1, 11   | P1        | BACKLOG | pilot opravený              | `AsyncState.test.tsx`   | rozdielne loading/error/empty správanie              | spoločná status/alert sémantika a recovery                         | izolovaný test loading, empty, error a retry | test      | UX4, UX8–UX9       | pilot hotový |
| UX0-07 | UX0   | ochrana proti dvojkliku                  | 3.6, 10.2  | P0        | BLOKUJE | opravené pre kritický pilot | browser scenár 07       | dva kliky môžu spôsobiť dva externé účinky           | busy stav a idempotencia vytvoria najviac jeden request/účinok     | `dblclick` → presne jeden confirm request    | test      | UX0 a každá doména | pilot hotový |
| UX0-08 | UX0   | návrat fokusu z modalu                   | 10.9, 12.2 | P0        | BLOKUJE | existujúci súlad            | browser scenár 16       | klávesnicový používateľ môže stratiť miesto          | Escape vráti fokus na opener                                       | desktop/mobile test prejde                   | test      | UX0 a každá doména | hotovo       |

Inventár východiskového dlhu: 241 hex výskytov v monolitickom `global.css`, 26 doménových farieb v Discord náhľade, 87 priamych použití button komponentu/elementu a viac lokálnych implementácií loading/error/empty stavu. UX0 tento dlh nezakrýva veľkým redesignom; uzamyká jeho rast a pripravuje po etapách overiteľnú konsolidáciu.

## UX1 – Reakcie

Nasleduje po uzavretom UX0.

## UX2 – Roly

Čaká na UX1.

## UX3 – Nastavenia

Čaká na UX2.

## UX4 – aplikačný rámec a spoločné stavy

Čaká na UX3.

## UX5 – Prehľad

Čaká na UX4.

## UX6 – Redakčný pult a Discord náhľad

Čaká na UX5.

## UX7 – Kanály

Čaká na UX6.

## UX8 – História publikácií a Audit

Čaká na UX7.

## UX9 – Stav systému a systémové obrazovky

Čaká na UX8.

## UX10 – finálna konzistencia a regresia

Čaká na UX9.

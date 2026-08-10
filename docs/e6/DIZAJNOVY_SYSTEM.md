# Dizajnový systém E6

## Vizuálny smer

Rozhranie má pôsobiť pokojne, redakčne a dôveryhodne. Vychádza z jemného
zeleno-neutrálneho pozadia, tmavozelenej značky a bielych pracovných plôch. Nepoužíva
dekoratívne dashboardové grafy ani generické ilustrácie; hierarchiu vytvára
typografia, priestor, stavové farby a reálny obsah oznamov.

## Tokeny

- shadcn semantické OKLCH tokeny pre background, foreground, card, muted, accent,
  border, input a ring,
- aplikačný canvas `#f4f7f4`, surface `#ffffff`, ink `#17231b`, muted ink
  `#66736b`, line `#dfe7e1`,
- brand `#2f7552`, strong brand `#20543a`, soft brand `#e4f1e9`,
- warning `#a45d13`, danger `#b53d3d`,
- focus používa kontrastný semantický `ring` token,
- základný radius 12 px, pracovné panely približne 16 px,
- tiene iba na hierarchicky zvýšených pracovných plochách.

## Typografia a hustota

- lokálne balený variabilný font Geist bez externého sieťového načítania,
- nadpis stránky približne `clamp(1.75rem, 3vw, 2.35rem)`,
- hustota sa prispôsobuje funkcii: formuláre ostávajú pohodlné, spoločný
  redakčný zoznam je kompaktnejší ako marketingová stránka,
- label môže byť verzálkami iba pri krátkom stavovom texte,
- editor používa pohodlnú hustotu; informácie sa neskrývajú iba do tooltipov.

## Povinné komponentové stavy

Shadcn komponenty nad Base UI primitívami sú základom pre button, input,
select, textarea, switch, modal a confirmation dialog. Každý musí mať default,
hover, focus-visible, active a disabled stav. Serverové bloky musia mať loading,
empty, error a retry. Uloženie musí rozlišovať saving, saved, validation error,
forbidden a version conflict.

## Accessibility

- sémantické landmarks a jediný hlavný `h1`,
- skip link, popisy formulárov a stavové oznamy cez `aria-live`,
- farba nikdy nie je jediným nositeľom stavu,
- logické poradie tabu a návrat focusu po zavretí dialógu,
- redukovaný pohyb rešpektuje `prefers-reduced-motion`,
- kontrast textu a ovládacích prvkov minimálne WCAG AA,
- náhľad Discordu je doplnok; rovnaký obsah zostáva čitateľný aj ako textový zoznam.

## Redakčný pult

- Google, manuálne a INFO položky používajú rovnaký riadkový model; pôvod sa
  rozlišuje ikonou, textovým názvom zdroja a stavom, nie odlišným layoutom.
- Na desktope sú zdrojové filtre, spoločný zoznam a Discord kanál tri súčasné
  časti jedného pracoviska.
- Pult sa na veľkom monitore rozšíri až po samostatný bezpečný pracovný limit a
  využije zostávajúcu výšku viewportu bez schovania spodného okraja; nepoužíva
  úzky limit dashboardových kariet. Dlhý obsah má vlastný vnútorný scroll.
- Hlavná plocha upraviteľného riadka je veľký button cieľ s názvom „Upraviť
  {názov}“, ovládaním Enter/Space a focus ringom. Samostatné tlačidlo „Upraviť“
  zostáva ako explicitná pomôcka; deštruktívna akcia je samostatný súrodenec.
- Discord náhľad má vlastnú tmavú vizuálnu vrstvu blízku skutočnému klientovi,
  ale nesmie znižovať čitateľnosť alebo meniť kanonický obsah.
- Embed accent zachováva pôvodnú mesačnú paletu: INFO používa jemný odtieň,
  kalendárová alebo manuálna udalosť sýty odtieň rovnakého mesiaca.
- Na mobile sa panely zoradia pod seba a zdrojové filtre sa zmenia na
  horizontálne rolovateľný pás; obsah a náhľad sa neschovávajú do záložiek.

# E12 – používateľská akceptácia

Výsledok pri každom bode označiť dátumom, rolou testera a `OK/CHYBA`.

## Admin

- [ ] Discord login a správne zobrazenie roly.
- [ ] Prehľad a najbližší 14-dňový balík.
- [ ] Redakcia jedného výskytu aj série odteraz.
- [ ] `stop carlo` je viditeľné, vylúčené a dá sa explicitne zaradiť.
- [ ] Manuálna udalosť vrátane viacdňovej celodennej udalosti.
- [ ] INFO s uploadom obrázka a inkluzívnou expiráciou.
- [ ] Discord náhľad, farby, jedno `@everyone` a seen cieľ.
- [ ] Vytvorenie kanála a schválenie správnej archivácie.
- [ ] Udelenie/odobranie Team Mod roly a ochrana posledného Admina.
- [ ] Reakcie, test reakcie, Google kalendáre, alert kategórie.
- [ ] História skutočných publikácií a oddelená tieňová prevádzka.

## Team Mod

- [ ] Upraví obsah a vytvorí manuálny/INFO záznam.
- [ ] Vytvorí kanál a požiada o archiváciu.
- [ ] Nevidí ani nevykoná Admin-only nastavenia, roly či publish.

## SDB / FMA

- [ ] Vidí draft a Discord náhľad.
- [ ] Prejde dvojkrokovým ručným publish potvrdením v staging kanáli; používa sa
  iba dočasný staging-only `ALLOW_MANUAL_PUBLICATION_IN_SHADOW=true` podľa
  `KROKY_PRE_POUZIVATELA.md`, nikdy globálny režim `live`.
- [ ] Nemá prístup k redakcii, kanálom, rolám ani Admin nastaveniam.

## Responzivita a prístupnosť

- [ ] desktop, tablet a mobil bez skrytých akcií alebo horizontálneho scrollu,
- [ ] 200 % zoom a dlhé slovenské texty,
- [ ] iba klávesnica: skip link, focus, modal/drawer, Escape a focus návrat,
- [ ] čitateľné loading, prázdne, konfliktové a chybové stavy,
- [ ] reduced motion a viditeľný focus.

Browser UAT zatiaľ nie je podpísaný; v aktuálnej relácii nebol dostupný in-app
browser ani pripojený externý browser. E13 cutover je do podpísania tohto
checklistu blokovaný.

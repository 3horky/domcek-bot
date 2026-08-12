# Autonómny priechod UI/UX auditu

Tento súbor je pracovný index nočného priechodu UX0–UX10. Normatívny postup je v kapitole 20 `PLAN_UI_UX_AUDITU.md`.

| Etapa | Oblasť                             | Stav               | Aktuálny dôkaz                     | Commit / CI    |
| ----- | ---------------------------------- | ------------------ | ---------------------------------- | -------------- |
| UX0   | auditná infraštruktúra             | hotovo             | lint, 15 unit, 46 browser scenárov | `87cb6ec`      |
| UX1   | Reakcie                            | hotovo             | 193 backend, 15 unit, 54 browser   | `ef96ccf`      |
| UX2   | Roly                               | hotovo             | 15 unit, 68 browser, 2 full-stack  | `0d7e1ba`      |
| UX3   | Nastavenia                         | hotovo             | 15 unit, 80 browser, 2 full-stack  | `a9dcbbe`      |
| UX4   | aplikačný rámec a spoločné stavy   | hotovo             | 15 unit, 86 browser, 2 full-stack  | `be701aa`      |
| UX5   | Prehľad                            | hotovo             | 193 backend, 15 unit, 92 browser   | `2a45873`      |
| UX6   | Redakčný pult a Discord náhľad     | hotovo             | 194 backend, 15 unit, 102 browser  | `9c7ad70`      |
| UX7   | Kanály                             | funkčný rez hotový | 15 unit, 110 browser; Undo → UX10  | `c8f4b6d`      |
| UX8   | História publikácií a Audit        | hotovo             | 15 unit, 122 browser, 2 backend    | `08a3fee`      |
| UX9   | Stav systému a systémové obrazovky | hotovo             | 16 unit, 132 browser, Axe + render | `b9cdc1f`      |
| UX10  | finálna konzistencia a regresia    | audit uzavretý     | 195 backend, 16 unit, 132 browser  | `5797694`; CI fix |

## Pravidlá pokračovania

- Pred etapou sa načíta celý destilát a celé relevantné kapitoly štandardu.
- Otázka, ktorá neblokuje bezpečnú prácu, ide do `ODLOZENE_ROZHODNUTIA.md`.
- Každý nález ide do `AUDIT_MATICA.md`; komentár v chate nie je evidencia.
- `STATUS.md` sa upraví v tom istom pracovnom reze ako kód alebo dokumentácia.
- `live`, produkčný externý zásah a deštruktívna práca zostávajú zakázané.

## Posledný checkpoint

- **Aktuálna etapa:** autonómny UX0–UX10 audit je uzavretý ako bezpečný shadow build; nejde o povolenie `live`
- **Najbližší krok:** opraviť mechanický Prettier nález z runu `31558315155` a odmonitorovať opakovaný CI; UX10-01/02 zostávajú samostatný stop-ship implementačný balík
- **Okamžitý blokátor:** žiadny

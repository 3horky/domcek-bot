# Autonómny priechod UI/UX auditu

Tento súbor je pracovný index nočného priechodu UX0–UX10. Normatívny postup je v kapitole 20 `PLAN_UI_UX_AUDITU.md`.

| Etapa | Oblasť                             | Stav     | Aktuálny dôkaz         | Commit / CI |
| ----- | ---------------------------------- | -------- | ---------------------- | ----------- |
| UX0   | auditná infraštruktúra             | prebieha | pripravuje sa baseline | –           |
| UX1   | Reakcie                            | čaká     | –                      | –           |
| UX2   | Roly                               | čaká     | –                      | –           |
| UX3   | Nastavenia                         | čaká     | –                      | –           |
| UX4   | aplikačný rámec a spoločné stavy   | čaká     | –                      | –           |
| UX5   | Prehľad                            | čaká     | –                      | –           |
| UX6   | Redakčný pult a Discord náhľad     | čaká     | –                      | –           |
| UX7   | Kanály                             | čaká     | –                      | –           |
| UX8   | História publikácií a Audit        | čaká     | –                      | –           |
| UX9   | Stav systému a systémové obrazovky | čaká     | –                      | –           |
| UX10  | finálna konzistencia a regresia    | čaká     | –                      | –           |

## Pravidlá pokračovania

- Pred etapou sa načíta celý destilát a celé relevantné kapitoly štandardu.
- Otázka, ktorá neblokuje bezpečnú prácu, ide do `ODLOZENE_ROZHODNUTIA.md`.
- Každý nález ide do `AUDIT_MATICA.md`; komentár v chate nie je evidencia.
- `STATUS.md` sa upraví v tom istom pracovnom reze ako kód alebo dokumentácia.
- `live`, produkčný externý zásah a deštruktívna práca zostávajú zakázané.

## Posledný checkpoint

- **Aktuálna etapa:** UX0
- **Najbližší krok:** inventarizácia route, rolí, fixtures a existujúcich testovacích mechanizmov
- **Okamžitý blokátor:** žiadny

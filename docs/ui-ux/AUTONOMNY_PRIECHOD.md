# Autonómny priechod UI/UX auditu

Tento súbor je pracovný index nočného priechodu UX0–UX10. Normatívny postup je v kapitole 20 `PLAN_UI_UX_AUDITU.md`.

| Etapa | Oblasť                             | Stav      | Aktuálny dôkaz                     | Commit / CI    |
| ----- | ---------------------------------- | --------- | ---------------------------------- | -------------- |
| UX0   | auditná infraštruktúra             | hotovo    | lint, 15 unit, 46 browser scenárov | `87cb6ec`      |
| UX1   | Reakcie                            | hotovo    | 193 backend, 15 unit, 54 browser   | `ef96ccf`      |
| UX2   | Roly                               | hotovo    | 15 unit, 68 browser, 2 full-stack  | `0d7e1ba`      |
| UX3   | Nastavenia                         | hotovo    | 15 unit, 80 browser, 2 full-stack  | `a9dcbbe`      |
| UX4   | aplikačný rámec a spoločné stavy   | hotovo    | 15 unit, 86 browser, 2 full-stack  | čaká na commit |
| UX5   | Prehľad                            | nasleduje | baseline sa pripraví               | –              |
| UX6   | Redakčný pult a Discord náhľad     | čaká      | –                                  | –              |
| UX7   | Kanály                             | čaká      | –                                  | –              |
| UX8   | História publikácií a Audit        | čaká      | –                                  | –              |
| UX9   | Stav systému a systémové obrazovky | čaká      | –                                  | –              |
| UX10  | finálna konzistencia a regresia    | čaká      | –                                  | –              |

## Pravidlá pokračovania

- Pred etapou sa načíta celý destilát a celé relevantné kapitoly štandardu.
- Otázka, ktorá neblokuje bezpečnú prácu, ide do `ODLOZENE_ROZHODNUTIA.md`.
- Každý nález ide do `AUDIT_MATICA.md`; komentár v chate nie je evidencia.
- `STATUS.md` sa upraví v tom istom pracovnom reze ako kód alebo dokumentácia.
- `live`, produkčný externý zásah a deštruktívna práca zostávajú zakázané.

## Posledný checkpoint

- **Aktuálna etapa:** UX4 lokálne uzavretá; nasleduje UX5
- **Najbližší krok:** commit/push UX4, potom rozhodovací audit Prehľadu
- **Okamžitý blokátor:** žiadny

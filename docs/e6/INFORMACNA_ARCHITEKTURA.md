# Informačná architektúra a route mapa E6

## Primárna navigácia

| Route | Názov | Primárna úloha | Minimálna capability |
|---|---|---|---|
| `/` | Prehľad | zistiť najbližší termín a stav balíka | `VIEW_ADMIN` |
| `/oznamy` | Redakčný pult | na jednom mieste spravovať Google, manuálny a INFO obsah a kontrolovať Discord výsledok | `VIEW_ADMIN`; zápis `EDIT_CONTENT` |
| `/audit` | Audit | dohľadať zmeny podľa rolového podvýberu | serverový audit policy |
| `/stav` | Stav systému | diagnostika API a databázy | `VIEW_ADMIN` |

Historické adresy `/manualne-udalosti` a `/info` presmerujú na `/oznamy`. Nie sú
samostatnými pracoviskami ani položkami navigácie. Redakčný pult vlastní spoločný
zoznam, zdrojové filtre, všetky obsahové modaly a kanonický Discord náhľad.

Kanály, archivácia, roly, reakcie a publikačné nastavenia sa pridajú do tejto
mapy v E9 po vzniku ich aplikačných služieb. História a ručné publikovanie sa
pridajú v E7. Nezobrazujú sa ako nefunkčné položky.

## Prihlasovací tok

1. Aplikácia načíta `/api/v1/session` s credentials.
2. HTTP 200 vytvorí principal kontext a sprístupní route podľa capability.
3. HTTP 401 zobrazí samostatnú prihlasovaciu obrazovku s Discord OAuth linkom a
   bezpečným lokálnym `return_to`.
4. Chyba dostupnosti identity zobrazí retry stav, nie falošnú anonymnú session.
5. Odhlásenie odošle CSRF chránený POST a vyčistí lokálny principal stav.
6. Každá chránená odpoveď 401 vráti aplikáciu do prihlasovacieho stavu.

## Načítanie a vlastníctvo dát

- Session kontext vlastní najvyššia aplikačná vrstva.
- Každá route vlastní iba svoj serverový load/error stav; Redakčný pult načíta
  draft, manuálne udalosti a INFO oznamy ako jedno pracovné prostredie.
- Draft je jediný zdroj pre dashboard, editor a Discord preview.
- Formulár drží lokálnu pracovnú kópiu a `expected_version`; po HTTP 409 zobrazí
  aktuálnu serverovú hodnotu a vyžaduje vedomé rozhodnutie používateľa.
- CSRF token sa číta z ne-HttpOnly cookie iba tesne pred meniacim requestom;
  neukladá sa do trvalého browser storage.

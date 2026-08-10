# Report vytvorenia Google Calendar fixtures

- **Dátum vytvorenia:** 8. august 2026
- **Posledné overenie:** 9. august 2026
- **Kalendár:** `Domcek Bot v2 Test`
- **Calendar ID:** `3horky.sk_classroom0fb38572@group.calendar.google.com`
- **Prístup pripojeného účtu:** owner
- **Kontrolované obdobie pred zápisom:** 24. 10. 2026 – 6. 4. 2027
- **Stav obdobia pred zápisom:** bez udalostí

## Vytvorené záznamy

| Scenár | Google event/master ID | Stav |
|---|---|---|
| window start | `qrpig6jonkc15ukg96a3nfrvs8` | vytvorený |
| before window | `ts7ltqs9h2ignlpplrjt8o2el8` | vytvorený |
| timed basic + Google popis | `b8i4lfjnbjm2i69jf04c4opgfo` | vytvorený, popis overený full readom |
| Google description policy | `uufko4jg1lsclu8vcc6f0vpbjs` | vytvorený, popis overený full readom |
| stop carlo | `mhpinbjm0tqk2356c5f47ud39o` | vytvorený, `STOP CARLO` overené full readom |
| weekly recurring master | `oj9d0039rmiqmfl6rcnmcbh228` | vytvorený, 3 výskyty |
| moved recurring instance | `oj9d0039rmiqmfl6rcnmcbh228_20261104T170000Z` | presunutý na 5. 11. 2026 19:00; original start zachovaný |
| cancellation series master | `ebs21fhhl9kmq8h25nj1s2d3d4` | vytvorený, 2 pôvodné výskyty |
| cancelled instance | `ebs21fhhl9kmq8h25nj1s2d3d4_20261102T160000Z` | odstránený iba konkrétny výskyt |
| same-time primary | `ofurslcu31vs0roijn10vojd7s` | vytvorený |
| minute before window end | `6g7efqmv16du9c1ajkaadubrug` | vytvorený |
| exact exclusive window end | `b84uvsdj0dtpd7j8c4cvml207g` | vytvorený |
| spring DST | `svek652gerchprhfr1b5imats4` | vytvorený s UTC+2 lokálnym časom |

Všetky konektorom vytvorené udalosti majú prefix `[DOMCEK V2]`, sú transparent a bez účastníkov alebo Google Meet linku. Pôvodná explicitná viditeľnosť `private` bola 9. augusta zmenená na `default`, aby read-only service account videl ich testovacie názvy a popisy bez zvýšenia svojich oprávnení.

## Overenie

- Po doplnkovom ICS importe kontrolné vyhľadanie v celom období vrátilo 16 viditeľných výskytov v primary kalendári.
- Secondary kalendár `Domcek Bot v2 Test Secondary` s ID `c_b1c070f7c5f86b6dfbed467349e07a351b49377f172efbfd24bb039cf9ccbed5@group.calendar.google.com` obsahuje jednu same-time priority fixture.
- Druhý zrušený výskyt cancellation série sa vo výsledkoch nezobrazuje.
- Presunutý výskyt má nový čas 5. 11. 2026 19:00 a `original_start_time` 4. 11. 2026 18:00.
- Full read potvrdil zdrojové popisy pri `timed-basic`, `google-description` a `stop-carlo`.
- Service account s OAuth scope `calendar.readonly` a efektívnou rolou `reader` načítal 16 aktívnych a 1 zrušený primary výskyt a 1 aktívny secondary výskyt.
- Primary list sa načítal na štyroch stranách pri `maxResults=5`, čím bolo reálne overené stránkovanie.
- Service-account výstup obsahoval dve celodenné udalosti, jednu udalosť bez titulku, štyri recurring výskyty, zachovaný original start presunutého výskytu, Google popis aj `STOP CARLO`.
- Google API vracia pre oba kalendáre kanonické časové pásmo `Europe/Prague`, ktoré má rovnaké časové pravidlá ako produktová zóna `Europe/Bratislava`.

## Doplnené fixtures

Dostupný konektor nevedel bezpečne vytvoriť:

- pravú celodennú udalosť,
- pravú viacdňovú celodennú udalosť,
- udalosť bez povinného titulku,
- udalosť v novom sekundárnom kalendári, kým tento kalendár neexistuje.

Tieto scenáre boli úspešne doplnené z dvoch pripravených ICS súborov.

## Výsledok E0

Google Calendar API, service-account autentifikácia, read-only zdieľanie, full list a stránkovanie sú overené. Inkrementálna synchronizácia so `syncToken` sa implementuje a automatizovane testuje v E3.

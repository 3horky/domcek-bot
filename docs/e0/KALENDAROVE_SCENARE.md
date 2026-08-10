# Kalendárové testovacie scenáre E0

## 1. Referenčný publikačný termín

Hlavná sada používa:

```text
publikačný termín: 26. 10. 2026 20:00 Europe/Bratislava
okno: [26. 10. 2026 20:00, 9. 11. 2026 20:00)
```

Tento termín je zámerne po jesennom prechode na štandardný čas. Samostatná DST sada testuje jarný prechod.

## 2. Povinné scenáre

| ID | Scenár | Očakávanie |
|---|---|---|
| `window-start` | udalosť presne na začiatku okna | zahrnúť |
| `before-window` | udalosť skončí minútu pred oknom | nezahrnúť |
| `timed-basic` | bežná časovaná udalosť | zahrnúť, odvodiť deň a čas |
| `all-day` | celodenná udalosť | zahrnúť pred časované eventy dňa |
| `multi-overlap` | viacdňová udalosť začne pred oknom a trvá v ňom | zahrnúť |
| `window-end` | udalosť začne presne na exkluzívnom konci | nezahrnúť |
| `before-window-end` | udalosť začne minútu pred koncom | zahrnúť |
| `google-description` | zdrojový popis bez override | defaultne nepublikovať, ponúknuť v editore |
| `stop-carlo` | popis obsahuje `STOP CARLO` | vylúčiť, ponechať v editore |
| `missing-title` | chýba názov | bezpečný fallback a warning |
| `recurring-base` | týždenná séria | stabilná series identita |
| `recurring-moved` | jeden výskyt presunutý | zachovať original start identitu |
| `recurring-cancelled` | jeden výskyt zrušený | nezahrnúť |
| `same-time-primary` | rovnaký čas, calendar priority 10 | zaradiť pred secondary |
| `same-time-secondary` | rovnaký čas, calendar priority 20 | zaradiť po primary |

## 3. Redakčné scenáre nad fixtures

Nad synchronizovanými udalosťami neskôr vytvoriť testy:

1. Vlastný popis `timed-basic` sa použije v dvoch po sebe nasledujúcich draftoch.
2. `stop-carlo` s `FORCE_INCLUDE` sa publikuje bez riadiacej frázy.
3. `timed-basic` s `FORCE_EXCLUDE` zostane iba v editore.
4. Instance override jedného recurring výskytu nezmení ďalší výskyt.
5. Series override účinný od druhého výskytu zmení druhý a ďalšie, nie prvý.
6. Instance override má prednosť pred series override.
7. `INTENTIONALLY_EMPTY` zastaví Google description aj series description.

## 4. DST scenáre

Jarné referenčné okno:

```text
publikačný termín: 22. 3. 2027 20:00 Europe/Bratislava
okno končí: 5. 4. 2027 20:00 Europe/Bratislava
```

Počas okna sa zmení offset z UTC+1 na UTC+2. Očakávania:

- lokálny publikačný čas zostáva 20:00,
- 14 dní sa vyhodnocuje podľa definovaného zoned času, nie pripočítaním pevného UTC offsetu,
- udalosť po zmene času sa zobrazuje s lokálnym časom z kalendára,
- ďalší týždenný termín zostáva v rovnaký lokálny deň a hodinu.

## 5. Artefakty

- `calendar-scenarios.json` je provider-neutrálny očakávaný vstup pre automatizované testy.
- `domcek-v2-test-calendar.ics` je úplná ručne importovateľná sada pre nový prázdny Google kalendár.
- `domcek-v2-test-calendar-remaining.ics` obsahuje iba scenáre, ktoré nevedel vytvoriť dostupný konektor v existujúcom kalendári `Test`.
- `domcek-v2-secondary-calendar.ics` patrí do druhého testovacieho kalendára na overenie priority zdrojov.
- Po importe sa Google pridelené event ID zachytia až cez sync; nesmú sa hardcodovať do doménových testov.

Aktuálny stav reálneho testovacieho kalendára je v `GOOGLE_FIXTURE_REPORT.md`.

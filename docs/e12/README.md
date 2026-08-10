# E12 – staging, tieňová prevádzka a UAT

## Bezpečný režim

Staging worker musí mať `PUBLICATION_EXECUTION_MODE=shadow`. V tomto režime
vykoná read-only Calendar sync a zostaví kanonický draft, ale nespustí živý
scheduler, nevytvorí `publication_run` a nevolá Discord odoslanie. Dôkaz uloží
do samostatnej tabuľky a zobrazí v Histórii publikácií. Dôkaz nesie stav a časy
syncu každého aktívneho kalendára; ak čo i len jeden zdroj zlyhá alebo chýba,
draft zostane diagnosticky viditeľný, ale je jasne označený ako neplatný a
nepočíta sa do akceptačných cyklov.

Povolené hodnoty sú:

- `paused` – žiadny automatický draft ani publish,
- `shadow` – sync a dôkaz bez odoslania,
- `live` – automatické odoslanie; patrí až do schváleného E13 cutoveru.

## Nasaditeľná staging konfigurácia

Repozitár obsahuje bezpečné šablóny `v2/.env.staging.example` a
`v2/deploy/.env.staging.deploy.example`. Po ich skopírovaní mimo repozitára,
nahradení placeholderov a nastavení oprávnení `600` sa staging pred štartom
overí bez vypísania tajomstiev:

```bash
cd v2
python scripts/validate_production_config.py \
  --staging \
  --app-env .env.staging \
  --deploy-env deploy/.env.staging.deploy \
  --check-files
CARLO_ENV_FILE=.env.staging \
  docker compose --env-file deploy/.env.staging.deploy \
  -f compose.production.yaml config --quiet
```

Preflight odmietne iný režim než `shadow`, zamenený produkčný env súbor,
meniteľné image tagy, HTTP URL, nezhodné Discord ID, otvorené oprávnenia
secretov a štandardne aj povolenie ručného publishu.

## Testovacie kalendáre

Lokálny staging možno idempotentne pripojiť k dvom E0 read-only kalendárom:

```bash
docker compose exec -T api python scripts/configure_shadow_calendars.py \
  --guild-id DISCORD_GUILD_ID \
  --actor-user-id ADMIN_DISCORD_USER_ID \
  --confirm-shadow
```

Skript načíta iba ID z `E3_TEST_PRIMARY_CALENDAR_ID` a
`E3_TEST_SECONDARY_CALENDAR_ID`, existujúci zdroj nezdvojí a nové zdroje založí
cez tú istú auditovanú `SettingsService` ako web.

## Kontrolná brána

E12 nemožno uzavrieť pred dvoma rôznymi týždennými slotmi alebo výslovne
prijatým ekvivalentným rehearsal dôkazom a podpísaným browser UAT Admina, Team
Moda a SDB/FMA. Používateľ rehearsal prijal 11. augusta 2026; zostávajúce
technické a UAT dôkazy sa zapisujú do `SHADOW_CYKLY.md` a `UAT_CHECKLIST.md`.

Presné používateľské a externé kroky vrátane bezpečnej staging-only výnimky
pre ručný publish sú v `KROKY_PRE_POUZIVATELA.md`. Výnimka nikdy nepovoľuje
automatický `live` worker a po UAT sa musí vrátiť na `false`.

Októbrové Calendar fixtures možno bez zápisu a bez Discord účinku nacvičiť cez
`scripts/rehearse_shadow_cycles.py` s dvoma explicitnými timezone-aware
`--reference-time`. Výstup obsahuje sloty, okná, hashe, verejné aj vylúčené
položky a počet plánovaných správ. Rehearsal dopĺňa testy a po výslovnom
akceptačnom rozhodnutí z 11. augusta 2026 tvorí schválený ekvivalent dvoch
reálnych shadow slotov pre E12.

# E12 – kroky, ktoré vyžadujú používateľa alebo externé prostredie

Lokálna implementácia a automatizované dôkazy sú hotové. Nasledujúce kroky
Codex nesmie vykonať bez používateľského rozhodnutia, prístupu k hostingu alebo
reálnych rolových testerov.

## 1. Rozhodnutie o shadow cykloch – splnené

Používateľ 11. augusta 2026 výslovne prijal read-only rehearsal slotov
26. októbra a 2. novembra 2026 ako ekvivalent pre E12. Čerstvé opakovanie
potvrdilo pôvodné hashe, prekryv udalosti, zachovanie redakčného popisu,
recurrence, `stop carlo`, dva kalendáre, viacdňové udalosti a delenie správ.
Rozhodnutie a kontrolné výsledky sú v `SHADOW_CYKLY.md`.

## 2. Commit, push a vzdialený CI

Používateľ 11. augusta 2026 výslovne povolil commit a push na `origin/main`.
Vznikol implementačný commit `6100cd63dea7136063a990cbbb5ec0f3a1a49d01`
a nadväzujúce dokumentačné commity. Pracovný strom je čistý, ale HTTPS push sa
na tomto hoste zastavil v `osxkeychain` bez sprístupnenia poverenia a existujúci
SSH kľúč GitHub nepozná. Remote `origin/main` preto stále bezpečne zostáva na
`48f301e91ebfb0f566b94ef462f557fa4e03d542`.

Používateľ musí v lokálnom Termináli dokončiť autentifikovaný fast-forward push
príkazom `git push origin main` alebo najprv odomknúť/povoliť macOS kľúčenku a
nechať Codex push zopakovať. Token ani heslo sa nesmú posielať v konverzácii.
Po pushnutí musí byť workflow `Domček Bot 2.0 CI` úplne zelený vrátane:

- 188 backendových testov,
- 13 Vitest testov,
- 34 browser acceptance behov,
- 2 full-stack browser behov proti izolovanému PostgreSQL,
- backend/frontend image buildov a repository-safety jobu.

Odkaz na konkrétny zelený beh a commit SHA treba doplniť do
`KONTROLNA_BRANA.md`.

## 3. Produkčne podobný HTTPS staging

Treba prideliť staging host a HTTPS doménu a pripraviť staging-only env/secrets.
Východiskové šablóny sú `v2/.env.staging.example` a
`v2/deploy/.env.staging.deploy.example`; ich kópie s reálnymi hodnotami musia
ostať mimo Gitu a mať oprávnenia `600`.
Povinné bezpečné hodnoty počas UAT:

```dotenv
APP_ENV=staging
PUBLICATION_EXECUTION_MODE=shadow
ALLOW_MANUAL_PUBLICATION_IN_SHADOW=false
```

Staging musí používať iba testovaciu Discord aplikáciu/guild, testovacie
kalendáre, staging PostgreSQL a staging oznamovací kanál. Produkčné credentials
sa nesmú zdieľať ani kopírovať do repozitára.

Pred prvým štartom treba spustiť bezpečnostný preflight:

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

## 4. Rolový a vizuálny UAT

Admin, Team Mod a SDB/FMA sa prihlásia vlastnými Discord účtami a pri každom
bode `UAT_CHECKLIST.md` zapíšu dátum, rolu testera a `OK` alebo `CHYBA`.
Vizuálna časť sa vykoná aspoň na počítači, tablete a mobile, pri 200 % zoome a
iba klávesnicou. Nález sa najprv zapíše ako otvorená chyba; checkbox sa nesmie
označiť, kým je chyba nevyriešená a znovu overená.

## 5. Bezpečný staging test ručného publikovania

Automatický worker musí zostať v `shadow`. Iba počas riadeného SDB/FMA testu je
možné na HTTPS stagingu dočasne nastaviť:

```dotenv
APP_ENV=staging
PUBLICATION_EXECUTION_MODE=shadow
ALLOW_MANUAL_PUBLICATION_IN_SHADOW=true
```

Túto dočasnú konfiguráciu preflight prijme iba s vedomým prepínačom
`--allow-staging-manual-publication`. Bez neho je povolenie ručného účinku
chyba:

```bash
python scripts/validate_production_config.py \
  --staging \
  --allow-staging-manual-publication \
  --app-env .env.staging \
  --deploy-env deploy/.env.staging.deploy \
  --check-files
```

Po reštarte API a bota sa skontroluje cieľový staging kanál, SDB/FMA vykoná
preview a dvojkrokové potvrdenie a Admin overí presný Discord výstup. Táto
výnimka povoľuje iba explicitný ručný staging účinok; automatický worker ostáva
bez Discord odoslania. Bezprostredne po teste sa hodnota vráti na `false`, API
a bot sa reštartujú a uloží sa dôkaz, že worker zostal v `shadow`.

## Zakázané do uzavretia E12

- nezapínať `PUBLICATION_EXECUTION_MODE=live`,
- nerobiť produkčný cutover,
- neprepínať produkčný Discord kanál ani credentials,
- nevyraďovať pôvodného bota,
- nepovažovať automatizované testy za ľudský UAT podpis.

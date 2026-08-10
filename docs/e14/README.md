# E14 – stabilizácia a ukončenie legacy verzie

## Stav

Runbook a read-only reporting sú pripravené. Etapa sa začne až po úspešnom E13
cutoveri a trvá minimálne tri skutočné publikačné cykly. Legacy bot zostáva
obnoviteľný až do podpísania kontrolnej brány E14.

## Automatizovaný podklad

Po každom cykle sa vytvorí report bez zápisu do databázy:

```bash
CARLO_ENV_FILE=.env.production docker compose \
  --env-file .env.production \
  --env-file deploy/.env.deploy \
  -f compose.production.yaml \
  exec -T api python scripts/generate_stabilization_report.py \
  --guild-id PRODUKCNY_GUILD_ID --cycles 3 \
  --cutover-at 2026-08-10T20:00:00+02:00 \
  --backup-restore-verified --discord-output-verified
```

`--cutover-at` musí byť skutočný schválený produkčný cutover s časovým pásmom.
Obe potvrdzovacie voľby sa smú použiť až po reálnej produkčnej restore rehearsal
a manuálnom porovnaní všetkých troch Discord výstupov.

Report počíta iba tri alebo viac rozvrhovo po sebe idúcich, odlišných a úspešných
automatických slotov po cutoveri. Ručný run, pred-cutover run, chýbajúci týždeň,
zmenený obsah opakovanej udalosti, nečerstvý či zlyhaný aktívny kalendár,
nevysvetlený warning kód, vypnutá automatika, otvorený incident alebo nezdravý
runtime bránu zastavia. Brána navyše vyžaduje presne jednu čerstvú pripojenú
inštanciu bota a jednu čerstvú bežiacu inštanciu workera v režime `live`.
`ready_for_legacy_retirement=true` je iba technický predpoklad; nenahrádza Admin
a technický podpis ani retenčné rozhodnutie.

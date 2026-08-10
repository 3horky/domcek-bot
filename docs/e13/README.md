# E13 – produkčné nasadenie a cutover

## Stav

Produkčné artefakty a runbook sú pripravené, ale produkcia nebola nasadená ani
aktivovaná. E13 je blokovaná otvorenou E12 bránou a chýbajúcim produkčným
hostom, doménou, credentials, release digestmi a explicitným cutover súhlasom.

## Artefakty

- `v2/compose.production.yaml` – samostatný produkčný runtime bez bind mountu
  zdrojového kódu,
- `v2/frontend/Dockerfile.production` – statický optimalizovaný frontend,
- `v2/deploy/Caddyfile` – HTTPS, reverse proxy, security headers a access log,
- `v2/.env.production.example` – aplikačná konfigurácia bez tajomstiev,
- `v2/deploy/.env.deploy.example` – nemenné image referencie a host paths,
- `v2/scripts/validate_production_config.py` – fail-fast preflight bez výpisu
  tajných hodnôt,
- `CUTOVER.md`, `CUTOVER_EVIDENCIA.md`, `ROLLBACK.md` a
  `RELEASE_MANIFEST.md` – vykonávacie runbooky a podpisový dôkaz.
- `BACKUP_POLICY.md`, produkčný backup wrapper a systemd timer – denná záloha,
  lokálna retencia, povinný off-site prenos a restore rehearsal.

Produkčný backend image obsahuje iba prevádzkovo potrebný read-only E14 report.
Staging seed/rehearsal a browser E2E launchery sú z produkčného build contextu
explicitne vylúčené.

API, frontend, bot aj worker majú skutočné healthchecky. Bot a worker sa
nepovažujú za zdravé iba preto, že proces existuje: PostgreSQL heartbeat musí
preukázať presne jednu čerstvú inštanciu, očakávaný stav a pri workeri aj
zhodný `PUBLICATION_EXECUTION_MODE`. Produkčný image obsahuje samostatný
neprivilegovaný príkaz `domcek-runtime-healthcheck`, ktorý overuje aj CI.

## Nemenná bezpečnostná hranica

Príprava súborov neoprávňuje zapnúť `PUBLICATION_EXECUTION_MODE=live`, zastaviť
legacy bota, meniť produkčný Discord alebo importovať produkčné údaje. Tieto
kroky sa vykonajú iba v schválenom okne po uzavretí E12.

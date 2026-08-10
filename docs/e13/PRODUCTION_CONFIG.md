# E13 – príprava produkčnej konfigurácie

## 1. Host a DNS

- Linux host s Docker Engine a Compose v2.
- Verejná doména smerujúca A/AAAA záznamom na host.
- Povolené prichádzajúce TCP 80/443 a UDP 443; databázový port sa nezverejňuje.
- Odchádzajúce HTTPS na Discord, Google Calendar a voliteľný intro provider.
- Dostatočný trvalý disk pre PostgreSQL, médiá, Caddy certifikáty a zálohy.

## 2. Súbory na hoste

Z `v2/` vytvoriť lokálne, Gitom ignorované súbory:

```bash
cp .env.production.example .env.production
cp deploy/.env.deploy.example deploy/.env.deploy
chmod 600 .env.production deploy/.env.deploy
```

V deployment env sa použijú iba image referencie s konkrétnym
`@sha256:<64 hex>` digestom. `CARLO_SECRETS_DIR` a `CARLO_THOUGHTS_FILE` musia
byť absolútne cesty. Secret adresár má obsahovať iba pre vlastníka čitateľné:

- `bot-token`,
- `oauth-client-secret`,
- `google-service-account.json`,
- `session-secret` s aspoň 32 náhodnými bajtmi,
- voliteľne `gemini-api-key` po zapnutí príslušnej konfiguračnej premennej.

Databázové heslo musí byť náhodné a v `DATABASE_URL` percent-enkódované. URL
musí smerovať na Compose host `db`; žiadny databázový port sa nepublikuje.

## 3. Povinný preflight

Pred každým nasadením, stále s workerom `paused`:

```bash
python3 scripts/validate_production_config.py \
  --app-env .env.production \
  --deploy-env deploy/.env.deploy \
  --check-files

CARLO_ENV_FILE=.env.production docker compose \
  --env-file .env.production \
  --env-file deploy/.env.deploy \
  -f compose.production.yaml config --quiet
```

Pri `--check-files` validátor overí aj owner-only práva oboch env súborov,
secret adresára a jednotlivých secret súborov. Validátor nikdy nevypisuje
hodnoty secrets. Ak zlyhá jediná kontrola, rollout
sa zastaví. Bez `--allow-live` vyžaduje presne `paused`; s `--allow-live`
vyžaduje presne `live`. Produkcia vždy vyžaduje
`ALLOW_MANUAL_PUBLICATION_IN_SHADOW=false`. `--allow-live` sa nepoužíva pri
príprave ani bežnom reštarte; patrí výhradne ku kroku 16 schváleného cutoveru.

Po štarte musí `docker compose ps` hlásiť `healthy` aj pre `bot` a `worker`.
Ich healthcheck číta iba prevádzkové heartbeat metadáta z PostgreSQL a zlyhá
pri chýbajúcej alebo starej inštancii, duplicite, neočakávanom stave či
nesúlade worker režimu s konfiguráciou kontajnera.

## 4. Externá konfigurácia

- Discord OAuth callback musí byť presne
  `https://HOST/api/v1/auth/discord/callback`.
- Produkčný bot musí byť iba v určenom guild a mať overenú hierarchiu rolí.
- Command sync sa pri bežnom štarte ponechá `false`; vykoná sa iba raz v
  kontrolovanom kroku.
- Google service account dostane iba read-only prístup k vybraným kalendárom.
- Caddy automaticky spravuje TLS; jeho `caddy-data` volume sa zachováva pri
  reštarte aj aktualizácii.

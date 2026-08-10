# Prostredia, konfigurácia a tajomstvá

## 1. Prostredia

| Prostredie | Účel | Discord | Google Calendar | Databáza | Externé správy |
|---|---|---|---|---|---|
| `local` | každodenný vývoj | testovacia aplikácia alebo fake adaptér | fixture/fake, voliteľne testovací kalendár | lokálny PostgreSQL | iba testovacie kanály |
| `test` | automatizované testy | fake adaptér | fake adaptér a uložené fixtures | izolovaný PostgreSQL | žiadne |
| `staging` | integračné a UAT testy | samostatná staging aplikácia a guild | samostatný projekt/service account/kalendár | samostatná staging DB | iba staging server |
| `production` | ostrá prevádzka | produkčná aplikácia a guild | produkčný read-only prístup | produkčná DB | produkčné kanály |

Žiadne neprodukčné prostredie nesmie používať produkčný bot token ani odosielať do produkčného oznamového kanála.

## 2. Kategórie konfigurácie

### 2.1 Bootstrap konfigurácia procesu

Načíta sa pri štarte z prostredia alebo secret store:

| Kľúč | Tajný | Vlastník | Poznámka |
|---|---:|---|---|
| `APP_ENV` | nie | infra | `local`, `test`, `staging`, `production` |
| `APP_BASE_URL` | nie | infra | verejný HTTPS základ webu |
| `LOG_LEVEL` | nie | infra | predvolene `INFO` mimo testu |
| `DATABASE_URL` | áno | infra/DB | obsahuje DB credential |
| `DISCORD_APPLICATION_ID` | nie | Discord owner | stabilné ID aplikácie |
| `DISCORD_BOT_TOKEN` | áno | Discord owner | nikdy nie do prehliadača |
| `DISCORD_OAUTH_CLIENT_ID` | nie | Discord owner | spravidla application ID |
| `DISCORD_OAUTH_CLIENT_SECRET` | áno | Discord owner | iba API proces |
| `DISCORD_OAUTH_REDIRECT_URI` | nie | infra | presná allowlisted URL |
| `SESSION_SECRET` | áno | infra | silná náhodná hodnota |
| `GOOGLE_SERVICE_ACCOUNT_FILE` alebo ekvivalent | áno/nepriamo | Google owner | cesta/mount, nie commitnutý JSON |
| `GOOGLE_CALENDAR_SCOPES` | nie | backend owner | read-only scope |
| `INTRO_GENERATOR_API_KEY` | áno | AI/infra owner | existujúci generátor úvodu |
| `THUMBNAIL_PROXY_BASE_URL` | nie | infra | iba schválená HTTPS služba |
| `ALLOWED_ORIGINS` | nie | infra/security | presný allowlist |
| `TRUSTED_PROXY_COUNT` | nie | infra | podľa reverse proxy |

### 2.2 Serverová produktová konfigurácia

Ukladá sa v `guild_config` alebo súvisiacich tabuľkách, nie ako povinné environment premenné:

| Hodnota | Tajná | Spravuje |
|---|---:|---|
| Discord guild ID | nie | infra/Admin |
| Admin role ID | nie | Admin/infra |
| Team Mod role ID | nie | Admin/infra |
| SDB / FMA role ID | nie | Admin/infra |
| cieľový oznamový channel ID | nie | Admin |
| moderators channel ID | nie | Admin |
| command channel ID | nie | Admin |
| pracovná category ID | nie | Admin |
| archívna category ID | nie | Admin |
| publikačný deň a čas | nie | Admin |
| časové pásmo | nie | systém; `Europe/Bratislava` |
| default Google descriptions | nie | Admin |
| Calendar source IDs a priority | nie | Admin |
| seen/auto/mention emoji | nie | Admin |
| auto-reaction channel IDs | nie | Admin |

### 2.3 Prevádzkové nastavenia

| Hodnota | Tajná | Vlastník |
|---|---:|---|
| maximálny vek Calendar cache | nie | backend/prevádzka |
| retry limity | nie | backend/prevádzka |
| scheduler grace period | nie | backend/prevádzka |
| session lifetime | nie | security/backend |
| backup retention | nie | infra |
| observability DSN/token | áno | infra |

## 3. Vlastníctvo

| Rola vlastníka | Zodpovednosť |
|---|---|
| Discord application owner | aplikácia, bot token, OAuth secret, privileged intents |
| Google project owner | API, service account, credential rotácia |
| Product Admin | guild IDs, rozvrh, obsahové nastavenia |
| Infrastructure owner | hostiteľ, DB credential, TLS, session secret, zálohy |
| Backend maintainer | scope zoznam, retry/cache policy, bezpečná validácia configu |

Jedna osoba môže zastávať viac rolí, zodpovednosť však musí zostať explicitná.

## 4. Bezpečné uloženie

- Lokálne credentials patria do ignorovaného adresára `secrets/` alebo do lokálneho secret managera.
- Produkčné credentials sa mountujú alebo injectujú pri deploymente; nesmú byť súčasťou image.
- Service account JSON sa nesmie premenovať na neškodný názov a commitnúť.
- `.env`, `.env.*`, `secrets/`, `service-account*.json`, `*.pem` a `*.key` sú ignorované.
- Dokumentácia obsahuje iba názvy a vlastníkov tajomstiev, nikdy hodnoty.
- Logovanie bootstrap konfigurácie používa explicitný allowlist netajných hodnôt.
- Rotácia bot tokenu, OAuth secretu, session secretu, DB hesla a Google credentialu musí byť dokumentovaná pred produkčným cutoverom.

## 5. Pravidlá zlyhania pri štarte

- Chýbajúce povinné tajomstvo zastaví príslušný proces s názvom chýbajúcej premennej, nie s jej hodnotou.
- `production` proces odmietne HTTP URL okrem explicitných interných health endpointov.
- `production` odmietne staging guild/calendar identifikátory podľa environment guardu.
- `staging` odmietne produkčný oznamový channel ID, keď bude známy.
- Worker sa nespustí do aktívneho publishing režimu, kým nie je explicitne aktivovaný v databázovej konfigurácii.

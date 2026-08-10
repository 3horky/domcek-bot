# Kontrolná brána E5

## Kritériá

- [x] OAuth login/callback overí state, scope, členstvo, chyby a bezpečný návrat.
- [x] Access token sa nedostane do klienta, session ani auditu.
- [x] Session expirácia, odhlásenie a CSRF fungujú serverovo.
- [x] Aktuálne Discord roly sa mapujú centralizovanou autorizačnou službou.
- [x] Každý implementovaný API use case má priamy server-side capability check.
- [x] Team Mod, SDB / FMA, Admin a bežný člen majú tabuľkové priame API testy.
- [x] API chyby, CORS, cookies, rate limit a bezpečnostné hlavičky majú regresné testy.
- [x] Editorové mutácie vyžadujú verziu a konflikt vracia bezpečný HTTP 409.
- [x] Úspešné aj zamietnuté citlivé operácie sú auditované bez tajomstiev.
- [x] Statické kontroly, testy, migrácie, secret scan a runtime prešli.

## Aktuálny výsledok

**Brána E5: SPLNENÁ.**

## Dôkazy

- Backend: Ruff format/lint, prísny mypy nad 57 zdrojovými súbormi a 114
  úspešných testov; jeden Google live test je štandardne opt-in.
- Frontend: Prettier, ESLint, TypeScript, 2 testy a produkčný Vite build.
- PostgreSQL: E5 downgrade/upgrade cyklus a `alembic check` bez driftu nad
  vývojovou aj testovacou databázou.
- Priamy ASGI/PostgreSQL test overuje draft, redakciu, force inclusion,
  manuálnu udalosť a audit pre všetky štyri typy používateľov.
- Locked Compose runtime: migrátor bez chyby, API a PostgreSQL healthy,
  frontend HTTP 200, worker beží a bot je pripojený iba k staging guild.
- Secret scan, Compose config a `git diff --check` prešli.

Endpointy funkcií, ktorých doménové služby vzniknú až v E7 až E9 (samotné
publikovanie, kanály, archivácia, roly a reakcie), sa pridajú spolu s týmito
službami a použijú rovnakú E5 autentifikačnú, autorizačnú a auditnú hranicu.

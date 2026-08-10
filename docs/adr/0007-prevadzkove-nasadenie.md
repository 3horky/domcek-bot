# ADR-0007: Prevádzkové nasadenie

- **Stav:** prijaté s povinným overením cieľovej infraštruktúry pred produkciou
- **Dátum:** 2026-08-08

## Kontext

Domček Bot 2.0 je riešenie pre jeden Discord server. Potrebuje tri aplikačné procesy, frontend, PostgreSQL, TLS, zálohy a samostatné staging prostredie. Plná kontajnerová orchestrácia typu Kubernetes by bola pre tento rozsah neprimeraná.

Presné parametre existujúceho produkčného hostiteľa zatiaľ nie sú v repozitári zdokumentované.

## Rozhodnutie

Východiskovým produkčným modelom bude Docker Compose alebo ekvivalentné kontajnerové nasadenie na jednom Linux hostiteľovi:

- reverse proxy s HTTPS,
- `api` proces,
- `bot` proces,
- `worker` proces,
- statický frontend,
- PostgreSQL alebo pripojenie na spravovaný PostgreSQL,
- perzistentné volumes iba pre DB a nevyhnutné prevádzkové dáta,
- oddelené tajomstvá mimo image,
- health checks a restart policy,
- off-host databázové zálohy.

Staging použije samostatnú databázu, Discord aplikáciu, Google projekt/credential, kalendár a verejnú OAuth callback URL. Nesmie zdieľať produkčný bot token.

Pred vytvorením produkčného deployment manifestu sa musí overiť:

- operačný systém a architektúra hostiteľa,
- dostupná RAM, CPU a disk,
- DNS a TLS,
- porty a reverse proxy,
- existujúca zálohovacia infraštruktúra,
- miesto a retencia off-host záloh,
- monitoring a log destination.

Ak overenie ukáže, že existujúca infraštruktúra vyžaduje inú formu process managera, nové ADR nahradí iba deployment mechanizmus; rozdelenie aplikačných procesov zostane.

## Dôsledky

Pozitívne:

- jednoduché a opakovateľné nasadenie,
- oddelené reštarty procesov,
- staging podobný produkcii,
- jednoduchšia lokálna reprodukcia.

Negatívne:

- jeden aplikačný hostiteľ je spoločný failure domain,
- treba prevádzkovať alebo platiť PostgreSQL,
- treba zabezpečiť reálne off-host zálohy.

## Zamietnuté alternatívy

- Kubernetes: neprimeraná prevádzková zložitosť.
- Manuálne Python procesy bez deklarácie: slabá reprodukovateľnosť a health management.
- Serverless-only architektúra: nevhodná pre dlhodobé Discord Gateway spojenie.

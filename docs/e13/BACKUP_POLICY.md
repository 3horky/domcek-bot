# Produkčná politika záloh Carla

## Povinný režim pred cutoverom

- Denne o 03:20 `Europe/Bratislava` vznikne PostgreSQL custom dump, archív INFO médií a SHA-256 manifest.
- Lokálne sa uchováva 35 dní. Retencia sa týka iba súborov s presnými Carlo názvami v explicitnom zálohovom adresári.
- Najneskôr do 24 hodín musí samostatný infraštruktúrny proces preniesť celý trojsúborový set do šifrovaného off-site úložiska s verziovaním alebo object lockom. Repo úmyselne neobsahuje credentials ani poskytovateľsky špecifický upload.
- Zlyhanie `carlo-backup.service`, chýbajúci denný manifest alebo zlyhaný off-site prenos musí upozorniť technického vlastníka mimo samotného Carlo runtime.
- Aspoň štvrťročne a pred každým významným databázovým cutoverom sa vykoná obnova do novej izolovanej databázy. Produkčná databáza sa restore rehearsal skriptom nikdy neprepisuje.

## Inštalácia timeru

1. Umiestniť projekt do `/opt/carlo` a vytvoriť používateľa `carlo` s minimálnym prístupom k Dockeru a zálohovému adresáru.
2. Skopírovať `v2/deploy/carlo-backup.env.example` do `/etc/carlo/backup.env`, doplniť cesty a nastaviť práva `600`.
3. Skopírovať `v2/deploy/systemd/carlo-backup.service` a `.timer` do `/etc/systemd/system/`.
4. Spustiť jednorazový backup, overiť manifest a vykonať restore rehearsal do novej databázy.
5. Až potom zapnúť timer a overiť jeho nasledujúci termín a monitoring.

Príklad obnovy konkrétneho dumpu do výhradne novej databázy:

```bash
CARLO_COMPOSE_FILE=/opt/carlo/v2/compose.production.yaml \
CARLO_COMPOSE_ENV_FILE=/etc/carlo/deploy.env \
/opt/carlo/v2/scripts/restore_postgres_rehearsal.sh \
  /var/backups/carlo/carlo-postgres-YYYYMMDDTHHMMSSZ.dump \
  carlo_restore_YYYYMMDD \
  --confirm CREATE:carlo_restore_YYYYMMDD
```

Pred obnovou sa kontroluje SHA-256 manifest. Po porovnaní sa odstraňuje iba
presne pomenovaná skúšobná databáza; dump a produkčná databáza sa nemenia.

## Povinné produkčné vlastníctvo

Pred E13 treba do prevádzkového záznamu doplniť konkrétne mená alebo tímy pre:

- vlastníka dennej zálohy a upozornení,
- vlastníka off-site úložiska a jeho retencie,
- osobu oprávnenú schváliť obnovu,
- dátum poslednej úspešnej restore rehearsal.

Bez týchto údajov a bez reálneho off-site cieľa zostáva E13 brána nesplnená.

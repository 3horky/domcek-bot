# Externé testovacie zdroje E0

Tento checklist sa musí vyplniť reálnymi izolovanými zdrojmi pred uzavretím E0. Identifikátory nie sú tajomstvá, no credentials a tokeny sa do tohto súboru nevkladajú.

## 1. Testovacia Discord aplikácia

### Požadované objekty

- [x] Vytvorená samostatná aplikácia `Domcek Bot v2 Staging`.
- [x] Vytvorený bot user.
- [x] Bot user bol pred E12 UAT používateľsky premenovaný na `Carlo`; názov
  izolovanej Developer Portal aplikácie zostáva `Domcek Bot v2 Staging`.
- [x] Bot token uložený v ignorovanom lokálnom `secrets/` s režimom `600`.
- [x] Nastavený OAuth callback pre lokálny vývoj.
- [ ] Nastavený OAuth callback pre staging HTTPS URL; čaká na doménu v E12 a neblokuje E0.
- [x] Zapnutý požadovaný Server Members Intent; ostatné privileged intents nie sú zapnuté.
- [x] Bot pridaný iba na testovací server; REST vracia presne jeden testovací guild.
- [x] Overená platnosť tokenu a základné Discord REST spojenie; Gateway spojenie čaká na E1.

### Evidencia

| Hodnota | Stav/hodnota |
|---|---|
| Application ID | `1535771583841439765` |
| Test guild ID | `1535774834955391047` |
| Lokálny callback | overený: `http://localhost:8000/api/v1/auth/discord/callback` |
| Staging callback | čaká na staging doménu |
| Credential owner | projektový vlastník; lokálne credentials spravuje používateľ |

Predvolená aj Guild Install konfigurácia obsahujú scope `bot` a `applications.commands` a granulárne permissions `268913744`. `Require OAuth2 Code Grant` je vypnuté.

## 2. Testovací Discord server

Vytvoriť alebo vyhradiť izolovaný server a nasledujúce objekty:

### Roly

- [x] `Admin v2 Test`
- [x] `Team Mod v2 Test`
- [x] `SDB / FMA v2 Test`
- [x] bot rola umiestnená nad rolami, ktoré má spravovať

### Kanály

- [x] `#v2-prikazy`
- [x] `#v2-oznamy`
- [x] `#v2-moderatori`
- [x] `#v2-auto-reaction`

### Kategórie

- [x] `V2 PROJEKTY`
- [x] archívna kategória; API názov `V2-ARCHIV`

### Emoji

- [x] jedno dostupné testovacie vlastné seen emoji s názvom `seen`
- [x] jedno dostupné testovacie vlastné auto-reaction emoji s názvom `autoreaction`
- [ ] overenie Unicode emoji fallbacku patrí do E9 a neblokuje E0

### Evidencia ID

| Objekt | ID |
|---|---|
| Guild | `1535774834955391047` |
| Admin role | `1535774886306390127` |
| Team Mod role | `1535775387307745400` |
| SDB / FMA role | `1535775015285559339` |
| Command channel | `1535774835479674933` |
| Announcements channel | `1535775856281133066` |
| Moderators channel | `1535775897695686717` |
| Auto-reaction channel | `1535775941853184081` |
| Projects category | `1535776011872903208` |
| Archive category | `1535776178097492048` |
| Seen emoji | `1535776335333687316` |
| Auto-reaction emoji | `1535776492699648021` |

## 3. Testovací Google Cloud projekt

- [x] Vytvorený samostatný testovací projekt.
- [x] Zapnuté Google Calendar API.
- [x] Vytvorený service account.
- [x] Credential uložený v ignorovanom lokálnom `secrets/` s režimom `600`.
- [x] Credential owner potvrdený; formálny rotačný runbook sa doplní pred produkčným nasadením.
- [x] Podľa potvrdeného setupu sa nepoužíva domain-wide delegation.
- [x] Potvrdený read-only Calendar scope a efektívna Calendar rola `reader`.

### Evidencia

| Hodnota | Stav/hodnota |
|---|---|
| Project ID | `animatori-504814` |
| Service account e-mail | `domcek-bot-v2-calendar-reader@animatori-504814.iam.gserviceaccount.com` |
| Credential owner | projektový vlastník; lokálny súbor spravuje používateľ |
| Calendar API | zapnuté; OAuth a Calendar resource/list volania úspešné |

## 4. Testovací Google kalendár

- [x] Existujúci vlastnený kalendár potvrdený ako vyhradený a premenovaný na `Domcek Bot v2 Test`.
- [x] Google API vracia kanonický ekvivalent `Europe/Prague`; aplikačná produktová zóna zostáva explicitne `Europe/Bratislava`.
- [x] Oba kalendáre sú zdieľané service accountu s efektívnou rolou `reader`.
- [x] Cez pripojený Google účet vytvorené podporované časované, hraničné, DST a recurring fixtures.
- [x] Konkrétny recurring výskyt bol presunutý pri zachovaní `original_start_time`.
- [x] Konkrétny recurring výskyt bol zrušený.
- [x] Importovaný `fixtures/domcek-v2-test-calendar-remaining.ics` pre celodenné, viacdňové a bezmenné scenáre.
- [x] Vytvorený sekundárny testovací kalendár a importovaný `fixtures/domcek-v2-secondary-calendar.ics`.
- [x] Overené, že service account vidí všetky testovacie udalosti a potrebné detaily.
- [x] Overený full list a reálne stránkovanie na štyroch primary stranách.

### Evidencia

| Hodnota | Stav/hodnota |
|---|---|
| Calendar ID | `3horky.sk_classroom0fb38572@group.calendar.google.com` |
| Calendar názov | `Domcek Bot v2 Test` |
| Access role pripojeného účtu | `owner` |
| Calendar timezone | API canonical value `Europe/Prague`; časové pravidlá ekvivalentné `Europe/Bratislava` |
| Vytvorené základné záznamy | 11 vrátane dvoch recurring masterov |
| Service-account výsledok | 16 aktívnych + 1 zrušený primary; 1 aktívny secondary |
| Secondary Calendar ID | `c_b1c070f7c5f86b6dfbed467349e07a351b49377f172efbfd24bb039cf9ccbed5@group.calendar.google.com` |
| Read-only prístup service accountu | overený; efektívna rola `reader`, OAuth scope `calendar.readonly` |

Podrobný stav a pridelené event ID sú v `GOOGLE_FIXTURE_REPORT.md`.

**Dôležité:** plný `domcek-v2-test-calendar.ics` sa nemá opätovne importovať do aktuálneho kalendára, pretože vznikli by duplicity.

## 5. Testovací generátor úvodu

- [ ] Určený testovací API projekt/kľúč oddelený od produkcie; patrí do E7 a neblokuje izoláciu E0.
- [ ] Nastavený bezpečný quota limit.
- [ ] Overený úspešný request.
- [ ] Pripravený test zlyhania bez kľúča a pri rate limite.

## 6. Pravidlo uzavretia

E0 je označená ako dokončená, pretože:

- vývoj nemusí používať produkčný Discord token/server,
- Calendar integračný test nemusí používať produkčný kalendár,
- staging OAuth nemusí používať produkčný client secret,
- skutočné testovacie ID a vlastníctvo lokálnych credentials sú potvrdené.

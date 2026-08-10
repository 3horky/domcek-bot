# Manuálne kroky potrebné na uzavretie E0

Tento postup obsahuje iba kroky, ktoré nebolo možné vykonať bez pripojeného prehliadača, používateľského potvrdenia alebo dvojfaktorového overenia.

Do repozitára ani do chatu nevkladaj bot token, OAuth client secret, service account JSON, API key, session secret ani databázové heslo.

## Aktuálne overený stav – 9. august 2026

Už je hotové a overené:

- primary kalendár bol premenovaný na `Domcek Bot v2 Test`,
- boli importované zostávajúce celodenné, viacdňové a bezmenné fixtures,
- bol vytvorený `Domcek Bot v2 Test Secondary` a importovaný secondary fixture,
- existuje Google Cloud projekt `animatori-504814`, service account a platný lokálny JSON credential,
- existuje Discord aplikácia `Domcek Bot v2 Staging`; používateľsky viditeľný
  bot účet bol 11. augusta 2026 premenovaný na `Carlo`,
- Discord bot token a OAuth client secret sú uložené lokálne a sú syntakticky platné,
- lokálny OAuth callback a Server Members Intent sú nastavené správne,
- Discord Guild Install je nastavený na `bot` + `applications.commands` s požadovanými granulárnymi oprávneniami,
- lokálne tajomstvá majú sprísnené súborové oprávnenia iba pre vlastníka.

Všetky manuálne kroky potrebné na uzavretie E0 boli dokončené a technicky overené. Predvolená aj Guild Install konfigurácia aplikácie používa scope `bot` a `applications.commands` s granulárnymi oprávneniami bez všeobecného `Administrator`. Bot je na jedinom izolovanom testovacom serveri a service account má read-only prístup k obom testovacím kalendárom.

Ďalší používateľský zásah momentálne nie je potrebný. Tento dokument zostáva ako reprodukovateľný setup návod pre nové prostredie.

## 1. Potvrdenie existujúceho Google kalendára

V pripojenom Google účte existuje vlastnený kalendár:

```text
názov: Domcek Bot v2 Test
calendar ID: 3horky.sk_classroom0fb38572@group.calendar.google.com
```

V kontrolovanom období bol pred zápisom prázdny a už obsahuje podporované `[DOMCEK V2]` fixtures.

### Potrebné rozhodnutie

Potvrď, či môže byť tento kalendár natrvalo vyhradený pre testovanie Domček Bot v2.

Ak áno:

1. Otvor Google Calendar.
2. Vľavo nájdi kalendár `Test`.
3. Otvor jeho **Settings and sharing**.
4. Premenuj ho na `Domcek Bot v2 Test`.
5. Nastav časové pásmo `Europe/Bratislava`.
6. Neimportuj plný `domcek-v2-test-calendar.ics`, pretože vznikli by duplicity.
7. Importuj iba [domcek-v2-test-calendar-remaining.ics](./fixtures/domcek-v2-test-calendar-remaining.ics) do tohto kalendára. Tento import už bol dokončený.

Partial ICS pridá:

- pravú celodennú udalosť,
- viacdňovú celodennú udalosť,
- udalosť bez názvu.

Ak kalendár `Test` nemožno vyhradiť, vytvor nový prázdny `Domcek Bot v2 Test`, importuj doň plný [domcek-v2-test-calendar.ics](./fixtures/domcek-v2-test-calendar.ics) a oznám nové Calendar ID. Connectorom vytvorené udalosti v pôvodnom `Test` kalendári potom odstránime kontrolovaným cleanupom.

## 2. Sekundárny testovací kalendár

1. V Google Calendar zvoľ **Other calendars → Create new calendar**.
2. Názov: `Domcek Bot v2 Test Secondary`.
3. Časové pásmo: `Europe/Bratislava`.
4. V **Settings → Import & export** importuj [domcek-v2-secondary-calendar.ics](./fixtures/domcek-v2-secondary-calendar.ics) do nového kalendára.
5. Skopíruj jeho Calendar ID; nejde o tajomstvo.

Tento kalendár overí deterministické radenie udalostí z viacerých zdrojov s rovnakým časom.

Aktuálne Calendar ID sekundárneho kalendára je:

```text
c_b1c070f7c5f86b6dfbed467349e07a351b49377f172efbfd24bb039cf9ccbed5@group.calendar.google.com
```

## 3. Google Cloud projekt a service account

Oficiálny základný postup je v dokumentácii [Create access credentials](https://developers.google.com/workspace/guides/create-credentials) a [Calendar API scopes](https://developers.google.com/workspace/calendar/api/auth).

### Projekt

1. Otvor Google Cloud Console.
2. Vytvor samostatný projekt, napríklad `domcek-bot-v2-staging`.
3. V **APIs & Services → Library** zapni **Google Calendar API**.

### Service account

1. Otvor **IAM & Admin → Service Accounts**.
2. Vytvor service account `domcek-bot-v2-calendar-reader`.
3. Nepovoľ domain-wide delegation.
4. Pre E0 mu netreba všeobecnú Google Cloud IAM rolu k iným cloudovým zdrojom.
5. Vytvor JSON credential iba pre staging/test.
6. Ulož ho lokálne napríklad ako:

```text
secrets/google-calendar-staging.json
```

Adresár aj typ súboru sú ignorované cez `.gitignore`. Hodnotu neposielaj do chatu.

### Zdieľanie kalendárov

Pre primary aj secondary testovací kalendár:

1. Otvor **Settings and sharing** kalendára.
2. V **Share with specific people or groups** pridaj e-mail service accountu.
3. Nastav iba čítacie oprávnenie umožňujúce vidieť detaily udalostí.
4. Nepovoľ úpravu udalostí ani správu zdieľania.

Po dokončení mi stačí oznámiť:

- Google Cloud Project ID, (animatori-504814)
- service account e-mail, (domcek-bot-v2-calendar-reader@animatori-504814.iam.gserviceaccount.com)
- Calendar ID primary test kalendára, (3horky.sk_classroom0fb38572@group.calendar.google.com)
- Calendar ID secondary test kalendára, (c_b1c070f7c5f86b6dfbed467349e07a351b49377f172efbfd24bb039cf9ccbed5@group.calendar.google.com)
- potvrdenie, že JSON credential je uložený lokálne v `secrets/`. - áno

## 4. Testovacia Discord aplikácia

Použi [Discord Developer Portal](https://discord.com/developers/applications). Discord dokumentuje aplikácie a inštaláciu v [Overview of Discord Apps](https://docs.discord.com/developers/quick-start/overview-of-apps).

### Aplikácia

1. Zvoľ **New Application**.
2. Názov aplikácie: `Domcek Bot v2 Staging`; bot účet sa pred UAT pomenuje
   `Carlo`.
3. Vytvor alebo aktivuj bot user.
4. Bot token ulož lokálne ako tajomstvo; neposielaj ho do chatu.
5. Skopíruj Application ID – to nie je tajomstvo. (1535771583841439765)

### OAuth2

Pridaj lokálnu redirect URL:

```text
http://localhost:8000/api/v1/auth/discord/callback
```

Staging HTTPS redirect URL doplníme po určení staging domény.

OAuth client secret ulož lokálne ako tajomstvo. Do chatu stačí potvrdiť, že existuje.

### Gateway intents

Zapni iba to, čo bude testovacia aplikácia potrebovať:

- **Server Members Intent** pre čerstvé členstvo a roly,
- základné guild/message/reaction udalosti podľa implementácie.

Message Content Intent zatiaľ nezapínaj. Nová verzia nemá prefixové administračné príkazy a plánované všeobecné interakcie nevyžadujú analyzovať obsah serverových správ. Ak E8 preukáže reálnu potrebu, rozhodnutie sa explicitne prehodnotí.

### Navrhované bot oprávnenia na testovacom serveri

- View Channels,
- Send Messages,
- Embed Links,
- Read Message History,
- Add Reactions,
- Use External Emoji/Stickers podľa použitého seen emoji,
- Manage Channels,
- Manage Roles,
- Mention Everyone.

Použitá hodnota Discord permission bitsetu je `268913744`.

Neudeľuj všeobecné `Administrator`, ak konkrétne oprávnenia postačujú.

## 5. Testovací Discord server

V Discord klientovi vytvor samostatný server, napríklad `Domcek Bot v2 Test`.

### Roly

- `Admin v2 Test` - 1535774886306390127
- `Team Mod v2 Test` - 1535775387307745400
- `SDB / FMA v2 Test` - 1535775015285559339

Bot rola musí byť v hierarchii nad rolami, ktoré bude pri integračných testoch prideľovať alebo odoberať.

### Kanály

- `#v2-prikazy` - 1535774835479674933
- `#v2-oznamy` - 1535775856281133066
- `#v2-moderatori` - 1535775897695686717
- `#v2-auto-reaction` - 1535775941853184081

### Kategórie

- `V2 PROJEKTY` - 1535776011872903208
- `V2 ARCHÍV` - 1535776178097492048

### Emoji

- jedno testovacie vlastné seen emoji, :seen:
- jedno testovacie vlastné auto-reaction emoji. :autoreaction:

Nainštaluj staging aplikáciu na tento server. Potom zapni v Discord nastaveniach Developer Mode a skopíruj ID servera, rolí, kanálov a kategórií.

Do chatu môžeš bezpečne poslať tieto ID; neposielaj bot token ani client secret.



## 6. Testovací generátor úvodu

Existujúci produkčný kľúč zatiaľ nerecykluj do stagingu. Vytvor alebo vyhraď samostatný testovací API key s rozumným quota limitom a ulož ho iba lokálne/na staging hostiteľovi.

Do chatu stačí oznámiť:

- ktorý provider/model zostáva použitý,
- že testovací key existuje,
- že má nastavený quota limit.

## 7. Čo mi následne poslať

Bezpečne môžeš poslať:

- Discord Application ID,
- Discord test Guild ID,
- ID troch rolí,
- ID štyroch kanálov,
- ID dvoch kategórií,
- Google Project ID,
- service account e-mail,
- primary a secondary Calendar ID,
- potvrdenie uloženia tajomstiev bez ich hodnôt.

Po prijatí týchto netajných údajov aktualizujem checklist, `STATUS.md`, vyhodnotím bránu E0 a pripravím bezpečný bootstrap konfigurácie pre E1.

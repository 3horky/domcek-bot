# Report overenia staging Discord prostredia

- **Dátum základného overenia:** 9. august 2026
- **Posledné branding overenie:** 11. august 2026
- **Developer Portal aplikácia:** `Domcek Bot v2 Staging`
- **Používateľsky viditeľný bot účet:** `Carlo`
- **Application/Bot ID:** `1535771583841439765`
- **Testovací server:** `Domcek Bot v2 Test`
- **Guild ID:** `1535774834955391047`

## Aplikácia

- bot token je platný a bezpečne uložený v ignorovanom lokálnom `secrets/`,
- `Require OAuth2 Code Grant` je vypnuté,
- lokálny OAuth callback je `http://localhost:8000/api/v1/auth/discord/callback`,
- Server Members Intent je zapnutý,
- Guild Install používa scope `bot` a `applications.commands`,
- permission bitset je `268913744`,
- bot je členom iba jedného izolovaného testovacieho servera.
- oficiálny Discord endpoint pre úpravu vlastného bot účtu premenoval username
  z `Domcek Bot v2 Staging` na `Carlo`; následný REST read vrátil ID
  `1535771583841439765` a username `Carlo`.

## Roly a hierarchia

| Rola | ID | Pozícia pri overení |
|---|---|---:|
| Bot | `1535775350821359697` | 5 |
| Admin v2 Test | `1535774886306390127` | 4 |
| SDB / FMA v2 Test | `1535775015285559339` | 3 |
| Team Mod v2 Test | `1535775387307745400` | 2 |

Bot rola je nad všetkými troma aplikačne spravovanými rolami. Bot má všetky požadované základné oprávnenia a nemá všeobecné oprávnenie `Administrator`.

## Kanály a kategórie

| Účel | Názov overený cez API | ID | Typ |
|---|---|---|---|
| príkazy | `v2-prikazy` | `1535774835479674933` | textový kanál |
| oznamy | `v2-oznamy` | `1535775856281133066` | textový kanál |
| moderátori | `v2-moderatori` | `1535775897695686717` | textový kanál |
| automatické reakcie | `v2-auto-reaction` | `1535775941853184081` | textový kanál |
| pracovná kategória | `V2 PROJEKTY` | `1535776011872903208` | kategória |
| archívna kategória | `V2-ARCHIV` | `1535776178097492048` | kategória |

Efektívne oprávnenia vrátane channel overwrites boli vypočítané pre všetky štyri textové kanály. Bot v každom z nich má príslušné požadované oprávnenia na čítanie, odosielanie, embedy, históriu a podľa účelu aj reakcie, externé emoji a `Mention Everyone`.

## Emoji

| Názov | ID | Dostupnosť |
|---|---|---|
| `seen` | `1535776335333687316` | dostupné |
| `autoreaction` | `1535776492699648021` | dostupné |

## Výsledok

Discord časť kontrolnej brány E0 je splnená. Gateway pripojenie a odoslanie testovacej správy patria do spustiteľnej kostry E1; E0 nevyžaduje spustenie ešte neexistujúceho runtime.

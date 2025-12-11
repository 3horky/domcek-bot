# 📘 Domček Bot - Používateľský a Administrátorský Manuál

Tento dokument slúži ako kompletný sprievodca funkcionalitou bota **Domček Bot**. Je určený pre administrátorov a moderátorov, ktorí potrebujú pochopiť, ako bot funguje, ako spravovať oznamy, kanály a konfiguráciu.

---

## 🤖 Prehľad Funkcionality

Domček Bot je modulárny Discord bot napísaný v jazyku Python (používa knižnicu `discord.py`). Jeho hlavným účelom je:
1.  **Správa oznamov**: Automatizácia vytvárania, formátovania a zverejňovania týždenných oznamov (Info a Eventy).
2.  **Správa kanálov**: Jednoduché vytváranie súkromných kanálov a ich archivácia.
3.  **Interakcia**: Automatické reakcie, odpovede na súkromné správy a dynamický status.
4.  **AI Integrácia**: Využíva Google Gemini na generovanie úvodných textov k oznamom.

Bot beží na modulárnej architektúre (Cogs), čo znamená, že jeho funkcie sú rozdelené do samostatných súborov v priečinku `cogs/`.

---

## 🔐 Roly a Oprávnenia

Bot rozoznáva nasledujúce kľúčové roly (definované v `config.py`):
*   **Admin**: Má prístup ku všetkým príkazom, vrátane konfigurácie bota a okamžitej archivácie.
*   **Team Mod** (Authorized Role): Má prístup k správe oznamov a vytváraniu kanálov.
*   **Oznamy**: Rola, ktorá môže byť spomenutá pri zverejňovaní oznamov.

---

## 📢 Modul: Oznamy (`cogs/announcements.py`)

Tento modul je jadrom bota. Umožňuje spravovať databázu oznamov a generovať z nich formátované správy.

### Príkazy

| Príkaz | Popis | Parametre |
| :--- | :--- | :--- |
| `/pridaj_oznam` | Otvorí formulár (Modal) na pridanie nového oznamu. | `typ`: `event` (akcia) alebo `info` (informácia). |
| `/zoznam_oznamov` | Vypíše zoznam všetkých oznamov v databáze s ich ID a stavom (aktuálne/plánované/expirované). | - |
| `/uprav_oznam` | Otvorí formulár na úpravu existujúceho oznamu podľa jeho ID. | `announcement_id`: ID oznamu. |
| `/vymaz_oznam` | Vymaže oznam z databázy (vyžaduje potvrdenie tlačidlom). | `announcement_id`: ID oznamu. |
| `/preview_oznam` | Zobrazí náhľad, ako bude konkrétny oznam vyzerať po zverejnení (Embed). | `announcement_id`: ID oznamu. |
| `/vygeneruj_oznamy` | Vygeneruje náhľad všetkých oznamov platných pre daný dátum. Používa AI na napísanie úvodu. | `datum` (voliteľné): Dátum zverejnenia (napr. najbližšia sobota). |
| `/uverejni_oznamy_teraz` | **Ostré zverejnenie.** Odošle aktuálne oznamy do kanála `#oznamy` a pridá reakciu pre potvrdenie prečítania. | - |

### Logika Oznamov
*   **Typy**:
    *   **Event**: Má dátum a čas konania. V zozname sa radí podľa dátumu akcie. Má sýtejšiu farbu.
    *   **Info**: Všeobecná informácia (napr. upratovanie). Radí sa na začiatok zoznamu. Má jemnejšiu farbu.
*   **Viditeľnosť**: Každý oznam má dátumy `visible_from` a `visible_to`. Bot zverejní len tie oznamy, ktoré sú v deň zverejnenia "aktívne".
*   **Farby**: Farba Embedu sa mení automaticky podľa aktuálneho mesiaca (napr. december = červená/zlatá, marec = fialová).

### Automatické úlohy
*   **Čistenie databázy**: Každý deň o 01:00 ráno bot skontroluje databázu a vymaže oznamy, ktorým už uplynul dátum `visible_to`.

---

## 📂 Modul: Kanály (`cogs/channels.py`)

Slúži na udržiavanie poriadku na serveri pri vytváraní dočasných alebo projektových kanálov.

### Príkazy

| Príkaz | Popis | Parametre |
| :--- | :--- | :--- |
| `/vytvor_channel` | Vytvorí nový súkromný textový kanál v určenej kategórii. | `emoji`, `name`, `uzivatelia` (zoznam @mentions), `rola` (voliteľné). |
| `/archivuj_channel` | Presunie kanál do archívu a premenuje ho (pridá dátum). | `datum` (napr. 2025_06), `dovod`. |

### Logika Archivácie
*   Ak príkaz spustí **Admin**, kanál sa okamžite premenuje a presunie do kategórie Archív.
*   Ak príkaz spustí **Team Mod** (nie Admin), bot pošle žiadosť do moderátorského kanála. Admin musí žiadosť schváliť reakciou ✅, až potom sa kanál archivuje.

---

## ⚙️ Modul: Admin (`cogs/admin.py`)

Nástroje pre konfiguráciu správania bota.

### Príkazy

| Príkaz | Popis | Oprávnenie |
| :--- | :--- | :--- |
| `/nastav_reaction_emoji` | Zmení emoji, ktorým bot reaguje na správy (globálne). | Admin |
| `/pridaj_autoemoji_channel` | Pridá kanál do zoznamu, kde bot automaticky reaguje na *každú* správu. | Admin |
| `/odober_autoemoji_channel` | Odoberie kanál zo zoznamu auto-reakcií. | Admin |
| `/zoznam_autoemoji_channelov` | Vypíše zoznam sledovaných kanálov. | Admin |
| `!sync` | Synchronizuje slash príkazy s Discord API (klasický prefixový príkaz). | Admin |

---

## 💬 Modul: General (`cogs/general.py`)

Stará sa o "život" bota a interakcie.

### Funkcionalita
*   **Status Bota**: Každých 10 minút bot náhodne vyberie myšlienku zo súboru `thoughts.txt` a nastaví si ju ako status (Activity: Listening to...).
*   **Auto-reakcie**:
    *   Ak je správa v kanáli zo zoznamu `auto_autoemoji_channels`, bot pridá reakciu (nastavenú cez admin príkaz).
    *   Ak niekto označí bota (@DomcekBot), bot pridá reakciu.
*   **Súkromné správy (DM)**: Ak používateľ napíše botovi do DM, bot odpovie náhodnou myšlienkou zo súboru `thoughts.txt`.

---

## 🛠️ Technické Pozadie

### Súborová štruktúra
*   `bot.py`: Spúšťač bota. Načítava premenné prostredia a Cogs.
*   `config.py`: Všetky konštanty (ID kanálov, farby, roly). **Tu upravujte IDčka ak sa zmenia.**
*   `utils.py`: Pomocné funkcie (parsovanie dátumov, triedenie, generovanie embedov).
*   `oznamy_db.py`: Obsluha SQLite databázy (`oznamy.db`).
*   `cogs/`: Priečinok s modulmi.

### Externé Služby
*   **Google Gemini API**: Používa sa v príkaze `/vygeneruj_oznamy` a `/uverejni_oznamy_teraz` na vygenerovanie kreatívneho úvodu k oznamom. Vyžaduje `GEMINI_API_KEY` v `.env`.
*   **Thumbnail Service**: Bot používa externú službu (`http://217.154.124.73:8080/thumbnail`) na generovanie náhľadov pre Info oznamy.

### Inštalácia a Spustenie
1.  Uistite sa, že máte Python 3.11+.
2.  Nainštalujte závislosti: `pip install -r requirements.txt`.
3.  Vytvorte súbor `.env` s `DISCORD_TOKEN` a `GEMINI_API_KEY`.
4.  Spustite bota: `python bot.py`.

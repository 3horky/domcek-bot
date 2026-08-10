# Prevádzkový manuál zlyhaného publikovania

Tento postup je určený Adminovi a technickému vlastníkovi. Cieľom je obnoviť
publikovanie bez duplicity. Pri neistote je bezpečnejšie publikovanie zablokovať
než naslepo zopakovať Discord odoslanie.

## 1. Najprv určte stav

1. Otvorte Carlo → **História publikácií** cez odkaz z moderátorského alertu.
2. Nájdite konkrétny termín a korelačné ID.
3. Skontrolujte Stav systému: bot, worker režim, Calendar zdroje a otvorené
   integračné úlohy.
4. Overte cieľový Discord kanál priamo na Discorde.

Nikdy nezapínajte `live`, nereštartujte oba systémy naraz ani neodosielajte
balík ručne, kým nie je známe, či predchádzajúca správa vznikla.

## 2. Calendar sync zlyhal pred snapshotom

Carlo finálnu synchronizáciu vykonáva bezprostredne pred due snapshotom.

- Predvolený výsledok je blokované publikovanie a moderátorský alert.
- Opravte prístup kalendára, credential, API dostupnosť alebo neplatný sync
  cursor a spustite/počkajte na nový sync.
- Overte, že Calendar zdroj má čerstvý úspech a draft obsahuje posledné zmeny.
- Admin môže vopred zapnúť núdzové použitie cache iba vtedy, keď vedome prijíma
  riziko a cache je ešte v bezpečnom limite. Každé použitie sa audituje.

Voľba núdzovej cache neobíde maximálny bezpečný vek a nesmie sa používať ako
trvalá náhrada funkčnej synchronizácie.

## 3. Discord odpoveď bola neistá

Typický prípad je timeout alebo 5xx po odoslaní requestu, keď Carlo nevie, či
Discord správu vytvoril. Run zostane čiastočný a správa má stav `uncertain`.

1. Na Discorde prejdite cieľový kanál a porovnajte čas aj obsah s nemenným
   snapshotom v Histórii.
2. Ak správa existuje, skopírujte jej číselné ID a zvoľte
   **Prepojiť existujúcu správu**.
3. Ak po dôkladnej kontrole neexistuje, rozbaľte
   **Správa na Discorde nevznikla** a potvrďte opätovné odoslanie tejto časti.
4. Sledujte pokračovanie ďalších správ a výsledný stav runu.

Recovery nikdy nemení uložený obsah snapshotu. Ak si nie ste istí, nevykonajte
ani jednu voľbu a eskalujte korelačné ID technickému vlastníkovi.

## 4. Definitívne zlyhanie alebo vyčerpaný retry

- Skontrolujte bezpečný error code, Discord oprávnenia, cieľový kanál a stav
  Gateway.
- Opravte príčinu; nevytvárajte nový termín ani druhý run.
- Použite existujúci recovery/retry tok konkrétneho runu.
- Po úspechu overte Discord message ID, jediný `@everyone`, správne poradie a
  seen na finálnej správe.

Neúspešný ručný run neoznačí slot ako vybavený. Úspešný run ho vybaví práve
raz. Text Discord odpovede pri čiastočnom stave nie je dôkaz úspechu; autoritou
je uložený stav a skutočný kanál.

## 5. Zlyhala iba seen reakcia

Ak boli všetky textové správy odoslané, chyba seen je warning, nie zlyhanie
publikácie. História ju ukáže pri konkrétnej správe.

- Overte emoji, `add_reactions` a dostupnosť serverového emoji.
- V Nastaveniach použite test reakcie v cieľovom kanáli.
- Chýbajúcu seen reakciu riešte samostatne; neopakujte textovú publikáciu.

## 6. Worker alebo bot sa reštartoval

- Bot a worker majú samostatné heartbeat-y; skontrolujte ich čerstvosť.
- Worker pri štarte obnoví iba bezpečné časti a neisté účinky nechá na Admina.
- Dve worker inštancie používajú DB lock; nezvyšujte počet inštancií ako pokus
  „urýchliť“ recovery.
- Pri starom zmeškanom slote mimo grace period Carlo bez Admin rozhodnutia
  nepublikuje.

## 7. Moderátorský alert neprišiel

Skontrolujte nakonfigurovaný moderátorský textový kanál, oprávnenia bota a
zapnutú kategóriu alertu. Chyba alertu nesmie byť jediným zdrojom pravdy:
História a Stav systému zostávajú autoritatívne.

## 8. Kedy vykonať rollback

Počas cutoveru použite `docs/e13/ROLLBACK.md`. Rollback je povinný najmä pri
riziku duplicity, nesprávnom migračnom obsahu, nefunkčnom OAuth, chybnom
termíne, nefunkčnom Calendar synce bez bezpečnej cache alebo nedostatočných
Discord oprávneniach.

Rollback znamená vypnúť nový worker a bot, zachovať novú DB iba na diagnostiku
a obnoviť legacy z explicitnej zálohy. Nikdy nemažte diagnostickú DB ani
incident pred zaznamenaním dôkazu.

## 9. Povinný záznam incidentu

Zaznamenajte:

- guild a plánovaný termín,
- run ID a korelačné ID,
- prvý pozorovaný symptóm a časy,
- ktoré Discord správy skutočne existovali,
- recovery rozhodnutie a osobu, ktorá ho vykonala,
- príčinu, nápravu a potrebu nového testu.

Do ticketu ani chatu nevkladajte bot token, OAuth secret, session cookie,
Google private key ani celý surový log s neovereným obsahom.

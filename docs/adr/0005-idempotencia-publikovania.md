# ADR-0005: Idempotencia a zotavenie publikovania

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Publikovanie pozostáva z databázového snapshotu, viacerých Discord správ a finálnej reakcie. Databázu a Discord nemožno zahrnúť do jednej spoločnej transakcie. Pád medzi odoslaním správy a uložením jej ID môže vytvoriť neistý stav.

Ručný trigger zároveň musí vybaviť práve jeden najbližší termín a zabrániť neskoršej automatickej duplicite.

## Rozhodnutie

Idempotencia sa implementuje kombináciou:

- stabilného identifikátora publikačného termínu,
- unikátneho DB obmedzenia `(guild_id, scheduled_for)`,
- databázového/advisory locku pre termín,
- explicitného stavového automatu,
- nemenného snapshotu pred externým odoslaním,
- samostatného záznamu pre každý message part,
- deterministického idempotency key a Discord nonce,
- uloženia Discord message ID po každej časti,
- recovery procesu pre rozpracované behy.

## Povinné pravidlá

- Composer nesmie počas jedného runu znovu načítať živé editovateľné údaje po vytvorení snapshotu.
- Dve požiadavky na ten istý termín musia skončiť pri tom istom run zázname.
- Úspešný ručný run označí konkrétny termín ako vybavený.
- Neúspešný ručný run termín nepreskočí.
- Worker po reštarte pokračuje iba pri známej bezpečnej ďalšej časti.
- Pri neistom externom účinku sa automaticky neposiela možná duplicita; vznikne incident pre reconcile.
- Seen emoji je doplnkový účinok a jeho zlyhanie nemení úspešné textové publikovanie na neúspešné.

## Dôsledky

Pozitívne:

- výrazne nižšie riziko duplicít,
- audit každej odoslanej časti,
- kontrolovateľný partial failure,
- rovnaké správanie manuálneho a automatického triggera.

Negatívne:

- viac stavov a databázových záznamov,
- nemožno matematicky garantovať exactly-once účinok medzi DB a cudzím API,
- treba administrátorský reconcile flow pre vzácny neistý stav.

## Zamietnuté alternatívy

- Jeden boolean `published`: nedostatočný pre viac správ a partial failure.
- Automaticky zmazať a poslať celý balík znova: riziko viditeľných duplicít a pingov.
- Spoliehať sa iba na časovač jednej inštancie: neodolné voči reconnectu a súbehu.

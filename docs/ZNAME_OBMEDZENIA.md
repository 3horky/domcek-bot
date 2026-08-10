# Známe obmedzenia Carla

## Otvorené predprodukčné dôkazy

- Lokálna implementácia E0–E11 a shadow runtime sú dokončené, ale aktuálny
  strom ešte neprešiel vzdialeným CI po schválenom commitnutí a pushnutí.
- Produkčne podobné HTTPS staging prostredie a podpísaný rolový/responzívny
  browser UAT nie sú dokončené. Bez nich sa E12 neuzavrie.
- Dva read-only rehearsal sloty sú zdokumentované, ale musia byť výslovne
  prijaté ako ekvivalent dvoch reálnych týždenných shadow slotov, alebo treba
  počkať na skutočné sloty.
- Produkčný cutover, tri stabilizačné cykly a vyradenie legacy neprebehli.
  `PUBLICATION_EXECUTION_MODE=live` preto zostáva zakázaný.
- Produkčný systemd backup timer sa musí reálne overiť na cieľovom Linux hoste;
  vývojový macOS host nemá `systemd-analyze`.

## Produktové hranice prvej verzie

- Carlo spravuje jeden konkrétny Discord server na deployment. Doménové dáta sú
  guild-scoped, nejde však o samoobslužný komerčný multitenant produkt.
- Google Calendar integrácia je read-only. Web nevytvára ani neupravuje Google
  udalosti.
- Podporované aplikačné roly sú Team Mod, SDB / FMA a Admin. Všeobecný editor
  ľubovoľných Discord rolí alebo permission overwrites nie je súčasťou prvej
  verzie.
- SDB / FMA sa používa na autorizáciu ručného publikovania, ale web jeho rolu
  všeobecne nespravuje.
- Carlo neposkytuje verejný portál pre bežných členov ani natívnu mobilnú
  aplikáciu; web je responzívna administrácia.
- Jazykový model nerozhoduje o zaradení udalostí. Generuje iba úvod; pri
  chýbajúcom alebo chybnom credentiale sa použije deterministický slovenský
  fallback.

## Prevádzkové hranice

- Discord a Google sú externé služby. Pri neistom Discord účinku Carlo zámerne
  zastaví automatické pokračovanie a vyžiada Admin reconcile.
- Núdzové použitie Calendar cache je predvolene vypnuté a aj po zapnutí má
  maximálnu bezpečnú hranicu. Nie je to offline režim bez časového limitu.
- INFO médiá musia mať v produkcii verejnú HTTPS základnú URL dostupnú
  Discordu. Lokálna URL nie je použiteľná pre verejný thumbnail.
- Automatická záloha sama osebe nie je off-site ochrana. Produkcia vyžaduje
  šifrovaný prenos, externý monitoring, menovaných vlastníkov a pravidelnú
  restore rehearsal.
- Známe nezlyhávajúce testovacie upozornenie pochádza z prechodu
  Starlette/FastAPI test klienta z `httpx` na budúci `httpx2`; runtime ani
  výsledok testov neovplyvňuje.
- Testovacie Google kalendáre hlásia kanonické pásmo `Europe/Prague`, ktoré má
  rovnaké pravidlá ako Bratislava. Produktová konfigurácia napriek tomu
  používa explicitné `Europe/Bratislava`.

Aktuálny zoznam blokátorov a najbližší krok je vždy v koreňovom `STATUS.md`.

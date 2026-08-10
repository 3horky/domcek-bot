# Kontrolná brána E0

## Kritérium z implementačného plánu

Etapa E0 je hotová, keď vývoj a testovanie nemusia používať produkčný Discord server, produkčný bot token ani produkčný Google kalendár.

## Kontrolný zoznam

### Lokálne a dokumentačné výstupy

- [x] Overený pracovný strom a legacy hranica.
- [x] Nová verzia izolovaná pod `v2/`.
- [x] ADR-0001: modulárny monolit a procesy.
- [x] ADR-0002: PostgreSQL.
- [x] ADR-0003: Discord OAuth sessions.
- [x] ADR-0004: Google autentifikácia.
- [x] ADR-0005: idempotencia publikovania.
- [x] ADR-0006: frontend.
- [x] ADR-0007: deployment model.
- [x] Matica prostredí, konfigurácie, tajomstiev a vlastníkov.
- [x] Provider-neutrálne Calendar fixtures.
- [x] ICS import pre testovací kalendár.
- [x] Checklist externých zdrojov.
- [x] Rozšírená ochrana credentials v `.gitignore`.

### Externé izolované zdroje

- [x] Testovacia Discord aplikácia, bot user a bezpečne uložený platný bot token.
- [x] Testovací Discord server overený cez API; Guild ID `1535774834955391047`.
- [x] Testovacie roly Admin, Team Mod a SDB / FMA sú vytvorené a ich ID zaznamenané.
- [x] Testovacie kanály, kategórie, emoji, ich ID a efektívne bot oprávnenia sú overené cez API.
- [x] Testovací Google Cloud projekt.
- [x] Testovací service account a bezpečne uložený platný credential.
- [x] Existujúci kalendár potvrdený/premenovaný ako vyhradený testovací kalendár.
- [x] Podporované fixture udalosti vytvorené a overené cez používateľské Google pripojenie.
- [x] Presunutý a zrušený recurring výskyt vytvorený a overený.
- [x] Doplnené zostávajúce celodenné/viacdňové/bezmenné fixtures cez partial ICS.
- [x] Vytvorený sekundárny kalendár a jeho priority fixture.
- [x] Oba testovacie Google kalendáre zdieľané service accountu s rolou `reader`; scope je `calendar.readonly`.
- [ ] Testovací prístup ku generátoru úvodu je presunutý do E7 a neblokuje E0.
- [x] Potvrdené vlastníctvo externých credentials; rotačný runbook zostáva predprodukčnou úlohou.

## Aktuálny výsledok

**Brána E0: SPLNENÁ – vývoj a testovanie majú samostatnú Discord aplikáciu/server, samostatný Google projekt/service account a dva izolované testovacie kalendáre s kompletnými fixtures.**

Service account s efektívnou rolou `reader` a scope `calendar.readonly` prečítal 16 aktívnych a 1 zrušený primary výskyt a 1 secondary výskyt. Overené boli popisy, `STOP CARLO`, celodenné udalosti, presunutý recurring výskyt aj stránkovanie. Discord API potvrdilo jediný testovací guild, všetky objekty a emoji, správnu hierarchiu bot roly, potrebné oprávnenia v štyroch kanáloch a absenciu všeobecného `Administrator`.

Rozhodnutie: etapa E0 je uzavretá a možno začať E1. Staging HTTPS callback, testovací intro-generator credential a Unicode emoji fallback zostávajú explicitne evidované v etapách, v ktorých sa prvýkrát používajú.

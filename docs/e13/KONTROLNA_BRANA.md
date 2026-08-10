# Kontrolná brána E13

## Stav: BLOKOVANÁ PRED CUTOVEROM

Prípravná implementácia je hotová, ale E13 nemožno vykonať pred uzavretím E12
a poskytnutím produkčnej infraštruktúry a schválenia.

- [x] produkčný Compose model bez source bind mountov,
- [x] statický frontend a HTTPS reverse proxy,
- [x] fail-safe `paused` konfigurácia a preflight validátor,
- [x] health checks vrátane DB-backed bot/worker freshness, singleton a mode
  kontroly, perzistentné DB/médiá/certifikáty a read-only secrets,
- [x] release, cutover a rollback runbook,
- [x] kroková cutover evidencia s operátorom, časom, výsledkom a rollback
  rozhodnutím,
- [ ] E12 kontrolná brána uzavretá,
- [ ] produkčný host, DNS, secret files a nemenné image digesty,
- [ ] vyplnený a schválený release manifest,
- [ ] finálny backup a úspešná restore rehearsal,
- [ ] explicitne schválené cutover okno,
- [ ] vykonaný import, OAuth/role/draft/health overenie,
- [ ] worker aktivovaný na `live` až po Admin potvrdení,
- [ ] jeden úspešný kontrolovaný produkčný draft.

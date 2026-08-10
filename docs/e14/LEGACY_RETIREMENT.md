# E14 – vyradenie starej verzie

Vykonať až po troch úspešných cykloch a spoločnom podpise Admina a technického
vlastníka.

- [ ] E14 report uvádza tri cykly bez anomálie.
- [ ] Nie je otvorený publication/reconcile incident.
- [ ] Nový backup, obnova a monitoring majú určeného vlastníka.
- [ ] Legacy finálna SQLite, konfigurácia a release sú archivované read-only.
- [ ] Archív má SHA-256 manifest, dátum, vlastníka a retenčný termín.
- [ ] Legacy autostart/service/container je deaktivovaný, nie bez dôkazu zmazaný.
- [ ] Produkčné legacy secrets sú odvolané alebo bezpečne odstránené.
- [ ] Discord token starej aplikácie je rotovaný/odvolaný podľa rozhodnutia.
- [ ] Staré Google credentials a prístupy sú odobraté.
- [ ] Prevádzkový a používateľský manuál odkazuje už iba na Carla.
- [ ] Migračné reporty a rollback záloha ostávajú podľa retenčnej politiky.

Materiálne zálohy sa nemažú bez samostatne schváleného retenčného rozhodnutia.
Vyradenie znamená najprv znemožniť štart a odvolať prístupy, až potom riešiť
neskoršie bezpečné odstránenie.

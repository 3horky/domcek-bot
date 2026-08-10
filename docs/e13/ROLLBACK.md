# E13 – rollback runbook

## Okamžité spúšťače

- chybný alebo neúplný import aktívnych oznamov,
- Admin sa nevie prihlásiť alebo dostane nesprávnu rolu,
- nesprávny najbližší slot, okno alebo časové pásmo,
- nepoužiteľný Calendar sync/cache,
- chýbajúce Discord oprávnenia alebo riziko duplicitného odoslania,
- nejasný čiastočný publikačný účinok.

## Postup

1. Nastaviť Carlo worker na `paused` a zastaviť jeho kontajner.
2. Zastaviť Carlo bot; API/web možno ponechať iba read-only na diagnostiku.
3. Nemeniť ani nemažte PostgreSQL alebo médiá; vytvoriť incidentný backup.
4. Zaznamenať všetky Carlo message ID, runy, sloty a externé účinky.
5. Rozhodnúť, či už Carlo niečo odoslalo. Pri neistote nič automaticky
   neopakovať a použiť reconcile incident postup.
6. Obnoviť legacy SQLite/config z presne označenej finálnej zálohy.
7. Spustiť jednu legacy inštanciu a potvrdiť jej najbližší termín pred zapnutím
   schedulera.
8. Až po Admin potvrdení obnoviť legacy scheduler.
9. Zdokumentovať incident, rozdiely vzniknuté v okne a rozhodnutie o ďalšom
   pokuse. Nový pokus musí mať nový release manifest, ak sa zmení kód/image.

Rollback nesmie vymazať dôkaz ani spustiť oba schedulery naraz.

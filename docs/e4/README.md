# Etapa E4 – kompozícia publikačného balíka

E4 vytvára jediný čistý a deterministický zobrazovací model pre webový editor,
Discord preview aj neskoršie publikovanie. Composer nemá sieťové ani databázové
vedľajšie účinky; pracuje iba s explicitným vstupným snapshotom.

## Dokumenty

- [Invarianty composeru](./INVARIANTY_COMPOSERU.md)
- [Kontrolná brána E4](./KONTROLNA_BRANA.md)

## Hranica etapy

E4 vypočíta termín, 14-dňové okno, finálne hodnoty, poradie a plán
Discord správ. Neukladá publication snapshot a nič neposiela do Discordu; tieto
externé účinky patria do E7.

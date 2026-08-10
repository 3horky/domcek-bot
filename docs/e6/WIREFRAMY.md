# Responzívne wireframy E6

## Desktop – prehľad

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Carlo               Správa oznamov                               [Používateľ]│
├───────────────┬────────────────────────────────────────────────────────────┤
│ Prehľad       │ Najbližší balík                              [Otvoriť editor]│
│ Redakčný pult │ ┌────────────────────────────────────────────────────────┐ │
│ Audit         │ │ Pondelok 20:00 · obdobie 14 dní · pripravené           │ │
│ Stav          │ └────────────────────────────────────────────────────────┘ │
│               │ [12 udalostí] [2 INFO] [1 vylúčená]                       │
│               │                                                            │
│               │ Čo si vyžaduje pozornosť                                  │
│               │ ┌───────────────────┐ ┌──────────────────────────────────┐ │
│               │ │ STOP CARLO        │ │ Posledná synchronizácia         │ │
│               │ │ 1 udalosť         │ │ pred 4 minútami                 │ │
│               │ └───────────────────┘ └──────────────────────────────────┘ │
└───────────────┴────────────────────────────────────────────────────────────┘
```

## Desktop – Redakčný pult

```text
┌───────────────┬─────────────────┬──────────────────────┬───────────────────┐
│ Navigácia     │ Zdroje          │ Spoločný obsah       │ Discord kanál      │
│               │ Najbližší   12  │ Google · St 18:00    │ # oznamy            │
│ Prehľad       │ Google       9  │ Otvorený Domček      │ Carlo  APP          │
│ Redakčný pult │ Manuálne     2  │ popis · stav [Upraviť]│ @everyone Ahojte…  │
│ Audit         │ INFO         1  │                      │ ┌ embed ─────────┐  │
│ Stav          │ Vylúčené     1  │ Manuálne · 17.–23.8. │ │ streda · titul │  │
│               │                 │ Letný tábor [Upraviť]│ └────────────────┘  │
│               │ + Manuálna      │                      │ ✓ 1                │
│               │ + INFO          │                      │ Správa pre #oznamy │
└───────────────┴─────────────────┴──────────────────────┴───────────────────┘
```

## Mobil – editor

```text
┌─────────────────────────────┐
│ Carlo             [profil]   │
│ Redakčný pult                │
│ Po 10. 8. · 20:00            │
├─────────────────────────────┤
│ [Prehľad 12] [Google 9]      │
│ [Manuálne 2] [INFO 1]        │
│                              │
│ ┌─────────────────────────┐ │
│ │ Google · 18:00–19:00    │ │
│ │ Udalosť · publikovaná   │ │
│ │ [Upraviť]               │ │
│ └─────────────────────────┘ │
│                              │
│ Discord náhľad               │
│ ┌─────────────────────────┐ │
│ │ # oznamy · Carlo APP    │ │
│ │ @everyone · embedy · ✓  │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│ Prehľad   Oznamy  Audit Stav│
└─────────────────────────────┘
```

Na šírke pod 1240 px sa Discord náhľad presunie pod spoločný zoznam, nie do
alternatívnej záložky. Pod 720 px sú zdrojové filtre v horizontálnom páse,
bočná aplikáčná navigácia sa zmení na spodnú a všetky primárne akcie zostávajú
dotykovo použiteľné.

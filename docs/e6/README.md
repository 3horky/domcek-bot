# Etapa E6 – webová administrácia

E6 premieňa bezpečné E5 API na každodenné pracovné rozhranie pre Admina a
Team Moda. Všetky rozhodnutia o oprávnení zostávajú na serveri; frontend iba
zobrazuje capability a zrozumiteľne reaguje na odmietnutie alebo konflikt.

## Princípy

- prvá obrazovka odpovedá na otázku „čo sa zverejní najbližšie a kedy?“,
- automaticky pripravený obsah je použiteľný bez povinnej redakcie,
- úprava konkrétneho výskytu a série sú dve vedomé operácie,
- Google, manuálne a INFO položky sa spravujú v jednom Redakčnom pulte,
- Discord preview Carla používa ten istý draft ako neskorší publisher a je
  dostupný spolu s obsahom, nie v alternatívnej záložke,
- mobilné zobrazenie používa karty a spodnú navigáciu, nie zmenšené tabuľky,
- každý asynchrónny blok má loading, empty, error a retry stav,
- konflikt verzie nikdy potichu neprepíše cudziu zmenu,
- klávesnica, čítačka obrazovky, viditeľný focus a dotykové ciele sú povinné.

## Dokumenty

- [Informačná architektúra a route mapa](./INFORMACNA_ARCHITEKTURA.md)
- [Wireframy](./WIREFRAMY.md)
- [Dizajnový systém](./DIZAJNOVY_SYSTEM.md)
- [Kontrolná brána](./KONTROLNA_BRANA.md)

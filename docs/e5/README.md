# Etapa E5 – autentifikácia, autorizácia a webové API

E5 vytvára bezpečnú HTTP hranicu nad existujúcimi aplikačnými službami. Web
nepozná Discord ani databázové tajomstvá a nikdy sám nerozhoduje o oprávnení.

## Dokumenty

- [Bezpečnostné invarianty](./BEZPECNOSTNE_INVARIANTY.md)
- [Autorizačná matica](./AUTORIZACNA_MATICA.md)
- [Kontrolná brána E5](./KONTROLNA_BRANA.md)

## Rozhodnutie OAuth

Prihlásenie používa Discord Authorization Code flow so scope `identify` a
`guilds.members.read`. Access token sa použije iba počas callbacku na získanie
identity a členstva a neukladá sa do prehliadača ani databázy. Aktuálne roly sa
pri chránených požiadavkách overujú serverovo cez bot API.

## Implementovaný rozsah API

- Discord login/callback, aktuálna session a odhlásenie,
- najbližší kanonický publikačný draft,
- verzovaná úprava konkrétneho výskytu a série od zvoleného výskytu,
- zoznam, vytvorenie, úprava a mäkké odstránenie manuálnych udalostí,
- zoznam, vytvorenie, úprava a mäkké odstránenie INFO oznamov,
- rolovo filtrovaný audit,
- jednotné CSRF, CORS, rate limit, bezpečnostné hlavičky a problem details.

Rozhrania neskorších doménových operácií sa pridajú v E7 až E9, keď vzniknú ich
aplikačné služby; neexistujú tu nefunkčné stub endpointy.

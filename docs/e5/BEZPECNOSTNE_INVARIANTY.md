# Bezpečnostné invarianty E5

- OAuth `state` je náhodný, krátko platný, podpísaný a porovnaný s HttpOnly
  cookie; callback URL je presná konfigurovaná hodnota.
- Návratová cesta môže byť iba lokálna absolútna cesta bez schémy, hostiteľa,
  spätných lomiek alebo riadiacich znakov.
- Discord access token, refresh token, bot token a OAuth client secret sa nikdy
  neposielajú frontendu, nevkladajú do session cookie, auditu ani logov.
- Session cookie obsahuje náhodný nepriehľadný token; databáza uchováva iba jeho
  HMAC hash. Odhlásenie a expirácia session serverovo zneplatnia.
- Meniaca požiadavka musí mať platnú session, rovnaký CSRF token v čitateľnej
  cookie a hlavičke a zhodný HMAC hash v session zázname.
- Oprávnenie sa vyhodnocuje v aplikačnom use case podľa aktuálnych Discord role
  ID. Skryté tlačidlo alebo route skupina nie sú autorizačnou hranicou.
- Chýbajúce členstvo, rola alebo konfigurácia oprávnenie nikdy nerozšíria.
- CORS používa presný allowlist, credentials a len explicitné metódy/hlavičky.
- Odpovede pridávajú CSP, `nosniff`, frame deny a referrer policy; celé
  administrátorské `/api/v1/` používa `Cache-Control: no-store`.
- Používateľská chyba má stabilný problem detail bez tracebacku a tajomstiev.
- OAuth vstupy a všetky meniace API požiadavky majú konfigurovateľný časový
  rate limit. Kľúč prihlásenia vychádza zo sieťového klienta; po prihlásení sa
  používa iba jednosmerný odtlačok session tokenu. Klientom dodané forwarding
  hlavičky limiter sám neinterpretuje.
- Limiter je lokálny pre jeden API proces, čo zodpovedá aktuálnemu deployment
  modelu. Pred horizontálnym škálovaním API sa musí nahradiť zdieľaným úložiskom
  alebo ekvivalentným limitom na dôveryhodnom reverse proxy.

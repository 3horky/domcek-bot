# ADR-0003: Discord OAuth a serverové relácie

- **Stav:** prijaté
- **Dátum:** 2026-08-08

## Kontext

Webová administrácia musí identifikovať používateľa, overiť členstvo na konkrétnom Discord serveri a pri každej operácii uplatniť roly Admin, Team Mod a SDB / FMA.

Frontend nesmie vlastniť Discord bot token ani rozhodovať o oprávnení iba podľa údajov uložených v prehliadači.

## Rozhodnutie

Prihlásenie použije Discord OAuth2 Authorization Code flow.

Základné pravidlá:

- OAuth scopes budú minimálne potrebné pre identitu a overenie serverového kontextu.
- Callback overí jednorazový `state` a presný allowlist návratových URL.
- Backend vytvorí náhodnú nepriehľadnú serverovú session.
- Prehliadač dostane iba Secure, HttpOnly a primerane SameSite session cookie.
- OAuth access token ani bot token sa neposiela klientskemu JavaScriptu.
- Aktuálne roly člena sa pre citlivú operáciu overia cez Discord bot API alebo krátko platnú serverovú cache.
- Každý use case vykoná vlastnú autorizačnú kontrolu.
- CSRF ochrana sa vyžaduje pre všetky meniace HTTP operácie.
- Odhlásenie session serverovo zneplatní.

Ak bude potrebné OAuth token uchovať, uloží sa šifrovane a s minimálnou retenciou. Ak nie je potrebný po vytvorení identity/session, nebude sa dlhodobo ukladať.

## Autorizačné zásady

- Roly sa identifikujú stabilným Discord ID.
- Frontend môže skryť nepovolenú akciu, ale nie je bezpečnostnou hranicou.
- SDB / FMA môže zobraziť draft a ručne publikovať, nie všeobecne administrovať.
- Team Mod nemôže ručne publikovať iba na základe tejto role.
- Zmena rolí počas aktívnej relácie sa musí prejaviť bez nutnosti nového dlhodobého prihlásenia.

## Dôsledky

Pozitívne:

- používateľ nepotrebuje nové heslo,
- roly zostávajú zdrojom oprávnení,
- tajomstvá zostávajú na serveri.

Negatívne:

- treba spravovať sessions, CSRF a OAuth callbacky,
- Discord nedostupnosť môže ovplyvniť čerstvé overenie role,
- staging a produkcia potrebujú oddelené callback URL.

## Zamietnuté alternatívy

- Lokálne používateľské mená a heslá: ďalší citlivý identity systém.
- JWT v `localStorage`: väčší dopad XSS a komplikovanejšie odvolanie.
- Oprávnenie iba vo frontende: bezpečnostne neakceptovateľné.

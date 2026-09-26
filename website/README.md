# linkgrp.nl, de website van LINK.

Een statische website zonder build-stap en zonder libraries: HTML, CSS en één JS-bestand. Je kunt hem uploaden naar elke hosting en hij werkt meteen. Openen kan ook lokaal, door `index.html` in je browser te openen.

## Hoe alles samenhangt

```
data/site.js  ──►  assets/js/main.js  ──►  alle pagina's
(één waarheid)      (leest en rendert)       header, footer, oprichter, foto's,
                                             werkmethode, contactgegevens,
                                             formulier
```

| Wat | Waar aanpassen | Waar het verschijnt |
|---|---|---|
| E-mail, telefoon | `data/site.js > contact` | header (mobiel), footer, contactpagina, CTA's, JSON-LD* |
| Menu | `data/site.js > nav` | header, mobiel menu, footer |
| Oprichter + quote | `data/site.js > founder` | home, ons verhaal, contact |
| Alle foto's | `data/site.js > photos` | elke pagina |
| Zo werkt het: 4 fases met foto, glaskaartjes en "wat je krijgt" | `data/site.js > method` (+ `pilotLabel`) | home, diensten |
| Voorbeelden in de hero-kaart | `data/site.js > liveCard` | home |
| Partnerportaal-knop | `data/site.js > contact.portalUrl` | header, mobiel menu, footer |
| Contactformulier-koppeling | `data/site.js > contact.form` | contactpagina |

\* Het JSON-LD-blok in `index.html` (voor Google) staat statisch in de HTML. Pas het telefoonnummer daar ook aan als het verandert.

**Wat bewust niet op de site staat.** De werkmethode staat er alleen als traject (kick-off, eerste belmoment, eerste meeting, structurele stroom). Hoe LINK. dat doet, en ook de resultaatcodes en het rapportageformat, blijft voor de kennismaking. Die staan dus ook niet in de code, zodat niemand ze uit de broncode kan halen.

## Bronnen

- Huisstijl: Drive > Website > *Huisstijl* (zwart `#000000`, blauw `#38b6ff`, Open Sans)
- Teksten: Drive > Website > *Website Teksten Opzet*
- Logo's: Drive > Website > *LINK. LOGO's.zip*, omgezet naar `assets/img/logo-zwart.png` en `logo-wit.png`
- Briefing: *Website Onboarding Vragen* (modern en hip, maar met rust, "geen kermis", doel: inbound leads)

## Nog in te vullen voor livegang

1. **Foto's** staan in `assets/img/hens/` (uit Drive > Website > wetransfer-map, bijgesneden, gecomprimeerd en zonder EXIF/GPS). Welke foto waar staat, regel je in `data/site.js > photos`. Een lege `src` laat het fotovak netjes verdwijnen. Op de portaalfoto zijn namen, notities, URL en bladwijzers onleesbaar gemaakt.
2. **Partnerportaal-URL** in `contact.portalUrl`. Zolang dit veld leeg is, blijft de knop verborgen.
3. **Contactformulier.** Zonder koppeling opent het formulier een ingevulde e-mail naar info@linkgrp.nl. Wil je het formulier aan een Google Form koppelen (zoals besproken in de website-evaluatie), vul dan `contact.form.endpoint` in met de `formResponse`-URL en zet bij `fields` de `entry.xxxx`-ID's.
4. **Controleer** e-mail en telefoonnummer. Die komen uit de *Website Teksten Opzet*.

## Techniek

- **Snel:** geen frameworks, fonts zelf gehost (`assets/fonts`, alleen Latin), afbeeldingen klein.
- **AVG:** geen Google Fonts-verzoeken, geen trackers en geen cookies. Voeg je later Analytics toe, zet er dan ook een cookiemelding bij.
- **Toegankelijk:** semantische HTML, skip-link, focusstijlen, labels bij formuliervelden. `prefers-reduced-motion` zet alle animaties uit.
- **SEO:** unieke titels en beschrijvingen per pagina, canonical-tags, Open Graph, `sitemap.xml`, `robots.txt`, Organization-schema.
- **Responsive:** getest op 360, 390, 768, 1024 en 1440 px zonder horizontaal scrollen.

## Structuur

```
website/
├── index.html          Home
├── diensten.html       Telefonische acquisitie + business development
├── ons-verhaal.html    Hens, waarom LINK. bestaat
├── waarom-link.html    Transparantie · Eerlijkheid · Lange termijn
├── contact.html        Formulier + gegevens
├── 404.html
├── data/site.js        ← centrale databron
├── assets/css/         style.css (designsysteem), fonts.css
├── assets/js/main.js
├── assets/fonts/       Montserrat + Open Sans (woff2)
├── assets/img/         logo's, favicon, og-image
├── robots.txt
└── sitemap.xml
```

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
| Oprichter + quote | `data/site.js > founder` | over LINK., contact |
| Alle foto's | `data/site.js > photos` | elke pagina |
| Zo werkt het: 4 fases met foto, glaskaartjes en "wat je krijgt" | `data/site.js > method` (+ `pilotLabel`) | home, diensten |
| Voorbeelden in de hero-kaart | `data/site.js > liveCard` | home |
| Voor beslissers (eigenaar / sales) | `data/site.js > audiences` | home |
| Markten (woordmuur) | `data/site.js > sectors` | home |
| Veelgestelde vragen + Google FAQ-data | `data/site.js > faq` | diensten |
| Verhalen | `content/verhalen/*.md` → `tools/build-verhalen.py` | verhalen, home (3 kaarten) |
| Reactietijd | `data/site.js > contact.responseTime` | chip, contact, FAQ, waarden, feiten |
| Kennismaking plannen (agenda-link) | `data/site.js > contact.bookingUrl` | alle "Plan een kennismaking"-knoppen, contact |
| Apollo-tracking (na toestemming) | `data/site.js > tracking.apolloAppId` | cookiemelding, alle pagina's |
| Anonieme referenties (functie + type bedrijf) | `data/site.js > references` | nog niet op de site; blok toevoegen in index.html met `data-refs` |
| Vacatures | `data/site.js > jobs` | werken-bij.html (+ Google Jobs-gegevens) |
| Partnerportaal-knop | `data/site.js > contact.portalUrl` | header, mobiel menu, footer |
| Contactformulier-koppeling | `data/site.js > contact.form` | contactpagina |

\* Het JSON-LD-blok in `index.html` (voor Google) staat statisch in de HTML. Pas het telefoonnummer daar ook aan als het verandert.

**Wat bewust niet op de site staat.** De werkmethode staat er alleen als traject (kick-off, eerste belmoment, eerste meeting, structurele stroom). Hoe LINK. dat doet, en ook de resultaatcodes en het rapportageformat, blijft voor de kennismaking. Die staan dus ook niet in de code, zodat niemand ze uit de broncode kan halen.

## Verhalen (blog)

De verhalen staan vast: vijf gewone pagina's (`verhaal-*.html`) plus het overzicht `verhalen.html`. Voor het online zetten hoef je niets te draaien of bij te houden.

Later uitbreiden? De teksten staan in `content/verhalen/`. Voeg een bestand toe en draai `python3 tools/build-verhalen.py --live`. Een opzet voor een partnerverhaal staat in `content/sjablonen/partnerverhaal.md`. Die gaat pas online met echte cijfers en toestemming van de partner.

## Bronnen

- Huisstijl: Drive > Website > *Huisstijl* (zwart `#000000`, blauw `#38b6ff`, Open Sans)
- Teksten: Drive > Website > *Website Teksten Opzet*
- Logo's: Drive > Website > *LINK. LOGO's.zip*, omgezet naar `assets/img/logo-zwart.png` en `logo-wit.png`
- Briefing: *Website Onboarding Vragen* (modern en hip, maar met rust, "geen kermis", doel: inbound leads)

## Nog in te vullen voor livegang

1. **Foto's** staan in `assets/img/hens/` (uit Drive > Website > wetransfer-map, bijgesneden, gecomprimeerd en zonder EXIF/GPS). Welke foto waar staat, regel je in `data/site.js > photos`. Een lege `src` laat het fotovak netjes verdwijnen.
2. **Partnerportaal-URL** in `contact.portalUrl`. Zolang dit veld leeg is, blijft de knop verborgen.
3. **Contactformulier.** Zonder koppeling opent het formulier een ingevulde e-mail naar info@linkgrp.nl. Wil je het formulier aan een Google Form koppelen (zoals besproken in de website-evaluatie), vul dan `contact.form.endpoint` in met de `formResponse`-URL en zet bij `fields` de `entry.xxxx`-ID's.
4. **Controleer** e-mail en telefoonnummer. Die komen uit de *Website Teksten Opzet*.

## Techniek

- **Snel:** geen frameworks, fonts zelf gehost (`assets/fonts`, alleen Latin), afbeeldingen klein.
- **AVG:** geen Google Fonts-verzoeken. Apollo-websitetracking laadt pas na toestemming via de cookiemelding. Privacyverklaring op `privacy.html`.
- **Toegankelijk:** semantische HTML, skip-link, focusstijlen, labels bij formuliervelden. `prefers-reduced-motion` zet alle animaties uit.
- **SEO:** unieke titels en beschrijvingen per pagina, canonical-tags, Open Graph, `sitemap.xml`, `robots.txt`, Organization-schema.
- **Responsive:** getest op 360, 390, 768, 1024 en 1440 px zonder horizontaal scrollen.

## Structuur

```
website/
├── index.html          Home
├── diensten.html       Telefonische acquisitie + business development
├── over-link.html      Over LINK.: Hens, waarom partners voor LINK. kiezen
├── ons-verhaal.html    (doorverwijzing naar over-link.html)
├── waarom-link.html    (doorverwijzing naar over-link.html#waarom)
├── verhalen.html       Overzicht verhalen (gegenereerd)
├── contact.html        Formulier + gegevens
├── werken-bij.html     Vacatures
├── privacy.html        Privacyverklaring
├── 404.html
├── data/site.js        ← centrale databron
├── assets/css/         style.css (designsysteem), fonts.css
├── assets/js/main.js
├── assets/fonts/       Montserrat + Open Sans (woff2)
├── assets/img/         logo's, favicon, og-image
├── robots.txt
└── sitemap.xml
```

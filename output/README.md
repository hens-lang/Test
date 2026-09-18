# LINK. kennismakingsdeck Techmetric3d

Kennismakingsdeck van LINK. voor Bart van Techmetric3d. Negen slides, 16:9 (1920x1080), opgeleverd als PDF (primair), PPTX (bewerkbaar) en PNG-previews.

## Bestanden

- `LINK. kennismaking Techmetric3d.pdf`, de primaire deck, elke slide is één pagina, tekst is selecteerbaar en fonts zijn ingesloten.
- `LINK. kennismaking Techmetric3d.pptx`, dezelfde slides als bewerkbare PowerPoint, gebouwd vanuit dezelfde contentlaag.
- `preview/slide-01.png` t/m `slide-09.png`, één PNG per slide.
- `preview/overview.png`, contact sheet met alle slides in een grid.

## Opnieuw bouwen

Vanuit de projectroot (één map boven deze map):

```bash
npm install            # eenmalig, installeert playwright, pptxgenjs, sharp en de fonts
node build/render.js   # bouwt deck.html, de PDF en de PNG-previews
node build/pptx.js     # bouwt de PPTX
node build/artifact.js # bouwt build/webdeck.html, de deelbare webversie
```

De webversie (`build/webdeck.html`) is dezelfde deck als klikbare presentatie in de browser, met pijltjestoetsen, stippen, swipe en volledig scherm. Die wordt als artifact gepubliceerd zodat je één link kunt delen.

De PDF wordt gerenderd met Playwright (Chromium headless). In deze omgeving staat Chromium op `/opt/pw-browsers/chromium`; draai je lokaal, verwijder dan de `executablePath` in `build/render.js` of draai eenmalig `npx playwright install chromium`.

## Teksten aanpassen

Alle teksten staan in `content/slides.json`, de templates halen daaruit. Eén regel wijzigen kan dus zonder in de layout te wroeten:

- `meta`: titel en footertekst.
- `slides[n].eyebrow`: het kleine blauwe label boven de kop.
- `slides[n].title`: de kop als lijst segmenten; een segment met `"accent": true` wordt in serif italic gezet.
- Overige velden per slidetype: `paragraphs`, `stats`, `cards`, `steps`, `rules`, `timeline`, `deliverables`, `contact`, `closing`.

Na een tekstwijziging draai je beide buildcommando's opnieuw, dan blijven PDF en PPTX inhoudelijk identiek.

## Layout of huisstijl aanpassen

- `build/template.js`: HTML-templates en alle CSS (kleuren, marges, typografie, iconen). De huisstijlkleuren staan bovenaan de CSS in `:root`.
- `build/pptx.js`: dezelfde opbouw voor PowerPoint, met de kleuren in de constante `C`.

## Huisstijl in het kort

Zwart `#000000` en donker `#141821` voor donkere slides, crème `#e9e0cd` voor lichte slides, kaarten `#f8f4eb`, inkt `#1c2230`, gedempt `#6f6a5c`, accentblauw `#38b6ff` als enige accent. Koppen in Inter extra bold met één serif italic accent (Playfair Display), iconen in monoline stijl in het accentblauw.

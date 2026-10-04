# Sablet VI – deelbare website

Twee manieren om te delen:
- **Link**: `deel/index.html` is gepubliceerd als claude.ai-pagina. Zet hem via de knop *Delen* op die pagina open voor anderen en stuur de link door.
- **Bestand**: `Sablet-VI.html` is één bestand (foto's zitten erin) dat je via WhatsApp, e-mail of WeTransfer kunt doorsturen. Dubbelklikken en het opent in elke browser.

## Zo hangt alles samen

```
huis.json  ──┐
fotos/     ──┼──>  python3 bouw.py  ──>  Sablet-VI.html   (dit bestand deel je)
template.html┘
```

- **`huis.json`**: alle gegevens op één plek: teksten, kamers, foto's, tarieven, omgeving, klimaat, reviews, FAQ en contact.
  Alles op de site wordt hieruit opgebouwd. Pas je een prijs aan, dan veranderen de tarievenkaarten, de seizoensbalk,
  de kleuren in de kalender, de prijs per maand bij "Wanneer ga jij?" en de prijsberekening tegelijk mee.
- **`fotos/`**: zet hier de foto's (namen staan in `fotos/LEESMIJ.txt`). `bouw.py` verkleint ze en stopt ze ín het HTML-bestand.
  Ontbreekt er een foto, dan toont de site een Provençaalse illustratie.
- **`template.html`**: het ontwerp en de animaties.
- **`bouw.py`**: voegt alles samen en waarschuwt als er iets niet klopt (ontbrekende foto, contact niet ingevuld, …).

## Impressie of verhuursite
In `huis.json` staat `"toonPrijzen": false`: de site is dan een impressie, zonder tarieven, prijzen en boekingskalender.
Zet het op `true` en draai `python3 bouw.py`, dan komen tarieven, kalender en aanvraag terug.

## Nog in te vullen in `huis.json`
1. `contact`: naam, WhatsApp-nummer (bv. `+32 470 12 34 56`) en e-mail. Zolang dit `VUL_IN` is, zijn de aanvraagknoppen verborgen
   (de knop "Kopieer aanvraagbericht" werkt altijd).
2. `tarieven.periodes`: voeg de periodes voor 2027 toe zodra ze bekend zijn. Weken buiten een periode tonen "contacteer ons".
3. `bezet`: geboekte weken, bv. `{ "van": "2027-07-04", "tot": "2027-07-18" }`. Die worden doorstreept in de kalender.

## Wat zit erin
- Diashow met jullie foto's bovenaan, rustige animaties bij het scrollen
- Rondleiding per verdieping: klik op een ruimte in de lijst of op het plan en zie de foto's van die ruimte
- Fotogalerij met grote weergave (pijltjes, vegen, miniaturen)
- Voorzieningen, het verhaal van het dorp, winkels en eten & drinken
- Interactieve kaart met afstanden en rijtijden, filters en route via Google Maps
- Per maand: weer, wat er te beleven valt en de prijs in die periode
- Tarieven met seizoensbalk, kalender per week (zondag–zondag) met prijsberekening en aanvraagbericht
- Reviews en praktische info
- Werkt op telefoon, tablet en computer

Tip: de foto's zijn nu 588 × 441 pixels (zoals ze uit de chat kwamen). Grotere originelen in `fotos/`
zetten (zelfde namen) en `python3 bouw.py` draaien maakt de site nog scherper.

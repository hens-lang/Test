# Sablet VI – deelbare website

Eén HTML-bestand (`Sablet-VI.html`) dat je kunt doorsturen via WhatsApp, e-mail, WeTransfer of een USB-stick.
Je hoeft niets te hosten: dubbelklikken en het opent in elke browser, op telefoon en computer.

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

## Nog in te vullen in `huis.json`
1. `contact`: naam, WhatsApp-nummer (bv. `+32 470 12 34 56`) en e-mail. Zolang dit `VUL_IN` is, zijn de aanvraagknoppen verborgen
   (de knop "Kopieer aanvraagbericht" werkt altijd).
2. `tarieven.periodes`: voeg de periodes voor 2027 toe zodra ze bekend zijn. Weken buiten een periode tonen "contacteer ons".
3. `bezet`: geboekte weken, bv. `{ "van": "2027-07-04", "tot": "2027-07-18" }`. Die worden doorstreept in de kalender.

## Wat zit erin
- Bewegend Provence-landschap met parallax, dag/nacht-knop en krekelgeluid
- Klikbaar plattegrond (2 verdiepingen) met foto's per ruimte
- Fotogalerij met filters en vergrootweergave (swipen, pijltjestoetsen)
- Draaikaarten met voorzieningen
- Interactieve kaart met afstanden en rijtijden, filters en route via Google Maps
- Klimaatgrafiek per maand met seizoensprijs
- Tarieven met seizoensbalk, kalender per week (zondag–zondag), prijsberekening en aanvraag via WhatsApp/e-mail
- Reviews en praktische info

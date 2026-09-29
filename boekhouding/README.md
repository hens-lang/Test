# Boekhouding — ons eigen "Exact light"

Facturen komen binnen, **jij keurt alleen goed**, en de app regelt de rest:
betaalbestand voor de bank, afletteren van betalingen, verkoopfacturen en btw-overzicht.
Alles zit in één database, dus relaties, facturen, betalingen en bankmutaties zijn aan elkaar gekoppeld.

## Starten

```bash
cd boekhouding
pip install -r requirements.txt
python demo.py        # optioneel: voorbeelddata
python app.py         # http://localhost:5000
```

Omgevingsvariabelen (optioneel):

| Variabele | Doel |
|---|---|
| `APP_WACHTWOORD` | Zet inloggen aan (verplicht als de app niet alleen lokaal draait) |
| `APP_GEHEIM` | Vaste sessiesleutel, zodat je ingelogd blijft na herstart |
| `BOEKHOUDING_DB` | Pad naar de database (standaard `data/boekhouding.db`) |
| `HOST` / `PORT` | Waar de app luistert (standaard `127.0.0.1:5000`) |

## De werkstroom

```
Inkoopfactuur ──► Goedkeuren ──► Betaalvoorstel ──► SEPA-bestand ──► Bank (1x bevestigen)
   (pdf)          (1 klik/bulk)   (plant op verval)    (pain.001)            │
                                                                            ▼
Verkoopfactuur ──► Verzonden ─────────────────────────────► Bankafschrift inlezen (CAMT.053/CSV)
                                                            └► automatisch op "betaald"
```

1. **Inkoop**: factuur invoeren met pdf. Dubbele facturen (zelfde leverancier + nummer) worden geweigerd.
2. **Automatisch goedkeuren**: geef vaste leveranciers bij *Relaties* een limiet; facturen daaronder
   worden direct goedgekeurd (en gelogd). Alles daarboven komt in *Goedkeuren*.
3. **Betalingen**: goedgekeurde facturen staan in het betaalvoorstel, gepland X dagen vóór de vervaldatum.
   Eén klik maakt een SEPA-betaalbestand (pain.001.001.03) dat elke Nederlandse bank accepteert,
   inclusief gestructureerde betalingskenmerken.
4. **Bank**: lees een CAMT.053- of CSV-afschrift (ING, Rabobank of eenvoudig formaat) in. Betalingen
   worden herkend aan de referentie `INK-<nr>` uit het betaalbestand, of aan bedrag + IBAN. Ontvangsten
   worden herkend aan het factuurnummer. Wat niet automatisch lukt, koppel je met één klik.
5. **Verkoop**: facturen met automatische nummering, meerdere btw-tarieven, afdrukken/PDF en e-mail aan de klant.
6. **Btw**: per kwartaal omzet-btw, voorbelasting en het saldo.
7. **Logboek**: elke goedkeuring, batch en koppeling wordt vastgelegd (audit trail).

## Structuur

| Bestand | Inhoud |
|---|---|
| `db.py` | Databaseschema (SQLite) en instellingen |
| `logica.py` | Alle bedrijfsregels: goedkeuren, betaalbatches, afletteren, verkoop, btw |
| `sepa.py` | SEPA pain.001 betaalbestand |
| `bankimport.py` | Inlezen CAMT.053 en CSV |
| `app.py` | Webschermen (Flask) |
| `tests/` | Test van de hele keten: `python -m pytest` |

## Volgende stappen (nog niet gebouwd)

- **Direct betalen via de bank-API** in plaats van een bestand uploaden (bijv. bunq API of Ponto/PSD2);
  goedkeuren in de app zet de betaling dan meteen klaar.
- **Facturen automatisch uit de mailbox** halen (inkoop@...) en velden uit de pdf uitlezen.
- **Herinneringen** automatisch mailen voor te late verkoopfacturen.
- **Export naar de accountant** (grootboek/auditfile XAF).

"""Vult een lege database met voorbeelddata om de app te verkennen:  python demo.py
Gebruik dit NIET op je echte administratie (het script weigert als er al gegevens zijn)."""

from datetime import date, timedelta

import betalen
import db
import logica

con = db.verbind()
db.initialiseer(con)
if con.execute("SELECT COUNT(*) FROM relaties").fetchone()[0]:
    raise SystemExit("Database bevat al gegevens; demo niet geladen.")

for k, v in {"bedrijfsnaam": "Demo B.V.", "iban": "NL91ABNA0417164300", "plaats": "Utrecht",
             "adres": "Voorbeeldstraat 1", "postcode": "3511 AA", "kvk": "12345678",
             "btw_nummer": "NL001234567B01", "email": "administratie@demo.nl"}.items():
    db.zet_instelling(con, k, v)


def d(n):
    return (date.today() + timedelta(days=n)).isoformat()


def relatie(naam, iban, soort="crediteur", limiet=0, rekening=None, geverifieerd=1, email=None, bron="handmatig"):
    return con.execute(
        "INSERT INTO relaties (naam, soort, iban, auto_goedkeur_limiet_cent, standaard_rekening, iban_geverifieerd, "
        "email, bron, aangemaakt_op) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (naam, soort, iban, limiet, rekening, geverifieerd, email, bron, db.nu())).lastrowid


tel = relatie("Telefonie Provider B.V.", "NL20INGB0001234567", limiet=50000, rekening="4200")
huur = relatie("Vastgoed Utrecht", "NL69INGB0123456789", rekening="4100")
lead = relatie("Leaddata Nederland", "NL44RABO0123456789", rekening="4400", geverifieerd=0, bron="automatisch")
soft = relatie("CRM Software B.V.", "NL86INGB0002445588", rekening="4300")
klant = relatie("Klant Groep B.V.", "NL02ABNA0123456789", soort="debiteur", email="crediteuren@klantgroep.nl")
klant2 = relatie("Zorg & Co", "NL18RABO0123459876", soort="debiteur", email="finance@zorgenco.nl")

# afgelopen maanden: facturen die al betaald zijn
for m in range(1, 6):
    datum = d(-30 * m)
    fid = logica.voeg_inkoopfactuur_toe(con, huur, f"HUUR-{m}", datum, datum, "Huur kantoor", 185000, 38850)
    logica.beoordeel(con, fid, True)
    v = logica.maak_verkoopfactuur(con, klant, [{"omschrijving": "Belcampagne", "aantal": 40 + 5 * m,
                                                 "prijs_cent": 6500, "btw_pct": 21}], datum)
    logica.zet_verkoopstatus(con, v, "verzonden")
    logica.importeer_transacties(con, [
        {"datum": datum, "bedrag_cent": -224850, "tegenrekening": "NL69INGB0123456789", "naam": "Vastgoed Utrecht",
         "omschrijving": "Huur", "referentie": f"INK-{fid}"},
        {"datum": d(-30 * m + 10), "bedrag_cent": logica.verkoop_totalen(con, v)["incl"],
         "tegenrekening": "NL02ABNA0123456789", "naam": "Klant Groep B.V.",
         "omschrijving": f"Betaling {con.execute('SELECT factuurnummer FROM verkoopfacturen WHERE id=?', (v,)).fetchone()[0]}"},
    ])

# nu: wat er op jou wacht
logica.voeg_inkoopfactuur_toe(con, tel, "TP-2031", d(-5), d(9), "Belminuten september", 15000, 3150, rekening="4200",
                              bron="email", zekerheid=0.98)
logica.voeg_inkoopfactuur_toe(con, huur, "HUUR-10", d(-2), d(12), "Huur oktober", 185000, 38850, bron="email", zekerheid=0.99)
logica.voeg_inkoopfactuur_toe(con, lead, "LD-778", d(-20), d(-1), "Leadbestand Q4", 42000, 8820, bron="upload",
                              zekerheid=0.93, waarschuwingen=["Nieuwe leverancier: controleer naam en IBAN bij de eerste factuur."])
logica.voeg_inkoopfactuur_toe(con, soft, "CRM-5521", d(-3), d(27), "Licenties CRM (10 gebruikers)", 49000, 10290,
                              bron="email", zekerheid=0.97, betaalwijze="incasso",
                              waarschuwingen=["Wordt geïncasseerd door de leverancier: niet zelf betalen."])
v = logica.maak_verkoopfactuur(con, klant2, [{"omschrijving": "Afspraken ingepland", "aantal": 18, "prijs_cent": 9500,
                                              "btw_pct": 21}], d(-25))
logica.zet_verkoopstatus(con, v, "verzonden")
logica.importeer_transacties(con, [{"datum": d(-1), "bedrag_cent": -1250, "tegenrekening": "", "naam": "ABN AMRO Bank",
                                    "omschrijving": "Kosten Ondernemerspakket"}])
con.commit()
print("Demo-data geladen:", len(betalen.betaalvoorstel(con)), "factuur in het betaalvoorstel.")
print("Start de app met:  python app.py")

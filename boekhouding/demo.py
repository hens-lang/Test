"""Vult een lege database met voorbeelddata om de app te verkennen:  python demo.py"""

from datetime import date, timedelta

import db
import logica

con = db.verbind()
db.initialiseer(con)
if con.execute("SELECT COUNT(*) FROM relaties").fetchone()[0]:
    raise SystemExit("Database bevat al gegevens; demo niet geladen.")

for k, v in {"bedrijfsnaam": "Demo B.V.", "iban": "NL91ABNA0417164300", "plaats": "Utrecht"}.items():
    con.execute("UPDATE instellingen SET waarde = ? WHERE sleutel = ?", (v, k))


def relatie(naam, iban, soort="crediteur", limiet=0):
    return con.execute("INSERT INTO relaties (naam, soort, iban, auto_goedkeur_limiet_cent, aangemaakt_op) "
                       "VALUES (?, ?, ?, ?, ?)", (naam, soort, iban, limiet, db.nu())).lastrowid


d = lambda n: (date.today() + timedelta(days=n)).isoformat()  # noqa: E731
tel = relatie("Telefonie Provider B.V.", "NL20INGB0001234567", limiet=25000)
huur = relatie("Vastgoed Utrecht", "NL69INGB0123456789")
lead = relatie("Leaddata Nederland", "NL44RABO0123456789")
klant = relatie("Klant Groep B.V.", "NL02ABNA0123456789", soort="debiteur")

logica.voeg_inkoopfactuur_toe(con, tel, "TP-2031", d(-5), d(9), "Belminuten september", 15000, 3150)
logica.voeg_inkoopfactuur_toe(con, huur, "HUUR-10", d(-2), d(12), "Huur oktober", 185000, 38850)
logica.voeg_inkoopfactuur_toe(con, lead, "LD-778", d(-20), d(-1), "Leadbestand Q4", 42000, 8820)
logica.maak_verkoopfactuur(con, klant, [{"omschrijving": "Belcampagne week 39", "aantal": 32,
                                        "prijs_cent": 6500, "btw_pct": 21}], d(-3))
con.execute("UPDATE verkoopfacturen SET status = 'verzonden'")
con.commit()
print("Demo-data geladen. Start de app met:  python app.py")

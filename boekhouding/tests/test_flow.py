"""Test de hele keten: relatie -> factuur -> goedkeuren -> betaalbatch -> bankafschrift -> betaald."""

import io
import os
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import bankimport  # noqa: E402
import db  # noqa: E402
import logica  # noqa: E402
from app import app  # noqa: E402

EIGEN_IBAN = "NL91ABNA0417164300"
LEV_IBAN = "NL20INGB0001234567"
KLANT_IBAN = "NL02RABO0123456789"


@pytest.fixture
def con(tmp_path):
    c = db.verbind(str(tmp_path / "t.db"))
    db.initialiseer(c)
    c.execute("UPDATE instellingen SET waarde = ? WHERE sleutel = 'iban'", (EIGEN_IBAN,))
    c.commit()
    yield c
    c.close()


def relatie(con, naam, iban, soort="crediteur", limiet=0):
    cur = con.execute("INSERT INTO relaties (naam, soort, iban, auto_goedkeur_limiet_cent, aangemaakt_op) "
                      "VALUES (?, ?, ?, ?, ?)", (naam, soort, iban, limiet, db.nu()))
    con.commit()
    return cur.lastrowid


def status(con, tabel, fid):
    return con.execute(f"SELECT status FROM {tabel} WHERE id = ?", (fid,)).fetchone()["status"]


def test_hulpfuncties():
    assert logica.iban_geldig("NL91 ABNA 0417 1643 00")
    assert not logica.iban_geldig("NL91ABNA0417164301")
    assert logica.naar_cent("1.234,56") == 123456
    assert logica.naar_cent("12.5") == 1250
    assert logica.euro(123456) == "€ 1.234,56"
    assert logica.euro(-5) == "-€ 0,05"


def test_inkoop_keten(con):
    lev = relatie(con, "Telefonie B.V.", LEV_IBAN)
    verval = (date.today() + timedelta(days=10)).isoformat()
    fid = logica.voeg_inkoopfactuur_toe(con, lev, "T-001", date.today().isoformat(), verval,
                                        "abonnement", 10000, 2100, "1234567890123456")
    assert status(con, "inkoopfacturen", fid) == "ter_goedkeuring"
    with pytest.raises(ValueError):  # dubbele factuur
        logica.voeg_inkoopfactuur_toe(con, lev, "T-001", date.today().isoformat(), verval, "", 1, 0)

    logica.beoordeel(con, fid, True)
    voorstel = logica.betaalvoorstel(con)
    assert [v["id"] for v in voorstel] == [fid]

    batch = logica.maak_betaalbatch(con, [fid])
    assert status(con, "inkoopfacturen", fid) == "in_batch"
    xml = con.execute("SELECT xml FROM betaalbatches WHERE id = ?", (batch,)).fetchone()["xml"]
    root = ET.fromstring(xml)
    ns = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}
    assert root.find(".//p:CtrlSum", ns).text == "121.00"
    assert root.find(".//p:EndToEndId", ns).text == f"INK-{fid}"
    assert root.find(".//p:CdtrRefInf/p:Ref", ns).text == "1234567890123456"

    # Bank meldt de afschrijving terug met onze end-to-end-referentie
    camt = f"""<?xml version="1.0"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"><BkToCstmrStmt><Stmt>
      <Ntry><Amt Ccy="EUR">121.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>{date.today()}</Dt></BookgDt>
      <AcctSvcrRef>ABC1</AcctSvcrRef><NtryDtls><TxDtls><Refs><EndToEndId>INK-{fid}</EndToEndId></Refs>
      <RltdPties><Cdtr><Nm>Telefonie B.V.</Nm></Cdtr><CdtrAcct><Id><IBAN>{LEV_IBAN}</IBAN></Id></CdtrAcct></RltdPties>
      </TxDtls></NtryDtls></Ntry></Stmt></BkToCstmrStmt></Document>""".encode()
    nieuw, gekoppeld = logica.importeer_transacties(con, bankimport.lees_bestand("afschrift.xml", camt))
    assert (nieuw, gekoppeld) == (1, 1)
    assert status(con, "inkoopfacturen", fid) == "betaald"
    # Nogmaals inlezen: geen dubbele transacties
    assert logica.importeer_transacties(con, bankimport.lees_bestand("afschrift.xml", camt)) == (0, 0)


def test_automatisch_goedkeuren(con):
    lev = relatie(con, "Software", LEV_IBAN, limiet=5000)
    d = date.today().isoformat()
    klein = logica.voeg_inkoopfactuur_toe(con, lev, "S-1", d, d, "", 4000, 840)
    groot = logica.voeg_inkoopfactuur_toe(con, lev, "S-2", d, d, "", 5000, 1050)
    assert status(con, "inkoopfacturen", klein) == "goedgekeurd"
    assert status(con, "inkoopfacturen", groot) == "ter_goedkeuring"


def test_verkoop_en_ontvangst(con):
    klant = relatie(con, "Klant B.V.", KLANT_IBAN, soort="debiteur")
    fid = logica.maak_verkoopfactuur(con, klant, [
        {"omschrijving": "Belcampagne", "aantal": 10, "prijs_cent": 5000, "btw_pct": 21},
        {"omschrijving": "Boek", "aantal": 1, "prijs_cent": 1000, "btw_pct": 9},
    ])
    t = logica.verkoop_totalen(con, fid)
    assert (t["excl"], t["btw"], t["incl"]) == (51000, {21: 10500, 9: 90}, 61590)
    nummer = con.execute("SELECT factuurnummer FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone()[0]
    assert logica.volgend_factuurnummer(con).endswith("0002")
    con.execute("UPDATE verkoopfacturen SET status = 'verzonden' WHERE id = ?", (fid,))

    csv_ing = ('"Datum";"Naam / Omschrijving";"Rekening";"Tegenrekening";"Code";"Af Bij";"Bedrag (EUR)";'
               '"Mutatiesoort";"Mededelingen"\n'
               f'"{date.today():%Y%m%d}";"Klant B.V.";"{EIGEN_IBAN}";"{KLANT_IBAN}";"OV";"Bij";"615,90";'
               f'"Overschrijving";"Betaling {nummer}"\n')
    assert logica.importeer_transacties(con, bankimport.lees_bestand("ing.csv", csv_ing.encode())) == (1, 1)
    assert status(con, "verkoopfacturen", fid) == "betaald"

    q = (date.today().month - 1) // 3 + 1
    assert logica.btw_overzicht(con, date.today().year, q)["verkoop_btw"] == 10590


def test_webschermen(tmp_path):
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "web.db"))
    web = app.test_client()
    web.post("/instellingen", data={**db.STANDAARD_INSTELLINGEN, "iban": EIGEN_IBAN})
    web.post("/relaties/nieuw", data={"naam": "Leverancier", "soort": "beide", "iban": LEV_IBAN,
                                      "auto_goedkeur_limiet": "0"})
    r = web.post("/inkoop/nieuw", data={
        "relatie_id": "1", "factuurnummer": "X1", "factuurdatum": date.today().isoformat(),
        "vervaldatum": date.today().isoformat(), "bedrag_excl": "100,00", "btw_pct": "21",
        "bestand": (io.BytesIO(b"%PDF-1.4"), "factuur.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 302
    assert b"121,00" in web.get("/goedkeuren").data
    web.post("/goedkeuren", data={"ids": "1", "actie": "goedkeuren"})
    r = web.post("/betalingen/batch", data={"ids": "1"})
    assert "nieuw=1" in r.headers["Location"]
    assert b"pain.001.001.03" in web.get("/betalingen/batch/1.xml").data
    web.post("/verkoop/nieuw", data={"relatie_id": "1", "omschrijving": ["Uren"], "aantal": ["2"],
                                     "prijs": ["75"], "btw_pct": ["21"]})
    for pad in ("/", "/relaties", "/relaties/1", "/inkoop", "/inkoop/1", "/betalingen", "/verkoop",
                "/verkoop/1", "/bank", "/bank?filter=alle", "/btw", "/logboek", "/instellingen"):
        assert web.get(pad).status_code == 200, pad
    assert b"181,50" in web.get("/verkoop/1").data

"""Test de hele keten: factuur binnen -> automatisch gelezen & geboekt -> goedkeuren -> betaalopdracht
(bestand of ABN via Ponto) -> bankmutatie -> betaald, plus verkoop, btw, rapportages en de schermen."""

import io
import json
import os
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["PLANNER_UIT"] = "1"
for k in ("ANTHROPIC_API_KEY", "PONTO_CLIENT_ID", "PONTO_CLIENT_SECRET", "SMTP_HOST", "IMAP_HOST"):
    os.environ.pop(k, None)

import ai  # noqa: E402
import bankimport  # noqa: E402
import betalen  # noqa: E402
import db  # noqa: E402
import factuurdocument  # noqa: E402
import grootboek  # noqa: E402
import intake  # noqa: E402
import logica  # noqa: E402
import mail  # noqa: E402
import planner  # noqa: E402
import ponto  # noqa: E402

EIGEN_IBAN = "NL91ABNA0417164300"
LEV_IBAN = "NL20INGB0001234567"
KLANT_IBAN = "NL02RABO0123456789"
ANDER_IBAN = "NL69INGB0123456789"
VANDAAG = date.today().isoformat()


@pytest.fixture
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "UPLOAD_MAP", str(tmp_path / "uploads"))
    monkeypatch.setattr(intake, "INBOX_MAP", str(tmp_path / "inbox"))
    c = db.verbind(str(tmp_path / "t.db"))
    db.initialiseer(c)
    db.zet_instelling(c, "iban", EIGEN_IBAN)
    db.zet_instelling(c, "bedrijfsnaam", "Wij B.V.")
    c.commit()
    yield c
    c.close()


def relatie(con, naam, iban, soort="crediteur", limiet=0, geverifieerd=0, email=None):
    rid = con.execute("INSERT INTO relaties (naam, soort, iban, auto_goedkeur_limiet_cent, iban_geverifieerd, email, "
                      "aangemaakt_op) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (naam, soort, iban, limiet, geverifieerd, email, db.nu())).lastrowid
    con.commit()
    return rid


def rij(con, tabel, fid):
    return con.execute(f"SELECT * FROM {tabel} WHERE id = ?", (fid,)).fetchone()


def saldo(con, rekening):
    return con.execute("SELECT COALESCE(SUM(debet_cent - credit_cent), 0) FROM journaalregels WHERE rekening = ?",
                       (rekening,)).fetchone()[0]


def journaal_in_balans(con):
    return con.execute("SELECT COALESCE(SUM(debet_cent), 0) = COALESCE(SUM(credit_cent), 0) FROM journaalregels").fetchone()[0]


def camt(entries):
    ntries = "".join(
        f"""<Ntry><Amt Ccy="EUR">{abs(b) / 100:.2f}</Amt><CdtDbtInd>{'DBIT' if b < 0 else 'CRDT'}</CdtDbtInd>
        <BookgDt><Dt>{VANDAAG}</Dt></BookgDt><AcctSvcrRef>{ref}</AcctSvcrRef><NtryDtls><TxDtls><Refs><EndToEndId>{e2e}</EndToEndId></Refs>
        <RltdPties><{'Cdtr' if b < 0 else 'Dbtr'}><Nm>{naam}</Nm></{'Cdtr' if b < 0 else 'Dbtr'}>
        <{'CdtrAcct' if b < 0 else 'DbtrAcct'}><Id><IBAN>{iban}</IBAN></Id></{'CdtrAcct' if b < 0 else 'DbtrAcct'}></RltdPties>
        <RmtInf><Ustrd>{oms}</Ustrd></RmtInf></TxDtls></NtryDtls></Ntry>"""
        for ref, b, e2e, naam, iban, oms in entries)
    return (f'<?xml version="1.0"?><Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02"><BkToCstmrStmt>'
            f"<Stmt>{ntries}</Stmt></BkToCstmrStmt></Document>").encode()


# ---------------------------------------------------------------- basis


def test_hulpfuncties():
    assert logica.iban_geldig("NL91 ABNA 0417 1643 00")
    assert not logica.iban_geldig("NL91ABNA0417164301")
    assert logica.naar_cent("1.234,56") == 123456
    assert logica.naar_cent(12.5) == 1250
    assert logica.euro(123456) == "€ 1.234,56"
    assert logica.euro(-5) == "-€ 0,05"


def test_inkoop_keten_met_betaalbestand(con):
    lev = relatie(con, "Telefonie B.V.", LEV_IBAN)
    verval = (date.today() + timedelta(days=10)).isoformat()
    fid = logica.voeg_inkoopfactuur_toe(con, lev, "T-001", VANDAAG, verval, "abonnement", 10000, 2100,
                                        "1234567890123456", rekening="4200")
    assert rij(con, "inkoopfacturen", fid)["status"] == "ter_goedkeuring"
    assert saldo(con, "4200") == 0                      # nog niet geboekt vóór goedkeuring
    with pytest.raises(ValueError):
        logica.voeg_inkoopfactuur_toe(con, lev, "T-001", VANDAAG, verval, "", 1, 0)

    logica.beoordeel(con, fid, True)
    assert saldo(con, "4200") == 10000 and saldo(con, "1510") == 2100 and saldo(con, "1600") == -12100
    assert rij(con, "relaties", lev)["iban_geverifieerd"] == 1

    batch, url = betalen.maak_betaalopdracht(con, [fid])
    assert url is None                                   # geen Ponto: betaalbestand
    assert rij(con, "inkoopfacturen", fid)["status"] == "in_batch"
    root = ET.fromstring(rij(con, "betaalbatches", batch)["xml"])
    ns = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}
    assert root.find(".//p:CtrlSum", ns).text == "121.00"
    assert root.find(".//p:EndToEndId", ns).text == f"INK-{fid}"
    assert root.find(".//p:CdtrRefInf/p:Ref", ns).text == "1234567890123456"

    afschrift = camt([("A1", -12100, f"INK-{fid}", "Telefonie B.V.", LEV_IBAN, "")])
    assert logica.importeer_transacties(con, bankimport.lees_bestand("a.xml", afschrift)) == (1, 1)
    assert rij(con, "inkoopfacturen", fid)["status"] == "betaald"
    assert saldo(con, "1600") == 0 and saldo(con, "1900") == 0 and saldo(con, "1100") == -12100
    assert logica.importeer_transacties(con, bankimport.lees_bestand("a.xml", afschrift)) == (0, 0)
    assert journaal_in_balans(con)


def test_afkeuren_na_goedkeuren_storneert(con):
    lev = relatie(con, "Lev", LEV_IBAN)
    fid = logica.voeg_inkoopfactuur_toe(con, lev, "X", VANDAAG, VANDAAG, "", 5000, 1050)
    logica.beoordeel(con, fid, True)
    logica.beoordeel(con, fid, False, "dubbel")
    assert saldo(con, "1600") == 0 and saldo(con, "1510") == 0
    logica.beoordeel(con, fid, True)                     # opnieuw goedkeuren boekt opnieuw
    assert saldo(con, "1600") == -6050
    logica.wijzig_inkoopfactuur(con, fid, {"bedrag_excl_cent": 6000, "btw_cent": 1260, "rekening": "4300"})
    assert saldo(con, "1600") == -7260 and saldo(con, "4300") == 6000 and saldo(con, "4900") == 0
    assert journaal_in_balans(con)


def test_automatisch_goedkeuren_alleen_bij_geverifieerd_iban(con):
    onbekend = relatie(con, "Nieuw", LEV_IBAN, limiet=50000)
    vertrouwd = relatie(con, "Vertrouwd", ANDER_IBAN, limiet=50000, geverifieerd=1)
    a = logica.voeg_inkoopfactuur_toe(con, onbekend, "1", VANDAAG, VANDAAG, "", 4000, 840)
    b = logica.voeg_inkoopfactuur_toe(con, vertrouwd, "1", VANDAAG, VANDAAG, "", 4000, 840)
    c = logica.voeg_inkoopfactuur_toe(con, vertrouwd, "2", VANDAAG, VANDAAG, "", 50000, 10500)
    d = logica.voeg_inkoopfactuur_toe(con, vertrouwd, "3", VANDAAG, VANDAAG, "", 100, 21,
                                      waarschuwingen=["LET OP: IBAN op factuur wijkt af van bekend IBAN"])
    assert [rij(con, "inkoopfacturen", i)["status"] for i in (a, b, c, d)] == \
        ["ter_goedkeuring", "goedgekeurd", "ter_goedkeuring", "ter_goedkeuring"]
    assert saldo(con, "1600") == -4840                   # automatisch goedgekeurd = automatisch geboekt


# ---------------------------------------------------------------- automatisch inlezen


def ubl_van_leverancier(tmp_path, iban=LEV_IBAN, nummer="LEV-2026-001", kvk="12345678"):
    """Maakt een echte e-factuur zoals een leverancier die zou sturen, met onze eigen UBL-generator."""
    lev = db.verbind(str(tmp_path / f"lev-{nummer}.db"))
    db.initialiseer(lev)
    for k, v in {"bedrijfsnaam": "Leverancier Software B.V.", "iban": iban, "kvk": kvk,
                 "btw_nummer": "NL123456789B01", "email": "factuur@lev.nl"}.items():
        db.zet_instelling(lev, k, v)
    klant = relatie(lev, "Wij B.V.", EIGEN_IBAN, soort="debiteur")
    db.zet_instelling(lev, "factuur_prefix", nummer.split("-")[0])
    fid = logica.maak_verkoopfactuur(lev, klant, [
        {"omschrijving": "Licentie CRM", "aantal": 5, "prijs_cent": 3000, "btw_pct": 21}])
    return factuurdocument.maak_ubl(lev, fid).encode()


def test_e_factuur_wordt_volledig_automatisch_verwerkt(con, tmp_path):
    ubl = ubl_van_leverancier(tmp_path)
    doc_id = intake.ontvang(con, "factuur.xml", ubl, "email", "factuur@lev.nl", "Factuur")
    doc = rij(con, "documenten", doc_id)
    assert doc["status"] == "verwerkt", doc["melding"]
    f = rij(con, "inkoopfacturen", doc["inkoopfactuur_id"])
    assert (f["bedrag_excl_cent"], f["btw_cent"], f["bedrag_incl_cent"]) == (15000, 3150, 18150)
    assert f["bron"] == "email" and f["zekerheid"] == 1.0 and f["bestand"].endswith(".pdf")
    lev = rij(con, "relaties", f["relatie_id"])
    assert (lev["naam"], lev["iban"], lev["kvk"], lev["bron"]) == ("Leverancier Software B.V.", LEV_IBAN, "12345678", "automatisch")
    assert "Nieuwe leverancier" in f["waarschuwingen"]
    # zelfde bestand nogmaals: geen dubbele factuur
    assert intake.ontvang(con, "factuur.xml", ubl, "email") == doc_id
    # zelfde factuur als ander bestand (bijv. opnieuw gemaild): herkend als dubbel, niet nogmaals geboekt
    ander = intake.ontvang(con, "kopie.xml", ubl.replace(b"Licentie CRM", b"Licentie  CRM"), "email")
    assert rij(con, "documenten", ander)["status"] == "genegeerd" and "bestaat al" in rij(con, "documenten", ander)["melding"]
    assert con.execute("SELECT COUNT(*) FROM inkoopfacturen").fetchone()[0] == 1


def test_iban_fraude_wordt_gesignaleerd(con, tmp_path):
    bekend = relatie(con, "Leverancier Software B.V.", LEV_IBAN, limiet=100000, geverifieerd=1)
    con.execute("UPDATE relaties SET kvk = '12345678' WHERE id = ?", (bekend,))
    doc_id = intake.ontvang(con, "f.xml", ubl_van_leverancier(tmp_path, iban=ANDER_IBAN), "email")
    f = rij(con, "inkoopfacturen", rij(con, "documenten", doc_id)["inkoopfactuur_id"])
    assert f["relatie_id"] == bekend and f["status"] == "ter_goedkeuring"      # niet automatisch goedgekeurd
    assert "wijkt af van bekend IBAN" in f["waarschuwingen"]
    assert rij(con, "relaties", bekend)["iban"] == LEV_IBAN                      # IBAN niet overschreven
    logica.beoordeel(con, f["id"], True)
    voorstel = betalen.betaalvoorstel(con)
    assert voorstel[0]["relatie_iban"] == LEV_IBAN                              # betaalt naar bekend IBAN


def test_pdf_via_claude(con, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    gezien = {}

    def nep_claude(inhoud, mediatype, bedrijf, rekeningen):
        gezien.update(mediatype=mediatype, bedrijf=bedrijf, codes=[c for c, _ in rekeningen])
        return {"is_factuur": True, "is_creditnota": False, "leverancier_naam": "KPN B.V.",
                "leverancier_iban": "NL20 INGB 0001 2345 67", "leverancier_kvk": "27124701",
                "leverancier_btw_nummer": "", "leverancier_email": "", "leverancier_adres": "", "leverancier_postcode": "",
                "leverancier_plaats": "Den Haag", "factuurnummer": "KPN-99", "factuurdatum": VANDAAG, "vervaldatum": "",
                "omschrijving": "Zakelijk mobiel", "bedrag_excl": 50.0, "btw_bedrag": 10.5, "bedrag_incl": 60.5,
                "btw_pct": 21, "betalingskenmerk": "", "betaalwijze": "incasso", "grootboekrekening": "4200",
                "zekerheid": 0.97, "opmerkingen": ""}

    monkeypatch.setattr(ai, "lees_factuur", nep_claude)
    doc_id = intake.ontvang(con, "kpn.pdf", b"%PDF-1.4 nep", "upload")
    f = rij(con, "inkoopfacturen", rij(con, "documenten", doc_id)["inkoopfactuur_id"])
    assert gezien["mediatype"] == "application/pdf" and gezien["bedrijf"] == "Wij B.V." and "4200" in gezien["codes"]
    assert (f["rekening"], f["betaalwijze"], f["bedrag_incl_cent"]) == ("4200", "incasso", 6050)
    assert "30 dagen" in f["waarschuwingen"]                                    # vervaldatum ontbrak

    # incasso: niet in betaalvoorstel, wel automatisch afgeletterd bij afschrijving
    logica.beoordeel(con, f["id"], True)
    assert betalen.betaalvoorstel(con) == []
    afschrift = camt([("K1", -6050, "", "KPN BV incasso", "NL11INGB0000000001", "incasso")])
    assert logica.importeer_transacties(con, bankimport.lees_bestand("k.xml", afschrift)) == (1, 1)
    assert rij(con, "inkoopfacturen", f["id"])["status"] == "betaald"


def test_geen_factuur_wordt_genegeerd(con, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(ai, "lees_factuur", lambda *a: {"is_factuur": False})
    doc_id = intake.ontvang(con, "nieuwsbrief.pdf", b"%PDF nieuwsbrief", "email")
    assert rij(con, "documenten", doc_id)["status"] == "genegeerd"


def test_inbox_map(con, tmp_path):
    os.makedirs(intake.INBOX_MAP, exist_ok=True)
    with open(os.path.join(intake.INBOX_MAP, "f.xml"), "wb") as fh:
        fh.write(ubl_van_leverancier(tmp_path))
    planner.ronde(con, "http://localhost")
    assert con.execute("SELECT COUNT(*) FROM inkoopfacturen").fetchone()[0] == 1
    assert os.path.exists(os.path.join(intake.INBOX_MAP, "verwerkt", "f.xml"))


# ---------------------------------------------------------------- betalen


def test_creditnota_wordt_verrekend(con):
    lev = relatie(con, "Lev", LEV_IBAN)
    f = logica.voeg_inkoopfactuur_toe(con, lev, "F1", VANDAAG, VANDAAG, "", 100000, 21000)
    c = logica.voeg_inkoopfactuur_toe(con, lev, "C1", VANDAAG, VANDAAG, "", -20000, -4200,
                                      waarschuwingen=["Creditnota: wordt verrekend"])
    logica.beoordeel(con, f, True)
    logica.beoordeel(con, c, True)
    voorstel = betalen.betaalvoorstel(con)
    assert len(voorstel) == 1 and voorstel[0]["te_betalen_cent"] == 96800
    betalen.maak_betaalopdracht(con, [f])
    logica.importeer_transacties(con, [{"datum": VANDAAG, "bedrag_cent": -96800, "tegenrekening": LEV_IBAN,
                                        "naam": "Lev", "omschrijving": "", "referentie": f"INK-{f}"}])
    assert rij(con, "inkoopfacturen", f)["status"] == "betaald" and rij(con, "inkoopfacturen", c)["status"] == "betaald"
    assert saldo(con, "1600") == 0 and journaal_in_balans(con)


class NepPonto(BaseHTTPRequestHandler):
    """Bootst de Ponto Connect API na zoals ponto.py hem aanroept."""
    staat = {}

    def log_message(self, *a):
        pass

    def _antwoord(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/vnd.api+json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/oauth2/token":
            assert self.headers["Authorization"].startswith("Basic ")
            return self._antwoord({"access_token": "AT", "refresh_token": "RT", "expires_in": 1800})
        assert self.headers["Authorization"] == "Bearer AT"
        if self.path == "/synchronizations":
            return self._antwoord({"data": {"id": "s1"}})
        if self.path.endswith("/bulk-payments"):
            NepPonto.staat["bulk"] = json.loads(body)["data"]["attributes"]
            return self._antwoord({"data": {"id": "bp1", "attributes": {"status": "unsigned"},
                                            "links": {"redirect": "https://ponto.test/sign/bp1"}}})
        self._antwoord({}, 404)

    def do_GET(self):
        if self.path == "/accounts":
            return self._antwoord({"data": [{"id": "acc1", "attributes": {"reference": EIGEN_IBAN,
                                                                          "availableForPayments": True}}]})
        if self.path == "/synchronizations/s1":
            return self._antwoord({"data": {"attributes": {"status": "success"}}})
        if self.path == "/accounts/acc1/bulk-payments/bp1":
            return self._antwoord({"data": {"attributes": {"status": NepPonto.staat.get("status", "unsigned")}}})
        if self.path.startswith("/accounts/acc1/transactions"):
            return self._antwoord({"data": [{"id": "t1", "attributes": {
                "valueDate": f"{VANDAAG}T00:00:00Z", "amount": -121.0, "counterpartName": "Lev",
                "counterpartReference": LEV_IBAN, "remittanceInformation": "Factuur F1", "endToEndId": "INK-1"}}],
                "links": {}})
        self._antwoord({}, 404)


def test_goedkeuren_zet_betaling_klaar_in_abn_via_ponto(con, monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), NepPonto)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("PONTO_CLIENT_ID", "id")
    monkeypatch.setenv("PONTO_CLIENT_SECRET", "geheim")
    monkeypatch.setenv("PONTO_API_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("PONTO_AUTORISATIE_URL", "https://ponto.test/auth")
    db.zet_instelling(con, "betaalmoment", "direct")
    try:
        url = ponto.autorisatie_url(con, "http://localhost/terug")
        assert "code_challenge=" in url and "scope=ai+pi+offline_access" in url
        state = url.split("state=")[1].split("&")[0]
        ponto.verwerk_terugkeer(con, "CODE", state)
        ponto.kies_rekening(con, EIGEN_IBAN)
        assert betalen.ponto_actief(con)

        lev = relatie(con, "Lev", LEV_IBAN)
        fid = logica.voeg_inkoopfactuur_toe(con, lev, "F1", VANDAAG, VANDAAG, "", 10000, 2100, "1234567890123456")
        logica.beoordeel(con, fid, True)
        batch_id, sign_url = betalen.na_goedkeuring(con, [fid], "http://localhost/betalingen/terug")
        assert sign_url == "https://ponto.test/sign/bp1"
        bulk = NepPonto.staat["bulk"]
        assert bulk["requestedExecutionDate"] == VANDAAG
        assert bulk["payments"][0] == {"remittanceInformation": "1234567890123456", "remittanceInformationType": "structured",
                                       "currency": "EUR", "amount": 121.0, "creditorName": "Lev",
                                       "creditorAccountReference": LEV_IBAN, "creditorAccountReferenceType": "IBAN",
                                       "endToEndId": f"INK-{fid}"}
        assert rij(con, "betaalbatches", batch_id)["status"] == "ter_ondertekening"

        NepPonto.staat["status"] = "accepted-technical-validation"
        betalen.werk_status_bij(con)
        assert rij(con, "betaalbatches", batch_id)["status"] == "ondertekend"

        assert planner.haal_bank_op(con) == (1, 1)                              # mutaties automatisch opgehaald
        assert rij(con, "inkoopfacturen", fid)["status"] == "betaald"
    finally:
        server.shutdown()


def test_geweigerde_betaling_gaat_terug_naar_voorstel(con, monkeypatch):
    lev = relatie(con, "Lev", LEV_IBAN)
    fid = logica.voeg_inkoopfactuur_toe(con, lev, "F1", VANDAAG, VANDAAG, "", 1000, 210)
    logica.beoordeel(con, fid, True)
    batch, _ = betalen.maak_betaalopdracht(con, [fid])
    betalen.annuleer(con, batch, "geweigerd")
    assert rij(con, "inkoopfacturen", fid)["status"] == "goedgekeurd"
    assert [v["id"] for v in betalen.betaalvoorstel(con)] == [fid]


# ---------------------------------------------------------------- verkoop, btw, rapportages, mail


def test_verkoop_btw_en_rapportages(con):
    klant = relatie(con, "Klant B.V.", KLANT_IBAN, soort="debiteur")
    fid = logica.maak_verkoopfactuur(con, klant, [
        {"omschrijving": "Belcampagne", "aantal": 10, "prijs_cent": 5000, "btw_pct": 21},
        {"omschrijving": "Boek", "aantal": 1, "prijs_cent": 1000, "btw_pct": 9}])
    t = logica.verkoop_totalen(con, fid)
    assert (t["excl"], t["btw"], t["incl"]) == (51000, {21: 10500, 9: 90}, 61590)
    assert saldo(con, "1300") == 0                       # concept wordt niet geboekt
    logica.zet_verkoopstatus(con, fid, "verzonden")
    assert saldo(con, "1300") == 61590 and saldo(con, "8000") == -50000 and saldo(con, "1521") == -90

    nummer = rij(con, "verkoopfacturen", fid)["factuurnummer"]
    csv_ing = ('"Datum";"Naam / Omschrijving";"Rekening";"Tegenrekening";"Code";"Af Bij";"Bedrag (EUR)";'
               '"Mutatiesoort";"Mededelingen"\n'
               f'"{date.today():%Y%m%d}";"Klant B.V.";"{EIGEN_IBAN}";"{KLANT_IBAN}";"OV";"Bij";"615,90";'
               f'"Overschrijving";"Betaling {nummer}"\n')
    assert logica.importeer_transacties(con, bankimport.lees_bestand("ing.csv", csv_ing.encode())) == (1, 1)
    assert rij(con, "verkoopfacturen", fid)["status"] == "betaald" and saldo(con, "1300") == 0

    lev = relatie(con, "Lev", LEV_IBAN)
    ink = logica.voeg_inkoopfactuur_toe(con, lev, "I1", VANDAAG, VANDAAG, "", 20000, 4200, rekening="4300")
    logica.beoordeel(con, ink, True)
    logica.importeer_transacties(con, [{"datum": VANDAAG, "bedrag_cent": -250, "tegenrekening": "",
                                        "naam": "ABN AMRO", "omschrijving": "Kosten betaalpakket"}])
    logica.boek_op_rekening(con, con.execute("SELECT id FROM banktransacties WHERE bedrag_cent = -250").fetchone()[0], "4800")

    q = (date.today().month - 1) // 3 + 1
    btw = logica.btw_overzicht(con, date.today().year, q)
    r = btw["aangifte"]["rubrieken"]
    assert (r["1a"]["omzet"], r["1a"]["btw"], r["1b"]["omzet"], r["1b"]["btw"]) == (50000, 10500, 1000, 90)
    assert btw["voorbelasting"] == 4200 and btw["te_betalen"] == 10590 - 4200

    wv = grootboek.winst_en_verlies(con, date.today().year)
    assert (wv["totaal_opbrengsten"], wv["totaal_kosten"], wv["resultaat"]) == (51000, 20250, 30750)
    bal = grootboek.balans(con, (date.today() + timedelta(days=1)).isoformat())
    assert bal["totaal_activa"] == bal["totaal_passiva"]
    assert journaal_in_balans(con)


def test_pdf_ubl_en_mail(con, monkeypatch):
    verstuurd = []

    class NepSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, m): verstuurd.append(m)

    monkeypatch.setattr(mail.smtplib, "SMTP", NepSMTP)
    for k, v in {"SMTP_HOST": "smtp.test", "SMTP_GEBRUIKER": "u@wij.nl", "SMTP_WACHTWOORD": "x"}.items():
        monkeypatch.setenv(k, v)
    klant = relatie(con, "Klant", KLANT_IBAN, soort="debiteur", email="klant@test.nl")
    fid = logica.maak_verkoopfactuur(con, klant, [{"omschrijving": "Uren", "aantal": 2, "prijs_cent": 7500, "btw_pct": 21}],
                                     (date.today() - timedelta(days=40)).isoformat())
    assert factuurdocument.maak_pdf(con, fid).startswith(b"%PDF")
    assert intake.lees_ubl(factuurdocument.maak_ubl(con, fid).encode())["incl"] == 18150   # eigen e-factuur is leesbaar

    mail.verstuur_verkoopfactuur(con, fid)
    assert rij(con, "verkoopfacturen", fid)["status"] == "verzonden"
    namen = [d.get_filename() for d in verstuurd[0].iter_attachments()]
    assert namen[0].endswith(".pdf") and namen[1].endswith(".xml")

    db.zet_instelling(con, "email", "ik@wij.nl")
    assert mail.stuur_herinneringen(con) == 1            # 40 dagen oud, termijn 14 -> 1e herinnering
    assert mail.stuur_herinneringen(con) == 1            # ook al voorbij 2e herinneringsmoment (21 dagen)
    assert mail.stuur_herinneringen(con) == 0
    assert "Tweede herinnering" in verstuurd[-1]["Subject"]
    assert mail.stuur_samenvatting(con, "http://localhost") is True
    assert "te laat" in verstuurd[-1].get_content()


# ---------------------------------------------------------------- schermen


def test_webschermen(tmp_path, monkeypatch):
    monkeypatch.setattr(intake, "UPLOAD_MAP", str(tmp_path / "uploads"))
    from app import app
    app.config.update(TESTING=True, DATABASE=str(tmp_path / "web.db"))
    web = app.test_client()
    web.post("/instellingen", data={**db.STANDAARD_INSTELLINGEN, "iban": EIGEN_IBAN})
    web.post("/relaties/nieuw", data={"naam": "Leverancier", "soort": "beide", "iban": LEV_IBAN,
                                      "auto_goedkeur_limiet": "0", "email": "a@b.nl"})
    r = web.post("/inkoop/nieuw", data={
        "relatie_id": "1", "factuurnummer": "X1", "factuurdatum": VANDAAG, "vervaldatum": VANDAAG,
        "bedrag_excl": "100,00", "btw_pct": "21", "rekening": "4300", "betaalwijze": "overboeking",
        "bestand": (io.BytesIO(b"%PDF-1.4"), "factuur.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 302
    r = web.post("/inbox", data={"bestanden": [(io.BytesIO(ubl_van_leverancier(tmp_path)), "e.xml")]},
                 content_type="multipart/form-data")
    assert r.status_code == 302
    assert b"121,00" in web.get("/goedkeuren").data and b"181,50" in web.get("/goedkeuren").data
    web.post("/goedkeuren", data={"ids": "1", "actie": "goedkeuren", "rekening_1": "4300"})
    r = web.post("/betalingen/opdracht", data={"ids": "1"})
    assert "nieuw=1" in r.headers["Location"]
    assert b"pain.001.001.03" in web.get("/betalingen/batch/1.xml").data
    web.post("/verkoop/nieuw", data={"relatie_id": "1", "omschrijving": ["Uren"], "aantal": ["2"],
                                     "prijs": ["75"], "btw_pct": ["21"]})
    web.post("/verkoop/1/status", data={"status": "verzonden"})
    web.post("/bank", data={"afschrift": (io.BytesIO(camt([("W1", -12100, "INK-1", "Leverancier", LEV_IBAN, "")])), "a.xml")},
             content_type="multipart/form-data")
    for pad in ("/", "/inbox", "/relaties", "/relaties/1", "/relaties/nieuw", "/inkoop", "/inkoop?status=betaald",
                "/inkoop/1", "/inkoop/2", "/inkoop/nieuw", "/goedkeuren", "/betalingen", "/verkoop", "/verkoop/nieuw",
                "/verkoop/1", "/verkoop/1.pdf", "/verkoop/1.xml", "/bank", "/bank?filter=alle", "/grootboek",
                "/grootboek/4300", "/rapportages", "/btw", "/logboek", "/instellingen"):
        assert web.get(pad).status_code == 200, pad
    assert b"betaald" in web.get("/inkoop/1").data
    assert b"181,50" in web.get("/verkoop/1").data
    r = web.get("/koppelen/ponto")                       # niet ingesteld -> nette melding, geen crash
    assert r.status_code == 302

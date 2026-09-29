"""Automatische verwerking van inkomende facturen.

Bronnen: upload in de app, een mailbox (IMAP) en een map op je computer (data/inbox).
Herkenning: e-facturen (UBL-XML) exact, pdf's en foto's via Claude, anders eenvoudige tekstherkenning.
Daarna: leverancier zoeken of aanmaken, fraudecontrole op het IBAN, grootboekrekening kiezen en
de factuur klaarzetten (of automatisch goedkeuren als alles klopt)."""

import email
import hashlib
import imaplib
import mimetypes
import os
import re
import secrets
import shutil
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr

import ai
import grootboek
import logica
from db import MAP, instellingen, log, nu

UPLOAD_MAP = os.path.join(MAP, "uploads")
INBOX_MAP = os.path.join(MAP, "data", "inbox")
TOEGESTAAN = {".pdf": "application/pdf", ".xml": "application/xml", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


# ---------------------------------------------------------------- documenten ontvangen


def ontvang(con, bestandsnaam, inhoud, bron="upload", afzender="", onderwerp=""):
    """Slaat een document op en verwerkt het direct. Geeft het document-id terug (bestaand bij dubbel)."""
    ext = os.path.splitext(bestandsnaam)[1].lower()
    if ext not in TOEGESTAAN:
        raise ValueError(f"{bestandsnaam}: alleen pdf, xml (e-factuur) of foto's worden verwerkt")
    hash_ = hashlib.sha256(inhoud).hexdigest()
    bestaand = con.execute("SELECT id FROM documenten WHERE hash = ?", (hash_,)).fetchone()
    if bestaand:
        return bestaand["id"]
    os.makedirs(UPLOAD_MAP, exist_ok=True)
    veilig = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(bestandsnaam))[-80:]
    opslag = f"{secrets.token_hex(4)}-{veilig}"
    with open(os.path.join(UPLOAD_MAP, opslag), "wb") as f:
        f.write(inhoud)
    doc_id = con.execute(
        "INSERT INTO documenten (bestandsnaam, opslag, bron, afzender, onderwerp, hash, ontvangen_op) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (bestandsnaam, opslag, bron, afzender, onderwerp, hash_, nu())).lastrowid
    log(con, "document ontvangen", "document", doc_id, f"{bestandsnaam} via {bron}")
    con.commit()
    verwerk(con, doc_id)
    return doc_id


def verwerk(con, doc_id):
    doc = con.execute("SELECT * FROM documenten WHERE id = ?", (doc_id,)).fetchone()
    pad = os.path.join(UPLOAD_MAP, doc["opslag"])
    try:
        with open(pad, "rb") as f:
            inhoud = f.read()
        gegevens = herken(con, doc["bestandsnaam"], inhoud)
        if gegevens is None:
            con.execute("UPDATE documenten SET status = 'genegeerd', melding = ? WHERE id = ?",
                        ("Geen factuur herkend", doc_id))
            con.commit()
            return None
        if gegevens.get("pdf_bijlage"):  # pdf-weergave uit een e-factuur
            opslag = doc["opslag"].rsplit(".", 1)[0] + ".pdf"
            with open(os.path.join(UPLOAD_MAP, opslag), "wb") as f:
                f.write(gegevens["pdf_bijlage"])
            gegevens["bestand"] = opslag
        fid = maak_inkoopfactuur(con, gegevens, doc)
        con.execute("UPDATE documenten SET status = 'verwerkt', melding = NULL, inkoopfactuur_id = ? WHERE id = ?",
                    (fid, doc_id))
        con.commit()
        return fid
    except ValueError as e:
        con.rollback()
        if "bestaat al" not in str(e):
            return _fout(con, doc_id, e)
        con.execute("UPDATE documenten SET status = 'genegeerd', melding = ? WHERE id = ?",
                    (f"Dubbel: {e}", doc_id))
        con.commit()
        return None
    except Exception as e:  # noqa: BLE001 - elk probleem moet zichtbaar worden in de inbox
        return _fout(con, doc_id, e)


def _fout(con, doc_id, e):
    con.rollback()
    con.execute("UPDATE documenten SET status = 'fout', melding = ? WHERE id = ?", (str(e)[:500], doc_id))
    log(con, "document niet verwerkt", "document", doc_id, str(e)[:200])
    con.commit()
    return None


# ---------------------------------------------------------------- herkennen


def herken(con, bestandsnaam, inhoud):
    ext = os.path.splitext(bestandsnaam)[1].lower()
    if ext == ".xml":
        return lees_ubl(inhoud)
    mediatype = TOEGESTAAN[ext]
    if ai.beschikbaar():
        inst = instellingen(con)
        rekeningen = [(r["code"], r["naam"]) for r in grootboek.kostenrekeningen(con)]
        d = ai.lees_factuur(inhoud, mediatype, inst["bedrijfsnaam"], rekeningen)
        if not d["is_factuur"]:
            return None
        teken = -1 if d["is_creditnota"] else 1
        return {
            "methode": "Claude",
            "leverancier": {"naam": d["leverancier_naam"], "iban": d["leverancier_iban"], "kvk": d["leverancier_kvk"],
                            "btw_nummer": d["leverancier_btw_nummer"], "email": d["leverancier_email"],
                            "adres": d["leverancier_adres"], "postcode": d["leverancier_postcode"],
                            "plaats": d["leverancier_plaats"]},
            "factuurnummer": d["factuurnummer"], "factuurdatum": d["factuurdatum"], "vervaldatum": d["vervaldatum"],
            "omschrijving": d["omschrijving"],
            "excl": teken * abs(logica.naar_cent(d["bedrag_excl"])), "btw": teken * abs(logica.naar_cent(d["btw_bedrag"])),
            "incl": teken * abs(logica.naar_cent(d["bedrag_incl"])),
            "btw_pct": d["btw_pct"], "kenmerk": d["betalingskenmerk"], "betaalwijze": d["betaalwijze"],
            "rekening": d["grootboekrekening"], "zekerheid": max(0.0, min(1.0, float(d["zekerheid"]))),
            "opmerkingen": d["opmerkingen"], "creditnota": d["is_creditnota"],
        }
    if mediatype == "application/pdf":
        return lees_pdf_tekst(inhoud)
    raise ValueError("Foto's kunnen alleen worden gelezen met Claude (ANTHROPIC_API_KEY in config.env)")


def _x(el, pad, ns):
    gevonden = el.find(pad, ns) if el is not None else None
    return (gevonden.text or "").strip() if gevonden is not None and gevonden.text else ""


def lees_ubl(inhoud):
    """E-factuur volgens UBL 2.1 / SI-UBL 2.0 (NLCIUS) / Peppol BIS: exact, zonder te hoeven gokken."""
    root = ET.fromstring(inhoud)
    tag = root.tag.split("}")[-1]
    if tag not in ("Invoice", "CreditNote"):
        return None
    ns = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
          "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    lev = root.find("cac:AccountingSupplierParty/cac:Party", ns)
    kvk = ""
    for eid in lev.findall("cac:PartyLegalEntity/cbc:CompanyID", ns) if lev is not None else []:
        if eid.get("schemeID") in (None, "0106", "NL:KVK"):
            kvk = (eid.text or "").strip()
    betaal = root.find("cac:PaymentMeans", ns)
    code = _x(betaal, "cbc:PaymentMeansCode", ns)
    totaal = root.find("cac:LegalMonetaryTotal", ns)
    excl = logica.naar_cent(_x(totaal, "cbc:TaxExclusiveAmount", ns))
    incl = logica.naar_cent(_x(totaal, "cbc:TaxInclusiveAmount", ns))
    te_betalen = _x(totaal, "cbc:PayableAmount", ns)
    btw = logica.naar_cent(_x(root, "cac:TaxTotal/cbc:TaxAmount", ns)) or incl - excl
    tarieven = [float(p.text) for p in root.findall("cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent", ns)
                if p.text]
    omschrijving = ", ".join(n.text.strip() for n in root.findall("cac:InvoiceLine/cac:Item/cbc:Name", ns)
                             + root.findall("cac:CreditNoteLine/cac:Item/cbc:Name", ns) if n.text)[:200]
    pdf = None
    for obj in root.findall("cac:AdditionalDocumentReference/cac:Attachment/cbc:EmbeddedDocumentBinaryObject", ns):
        if obj.get("mimeCode") == "application/pdf" and obj.text:
            import base64
            pdf = base64.b64decode(obj.text)
            break
    teken = -1 if tag == "CreditNote" else 1
    return {
        "methode": "e-factuur (UBL)",
        "leverancier": {
            "naam": _x(lev, "cac:PartyName/cbc:Name", ns) or _x(lev, "cac:PartyLegalEntity/cbc:RegistrationName", ns),
            "iban": _x(betaal, "cac:PayeeFinancialAccount/cbc:ID", ns), "kvk": kvk,
            "btw_nummer": _x(lev, "cac:PartyTaxScheme/cbc:CompanyID", ns),
            "email": _x(lev, "cac:Contact/cbc:ElectronicMail", ns),
            "adres": _x(lev, "cac:PostalAddress/cbc:StreetName", ns),
            "postcode": _x(lev, "cac:PostalAddress/cbc:PostalZone", ns),
            "plaats": _x(lev, "cac:PostalAddress/cbc:CityName", ns)},
        "factuurnummer": _x(root, "cbc:ID", ns),
        "factuurdatum": _x(root, "cbc:IssueDate", ns),
        "vervaldatum": _x(root, "cbc:DueDate", ns) or _x(betaal, "cbc:PaymentDueDate", ns),
        "omschrijving": omschrijving,
        "excl": teken * abs(excl), "btw": teken * abs(btw),
        "incl": teken * abs(logica.naar_cent(te_betalen) if te_betalen else incl),
        "btw_pct": int(max(tarieven)) if tarieven else 21,
        "kenmerk": _x(betaal, "cbc:PaymentID", ns),
        "betaalwijze": "incasso" if code in ("49", "59") else "overboeking",
        "rekening": None, "zekerheid": 1.0, "opmerkingen": "", "creditnota": tag == "CreditNote",
        "pdf_bijlage": pdf,
    }


IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?)\b")
BEDRAG = r"€?\s*(-?\d{1,3}(?:[.\s]\d{3})*,\d{2}|-?\d+[.,]\d{2})"


def lees_pdf_tekst(inhoud):
    """Noodoplossing zonder Claude: zoekt de belangrijkste velden met patronen. Altijd handmatig controleren."""
    import io
    from pypdf import PdfReader

    tekst = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(inhoud)).pages)
    if len(tekst.strip()) < 20:
        raise ValueError("Deze pdf is een scan zonder tekst; zet een ANTHROPIC_API_KEY in config.env om scans te lezen")

    def zoek(patroon):
        m = re.search(patroon, tekst, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    def datum(label):
        s = zoek(label + r"[^\d]{0,20}(\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{4}-\d{2}-\d{2})")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", s)
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""

    ibans = [logica.normaliseer_iban(i) for i in IBAN_RE.findall(tekst)]
    incl = logica.naar_cent(zoek(r"(?:totaal\s*(?:incl|te betalen)[^\d€-]*|te betalen[^\d€-]*)" + BEDRAG) or "0")
    btw = logica.naar_cent(zoek(r"(?:btw|vat)[^\d€\n-]{0,25}" + BEDRAG) or "0")
    regels = [r.strip() for r in tekst.splitlines() if r.strip()]
    return {
        "methode": "tekstherkenning",
        "leverancier": {"naam": regels[0][:80] if regels else "Onbekende leverancier",
                        "iban": next((i for i in ibans if logica.iban_geldig(i)), ""),
                        "kvk": zoek(r"k\.?v\.?k\.?[^\d]{0,10}(\d{8})"),
                        "btw_nummer": zoek(r"\b(NL\d{9}B\d{2})\b"), "email": "", "adres": "", "postcode": "", "plaats": ""},
        "factuurnummer": zoek(r"factuur\s*(?:nummer|nr\.?)\s*:?\s*([A-Z0-9][A-Z0-9\-/.]{1,30})"),
        "factuurdatum": datum("factuurdatum") or datum("datum"),
        "vervaldatum": datum("vervaldatum"),
        "omschrijving": "",
        "excl": incl - btw, "btw": btw, "incl": incl, "btw_pct": 21,
        "kenmerk": zoek(r"betalingskenmerk\s*:?\s*([\d\s]{16,19})").replace(" ", ""),
        "betaalwijze": "incasso" if re.search(r"ge[iï]ncasseerd|automatische incasso", tekst, re.I) else "overboeking",
        "rekening": None, "zekerheid": 0.4, "opmerkingen": "Automatisch gelezen zonder AI: controleer alle velden.",
        "creditnota": False,
    }


# ---------------------------------------------------------------- leverancier & boeken


def _naam_sleutel(naam):
    naam = re.sub(r"\b(b\.?v\.?|n\.?v\.?|v\.?o\.?f\.?|holding|nederland)\b", "", (naam or "").lower())
    return re.sub(r"[^a-z0-9]", "", naam)


def zoek_of_maak_relatie(con, lev):
    """Geeft (relatie_id, waarschuwingen). Wijzigt NOOIT automatisch het IBAN van een bestaande leverancier."""
    iban = logica.normaliseer_iban(lev.get("iban"))
    kvk = re.sub(r"\D", "", lev.get("kvk") or "")
    btw_nr = re.sub(r"\s", "", (lev.get("btw_nummer") or "").upper())
    relaties = con.execute("SELECT * FROM relaties WHERE soort IN ('crediteur', 'beide')").fetchall()
    gevonden = (next((r for r in relaties if iban and logica.normaliseer_iban(r["iban"]) == iban), None)
                or next((r for r in relaties if kvk and re.sub(r"\D", "", r["kvk"] or "") == kvk), None)
                or next((r for r in relaties if btw_nr and re.sub(r"\s", "", (r["btw_nummer"] or "").upper()) == btw_nr), None)
                or next((r for r in relaties if _naam_sleutel(lev.get("naam")) and
                         _naam_sleutel(r["naam"]) == _naam_sleutel(lev.get("naam"))), None))
    waarschuwingen = []
    if gevonden:
        bekend = logica.normaliseer_iban(gevonden["iban"])
        if iban and bekend and iban != bekend:
            waarschuwingen.append(f"LET OP: IBAN op factuur ({iban}) wijkt af van bekend IBAN ({bekend}). "
                                  "We betalen altijd naar het bekende IBAN. Klopt de wijziging? Bel de leverancier op een bekend "
                                  "nummer en pas het IBAN daarna aan bij de relatie (bescherming tegen factuurfraude).")
        elif iban and not bekend:
            con.execute("UPDATE relaties SET iban = ? WHERE id = ?", (iban, gevonden["id"]))
            waarschuwingen.append(f"IBAN {iban} toegevoegd aan {gevonden['naam']}; nog niet geverifieerd.")
        # vul lege gegevens aan, overschrijf nooit bestaande
        for veld in ("kvk", "btw_nummer", "email", "adres", "postcode", "plaats"):
            if lev.get(veld) and not gevonden[veld]:
                con.execute(f"UPDATE relaties SET {veld} = ? WHERE id = ?", (lev[veld], gevonden["id"]))
        return gevonden["id"], waarschuwingen

    if iban and not logica.iban_geldig(iban):
        waarschuwingen.append(f"IBAN {iban} op de factuur is ongeldig.")
        iban = ""
    rid = con.execute(
        "INSERT INTO relaties (naam, soort, email, iban, adres, postcode, plaats, kvk, btw_nummer, bron, aangemaakt_op) "
        "VALUES (?, 'crediteur', ?, ?, ?, ?, ?, ?, ?, 'automatisch', ?)",
        (lev.get("naam") or "Onbekende leverancier", lev.get("email"), iban, lev.get("adres"), lev.get("postcode"),
         lev.get("plaats"), kvk, btw_nr, nu())).lastrowid
    log(con, "leverancier automatisch aangemaakt", "relatie", rid, lev.get("naam") or "")
    waarschuwingen.append("Nieuwe leverancier: controleer naam en IBAN bij de eerste factuur.")
    return rid, waarschuwingen


def kies_rekening(con, relatie_id, voorstel):
    rel = con.execute("SELECT standaard_rekening FROM relaties WHERE id = ?", (relatie_id,)).fetchone()
    if rel["standaard_rekening"]:
        return rel["standaard_rekening"]
    vorige = con.execute("SELECT rekening FROM inkoopfacturen WHERE relatie_id = ? AND rekening IS NOT NULL "
                         "AND status != 'afgekeurd' ORDER BY id DESC LIMIT 1", (relatie_id,)).fetchone()
    if vorige:
        return vorige["rekening"]
    if voorstel and con.execute("SELECT 1 FROM grootboekrekeningen WHERE code = ?", (voorstel,)).fetchone():
        return voorstel
    return grootboek.standaard_kostenrekening(con)


def maak_inkoopfactuur(con, g, doc):
    relatie_id, waarschuwingen = zoek_of_maak_relatie(con, g["leverancier"])
    vandaag = date.today()
    factuurdatum = g["factuurdatum"] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", g["factuurdatum"] or "") else ""
    if not factuurdatum:
        factuurdatum = vandaag.isoformat()
        waarschuwingen.append("Factuurdatum niet gevonden; datum van vandaag gebruikt.")
    elif factuurdatum > (vandaag + timedelta(days=7)).isoformat():
        waarschuwingen.append(f"Factuurdatum {factuurdatum} ligt in de toekomst.")
    vervaldatum = g["vervaldatum"] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", g["vervaldatum"] or "") else ""
    if not vervaldatum:
        vervaldatum = (date.fromisoformat(factuurdatum) + timedelta(days=30)).isoformat()
        waarschuwingen.append("Geen vervaldatum op de factuur; 30 dagen aangehouden.")
    nummer = (g["factuurnummer"] or "").strip()
    if not nummer:
        nummer = f"ONBEKEND-{doc['id']}"
        waarschuwingen.append("Factuurnummer niet gevonden.")
    if abs(g["excl"] + g["btw"] - g["incl"]) > 2:
        waarschuwingen.append(f"Bedragen tellen niet op: {logica.euro(g['excl'])} + {logica.euro(g['btw'])} "
                              f"≠ {logica.euro(g['incl'])}.")
    if not g["incl"]:
        waarschuwingen.append("Geen totaalbedrag gevonden.")
    if g["zekerheid"] < 0.85:
        waarschuwingen.append(f"Automatisch gelezen met lage zekerheid ({round(g['zekerheid'] * 100)}%): controleer de velden.")
    if g["creditnota"]:
        waarschuwingen.append("Creditnota: wordt niet uitbetaald maar verrekend met een volgende betaling of terugbetaling.")
    if g["betaalwijze"] == "incasso":
        waarschuwingen.append("Wordt geïncasseerd door de leverancier: niet zelf betalen.")
    elif g["betaalwijze"] == "al_betaald":
        waarschuwingen.append("Factuur is al betaald (bijv. creditcard of iDEAL).")
    if g.get("opmerkingen"):
        waarschuwingen.append(g["opmerkingen"])

    return logica.voeg_inkoopfactuur_toe(
        con, relatie_id, nummer, factuurdatum, vervaldatum, g["omschrijving"] or "",
        g["incl"] - g["btw"], g["btw"], g["kenmerk"] or "",
        bestand=g.get("bestand") or doc["opslag"], rekening=kies_rekening(con, relatie_id, g.get("rekening")),
        bron=doc["bron"], zekerheid=g["zekerheid"], waarschuwingen=waarschuwingen, document_id=doc["id"],
        betaalwijze=g["betaalwijze"], methode=g["methode"])


# ---------------------------------------------------------------- mailbox & map


def mailbox_ingesteld():
    return all(os.environ.get(k) for k in ("IMAP_HOST", "IMAP_GEBRUIKER", "IMAP_WACHTWOORD"))


def _decodeer(waarde):
    return str(make_header(decode_header(waarde or "")))


def haal_mail_op(con):
    """Leest ongelezen mails in de factuurmailbox, verwerkt pdf/xml/foto-bijlagen en markeert ze als gelezen."""
    if not mailbox_ingesteld():
        return 0
    aantal = 0
    with imaplib.IMAP4_SSL(os.environ["IMAP_HOST"], int(os.environ.get("IMAP_POORT", 993))) as imap:
        imap.login(os.environ["IMAP_GEBRUIKER"], os.environ["IMAP_WACHTWOORD"])
        imap.select(os.environ.get("IMAP_MAP", "INBOX"))
        _, data = imap.search(None, "UNSEEN")
        for num in data[0].split():
            _, delen = imap.fetch(num, "(RFC822)")
            bericht = email.message_from_bytes(delen[0][1])
            afzender = parseaddr(bericht.get("From"))[1]
            onderwerp = _decodeer(bericht.get("Subject"))
            for deel in bericht.walk():
                naam = deel.get_filename()
                if not naam:
                    continue
                naam = _decodeer(naam)
                if os.path.splitext(naam)[1].lower() in TOEGESTAAN:
                    ontvang(con, naam, deel.get_payload(decode=True), "email", afzender, onderwerp)
                    aantal += 1
            imap.store(num, "+FLAGS", "\\Seen")
            if os.environ.get("IMAP_VERWERKT_MAP"):
                if imap.copy(num, os.environ["IMAP_VERWERKT_MAP"])[0] == "OK":
                    imap.store(num, "+FLAGS", "\\Deleted")
        imap.expunge()
    return aantal


def verwerk_map(con):
    """Bestanden die je in data/inbox sleept worden verwerkt en daarna verplaatst naar data/inbox/verwerkt."""
    os.makedirs(os.path.join(INBOX_MAP, "verwerkt"), exist_ok=True)
    aantal = 0
    for naam in sorted(os.listdir(INBOX_MAP)):
        pad = os.path.join(INBOX_MAP, naam)
        if not os.path.isfile(pad) or naam.startswith(".") or os.path.splitext(naam)[1].lower() not in TOEGESTAAN:
            continue
        with open(pad, "rb") as f:
            ontvang(con, naam, f.read(), "map")
        shutil.move(pad, os.path.join(INBOX_MAP, "verwerkt", naam))
        aantal += 1
    return aantal


def raad_mediatype(naam):
    return TOEGESTAAN.get(os.path.splitext(naam)[1].lower()) or mimetypes.guess_type(naam)[0]

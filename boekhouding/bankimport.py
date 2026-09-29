"""Inlezen van bankafschriften: CAMT.053 (XML, alle NL banken) en CSV (ING, Rabobank of eenvoudig)."""

import csv
import io
import re
import xml.etree.ElementTree as ET

from logica import naar_cent


def _zonder_ns(root):
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _t(el, pad):
    if el is None:
        return ""
    gevonden = el.find(pad)
    return (gevonden.text or "").strip() if gevonden is not None else ""


def lees_camt053(inhoud):
    root = _zonder_ns(ET.fromstring(inhoud))
    resultaat = []
    for ntry in root.iter("Ntry"):
        cent = naar_cent(_t(ntry, "Amt"))
        credit = _t(ntry, "CdtDbtInd") == "CRDT"
        tx = ntry.find("NtryDtls/TxDtls")
        tegenpartij = "Dbtr" if credit else "Cdtr"
        omschrijving = " ".join(u.text.strip() for u in ntry.iter("Ustrd") if u.text) or _t(ntry, "AddtlNtryInf")
        kenmerk = _t(tx, "RmtInf/Strd/CdtrRefInf/Ref")
        resultaat.append({
            "datum": (_t(ntry, "BookgDt/Dt") or _t(ntry, "BookgDt/DtTm"))[:10],
            "bedrag_cent": cent if credit else -cent,
            "tegenrekening": _t(tx, f"RltdPties/{tegenpartij}Acct/Id/IBAN"),
            "naam": _t(tx, f"RltdPties/{tegenpartij}/Nm"),
            "omschrijving": " ".join(x for x in (omschrijving, kenmerk) if x),
            "referentie": _t(tx, "Refs/EndToEndId"),
            "import_sleutel": _t(ntry, "AcctSvcrRef") or _t(tx, "Refs/AcctSvcrRef") or None,
        })
    return resultaat


def _datum(s):
    s = s.strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    m = re.fullmatch(r"(\d{2})[-/](\d{2})[-/](\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return s[:10]


def lees_csv(inhoud):
    tekst = inhoud.decode("utf-8-sig", errors="replace") if isinstance(inhoud, bytes) else inhoud
    dialect = csv.Sniffer().sniff(tekst.splitlines()[0], delimiters=",;\t")
    rijen = list(csv.DictReader(io.StringIO(tekst), dialect=dialect))
    resultaat = []
    for r in rijen:
        k = {key.strip().lower(): (v or "").strip() for key, v in r.items() if key}
        if "af bij" in k:                                   # ING
            cent = naar_cent(k.get("bedrag (eur)"))
            cent = -cent if k["af bij"].lower() == "af" else cent
            naam = k.get("naam / omschrijving", "")
            omschr = k.get("mededelingen", "")
        elif "naam tegenpartij" in k:                       # Rabobank
            cent = naar_cent(k.get("bedrag"))
            naam = k["naam tegenpartij"]
            omschr = " ".join(k.get(f"omschrijving-{i}", "") for i in (1, 2, 3)).strip()
        else:                                               # eenvoudig formaat
            cent = naar_cent(k.get("bedrag"))
            naam = k.get("naam", "")
            omschr = k.get("omschrijving", "")
        resultaat.append({
            "datum": _datum(k.get("datum", "")),
            "bedrag_cent": cent,
            "tegenrekening": k.get("tegenrekening") or k.get("tegenrekening iban/bban") or "",
            "naam": naam,
            "omschrijving": omschr,
            "referentie": k.get("end-to-end id") or k.get("referentie") or "",
            "import_sleutel": (f"rabo-{k['volgnr']}-{k.get('iban/bban', '')}" if k.get("volgnr") else None),
        })
    return resultaat


def lees_bestand(bestandsnaam, inhoud):
    if bestandsnaam.lower().endswith(".xml") or inhoud.lstrip()[:5] in (b"<?xml", b"<Docu"):
        return lees_camt053(inhoud)
    return lees_csv(inhoud)

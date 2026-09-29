"""SEPA-betaalbestand (pain.001.001.03). Dit bestand upload je in je bankomgeving
(ING, Rabobank, ABN AMRO, bunq, Knab, ...) en keur je daar met één handeling goed."""

import re
from datetime import datetime
from xml.sax.saxutils import escape

TOEGESTAAN = re.compile(r"[^A-Za-z0-9/\-?:().,'+ ]")


def end_to_end_id(factuur_id):
    """Referentie die bij de bank terugkomt, zodat we de betaling later automatisch herkennen."""
    return f"INK-{factuur_id}"


def _tekst(s, maxlen):
    s = TOEGESTAAN.sub("", (s or "").replace("&", "+"))
    return escape(s[:maxlen].strip())


def _bedrag(cent):
    return f"{cent // 100}.{cent % 100:02d}"


def maak_pain001(bericht_id, opdrachtgever, iban, bic, uitvoerdatum, betalingen):
    totaal = sum(b["bedrag_cent"] for b in betalingen)
    tijd = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    bic_blok = (f"<DbtrAgt><FinInstnId><BIC>{_tekst(bic, 11)}</BIC></FinInstnId></DbtrAgt>" if bic
                else "<DbtrAgt><FinInstnId><Othr><Id>NOTPROVIDED</Id></Othr></FinInstnId></DbtrAgt>")

    posten = []
    for b in betalingen:
        kenmerk = re.sub(r"\D", "", b["omschrijving"]) if b.get("is_kenmerk") else ""
        if kenmerk and len(kenmerk) == 16:
            rmt = ("<RmtInf><Strd><CdtrRefInf><Tp><CdOrPrtry><Cd>SCOR</Cd></CdOrPrtry><Issr>CUR</Issr></Tp>"
                   f"<Ref>{kenmerk}</Ref></CdtrRefInf></Strd></RmtInf>")
        else:
            rmt = f"<RmtInf><Ustrd>{_tekst(b['omschrijving'], 140)}</Ustrd></RmtInf>"
        agt = (f"<CdtrAgt><FinInstnId><BIC>{_tekst(b['bic'], 11)}</BIC></FinInstnId></CdtrAgt>"
               if b.get("bic") else "")
        posten.append(
            "<CdtTrfTxInf>"
            f"<PmtId><EndToEndId>{_tekst(b['end_to_end'], 35)}</EndToEndId></PmtId>"
            f"<Amt><InstdAmt Ccy=\"EUR\">{_bedrag(b['bedrag_cent'])}</InstdAmt></Amt>"
            f"{agt}"
            f"<Cdtr><Nm>{_tekst(b['naam'], 70)}</Nm></Cdtr>"
            f"<CdtrAcct><Id><IBAN>{b['iban']}</IBAN></Id></CdtrAcct>"
            f"{rmt}"
            "</CdtTrfTxInf>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<CstmrCdtTrfInitn>"
        f"<GrpHdr><MsgId>{_tekst(bericht_id, 35)}</MsgId><CreDtTm>{tijd}</CreDtTm>"
        f"<NbOfTxs>{len(betalingen)}</NbOfTxs><CtrlSum>{_bedrag(totaal)}</CtrlSum>"
        f"<InitgPty><Nm>{_tekst(opdrachtgever, 70)}</Nm></InitgPty></GrpHdr>"
        "<PmtInf>"
        f"<PmtInfId>{_tekst(bericht_id, 35)}</PmtInfId><PmtMtd>TRF</PmtMtd><BtchBookg>true</BtchBookg>"
        f"<NbOfTxs>{len(betalingen)}</NbOfTxs><CtrlSum>{_bedrag(totaal)}</CtrlSum>"
        "<PmtTpInf><SvcLvl><Cd>SEPA</Cd></SvcLvl></PmtTpInf>"
        f"<ReqdExctnDt>{uitvoerdatum}</ReqdExctnDt>"
        f"<Dbtr><Nm>{_tekst(opdrachtgever, 70)}</Nm></Dbtr>"
        f"<DbtrAcct><Id><IBAN>{iban}</IBAN></Id></DbtrAcct>"
        f"{bic_blok}<ChrgBr>SLEV</ChrgBr>"
        + "".join(posten)
        + "</PmtInf></CstmrCdtTrfInitn></Document>\n"
    )

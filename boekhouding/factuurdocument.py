"""Verkoopfactuur als pdf (om te mailen) en als e-factuur (UBL 2.1 / SI-UBL 2.0), zodat klanten
met een boekhoudpakket de factuur automatisch kunnen inlezen."""

import io
from xml.sax.saxutils import escape

from db import instellingen
from logica import euro, verkoop_totalen


def _gegevens(con, fid):
    v = con.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone()
    r = con.execute("SELECT * FROM relaties WHERE id = ?", (v["relatie_id"],)).fetchone()
    return v, r, verkoop_totalen(con, fid), instellingen(con)


def maak_pdf(con, fid):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    v, r, t, inst = _gegevens(con, fid)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=f"Factuur {v['factuurnummer']}", author=inst["bedrijfsnaam"])
    klein = ParagraphStyle("klein", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#4a5568"))
    normaal = ParagraphStyle("normaal", fontName="Helvetica", fontSize=10, leading=14)
    kop = ParagraphStyle("kop", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#111827"))

    def regels(*delen):
        return "<br/>".join(escape(d) for d in delen if d)

    afzender = regels(inst["bedrijfsnaam"], inst["adres"], f"{inst['postcode']} {inst['plaats']}".strip(),
                      inst["email"], f"KvK {inst['kvk']}" if inst["kvk"] else "",
                      f"Btw {inst['btw_nummer']}" if inst["btw_nummer"] else "", f"IBAN {inst['iban']}")
    ontvanger = regels(r["naam"], r["adres"], f"{r['postcode'] or ''} {r['plaats'] or ''}".strip(),
                       f"Btw {r['btw_nummer']}" if r["btw_nummer"] else "")
    inhoud = [
        Table([[Paragraph("Factuur", kop), Paragraph(afzender, klein)]], colWidths=[95 * mm, 75 * mm],
              style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]),
        Spacer(1, 10 * mm),
        Table([[Paragraph(ontvanger, normaal),
                Paragraph(regels(f"Factuurnummer: {v['factuurnummer']}", f"Factuurdatum: {v['factuurdatum']}",
                                 f"Vervaldatum: {v['vervaldatum']}"), normaal)]],
              colWidths=[95 * mm, 75 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]),
        Spacer(1, 10 * mm),
    ]
    data = [["Omschrijving", "Aantal", "Prijs", "Btw", "Totaal"]]
    for regel in t["regels"]:
        data.append([Paragraph(escape(regel["omschrijving"]), normaal), f"{regel['aantal']:g}",
                     euro(regel["prijs_cent"]), f"{regel['btw_pct']}%", euro(t["regel_excl"][regel["id"]])])
    data.append(["", "", "", "Subtotaal", euro(t["excl"])])
    for pct, bedrag in sorted(t["btw"].items()):
        data.append(["", "", "", f"Btw {pct}%", euro(bedrag)])
    data.append(["", "", "", "Totaal", euro(t["incl"])])
    n = len(data)
    inhoud.append(Table(data, colWidths=[80 * mm, 18 * mm, 26 * mm, 22 * mm, 24 * mm], style=[
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6b7280")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#d1d5db")),
        ("LINEBELOW", (0, len(t["regels"])), (-1, len(t["regels"])), 0.5, colors.HexColor("#e5e7eb")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("FONT", (0, 1), (-1, -1), "Helvetica", 10),
        ("FONT", (3, n - 1), (-1, n - 1), "Helvetica-Bold", 11),
        ("LINEABOVE", (3, n - 1), (-1, n - 1), 0.8, colors.HexColor("#111827")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    inhoud.append(Spacer(1, 10 * mm))
    if v["notities"]:
        inhoud += [Paragraph(escape(v["notities"]), normaal), Spacer(1, 5 * mm)]
    inhoud.append(Paragraph(
        f"Graag het totaalbedrag van <b>{euro(t['incl'])}</b> vóór {v['vervaldatum']} overmaken op "
        f"{escape(inst['iban'])} t.n.v. {escape(inst['bedrijfsnaam'])}, onder vermelding van "
        f"<b>{escape(v['factuurnummer'])}</b>.", normaal))
    doc.build(inhoud)
    return buf.getvalue()


def _bedrag(cent):
    return f"{cent / 100:.2f}"


def maak_ubl(con, fid, met_pdf=True):
    v, r, t, inst = _gegevens(con, fid)
    e = lambda s: escape(str(s or ""))  # noqa: E731

    def partij(naam, adres, postcode, plaats, btw, kvk, email=""):
        return (f"<cac:Party><cac:PartyName><cbc:Name>{e(naam)}</cbc:Name></cac:PartyName>"
                f"<cac:PostalAddress><cbc:StreetName>{e(adres)}</cbc:StreetName><cbc:CityName>{e(plaats)}</cbc:CityName>"
                f"<cbc:PostalZone>{e(postcode)}</cbc:PostalZone><cac:Country><cbc:IdentificationCode>NL"
                f"</cbc:IdentificationCode></cac:Country></cac:PostalAddress>"
                + (f"<cac:PartyTaxScheme><cbc:CompanyID>{e(btw)}</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID>"
                   f"</cac:TaxScheme></cac:PartyTaxScheme>" if btw else "")
                + f"<cac:PartyLegalEntity><cbc:RegistrationName>{e(naam)}</cbc:RegistrationName>"
                + (f'<cbc:CompanyID schemeID="0106">{e(kvk)}</cbc:CompanyID>' if kvk else "")
                + "</cac:PartyLegalEntity>"
                + (f"<cac:Contact><cbc:ElectronicMail>{e(email)}</cbc:ElectronicMail></cac:Contact>" if email else "")
                + "</cac:Party>")

    def categorie(pct):
        return "S" if pct else "Z"

    subtotalen = "".join(
        f'<cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">{_bedrag(t["basis"][pct])}</cbc:TaxableAmount>'
        f'<cbc:TaxAmount currencyID="EUR">{_bedrag(t["btw"][pct])}</cbc:TaxAmount><cac:TaxCategory>'
        f"<cbc:ID>{categorie(pct)}</cbc:ID><cbc:Percent>{pct}</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID>"
        f"</cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal>" for pct in sorted(t["basis"]))
    regels = "".join(
        f'<cac:InvoiceLine><cbc:ID>{i}</cbc:ID><cbc:InvoicedQuantity unitCode="C62">{rg["aantal"]:g}</cbc:InvoicedQuantity>'
        f'<cbc:LineExtensionAmount currencyID="EUR">{_bedrag(t["regel_excl"][rg["id"]])}</cbc:LineExtensionAmount>'
        f"<cac:Item><cbc:Name>{e(rg['omschrijving'])}</cbc:Name><cac:ClassifiedTaxCategory><cbc:ID>"
        f"{categorie(rg['btw_pct'])}</cbc:ID><cbc:Percent>{rg['btw_pct']}</cbc:Percent><cac:TaxScheme><cbc:ID>VAT"
        f'</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory></cac:Item><cac:Price><cbc:PriceAmount currencyID="EUR">'
        f"{_bedrag(rg['prijs_cent'])}</cbc:PriceAmount></cac:Price></cac:InvoiceLine>"
        for i, rg in enumerate(t["regels"], 1))
    bijlage = ""
    if met_pdf:
        import base64
        bijlage = (f"<cac:AdditionalDocumentReference><cbc:ID>{e(v['factuurnummer'])}</cbc:ID><cac:Attachment>"
                   f'<cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename="{e(v["factuurnummer"])}.pdf">'
                   f"{base64.b64encode(maak_pdf(con, fid)).decode()}</cbc:EmbeddedDocumentBinaryObject></cac:Attachment>"
                   "</cac:AdditionalDocumentReference>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
        'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
        'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">'
        "<cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0</cbc:CustomizationID>"
        "<cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>"
        f"<cbc:ID>{e(v['factuurnummer'])}</cbc:ID><cbc:IssueDate>{v['factuurdatum']}</cbc:IssueDate>"
        f"<cbc:DueDate>{v['vervaldatum']}</cbc:DueDate><cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"
        "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        f"<cbc:BuyerReference>{e(v['factuurnummer'])}</cbc:BuyerReference>{bijlage}"
        f"<cac:AccountingSupplierParty>{partij(inst['bedrijfsnaam'], inst['adres'], inst['postcode'], inst['plaats'], inst['btw_nummer'], inst['kvk'], inst['email'])}</cac:AccountingSupplierParty>"
        f"<cac:AccountingCustomerParty>{partij(r['naam'], r['adres'], r['postcode'], r['plaats'], r['btw_nummer'], r['kvk'], r['email'])}</cac:AccountingCustomerParty>"
        f"<cac:PaymentMeans><cbc:PaymentMeansCode>30</cbc:PaymentMeansCode><cbc:PaymentID>{e(v['factuurnummer'])}"
        f"</cbc:PaymentID><cac:PayeeFinancialAccount><cbc:ID>{e(inst['iban'])}</cbc:ID></cac:PayeeFinancialAccount>"
        "</cac:PaymentMeans>"
        f'<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">{_bedrag(t["btw_totaal"])}</cbc:TaxAmount>{subtotalen}</cac:TaxTotal>'
        f'<cac:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="EUR">{_bedrag(t["excl"])}</cbc:LineExtensionAmount>'
        f'<cbc:TaxExclusiveAmount currencyID="EUR">{_bedrag(t["excl"])}</cbc:TaxExclusiveAmount>'
        f'<cbc:TaxInclusiveAmount currencyID="EUR">{_bedrag(t["incl"])}</cbc:TaxInclusiveAmount>'
        f'<cbc:PayableAmount currencyID="EUR">{_bedrag(t["incl"])}</cbc:PayableAmount></cac:LegalMonetaryTotal>'
        f"{regels}</Invoice>\n")

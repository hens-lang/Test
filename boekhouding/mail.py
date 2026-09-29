"""Uitgaande e-mail: verkoopfacturen (pdf + e-factuur), automatische betalingsherinneringen en een
dagelijkse samenvatting van wat op jou wacht. Instellen via SMTP_* in config.env."""

import os
import smtplib
from datetime import date, timedelta
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

import factuurdocument
import logica
from db import instellingen, log, nu


def ingesteld():
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_GEBRUIKER", "SMTP_WACHTWOORD"))


def verstuur(con, aan, onderwerp, tekst, bijlagen=()):
    if not ingesteld():
        raise ValueError("E-mail is nog niet ingesteld (SMTP_HOST, SMTP_GEBRUIKER en SMTP_WACHTWOORD in config.env)")
    if not aan:
        raise ValueError("Geen e-mailadres bekend voor deze ontvanger")
    inst = instellingen(con)
    afzender = os.environ.get("SMTP_AFZENDER") or os.environ["SMTP_GEBRUIKER"]
    bericht = EmailMessage()
    bericht["From"] = formataddr((inst["bedrijfsnaam"], afzender))
    bericht["To"] = aan
    bericht["Subject"] = onderwerp
    bericht["Message-ID"] = make_msgid()
    if inst.get("email"):
        bericht["Reply-To"] = inst["email"]
    bericht.set_content(tekst)
    for naam, inhoud, mediatype in bijlagen:
        hoofd, sub = mediatype.split("/")
        bericht.add_attachment(inhoud, maintype=hoofd, subtype=sub, filename=naam)
    poort = int(os.environ.get("SMTP_POORT", 587))
    if poort == 465:
        server = smtplib.SMTP_SSL(os.environ["SMTP_HOST"], poort, timeout=30)
    else:
        server = smtplib.SMTP(os.environ["SMTP_HOST"], poort, timeout=30)
        server.starttls()
    with server:
        server.login(os.environ["SMTP_GEBRUIKER"], os.environ["SMTP_WACHTWOORD"])
        server.send_message(bericht)


def _factuurbijlagen(con, v):
    return [(f"{v['factuurnummer']}.pdf", factuurdocument.maak_pdf(con, v["id"]), "application/pdf"),
            (f"{v['factuurnummer']}.xml", factuurdocument.maak_ubl(con, v["id"], met_pdf=False).encode(),
             "application/xml")]


def verstuur_verkoopfactuur(con, fid):
    v = con.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone()
    r = con.execute("SELECT * FROM relaties WHERE id = ?", (v["relatie_id"],)).fetchone()
    inst = instellingen(con)
    t = logica.verkoop_totalen(con, fid)
    tekst = (f"Beste {r['naam']},\n\nIn de bijlage vind je factuur {v['factuurnummer']} van {logica.euro(t['incl'])}.\n"
             f"Graag voldoen vóór {v['vervaldatum']} op {inst['iban']} t.n.v. {inst['bedrijfsnaam']}, onder vermelding "
             f"van {v['factuurnummer']}.\n\nDe factuur is ook bijgevoegd als e-factuur (UBL), zodat je hem direct in je "
             f"boekhouding kunt inlezen.\n\nMet vriendelijke groet,\n{inst['bedrijfsnaam']}")
    verstuur(con, r["email"], f"Factuur {v['factuurnummer']} - {inst['bedrijfsnaam']}", tekst, _factuurbijlagen(con, v))
    if v["status"] == "concept":
        logica.zet_verkoopstatus(con, fid, "verzonden")
    log(con, "verkoopfactuur gemaild", "verkoop", fid, r["email"])
    con.commit()


def stuur_herinneringen(con):
    """1e en 2e herinnering op de ingestelde dagen na de vervaldatum. Daarna niet meer automatisch."""
    inst = instellingen(con)
    if inst.get("herinneringen_aan") != "1" or not ingesteld():
        return 0
    dagen = [int(d) for d in (inst.get("herinnering_dagen") or "7,21").split(",") if d.strip().isdigit()]
    verstuurd = 0
    for v in con.execute("SELECT * FROM verkoopfacturen WHERE status = 'verzonden'").fetchall():
        niveau = v["herinneringen"]
        if niveau >= len(dagen):
            continue
        if date.today() < date.fromisoformat(v["vervaldatum"]) + timedelta(days=dagen[niveau]):
            continue
        r = con.execute("SELECT * FROM relaties WHERE id = ?", (v["relatie_id"],)).fetchone()
        if not r["email"]:
            continue
        bedrag = logica.euro(logica.verkoop_totalen(con, v["id"])["incl"])
        if niveau == 0:
            tekst = (f"Beste {r['naam']},\n\nWellicht is het aan je aandacht ontsnapt: factuur {v['factuurnummer']} "
                     f"van {bedrag} (vervaldatum {v['vervaldatum']}) staat nog open.\n"
                     f"Wil je het bedrag overmaken op {inst['iban']} o.v.v. {v['factuurnummer']}? "
                     "Heb je al betaald, dan kun je deze mail negeren.\n\nMet vriendelijke groet,\n" + inst["bedrijfsnaam"])
        else:
            tekst = (f"Beste {r['naam']},\n\nOndanks onze eerdere herinnering hebben we de betaling van factuur "
                     f"{v['factuurnummer']} ({bedrag}, vervaldatum {v['vervaldatum']}) nog niet ontvangen.\n"
                     f"We verzoeken je vriendelijk maar dringend het bedrag binnen 7 dagen over te maken op "
                     f"{inst['iban']} o.v.v. {v['factuurnummer']}. Neem bij vragen gerust contact met ons op."
                     f"\n\nMet vriendelijke groet,\n{inst['bedrijfsnaam']}")
        soort = "Herinnering" if niveau == 0 else "Tweede herinnering"
        verstuur(con, r["email"], f"{soort}: factuur {v['factuurnummer']}", tekst, _factuurbijlagen(con, v))
        con.execute("UPDATE verkoopfacturen SET herinneringen = ?, laatst_herinnerd = ? WHERE id = ?",
                    (niveau + 1, nu(), v["id"]))
        log(con, f"{soort.lower()} verstuurd", "verkoop", v["id"], r["email"])
        con.commit()
        verstuurd += 1
    return verstuurd


def stuur_samenvatting(con, app_url):
    inst = instellingen(con)
    ontvanger = os.environ.get("MELDING_EMAIL") or inst.get("email")
    if inst.get("samenvatting_aan") != "1" or not ingesteld() or not ontvanger:
        return False
    d = logica.dashboard(con)
    punten = []
    if d["te_keuren_n"]:
        punten.append(f"- {d['te_keuren_n']} factuur/facturen wachten op goedkeuring ({logica.euro(d['te_keuren_s'])})")
    if d["te_ondertekenen_n"]:
        punten.append(f"- {d['te_ondertekenen_n']} betaalopdracht(en) wachten op bevestiging in de ABN-app")
    if d["inbox_fout_n"]:
        punten.append(f"- {d['inbox_fout_n']} document(en) in de inbox konden niet automatisch worden gelezen")
    if d["te_laat_n"]:
        punten.append(f"- {d['te_laat_n']} klant(en) hebben een factuur te laat betaald")
    if not punten:
        return False
    verstuur(con, ontvanger, f"Boekhouding: {len(punten)} punt(en) voor vandaag",
             "Goedemorgen,\n\nDit wacht op jou:\n\n" + "\n".join(punten) + f"\n\nOpen de boekhouding: {app_url}\n")
    return True

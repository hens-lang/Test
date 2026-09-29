"""Inkoopfacturen automatisch doorsturen naar het boekhoudadres (bijv. de scan- en herkenmailbox van de
accountant). Elke factuur gaat precies één keer, met het originele bestand en de belangrijkste gegevens.

Standaard pas na goedkeuring, zodat afgekeurde, dubbele of frauduleuze facturen niet worden doorgestuurd.
Lukt versturen niet (bijv. geen internet), dan probeert de achtergrondtaak het elke 5 minuten opnieuw."""

import os
import re

import intake
import mail
from db import instellingen, log, nu
from logica import euro

STATUSSEN = {"goedkeuring": ("goedgekeurd", "in_batch", "betaald"),
             "ontvangst": ("ter_goedkeuring", "goedgekeurd", "in_batch", "betaald")}
BETAALWIJZE = {"overboeking": "zelf overmaken", "incasso": "automatische incasso", "al_betaald": "al betaald"}


def adres(con):
    return (instellingen(con).get("doorstuur_email") or "").strip()


def wachtrij(con):
    inst = instellingen(con)
    if not adres(con):
        return []
    statussen = STATUSSEN.get(inst.get("doorstuur_moment"), STATUSSEN["goedkeuring"])
    return con.execute(
        f"""SELECT id FROM inkoopfacturen
            WHERE doorgestuurd_op IS NULL AND bestand IS NOT NULL
              AND status IN ({','.join('?' * len(statussen))}) AND aangemaakt_op >= ?
            ORDER BY id""", (*statussen, inst.get("doorsturen_vanaf") or "")).fetchall()


def _bijlagen(con, f):  # f bevat relatie_naam
    bijlagen, gezien = [], set()
    namen = [f["bestand"]]
    if f["document_id"]:
        doc = con.execute("SELECT opslag FROM documenten WHERE id = ?", (f["document_id"],)).fetchone()
        if doc:
            namen.append(doc["opslag"])          # bij een e-factuur ook de originele xml meesturen
    basis = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{f['relatie_naam']}_{f['factuurnummer']}").strip("_")
    for naam in namen:
        pad = os.path.join(intake.UPLOAD_MAP, naam)
        if naam in gezien or not os.path.exists(pad):
            continue
        gezien.add(naam)
        with open(pad, "rb") as fh:
            # herkenbare bestandsnaam voor de boekhouding: Leverancier_Factuurnummer.pdf
            leesbaar = basis + os.path.splitext(naam)[1].lower()
            bijlagen.append((leesbaar, fh.read(), intake.raad_mediatype(naam) or "application/octet-stream"))
    if not bijlagen:
        raise ValueError("Het factuurbestand is niet meer aanwezig in de map uploads")
    return bijlagen


def stuur(con, factuur_id):
    f = con.execute("""SELECT i.*, r.naam AS relatie_naam, r.iban AS relatie_iban, g.naam AS rekening_naam
                       FROM inkoopfacturen i JOIN relaties r ON r.id = i.relatie_id
                       LEFT JOIN grootboekrekeningen g ON g.code = i.rekening WHERE i.id = ?""",
                    (factuur_id,)).fetchone()
    aan = adres(con)
    if not aan:
        raise ValueError("Vul eerst bij Instellingen het e-mailadres van de boekhouding in")
    if not f["bestand"]:
        raise ValueError("Deze factuur heeft geen bestand om door te sturen")
    inst = instellingen(con)
    soort = "Creditnota" if f["bedrag_incl_cent"] < 0 else "Inkoopfactuur"
    tekst = "\n".join([
        f"{soort} van {f['relatie_naam']} voor {inst['bedrijfsnaam']}.",
        "",
        f"Leverancier:      {f['relatie_naam']}" + (f" ({f['relatie_iban']})" if f["relatie_iban"] else ""),
        f"Factuurnummer:    {f['factuurnummer']}",
        f"Factuurdatum:     {f['factuurdatum']}",
        f"Vervaldatum:      {f['vervaldatum']}",
        f"Bedrag excl. btw: {euro(f['bedrag_excl_cent'])}",
        f"Btw:              {euro(f['btw_cent'])}",
        f"Totaal:           {euro(f['bedrag_incl_cent'])}",
        f"Grootboek:        {f['rekening'] or ''} {f['rekening_naam'] or ''}".rstrip(),
        f"Betaalwijze:      {BETAALWIJZE.get(f['betaalwijze'], f['betaalwijze'])}",
        f"Status:           {f['status'].replace('_', ' ').replace('in batch', 'in betaling')}"
        + (f" (goedgekeurd op {f['beoordeeld_op'][:10]})" if f["beoordeeld_op"] and f["status"] != "ter_goedkeuring" else ""),
        "",
        f"Automatisch doorgestuurd door de boekhouding van {inst['bedrijfsnaam']}.",
    ])
    mail.verstuur(con, aan, f"{soort} {f['relatie_naam']} {f['factuurnummer']} ({euro(f['bedrag_incl_cent'])})",
                  tekst, _bijlagen(con, f))
    con.execute("UPDATE inkoopfacturen SET doorgestuurd_op = ?, doorstuur_melding = NULL WHERE id = ?",
                (nu(), factuur_id))
    log(con, "inkoopfactuur doorgestuurd naar boekhouding", "inkoop", factuur_id, aan)
    con.commit()


def verwerk_wachtrij(con):
    """Stuurt alles door wat klaarstaat. Fouten worden per factuur bewaard en later opnieuw geprobeerd."""
    verstuurd = 0
    for r in wachtrij(con):
        try:
            stuur(con, r["id"])
            verstuurd += 1
        except Exception as e:  # noqa: BLE001 - één mislukte factuur mag de rest niet tegenhouden
            # geen rollback: stuur() schrijft pas na een geslaagde verzending, en zo blijven andere
            # (nog niet opgeslagen) wijzigingen van de aanroeper intact
            melding = str(e)[:300]
            oud = con.execute("SELECT doorstuur_melding FROM inkoopfacturen WHERE id = ?", (r["id"],)).fetchone()[0]
            if melding != oud:
                con.execute("UPDATE inkoopfacturen SET doorstuur_melding = ? WHERE id = ?", (melding, r["id"]))
                log(con, "doorsturen naar boekhouding mislukt", "inkoop", r["id"], melding)
                con.commit()
    return verstuurd


def probeer_direct(con):
    """Na goedkeuren of uploaden meteen doorsturen; mislukt het, dan pakt de planner het later op."""
    if adres(con) and mail.ingesteld():
        return verwerk_wachtrij(con)
    return 0

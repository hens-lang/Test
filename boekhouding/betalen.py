"""Betalen: van goedgekeurde factuur naar betaalopdracht.

Met Ponto-koppeling: goedkeuren -> betaalopdracht staat direct klaar in je ABN-app -> jij bevestigt.
Zonder koppeling: goedkeuren -> betaalvoorstel -> SEPA-bestand -> uploaden bij ABN AMRO.
Er wordt altijd betaald naar het BEKENDE IBAN van de leverancier, nooit naar een IBAN dat alleen op een
nieuwe factuur staat (bescherming tegen factuurfraude)."""

from datetime import date, timedelta

import ponto
import sepa
from db import instellingen, log, nu
from logica import euro, iban_geldig, normaliseer_iban, vandaag


def ponto_actief(con):
    return ponto.ingesteld() and ponto.status(con)["verbonden"] and ponto.status(con)["rekening"]


def betaalvoorstel(con, ids=None):
    """Goedgekeurde facturen die we zelf moeten overmaken, met geplande betaaldatum en verrekende creditnota's."""
    inst = instellingen(con)
    marge = int(inst.get("betaal_dagen_voor_verval") or 0)
    direct = inst.get("betaalmoment") == "direct"
    rijen = con.execute(
        """SELECT i.*, r.naam AS relatie_naam, r.iban AS relatie_iban, r.bic AS relatie_bic
           FROM inkoopfacturen i JOIN relaties r ON r.id = i.relatie_id
           WHERE i.status = 'goedgekeurd' AND i.betaalwijze = 'overboeking' ORDER BY i.vervaldatum""").fetchall()
    facturen = [dict(r) for r in rijen if r["bedrag_incl_cent"] > 0 and (ids is None or r["id"] in ids)]
    credits = [dict(r) for r in rijen if r["bedrag_incl_cent"] < 0]

    # creditnota's verrekenen met de grootste open factuur van dezelfde leverancier
    for c in credits:
        kandidaat = max((f for f in facturen if f["relatie_id"] == c["relatie_id"]
                         and f["bedrag_incl_cent"] + c["bedrag_incl_cent"] > 0),
                        key=lambda f: f["bedrag_incl_cent"], default=None)
        if kandidaat:
            kandidaat.setdefault("credits", []).append(c)

    for f in facturen:
        f["credits"] = f.get("credits", [])
        f["te_betalen_cent"] = f["bedrag_incl_cent"] + sum(c["bedrag_incl_cent"] for c in f["credits"])
        gepland = vandaag() if direct else max(vandaag(), date.fromisoformat(f["vervaldatum"]) - timedelta(days=marge))
        f["betaaldatum"] = gepland.isoformat()
        f["iban_ok"] = iban_geldig(f["relatie_iban"])
    return facturen


def maak_betaalopdracht(con, factuur_ids, uitvoerdatum=None, terug_url=None):
    """Maakt één betaalopdracht voor de gekozen facturen. Geeft (batch_id, ondertekenen_url of None)."""
    inst = instellingen(con)
    if not iban_geldig(inst.get("iban")):
        raise ValueError("Vul eerst een geldig eigen IBAN in bij Instellingen")
    ids = {int(i) for i in factuur_ids}
    posten = betaalvoorstel(con, ids)
    ontbrekend = ids - {p["id"] for p in posten}
    if ontbrekend:
        raise ValueError(f"Factuur #{min(ontbrekend)} is niet (meer) klaar om te betalen")
    for p in posten:
        if not p["iban_ok"]:
            raise ValueError(f"{p['relatie_naam']} heeft geen geldig IBAN; vul het aan bij Relaties")
    if not posten:
        raise ValueError("Geen facturen geselecteerd")

    uitvoerdatum = max(uitvoerdatum or min(p["betaaldatum"] for p in posten), vandaag().isoformat())
    totaal = sum(p["te_betalen_cent"] for p in posten)
    kanaal = "ponto" if ponto_actief(con) else "bestand"
    batch_id = con.execute(
        "INSERT INTO betaalbatches (aangemaakt_op, uitvoerdatum, aantal, totaal_cent, bericht_id, xml, kanaal) "
        "VALUES (?, ?, ?, ?, '', '', ?)", (nu(), uitvoerdatum, len(posten), totaal, kanaal)).lastrowid
    bericht_id = f"BATCH-{batch_id}-{vandaag():%Y%m%d}"
    regels = [{
        "end_to_end": sepa.end_to_end_id(p["id"]),
        "bedrag_cent": p["te_betalen_cent"],
        "naam": p["relatie_naam"], "iban": normaliseer_iban(p["relatie_iban"]), "bic": p["relatie_bic"] or "",
        "omschrijving": (p["betalingskenmerk"] if p["betalingskenmerk"] and not p["credits"] else
                         f"Factuur {p['factuurnummer']}" + "".join(f" -/- credit {c['factuurnummer']}" for c in p["credits"])),
        "is_kenmerk": bool(p["betalingskenmerk"]) and not p["credits"],
    } for p in posten]
    xml = sepa.maak_pain001(bericht_id=bericht_id, opdrachtgever=inst["bedrijfsnaam"],
                            iban=normaliseer_iban(inst["iban"]), bic=inst.get("bic", ""),
                            uitvoerdatum=uitvoerdatum, betalingen=regels)
    url = None
    if kanaal == "ponto":
        extern_id, url = ponto.bulkbetaling(con, bericht_id, uitvoerdatum, regels, terug_url)
        con.execute("UPDATE betaalbatches SET extern_id = ?, status = 'ter_ondertekening', ondertekenen_url = ? "
                    "WHERE id = ?", (extern_id, url, batch_id))
    con.execute("UPDATE betaalbatches SET bericht_id = ?, xml = ? WHERE id = ?", (bericht_id, xml, batch_id))
    for p in posten:
        con.execute("UPDATE inkoopfacturen SET status = 'in_batch', betaalbatch_id = ? WHERE id = ?", (batch_id, p["id"]))
        for c in p["credits"]:
            con.execute("UPDATE inkoopfacturen SET status = 'in_batch', betaalbatch_id = ?, verrekend_met = ? "
                        "WHERE id = ?", (batch_id, p["id"], c["id"]))
    log(con, "betaalopdracht aangemaakt", "batch", batch_id,
        f"{len(posten)} betalingen, {euro(totaal)}, uitvoerdatum {uitvoerdatum}, via "
        + ("ABN AMRO (Ponto)" if kanaal == "ponto" else "betaalbestand"))
    con.commit()
    return batch_id, url


def na_goedkeuring(con, factuur_ids, terug_url):
    """Direct na goedkeuren: met bankkoppeling meteen een betaalopdracht klaarzetten om te bevestigen."""
    if not ponto_actief(con):
        return None, None
    klaar = [p["id"] for p in betaalvoorstel(con, {int(i) for i in factuur_ids}) if p["iban_ok"]]
    if not klaar:
        return None, None
    return maak_betaalopdracht(con, klaar, terug_url=terug_url)


def annuleer(con, batch_id, reden="geannuleerd"):
    con.execute("UPDATE inkoopfacturen SET status = 'goedgekeurd', betaalbatch_id = NULL, verrekend_met = NULL "
                "WHERE betaalbatch_id = ? AND status = 'in_batch'", (batch_id,))
    con.execute("UPDATE betaalbatches SET status = ? WHERE id = ?",
                ("geweigerd" if reden == "geweigerd" else "geannuleerd", batch_id))
    log(con, f"betaalopdracht {reden}", "batch", batch_id)
    con.commit()


def werk_status_bij(con, batch_id=None):
    """Vraagt bij Ponto na of openstaande betaalopdrachten zijn bevestigd of geweigerd."""
    sql = "SELECT * FROM betaalbatches WHERE kanaal = 'ponto' AND status = 'ter_ondertekening'"
    batches = con.execute(sql + (" AND id = ?" if batch_id else ""), (batch_id,) if batch_id else ()).fetchall()
    for b in batches:
        st = ponto.bulkbetaling_status(con, b["extern_id"])
        if st.startswith("accepted") or st in ("pending", "signed"):
            con.execute("UPDATE betaalbatches SET status = 'ondertekend' WHERE id = ?", (b["id"],))
            log(con, "betaalopdracht bevestigd in ABN AMRO", "batch", b["id"], st)
            con.commit()
        elif st in ("rejected", "cancelled", "canceled", "failed"):
            annuleer(con, b["id"], "geweigerd")
    return len(batches)

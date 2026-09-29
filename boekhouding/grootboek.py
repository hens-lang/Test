"""Dubbel boekhouden: elke factuur en elke bankmutatie wordt automatisch als journaalpost
geboekt. Winst & verlies, balans en btw-aangifte worden rechtstreeks uit het journaal berekend."""

from datetime import date

from db import log, nu

BANK, DEBITEUREN, VOORBELASTING, BTW_HOOG, BTW_LAAG, CREDITEUREN, TE_VERWERKEN = (
    "1100", "1300", "1510", "1520", "1521", "1600", "1900")
OMZET_PER_TARIEF = {21: ("8000", "1a"), 9: ("8010", "1b"), 0: ("8020", "1e")}
BTW_PER_TARIEF = {21: BTW_HOOG, 9: BTW_LAAG}


class BoekingsFout(ValueError):
    pass


def boek(con, datum, dagboek, omschrijving, regels, bron_type=None, bron_id=None):
    """regels: lijst van dicts met rekening, debet/credit (centen), optioneel relatie_id en btw_rubriek.
    Negatieve bedragen (creditnota's) worden naar de andere kant gezet."""
    genormaliseerd = []
    for r in regels:
        saldo = r.get("debet", 0) - r.get("credit", 0)
        if saldo:
            genormaliseerd.append({**r, "debet": max(saldo, 0), "credit": max(-saldo, 0)})
    regels = genormaliseerd
    debet = sum(r.get("debet", 0) for r in regels)
    credit = sum(r.get("credit", 0) for r in regels)
    if debet != credit:
        raise BoekingsFout(f"Journaalpost '{omschrijving}' is niet in balans: debet {debet} ≠ credit {credit}")
    if not regels:
        return None
    for r in regels:
        if con.execute("SELECT 1 FROM grootboekrekeningen WHERE code = ?", (r["rekening"],)).fetchone() is None:
            raise BoekingsFout(f"Onbekende grootboekrekening {r['rekening']}")
    post = con.execute(
        "INSERT INTO journaalposten (datum, dagboek, omschrijving, bron_type, bron_id, aangemaakt_op) "
        "VALUES (?, ?, ?, ?, ?, ?)", (datum, dagboek, omschrijving, bron_type, bron_id, nu())).lastrowid
    con.executemany(
        "INSERT INTO journaalregels (post_id, rekening, debet_cent, credit_cent, relatie_id, btw_rubriek) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(post, r["rekening"], r.get("debet", 0), r.get("credit", 0), r.get("relatie_id"), r.get("btw_rubriek"))
         for r in regels])
    return post


def is_geboekt(con, bron_type, bron_id):
    """Waar als de boekingen van deze bron (na eventuele storno's) nog een saldo hebben."""
    return con.execute(
        """SELECT 1 FROM journaalregels r JOIN journaalposten p ON p.id = r.post_id
           WHERE p.bron_type = ? AND p.bron_id = ?
           GROUP BY r.rekening HAVING SUM(r.debet_cent - r.credit_cent) != 0 LIMIT 1""",
        (bron_type, bron_id)).fetchone() is not None


def storneer(con, bron_type, bron_id, reden):
    """Draait alle boekingen van een bron terug met een tegenboeking (nooit verwijderen: audit trail)."""
    saldo = con.execute(
        """SELECT r.rekening, r.relatie_id, r.btw_rubriek, SUM(r.debet_cent) d, SUM(r.credit_cent) c
           FROM journaalregels r JOIN journaalposten p ON p.id = r.post_id
           WHERE p.bron_type = ? AND p.bron_id = ?
           GROUP BY r.rekening, r.relatie_id, r.btw_rubriek""", (bron_type, bron_id)).fetchall()
    regels = [{"rekening": s["rekening"], "debet": max(s["c"] - s["d"], 0), "credit": max(s["d"] - s["c"], 0),
               "relatie_id": s["relatie_id"], "btw_rubriek": s["btw_rubriek"]} for s in saldo]
    if any(r["debet"] or r["credit"] for r in regels):
        boek(con, date.today().isoformat(), "memoriaal", f"Storno: {reden}", regels, bron_type, bron_id)


# ---------------------------------------------------------------- automatische boekingen


def boek_inkoopfactuur(con, f):
    if is_geboekt(con, "inkoop", f["id"]):
        return
    rekening = f["rekening"] or standaard_kostenrekening(con)
    rel = con.execute("SELECT naam FROM relaties WHERE id = ?", (f["relatie_id"],)).fetchone()
    boek(con, f["factuurdatum"], "inkoop", f"{rel['naam']} factuur {f['factuurnummer']}", [
        {"rekening": rekening, "debet": f["bedrag_excl_cent"], "relatie_id": f["relatie_id"]},
        {"rekening": VOORBELASTING, "debet": f["btw_cent"], "relatie_id": f["relatie_id"], "btw_rubriek": "5b"},
        {"rekening": CREDITEUREN, "credit": f["bedrag_incl_cent"], "relatie_id": f["relatie_id"]},
    ], "inkoop", f["id"])
    log(con, "inkoopfactuur geboekt", "inkoop", f["id"], f"op {rekening}")


def boek_verkoopfactuur(con, v, totalen):
    if is_geboekt(con, "verkoop", v["id"]):
        return
    regels = [{"rekening": DEBITEUREN, "debet": totalen["incl"], "relatie_id": v["relatie_id"]}]
    per_rekening = {}
    for r in totalen["regels"]:
        standaard, rubriek = OMZET_PER_TARIEF.get(r["btw_pct"], ("8000", "1a"))
        sleutel = (r["rekening"] or standaard, rubriek)
        per_rekening[sleutel] = per_rekening.get(sleutel, 0) + totalen["regel_excl"][r["id"]]
    for (rekening, rubriek), bedrag in per_rekening.items():
        regels.append({"rekening": rekening, "credit": bedrag, "relatie_id": v["relatie_id"], "btw_rubriek": rubriek})
    for pct, btw in totalen["btw"].items():
        if btw:
            regels.append({"rekening": BTW_PER_TARIEF.get(pct, BTW_HOOG), "credit": btw, "relatie_id": v["relatie_id"],
                           "btw_rubriek": OMZET_PER_TARIEF.get(pct, ("", "1a"))[1] + "-btw"})
    boek(con, v["factuurdatum"], "verkoop", f"Verkoopfactuur {v['factuurnummer']}", regels, "verkoop", v["id"])
    log(con, "verkoopfactuur geboekt", "verkoop", v["id"], v["factuurnummer"])


def boek_banktransactie(con, t):
    """Bij import: bank tegenover 'nog te verwerken'. Afletteren verplaatst het daarna naar de juiste rekening."""
    bedrag = t["bedrag_cent"]
    boek(con, t["datum"], "bank", f"{t['naam'] or 'Bank'}: {t['omschrijving'] or ''}"[:200], [
        {"rekening": BANK, "debet": max(bedrag, 0), "credit": max(-bedrag, 0)},
        {"rekening": TE_VERWERKEN, "debet": max(-bedrag, 0), "credit": max(bedrag, 0)},
    ], "bank", t["id"])


def boek_bank_verwerking(con, t, tegenrekening, relatie_id=None, omschrijving=""):
    bedrag = t["bedrag_cent"]
    boek(con, t["datum"], "bank", omschrijving or f"Verwerking bankmutatie #{t['id']}", [
        {"rekening": TE_VERWERKEN, "debet": max(bedrag, 0), "credit": max(-bedrag, 0)},
        {"rekening": tegenrekening, "debet": max(-bedrag, 0), "credit": max(bedrag, 0), "relatie_id": relatie_id},
    ], "bank-verwerking", t["id"])


# ---------------------------------------------------------------- rapportages


def rekeningen(con, alleen_actief=True):
    sql = "SELECT * FROM grootboekrekeningen" + (" WHERE actief = 1" if alleen_actief else "") + " ORDER BY code"
    return con.execute(sql).fetchall()


def kostenrekeningen(con):
    return con.execute("SELECT * FROM grootboekrekeningen WHERE soort = 'kosten' AND actief = 1 ORDER BY code").fetchall()


def standaard_kostenrekening(con):
    r = con.execute("SELECT waarde FROM instellingen WHERE sleutel = 'standaard_kostenrekening'").fetchone()
    return (r and r["waarde"]) or "4900"


def saldi(con, van=None, tot=None):
    """Saldo per rekening (debet positief) over een periode [van, tot)."""
    sql = """SELECT g.code, g.naam, g.soort, COALESCE(SUM(r.debet_cent - r.credit_cent), 0) AS saldo
             FROM grootboekrekeningen g
             LEFT JOIN journaalregels r ON r.rekening = g.code
             LEFT JOIN journaalposten p ON p.id = r.post_id"""
    voorwaarden, args = [], []
    if van:
        voorwaarden.append("(p.datum IS NULL OR p.datum >= ?)")
        args.append(van)
    if tot:
        voorwaarden.append("(p.datum IS NULL OR p.datum < ?)")
        args.append(tot)
    if voorwaarden:
        sql += " WHERE " + " AND ".join(voorwaarden)
    return con.execute(sql + " GROUP BY g.code ORDER BY g.code", args).fetchall()


def winst_en_verlies(con, jaar):
    rijen = [r for r in saldi(con, f"{jaar}-01-01", f"{jaar + 1}-01-01") if r["soort"] in ("opbrengst", "kosten")]
    opbrengsten = [(r["code"], r["naam"], -r["saldo"]) for r in rijen if r["soort"] == "opbrengst" and r["saldo"]]
    kosten = [(r["code"], r["naam"], r["saldo"]) for r in rijen if r["soort"] == "kosten" and r["saldo"]]
    totaal_o = sum(b for *_, b in opbrengsten)
    totaal_k = sum(b for *_, b in kosten)
    return {"opbrengsten": opbrengsten, "kosten": kosten, "totaal_opbrengsten": totaal_o,
            "totaal_kosten": totaal_k, "resultaat": totaal_o - totaal_k}


def balans(con, peildatum):
    rijen = saldi(con, tot=peildatum)
    activa = [(r["code"], r["naam"], r["saldo"]) for r in rijen if r["soort"] == "activa" and r["saldo"]]
    passiva = [(r["code"], r["naam"], -r["saldo"]) for r in rijen if r["soort"] == "passiva" and r["saldo"]]
    resultaat = -sum(r["saldo"] for r in rijen if r["soort"] in ("opbrengst", "kosten"))
    return {"activa": activa, "passiva": passiva, "resultaat": resultaat,
            "totaal_activa": sum(b for *_, b in activa),
            "totaal_passiva": sum(b for *_, b in passiva) + resultaat}


def btw_aangifte(con, van, tot):
    """Rubrieken van de Nederlandse btw-aangifte, berekend uit het journaal."""
    def som(rubriek):
        r = con.execute(
            """SELECT COALESCE(SUM(r.credit_cent - r.debet_cent), 0) FROM journaalregels r
               JOIN journaalposten p ON p.id = r.post_id
               WHERE r.btw_rubriek = ? AND p.datum >= ? AND p.datum < ?""", (rubriek, van, tot)).fetchone()
        return r[0]

    rubrieken = {
        "1a": {"omschrijving": "Leveringen/diensten belast met hoog tarief", "omzet": som("1a"), "btw": som("1a-btw")},
        "1b": {"omschrijving": "Leveringen/diensten belast met laag tarief", "omzet": som("1b"), "btw": som("1b-btw")},
        "1e": {"omschrijving": "Leveringen/diensten belast met 0% of niet bij u belast", "omzet": som("1e"), "btw": 0},
    }
    voorbelasting = -som("5b")
    verschuldigd = sum(r["btw"] for r in rubrieken.values())
    return {"rubrieken": rubrieken, "5a": verschuldigd, "5b": voorbelasting, "totaal": verschuldigd - voorbelasting}


def grootboekkaart(con, code, van, tot):
    return con.execute(
        """SELECT p.datum, p.dagboek, p.omschrijving, p.bron_type, p.bron_id, r.debet_cent, r.credit_cent
           FROM journaalregels r JOIN journaalposten p ON p.id = r.post_id
           WHERE r.rekening = ? AND p.datum >= ? AND p.datum < ? ORDER BY p.datum, p.id""",
        (code, van, tot)).fetchall()

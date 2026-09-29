"""Bedrijfsregels: goedkeuren, betaalbatches, bankkoppeling, verkoopfacturen en btw.
Alle schermen gebruiken deze functies, zodat de data overal hetzelfde gedrag heeft."""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from db import instellingen, log, nu
import sepa

# ---------------------------------------------------------------- hulpfuncties


def naar_cent(tekst):
    """'1.234,56' / '1234.56' / '1234' -> 123456"""
    if tekst is None:
        return 0
    s = str(tekst).strip().replace("€", "").replace(" ", "")
    if not s:
        return 0
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return int((Decimal(s) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        raise ValueError(f"Ongeldig bedrag: {tekst}")


def euro(cent):
    cent = cent or 0
    teken = "-" if cent < 0 else ""
    e, c = divmod(abs(int(cent)), 100)
    return f"{teken}€ {e:,}".replace(",", ".") + f",{c:02d}"


def normaliseer_iban(iban):
    return re.sub(r"\s+", "", iban or "").upper()


def iban_geldig(iban):
    iban = normaliseer_iban(iban)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", iban):
        return False
    omgezet = "".join(str(int(ch, 36)) for ch in iban[4:] + iban[:4])
    return int(omgezet) % 97 == 1


def vandaag():
    return date.today()


# ---------------------------------------------------------------- inkoop / goedkeuren


def voeg_inkoopfactuur_toe(con, relatie_id, factuurnummer, factuurdatum, vervaldatum,
                           omschrijving, bedrag_excl_cent, btw_cent, betalingskenmerk="", bestand=None):
    relatie = con.execute("SELECT * FROM relaties WHERE id = ?", (relatie_id,)).fetchone()
    if relatie is None:
        raise ValueError("Onbekende relatie")
    dubbel = con.execute(
        "SELECT id FROM inkoopfacturen WHERE relatie_id = ? AND factuurnummer = ?",
        (relatie_id, factuurnummer),
    ).fetchone()
    if dubbel:
        raise ValueError(f"Factuur {factuurnummer} van {relatie['naam']} bestaat al (#{dubbel['id']})")

    incl = bedrag_excl_cent + btw_cent
    cur = con.execute(
        """INSERT INTO inkoopfacturen (relatie_id, factuurnummer, factuurdatum, vervaldatum, omschrijving,
               bedrag_excl_cent, btw_cent, bedrag_incl_cent, betalingskenmerk, bestand, aangemaakt_op)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (relatie_id, factuurnummer, factuurdatum, vervaldatum, omschrijving,
         bedrag_excl_cent, btw_cent, incl, betalingskenmerk, bestand, nu()),
    )
    fid = cur.lastrowid
    log(con, "inkoopfactuur ingevoerd", "inkoop", fid, f"{relatie['naam']} {factuurnummer} {euro(incl)}")

    # Automatisch goedkeuren voor vertrouwde crediteuren onder hun limiet
    limiet = relatie["auto_goedkeur_limiet_cent"] or 0
    if limiet > 0 and incl <= limiet and iban_geldig(relatie["iban"]):
        beoordeel(con, fid, True, f"automatisch: onder limiet {euro(limiet)}")
    con.commit()
    return fid


def beoordeel(con, factuur_id, goedkeuren, notitie=""):
    f = con.execute("SELECT * FROM inkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
    if f is None:
        raise ValueError("Factuur niet gevonden")
    if f["status"] not in ("ter_goedkeuring", "afgekeurd", "goedgekeurd"):
        raise ValueError(f"Factuur heeft status '{f['status']}' en kan niet meer beoordeeld worden")
    status = "goedgekeurd" if goedkeuren else "afgekeurd"
    con.execute(
        "UPDATE inkoopfacturen SET status = ?, beoordeeld_op = ?, beoordeling_notitie = ? WHERE id = ?",
        (status, nu(), notitie, factuur_id),
    )
    log(con, f"inkoopfactuur {status}", "inkoop", factuur_id, notitie)


def betaalvoorstel(con):
    """Goedgekeurde facturen die nog betaald moeten worden, met geplande betaaldatum."""
    inst = instellingen(con)
    marge = int(inst.get("betaal_dagen_voor_verval") or 0)
    rijen = con.execute(
        """SELECT i.*, r.naam AS relatie_naam, r.iban AS relatie_iban, r.bic AS relatie_bic
           FROM inkoopfacturen i JOIN relaties r ON r.id = i.relatie_id
           WHERE i.status = 'goedgekeurd' ORDER BY i.vervaldatum"""
    ).fetchall()
    voorstel = []
    for r in rijen:
        gepland = max(vandaag(), date.fromisoformat(r["vervaldatum"]) - timedelta(days=marge))
        voorstel.append({**dict(r), "betaaldatum": gepland.isoformat(),
                         "iban_ok": iban_geldig(r["relatie_iban"])})
    return voorstel


def maak_betaalbatch(con, factuur_ids, uitvoerdatum=None):
    inst = instellingen(con)
    if not iban_geldig(inst.get("iban")):
        raise ValueError("Vul eerst een geldig eigen IBAN in bij Instellingen")
    voorstel = {v["id"]: v for v in betaalvoorstel(con)}
    posten = []
    for fid in factuur_ids:
        v = voorstel.get(int(fid))
        if v is None:
            raise ValueError(f"Factuur #{fid} is niet goedgekeurd of al in een batch")
        if not v["iban_ok"]:
            raise ValueError(f"Relatie {v['relatie_naam']} heeft geen geldig IBAN")
        posten.append(v)
    if not posten:
        raise ValueError("Geen facturen geselecteerd")

    uitvoerdatum = uitvoerdatum or min(p["betaaldatum"] for p in posten)
    totaal = sum(p["bedrag_incl_cent"] for p in posten)
    cur = con.execute(
        "INSERT INTO betaalbatches (aangemaakt_op, uitvoerdatum, aantal, totaal_cent, bericht_id, xml) "
        "VALUES (?, ?, ?, ?, '', '')",
        (nu(), uitvoerdatum, len(posten), totaal),
    )
    batch_id = cur.lastrowid
    bericht_id = f"BATCH-{batch_id}-{vandaag():%Y%m%d}"
    xml = sepa.maak_pain001(
        bericht_id=bericht_id,
        opdrachtgever=inst["bedrijfsnaam"], iban=normaliseer_iban(inst["iban"]), bic=inst.get("bic", ""),
        uitvoerdatum=uitvoerdatum,
        betalingen=[{
            "end_to_end": sepa.end_to_end_id(p["id"]),
            "bedrag_cent": p["bedrag_incl_cent"],
            "naam": p["relatie_naam"],
            "iban": normaliseer_iban(p["relatie_iban"]),
            "bic": p["relatie_bic"] or "",
            "omschrijving": p["betalingskenmerk"] or f"Factuur {p['factuurnummer']}",
            "is_kenmerk": bool(p["betalingskenmerk"]),
        } for p in posten],
    )
    con.execute("UPDATE betaalbatches SET bericht_id = ?, xml = ? WHERE id = ?", (bericht_id, xml, batch_id))
    for p in posten:
        con.execute("UPDATE inkoopfacturen SET status = 'in_batch', betaalbatch_id = ? WHERE id = ?",
                    (batch_id, p["id"]))
    log(con, "betaalbatch aangemaakt", "batch", batch_id, f"{len(posten)} betalingen, {euro(totaal)}")
    con.commit()
    return batch_id


def annuleer_batch(con, batch_id):
    con.execute("UPDATE inkoopfacturen SET status = 'goedgekeurd', betaalbatch_id = NULL "
                "WHERE betaalbatch_id = ? AND status = 'in_batch'", (batch_id,))
    log(con, "betaalbatch geannuleerd", "batch", batch_id)
    con.commit()


# ---------------------------------------------------------------- verkoop


def verkoop_totalen(con, factuur_id):
    regels = con.execute("SELECT * FROM verkoopregels WHERE factuur_id = ?", (factuur_id,)).fetchall()
    excl = 0
    btw_per_tarief = {}
    for r in regels:
        regel_excl = int((Decimal(str(r["aantal"])) * r["prijs_cent"]).quantize(Decimal("1"), ROUND_HALF_UP))
        excl += regel_excl
        btw_per_tarief[r["btw_pct"]] = btw_per_tarief.get(r["btw_pct"], 0) + regel_excl
    btw = {pct: int((Decimal(basis) * pct / 100).quantize(Decimal("1"), ROUND_HALF_UP))
           for pct, basis in btw_per_tarief.items()}
    return {"regels": regels, "excl": excl, "btw": btw, "btw_totaal": sum(btw.values()),
            "incl": excl + sum(btw.values())}


def volgend_factuurnummer(con):
    inst = instellingen(con)
    prefix = f"{inst.get('factuur_prefix') or 'F'}{vandaag().year}-"
    laatste = con.execute(
        "SELECT factuurnummer FROM verkoopfacturen WHERE factuurnummer LIKE ? ORDER BY id DESC LIMIT 1",
        (prefix + "%",),
    ).fetchone()
    volgnr = int(laatste["factuurnummer"][len(prefix):]) + 1 if laatste else 1
    return f"{prefix}{volgnr:04d}"


def maak_verkoopfactuur(con, relatie_id, regels, factuurdatum=None, notities=""):
    inst = instellingen(con)
    factuurdatum = factuurdatum or vandaag().isoformat()
    verval = (date.fromisoformat(factuurdatum) + timedelta(days=int(inst.get("betaaltermijn_dagen") or 14))).isoformat()
    nummer = volgend_factuurnummer(con)
    cur = con.execute(
        "INSERT INTO verkoopfacturen (relatie_id, factuurnummer, factuurdatum, vervaldatum, notities, aangemaakt_op) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (relatie_id, nummer, factuurdatum, verval, notities, nu()),
    )
    fid = cur.lastrowid
    for r in regels:
        con.execute(
            "INSERT INTO verkoopregels (factuur_id, omschrijving, aantal, prijs_cent, btw_pct) VALUES (?, ?, ?, ?, ?)",
            (fid, r["omschrijving"], r["aantal"], r["prijs_cent"], r["btw_pct"]),
        )
    log(con, "verkoopfactuur aangemaakt", "verkoop", fid, nummer)
    con.commit()
    return fid


# ---------------------------------------------------------------- bank & afletteren


def importeer_transacties(con, transacties):
    """Slaat transacties op (dubbele worden overgeslagen) en koppelt ze automatisch."""
    nieuw, gekoppeld = 0, 0
    for t in transacties:
        sleutel = t.get("import_sleutel") or "|".join(
            str(t.get(k, "")) for k in ("datum", "bedrag_cent", "tegenrekening", "omschrijving", "referentie"))
        try:
            cur = con.execute(
                "INSERT INTO banktransacties (datum, bedrag_cent, tegenrekening, naam, omschrijving, referentie, "
                "import_sleutel, geimporteerd_op) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (t["datum"], t["bedrag_cent"], normaliseer_iban(t.get("tegenrekening")), t.get("naam", ""),
                 t.get("omschrijving", ""), t.get("referentie", ""), sleutel, nu()),
            )
        except Exception as e:  # dubbele import
            if "UNIQUE" in str(e):
                continue
            raise
        nieuw += 1
        if koppel_automatisch(con, cur.lastrowid):
            gekoppeld += 1
    log(con, "bankafschrift geïmporteerd", details=f"{nieuw} nieuw, {gekoppeld} automatisch gekoppeld")
    con.commit()
    return nieuw, gekoppeld


def _kandidaten(con, t):
    tekst = f"{t['omschrijving']} {t['referentie']}".upper()
    if t["bedrag_cent"] < 0:
        bedrag = -t["bedrag_cent"]
        # 1. Onze eigen end-to-end-referentie uit de betaalbatch
        m = re.search(r"INK-(\d+)", tekst)
        if m:
            f = con.execute("SELECT id FROM inkoopfacturen WHERE id = ? AND status != 'betaald'",
                            (int(m.group(1)),)).fetchone()
            if f:
                return [("inkoop", f["id"])]
        # 2. Zelfde bedrag + zelfde IBAN
        rijen = con.execute(
            """SELECT i.id FROM inkoopfacturen i JOIN relaties r ON r.id = i.relatie_id
               WHERE i.status IN ('goedgekeurd', 'in_batch', 'ter_goedkeuring')
                 AND i.bedrag_incl_cent = ? AND REPLACE(UPPER(r.iban), ' ', '') = ?""",
            (bedrag, t["tegenrekening"] or ""),
        ).fetchall()
        return [("inkoop", r["id"]) for r in rijen]

    # Ontvangst: factuurnummer in omschrijving, anders bedrag + IBAN
    openstaand = con.execute(
        """SELECT v.id, v.factuurnummer, r.iban FROM verkoopfacturen v JOIN relaties r ON r.id = v.relatie_id
           WHERE v.status IN ('verzonden', 'concept')"""
    ).fetchall()
    op_nummer = [("verkoop", v["id"]) for v in openstaand if v["factuurnummer"].upper() in tekst]
    if op_nummer:
        return op_nummer
    return [("verkoop", v["id"]) for v in openstaand
            if verkoop_totalen(con, v["id"])["incl"] == t["bedrag_cent"]
            and normaliseer_iban(v["iban"]) == (t["tegenrekening"] or "")]


def koppel_automatisch(con, transactie_id):
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    kandidaten = _kandidaten(con, t)
    if len(kandidaten) == 1:
        soort, fid = kandidaten[0]
        koppel(con, transactie_id, soort, fid, automatisch=True)
        return True
    return False


def koppel(con, transactie_id, soort, factuur_id, automatisch=False):
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    tabel = {"inkoop": "inkoopfacturen", "verkoop": "verkoopfacturen"}[soort]
    con.execute("UPDATE banktransacties SET gekoppeld_type = ?, gekoppeld_id = ? WHERE id = ?",
                (soort, factuur_id, transactie_id))
    con.execute(f"UPDATE {tabel} SET status = 'betaald', betaald_op = ? WHERE id = ?", (t["datum"], factuur_id))
    log(con, "betaling gekoppeld" + (" (automatisch)" if automatisch else ""), soort, factuur_id,
        f"banktransactie #{transactie_id} {euro(t['bedrag_cent'])}")
    con.commit()


def kandidaten_voor(con, transactie_id):
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    return _kandidaten(con, t)


# ---------------------------------------------------------------- overzichten


def btw_overzicht(con, jaar, kwartaal):
    start = date(jaar, 3 * (kwartaal - 1) + 1, 1)
    eind = date(jaar + (kwartaal == 4), (3 * kwartaal) % 12 + 1, 1)
    verkoop_btw, omzet = 0, 0
    for v in con.execute("SELECT id FROM verkoopfacturen WHERE status != 'concept' "
                         "AND factuurdatum >= ? AND factuurdatum < ?", (start.isoformat(), eind.isoformat())):
        tot = verkoop_totalen(con, v["id"])
        omzet += tot["excl"]
        verkoop_btw += tot["btw_totaal"]
    inkoop = con.execute(
        "SELECT COALESCE(SUM(btw_cent), 0) AS btw, COALESCE(SUM(bedrag_excl_cent), 0) AS excl FROM inkoopfacturen "
        "WHERE status != 'afgekeurd' AND factuurdatum >= ? AND factuurdatum < ?",
        (start.isoformat(), eind.isoformat()),
    ).fetchone()
    return {"periode": f"Q{kwartaal} {jaar}", "omzet": omzet, "verkoop_btw": verkoop_btw,
            "kosten": inkoop["excl"], "voorbelasting": inkoop["btw"],
            "te_betalen": verkoop_btw - inkoop["btw"]}


def dashboard(con):
    def een(sql, *args):
        return con.execute(sql, args).fetchone()

    vandaag_s = vandaag().isoformat()
    te_keuren = een("SELECT COUNT(*) n, COALESCE(SUM(bedrag_incl_cent),0) s FROM inkoopfacturen "
                    "WHERE status = 'ter_goedkeuring'")
    te_betalen = een("SELECT COUNT(*) n, COALESCE(SUM(bedrag_incl_cent),0) s FROM inkoopfacturen "
                     "WHERE status IN ('goedgekeurd', 'in_batch')")
    open_verkoop = con.execute("SELECT id, vervaldatum FROM verkoopfacturen WHERE status = 'verzonden'").fetchall()
    te_ontvangen = sum(verkoop_totalen(con, v["id"])["incl"] for v in open_verkoop)
    te_laat = [v for v in open_verkoop if v["vervaldatum"] < vandaag_s]
    saldo = een("SELECT COALESCE(SUM(bedrag_cent),0) s FROM banktransacties")["s"]
    ongekoppeld = een("SELECT COUNT(*) n FROM banktransacties WHERE gekoppeld_type IS NULL")["n"]
    q = (vandaag().month - 1) // 3 + 1
    return {
        "te_keuren_n": te_keuren["n"], "te_keuren_s": te_keuren["s"],
        "te_betalen_n": te_betalen["n"], "te_betalen_s": te_betalen["s"],
        "te_ontvangen_n": len(open_verkoop), "te_ontvangen_s": te_ontvangen,
        "te_laat_n": len(te_laat),
        "bankmutaties_saldo": saldo, "ongekoppeld_n": ongekoppeld,
        "btw": btw_overzicht(con, vandaag().year, q),
        "log": con.execute("SELECT * FROM logboek ORDER BY id DESC LIMIT 12").fetchall(),
    }

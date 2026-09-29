"""Bedrijfsregels: inkoop en goedkeuren, verkoop, bank en afletteren, overzichten.
Alle schermen en achtergrondtaken gebruiken deze functies, zodat de data overal hetzelfde gedrag heeft."""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import grootboek
from db import instellingen, log, nu

# ---------------------------------------------------------------- hulpfuncties


def naar_cent(tekst):
    """'1.234,56' / '1234.56' / 1234.5 -> 123456"""
    if tekst is None:
        return 0
    if isinstance(tekst, (int, float)):
        return int((Decimal(str(tekst)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    s = str(tekst).strip().replace("€", "").replace(" ", "").replace("EUR", "")
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


INFO_WAARSCHUWINGEN = ("Wordt geïncasseerd", "Factuur is al betaald", "Creditnota:")


def blokkerende_waarschuwingen(waarschuwingen):
    return [w for w in waarschuwingen if not w.startswith(INFO_WAARSCHUWINGEN)]


# ---------------------------------------------------------------- inkoop / goedkeuren


def voeg_inkoopfactuur_toe(con, relatie_id, factuurnummer, factuurdatum, vervaldatum, omschrijving,
                           bedrag_excl_cent, btw_cent, betalingskenmerk="", bestand=None, rekening=None,
                           bron="handmatig", zekerheid=None, waarschuwingen=(), document_id=None,
                           betaalwijze="overboeking", methode=None):
    relatie = con.execute("SELECT * FROM relaties WHERE id = ?", (relatie_id,)).fetchone()
    if relatie is None:
        raise ValueError("Onbekende relatie")
    dubbel = con.execute("SELECT id FROM inkoopfacturen WHERE relatie_id = ? AND factuurnummer = ?",
                         (relatie_id, factuurnummer)).fetchone()
    if dubbel:
        raise ValueError(f"Factuur {factuurnummer} van {relatie['naam']} bestaat al (#{dubbel['id']})")
    waarschuwingen = list(waarschuwingen)
    incl = bedrag_excl_cent + btw_cent
    rekening = rekening or relatie["standaard_rekening"] or grootboek.standaard_kostenrekening(con)
    fid = con.execute(
        """INSERT INTO inkoopfacturen (relatie_id, factuurnummer, factuurdatum, vervaldatum, omschrijving,
               bedrag_excl_cent, btw_cent, bedrag_incl_cent, betalingskenmerk, betaalwijze, bestand, rekening,
               bron, zekerheid, waarschuwingen, document_id, aangemaakt_op)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (relatie_id, factuurnummer, factuurdatum, vervaldatum, omschrijving, bedrag_excl_cent, btw_cent, incl,
         betalingskenmerk, betaalwijze, bestand, rekening, bron, zekerheid, "\n".join(waarschuwingen) or None,
         document_id, nu())).lastrowid
    log(con, "inkoopfactuur ingevoerd", "inkoop", fid,
        f"{relatie['naam']} {factuurnummer} {euro(incl)}" + (f" (gelezen via {methode})" if methode else ""))

    # Automatisch goedkeuren: alleen vertrouwde leveranciers, geverifieerd IBAN, niets verdachts
    limiet = relatie["auto_goedkeur_limiet_cent"] or 0
    if (limiet > 0 and 0 < incl <= limiet and relatie["iban_geverifieerd"] and iban_geldig(relatie["iban"])
            and not blokkerende_waarschuwingen(waarschuwingen) and (zekerheid is None or zekerheid >= 0.85)):
        beoordeel(con, fid, True, f"automatisch: vertrouwde leverancier, onder limiet {euro(limiet)}", automatisch=True)
    con.commit()
    return fid


def beoordeel(con, factuur_id, goedkeuren, notitie="", automatisch=False):
    f = con.execute("SELECT * FROM inkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
    if f is None:
        raise ValueError("Factuur niet gevonden")
    if f["status"] not in ("ter_goedkeuring", "afgekeurd", "goedgekeurd"):
        raise ValueError(f"Factuur {f['factuurnummer']} heeft status '{f['status'].replace('_', ' ')}' "
                         "en kan niet meer beoordeeld worden")
    status = "goedgekeurd" if goedkeuren else "afgekeurd"
    con.execute("UPDATE inkoopfacturen SET status = ?, beoordeeld_op = ?, beoordeling_notitie = ? WHERE id = ?",
                (status, nu(), notitie, factuur_id))
    log(con, f"inkoopfactuur {status}", "inkoop", factuur_id, notitie)
    f = con.execute("SELECT * FROM inkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
    if goedkeuren:
        grootboek.boek_inkoopfactuur(con, f)
        waarschuwingen = (f["waarschuwingen"] or "")
        if not automatisch and "wijkt af van bekend IBAN" not in waarschuwingen:
            # jij hebt de factuur met IBAN gezien en goedgekeurd: IBAN geldt vanaf nu als geverifieerd
            con.execute("UPDATE relaties SET iban_geverifieerd = 1 WHERE id = ?", (f["relatie_id"],))
    else:
        grootboek.storneer(con, "inkoop", factuur_id, f"afgekeurd: {f['factuurnummer']}")


def wijzig_inkoopfactuur(con, factuur_id, velden):
    """Corrigeert een (automatisch gelezen) factuur. Is hij al geboekt, dan wordt er netjes herboekt."""
    f = con.execute("SELECT * FROM inkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
    if f["status"] not in ("ter_goedkeuring", "goedgekeurd", "afgekeurd"):
        raise ValueError("Een factuur die al in betaling is kan niet meer gewijzigd worden")
    toegestaan = ("factuurnummer", "factuurdatum", "vervaldatum", "omschrijving", "bedrag_excl_cent", "btw_cent",
                  "betalingskenmerk", "rekening", "betaalwijze", "relatie_id")
    velden = {k: v for k, v in velden.items() if k in toegestaan}
    if not velden:
        return
    nieuw = {**dict(f), **velden}
    nieuw["bedrag_incl_cent"] = nieuw["bedrag_excl_cent"] + nieuw["btw_cent"]
    velden["bedrag_incl_cent"] = nieuw["bedrag_incl_cent"]
    geboekt = grootboek.is_geboekt(con, "inkoop", factuur_id)
    if geboekt:
        grootboek.storneer(con, "inkoop", factuur_id, f"correctie {f['factuurnummer']}")
    con.execute(f"UPDATE inkoopfacturen SET {', '.join(k + ' = ?' for k in velden)} WHERE id = ?",
                (*velden.values(), factuur_id))
    if geboekt:
        grootboek.boek_inkoopfactuur(con, con.execute("SELECT * FROM inkoopfacturen WHERE id = ?",
                                                     (factuur_id,)).fetchone())
    log(con, "inkoopfactuur gecorrigeerd", "inkoop", factuur_id, ", ".join(velden))
    con.commit()


# ---------------------------------------------------------------- verkoop


def verkoop_totalen(con, factuur_id):
    regels = con.execute("SELECT * FROM verkoopregels WHERE factuur_id = ? ORDER BY id", (factuur_id,)).fetchall()
    excl, basis_per_tarief, regel_excl = 0, {}, {}
    for r in regels:
        bedrag = int((Decimal(str(r["aantal"])) * r["prijs_cent"]).quantize(Decimal("1"), ROUND_HALF_UP))
        regel_excl[r["id"]] = bedrag
        excl += bedrag
        basis_per_tarief[r["btw_pct"]] = basis_per_tarief.get(r["btw_pct"], 0) + bedrag
    btw = {pct: int((Decimal(basis) * pct / 100).quantize(Decimal("1"), ROUND_HALF_UP))
           for pct, basis in basis_per_tarief.items()}
    return {"regels": regels, "regel_excl": regel_excl, "excl": excl, "btw": btw, "basis": basis_per_tarief,
            "btw_totaal": sum(btw.values()), "incl": excl + sum(btw.values())}


def volgend_factuurnummer(con):
    inst = instellingen(con)
    prefix = f"{inst.get('factuur_prefix') or 'F'}{vandaag().year}-"
    laatste = con.execute("SELECT factuurnummer FROM verkoopfacturen WHERE factuurnummer LIKE ? "
                          "ORDER BY factuurnummer DESC LIMIT 1", (prefix + "%",)).fetchone()
    volgnr = int(laatste["factuurnummer"][len(prefix):]) + 1 if laatste else 1
    return f"{prefix}{volgnr:04d}"


def maak_verkoopfactuur(con, relatie_id, regels, factuurdatum=None, notities=""):
    inst = instellingen(con)
    factuurdatum = factuurdatum or vandaag().isoformat()
    verval = (date.fromisoformat(factuurdatum) + timedelta(days=int(inst.get("betaaltermijn_dagen") or 14))).isoformat()
    nummer = volgend_factuurnummer(con)
    fid = con.execute(
        "INSERT INTO verkoopfacturen (relatie_id, factuurnummer, factuurdatum, vervaldatum, notities, aangemaakt_op) "
        "VALUES (?, ?, ?, ?, ?, ?)", (relatie_id, nummer, factuurdatum, verval, notities, nu())).lastrowid
    for r in regels:
        con.execute("INSERT INTO verkoopregels (factuur_id, omschrijving, aantal, prijs_cent, btw_pct, rekening) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (fid, r["omschrijving"], r["aantal"], r["prijs_cent"], r["btw_pct"], r.get("rekening")))
    log(con, "verkoopfactuur aangemaakt", "verkoop", fid, nummer)
    con.commit()
    return fid


def zet_verkoopstatus(con, fid, status):
    v = con.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone()
    if status not in ("concept", "verzonden", "betaald"):
        raise ValueError("Onbekende status")
    if status == "concept" and v["status"] != "concept":
        grootboek.storneer(con, "verkoop", fid, f"terug naar concept: {v['factuurnummer']}")
    if status in ("verzonden", "betaald"):
        grootboek.boek_verkoopfactuur(con, v, verkoop_totalen(con, fid))
    con.execute("UPDATE verkoopfacturen SET status = ?, verzonden_op = COALESCE(verzonden_op, ?), betaald_op = ? "
                "WHERE id = ?", (status, nu() if status != "concept" else None,
                                 vandaag().isoformat() if status == "betaald" else None, fid))
    log(con, f"verkoopfactuur {status}", "verkoop", fid, v["factuurnummer"])
    con.commit()


# ---------------------------------------------------------------- bank & afletteren


def importeer_transacties(con, transacties):
    """Slaat transacties op (dubbele worden overgeslagen), boekt ze en koppelt ze automatisch aan facturen."""
    nieuw, gekoppeld = 0, 0
    for t in transacties:
        sleutel = t.get("import_sleutel") or "|".join(
            str(t.get(k, "")) for k in ("datum", "bedrag_cent", "tegenrekening", "omschrijving", "referentie"))
        if con.execute("SELECT 1 FROM banktransacties WHERE import_sleutel = ?", (sleutel,)).fetchone():
            continue
        tid = con.execute(
            "INSERT INTO banktransacties (datum, bedrag_cent, tegenrekening, naam, omschrijving, referentie, "
            "import_sleutel, geimporteerd_op) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (t["datum"], t["bedrag_cent"], normaliseer_iban(t.get("tegenrekening")), t.get("naam", ""),
             t.get("omschrijving", ""), t.get("referentie", ""), sleutel, nu())).lastrowid
        grootboek.boek_banktransactie(con, con.execute("SELECT * FROM banktransacties WHERE id = ?", (tid,)).fetchone())
        nieuw += 1
        if koppel_automatisch(con, tid):
            gekoppeld += 1
    if nieuw:
        log(con, "bankmutaties ingelezen", details=f"{nieuw} nieuw, {gekoppeld} automatisch gekoppeld")
    con.commit()
    return nieuw, gekoppeld


def _naam_lijkt(a, b):
    a = re.sub(r"[^a-z0-9]", "", (a or "").lower())
    b = re.sub(r"[^a-z0-9]", "", (b or "").lower())
    return bool(a and b) and (a[:8] in b or b[:8] in a)


def _kandidaten(con, t):
    tekst = f"{t['omschrijving']} {t['referentie']}".upper()
    if t["bedrag_cent"] < 0:
        bedrag = -t["bedrag_cent"]
        m = re.search(r"INK-(\d+)", tekst)          # eigen referentie uit het betaalbestand / Ponto
        if m:
            f = con.execute("SELECT id FROM inkoopfacturen WHERE id = ? AND status != 'betaald'",
                            (int(m.group(1)),)).fetchone()
            if f:
                return [("inkoop", f["id"])]
        open_ = con.execute(
            """SELECT i.id, i.bedrag_incl_cent, i.betaalwijze, r.iban, r.naam FROM inkoopfacturen i
               JOIN relaties r ON r.id = i.relatie_id
               WHERE i.status IN ('goedgekeurd', 'in_batch', 'ter_goedkeuring') AND i.bedrag_incl_cent = ?""",
            (bedrag,)).fetchall()
        op_iban = [("inkoop", f["id"]) for f in open_ if normaliseer_iban(f["iban"]) == (t["tegenrekening"] or "")]
        if op_iban:
            return op_iban
        # incasso's komen vaak van een ander rekeningnummer: dan op bedrag + naam
        return [("inkoop", f["id"]) for f in open_ if f["betaalwijze"] != "overboeking" and _naam_lijkt(f["naam"], t["naam"])]

    open_ = con.execute("""SELECT v.id, v.factuurnummer, r.iban, r.naam FROM verkoopfacturen v
                           JOIN relaties r ON r.id = v.relatie_id WHERE v.status = 'verzonden'""").fetchall()
    op_nummer = [("verkoop", v["id"]) for v in open_ if v["factuurnummer"].upper() in tekst]
    if op_nummer:
        return op_nummer
    op_bedrag = [v for v in open_ if verkoop_totalen(con, v["id"])["incl"] == t["bedrag_cent"]]
    return [("verkoop", v["id"]) for v in op_bedrag
            if normaliseer_iban(v["iban"]) == (t["tegenrekening"] or "") or _naam_lijkt(v["naam"], t["naam"])]


def koppel_automatisch(con, transactie_id):
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    kandidaten = _kandidaten(con, t)
    if len(kandidaten) == 1:
        koppel(con, transactie_id, *kandidaten[0], automatisch=True)
        return True
    return False


def koppel(con, transactie_id, soort, factuur_id, automatisch=False):
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    if t["gekoppeld_type"]:
        raise ValueError("Deze bankmutatie is al verwerkt")
    if soort == "inkoop":
        f = con.execute("SELECT * FROM inkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
        if f["status"] in ("ter_goedkeuring", "afgekeurd"):
            # betaling zonder goedkeuring (bijv. incasso): factuur alsnog boeken zodat het grootboek klopt
            grootboek.boek_inkoopfactuur(con, f)
        grootboek.boek_bank_verwerking(con, t, grootboek.CREDITEUREN, f["relatie_id"], f"Betaling {f['factuurnummer']}")
        con.execute("UPDATE inkoopfacturen SET status = 'betaald', betaald_op = ? WHERE id = ?", (t["datum"], factuur_id))
        # creditnota's die met deze betaling verrekend zijn, zijn nu ook afgehandeld
        con.execute("UPDATE inkoopfacturen SET status = 'betaald', betaald_op = ? WHERE verrekend_met = ?",
                    (t["datum"], factuur_id))
        rel = con.execute("SELECT iban FROM relaties WHERE id = ?", (f["relatie_id"],)).fetchone()
        if normaliseer_iban(rel["iban"]) == t["tegenrekening"]:
            con.execute("UPDATE relaties SET iban_geverifieerd = 1 WHERE id = ?", (f["relatie_id"],))
    else:
        v = con.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (factuur_id,)).fetchone()
        grootboek.boek_verkoopfactuur(con, v, verkoop_totalen(con, factuur_id))
        grootboek.boek_bank_verwerking(con, t, grootboek.DEBITEUREN, v["relatie_id"], f"Ontvangst {v['factuurnummer']}")
        con.execute("UPDATE verkoopfacturen SET status = 'betaald', betaald_op = ? WHERE id = ?", (t["datum"], factuur_id))
    con.execute("UPDATE banktransacties SET gekoppeld_type = ?, gekoppeld_id = ? WHERE id = ?",
                (soort, factuur_id, transactie_id))
    log(con, "betaling gekoppeld" + (" (automatisch)" if automatisch else ""), soort, factuur_id,
        f"bankmutatie #{transactie_id} {euro(t['bedrag_cent'])}")
    con.commit()


def boek_op_rekening(con, transactie_id, rekening):
    """Bankmutatie zonder factuur (bankkosten, loon, belasting, privé) direct op een grootboekrekening."""
    t = con.execute("SELECT * FROM banktransacties WHERE id = ?", (transactie_id,)).fetchone()
    if t["gekoppeld_type"]:
        raise ValueError("Deze bankmutatie is al verwerkt")
    grootboek.boek_bank_verwerking(con, t, rekening, omschrijving=f"{t['naam']}: {t['omschrijving']}"[:200])
    con.execute("UPDATE banktransacties SET gekoppeld_type = 'grootboek', rekening = ? WHERE id = ?",
                (rekening, transactie_id))
    log(con, "bankmutatie geboekt", "bank", transactie_id, f"op {rekening}")
    con.commit()


# ---------------------------------------------------------------- overzichten


def kwartaal_grenzen(jaar, kwartaal):
    start = date(jaar, 3 * (kwartaal - 1) + 1, 1)
    eind = date(jaar + (kwartaal == 4), (3 * kwartaal) % 12 + 1, 1)
    return start.isoformat(), eind.isoformat()


def btw_overzicht(con, jaar, kwartaal):
    van, tot = kwartaal_grenzen(jaar, kwartaal)
    a = grootboek.btw_aangifte(con, van, tot)
    omzet = sum(r["omzet"] for r in a["rubrieken"].values())
    return {"periode": f"Q{kwartaal} {jaar}", "van": van, "tot": tot, "omzet": omzet, "verkoop_btw": a["5a"],
            "voorbelasting": a["5b"], "te_betalen": a["totaal"], "aangifte": a}


def dashboard(con):
    def een(sql, *args):
        return con.execute(sql, args).fetchone()

    vandaag_s = vandaag().isoformat()
    te_keuren = een("SELECT COUNT(*) n, COALESCE(SUM(bedrag_incl_cent),0) s FROM inkoopfacturen "
                    "WHERE status = 'ter_goedkeuring'")
    te_betalen = een("SELECT COUNT(*) n, COALESCE(SUM(bedrag_incl_cent),0) s FROM inkoopfacturen "
                     "WHERE status IN ('goedgekeurd', 'in_batch') AND betaalwijze = 'overboeking'")
    te_ondertekenen = een("SELECT COUNT(*) n FROM betaalbatches WHERE status = 'ter_ondertekening'")["n"]
    open_verkoop = con.execute("SELECT id, vervaldatum FROM verkoopfacturen WHERE status = 'verzonden'").fetchall()
    te_ontvangen = sum(verkoop_totalen(con, v["id"])["incl"] for v in open_verkoop)
    te_laat = [v for v in open_verkoop if v["vervaldatum"] < vandaag_s]
    saldo_bank = een("SELECT COALESCE(SUM(debet_cent - credit_cent), 0) s FROM journaalregels WHERE rekening = '1100'")["s"]
    ongekoppeld = een("SELECT COUNT(*) n FROM banktransacties WHERE gekoppeld_type IS NULL")["n"]
    inbox_fout = een("SELECT COUNT(*) n FROM documenten WHERE status = 'fout'")["n"]
    q = (vandaag().month - 1) // 3 + 1
    jaar = vandaag().year
    wv = grootboek.winst_en_verlies(con, jaar)
    return {
        "te_keuren_n": te_keuren["n"], "te_keuren_s": te_keuren["s"],
        "te_betalen_n": te_betalen["n"], "te_betalen_s": te_betalen["s"], "te_ondertekenen_n": te_ondertekenen,
        "te_ontvangen_n": len(open_verkoop), "te_ontvangen_s": te_ontvangen, "te_laat_n": len(te_laat),
        "saldo_bank": saldo_bank, "ongekoppeld_n": ongekoppeld, "inbox_fout_n": inbox_fout,
        "btw": btw_overzicht(con, jaar, q), "resultaat": wv["resultaat"], "omzet": wv["totaal_opbrengsten"],
        "jaar": jaar,
        "maanden": resultaat_per_maand(con, jaar),
        "log": con.execute("SELECT * FROM logboek ORDER BY id DESC LIMIT 10").fetchall(),
    }


def resultaat_per_maand(con, jaar):
    rijen = con.execute(
        """SELECT substr(p.datum, 6, 2) AS maand, g.soort, SUM(r.credit_cent - r.debet_cent) AS bedrag
           FROM journaalregels r JOIN journaalposten p ON p.id = r.post_id
           JOIN grootboekrekeningen g ON g.code = r.rekening
           WHERE p.datum >= ? AND p.datum < ? AND g.soort IN ('opbrengst', 'kosten')
           GROUP BY maand, g.soort""", (f"{jaar}-01-01", f"{jaar + 1}-01-01")).fetchall()
    maanden = [{"maand": m, "omzet": 0, "kosten": 0} for m in range(1, 13)]
    for r in rijen:
        m = maanden[int(r["maand"]) - 1]
        if r["soort"] == "opbrengst":
            m["omzet"] = r["bedrag"]
        else:
            m["kosten"] = -r["bedrag"]
    return maanden

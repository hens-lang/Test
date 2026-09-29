"""Eigen boekhouding: facturen komen vanzelf binnen, jij keurt goed, de rest gaat automatisch.

Start:  python app.py   ->  http://localhost:5000
"""

import os
import secrets
from datetime import date, timedelta
from functools import wraps

import db

db.laad_configbestand()

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request,  # noqa: E402
                   send_from_directory, session, url_for)

import ai  # noqa: E402
import bankimport  # noqa: E402
import betalen  # noqa: E402
import factuurdocument  # noqa: E402
import grootboek  # noqa: E402
import intake  # noqa: E402
import logica  # noqa: E402
import mail  # noqa: E402
import planner  # noqa: E402
import ponto  # noqa: E402
from logica import euro, naar_cent  # noqa: E402

app = Flask(__name__)
app.secret_key = os.environ.get("APP_GEHEIM") or secrets.token_hex(16)
app.config["MAX_CONTENT_LENGTH"] = 40 * 1024 * 1024
app.jinja_env.filters["euro"] = euro


def con():
    if "con" not in g:
        g.con = db.verbind(app.config.get("DATABASE"))
        db.initialiseer(g.con)
    return g.con


@app.teardown_appcontext
def sluit(_):
    c = g.pop("con", None)
    if c is not None:
        c.close()


@app.context_processor
def globaal():
    if request.endpoint in ("login", "static"):
        return {}
    c = con()
    return {"inst": db.instellingen(c),
            "badge": {"goedkeuren": c.execute("SELECT COUNT(*) FROM inkoopfacturen WHERE status = 'ter_goedkeuring'").fetchone()[0],
                      "inbox": c.execute("SELECT COUNT(*) FROM documenten WHERE status = 'fout'").fetchone()[0],
                      "bank": c.execute("SELECT COUNT(*) FROM banktransacties WHERE gekoppeld_type IS NULL").fetchone()[0],
                      "betalingen": c.execute("SELECT COUNT(*) FROM betaalbatches WHERE status = 'ter_ondertekening'").fetchone()[0]},
            "vandaag": date.today().isoformat()}


# ---------------------------------------------------------------- inloggen

@app.before_request
def vereis_login():
    wachtwoord = os.environ.get("APP_WACHTWOORD")
    if wachtwoord and not session.get("ingelogd") and request.endpoint not in ("login", "static"):
        return redirect(url_for("login", volgende=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("wachtwoord", ""), os.environ.get("APP_WACHTWOORD", "")):
            session["ingelogd"] = True
            session.permanent = True
            volgende = request.args.get("volgende") or ""
            return redirect(volgende if volgende.startswith("/") else url_for("dashboard"))
        flash("Onjuist wachtwoord", "fout")
    return render_template("login.html")


@app.route("/uitloggen")
def uitloggen():
    session.clear()
    return redirect(url_for("login"))


def met_fouten(view):
    """Toont fouten uit de bedrijfslogica en koppelingen als melding in plaats van een crash."""
    @wraps(view)
    def wrapper(*a, **kw):
        try:
            return view(*a, **kw)
        except (ValueError, ponto.PontoFout) as e:
            if "con" in g:
                g.con.rollback()
            flash(str(e), "fout")
            return redirect(request.referrer or url_for("dashboard"))
    return wrapper


# ---------------------------------------------------------------- dashboard

@app.route("/")
def dashboard():
    return render_template("dashboard.html", d=logica.dashboard(con()), ponto_status=ponto.status(con()),
                           ai_aan=ai.beschikbaar(), mail_in=intake.mailbox_ingesteld())


# ---------------------------------------------------------------- inbox (automatische verwerking)

@app.route("/inbox", methods=["GET", "POST"])
@met_fouten
def inbox():
    c = con()
    if request.method == "POST":
        bestanden = [f for f in request.files.getlist("bestanden") if f and f.filename]
        if not bestanden:
            raise ValueError("Kies of sleep één of meer facturen (pdf, e-factuur xml of foto)")
        resultaat = {"verwerkt": 0, "fout": 0, "genegeerd": 0}
        for f in bestanden:
            doc_id = intake.ontvang(c, f.filename, f.read(), "upload")
            st = c.execute("SELECT status FROM documenten WHERE id = ?", (doc_id,)).fetchone()["status"]
            resultaat[st] = resultaat.get(st, 0) + 1
        flash(f"{len(bestanden)} document(en) ontvangen: {resultaat['verwerkt']} automatisch verwerkt"
              + (f", {resultaat['fout']} met een probleem" if resultaat["fout"] else "")
              + (f", {resultaat['genegeerd']} geen factuur" if resultaat["genegeerd"] else ""), "ok")
        return redirect(url_for("goedkeuren") if resultaat["verwerkt"] and not resultaat["fout"] else url_for("inbox"))
    docs = c.execute("""SELECT d.*, i.status AS factuur_status, i.bedrag_incl_cent, r.naam AS relatie_naam
                        FROM documenten d LEFT JOIN inkoopfacturen i ON i.id = d.inkoopfactuur_id
                        LEFT JOIN relaties r ON r.id = i.relatie_id ORDER BY d.id DESC LIMIT 200""").fetchall()
    return render_template("inbox.html", docs=docs, ai_aan=ai.beschikbaar(), mail_in=intake.mailbox_ingesteld(),
                           mailadres=os.environ.get("IMAP_GEBRUIKER"), inbox_map=intake.INBOX_MAP)


@app.route("/inbox/<int:doc_id>/<actie>", methods=["POST"])
@met_fouten
def inbox_actie(doc_id, actie):
    c = con()
    if actie == "opnieuw":
        fid = intake.verwerk(c, doc_id)
        flash("Document opnieuw verwerkt" if fid else "Verwerken lukt nog steeds niet; voer de factuur handmatig in",
              "ok" if fid else "fout")
    elif actie == "negeer":
        c.execute("UPDATE documenten SET status = 'genegeerd' WHERE id = ?", (doc_id,))
        c.commit()
    return redirect(url_for("inbox"))


@app.route("/inbox/ophalen", methods=["POST"])
@met_fouten
def inbox_ophalen():
    n = intake.haal_mail_op(con()) + intake.verwerk_map(con())
    flash(f"{n} nieuwe document(en) opgehaald", "ok")
    return redirect(url_for("inbox"))


# ---------------------------------------------------------------- relaties

RELATIE_VELDEN = ("naam", "soort", "email", "iban", "bic", "adres", "postcode", "plaats", "kvk", "btw_nummer", "notities")


@app.route("/relaties")
def relaties():
    rijen = con().execute("""SELECT r.*, (SELECT COUNT(*) FROM inkoopfacturen WHERE relatie_id = r.id) AS n_inkoop,
                             (SELECT COUNT(*) FROM verkoopfacturen WHERE relatie_id = r.id) AS n_verkoop
                             FROM relaties r ORDER BY r.naam""").fetchall()
    return render_template("relaties.html", relaties=rijen)


@app.route("/relaties/nieuw", methods=["GET", "POST"])
@app.route("/relaties/<int:rid>", methods=["GET", "POST"])
@met_fouten
def relatie(rid=None):
    c = con()
    oud = c.execute("SELECT * FROM relaties WHERE id = ?", (rid,)).fetchone() if rid else None
    if rid and oud is None:
        abort(404)
    if request.method == "POST":
        velden = {k: request.form.get(k, "").strip() for k in RELATIE_VELDEN}
        velden["iban"] = logica.normaliseer_iban(velden["iban"])
        if velden["iban"] and not logica.iban_geldig(velden["iban"]):
            raise ValueError(f"IBAN {velden['iban']} is ongeldig")
        velden["auto_goedkeur_limiet_cent"] = naar_cent(request.form.get("auto_goedkeur_limiet"))
        velden["standaard_rekening"] = request.form.get("standaard_rekening") or None
        iban_gewijzigd = bool(oud) and logica.normaliseer_iban(oud["iban"]) != velden["iban"]
        velden["iban_geverifieerd"] = 1 if request.form.get("iban_geverifieerd") else 0
        if rid:
            c.execute(f"UPDATE relaties SET {', '.join(k + ' = ?' for k in velden)} WHERE id = ?", (*velden.values(), rid))
            db.log(c, "relatie gewijzigd", "relatie", rid, velden["naam"])
            if iban_gewijzigd:
                db.log(c, "IBAN gewijzigd", "relatie", rid, f"{oud['iban'] or '-'} → {velden['iban'] or '-'}")
        else:
            rid = c.execute(f"INSERT INTO relaties ({', '.join(velden)}, aangemaakt_op) "
                            f"VALUES ({', '.join('?' * len(velden))}, ?)", (*velden.values(), db.nu())).lastrowid
            db.log(c, "relatie aangemaakt", "relatie", rid, velden["naam"])
        c.commit()
        flash("Relatie opgeslagen", "ok")
        terug = request.args.get("terug") or ""
        return redirect(terug if terug.startswith("/") else url_for("relatie", rid=rid))
    inkoop = c.execute("SELECT * FROM inkoopfacturen WHERE relatie_id = ? ORDER BY factuurdatum DESC", (rid,)).fetchall() if rid else []
    verkoop = c.execute("SELECT * FROM verkoopfacturen WHERE relatie_id = ? ORDER BY factuurdatum DESC", (rid,)).fetchall() if rid else []
    return render_template("relatie.html", r=oud, inkoop=inkoop, verkoop=verkoop, rekeningen=grootboek.kostenrekeningen(c),
                           verkoop_incl={v["id"]: logica.verkoop_totalen(c, v["id"])["incl"] for v in verkoop})


# ---------------------------------------------------------------- inkoop & goedkeuren

INKOOP_SQL = """SELECT i.*, r.naam AS relatie_naam, r.iban AS relatie_iban, r.iban_geverifieerd,
                       g.naam AS rekening_naam
                FROM inkoopfacturen i JOIN relaties r ON r.id = i.relatie_id
                LEFT JOIN grootboekrekeningen g ON g.code = i.rekening"""


@app.route("/inkoop")
def inkoop():
    status = request.args.get("status")
    sql, args = INKOOP_SQL, ()
    if status:
        sql, args = sql + " WHERE i.status = ?", (status,)
    rijen = con().execute(sql + " ORDER BY i.id DESC LIMIT 500", args).fetchall()
    return render_template("inkoop.html", facturen=rijen, status=status)


@app.route("/inkoop/nieuw", methods=["GET", "POST"])
@met_fouten
def inkoop_nieuw():
    c = con()
    if request.method == "POST":
        f = request.form
        bestand = None
        upload = request.files.get("bestand")
        if upload and upload.filename:
            ext = os.path.splitext(upload.filename)[1].lower()
            if ext not in intake.TOEGESTAAN:
                raise ValueError("Alleen pdf, xml of foto's")
            os.makedirs(intake.UPLOAD_MAP, exist_ok=True)
            bestand = f"{secrets.token_hex(4)}-handmatig{ext}"
            upload.save(os.path.join(intake.UPLOAD_MAP, bestand))
        excl = naar_cent(f.get("bedrag_excl"))
        btw = naar_cent(f.get("btw")) if f.get("btw") else round(excl * int(f.get("btw_pct", 21)) / 100)
        fid = logica.voeg_inkoopfactuur_toe(
            c, int(f["relatie_id"]), f["factuurnummer"].strip(), f["factuurdatum"], f["vervaldatum"],
            f.get("omschrijving", ""), excl, btw, f.get("betalingskenmerk", "").strip(), bestand,
            rekening=f.get("rekening") or None, betaalwijze=f.get("betaalwijze", "overboeking"))
        status = c.execute("SELECT status FROM inkoopfacturen WHERE id = ?", (fid,)).fetchone()["status"]
        flash("Factuur ingevoerd en automatisch goedgekeurd" if status == "goedgekeurd"
              else "Factuur ingevoerd, staat klaar om goed te keuren", "ok")
        return redirect(url_for("inkoop_nieuw") if "nog_een" in f else url_for("goedkeuren"))
    crediteuren = c.execute("SELECT id, naam FROM relaties WHERE soort IN ('crediteur','beide') ORDER BY naam").fetchall()
    return render_template("inkoop_nieuw.html", crediteuren=crediteuren, rekeningen=grootboek.kostenrekeningen(c),
                           verval=(date.today() + timedelta(days=30)).isoformat())


@app.route("/inkoop/<int:fid>")
def inkoop_detail(fid):
    c = con()
    f = c.execute(INKOOP_SQL + " WHERE i.id = ?", (fid,)).fetchone() or abort(404)
    log = c.execute("SELECT * FROM logboek WHERE object_type = 'inkoop' AND object_id = ? ORDER BY id", (fid,)).fetchall()
    boekingen = c.execute("""SELECT p.datum, p.omschrijving, r.rekening, g.naam, r.debet_cent, r.credit_cent
                             FROM journaalposten p JOIN journaalregels r ON r.post_id = p.id
                             JOIN grootboekrekeningen g ON g.code = r.rekening
                             WHERE p.bron_type = 'inkoop' AND p.bron_id = ? ORDER BY p.id, r.id""", (fid,)).fetchall()
    return render_template("inkoop_detail.html", f=f, log=log, boekingen=boekingen,
                           rekeningen=grootboek.kostenrekeningen(c),
                           crediteuren=c.execute("SELECT id, naam FROM relaties WHERE soort IN ('crediteur','beide') ORDER BY naam").fetchall())


@app.route("/inkoop/<int:fid>/wijzig", methods=["POST"])
@met_fouten
def inkoop_wijzig(fid):
    f = request.form
    logica.wijzig_inkoopfactuur(con(), fid, {
        "relatie_id": int(f["relatie_id"]), "factuurnummer": f["factuurnummer"].strip(),
        "factuurdatum": f["factuurdatum"], "vervaldatum": f["vervaldatum"], "omschrijving": f.get("omschrijving", ""),
        "bedrag_excl_cent": naar_cent(f["bedrag_excl"]), "btw_cent": naar_cent(f["btw"]),
        "betalingskenmerk": f.get("betalingskenmerk", "").strip(), "rekening": f["rekening"],
        "betaalwijze": f["betaalwijze"]})
    flash("Factuur gecorrigeerd", "ok")
    return redirect(url_for("inkoop_detail", fid=fid))


@app.route("/bestand/<path:naam>")
def bestand(naam):
    return send_from_directory(intake.UPLOAD_MAP, naam)


@app.route("/goedkeuren")
def goedkeuren():
    c = con()
    rijen = c.execute(INKOOP_SQL + " WHERE i.status = 'ter_goedkeuring' ORDER BY i.vervaldatum").fetchall()
    return render_template("goedkeuren.html", facturen=rijen, rekeningen=grootboek.kostenrekeningen(c),
                           iban_ok={r["id"]: logica.iban_geldig(r["relatie_iban"]) for r in rijen},
                           ponto_aan=betalen.ponto_actief(c))


@app.route("/goedkeuren", methods=["POST"])
@met_fouten
def goedkeuren_post():
    c = con()
    ids = [int(i) for i in (request.form.getlist("ids") or [request.form.get("id")]) if i]
    if not ids:
        raise ValueError("Selecteer eerst een of meer facturen")
    ok = request.form.get("actie") == "goedkeuren"
    for fid in ids:
        rekening = request.form.get(f"rekening_{fid}")
        if rekening:
            logica.wijzig_inkoopfactuur(c, fid, {"rekening": rekening})
        logica.beoordeel(c, fid, ok, request.form.get("notitie", ""))
    c.commit()
    if ok:
        batch_id, url = betalen.na_goedkeuring(c, ids, url_for("betalen_terug", _external=True))
        if url:
            flash(f"{len(ids)} factuur/facturen goedgekeurd. Bevestig de betaling nu in je ABN AMRO-app.", "ok")
            return redirect(url)
    flash(f"{len(ids)} factuur/facturen {'goedgekeurd en geboekt' if ok else 'afgekeurd'}", "ok")
    terug = request.form.get("terug") or ""
    return redirect(terug if terug.startswith("/") else url_for("goedkeuren"))


# ---------------------------------------------------------------- betalingen

@app.route("/betalingen")
def betalingen():
    c = con()
    batches = c.execute("SELECT id, aangemaakt_op, uitvoerdatum, aantal, totaal_cent, bericht_id, kanaal, status, "
                        "ondertekenen_url FROM betaalbatches ORDER BY id DESC LIMIT 100").fetchall()
    batch_status = {b["id"]: c.execute(
        "SELECT SUM(status = 'betaald') betaald, SUM(status = 'in_batch') open FROM inkoopfacturen "
        "WHERE betaalbatch_id = ? AND bedrag_incl_cent > 0", (b["id"],)).fetchone() for b in batches}
    wachtend = c.execute(INKOOP_SQL + " WHERE i.status = 'goedgekeurd' AND i.betaalwijze != 'overboeking'").fetchall()
    return render_template("betalingen.html", voorstel=betalen.betaalvoorstel(c), batches=batches,
                           batch_status=batch_status, ponto_aan=betalen.ponto_actief(c), wachtend=wachtend)


@app.route("/betalingen/opdracht", methods=["POST"])
@met_fouten
def betaalopdracht_maken():
    batch_id, url = betalen.maak_betaalopdracht(con(), request.form.getlist("ids"),
                                                request.form.get("uitvoerdatum") or None,
                                                url_for("betalen_terug", _external=True))
    if url:
        return redirect(url)
    flash("Betaalbestand aangemaakt. Download het en upload het in ABN AMRO Internet Bankieren.", "ok")
    return redirect(url_for("betalingen", nieuw=batch_id))


@app.route("/betalingen/terug")
@met_fouten
def betalen_terug():
    betalen.werk_status_bij(con())
    open_ = con().execute("SELECT COUNT(*) FROM betaalbatches WHERE status = 'ter_ondertekening'").fetchone()[0]
    flash("Betaling bevestigd bij ABN AMRO. Zodra hij is afgeschreven gaat de factuur automatisch op betaald."
          if not open_ else "De betaling is nog niet bevestigd. Je kunt dat later alsnog doen via Betalingen.",
          "ok" if not open_ else "fout")
    return redirect(url_for("betalingen"))


@app.route("/betalingen/batch/<int:bid>.xml")
def batch_download(bid):
    b = con().execute("SELECT * FROM betaalbatches WHERE id = ?", (bid,)).fetchone() or abort(404)
    return Response(b["xml"], mimetype="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={b['bericht_id']}.xml"})


@app.route("/betalingen/batch/<int:bid>/annuleren", methods=["POST"])
def batch_annuleren(bid):
    betalen.annuleer(con(), bid)
    flash("Betaalopdracht geannuleerd; de facturen staan weer in het betaalvoorstel", "ok")
    return redirect(url_for("betalingen"))


# ---------------------------------------------------------------- verkoop

@app.route("/verkoop")
def verkoop():
    c = con()
    rijen = c.execute("""SELECT v.*, r.naam AS relatie_naam FROM verkoopfacturen v
                         JOIN relaties r ON r.id = v.relatie_id ORDER BY v.id DESC""").fetchall()
    return render_template("verkoop.html", facturen=rijen,
                           totalen={v["id"]: logica.verkoop_totalen(c, v["id"])["incl"] for v in rijen})


@app.route("/verkoop/nieuw", methods=["GET", "POST"])
@met_fouten
def verkoop_nieuw():
    c = con()
    if request.method == "POST":
        f = request.form
        regels = []
        for oms, aantal, prijs, btw in zip(f.getlist("omschrijving"), f.getlist("aantal"),
                                           f.getlist("prijs"), f.getlist("btw_pct")):
            if oms.strip():
                regels.append({"omschrijving": oms.strip(), "aantal": float((aantal or "1").replace(",", ".")),
                               "prijs_cent": naar_cent(prijs), "btw_pct": int(btw)})
        if not regels:
            raise ValueError("Voeg minstens één factuurregel toe")
        fid = logica.maak_verkoopfactuur(c, int(f["relatie_id"]), regels, f.get("factuurdatum"), f.get("notities", ""))
        if f.get("direct_mailen"):
            mail.verstuur_verkoopfactuur(c, fid)
            flash("Factuur aangemaakt, geboekt en gemaild naar de klant", "ok")
        else:
            flash("Verkoopfactuur aangemaakt (concept)", "ok")
        return redirect(url_for("verkoop_detail", fid=fid))
    debiteuren = c.execute("SELECT id, naam, email FROM relaties WHERE soort IN ('debiteur','beide') ORDER BY naam").fetchall()
    return render_template("verkoop_nieuw.html", debiteuren=debiteuren, nummer=logica.volgend_factuurnummer(c),
                           mail_aan=mail.ingesteld())


@app.route("/verkoop/<int:fid>")
def verkoop_detail(fid):
    c = con()
    v = c.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone() or abort(404)
    r = c.execute("SELECT * FROM relaties WHERE id = ?", (v["relatie_id"],)).fetchone()
    log = c.execute("SELECT * FROM logboek WHERE object_type = 'verkoop' AND object_id = ? ORDER BY id", (fid,)).fetchall()
    return render_template("verkoop_detail.html", v=v, r=r, t=logica.verkoop_totalen(c, fid), log=log,
                           mail_aan=mail.ingesteld())


@app.route("/verkoop/<int:fid>.pdf")
def verkoop_pdf(fid):
    v = con().execute("SELECT factuurnummer FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone() or abort(404)
    return Response(factuurdocument.maak_pdf(con(), fid), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={v['factuurnummer']}.pdf"})


@app.route("/verkoop/<int:fid>.xml")
def verkoop_ubl(fid):
    v = con().execute("SELECT factuurnummer FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone() or abort(404)
    return Response(factuurdocument.maak_ubl(con(), fid), mimetype="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={v['factuurnummer']}.xml"})


@app.route("/verkoop/<int:fid>/status", methods=["POST"])
@met_fouten
def verkoop_status(fid):
    logica.zet_verkoopstatus(con(), fid, request.form["status"])
    return redirect(url_for("verkoop_detail", fid=fid))


@app.route("/verkoop/<int:fid>/mailen", methods=["POST"])
@met_fouten
def verkoop_mailen(fid):
    mail.verstuur_verkoopfactuur(con(), fid)
    flash("Factuur gemaild (pdf + e-factuur) en geboekt", "ok")
    return redirect(url_for("verkoop_detail", fid=fid))


# ---------------------------------------------------------------- bank

@app.route("/bank", methods=["GET", "POST"])
@met_fouten
def bank():
    c = con()
    if request.method == "POST":
        upload = request.files.get("afschrift")
        if not upload or not upload.filename:
            raise ValueError("Kies een bankbestand (CAMT.053 XML of CSV)")
        nieuw, gekoppeld = logica.importeer_transacties(c, bankimport.lees_bestand(upload.filename, upload.read()))
        flash(f"{nieuw} nieuwe mutaties ingelezen, {gekoppeld} automatisch aan facturen gekoppeld", "ok")
        return redirect(url_for("bank"))
    filter_ = request.args.get("filter", "ongekoppeld")
    sql = "SELECT * FROM banktransacties"
    if filter_ == "ongekoppeld":
        sql += " WHERE gekoppeld_type IS NULL"
    rijen = c.execute(sql + " ORDER BY datum DESC, id DESC LIMIT 500").fetchall()
    open_inkoop = c.execute(INKOOP_SQL + " WHERE i.status IN ('ter_goedkeuring','goedgekeurd','in_batch') ORDER BY r.naam").fetchall()
    open_verkoop = c.execute("SELECT v.*, r.naam AS relatie_naam FROM verkoopfacturen v JOIN relaties r "
                             "ON r.id = v.relatie_id WHERE v.status != 'betaald' ORDER BY v.factuurnummer").fetchall()
    saldo = c.execute("SELECT COALESCE(SUM(debet_cent - credit_cent), 0) FROM journaalregels WHERE rekening = '1100'").fetchone()[0]
    return render_template("bank.html", transacties=rijen, filter=filter_, open_inkoop=open_inkoop, saldo=saldo,
                           open_verkoop=open_verkoop, rekeningen=grootboek.rekeningen(c), ponto_status=ponto.status(c),
                           verkoop_incl={v["id"]: logica.verkoop_totalen(c, v["id"])["incl"] for v in open_verkoop})


@app.route("/bank/<int:tid>/koppel", methods=["POST"])
@met_fouten
def bank_koppel(tid):
    keuze = request.form["keuze"]
    soort, waarde = keuze.split(":", 1)
    if soort == "grootboek":
        logica.boek_op_rekening(con(), tid, waarde)
        flash(f"Geboekt op {waarde}", "ok")
    else:
        logica.koppel(con(), tid, soort, int(waarde))
        flash("Gekoppeld: factuur staat op betaald", "ok")
    return redirect(url_for("bank"))


@app.route("/bank/ophalen", methods=["POST"])
@met_fouten
def bank_ophalen():
    nieuw, gekoppeld = planner.haal_bank_op(con())
    flash(f"{nieuw} nieuwe mutaties van ABN AMRO, {gekoppeld} automatisch gekoppeld", "ok")
    return redirect(url_for("bank"))


# ---------------------------------------------------------------- grootboek & rapportages

@app.route("/grootboek", methods=["GET", "POST"])
@met_fouten
def grootboek_scherm():
    c = con()
    if request.method == "POST":
        code, naam, soort = request.form["code"].strip(), request.form["naam"].strip(), request.form["soort"]
        if not code.isdigit() or not naam or soort not in ("activa", "passiva", "opbrengst", "kosten"):
            raise ValueError("Vul een numerieke code, een naam en een soort in")
        c.execute("INSERT INTO grootboekrekeningen (code, naam, soort) VALUES (?, ?, ?)", (code, naam, soort))
        db.log(c, "grootboekrekening toegevoegd", details=f"{code} {naam}")
        c.commit()
        flash("Rekening toegevoegd", "ok")
        return redirect(url_for("grootboek_scherm"))
    jaar = int(request.args.get("jaar", date.today().year))
    return render_template("grootboek.html", jaar=jaar, saldi=grootboek.saldi(c, f"{jaar}-01-01", f"{jaar + 1}-01-01"))


@app.route("/grootboek/<code>")
def grootboekkaart(code):
    c = con()
    rek = c.execute("SELECT * FROM grootboekrekeningen WHERE code = ?", (code,)).fetchone() or abort(404)
    jaar = int(request.args.get("jaar", date.today().year))
    return render_template("grootboekkaart.html", rek=rek, jaar=jaar,
                           regels=grootboek.grootboekkaart(c, code, f"{jaar}-01-01", f"{jaar + 1}-01-01"))


@app.route("/rapportages")
def rapportages():
    c = con()
    jaar = int(request.args.get("jaar", date.today().year))
    peildatum = min(date(jaar + 1, 1, 1), date.today() + timedelta(days=1)).isoformat()
    return render_template("rapportages.html", jaar=jaar, wv=grootboek.winst_en_verlies(c, jaar),
                           balans=grootboek.balans(c, peildatum), peildatum=peildatum,
                           maanden=logica.resultaat_per_maand(c, jaar))


@app.route("/btw")
def btw():
    jaar = int(request.args.get("jaar", date.today().year))
    return render_template("btw.html", jaar=jaar, kwartalen=[logica.btw_overzicht(con(), jaar, q) for q in (1, 2, 3, 4)])


@app.route("/logboek")
def logboek():
    return render_template("logboek.html", log=con().execute("SELECT * FROM logboek ORDER BY id DESC LIMIT 1000").fetchall())


# ---------------------------------------------------------------- instellingen & koppelingen

@app.route("/instellingen", methods=["GET", "POST"])
@met_fouten
def instellingen():
    c = con()
    if request.method == "POST":
        iban = logica.normaliseer_iban(request.form.get("iban"))
        if iban and not logica.iban_geldig(iban):
            raise ValueError(f"IBAN {iban} is ongeldig")
        for k in db.STANDAARD_INSTELLINGEN:
            if k in ("herinneringen_aan", "samenvatting_aan"):
                waarde = "1" if request.form.get(k) else "0"
            else:
                waarde = iban if k == "iban" else request.form.get(k, "").strip()
            db.zet_instelling(c, k, waarde)
        db.log(c, "instellingen gewijzigd")
        c.commit()
        flash("Instellingen opgeslagen", "ok")
        return redirect(url_for("instellingen"))
    return render_template("instellingen.html", ponto_status=ponto.status(c), ai_aan=ai.beschikbaar(),
                           mail_in=intake.mailbox_ingesteld(), mail_uit=mail.ingesteld(),
                           rekeningen=grootboek.kostenrekeningen(c),
                           redirect_uri=url_for("ponto_terug", _external=True))


@app.route("/koppelen/ponto")
@met_fouten
def ponto_koppelen():
    if not ponto.ingesteld():
        raise ValueError("Zet eerst PONTO_CLIENT_ID en PONTO_CLIENT_SECRET in config.env (zie README)")
    return redirect(ponto.autorisatie_url(con(), url_for("ponto_terug", _external=True)))


@app.route("/koppelen/ponto/terug")
@met_fouten
def ponto_terug():
    c = con()
    if request.args.get("error"):
        raise ValueError(f"Koppelen afgebroken: {request.args.get('error_description') or request.args['error']}")
    ponto.verwerk_terugkeer(c, request.args.get("code"), request.args.get("state"))
    ponto.kies_rekening(c, db.instellingen(c)["iban"])
    db.log(c, "ABN AMRO gekoppeld via Ponto")
    c.commit()
    flash("ABN AMRO is gekoppeld. Bankmutaties komen voortaan automatisch binnen.", "ok")
    return redirect(url_for("instellingen"))


@app.route("/koppelen/ponto/betalen-activeren")
@met_fouten
def ponto_betalen_activeren():
    return redirect(ponto.betalingen_activeren(con(), url_for("instellingen", _external=True)))


@app.route("/koppelen/ponto/ontkoppelen", methods=["POST"])
def ponto_ontkoppelen():
    ponto.ontkoppel(con())
    db.log(con(), "ABN AMRO-koppeling verbroken")
    con().commit()
    flash("Koppeling verbroken", "ok")
    return redirect(url_for("instellingen"))


if __name__ == "__main__":
    host, poort = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", 5000))
    planner.start(f"http://localhost:{poort}")
    app.run(host=host, port=poort, debug=bool(os.environ.get("DEBUG")), use_reloader=False)

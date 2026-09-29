"""Eigen boekhouding: facturen in, jij keurt goed, de app regelt de betalingen.

Start:  python app.py   ->  http://localhost:5000
"""

import os
import secrets
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from werkzeug.utils import secure_filename

import bankimport
import db
import logica
from logica import euro, naar_cent

UPLOAD_MAP = os.path.join(os.path.dirname(__file__), "uploads")

app = Flask(__name__)
app.secret_key = os.environ.get("APP_GEHEIM") or secrets.token_hex(16)
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
    return {"te_keuren_badge": con().execute(
        "SELECT COUNT(*) FROM inkoopfacturen WHERE status = 'ter_goedkeuring'").fetchone()[0],
        "inst": db.instellingen(con())}


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
            return redirect(request.args.get("volgende") or url_for("dashboard"))
        flash("Onjuist wachtwoord", "fout")
    return render_template("login.html")


@app.route("/uitloggen")
def uitloggen():
    session.clear()
    return redirect(url_for("login"))


def met_fouten(view):
    """Toont ValueErrors uit de bedrijfslogica als melding in plaats van een crash."""
    @wraps(view)
    def wrapper(*a, **kw):
        try:
            return view(*a, **kw)
        except ValueError as e:
            flash(str(e), "fout")
            return redirect(request.referrer or url_for("dashboard"))
    return wrapper


# ---------------------------------------------------------------- dashboard

@app.route("/")
def dashboard():
    return render_template("dashboard.html", d=logica.dashboard(con()))


# ---------------------------------------------------------------- relaties

RELATIE_VELDEN = ("naam", "soort", "email", "iban", "bic", "adres", "postcode", "plaats", "kvk", "btw_nummer", "notities")


@app.route("/relaties")
def relaties():
    rijen = con().execute("SELECT * FROM relaties ORDER BY naam").fetchall()
    return render_template("relaties.html", relaties=rijen)


@app.route("/relaties/nieuw", methods=["GET", "POST"])
@app.route("/relaties/<int:rid>", methods=["GET", "POST"])
@met_fouten
def relatie(rid=None):
    c = con()
    if request.method == "POST":
        velden = {k: request.form.get(k, "").strip() for k in RELATIE_VELDEN}
        velden["iban"] = logica.normaliseer_iban(velden["iban"])
        if velden["iban"] and not logica.iban_geldig(velden["iban"]):
            raise ValueError(f"IBAN {velden['iban']} is ongeldig")
        velden["auto_goedkeur_limiet_cent"] = naar_cent(request.form.get("auto_goedkeur_limiet"))
        if rid:
            c.execute(f"UPDATE relaties SET {', '.join(k + ' = ?' for k in velden)} WHERE id = ?",
                      (*velden.values(), rid))
            db.log(c, "relatie gewijzigd", "relatie", rid, velden["naam"])
        else:
            cur = c.execute(f"INSERT INTO relaties ({', '.join(velden)}, aangemaakt_op) "
                            f"VALUES ({', '.join('?' * len(velden))}, ?)", (*velden.values(), db.nu()))
            rid = cur.lastrowid
            db.log(c, "relatie aangemaakt", "relatie", rid, velden["naam"])
        c.commit()
        flash("Relatie opgeslagen", "ok")
        return redirect(request.args.get("terug") or url_for("relatie", rid=rid))
    r = c.execute("SELECT * FROM relaties WHERE id = ?", (rid,)).fetchone() if rid else None
    if rid and r is None:
        abort(404)
    inkoop = c.execute("SELECT * FROM inkoopfacturen WHERE relatie_id = ? ORDER BY factuurdatum DESC", (rid,)).fetchall() if rid else []
    verkoop = c.execute("SELECT * FROM verkoopfacturen WHERE relatie_id = ? ORDER BY factuurdatum DESC", (rid,)).fetchall() if rid else []
    return render_template("relatie.html", r=r, inkoop=inkoop, verkoop=verkoop,
                           verkoop_incl={v["id"]: logica.verkoop_totalen(c, v["id"])["incl"] for v in verkoop})


# ---------------------------------------------------------------- inkoop & goedkeuren

INKOOP_SQL = """SELECT i.*, r.naam AS relatie_naam, r.iban AS relatie_iban FROM inkoopfacturen i
                JOIN relaties r ON r.id = i.relatie_id"""


@app.route("/inkoop")
def inkoop():
    status = request.args.get("status")
    sql, args = INKOOP_SQL, ()
    if status:
        sql, args = sql + " WHERE i.status = ?", (status,)
    rijen = con().execute(sql + " ORDER BY i.vervaldatum DESC", args).fetchall()
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
            os.makedirs(UPLOAD_MAP, exist_ok=True)
            bestand = f"{secrets.token_hex(4)}-{secure_filename(upload.filename)}"
            upload.save(os.path.join(UPLOAD_MAP, bestand))
        excl = naar_cent(f.get("bedrag_excl"))
        btw = naar_cent(f.get("btw")) if f.get("btw") else round(excl * int(f.get("btw_pct", 21)) / 100)
        fid = logica.voeg_inkoopfactuur_toe(
            c, int(f["relatie_id"]), f["factuurnummer"].strip(), f["factuurdatum"], f["vervaldatum"],
            f.get("omschrijving", ""), excl, btw, f.get("betalingskenmerk", "").strip(), bestand)
        status = c.execute("SELECT status FROM inkoopfacturen WHERE id = ?", (fid,)).fetchone()["status"]
        flash("Factuur ingevoerd en automatisch goedgekeurd" if status == "goedgekeurd"
              else "Factuur ingevoerd, staat klaar om goed te keuren", "ok")
        return redirect(url_for("inkoop_nieuw") if "nog_een" in f else url_for("goedkeuren"))
    crediteuren = c.execute("SELECT id, naam FROM relaties WHERE soort IN ('crediteur','beide') ORDER BY naam").fetchall()
    return render_template("inkoop_nieuw.html", crediteuren=crediteuren, vandaag=date.today().isoformat(),
                           verval=(date.today() + timedelta(days=30)).isoformat())


@app.route("/inkoop/<int:fid>")
def inkoop_detail(fid):
    f = con().execute(INKOOP_SQL + " WHERE i.id = ?", (fid,)).fetchone() or abort(404)
    log = con().execute("SELECT * FROM logboek WHERE object_type = 'inkoop' AND object_id = ? ORDER BY id", (fid,)).fetchall()
    return render_template("inkoop_detail.html", f=f, log=log)


@app.route("/bestand/<path:naam>")
def bestand(naam):
    return send_from_directory(UPLOAD_MAP, naam)


@app.route("/goedkeuren")
def goedkeuren():
    rijen = con().execute(INKOOP_SQL + " WHERE i.status = 'ter_goedkeuring' ORDER BY i.vervaldatum").fetchall()
    return render_template("goedkeuren.html", facturen=rijen,
                           iban_ok={r["id"]: logica.iban_geldig(r["relatie_iban"]) for r in rijen},
                           vandaag=date.today().isoformat())


@app.route("/goedkeuren", methods=["POST"])
@met_fouten
def goedkeuren_post():
    c = con()
    ids = request.form.getlist("ids") or [request.form.get("id")]
    ok = request.form.get("actie") == "goedkeuren"
    for fid in filter(None, ids):
        logica.beoordeel(c, int(fid), ok, request.form.get("notitie", ""))
    c.commit()
    flash(f"{len([i for i in ids if i])} factuur/facturen {'goedgekeurd' if ok else 'afgekeurd'}", "ok")
    return redirect(request.form.get("terug") or url_for("goedkeuren"))


# ---------------------------------------------------------------- betalingen

@app.route("/betalingen")
def betalingen():
    c = con()
    batches = c.execute("SELECT id, aangemaakt_op, uitvoerdatum, aantal, totaal_cent, bericht_id FROM betaalbatches "
                        "ORDER BY id DESC").fetchall()
    batch_status = {b["id"]: c.execute(
        "SELECT SUM(status = 'betaald') betaald, SUM(status = 'in_batch') open FROM inkoopfacturen "
        "WHERE betaalbatch_id = ?", (b["id"],)).fetchone() for b in batches}
    return render_template("betalingen.html", voorstel=logica.betaalvoorstel(c), batches=batches,
                           batch_status=batch_status)


@app.route("/betalingen/batch", methods=["POST"])
@met_fouten
def batch_maken():
    batch_id = logica.maak_betaalbatch(con(), request.form.getlist("ids"), request.form.get("uitvoerdatum") or None)
    flash("Betaalbatch aangemaakt. Download het bestand en upload het bij je bank.", "ok")
    return redirect(url_for("betalingen", nieuw=batch_id))


@app.route("/betalingen/batch/<int:bid>.xml")
def batch_download(bid):
    b = con().execute("SELECT * FROM betaalbatches WHERE id = ?", (bid,)).fetchone() or abort(404)
    return Response(b["xml"], mimetype="application/xml",
                    headers={"Content-Disposition": f"attachment; filename={b['bericht_id']}.xml"})


@app.route("/betalingen/batch/<int:bid>/annuleren", methods=["POST"])
def batch_annuleren(bid):
    logica.annuleer_batch(con(), bid)
    flash("Batch geannuleerd; facturen staan weer in het betaalvoorstel", "ok")
    return redirect(url_for("betalingen"))


# ---------------------------------------------------------------- verkoop

@app.route("/verkoop")
def verkoop():
    c = con()
    rijen = c.execute("""SELECT v.*, r.naam AS relatie_naam FROM verkoopfacturen v
                         JOIN relaties r ON r.id = v.relatie_id ORDER BY v.id DESC""").fetchall()
    return render_template("verkoop.html", facturen=rijen, vandaag=date.today().isoformat(),
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
                regels.append({"omschrijving": oms.strip(), "aantal": float(aantal.replace(",", ".") or 1),
                               "prijs_cent": naar_cent(prijs), "btw_pct": int(btw)})
        if not regels:
            raise ValueError("Voeg minstens één factuurregel toe")
        fid = logica.maak_verkoopfactuur(c, int(f["relatie_id"]), regels, f.get("factuurdatum"), f.get("notities", ""))
        flash("Verkoopfactuur aangemaakt (concept)", "ok")
        return redirect(url_for("verkoop_detail", fid=fid))
    debiteuren = c.execute("SELECT id, naam FROM relaties WHERE soort IN ('debiteur','beide') ORDER BY naam").fetchall()
    return render_template("verkoop_nieuw.html", debiteuren=debiteuren, vandaag=date.today().isoformat(),
                           nummer=logica.volgend_factuurnummer(c))


@app.route("/verkoop/<int:fid>")
def verkoop_detail(fid):
    c = con()
    v = c.execute("SELECT * FROM verkoopfacturen WHERE id = ?", (fid,)).fetchone() or abort(404)
    r = c.execute("SELECT * FROM relaties WHERE id = ?", (v["relatie_id"],)).fetchone()
    return render_template("verkoop_detail.html", v=v, r=r, t=logica.verkoop_totalen(c, fid),
                           print_modus="print" in request.args)


@app.route("/verkoop/<int:fid>/status", methods=["POST"])
def verkoop_status(fid):
    c = con()
    status = request.form["status"]
    if status not in ("concept", "verzonden", "betaald"):
        abort(400)
    c.execute("UPDATE verkoopfacturen SET status = ?, betaald_op = ? WHERE id = ?",
              (status, date.today().isoformat() if status == "betaald" else None, fid))
    db.log(c, f"verkoopfactuur {status}", "verkoop", fid)
    c.commit()
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
        transacties = bankimport.lees_bestand(upload.filename, upload.read())
        nieuw, gekoppeld = logica.importeer_transacties(c, transacties)
        flash(f"{nieuw} nieuwe transacties ingelezen, {gekoppeld} automatisch aan facturen gekoppeld", "ok")
        return redirect(url_for("bank"))
    filter_ = request.args.get("filter", "ongekoppeld")
    sql = "SELECT * FROM banktransacties"
    if filter_ == "ongekoppeld":
        sql += " WHERE gekoppeld_type IS NULL"
    rijen = c.execute(sql + " ORDER BY datum DESC, id DESC LIMIT 500").fetchall()
    open_inkoop = c.execute(INKOOP_SQL + " WHERE i.status IN ('ter_goedkeuring','goedgekeurd','in_batch') "
                            "ORDER BY r.naam").fetchall()
    open_verkoop = c.execute("SELECT v.*, r.naam AS relatie_naam FROM verkoopfacturen v JOIN relaties r "
                             "ON r.id = v.relatie_id WHERE v.status != 'betaald' ORDER BY v.factuurnummer").fetchall()
    return render_template("bank.html", transacties=rijen, filter=filter_, open_inkoop=open_inkoop,
                           open_verkoop=open_verkoop,
                           verkoop_incl={v["id"]: logica.verkoop_totalen(c, v["id"])["incl"] for v in open_verkoop})


@app.route("/bank/<int:tid>/koppel", methods=["POST"])
@met_fouten
def bank_koppel(tid):
    soort, fid = request.form["factuur"].split(":")
    logica.koppel(con(), tid, soort, int(fid))
    flash("Transactie gekoppeld, factuur staat op betaald", "ok")
    return redirect(url_for("bank"))


# ---------------------------------------------------------------- btw, logboek, instellingen

@app.route("/btw")
def btw():
    jaar = int(request.args.get("jaar", date.today().year))
    kwartalen = [logica.btw_overzicht(con(), jaar, q) for q in (1, 2, 3, 4)]
    return render_template("btw.html", jaar=jaar, kwartalen=kwartalen)


@app.route("/logboek")
def logboek():
    return render_template("logboek.html", log=con().execute("SELECT * FROM logboek ORDER BY id DESC LIMIT 500").fetchall())


@app.route("/instellingen", methods=["GET", "POST"])
@met_fouten
def instellingen():
    c = con()
    if request.method == "POST":
        iban = logica.normaliseer_iban(request.form.get("iban"))
        if iban and not logica.iban_geldig(iban):
            raise ValueError(f"IBAN {iban} is ongeldig")
        for k in db.STANDAARD_INSTELLINGEN:
            waarde = iban if k == "iban" else request.form.get(k, "").strip()
            c.execute("UPDATE instellingen SET waarde = ? WHERE sleutel = ?", (waarde, k))
        db.log(c, "instellingen gewijzigd")
        c.commit()
        flash("Instellingen opgeslagen", "ok")
        return redirect(url_for("instellingen"))
    return render_template("instellingen.html")


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
            debug=bool(os.environ.get("DEBUG")))

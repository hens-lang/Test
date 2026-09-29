"""Achtergrondtaken die draaien zolang de app aanstaat:
- elke 5 minuten: mailbox en inbox-map verwerken, status van betaalopdrachten bij de bank nagaan
- elk uur: bankmutaties ophalen via Ponto en automatisch afletteren
- elke ochtend: betalingsherinneringen en de dagelijkse samenvatting."""

import os
import threading
import time
import traceback
from datetime import date, datetime, timedelta

import betalen
import db
import intake
import logica
import mail
import ponto

INTERVAL = 300


def _mag(con, sleutel, na):
    """Geeft True als taak `sleutel` voor het laatst langer dan `na` geleden is gedraaid (en noteert nu)."""
    r = con.execute("SELECT waarde FROM instellingen WHERE sleutel = ?", (f"taak_{sleutel}",)).fetchone()
    if r and r["waarde"] and datetime.fromisoformat(r["waarde"]) > datetime.now() - na:
        return False
    db.zet_instelling(con, f"taak_{sleutel}", db.nu())
    con.commit()
    return True


def _probeer(con, naam, functie):
    try:
        return functie()
    except Exception as e:  # noqa: BLE001 - een fout in één taak mag de rest niet stoppen
        con.rollback()
        db.log(con, f"achtergrondtaak '{naam}' mislukt", details=str(e)[:300])
        con.commit()
        traceback.print_exc()


def haal_bank_op(con):
    if not betalen.ponto_actief(con):
        return 0, 0
    st = ponto.status(con)
    sinds = (st["laatste_sync"] or "")[:10] or (date.today() - timedelta(days=90)).isoformat()
    sinds = (date.fromisoformat(sinds) - timedelta(days=3)).isoformat()   # overlap: dubbele worden overgeslagen
    ponto.synchroniseer(con)
    resultaat = logica.importeer_transacties(con, ponto.transacties(con, sinds))
    ponto.markeer_sync(con)
    return resultaat


def ronde(con, app_url):
    _probeer(con, "inbox-map", lambda: intake.verwerk_map(con))
    if intake.mailbox_ingesteld():
        _probeer(con, "mailbox", lambda: intake.haal_mail_op(con))
    if betalen.ponto_actief(con):
        _probeer(con, "status betaalopdrachten", lambda: betalen.werk_status_bij(con))
        if _mag(con, "bank", timedelta(minutes=55)):
            _probeer(con, "bankmutaties", lambda: haal_bank_op(con))
    if datetime.now().hour >= 8 and _mag(con, "ochtend", timedelta(hours=20)):
        _probeer(con, "herinneringen", lambda: mail.stuur_herinneringen(con))
        _probeer(con, "samenvatting", lambda: mail.stuur_samenvatting(con, app_url))
    # documenten die eerder faalden door een tijdelijke storing opnieuw proberen
    for doc in con.execute("SELECT id FROM documenten WHERE status = 'fout' AND "
                           "(melding LIKE '%later opnieuw%' OR melding LIKE '%verbinding%')").fetchall():
        _probeer(con, "document opnieuw", lambda: intake.verwerk(con, doc["id"]))


def start(app_url):
    if os.environ.get("PLANNER_UIT"):
        return

    def lus():
        con = db.verbind()
        db.initialiseer(con)
        while True:
            ronde(con, app_url)
            time.sleep(INTERVAL)

    threading.Thread(target=lus, name="planner", daemon=True).start()

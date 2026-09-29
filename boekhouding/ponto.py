"""Koppeling met ABN AMRO via Ponto (Isabel Group, PSD2-vergunninghouder).

- Rekeninginformatie: bankmutaties komen automatisch binnen (geen afschriften meer inlezen).
- Betaalopdrachten: na goedkeuren zet de app een (bulk)betaling klaar; jij bevestigt die in de ABN-app.

Instellen in config.env (gegevens uit het Ponto-dashboard, onder 'Integrations'):
    PONTO_CLIENT_ID, PONTO_CLIENT_SECRET, PONTO_CERT (pad naar certificate.pem),
    PONTO_KEY (pad naar private_key.pem), PONTO_KEY_WACHTWOORD, PONTO_OMGEVING (sandbox / live)
"""

import base64
import hashlib
import json
import os
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from db import MAP, nu

API = "https://api.ibanity.com/ponto-connect"
AUTORISATIE = {"sandbox": "https://sandbox-authorization.myponto.com/oauth2/auth",
               "live": "https://authorization.myponto.com/oauth2/auth"}


class PontoFout(Exception):
    pass


def ingesteld():
    return bool(os.environ.get("PONTO_CLIENT_ID") and os.environ.get("PONTO_CLIENT_SECRET"))


def _api():
    return os.environ.get("PONTO_API_URL", API).rstrip("/")


def _pad(p):
    return p if not p or os.path.isabs(p) else os.path.join(MAP, p)


def _ssl():
    ctx = ssl.create_default_context()
    cert, key = _pad(os.environ.get("PONTO_CERT")), _pad(os.environ.get("PONTO_KEY"))
    if cert and key:
        ctx.load_cert_chain(cert, key, os.environ.get("PONTO_KEY_WACHTWOORD") or None)
    return ctx


# ---------------------------------------------------------------- opslag van tokens


def _lees(con):
    r = con.execute("SELECT data FROM koppelingen WHERE naam = 'ponto'").fetchone()
    return json.loads(r["data"]) if r else {}


def _schrijf(con, data):
    con.execute("INSERT INTO koppelingen (naam, data) VALUES ('ponto', ?) "
                "ON CONFLICT(naam) DO UPDATE SET data = excluded.data", (json.dumps(data),))
    con.commit()


def status(con):
    d = _lees(con)
    return {"ingesteld": ingesteld(), "verbonden": bool(d.get("refresh_token")), "rekening": d.get("rekening_iban"),
            "laatste_sync": d.get("laatste_sync"), "betalen_actief": d.get("betalen_actief", False)}


def ontkoppel(con):
    con.execute("DELETE FROM koppelingen WHERE naam = 'ponto'")
    con.commit()


# ---------------------------------------------------------------- OAuth (eenmalig koppelen)


def autorisatie_url(con, redirect_uri):
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    _schrijf(con, {**_lees(con), "pkce": verifier, "state": state, "redirect_uri": redirect_uri})
    params = {"client_id": os.environ["PONTO_CLIENT_ID"], "redirect_uri": redirect_uri, "response_type": "code",
              "scope": "ai pi offline_access", "state": state, "code_challenge": challenge,
              "code_challenge_method": "S256"}
    basis = os.environ.get("PONTO_AUTORISATIE_URL") or AUTORISATIE[os.environ.get("PONTO_OMGEVING", "live")]
    return f"{basis}?{urllib.parse.urlencode(params)}"


def _token_aanvraag(velden):
    auth = base64.b64encode(f"{os.environ['PONTO_CLIENT_ID']}:{os.environ['PONTO_CLIENT_SECRET']}".encode()).decode()
    req = urllib.request.Request(f"{_api()}/oauth2/token", data=urllib.parse.urlencode(velden).encode(),
                                 headers={"Authorization": f"Basic {auth}", "Accept": "application/vnd.api+json",
                                          "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, context=_ssl(), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise PontoFout(f"Ponto weigerde de aanmelding ({e.code}): {e.read()[:300].decode(errors='replace')}")


def verwerk_terugkeer(con, code, state):
    d = _lees(con)
    if not state or state != d.get("state"):
        raise PontoFout("Ongeldige terugkeer van Ponto (state komt niet overeen); probeer opnieuw te koppelen")
    t = _token_aanvraag({"grant_type": "authorization_code", "code": code, "code_verifier": d["pkce"],
                         "redirect_uri": d["redirect_uri"], "client_id": os.environ["PONTO_CLIENT_ID"]})
    d.update(access_token=t["access_token"], refresh_token=t["refresh_token"],
             verloopt=time.time() + int(t.get("expires_in", 1800)) - 60)
    for k in ("pkce", "state"):
        d.pop(k, None)
    _schrijf(con, d)


def _token(con):
    d = _lees(con)
    if not d.get("refresh_token"):
        raise PontoFout("ABN AMRO is nog niet gekoppeld (Instellingen → Bank koppelen)")
    if d.get("access_token") and d.get("verloopt", 0) > time.time():
        return d["access_token"]
    t = _token_aanvraag({"grant_type": "refresh_token", "refresh_token": d["refresh_token"],
                         "client_id": os.environ["PONTO_CLIENT_ID"]})
    d.update(access_token=t["access_token"], refresh_token=t.get("refresh_token", d["refresh_token"]),
             verloopt=time.time() + int(t.get("expires_in", 1800)) - 60)
    _schrijf(con, d)
    return d["access_token"]


def _verzoek(con, methode, pad, body=None):
    url = pad if pad.startswith("http") else f"{_api()}{pad}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=methode, headers={
        "Authorization": f"Bearer {_token(con)}", "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json", "Ibanity-Idempotency-Key": secrets.token_hex(16)})
    try:
        with urllib.request.urlopen(req, context=_ssl(), timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        tekst = e.read()[:500].decode(errors="replace")
        raise PontoFout(f"Ponto gaf een fout ({e.code}) bij {methode} {pad}: {tekst}")
    except urllib.error.URLError as e:
        raise PontoFout(f"Geen verbinding met Ponto: {e.reason}")


# ---------------------------------------------------------------- rekening & mutaties


def rekeningen(con):
    """Alle rekeningen die in Ponto aan deze koppeling zijn gegeven."""
    return [{"id": r["id"], "iban": r["attributes"].get("reference", ""),
             "naam": r["attributes"].get("description") or r["attributes"].get("product") or "",
             "saldo": r["attributes"].get("currentBalance")}
            for r in _verzoek(con, "GET", "/accounts")["data"]]


def kies_rekening(con, eigen_iban=None, rekening_id=None):
    """Koppelt de rekening met dit id, of anders die met het IBAN uit Instellingen.
    Geeft None terug als er geen passende rekening is (dan kiest de gebruiker zelf)."""
    alle = _verzoek(con, "GET", "/accounts")["data"]
    iban = (eigen_iban or "").replace(" ", "").upper()
    match = next((r for r in alle if (rekening_id and r["id"] == rekening_id) or
                  (not rekening_id and iban and r["attributes"].get("reference", "").replace(" ", "").upper() == iban)),
                 None)
    if match is None:
        return None
    d = _lees(con)
    d.update(rekening_id=match["id"], rekening_iban=match["attributes"].get("reference", "").replace(" ", "").upper(),
             betalen_actief=bool(match["attributes"].get("availableForPayments", True)))
    _schrijf(con, d)
    return match


def _rekening_id(con):
    d = _lees(con)
    if not d.get("rekening_id"):
        raise PontoFout("Nog geen bankrekening gekozen; open Instellingen → Bank koppelen")
    return d["rekening_id"]


def synchroniseer(con, wacht=20):
    """Vraagt Ponto om nieuwe mutaties bij ABN op te halen en wacht kort tot dat klaar is."""
    rid = _rekening_id(con)
    s = _verzoek(con, "POST", "/synchronizations", {"data": {"type": "synchronization", "attributes": {
        "resourceType": "account", "resourceId": rid, "subtype": "accountTransactions"}}})
    einde = time.time() + wacht
    while time.time() < einde:
        st = _verzoek(con, "GET", f"/synchronizations/{s['data']['id']}")["data"]["attributes"]["status"]
        if st in ("success", "error"):
            return st
        time.sleep(2)
    return "pending"


def transacties(con, sinds=None):
    """Haalt mutaties op in het formaat van logica.importeer_transacties (nieuwste eerst, tot 'sinds')."""
    rid = _rekening_id(con)
    url, resultaat = f"/accounts/{rid}/transactions?page%5Blimit%5D=100", []
    while url:
        antwoord = _verzoek(con, "GET", url)
        for t in antwoord["data"]:
            a = t["attributes"]
            datum = (a.get("valueDate") or a.get("executionDate") or "")[:10]
            if sinds and datum < sinds:
                return resultaat
            resultaat.append({
                "datum": datum,
                "bedrag_cent": round(float(a["amount"]) * 100),
                "tegenrekening": a.get("counterpartReference") or "",
                "naam": a.get("counterpartName") or "",
                "omschrijving": a.get("remittanceInformation") or a.get("description") or "",
                "referentie": a.get("endToEndId") or "",
                "import_sleutel": f"ponto-{t['id']}",
            })
        url = antwoord.get("links", {}).get("next")
    return resultaat


def markeer_sync(con):
    d = _lees(con)
    d["laatste_sync"] = nu()
    _schrijf(con, d)


# ---------------------------------------------------------------- betalen


def betalingen_activeren(con, redirect_uri):
    """Eenmalig: betaalopdrachten toestaan voor je organisatie in Ponto."""
    a = _verzoek(con, "POST", "/payment-activation-requests", {"data": {
        "type": "paymentActivationRequest", "attributes": {"redirectUri": redirect_uri}}})
    return a["data"]["links"]["redirect"]


def bulkbetaling(con, referentie, uitvoerdatum, posten, redirect_uri):
    """posten: dicts met end_to_end, bedrag_cent, naam, iban, omschrijving, is_kenmerk.
    Geeft (ponto-id, ondertekenen-url) terug. Jij bevestigt de batch daarna in je ABN-app."""
    betalingen = []
    for p in posten:
        kenmerk = "".join(ch for ch in p["omschrijving"] if ch.isdigit()) if p.get("is_kenmerk") else ""
        gestructureerd = len(kenmerk) == 16
        betalingen.append({
            "remittanceInformation": kenmerk if gestructureerd else p["omschrijving"][:140],
            "remittanceInformationType": "structured" if gestructureerd else "unstructured",
            "currency": "EUR",
            "amount": round(p["bedrag_cent"] / 100, 2),
            "creditorName": p["naam"][:70],
            "creditorAccountReference": p["iban"],
            "creditorAccountReferenceType": "IBAN",
            "endToEndId": p["end_to_end"],
        })
    a = _verzoek(con, "POST", f"/accounts/{_rekening_id(con)}/bulk-payments", {"data": {
        "type": "bulkPayment", "attributes": {
            "reference": referentie[:35], "requestedExecutionDate": uitvoerdatum, "redirectUri": redirect_uri,
            "batchBookingPreferred": True, "payments": betalingen}}})
    return a["data"]["id"], a["data"]["links"]["redirect"]


def bulkbetaling_status(con, ponto_id):
    """unsigned / accepted-... / rejected / cancelled (zoals Ponto het rapporteert)."""
    a = _verzoek(con, "GET", f"/accounts/{_rekening_id(con)}/bulk-payments/{ponto_id}")
    return a["data"]["attributes"]["status"]

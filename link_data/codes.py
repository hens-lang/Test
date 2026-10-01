"""Resultaatcodes van Steam/Belstat en de afgeleide groepen. Eén plek, overal gebruikt."""

OMSCHRIJVING = {
    100: "Afspraak ingepland",
    101: "Overdracht/lead",
    200: "Geen interesse",
    201: "Al voorzien",
    202: "Niet geschikt",
    300: "Onjuist telefoonnummer",
    400: "Geen gehoor",
    401: "Voicemail",
    402: "Bezet",
    403: "Nabellen volgende dag",
    500: "Terugbelafspraak",
    501: "Informatiemail sturen",
    502: "Terugbelverzoek achtergelaten",
}

RESULTAAT = {100, 101}
BEREIKT = {100, 101, 200, 201, 500, 501}
NIET_GESCHIKT = {202}
NIET_BEREIKT = {400, 401, 402, 403, 502}
DATA_FOUT = {300}
PIJPLIJN = {500, 501}
LEAD = 101

GROEPEN = ["bereikt", "niet_geschikt", "niet_bereikt", "data_fout", "overig"]


def groep(code):
    """Funnelgroep van een (genormaliseerde) resultaatcode."""
    if code in BEREIKT:
        return "bereikt"
    if code in NIET_GESCHIKT:
        return "niet_geschikt"
    if code in NIET_BEREIKT:
        return "niet_bereikt"
    if code in DATA_FOUT:
        return "data_fout"
    return "overig"


def normaliseer(raw):
    """'MAX-400' -> (400, True); '100' -> (100, False); onbekend -> (None, False)."""
    if raw is None:
        return None, False
    s = str(raw).strip().upper()
    is_max = s.startswith("MAX-")
    if is_max:
        s = s[4:]
    try:
        return int(float(s)), is_max
    except ValueError:
        return None, is_max

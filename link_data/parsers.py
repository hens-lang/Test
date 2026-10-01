"""Parsers voor Steam Connect / Belstat-exports.

Alle exports zijn HTML-tabellen met een .xls-extensie. `parse_bestand(pad)` herkent
het type automatisch en geeft een `Export` met een genormaliseerde DataFrame terug.

Type A  belexport (Management module, tabel idTableRapportage, loadRecord per rij)
Type B  urenexport (PayableHoursPerDay: één rij per beller per dag)
Type C  historie-export (één rij per belpoging), herkend aan de kolommen
Type F  factuur van een beller (PDF): nummer, datum, week, uren, bedrag excl. btw
Type S  contactstatistieken per agent x campagne x bellijst (Excel-XML, "contactstatistics_agents"):
        alle contactpogingen, hits, afgehandeld en de beltijd per campagne
Type P  belpogingen ("Call attempts statuses"): elke gekozen poging met tijdstip, beller, campagne en
        of het gesprek verbonden werd (geen resultaatcode). Het gekozen nummer wordt niet bewaard.
Type L  in- en uitlogtijden ("LogIn_Out"): sessies per medewerker (IP-adres wordt niet bewaard)
Type R  contactresultaten per campagne ("callresults"): aantal pogingen per resultaatcode over alle
        pogingen, plus voorraad van de bellijst (totaal, onaangeraakt, niet afgehandeld)
Type V  verkoopfactuur van LINK. aan een opdrachtgever (PDF): één regel per factuurregel,
        met werkperiode-nummer en periode

De genormaliseerde kolommen van A en C zijn gelijk (CONTACT_KOLOMMEN), zodat het model
en de wekelijkse klantrapportages dezelfde functies kunnen gebruiken.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from . import codes

CONTACT_KOLOMMEN = [
    "sleutel", "bron", "campagne_pid", "ctpid", "historiepid", "agent_raw", "agent_pid",
    "project", "campagne_naam", "bedrijf", "contact_dt", "datum", "uur",
    "code", "code_raw", "is_max", "omschrijving", "gespreksduur_s", "prepare_s", "dial_s",
    "finish_s", "aantal_pogingen", "is_hit", "is_contactmoment", "is_afgehandeld", "afspraak_dt", "memo",
]

UREN_TIJDKOLOMMEN = {
    "Wachten": "wachten_s", "Laden": "laden_s", "Prepare": "prepare_s", "Dial": "dial_s",
    "Talking": "talking_s", "Finish": "finish_s", "Chat": "chat_s", "Social media": "social_s",
    "Totaaltijd campagnes": "campagnetijd_s", "Onbetaalde tijd campagnes": "onbetaald_campagne_s",
    "Persoonlijke verzorging": "verzorging_s", "Lange pauze": "lange_pauze_s",
    "Korte pauze": "korte_pauze_s", "Menu": "menu_s", "Algemene training": "training_alg_s",
    "Persoonlijke training": "training_pers_s", "Unbound wait": "unbound_wait_s",
    "Totaal pauzes": "pauzes_s", "Onbetaalde pauzes": "onbetaalde_pauzes_s",
    "Totaal gewerkt": "gewerkt_s", "Te betalen": "te_betalen_s", "Betaald": "betaald_s", "DND": "dnd_s",
}
UREN_TELKOLOMMEN = {"Pogingen": "pogingen", "Records": "records", "Hits": "hits",
                    "Afgehandelde": "afgehandeld"}
UREN_KOLOMMEN = ["datum", "agent_raw", "afdeling", *UREN_TELKOLOMMEN.values(), *UREN_TIJDKOLOMMEN.values()]

FACTUUR_KOLOMMEN = ["sleutel", "afzender", "factuurnr", "factuurdatum", "week_genoemd", "uren",
                    "tarief", "bedrag_excl", "omschrijving"]

VERKOOP_KOLOMMEN = ["sleutel", "factuurnr", "klant_naam", "debiteurnr", "factuurdatum", "regel",
                    "omschrijving", "werkperiode_nr", "periode_van", "periode_tot", "bedrag_excl", "is_lead", "bron", "status"]

STATS_KOLOMMEN = ["sleutel", "peildatum", "agent_raw", "campagne", "project", "contactpogingen", "calls", "hits",
                  "afgehandeld", "recordtijd_s", "wachten_s", "laden_s", "prepare_s", "dial_s", "gesprek_s",
                  "finish_s"]

POGING_KOLOMMEN = ["sleutel", "campagne", "project", "ctpid", "chpid", "poging_dt", "datum", "uur", "agent_raw",
                   "verbonden", "status", "sip"]

SESSIE_KOLOMMEN = ["sleutel", "personeel_pid", "agent_raw", "ingelogd", "uitgelogd", "duur_s", "functie", "datum"]

RESULTATEN_KOLOMMEN = ["sleutel", "exportdatum", "campagne", "periode_van", "periode_tot", "agentfilter",
                       "adressen", "onaangeraakt", "niet_afgehandeld", "contactpogingen", "code", "omschrijving",
                       "aantal"]

# Kolomnamen (lowercase) die in Type C kunnen voorkomen, per genormaliseerd veld.
C_ALIASSEN = {
    "agent_raw": ["naam agent", "agent", "medewerker", "gebruiker"],
    "contact_dt": ["contactmoment datum & tijd", "datum & tijd", "datum tijd", "datumtijd",
                   "tijdstip", "historie datum & tijd", "belmoment"],
    "datum_los": ["contactdatum", "datum"],
    "tijd_los": ["contact tijdstip", "tijd"],
    "code_raw": ["resultaatcode", "resultaat code", "resultcode", "code"],
    "campagne_pid": ["campagnepid", "campagne pid"],
    "campagne_naam": ["campagne"],
    "ctpid": ["ctpid"],
    "historiepid": ["historiepid", "historie pid"],
    "project": ["naam project", "projectcode", "project"],
    "bedrijf": ["bedrijf"],
    "memo": ["laatste interne memo", "memo", "interne memo"],
    "omschrijving": ["resultcode omschr.", "resultaatomschrijving", "omschrijving"],
    "gespreksduur_s": ["gespreksduur", "talking"],
}


EXTENSIES = (".xls", ".html", ".htm", ".pdf", ".csv")


@dataclass
class Export:
    pad: Path
    type: str                     # "A", "B", "C" of "onbekend"
    df: pd.DataFrame
    sha256: str
    kolommen: list = field(default_factory=list)
    melding: str = ""

    @property
    def periode(self):
        if self.df.empty or "datum" not in self.df:
            return None, None
        d = pd.to_datetime(self.df["datum"])
        return d.min().date(), d.max().date()


# ---------------------------------------------------------------- hulpfuncties

def schoon(tekst) -> str:
    """Non-breaking spaces en dubbele spaties weg."""
    if tekst is None:
        return ""
    return re.sub(r"\s+", " ", str(tekst).replace("\xa0", " ")).strip()


def tijd_naar_sec(v) -> int | None:
    """'1:23:45' -> 5025. Ook '83:10:00' en 'mm:ss'. Leeg -> None."""
    s = schoon(v)
    if not s:
        return None
    try:
        delen = [int(float(x)) for x in s.split(":")]
    except ValueError:
        return None
    while len(delen) < 3:
        delen.insert(0, 0)
    h, m, sec = delen[-3:]
    return h * 3600 + m * 60 + sec


def parse_datumtijd(v) -> dt.datetime | None:
    """'4-8-2026 13:21:15' (d-m-yyyy) -> datetime."""
    s = schoon(v)
    if not s:
        return None
    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _int(v):
    s = schoon(v)
    try:
        return int(float(s.replace(",", "."))) if s else None
    except ValueError:
        return None


def _lees(pad: Path) -> tuple[str, BeautifulSoup]:
    ruw = Path(pad).read_bytes()
    html = ruw.decode("utf-8", errors="replace")
    return hashlib.sha256(ruw).hexdigest(), BeautifulSoup(html, "lxml")


def _tabel_rijen(tabel):
    """Kop + rijen (lijst van (tr, [celteksten])) uit een HTML-tabel."""
    kop_tr = tabel.find("thead").find("tr") if tabel.find("thead") else tabel.find("tr")
    kop = [schoon(th.get_text()) for th in kop_tr.find_all(["th", "td"])]
    body = tabel.find("tbody") or tabel
    rijen = []
    for tr in body.find_all("tr", recursive=False if tabel.find("tbody") else True):
        if tr is kop_tr:
            continue
        cellen = [schoon(td.get_text()) for td in tr.find_all("td")]
        if cellen:
            rijen.append((tr, cellen))
    return kop, rijen


def _rij_dict(kop, cellen):
    """Kolomnaam -> waarde. Dubbele kolomnamen (bv. 'Telefoonnummer') houden de eerste niet-lege."""
    d = {}
    for k, v in zip(kop, cellen):
        if k not in d or (not d[k] and v):
            d[k] = v
    return d


# ---------------------------------------------------------------- herkenning

def herken(soup: BeautifulSoup, pad: Path) -> tuple[str, object]:
    """Geeft (type, tabel) terug."""
    naam = Path(pad).name.lower()
    for tabel in soup.find_all("table"):
        try:
            kop, rijen = _tabel_rijen(tabel)
        except AttributeError:
            continue
        kl = {k.lower() for k in kop}
        if {"te betalen", "agent", "datum"} <= kl:
            return "B", tabel
        heeft_load = any("loadRecord" in (tr.get("ondblclick") or "") for tr, _ in rijen[:20])
        if "histor" in naam and _is_contacttabel(kl):
            return "C", tabel
        if tabel.get("id") == "idTableRapportage" and heeft_load:
            return "A", tabel
        if _is_contacttabel(kl):
            return "C", tabel
    return "onbekend", None


def _is_contacttabel(kl: set) -> bool:
    def heeft(veld):
        return any(a in kl for a in C_ALIASSEN[veld])
    return heeft("agent_raw") and heeft("code_raw") and (heeft("contact_dt") or heeft("datum_los"))


# ---------------------------------------------------------------- Type A en C

def _contact_record(d: dict, bron: str, pid_load=None, ctpid_load=None) -> dict:
    def pak(veld):
        for a in C_ALIASSEN.get(veld, [veld]):
            for k, v in d.items():
                if k.lower() == a and v:
                    return v
        return None

    moment = parse_datumtijd(pak("contact_dt"))
    if moment is None and pak("datum_los"):
        moment = parse_datumtijd(f"{pak('datum_los')} {pak('tijd_los') or ''}".strip())
    code_raw = pak("code_raw")
    code, is_max = codes.normaliseer(code_raw)
    pid = _int(d.get("CampagnePID")) or pid_load or _int(pak("campagne_pid"))
    ctpid = _int(d.get("CTPID")) or ctpid_load
    agent = pak("agent_raw")
    iso = moment.isoformat(sep=" ") if moment else None
    sleutel = f"{pid}|{ctpid}|{iso}" if ctpid is not None else f"{pid}|agent:{agent}|{iso}"
    return {
        "sleutel": sleutel,
        "bron": bron,
        "campagne_pid": pid,
        "ctpid": ctpid,
        "historiepid": _int(pak("historiepid")),
        "agent_raw": agent,
        "agent_pid": _int(d.get("Agent PID")),
        "project": pak("project"),
        "campagne_naam": d.get("Campagne") or None,
        "bedrijf": pak("bedrijf"),
        "contact_dt": iso,
        "datum": moment.date().isoformat() if moment else None,
        "uur": moment.hour if moment else None,
        "code": code,
        "code_raw": code_raw,
        "is_max": bool(is_max),
        "omschrijving": pak("omschrijving") or codes.OMSCHRIJVING.get(code),
        "gespreksduur_s": tijd_naar_sec(d.get("Gespreksduur") or pak("gespreksduur_s")),
        "prepare_s": tijd_naar_sec(d.get("Prepare")),
        "dial_s": tijd_naar_sec(d.get("Dial")),
        "finish_s": tijd_naar_sec(d.get("Finish")),
        "aantal_pogingen": _int(d.get("Aantal contactpogingen")),
        "is_hit": _int(d.get("Is hit")),
        "is_contactmoment": _int(d.get("Is contactmoment")),
        "is_afgehandeld": _int(d.get("Is afgehandeld")),
        "afspraak_dt": (lambda x: x.isoformat(sep=" ") if x else None)(parse_datumtijd(d.get("Afspraakdatum + tijd"))),
        "memo": pak("memo"),
    }


def _parse_contacten(tabel, bron: str) -> tuple[pd.DataFrame, list]:
    kop, rijen = _tabel_rijen(tabel)
    records = []
    for tr, cellen in rijen:
        m = re.search(r"loadRecord\(\s*(\d+)\s*,\s*(\d+)", tr.get("ondblclick") or "")
        pid, ctpid = (int(m.group(1)), int(m.group(2))) if m else (None, None)
        records.append(_contact_record(_rij_dict(kop, cellen), bron, pid, ctpid))
    df = pd.DataFrame(records, columns=CONTACT_KOLOMMEN)
    # Steam herhaalt een record per opname (Recording); zelfde contactmoment = één regel.
    df = df.drop_duplicates("sleutel", keep="first").reset_index(drop=True)
    return df, kop


# ---------------------------------------------------------------- Type B

def _parse_uren(tabel) -> tuple[pd.DataFrame, list]:
    kop, rijen = _tabel_rijen(tabel)
    records = []
    for _, cellen in rijen:
        d = _rij_dict(kop, cellen)
        datum = parse_datumtijd(d.get("Datum"))
        if datum is None or not d.get("Agent"):
            continue  # totaalregels e.d.
        r = {"datum": datum.date().isoformat(), "agent_raw": d["Agent"], "afdeling": d.get("Afdeling")}
        for k, n in UREN_TELKOLOMMEN.items():
            r[n] = _int(d.get(k)) or 0
        for k, n in UREN_TIJDKOLOMMEN.items():
            r[n] = tijd_naar_sec(d.get(k)) or 0
        records.append(r)
    return pd.DataFrame(records, columns=UREN_KOLOMMEN), kop


# ---------------------------------------------------------------- Type F (facturen)

_MAANDEN = {m: i + 1 for i, m in enumerate(
    ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
     "oktober", "november", "december"])}


def _bedrag(s):
    return float(s.replace(".", "").replace(",", ".")) if s else None


def _pdf_tekst(pad: Path) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(str(pad)).pages)


def parse_factuur_tekst(tekst: str, bestandsnaam: str = "") -> dict | None:
    """Haalt de kernvelden uit de tekst van een factuur. None als het geen factuur lijkt."""
    t = tekst.replace("\xa0", " ")
    if not re.search(r"factuur", t, re.I):
        return None
    m = (re.search(r"Factuur(?:nummer)?\s*:\s*(\w+)", t) or re.search(r"FACTUUR\s*\n\s*(\d{3,})", t)
         or re.search(r"(\d{3,})", bestandsnaam))
    nr = m.group(1) if m else None
    datum = None
    m = re.search(r"Factuurdatum[\s\S]{0,60}?(\d{1,2})[/-](\d{1,2})[/-](\d{4})", t, re.I)
    if m:
        datum = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    else:
        m = re.search(r"Factuurdatum[\s\S]{0,60}?(\d{1,2})\s+([a-z]+)\s+(\d{4})", t, re.I)
        if m and m.group(2).lower() in _MAANDEN:
            datum = dt.date(int(m.group(3)), _MAANDEN[m.group(2).lower()], int(m.group(1)))
    m = re.search(r"Betreft\s*:?\s*week\s*(\d{1,2})", t, re.I)
    week = int(m.group(1)) if m else None
    m = (re.search(r"(\d+(?:,\d+)?)\s*(?:uur|gewerkte\s+uren)", t, re.I)
         or re.search(r"Werkzaamheden\s*\n?\s*(\d+(?:,\d+)?)\s*\n?\s*€", t))
    uren = _bedrag(m.group(1)) if m else None
    m = re.search(r"(?:Totaalbedrag|Subtotaal)\s+excl\.?\s*btw\s*\n?\s*€\s*([\d.]+,\d{2})", t, re.I)
    bedrag = _bedrag(m.group(1)) if m else None
    m = re.search(r"€\s*([\d.]+,\d{2})\s*\n?\s*€\s*[\d.]+,\d{2}", t[t.find("Werkzaamheden"):]) if "Werkzaamheden" in t else None
    tarief = _bedrag(m.group(1)) if m else (round(bedrag / uren, 2) if bedrag and uren else None)
    m = re.search(r"(?:t\.\s?n\.\s?v\.|Ten name van)\s+(.+?)(?:\s+o\.v\.v\.|\n|$)", t, re.I)
    afzender = schoon(m.group(1)) if m else None
    m = re.search(r"Betreft\s*:?\s*(.+)", t, re.I)
    if bedrag is None or datum is None:
        return None
    return {"sleutel": f"{afzender}|{nr}", "afzender": afzender, "factuurnr": nr,
            "factuurdatum": datum.isoformat(), "week_genoemd": week, "uren": uren, "tarief": tarief,
            "bedrag_excl": bedrag, "omschrijving": schoon(m.group(1)) if m else None}


def _bedrag_flex(s: str) -> float:
    """'2,000.00' en '2.000,00' -> 2000.0"""
    s = s.strip()
    if "," in s and "." in s:
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) == 2 else s.replace(",", "")
    return float(s)


def _d(s):
    return dt.datetime.strptime(s, "%d-%m-%Y").date().isoformat()


def parse_verkoopfactuur_tekst(tekst: str) -> list[dict] | None:
    """Verkoopfactuur van LINK. (herkend aan 'Debiteurnummer'). Eén dict per factuurregel."""
    if "Debiteurnummer" not in tekst:
        return None
    t = re.sub(r"(\d)-\s*\n\s*(\d)", r"\1-\2", tekst.replace("\xa0", " "))  # datums over regels heen
    klant = schoon(t.strip().splitlines()[0])
    nr = re.search(r"Factuurnummer\s+(\S+)", t)
    datum = re.search(r"Factuurdatum\s+(\d{2}-\d{2}-\d{4})", t)
    deb = re.search(r"Debiteurnummer\s+(\S+)", t)
    if not (nr and datum):
        return None
    start = t.find("btw)", t.find("Beschrijving"))
    eind = t.find("btw naam", start)
    blok = t[start + 4: eind if eind > 0 else None]
    regels = []
    for i, m in enumerate(re.finditer(r"(?ms)^\s*(\d+(?:[.,]\d+)?)\s+(.*?)€\s*([\d.,]+)[^\n€]*?€\s*([\d.,]+)", blok)):
        oms = schoon(m.group(2))
        wp = re.search(r"werkperiode\s+(\d+)", oms, re.I)
        per = re.search(r"(\d{2}-\d{2}-\d{4})\s*t/m\s*(\d{2}-\d{2}-\d{4})", oms)
        regels.append({
            "sleutel": f"{nr.group(1)}|{i + 1}", "factuurnr": nr.group(1), "klant_naam": klant,
            "debiteurnr": deb.group(1) if deb else None, "factuurdatum": _d(datum.group(1)), "regel": i + 1,
            "omschrijving": oms, "werkperiode_nr": int(wp.group(1)) if wp else None,
            "periode_van": _d(per.group(1)) if per else None, "periode_tot": _d(per.group(2)) if per else None,
            "bedrag_excl": _bedrag_flex(m.group(4)),
            "is_lead": bool(re.search(r"\blead|overdracht", oms, re.I)) and not re.search(r"retainer|werkperiode", oms, re.I),
            "bron": "pdf", "status": None,
        })
    return regels or None


def _parse_factuur(pad: Path) -> Export:
    ruw = pad.read_bytes()
    sha = hashlib.sha256(ruw).hexdigest()
    tekst = _pdf_tekst(pad)
    verkoop = parse_verkoopfactuur_tekst(tekst)
    if verkoop:
        df = pd.DataFrame(verkoop, columns=VERKOOP_KOLOMMEN)
        df["datum"] = df["factuurdatum"]
        return Export(pad, "V", df, sha, VERKOOP_KOLOMMEN)
    r = parse_factuur_tekst(tekst, pad.name)
    if r is None:
        return Export(pad, "onbekend", pd.DataFrame(), sha, [], "PDF zonder herkenbare factuur")
    df = pd.DataFrame([r], columns=FACTUUR_KOLOMMEN)
    df["datum"] = df["factuurdatum"]
    return Export(pad, "F", df, sha, FACTUUR_KOLOMMEN)


# ---------------------------------------------------------------- publiek

def _parse_verkoop_csv(pad: Path) -> Export:
    """Lijst verkoopfacturen (bv. uit de mailbox):
    factuurnr;factuurdatum;debiteur;bedrag_incl[;bedrag_excl;opmerking;periode_van;periode_tot;werkperiode;status;regel].
    Meerdere regels per factuur: zelfde factuurnr met regel 1, 2, ... (opmerking met 'lead' = leadfee).
    Bedragen incl. 21% btw worden omgerekend naar excl. Een PDF van dezelfde factuur gaat voor."""
    ruw = pad.read_bytes()
    sha = hashlib.sha256(ruw).hexdigest()
    df = pd.read_csv(pad, sep=";", dtype=str, encoding="utf-8-sig").fillna("")
    kol = {c.lower().strip() for c in df.columns}
    if not {"factuurnr", "factuurdatum", "debiteur"} <= kol:
        return Export(pad, "onbekend", pd.DataFrame(), sha, list(df.columns), "CSV zonder bekende kolommen")
    df.columns = [c.lower().strip() for c in df.columns]
    rijen, zonder_datum = [], []
    for r in df.itertuples():
        if not r.factuurdatum:
            zonder_datum.append(r.factuurnr)
            continue
        if getattr(r, "bedrag_excl", ""):
            excl = _bedrag_flex(r.bedrag_excl)
        elif getattr(r, "bedrag_incl", ""):
            excl = round(_bedrag_flex(r.bedrag_incl) / 1.21, 2)
        else:
            continue
        regel = int(getattr(r, "regel", "") or 1)
        oms = getattr(r, "opmerking", "") or ""
        rijen.append({"sleutel": f"{r.factuurnr}|{regel}", "factuurnr": r.factuurnr, "klant_naam": schoon(r.debiteur),
                      "debiteurnr": None, "factuurdatum": r.factuurdatum, "regel": regel,
                      "omschrijving": oms,
                      "werkperiode_nr": int(r.werkperiode) if getattr(r, "werkperiode", "") else None,
                      "periode_van": getattr(r, "periode_van", "") or None,
                      "periode_tot": getattr(r, "periode_tot", "") or None, "bedrag_excl": excl,
                      "is_lead": bool(re.search(r"\blead|overdracht", oms, re.I)), "bron": "mail", "status": (getattr(r, "status", "") or None)})
    out = pd.DataFrame(rijen, columns=VERKOOP_KOLOMMEN)
    out["datum"] = out["factuurdatum"]
    melding = f"overgeslagen zonder factuurdatum: {', '.join(zonder_datum)}" if zonder_datum else ""
    return Export(pad, "V", out, sha, list(df.columns), melding)


def _xml_duur(v) -> int:
    """Excel-XML duur '1900-01-01T15:04:00.000' (dagen sinds 31-12-1899) -> seconden."""
    s = schoon(v)
    try:
        t = dt.datetime.fromisoformat(s[:19])
    except ValueError:
        return tijd_naar_sec(s) or 0
    return int((t - dt.datetime(1899, 12, 31)).total_seconds())


def _parse_stats(pad: Path, ruw: bytes) -> Export:
    sha = hashlib.sha256(ruw).hexdigest()
    soup = BeautifulSoup(ruw.decode("utf-8", errors="replace"), "lxml-xml")
    rijen = soup.find_all("Row")
    tekst = lambda c: schoon(BeautifulSoup(c.get_text(), "lxml").get_text(" "))
    kop = [tekst(c) for c in rijen[0].find_all("Cell")]
    idx = {k: i for i, k in enumerate(kop)}
    m = re.search(r"(\d{4}-\d{2}-\d{2})", pad.name)
    peil = m.group(1) if m else dt.date.fromtimestamp(pad.stat().st_mtime).isoformat()
    out = []
    for r in rijen[1:]:
        c = [tekst(x) for x in r.find_all("Cell")]
        if len(c) < len(kop) - 1 or not c[0] or c[0].startswith(("Subtotaal", "Records:")):
            if len(c) < 10:
                break   # tweede tabel (pauzes per campagne)
            continue
        g = lambda k: c[idx[k]] if k in idx and idx[k] < len(c) else ""
        out.append({
            "sleutel": f"{peil}|{g('Agent')}|{g('Campagne')}|{g('Project')}", "peildatum": peil,
            "agent_raw": g("Agent"), "campagne": g("Campagne"), "project": g("Project"),
            "contactpogingen": _int(g("Contactpog.")) or 0, "calls": _int(g("Calls")) or 0,
            "hits": _int(g("Hits")) or 0, "afgehandeld": _int(g("Afgeh")) or 0,
            "recordtijd_s": _xml_duur(g("Record tijd")), "wachten_s": _xml_duur(g("Wachten")),
            "laden_s": _xml_duur(g("Laadtijd")), "prepare_s": _xml_duur(g("Prepare")), "dial_s": _xml_duur(g("Dial")),
            "gesprek_s": _xml_duur(g("Gespreksduur")), "finish_s": _xml_duur(g("Finish")),
        })
    df = pd.DataFrame(out, columns=STATS_KOLOMMEN)
    df["datum"] = peil
    return Export(pad, "S", df, sha, kop)


def _parse_callresults(pad: Path, soup: BeautifulSoup, sha: str) -> Export:
    tekst = schoon(soup.body.get_text(" ") if soup.body else soup.get_text(" "))
    g = lambda pat: (re.search(pat, tekst) or [None, None])[1]
    campagne = schoon(g(r"Campagne:\s*(.+?)\s*\(Aantal adressen"))
    van, tot = parse_datumtijd(g(r"Startdatum:\s*(\S+)")), parse_datumtijd(g(r"Einddatum:\s*(\S+)"))
    agent = schoon(g(r"Agent:\s*(.*?)\s*Totaal aantal adressen")) or None
    m = re.search(r"callresults_(\d{1,2})-(\d{1,2})-(\d{4})", pad.name)
    export = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat() if m else None
    getal = lambda pat: _int(g(pat)) or 0
    basis = {"exportdatum": export, "campagne": campagne, "periode_van": van and van.date().isoformat(),
             "periode_tot": tot and tot.date().isoformat(), "agentfilter": agent,
             "adressen": getal(r"Totaal aantal adressen:\s*(\d+)"), "onaangeraakt": getal(r"Onaangeraakte adressen:\s*(\d+)"),
             "niet_afgehandeld": getal(r"Niet afgehandeld:\s*(\d+)"), "contactpogingen": getal(r"# Contactpogingen:\s*(\d+)")}
    rijen, gezien = [], set()
    for tr in soup.find_all("tr"):
        c = [schoon(x.get_text(" ")) for x in tr.find_all(["td", "th"])]
        if len(c) >= 3 and re.fullmatch(r"(MAX-)?\d{3}", c[0]) and c[0] not in gezien:
            gezien.add(c[0])
            code, _ = codes.normaliseer(c[0])
            rijen.append({**basis, "sleutel": f"{campagne}|{basis['periode_van']}|{basis['periode_tot']}|{agent}|{c[0]}",
                          "code": code, "omschrijving": c[1], "aantal": _int(c[2]) or 0})
    df = pd.DataFrame(rijen, columns=RESULTATEN_KOLOMMEN)
    df["datum"] = export
    return Export(pad, "R", df, sha, ["Rc", "", "Aantal"])


def _parse_sessies(tabel, sha: str, pad: Path) -> Export:
    kop, rijen = _tabel_rijen(tabel)
    uit = []
    for _, cellen in rijen:
        d = _rij_dict(kop, cellen)
        t_in = parse_datumtijd(d.get("Ingelogd"))
        if t_in is None or not d.get("Personeel"):
            continue
        t_uit = parse_datumtijd(d.get("Uitgelogd"))
        uit.append({"sleutel": d.get("Sessie-ID") or f"{d.get('Personeel')}|{t_in}", "personeel_pid": _int(d.get("PersoneelsPID")),
                    "agent_raw": d.get("Personeel"), "ingelogd": t_in.isoformat(sep=" "),
                    "uitgelogd": t_uit.isoformat(sep=" ") if t_uit else None,
                    "duur_s": tijd_naar_sec(d.get("Ingelogde tijd")), "functie": d.get("Functie"),
                    "datum": t_in.date().isoformat()})
    return Export(pad, "L", pd.DataFrame(uit, columns=SESSIE_KOLOMMEN), sha, kop)


def _parse_pogingen(tabel, sha: str, pad: Path) -> Export:
    kop, rijen = _tabel_rijen(tabel)
    uit = []
    for _, cellen in rijen:
        d = _rij_dict(kop, cellen)
        t = parse_datumtijd(d.get("Contactdatum"))
        if t is None:
            continue
        iso = t.isoformat(sep=" ")
        uit.append({"sleutel": f"{d.get('Campagne')}|{d.get('CtPID')}|{iso}|{d.get('Gecontacteerd door')}",
                    "campagne": d.get("Campagne"), "project": d.get("Project"), "ctpid": _int(d.get("CtPID")),
                    "chpid": _int(d.get("ChPID")), "poging_dt": iso, "datum": t.date().isoformat(), "uur": t.hour,
                    "agent_raw": d.get("Gecontacteerd door"), "verbonden": d.get("Status") == "Gesprek verbonden",
                    "status": d.get("Status"), "sip": d.get("SIP Response") or None})
    df = pd.DataFrame(uit, columns=POGING_KOLOMMEN).drop_duplicates("sleutel")
    return Export(pad, "P", df, sha, kop)


def parse_bestand(pad) -> Export:
    pad = Path(pad)
    begin = pad.read_bytes()[:400]
    if begin.lstrip().startswith(b"<?xml") and b"Workbook" in begin:
        ruw = pad.read_bytes()
        if b"Contactpog." in ruw and b"Record tijd" in ruw:
            return _parse_stats(pad, ruw)
    if pad.suffix.lower() == ".pdf":
        return _parse_factuur(pad)
    if pad.suffix.lower() == ".csv":
        return _parse_verkoop_csv(pad)
    sha, soup = _lees(pad)
    if "callresults" in pad.name.lower() or re.search(r"Afgehandeld positief", soup.get_text()[:20000] or ""):
        if soup.find(string=re.compile("Contactpogingen")) and soup.find(string=re.compile("Onaangeraakte adressen")):
            return _parse_callresults(pad, soup, sha)
    for t in soup.find_all("table"):
        tr = t.find("tr")
        kopje = {schoon(x.get_text()) for x in tr.find_all(["th", "td"])} if tr else set()
        if {"Gecontacteerd door", "Contactdatum", "Status", "CtPID"} <= kopje:
            return _parse_pogingen(t, sha, pad)
        if {"Personeel", "Ingelogd", "Uitgelogd", "Sessie-ID"} <= kopje:
            return _parse_sessies(t, sha, pad)
    type_, tabel = herken(soup, pad)
    if type_ == "B":
        df, kop = _parse_uren(tabel)
    elif type_ in ("A", "C"):
        df, kop = _parse_contacten(tabel, type_)
    else:
        return Export(pad, "onbekend", pd.DataFrame(), sha, [], "Geen bekende Steam-tabel gevonden")
    return Export(pad, type_, df, sha, kop)


def parse_map(map_) -> list[Export]:
    return [parse_bestand(p) for p in sorted(Path(map_).iterdir())
            if p.is_file() and p.suffix.lower() in EXTENSIES]

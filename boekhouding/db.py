"""Database-laag: één SQLite-bestand waarin alle onderdelen (relaties, facturen, grootboek,
betalingen, bank, inbox) met elkaar verbonden zijn. Bedragen staan altijd in centen."""

import os
import sqlite3
from datetime import datetime

MAP = os.path.dirname(os.path.abspath(__file__))
DB_PAD = os.environ.get("BOEKHOUDING_DB", os.path.join(MAP, "data", "boekhouding.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS instellingen (
    sleutel TEXT PRIMARY KEY,
    waarde  TEXT
);

CREATE TABLE IF NOT EXISTS grootboekrekeningen (
    code TEXT PRIMARY KEY,
    naam TEXT NOT NULL,
    soort TEXT NOT NULL,          -- activa / passiva / opbrengst / kosten
    actief INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS relaties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naam TEXT NOT NULL,
    soort TEXT NOT NULL DEFAULT 'crediteur',       -- crediteur / debiteur / beide
    email TEXT, iban TEXT, bic TEXT,
    adres TEXT, postcode TEXT, plaats TEXT,
    kvk TEXT, btw_nummer TEXT,
    auto_goedkeur_limiet_cent INTEGER NOT NULL DEFAULT 0,  -- 0 = altijd handmatig goedkeuren
    standaard_rekening TEXT REFERENCES grootboekrekeningen(code),
    iban_geverifieerd INTEGER NOT NULL DEFAULT 0,   -- 1 = IBAN door jou bevestigd of al eerder succesvol betaald
    bron TEXT NOT NULL DEFAULT 'handmatig',         -- handmatig / automatisch (aangemaakt vanuit een factuur)
    notities TEXT,
    aangemaakt_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS betaalbatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aangemaakt_op TEXT NOT NULL,
    uitvoerdatum TEXT NOT NULL,
    aantal INTEGER NOT NULL,
    totaal_cent INTEGER NOT NULL,
    bericht_id TEXT NOT NULL,
    xml TEXT NOT NULL,
    kanaal TEXT NOT NULL DEFAULT 'bestand',        -- bestand / ponto
    extern_id TEXT,
    status TEXT NOT NULL DEFAULT 'aangemaakt',     -- aangemaakt / ter_ondertekening / ondertekend / geweigerd / geannuleerd
    ondertekenen_url TEXT
);

CREATE TABLE IF NOT EXISTS documenten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bestandsnaam TEXT NOT NULL,
    opslag TEXT NOT NULL,                          -- bestandsnaam in uploads/
    bron TEXT NOT NULL,                            -- upload / email / map
    afzender TEXT, onderwerp TEXT,
    status TEXT NOT NULL DEFAULT 'nieuw',          -- nieuw / verwerkt / fout / genegeerd
    melding TEXT,
    inkoopfactuur_id INTEGER,
    hash TEXT NOT NULL UNIQUE,
    ontvangen_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inkoopfacturen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relatie_id INTEGER NOT NULL REFERENCES relaties(id),
    factuurnummer TEXT NOT NULL,
    factuurdatum TEXT NOT NULL,
    vervaldatum TEXT NOT NULL,
    omschrijving TEXT,
    bedrag_excl_cent INTEGER NOT NULL,
    btw_cent INTEGER NOT NULL,
    bedrag_incl_cent INTEGER NOT NULL,
    betalingskenmerk TEXT,
    betaalwijze TEXT NOT NULL DEFAULT 'overboeking',  -- overboeking / incasso / al_betaald
    bestand TEXT,
    rekening TEXT REFERENCES grootboekrekeningen(code),
    bron TEXT NOT NULL DEFAULT 'handmatig',        -- handmatig / upload / email / map
    zekerheid REAL,                                -- 0..1 bij automatisch uitlezen
    waarschuwingen TEXT,                           -- regels gescheiden door \n
    document_id INTEGER REFERENCES documenten(id),
    status TEXT NOT NULL DEFAULT 'ter_goedkeuring',
        -- ter_goedkeuring / goedgekeurd / afgekeurd / in_batch / betaald
    beoordeeld_op TEXT,
    beoordeling_notitie TEXT,
    betaalbatch_id INTEGER REFERENCES betaalbatches(id),
    verrekend_met INTEGER REFERENCES inkoopfacturen(id),   -- creditnota verrekend met deze factuur
    doorgestuurd_op TEXT,                          -- naar het boekhoudadres gemaild
    doorstuur_melding TEXT,                        -- reden als doorsturen (nog) niet lukte
    betaald_op TEXT,
    aangemaakt_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verkoopfacturen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    relatie_id INTEGER NOT NULL REFERENCES relaties(id),
    factuurnummer TEXT NOT NULL UNIQUE,
    factuurdatum TEXT NOT NULL,
    vervaldatum TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'concept',        -- concept / verzonden / betaald
    notities TEXT,
    verzonden_op TEXT,
    herinneringen INTEGER NOT NULL DEFAULT 0,
    laatst_herinnerd TEXT,
    betaald_op TEXT,
    aangemaakt_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verkoopregels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factuur_id INTEGER NOT NULL REFERENCES verkoopfacturen(id) ON DELETE CASCADE,
    omschrijving TEXT NOT NULL,
    aantal REAL NOT NULL,
    prijs_cent INTEGER NOT NULL,
    btw_pct INTEGER NOT NULL,
    rekening TEXT REFERENCES grootboekrekeningen(code)
);

CREATE TABLE IF NOT EXISTS banktransacties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datum TEXT NOT NULL,
    bedrag_cent INTEGER NOT NULL,             -- positief = ontvangen, negatief = betaald
    tegenrekening TEXT, naam TEXT, omschrijving TEXT, referentie TEXT,
    gekoppeld_type TEXT,                      -- inkoop / verkoop / grootboek / NULL
    gekoppeld_id INTEGER,
    rekening TEXT,                            -- bij gekoppeld_type = grootboek
    import_sleutel TEXT NOT NULL UNIQUE,
    geimporteerd_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journaalposten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datum TEXT NOT NULL,
    dagboek TEXT NOT NULL,                    -- inkoop / verkoop / bank / memoriaal
    omschrijving TEXT NOT NULL,
    bron_type TEXT, bron_id INTEGER,
    aangemaakt_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journaalregels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES journaalposten(id) ON DELETE CASCADE,
    rekening TEXT NOT NULL REFERENCES grootboekrekeningen(code),
    debet_cent INTEGER NOT NULL DEFAULT 0,
    credit_cent INTEGER NOT NULL DEFAULT 0,
    relatie_id INTEGER REFERENCES relaties(id),
    btw_rubriek TEXT                          -- 1a / 1b / 1c / 1e / 5b ... voor de btw-aangifte
);

CREATE TABLE IF NOT EXISTS koppelingen (
    naam TEXT PRIMARY KEY,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logboek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tijd TEXT NOT NULL,
    actie TEXT NOT NULL,
    object_type TEXT, object_id INTEGER,
    details TEXT
);

CREATE INDEX IF NOT EXISTS ix_regels_rekening ON journaalregels(rekening);
CREATE INDEX IF NOT EXISTS ix_posten_bron ON journaalposten(bron_type, bron_id);
"""

# Rekeningschema, afgeleid van het Referentie Grootboekschema (RGS), beperkt tot wat een
# dienstverlenend bedrijf nodig heeft. Uit te breiden via het scherm Grootboek.
REKENINGSCHEMA = [
    ("0500", "Inventaris", "activa"),
    ("1100", "Bank", "activa"),
    ("1300", "Debiteuren", "activa"),
    ("1510", "Te vorderen btw (voorbelasting)", "activa"),
    ("1520", "Af te dragen btw hoog", "passiva"),
    ("1521", "Af te dragen btw laag", "passiva"),
    ("1530", "Btw-afdracht (rekening-courant)", "passiva"),
    ("1600", "Crediteuren", "passiva"),
    ("1900", "Nog te verwerken bankmutaties", "activa"),
    ("0900", "Eigen vermogen", "passiva"),
    ("4000", "Lonen en salarissen", "kosten"),
    ("4050", "Inhuur personeel / freelancers", "kosten"),
    ("4100", "Huisvestingskosten", "kosten"),
    ("4200", "Telefonie en internet", "kosten"),
    ("4300", "Software en ICT", "kosten"),
    ("4400", "Marketing en leadgeneratie", "kosten"),
    ("4500", "Reis- en verblijfkosten", "kosten"),
    ("4550", "Autokosten", "kosten"),
    ("4600", "Kantoorkosten", "kosten"),
    ("4700", "Advies, accountant en administratie", "kosten"),
    ("4750", "Verzekeringen", "kosten"),
    ("4800", "Bankkosten", "kosten"),
    ("4850", "Representatie en relatiegeschenken", "kosten"),
    ("4900", "Overige kosten", "kosten"),
    ("7000", "Inkoop / uitbesteed werk", "kosten"),
    ("8000", "Omzet btw hoog", "opbrengst"),
    ("8010", "Omzet btw laag", "opbrengst"),
    ("8020", "Omzet btw 0% / verlegd", "opbrengst"),
    ("8900", "Overige opbrengsten", "opbrengst"),
]

STANDAARD_INSTELLINGEN = {
    "bedrijfsnaam": "Mijn Bedrijf B.V.",
    "adres": "", "postcode": "", "plaats": "",
    "iban": "", "bic": "ABNANL2A",
    "kvk": "", "btw_nummer": "", "email": "",
    "factuur_prefix": "F",
    "betaaltermijn_dagen": "14",
    "betaal_dagen_voor_verval": "2",       # betalingen worden X dagen vóór vervaldatum uitgevoerd
    "betaalmoment": "vervaldatum",         # vervaldatum / direct
    "herinneringen_aan": "1",              # automatisch betalingsherinneringen sturen
    "herinnering_dagen": "7,21",           # dagen na vervaldatum: 1e en 2e herinnering
    "samenvatting_aan": "1",               # dagelijkse e-mail met wat op jou wacht
    "standaard_kostenrekening": "4900",
    "doorstuur_email": "",                 # inkoopfacturen automatisch doorsturen naar dit adres
    "doorstuur_moment": "goedkeuring",     # goedkeuring / ontvangst
    "doorsturen_vanaf": "",                # alleen facturen die na het instellen binnenkwamen
}

# Kolommen die in latere versies zijn toegevoegd; oudere databases worden bijgewerkt.
MIGRATIES = {
    "relaties": {"standaard_rekening": "TEXT", "iban_geverifieerd": "INTEGER NOT NULL DEFAULT 0",
                 "bron": "TEXT NOT NULL DEFAULT 'handmatig'"},
    "inkoopfacturen": {"rekening": "TEXT", "betaalwijze": "TEXT NOT NULL DEFAULT 'overboeking'", "bron": "TEXT NOT NULL DEFAULT 'handmatig'", "zekerheid": "REAL",
                       "waarschuwingen": "TEXT", "document_id": "INTEGER",
                       "verrekend_met": "INTEGER", "doorgestuurd_op": "TEXT", "doorstuur_melding": "TEXT"},
    "verkoopfacturen": {"verzonden_op": "TEXT", "herinneringen": "INTEGER NOT NULL DEFAULT 0",
                        "laatst_herinnerd": "TEXT"},
    "verkoopregels": {"rekening": "TEXT"},
    "banktransacties": {"rekening": "TEXT"},
    "betaalbatches": {"kanaal": "TEXT NOT NULL DEFAULT 'bestand'", "extern_id": "TEXT",
                      "status": "TEXT NOT NULL DEFAULT 'aangemaakt'", "ondertekenen_url": "TEXT"},
}


def nu():
    return datetime.now().isoformat(timespec="seconds")


def laad_configbestand(pad=None):
    """Leest geheime instellingen (API-sleutels, wachtwoorden) uit config.env naar de omgeving."""
    pad = pad or os.path.join(MAP, "config.env")
    if not os.path.exists(pad):
        return
    with open(pad, encoding="utf-8") as f:
        for regel in f:
            regel = regel.strip()
            if regel and not regel.startswith("#") and "=" in regel:
                k, v = regel.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def verbind(pad=None):
    pad = pad or DB_PAD
    os.makedirs(os.path.dirname(os.path.abspath(pad)), exist_ok=True)
    con = sqlite3.connect(pad, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return con


def initialiseer(con):
    for tabel, kolommen in MIGRATIES.items():
        bestaand = {r["name"] for r in con.execute(f"PRAGMA table_info({tabel})")}
        if bestaand:
            for kolom, definitie in kolommen.items():
                if kolom not in bestaand:
                    con.execute(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {definitie}")
    con.executescript(SCHEMA)
    for k, v in STANDAARD_INSTELLINGEN.items():
        con.execute("INSERT OR IGNORE INTO instellingen (sleutel, waarde) VALUES (?, ?)", (k, v))
    con.executemany("INSERT OR IGNORE INTO grootboekrekeningen (code, naam, soort) VALUES (?, ?, ?)", REKENINGSCHEMA)
    con.commit()


def instellingen(con):
    return {r["sleutel"]: r["waarde"] for r in con.execute("SELECT sleutel, waarde FROM instellingen")}


def zet_instelling(con, sleutel, waarde):
    con.execute("INSERT INTO instellingen (sleutel, waarde) VALUES (?, ?) "
                "ON CONFLICT(sleutel) DO UPDATE SET waarde = excluded.waarde", (sleutel, str(waarde)))


def log(con, actie, object_type=None, object_id=None, details=""):
    con.execute(
        "INSERT INTO logboek (tijd, actie, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
        (nu(), actie, object_type, object_id, details),
    )

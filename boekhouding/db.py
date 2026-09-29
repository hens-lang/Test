"""Database-laag: één SQLite-bestand waarin alle onderdelen (relaties, facturen,
betalingen, bank) met elkaar verbonden zijn. Bedragen staan altijd in centen."""

import os
import sqlite3
from datetime import datetime

DB_PAD = os.environ.get("BOEKHOUDING_DB", os.path.join(os.path.dirname(__file__), "data", "boekhouding.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS instellingen (
    sleutel TEXT PRIMARY KEY,
    waarde  TEXT
);

CREATE TABLE IF NOT EXISTS relaties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    naam TEXT NOT NULL,
    soort TEXT NOT NULL DEFAULT 'crediteur',       -- crediteur / debiteur / beide
    email TEXT, iban TEXT, bic TEXT,
    adres TEXT, postcode TEXT, plaats TEXT,
    kvk TEXT, btw_nummer TEXT,
    auto_goedkeur_limiet_cent INTEGER NOT NULL DEFAULT 0,  -- 0 = altijd handmatig goedkeuren
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
    xml TEXT NOT NULL
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
    bestand TEXT,
    status TEXT NOT NULL DEFAULT 'ter_goedkeuring',
        -- ter_goedkeuring / goedgekeurd / afgekeurd / in_batch / betaald
    beoordeeld_op TEXT,
    beoordeling_notitie TEXT,
    betaalbatch_id INTEGER REFERENCES betaalbatches(id),
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
    betaald_op TEXT,
    aangemaakt_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verkoopregels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factuur_id INTEGER NOT NULL REFERENCES verkoopfacturen(id) ON DELETE CASCADE,
    omschrijving TEXT NOT NULL,
    aantal REAL NOT NULL,
    prijs_cent INTEGER NOT NULL,
    btw_pct INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS banktransacties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datum TEXT NOT NULL,
    bedrag_cent INTEGER NOT NULL,             -- positief = ontvangen, negatief = betaald
    tegenrekening TEXT, naam TEXT, omschrijving TEXT, referentie TEXT,
    gekoppeld_type TEXT,                      -- inkoop / verkoop / NULL
    gekoppeld_id INTEGER,
    import_sleutel TEXT NOT NULL UNIQUE,
    geimporteerd_op TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logboek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tijd TEXT NOT NULL,
    actie TEXT NOT NULL,
    object_type TEXT, object_id INTEGER,
    details TEXT
);
"""

STANDAARD_INSTELLINGEN = {
    "bedrijfsnaam": "Mijn Bedrijf B.V.",
    "adres": "", "postcode": "", "plaats": "",
    "iban": "", "bic": "",
    "kvk": "", "btw_nummer": "", "email": "",
    "factuur_prefix": "F",
    "betaaltermijn_dagen": "14",
    "betaal_dagen_voor_verval": "2",   # betaalbatch plant betalingen X dagen voor vervaldatum
}


def nu():
    return datetime.now().isoformat(timespec="seconds")


def verbind(pad=None):
    pad = pad or DB_PAD
    os.makedirs(os.path.dirname(os.path.abspath(pad)), exist_ok=True)
    con = sqlite3.connect(pad)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def initialiseer(con):
    con.executescript(SCHEMA)
    for k, v in STANDAARD_INSTELLINGEN.items():
        con.execute("INSERT OR IGNORE INTO instellingen (sleutel, waarde) VALUES (?, ?)", (k, v))
    con.commit()


def instellingen(con):
    return {r["sleutel"]: r["waarde"] for r in con.execute("SELECT sleutel, waarde FROM instellingen")}


def log(con, actie, object_type=None, object_id=None, details=""):
    con.execute(
        "INSERT INTO logboek (tijd, actie, object_type, object_id, details) VALUES (?, ?, ?, ?, ?)",
        (nu(), actie, object_type, object_id, details),
    )

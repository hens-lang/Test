"""SQLite-opslag: data/link.db is de enige bron van waarheid.

Ontdubbeling:
  contactmomenten  sleutel = campagne-PID | CTPID | contactmoment. Dezelfde export twee keer
                   inlezen geeft dus geen dubbele regels. Een historie-regel (bron C) wint van
                   een belexport-regel (bron A) met dezelfde sleutel.
  uren             (datum, agent_raw). Een nieuwere export overschrijft de oude regel.
  facturen         afzender | factuurnummer.
  bestanden        sha256 van de inhoud; hetzelfde bestand wordt één keer geregistreerd.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd

from .config import ROOT
from .parsers import CONTACT_KOLOMMEN, EXTENSIES, FACTUUR_KOLOMMEN, UREN_KOLOMMEN, Export, parse_bestand

DB_PAD = ROOT / "data" / "link.db"

_TYPES = {"campagne_pid": "INTEGER", "ctpid": "INTEGER", "historiepid": "INTEGER", "agent_pid": "INTEGER",
          "uur": "INTEGER", "code": "INTEGER", "is_max": "INTEGER", "gespreksduur_s": "INTEGER",
          "prepare_s": "INTEGER", "dial_s": "INTEGER", "finish_s": "INTEGER", "aantal_pogingen": "INTEGER",
          "is_hit": "INTEGER", "is_contactmoment": "INTEGER", "is_afgehandeld": "INTEGER"}


def verbind(pad: Path | str = DB_PAD) -> sqlite3.Connection:
    Path(pad).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(pad)
    contact_cols = ", ".join(f"{c} {_TYPES.get(c, 'TEXT')}" for c in CONTACT_KOLOMMEN if c != "sleutel")
    uren_cols = ", ".join(f"{c} {'TEXT' if c in ('datum', 'agent_raw', 'afdeling') else 'INTEGER'}"
                          for c in UREN_KOLOMMEN)
    con.executescript(f"""
        CREATE TABLE IF NOT EXISTS contactmomenten (sleutel TEXT PRIMARY KEY, {contact_cols}, bestand TEXT);
        CREATE TABLE IF NOT EXISTS uren ({uren_cols}, bestand TEXT, PRIMARY KEY (datum, agent_raw));
        CREATE TABLE IF NOT EXISTS facturen (sleutel TEXT PRIMARY KEY, afzender TEXT, factuurnr TEXT,
            factuurdatum TEXT, week_genoemd INTEGER, uren REAL, tarief REAL, bedrag_excl REAL,
            omschrijving TEXT, bestand TEXT);
        CREATE TABLE IF NOT EXISTS bestanden (
            sha256 TEXT PRIMARY KEY, naam TEXT, type TEXT, rijen INTEGER,
            periode_van TEXT, periode_tot TEXT, kolommen INTEGER, ingelezen_op TEXT);
    """)
    return con


def _upsert(con, tabel, df: pd.DataFrame, sleutel: list[str], voorwaarde: str = ""):
    if df.empty:
        return
    cols = list(df.columns)
    upd = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in sleutel)
    sql = (f"INSERT INTO {tabel} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
           f"ON CONFLICT({', '.join(sleutel)}) DO UPDATE SET {upd} {voorwaarde}")
    rows = [tuple(None if pd.isna(v) else (int(v) if isinstance(v, bool) else v) for v in r)
            for r in df.itertuples(index=False, name=None)]
    con.executemany(sql, rows)


def bewaar(con, exp: Export) -> int:
    """Schrijft een geparste export weg. Geeft het aantal rijen in de export terug."""
    van, tot = exp.periode
    con.execute(
        "INSERT OR REPLACE INTO bestanden VALUES (?,?,?,?,?,?,?,?)",
        (exp.sha256, exp.pad.name, exp.type, len(exp.df), van and van.isoformat(), tot and tot.isoformat(),
         len(exp.kolommen), dt.datetime.now().isoformat(timespec="seconds")),
    )
    df = exp.df.copy()
    df["bestand"] = exp.pad.name
    if exp.type in ("A", "C"):
        df = df.dropna(subset=["contact_dt"])
        _upsert(con, "contactmomenten", df, ["sleutel"],
                "WHERE contactmomenten.bron = 'A' OR excluded.bron = 'C'")
    elif exp.type == "B":
        _upsert(con, "uren", df, ["datum", "agent_raw"])
    elif exp.type == "F":
        _upsert(con, "facturen", df[FACTUUR_KOLOMMEN + ["bestand"]], ["sleutel"])
    con.commit()
    return len(exp.df)


def ingest(inbox, con) -> list[Export]:
    exports = []
    for p in sorted(Path(inbox).iterdir()):
        if p.is_file() and p.suffix.lower() in EXTENSIES:
            exp = parse_bestand(p)
            if exp.type != "onbekend":
                bewaar(con, exp)
            exports.append(exp)
    return exports


def lees(con, tabel: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {tabel}", con)

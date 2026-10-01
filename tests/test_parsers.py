"""Parsers op geanonimiseerde echte exports (tests/fixtures) en, als aanwezig, op data/inbox."""
import datetime as dt

import pytest

from conftest import FIXTURES, INBOX
from link_data import codes
from link_data.parsers import (CONTACT_KOLOMMEN, UREN_KOLOMMEN, parse_bestand, parse_factuur_tekst,
                               schoon, tijd_naar_sec)

BELEXPORTS = sorted(FIXTURES.glob("belexport_*.xls"))
UREN = sorted(FIXTURES.glob("uren_*.xls"))


def test_hulpfuncties():
    assert schoon("Naam\xa0project ") == "Naam project"
    assert tijd_naar_sec("1:23:45") == 5025
    assert tijd_naar_sec("83:10:00") == 83 * 3600 + 600
    assert tijd_naar_sec("") is None
    assert codes.normaliseer("MAX-400") == (400, True)
    assert codes.normaliseer("101") == (101, False)
    assert codes.normaliseer("abc") == (None, False)
    assert codes.groep(100) == "bereikt" and codes.groep(300) == "data_fout" and codes.groep(202) == "niet_geschikt"


@pytest.mark.parametrize("pad", BELEXPORTS, ids=lambda p: p.name)
def test_belexport(pad):
    e = parse_bestand(pad)
    assert e.type == "A"
    assert list(e.df.columns) == CONTACT_KOLOMMEN
    assert len(e.df) > 0
    assert e.df["campagne_pid"].notna().all(), "PID moet uit loadRecord komen, ook zonder kolom Campagne"
    assert e.df["ctpid"].notna().all()
    assert e.df["contact_dt"].notna().all()
    assert e.df["sleutel"].is_unique
    assert e.df["uur"].between(0, 23).all()
    assert e.df["code"].notna().all()
    assert not any("\xa0" in k for k in e.kolommen)
    # MAX-codes worden genormaliseerd
    max_rijen = e.df[e.df["code_raw"].str.startswith("MAX-")]
    assert max_rijen["is_max"].all()
    assert (max_rijen["code"] == max_rijen["code_raw"].str[4:].astype(int)).all()


def test_lange_kolomset_vult_extra_velden():
    lang = [p for p in BELEXPORTS if int(p.stem.split("_")[1].rstrip("kol")) > 50]
    assert lang
    e = parse_bestand(lang[0])
    assert e.df["omschrijving"].notna().any()
    assert e.df["gespreksduur_s"].notna().any()
    assert e.df["aantal_pogingen"].notna().any()
    assert (e.df["campagne_naam"].notna()).any()


def test_dubbele_opnameregels_worden_een_contactmoment(tmp_path):
    bron = (FIXTURES / "belexport_9kol.xls").read_text(encoding="utf-8")
    eerste_rij = bron[bron.index("<tr ondblclick"):]
    eerste_rij = eerste_rij[:eerste_rij.index("</tr>") + 5]
    dubbel = bron.replace(eerste_rij, eerste_rij + eerste_rij.replace("X0", "X0-opname2"), 1)
    p = tmp_path / "dubbel.xls"
    p.write_text(dubbel, encoding="utf-8")
    assert len(parse_bestand(p).df) == len(parse_bestand(FIXTURES / "belexport_9kol.xls").df)


@pytest.mark.parametrize("pad", UREN, ids=lambda p: p.name)
def test_urenexport(pad):
    e = parse_bestand(pad)
    assert e.type == "B"
    assert list(e.df.columns) == UREN_KOLOMMEN
    assert (e.df["te_betalen_s"] > 0).all()
    assert e.df[["datum", "agent_raw"]].drop_duplicates().shape[0] == len(e.df)
    rij = e.df.iloc[0]
    assert rij["gewerkt_s"] >= rij["campagnetijd_s"]


def test_factuur_tekst_steam_stijl():
    t = ("LINK.\nMart Blijleven\nFactuurdatum:\n28/08/2026\nFactuur: 2026080007\nBetreft: Week 35\n"
         "1\n28 uur gewerkt\n€ 700,00\n€ 700,00\nTotaalbedrag excl. btw\n€ 700,00\n"
         " t.n.v. Mart Blijleven o.v.v. \"Factuur 2026080007\".")
    r = parse_factuur_tekst(t)
    assert r["factuurnr"] == "2026080007" and r["week_genoemd"] == 35 and r["uren"] == 28
    assert r["bedrag_excl"] == 700 and r["factuurdatum"] == "2026-08-28" and r["afzender"] == "Mart Blijleven"


def test_factuur_tekst_tabel_stijl():
    t = ("SVV\nEcommerce FACTUUR\n0240\nFACTUURDATUM\nBETALINGSTERMIJN\n30 september 2026\n7 dagen\n"
         "Werkzaamheden\n16,00\n€ 25,00\n€ 400,00\nSubtotaal excl. btw\n€ 400,00\nTen name van SVV Ecommerce\n")
    r = parse_factuur_tekst(t)
    assert r["factuurnr"] == "0240" and r["week_genoemd"] is None and r["uren"] == 16
    assert r["tarief"] == 25 and r["bedrag_excl"] == 400 and r["factuurdatum"] == "2026-09-30"
    assert r["afzender"] == "SVV Ecommerce"


# ---- echte bestanden (alleen lokaal; data/inbox staat niet in git)
ECHT = sorted(INBOX.glob("*")) if INBOX.exists() else []


@pytest.mark.skipif(not ECHT, reason="geen bestanden in data/inbox")
@pytest.mark.parametrize("pad", [p for p in ECHT if p.suffix.lower() in (".xls", ".pdf")], ids=lambda p: p.name)
def test_echte_inbox(pad):
    e = parse_bestand(pad)
    assert e.type in ("A", "B", "C", "F"), f"{pad.name} niet herkend"
    assert len(e.df) > 0
    van, tot = e.periode
    assert van <= tot <= dt.date.today() + dt.timedelta(days=1)

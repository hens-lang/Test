"""Pipeline: ingest -> SQLite -> model, op de fixtures. Controleert ontdubbeling en somregels."""
import shutil

import pandas as pd
import pytest

from conftest import FIXTURES
from link_data import config, model, store
from link_data.export import payload


@pytest.fixture()
def pipeline(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for p in FIXTURES.glob("*.xls"):
        shutil.copy(p, inbox / p.name)
    con = store.verbind(tmp_path / "test.db")
    exports = store.ingest(inbox, con)
    cfg = config.laad()
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"),
                   store.lees(con, "bestanden"), store.lees(con, "facturen"))
    return con, inbox, exports, cfg, m


def test_dubbel_inlezen_geeft_geen_dubbele_data(pipeline, tmp_path):
    con, inbox, exports, *_ = pipeline
    n_c = len(store.lees(con, "contactmomenten"))
    n_u = len(store.lees(con, "uren"))
    shutil.copy(next(inbox.glob("belexport_*")), inbox / "zelfde_bestand_andere_naam.xls")
    store.ingest(inbox, con)
    assert len(store.lees(con, "contactmomenten")) == n_c
    assert len(store.lees(con, "uren")) == n_u
    assert n_c == len(pd.concat([e.df for e in exports if e.type == "A"]).drop_duplicates("sleutel"))


def test_somcontroles(pipeline):
    *_, m = pipeline
    assert all(c["ok"] for c in m.dq["controles"]), m.dq["controles"]
    # betaalde uren in de verdeelsleutel = som urenexport
    assert m.verdeling["uren"].sum() == pytest.approx(m.uren["te_betalen_s"].sum() / 3600)
    # verdeelsleutel per beller per dag telt op tot 1
    a = m.verdeling[m.verdeling["uren"] > 0].groupby(["datum", "beller"])["aandeel"].sum()
    assert (a.round(6) == 1).all()


def test_resultaten_per_klant_gelijk_aan_ruwe_telling(pipeline):
    _, _, exports, cfg, m = pipeline
    ruw = pd.concat([e.df for e in exports if e.type == "A"]).drop_duplicates("sleutel")
    pid = cfg.pid_naar_klant
    telt = {k.naam: set(k.telt_als_resultaat) for k in cfg.klanten.values()}
    ruw["klant"] = ruw["campagne_pid"].map(lambda p: pid.get(int(p), model.niet_gekoppeld_label(int(p))))
    verwacht = ruw[[c in telt.get(k, {100, 101}) for c, k in zip(ruw["code"], ruw["klant"])]].groupby("klant").size()
    assert model.resultaten_per_klant(m).sort_index().to_dict() == verwacht.sort_index().to_dict()


def test_onbekende_pid_wordt_niet_gegokt(pipeline):
    con, _, _, cfg, _ = pipeline
    c = store.lees(con, "contactmomenten")
    c.loc[c.index[:3], "campagne_pid"] = 99999
    m = model.bouw(cfg, c, store.lees(con, "uren"))
    assert [r["pid"] for r in m.dq["niet_gekoppelde_pids"]] == [99999]
    assert "PID 99999 (niet gekoppeld)" in set(m.contacten["klant_label"])


def test_null_velden_crashen_niet(pipeline):
    *_, cfg, m = pipeline
    assert any(o["veld"] == "fee_per_4wk" for o in m.dq["ontbrekende_config"])
    t = m.targets.set_index("klant")
    assert t.loc["KIK Ongediertebestrijding", "stoplicht"] == "startdatum ontbreekt"
    p = payload(m, cfg)
    assert p["feiten"]["c"] and p["feiten"]["u"]


def test_factuur_vervangt_geschatte_kosten(pipeline):
    con, _, _, cfg, _ = pipeline
    u = store.lees(con, "uren")
    zzp = u[u["agent_raw"] == "M. Blijleven"]
    if zzp.empty:
        pytest.skip("geen ZZP-uren in fixture")
    dag = pd.to_datetime(zzp["datum"].iloc[0]).date()
    f = pd.DataFrame([{"sleutel": "Mart Blijleven|T1", "afzender": "Mart Blijleven", "factuurnr": "T1",
                       "factuurdatum": dag.isoformat(), "week_genoemd": dag.isocalendar()[1], "uren": 1.0,
                       "tarief": 25.0, "bedrag_excl": 123.45, "omschrijving": "test"}])
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), u, None, f)
    week = m.uren[(m.uren["beller"] == "Mart Blijleven") & (m.uren["kostenbasis"] == "factuur")]
    assert week["kosten_uur"].sum() == pytest.approx(123.45)
    assert all(c["ok"] for c in m.dq["controles"])


def test_historie_export_type_c_wint_van_belexport(pipeline, tmp_path):
    """Een historie-export (één regel per poging) wordt herkend aan de kolommen en overschrijft A-regels."""
    con, _, _, cfg, _ = pipeline
    a = store.lees(con, "contactmomenten").iloc[0]
    d = pd.to_datetime(a["contact_dt"])
    eerder = d - pd.Timedelta(hours=2)
    rijen = "".join(
        f"<tr><td>{a['agent_raw']}</td><td>{t:%d-%m-%Y %H:%M:%S}</td><td>{code}</td>"
        f"<td>{int(a['campagne_pid'])}</td><td>{int(a['ctpid'])}</td></tr>"
        for t, code in ((eerder, "400"), (d, "200")))
    html = ("<html><body><table><thead><tr><th>Naam&nbsp;agent</th><th>Contactmoment&nbsp;datum&nbsp;&amp;&nbsp;tijd</th>"
            f"<th>Resultaatcode</th><th>CampagnePID</th><th>CTPID</th></tr></thead><tbody>{rijen}</tbody></table></body></html>")
    p = tmp_path / "historie_export.xls"
    p.write_text(html, encoding="utf-8")
    from link_data.parsers import parse_bestand
    e = parse_bestand(p)
    assert e.type == "C" and len(e.df) == 2
    voor = len(store.lees(con, "contactmomenten"))
    store.bewaar(con, e)
    c = store.lees(con, "contactmomenten")
    assert len(c) == voor + 1                       # de eerdere poging is nieuw
    assert c.loc[c["sleutel"] == a["sleutel"], "bron"].item() == "C"   # zelfde moment: C wint
    m = model.bouw(cfg, c, store.lees(con, "uren"))
    assert "C" in m.dq["bron_contacten"]

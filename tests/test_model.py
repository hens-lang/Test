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
    assert any(o["veld"] == "belstart" for o in m.dq["ontbrekende_config"])
    t = m.targets.set_index("klant")
    assert t.loc["KIK Ongediertebestrijding", "stoplicht"] == "pauze"   # niet-actieve klant: geen stoplicht
    assert t.loc["Helden Productions", "stoplicht"] == "gestopt"
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


def test_verkoopfacturen_bepalen_opbrengst(pipeline):
    con, _, _, cfg, _ = pipeline
    v = pd.DataFrame([{"sleutel": "T-1|1", "factuurnr": "T-1", "klant_naam": "GrowOn Agency B.V.", "debiteurnr": None,
                       "factuurdatum": "2026-09-01", "regel": 1, "omschrijving": "Retainer werkperiode 2",
                       "werkperiode_nr": 2, "periode_van": "2026-09-01", "periode_tot": "2026-09-28",
                       "bedrag_excl": 1400.0, "is_lead": False, "bron": "pdf"}])
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"), None, None, v)
    o = m.opbrengst[m.opbrengst["klant"] == "GrowOn Agency"]
    assert o["fee"].sum() == pytest.approx(1400.0 * min(28, (m.peildatum - pd.Timestamp("2026-09-01").date()).days + 1) / 28)
    assert o["gefactureerd"].all()
    assert all(c["ok"] for c in m.dq["controles"])
    # startdatum afgeleid uit 'werkperiode 2'
    t = m.targets.set_index("klant").loc["GrowOn Agency"]
    assert t["start_bron"] in ("config", "verkoopfactuur")


def test_conceptfactuur_vervalt_als_echte_factuur_er_is(pipeline):
    con, _, _, cfg, _ = pipeline
    basis = {"debiteurnr": None, "regel": 1, "omschrijving": "", "werkperiode_nr": None, "periode_van": None,
             "periode_tot": None, "is_lead": False, "bron": "mail", "klant_naam": "GrowOn Agency B.V."}
    v = pd.DataFrame([
        {**basis, "sleutel": "concept-x|1", "factuurnr": "concept-x", "factuurdatum": "2026-10-26",
         "bedrag_excl": 1600.0, "status": "te_versturen"},
        {**basis, "sleutel": "2026-0100|1", "factuurnr": "2026-0100", "factuurdatum": "2026-10-27",
         "bedrag_excl": 1600.0, "status": "open"},
    ])
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"), None, None, v)
    assert m.verkoop["factuurnr"].tolist() == ["2026-0100"]
    assert m.dq["mogelijk_dubbel"] == []


def test_verdeelsleutel_gekalibreerd_op_steam_beltijd(pipeline):
    con, _, _, cfg, _ = pipeline
    from link_data.parsers import parse_bestand
    st = parse_bestand(FIXTURES / "contactstatistics_agents_2026-10-01.xls").df
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"), None, None, None, st)
    for b in m.verdeling["beller"].dropna().unique():
        s = m.stats[m.stats.beller == b].groupby("klant").recordtijd_s.sum()
        if s.empty:
            continue
        v = m.verdeling[(m.verdeling.beller == b) & (m.verdeling.uren > 0)].groupby("klant").uren.sum()
        d = pd.concat([s / s.sum(), v / v.sum()], axis=1).fillna(0)
        assert (d.iloc[:, 0] - d.iloc[:, 1]).abs().max() < 0.005, b
    a = m.verdeling[m.verdeling.uren > 0].groupby(["datum", "beller"]).aandeel.sum()
    assert (a.round(6) == 1).all()
    assert all(c["ok"] for c in m.dq["controles"])


def test_memo_classificatie_moyee(pipeline):
    con, _, _, cfg, _ = pipeline
    c = store.lees(con, "contactmomenten").head(5).copy()
    c["campagne_pid"] = 11
    c["code"] = 101
    c["code_raw"] = "101"
    c["memo"] = ["01-09-2026 10:00:00 kortingscode meegegeven",                 # lead (stempel telt niet)
                 "Flavia Monday to thursday 16-09-2026 10:00",                  # afspraak
                 "Afspraak is ingepland in oktober",                            # afspraak
                 "enthousiast, offerte sturen en daarna proeverij inplannen",   # lead (nog niet gepland)
                 "Op 20 augustus perfect voor de proeverij. do 20 augustus 09:30"]  # tasting gepland
    c["sleutel"] = [f"t{i}" for i in range(5)]
    m = model.bouw(cfg, c, store.lees(con, "uren"))
    assert m.contacten.sort_values("sleutel")["code_eff"].tolist() == [101, 100, 100, 101, 100]


def _html(kop, rijen):
    th = "".join(f"<th>{k}</th>" for k in kop)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rijen)
    return f"<html><body><table id='idTableRapportage'><tr>{th}</tr>{tr}</table></body></html>"


def test_belpogingen_utc_en_werkdag_uit_inlog(pipeline, tmp_path):
    con, _, _, cfg, _ = pipeline
    from link_data.parsers import parse_bestand
    pk = ["Campagne", "Project", "CallerID", "CtPID", "ChPID", "Contactdatum", "Gecontacteerd door",
          "Gekozen nummer", "Status", "SIP Response"]
    # 06:30 UTC = 08:30 Nederlandse zomertijd
    p_rows = [["GrowOn Agency", "x", "1", str(i), str(i), f"2026-09-30 {6 + i // 10:02d}:{(i * 5) % 60:02d}:00",
               "M. Blijleven", "0000", "Gesprek verbonden" if i % 2 else "Kon niet verbinden", ""] for i in range(60)]
    (tmp_path / "Call_attempts_statuses_x.xls").write_text(_html(pk, p_rows), encoding="utf-8")
    sk = ["PersoneelsPID", "Personeel", "Ingelogd", "Uitgelogd", "Ingelogde tijd", "Sessie-ID", "IP-address", "Afdeling", "Functie"]
    s_rows = [["7", "Mart Blijleven", "30-9-2026 08:30:00", "30-9-2026 23:59:00", "15:29:00", "{A}", "-", "Agents", "Agent"]]
    (tmp_path / "LogIn_Out_x.xls").write_text(_html(sk, s_rows), encoding="utf-8")
    P = parse_bestand(tmp_path / "Call_attempts_statuses_x.xls")
    L = parse_bestand(tmp_path / "LogIn_Out_x.xls")
    assert P.type == "P" and len(P.df) == 60 and "Gekozen nummer" not in P.df.columns
    assert L.type == "L" and "IP-address" not in L.df.columns
    m = model.bouw(cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"),
                   None, None, None, None, None, P.df, L.df)
    assert m.pogingen["uur"].min() == 8                       # omgerekend van UTC
    w = m.werkdagen.set_index("beller").loc["Mart Blijleven"]
    assert w["start"] == 8.5
    assert w["eind_bron"] == "laatste belpoging"              # uitlog om 23:59 is onbetrouwbaar
    assert abs(w["eind"] - (13 + 55 / 60)) < 0.01             # laatste poging 11:55 UTC = 13:55

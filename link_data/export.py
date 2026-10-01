"""Exports uit het model: CSV-tabellen (Google Sheet) en de JSON-payload voor het dashboard."""
from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import pandas as pd

from .config import Config
from .model import NIET_TOEGEREKEND, Model


KOSTENBASIS = {"geschat": 0, "factuur": 1, "vast": 2, "geen": 3, "afspraak": 4}


def csv_export(model: Model, map_: Path) -> list[Path]:
    map_ = Path(map_)
    map_.mkdir(parents=True, exist_ok=True)
    c = model.contacten
    tabellen = {
        "contactmomenten.csv": c.drop(columns=["bedrijf", "memo"], errors="ignore"),
        "uren_per_dag.csv": model.uren,
        "steam_contactstatistieken.csv": model.stats,
        "facturen.csv": model.facturen,
        "verdeelsleutel.csv": model.verdeling,
        "opbrengst_per_dag.csv": model.opbrengst,
        "overige_kosten_per_dag.csv": model.overig,
        "verkoopfacturen.csv": model.verkoop,
        "targets_huidige_werkperiode.csv": model.targets,
    }
    # Weekoverzicht per opdrachtgever, handig voor het Omzet Dashboard.
    def week(s):
        return pd.to_datetime(s).dt.strftime("%G-W%V")
    v = model.verdeling.assign(week=week(model.verdeling["datum"])).groupby(["week", "klant"])[["uren", "kosten"]].sum()
    o = model.opbrengst.assign(week=week(model.opbrengst["datum"])).groupby(["week", "klant"])[["fee", "leads_eur"]].sum()
    r = (c[c["is_resultaat"]].assign(week=week(c["datum"])).groupby(["week", "klant_label"]).size()
         .rename("resultaten").rename_axis(["week", "klant"]))
    w = pd.concat([v, o, r], axis=1).fillna(0).reset_index()
    w["opbrengst"] = w["fee"] + w["leads_eur"]
    w["marge"] = w["opbrengst"] - w["kosten"]
    tabellen["week_per_opdrachtgever.csv"] = w
    paden = []
    for naam, df in tabellen.items():
        p = map_ / naam
        df.to_csv(p, index=False, sep=";", decimal=",", encoding="utf-8-sig")
        paden.append(p)
    return paden


def _r(x, n=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


def _schoon(v):
    if isinstance(v, (dt.date, pd.Timestamp)):
        return str(v)[:10]
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def payload(model: Model, cfg: Config) -> dict:
    c, u, v, o, x = model.contacten, model.uren, model.verdeling, model.opbrengst, model.overig
    pg = model.pogingen
    alle = [s for s in (c["datum"], u["datum"], v["datum"], o["datum"], x["datum"], pg["datum"] if len(pg) else []) if len(s)]
    eerste = min(s.min() for s in alle)
    laatste = max(s.max() for s in alle)
    datums = [d.isoformat() for d in pd.date_range(eerste, laatste).date]
    di = {d: i for i, d in enumerate(datums)}

    def d(i):
        return di[str(i)[:10]]

    bellers = list(cfg.bellers)
    bi = {b: i for i, b in enumerate(bellers)}
    labels = list(cfg.klanten)
    for lab in list(c["klant_label"].unique()) + list(v["klant"].unique()):
        if lab not in labels and lab != NIET_TOEGEREKEND:
            labels.append(lab)
    labels.append(NIET_TOEGEREKEND)
    ki = {k: i for i, k in enumerate(labels)}
    projecten = sorted(c["project"].unique())
    posten = sorted(x["post"].unique()) if len(x) else []
    pi = {p: i for i, p in enumerate(projecten)}

    klanten = []
    for k in labels:
        kc = cfg.klanten.get(k)
        klanten.append({
            "naam": k, "config": kc is not None,
            "fee": kc and kc.fee_per_4wk, "lead": kc and kc.extra_per_lead,
            "target": kc and kc.target_per_4wk, "deliverable": kc and kc.deliverable,
            "telt_als": kc.telt_als_resultaat if kc else [100, 101], "pids": kc.pids if kc else [],
            "status": kc.status if kc else "onbekend", "lead_code": kc.extra_code if kc else 101,
            "target_wp": (kc.pilot_target if kc and kc.pilot_weken else kc.target_per_4wk) if kc else None,
            "targets_per_code": {str(c): t for c, t in kc.targets_per_code.items()} if kc else {},
            "perioden": (model.dq.get("klant_perioden") or {}).get(k, []),
        })

    feiten = {
        "c": [[d(r.datum), int(r.uur), bi.get(r.beller, -1), ki[r.klant_label], int(r.code_eff) if pd.notna(r.code_eff) else -1,
               int(bool(r.is_max)), pi[r.project], int(bool(r.is_resultaat)), int(bool(r.met_uren))]
              for r in c.itertuples()],
        "u": [[d(r.datum), bi.get(r.beller, -1), int(r.te_betalen_s), int(r.pogingen), int(r.records),
               int(r.afgehandeld), int(r.hits), int(r.wachten_s + r.laden_s + r.unbound_wait_s), int(r.prepare_s),
               int(r.dial_s), int(r.talking_s), int(r.finish_s), int(r.pauzes_s), _r(r.kosten),
               KOSTENBASIS.get(r.kostenbasis, 3)]
              for r in u.itertuples()],
        "v": [[d(r.datum), bi.get(r.beller, -1), ki[r.klant], _r(r.uren, 4), _r(r.pogingen, 3), _r(r.kosten, 3)]
              for r in v.itertuples()],
        "o": [[d(r.datum), ki[r.klant], _r(r.fee, 3), _r(r.leads_eur), int(r.leads), int(bool(r.gefactureerd))]
              for r in o.itertuples()],
        "x": [[d(r.datum), _r(r.bedrag, 3), posten.index(r.post), int(r.basis == "factuur")] for r in x.itertuples()],
        # Belpogingen: dag, uur (decimaal), beller, klant, verbonden
        "p": [[d(r.datum), round(pd.Timestamp(r.poging_dt).hour + pd.Timestamp(r.poging_dt).minute / 60, 3), bi.get(r.beller, -1), ki.get(r.klant, ki[NIET_TOEGEREKEND]) if r.klant else ki[NIET_TOEGEREKEND],
               int(r.verbonden)] for r in pg.itertuples()] if len(pg) else [],
        # Werkdag uit in- en uitlogtijden: dag, beller, start (uur, decimaal), eind
        "w": [[d(r.datum), bi.get(r.beller, -1), r.start, r.eind] for r in model.werkdagen.itertuples()
              if str(r.datum) in di] if len(model.werkdagen) else [],
        # Steam-contactstatistieken (cumulatief, geen datum): beller, klant, pogingen, calls, hits, afgehandeld,
        # beltijd (s), gesprekstijd (s)
        "s": [[bi.get(r.beller, -1), ki.get(r.klant, ki[NIET_TOEGEREKEND]) if r.klant else ki[NIET_TOEGEREKEND],
               int(r.contactpogingen), int(r.calls), int(r.hits), int(r.afgehandeld), int(r.recordtijd_s),
               int(r.gesprek_s)] for r in model.stats.itertuples()] if len(model.stats) else [],
    }
    inst = cfg.instellingen
    return {
        "meta": {
            "peildatum": model.peildatum.isoformat(), "gegenereerd": dt.datetime.now().strftime("%d-%m-%Y %H:%M"),
            "bron_contacten": model.dq.get("bron_contacten", []),
            "werkdag_bron": model.dq.get("werkdag_bron"),
            "anker": inst["werkperiode_anker"].isoformat(),
            "focus_drempel": inst.get("focus_drempel", 0.8),
            "uur_start": inst.get("beldag_start_uur", 8), "uur_eind": inst.get("beldag_eind_uur", 17),
            "werkdagen_per_week": inst.get("werkdagen_per_week", 5),
            "tarief_nu": (inst.get("scenario") or {}).get("tarief_nu", 25),
            "tarief_doel": (inst.get("scenario") or {}).get("tarief_doel", 36),
            "normen": inst.get("normen") or {},
        },
        "datums": datums,
        "bellers": [{"naam": b, "type": cfg.bellers[b].type, "tarief_nu": cfg.bellers[b].tarief_nu,
                     "tarief_nieuw": cfg.bellers[b].tarief_nieuw,
                     "vast": cfg.bellers[b].vaste_vergoeding_per_maand} for b in bellers],
        "klanten": klanten,
        "projecten": projecten,
        "kostenposten": posten,
        "feiten": feiten,
        "targets": [{k: _schoon(val) for k, val in r.items()} for r in model.targets.to_dict("records")],
        "dq": {k: ([{kk: _schoon(vv) for kk, vv in r.items()} for r in val] if isinstance(val, list)
                   and val and isinstance(val[0], dict) else val) for k, val in model.dq.items()},
    }

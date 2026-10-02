"""Eén commando: ingest -> model -> dashboard -> CSV-export.

    python run.py                    alles
    python run.py --alleen-dashboard sla ingest over, bouw vanuit data/link.db
    python run.py --opnieuw          gooi data/link.db weg en lees alle exports opnieuw in
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from link_data import config, model as model_mod, store
from link_data.config import ROOT
from link_data.export import csv_export

INBOX = ROOT / "data" / "inbox"
EXPORT = ROOT / "data" / "export"


def _resultaatcontrole(exports, m) -> list[dict]:
    """Resultaten per opdrachtgever in het model = telling in de ruwe exports (unieke contactmomenten)."""
    ruw = pd.concat([e.df for e in exports if e.type in ("A", "C") and len(e.df)], ignore_index=True)
    if ruw.empty:
        return []
    ruw = ruw.drop_duplicates("sleutel")
    ruw = ruw[pd.to_datetime(ruw["datum"]).dt.date <= m.peildatum]   # zelfde peildatum als het model
    pid_map = m_cfg.pid_naar_klant
    telt = {k.naam: set(k.telt_als_resultaat) for k in m_cfg.klanten.values()}
    ruw["klant"] = ruw["campagne_pid"].map(lambda p: pid_map.get(int(p), model_mod.niet_gekoppeld_label(int(p))))
    ruw["res"] = [c in telt.get(k, {100, 101}) for c, k in zip(ruw["code"], ruw["klant"])]
    bron = ruw[ruw["res"]].groupby("klant").size()
    mod = model_mod.resultaten_per_klant(m)
    rijen = []
    for k in sorted(set(bron.index) | set(mod.index)):
        a, b = int(mod.get(k, 0)), int(bron.get(k, 0))
        rijen.append({"controle": f"Resultaten {k}", "dashboard": a, "bron": b, "ok": a == b})
    return rijen


def main(argv=None):
    global m_cfg
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alleen-dashboard", action="store_true")
    ap.add_argument("--opnieuw", action="store_true")
    args = ap.parse_args(argv)

    m_cfg = config.laad()
    if args.opnieuw and store.DB_PAD.exists():
        store.DB_PAD.unlink()
    con = store.verbind()

    exports = []
    if not args.alleen_dashboard:
        INBOX.mkdir(parents=True, exist_ok=True)
        exports = store.ingest(INBOX, con)
        print(f"Ingelezen uit {INBOX.relative_to(ROOT)}:")
        for e in exports:
            van, tot = e.periode
            extra = ""
            if e.type in ("A", "C") and len(e.df):
                extra = f" PID {', '.join(map(str, sorted(e.df['campagne_pid'].dropna().unique())))}"
            elif e.type == "F" and len(e.df):
                extra = f" {e.df['afzender'].iloc[0]} € {e.df['bedrag_excl'].iloc[0]:.2f}"
            elif e.type == "V" and len(e.df):
                extra = f" {e.df['klant_naam'].iloc[0]} € {e.df['bedrag_excl'].sum():.2f}"
            print(f"  [{e.type}] {e.pad.name:55s} {len(e.df):5d} rijen  {van} t/m {tot}{extra} {e.melding}")

    m = model_mod.bouw(m_cfg, store.lees(con, "contactmomenten"), store.lees(con, "uren"),
                       store.lees(con, "bestanden"), store.lees(con, "facturen"),
                       store.lees(con, "verkoopfacturen"), store.lees(con, "steamstats"),
                       store.lees(con, "campagneresultaten"), store.lees(con, "belpogingen"),
                       store.lees(con, "sessies"))
    if exports:
        m.dq["controles"].extend(_resultaatcontrole(exports, m))

    from build_dashboard import bouw_dashboard
    pad = bouw_dashboard(m, m_cfg)
    csvs = csv_export(m, EXPORT)

    print(f"\nPeildatum: {m.peildatum} (laatste dag in de urenexport; alles telt tot en met deze dag)")
    na = m.dq.get("na_peildatum") or {}
    if na.get("bronnen"):
        bronnen = ", ".join(f"{b} t/m {d}" for b, d in na["bronnen"].items())
        print(f"  Wacht op urenexport: {bronnen}. {na['belregels']} belregels "
              f"({sum(na['resultaten'].values())} resultaten) tellen mee zodra PayableHoursPerDay die dagen bevat.")
    print("Controles:")
    for c in m.dq["controles"]:
        print(f"  {'OK ' if c['ok'] else 'AFW'} {c['controle']}: dashboard {c['dashboard']} / bron {c['bron']}")
    for titel, sleutel in (("Niet gekoppelde PID's", "niet_gekoppelde_pids"),
                           ("Niet gekoppelde agents", "niet_gekoppelde_agents"),
                           ("Werkperiodes zonder verkoopfactuur", "werkperiodes_zonder_verkoopfactuur")):
        if m.dq[sleutel]:
            print(f"{titel}: {m.dq[sleutel]}")
    print(f"\nDashboard: {pad.relative_to(ROOT)}")
    print(f"CSV-export: {len(csvs)} bestanden in {EXPORT.relative_to(ROOT)}")
    return 0 if all(c["ok"] for c in m.dq["controles"]) else 1


m_cfg = None

if __name__ == "__main__":
    sys.exit(main())

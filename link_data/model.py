"""Bouwt de schone tabellen en KPI-basis uit data/link.db + config.

Alle bedragen en tellingen komen hier vandaan: het dashboard, de CSV-export en de tests
lezen dezelfde `Model`-tabellen. Het dashboard aggregeert ze alleen (filters, periodes).

Tabellen in Model:
  contacten   één regel per contactmoment, met beller, klant, groep en resultaatvlag
  uren        één regel per beller per dag, met uren, tarief en kosten
              (kostenbasis: factuur, geschat = uren x tarief, of vast = vaste vergoeding)
  facturen    facturen van bellers, met toegewezen week
  verdeling   verdeelsleutel: uren, pogingen en kosten per dag x beller x klant
  opbrengst   per dag x klant: vaste fee (fee / 28 per kalenderdag) en leadfee
  overig      overige kosten per dag
  targets     stand van de huidige werkperiode per klant
  dq          datakwaliteit (lijsten en controles)
"""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import codes
from .config import Config

NIET_TOEGEREKEND = "Niet toegerekend"


def niet_gekoppeld_label(pid) -> str:
    return f"PID {pid} (niet gekoppeld)"


@dataclass
class Model:
    contacten: pd.DataFrame
    uren: pd.DataFrame
    facturen: pd.DataFrame
    verdeling: pd.DataFrame
    opbrengst: pd.DataFrame
    overig: pd.DataFrame
    targets: pd.DataFrame
    peildatum: dt.date
    dq: dict = field(default_factory=dict)


# ---------------------------------------------------------------- hulpfuncties

def werkdagen(van: dt.date, tot: dt.date) -> int:
    """Werkdagen (ma-vr) van t/m tot, inclusief."""
    if tot < van:
        return 0
    return int(np.busday_count(van, tot + dt.timedelta(days=1)))


def _dagen_in_maand(d: dt.date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


# ---------------------------------------------------------------- bouwstenen

def _contacten(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    df = df.copy()
    pid_map = cfg.pid_naar_klant
    df["beller"] = df["agent_raw"].map(cfg.beller_voor)
    df["klant"] = df["campagne_pid"].map(lambda p: pid_map.get(int(p)) if pd.notna(p) else None)
    df["klant"] = df["klant"].where(df["klant"].notna(), None)
    df["klant_label"] = [k if isinstance(k, str) else niet_gekoppeld_label(int(p)) if pd.notna(p) else NIET_TOEGEREKEND
                         for k, p in zip(df["klant"], df["campagne_pid"])]
    telt = {k.naam: set(k.telt_als_resultaat) for k in cfg.klanten.values()}
    df["is_resultaat"] = [c in telt.get(k, codes.RESULTAAT) for c, k in zip(df["code"], df["klant"])]
    df["is_lead"] = df["code"] == codes.LEAD
    df["groep"] = df["code"].map(codes.groep)
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    df["project"] = df["project"].fillna("(onbekend)")
    return df.sort_values("contact_dt").reset_index(drop=True)


def _uren(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    df = df.copy()
    df["beller"] = df["agent_raw"].map(cfg.beller_voor)
    df["datum"] = pd.to_datetime(df["datum"]).dt.date
    df["uren"] = df["te_betalen_s"] / 3600

    def tarief(r):
        b = cfg.bellers.get(r.beller)
        return (b.tarief_op(r.datum) if b else None)
    df["tarief"] = [tarief(r) for r in df.itertuples()]
    df["kosten_uur"] = df["uren"] * df["tarief"].fillna(0)
    df["kosten_vast"] = 0.0
    return df.sort_values(["datum", "agent_raw"]).reset_index(drop=True)


def _vaste_vergoedingen(uren: pd.DataFrame, cfg: Config, peildatum: dt.date):
    """Verdeelt vaste maandvergoedingen over de betaalde uren in die maand.
    Maanden zonder uren komen als dagregels zonder uren terug (worden 'Niet toegerekend')."""
    zonder_uren = []
    for b in cfg.bellers.values():
        if not b.vaste_vergoeding_per_maand or not b.vaste_vergoeding_vanaf:
            continue
        eind = min(peildatum, b.vertrokken_per) if b.vertrokken_per else peildatum
        m = dt.date(b.vaste_vergoeding_vanaf.year, b.vaste_vergoeding_vanaf.month, 1)
        while m <= eind:
            dim = _dagen_in_maand(m)
            laatste = min(dt.date(m.year, m.month, dim), eind)
            bedrag = b.vaste_vergoeding_per_maand * (laatste.day / dim)
            mask = (uren["beller"] == b.naam) & (pd.to_datetime(uren["datum"]).dt.to_period("M")
                                                 == pd.Period(m, "M")) & (uren["datum"] <= laatste)
            totaal_s = uren.loc[mask, "te_betalen_s"].sum()
            if totaal_s > 0:
                uren.loc[mask, "kosten_vast"] += bedrag * uren.loc[mask, "te_betalen_s"] / totaal_s
            else:
                per_dag = bedrag / laatste.day
                for d in range(1, laatste.day + 1):
                    zonder_uren.append({"datum": dt.date(m.year, m.month, d), "beller": b.naam,
                                        "klant": NIET_TOEGEREKEND, "aandeel": 1.0, "uren": 0.0,
                                        "pogingen": 0.0, "kosten": per_dag, "basis": "vaste vergoeding"})
            m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return pd.DataFrame(zonder_uren)


def _maandag(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())


def _facturen(f: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    f = f.copy()
    if f.empty:
        return pd.DataFrame(columns=["afzender", "factuurnr", "factuurdatum", "week_genoemd", "uren", "tarief",
                                     "bedrag_excl", "beller", "week_start", "week_bron"])
    drempel = int(cfg.instellingen.get("factuur_zelfde_week_vanaf_weekdag", 4))
    f["factuurdatum"] = pd.to_datetime(f["factuurdatum"]).dt.date
    f["beller"] = f["afzender"].map(cfg.beller_voor_afzender)

    def week(r):
        if pd.notna(r.week_genoemd):
            return dt.date.fromisocalendar(r.factuurdatum.isocalendar()[0], int(r.week_genoemd), 1), "factuur"
        ma = _maandag(r.factuurdatum)
        if r.factuurdatum.isoweekday() >= drempel:
            return ma, "afgeleid (zelfde week)"
        return ma - dt.timedelta(days=7), "afgeleid (week ervoor)"
    w = [week(r) for r in f.itertuples()]
    f["week_start"] = [x[0] for x in w]
    f["week_bron"] = [x[1] for x in w]
    return f.sort_values(["beller", "week_start"]).reset_index(drop=True)


def _pas_facturen_toe(uren: pd.DataFrame, facturen: pd.DataFrame):
    """Weken met een factuur: kosten = gefactureerd bedrag, verdeeld over de Steam-uren van die week."""
    uren["kostenbasis"] = np.where(uren["tarief"].fillna(0) > 0, "geschat", "geen")
    uren["week_start"] = [_maandag(d) for d in uren["datum"]]
    extra = []
    for (b, w), g in facturen.dropna(subset=["beller"]).groupby(["beller", "week_start"]):
        bedrag = g["bedrag_excl"].sum()
        mask = (uren["beller"] == b) & (uren["week_start"] == w)
        tot = uren.loc[mask, "te_betalen_s"].sum()
        if tot > 0:
            uren.loc[mask, "kosten_uur"] = bedrag * uren.loc[mask, "te_betalen_s"] / tot
            uren.loc[mask, "kostenbasis"] = "factuur"
        else:
            extra.append({"datum": w, "beller": b, "klant": NIET_TOEGEREKEND, "aandeel": 1.0, "uren": 0.0,
                          "pogingen": 0.0, "kosten": bedrag, "basis": "factuur zonder Steam-uren"})
    return pd.DataFrame(extra)


def _factuurvergelijking(uren: pd.DataFrame, facturen: pd.DataFrame, cfg: Config) -> list:
    zzp = {b.naam for b in cfg.bellers.values() if (b.tarief_nu or 0) > 0}
    u = (uren[uren["beller"].isin(zzp)].assign(geschat=lambda x: x["uren"] * x["tarief"])
         .groupby(["beller", "week_start"]).agg(steam_uren=("uren", "sum"), geschat=("geschat", "sum")))
    f = (facturen.dropna(subset=["beller"]).groupby(["beller", "week_start"])
         .agg(factuur_uren=("uren", "sum"), gefactureerd=("bedrag_excl", "sum"),
              facturen=("factuurnr", lambda x: ", ".join(map(str, x))),
              week_bron=("week_bron", "first")))
    m = pd.concat([u, f], axis=1).reset_index()
    rijen = []
    for r in m.sort_values(["beller", "week_start"]).itertuples():
        heeft_f = pd.notna(r.gefactureerd)
        heeft_u = pd.notna(r.steam_uren)
        status = ("gefactureerd" if heeft_f and heeft_u else "nog geen factuur" if heeft_u
                  else "factuur zonder Steam-uren")
        iso = r.week_start.isocalendar()
        rijen.append({
            "beller": r.beller, "week": f"{iso[0]}-W{iso[1]:02d}", "week_start": str(r.week_start),
            "steam_uren": round(r.steam_uren, 2) if heeft_u else None,
            "factuur_uren": r.factuur_uren if heeft_f else None,
            "verschil_uren": round(r.factuur_uren - r.steam_uren, 2) if heeft_f and heeft_u else None,
            "geschat": round(r.geschat, 2) if heeft_u else None,
            "gefactureerd": r.gefactureerd if heeft_f else None,
            "facturen": r.facturen if heeft_f else "", "week_bron": r.week_bron if heeft_f else "",
            "status": status})
    return rijen


def _verdeling(uren: pd.DataFrame, contacten: pd.DataFrame, extra: pd.DataFrame) -> pd.DataFrame:
    """Verdeelsleutel: uren/kosten per beller per dag naar rato van contactmomenten per klant."""
    tel = (contacten.dropna(subset=["beller"]).groupby(["datum", "beller", "klant_label"])
           .size().rename("n").reset_index())
    tel["aandeel"] = tel["n"] / tel.groupby(["datum", "beller"])["n"].transform("sum")
    u = uren.dropna(subset=["beller"]).groupby(["datum", "beller"], as_index=False).agg(
        uren=("uren", "sum"), pogingen=("pogingen", "sum"), kosten=("kosten", "sum"))
    v = u.merge(tel[["datum", "beller", "klant_label", "aandeel"]], on=["datum", "beller"], how="left")
    v["basis"] = np.where(v["klant_label"].isna(), "geen belregels", "belregels")
    v["klant_label"] = v["klant_label"].fillna(NIET_TOEGEREKEND)
    v["aandeel"] = v["aandeel"].fillna(1.0)
    for c in ("uren", "pogingen", "kosten"):
        v[c] = v[c] * v["aandeel"]
    v = v.rename(columns={"klant_label": "klant"})
    if not extra.empty:
        v = pd.concat([v, extra], ignore_index=True)
    return v[["datum", "beller", "klant", "aandeel", "uren", "pogingen", "kosten", "basis"]]


def _startdatum(klant, contacten) -> tuple[dt.date | None, str]:
    if klant.belstart:
        return klant.belstart, "config"
    eigen = contacten[contacten["klant"] == klant.naam]
    if not eigen.empty:
        return eigen["datum"].min(), "eerste belregel"
    return None, "ontbreekt"


def _opbrengst(cfg: Config, contacten: pd.DataFrame, peildatum: dt.date) -> pd.DataFrame:
    rijen = []
    for k in cfg.klanten.values():
        start, _ = _startdatum(k, contacten)
        if k.fee_per_4wk and start and start <= peildatum:
            for d in pd.date_range(start, peildatum).date:
                rijen.append({"datum": d, "klant": k.naam, "fee": k.fee_per_4wk / 28, "leads_eur": 0.0, "leads": 0})
        if k.extra_per_lead:
            leads = contacten[(contacten["klant"] == k.naam) & contacten["is_lead"]].groupby("datum").size()
            for d, n in leads.items():
                rijen.append({"datum": d, "klant": k.naam, "fee": 0.0,
                              "leads_eur": n * k.extra_per_lead, "leads": int(n)})
    df = pd.DataFrame(rijen, columns=["datum", "klant", "fee", "leads_eur", "leads"])
    return df.groupby(["datum", "klant"], as_index=False).sum()


def _overig(cfg: Config, peildatum: dt.date, eerste: dt.date) -> pd.DataFrame:
    posten = {p: b for p, b in (cfg.instellingen.get("overige_kosten_per_maand") or {}).items() if b}
    totaal = sum(posten.values())
    van = cfg.instellingen.get("overige_kosten_vanaf") or eerste
    if not totaal or van > peildatum:
        return pd.DataFrame(columns=["datum", "bedrag"])
    dagen = pd.date_range(van, peildatum).date
    return pd.DataFrame({"datum": dagen, "bedrag": [totaal / _dagen_in_maand(d) for d in dagen]})


def _targets(cfg: Config, contacten: pd.DataFrame, peildatum: dt.date) -> pd.DataFrame:
    groen = cfg.instellingen.get("stoplicht_groen", 1.0)
    oranje = cfg.instellingen.get("stoplicht_oranje", 0.8)
    rijen = []
    for k in cfg.klanten.values():
        start, bron = _startdatum(k, contacten)
        r = {"klant": k.naam, "target": k.target_per_4wk, "start": start, "start_bron": bron,
             "telt_als": "+".join(map(str, k.telt_als_resultaat))}
        eigen = contacten[(contacten["klant"] == k.naam) & contacten["is_resultaat"]]
        if start and start <= peildatum:
            nr = (peildatum - start).days // 28
            p_van = start + dt.timedelta(days=28 * nr)
            p_tot = p_van + dt.timedelta(days=27)
            res = int(((eigen["datum"] >= p_van) & (eigen["datum"] <= p_tot)).sum())
            verstreken = werkdagen(p_van, peildatum)
            totaal = werkdagen(p_van, p_tot)
            rest = werkdagen(peildatum + dt.timedelta(days=1), p_tot)
            prognose = res / verstreken * totaal if verstreken else None
            r.update(periode_nr=nr + 1, periode_van=p_van, periode_tot=p_tot, resultaten=res,
                     werkdagen_verstreken=verstreken, werkdagen_rest=rest, prognose=prognose)
            if k.target_per_4wk:
                ratio = (prognose or 0) / k.target_per_4wk
                r["stoplicht"] = "groen" if ratio >= groen else "oranje" if ratio >= oranje else "rood"
                r["benodigd_per_werkdag"] = (max(0, k.target_per_4wk - res) / rest) if rest else None
            else:
                r["stoplicht"] = "geen target"
        else:
            r.update(stoplicht="nog niet gestart" if start else "startdatum ontbreekt",
                     resultaten=int(len(eigen)))
        rijen.append(r)
    return pd.DataFrame(rijen)


# ---------------------------------------------------------------- datakwaliteit

def _datakwaliteit(cfg, contacten, uren, bestanden, verdeling, ruwe_uren_s) -> dict:
    dq = {}
    dq["bestanden"] = bestanden.sort_values("naam").to_dict("records")

    bronnen = (contacten.groupby(["bron", "klant_label"]).agg(
        rijen=("sleutel", "size"), van=("datum", "min"), tot=("datum", "max")).reset_index())
    ub = uren.groupby("agent_raw").agg(rijen=("datum", "size"), van=("datum", "min"), tot=("datum", "max")).reset_index()
    ub.insert(0, "bron", "B")
    dq["periodes"] = ([{"bron": r.bron, "onderwerp": r.klant_label, "rijen": int(r.rijen),
                        "van": str(r.van), "tot": str(r.tot)} for r in bronnen.itertuples()]
                      + [{"bron": "B", "onderwerp": r.agent_raw, "rijen": int(r.rijen),
                          "van": str(r.van), "tot": str(r.tot)} for r in ub.itertuples()])

    ng = contacten[contacten["klant"].isna()]
    dq["niet_gekoppelde_pids"] = [
        {"pid": int(p), "campagne_in_export": ", ".join(sorted(set(g["campagne_naam"].dropna()))) or "-",
         "projecten": ", ".join(sorted(set(g["project"].dropna()))[:3]), "rijen": len(g),
         "van": str(g["datum"].min()), "tot": str(g["datum"].max())}
        for p, g in ng.groupby("campagne_pid")]

    agents = pd.concat([contacten[["agent_raw", "beller"]].assign(bron="belexport"),
                        uren[["agent_raw", "beller"]].assign(bron="urenexport")])
    dq["niet_gekoppelde_agents"] = [
        {"agent": a, "bron": ", ".join(sorted(set(g["bron"]))), "rijen": len(g)}
        for a, g in agents[agents["beller"].isna()].groupby("agent_raw")]

    c_dag = contacten.dropna(subset=["beller"]).groupby(["beller", "datum"]).size().rename("belregels")
    u_dag = uren.dropna(subset=["beller"]).groupby(["beller", "datum"]).agg(
        uren=("uren", "sum"), pogingen=("pogingen", "sum"))
    m = pd.concat([c_dag, u_dag], axis=1).fillna(0).reset_index()
    zonder_uren = m[(m["belregels"] > 0) & (m["uren"] == 0)]
    dq["bellers_zonder_uren"] = [
        {"beller": b, "dagen": len(g), "belregels": int(g["belregels"].sum()),
         "van": str(g["datum"].min()), "tot": str(g["datum"].max())}
        for b, g in zonder_uren.groupby("beller")]
    gekoppeld = {b for b in cfg.bellers}
    dq["bellers_zonder_data"] = [b for b in gekoppeld
                                 if b not in set(contacten["beller"].dropna()) | set(uren["beller"].dropna())]
    mis = m[((m["uren"] > 0) & (m["belregels"] == 0)) | ((m["belregels"] > 0) & (m["uren"] == 0))]
    dq["dagen_niet_aansluitend"] = [
        {"datum": str(r.datum), "beller": r.beller, "uren": round(r.uren, 2), "pogingen_urenexport": int(r.pogingen),
         "belregels": int(r.belregels),
         "probleem": "uren zonder belregels" if r.belregels == 0 else "belregels zonder uren"}
        for r in mis.sort_values(["datum", "beller"]).itertuples()]
    dq["ontbrekende_config"] = [{"onderwerp": o, "veld": v} for o, v in cfg.ontbrekend]
    zonder_data = [k.naam for k in cfg.klanten.values()
                   if k.naam not in set(contacten["klant"].dropna())]
    dq["klanten_zonder_beldata"] = zonder_data

    # Somcontroles
    totaal_model = verdeling["uren"].sum()
    dq["controles"] = [
        {"controle": "Betaalde uren: dashboard = som urenexport",
         "dashboard": round(totaal_model, 2), "bron": round(ruwe_uren_s / 3600, 2),
         "ok": bool(abs(totaal_model - ruwe_uren_s / 3600) < 0.01)},
    ]
    return dq


# ---------------------------------------------------------------- publiek

def bouw(cfg: Config, contacten_raw: pd.DataFrame, uren_raw: pd.DataFrame,
         bestanden: pd.DataFrame | None = None, facturen_raw: pd.DataFrame | None = None) -> Model:
    contacten = _contacten(contacten_raw, cfg)
    uren = _uren(uren_raw, cfg)
    facturen = _facturen(facturen_raw if facturen_raw is not None else pd.DataFrame(), cfg)
    extra_f = _pas_facturen_toe(uren, facturen)
    # Peildatum = laatste dag met uren: kosten en opbrengst lopen dan over dezelfde periode.
    if len(uren):
        peildatum = uren["datum"].max()
    elif len(contacten):
        peildatum = contacten["datum"].max()
    else:
        peildatum = dt.date.today()
    eerste = min([d for d in (contacten["datum"].min() if len(contacten) else None,
                              uren["datum"].min() if len(uren) else None) if d] or [peildatum])

    extra = _vaste_vergoedingen(uren, cfg, peildatum)
    uren.loc[uren["kosten_vast"] > 0, "kostenbasis"] = "vast"
    extra = pd.concat([x for x in (extra, extra_f) if len(x)], ignore_index=True) if len(extra) or len(extra_f) \
        else pd.DataFrame()
    uren["kosten"] = uren["kosten_uur"] + uren["kosten_vast"]
    uren["uurkosten_effectief"] = np.where(uren["uren"] > 0, uren["kosten"] / uren["uren"], 0)

    dagen_met_uren = set(zip(uren["beller"], uren["datum"]))
    contacten["met_uren"] = [(b, d) in dagen_met_uren for b, d in zip(contacten["beller"], contacten["datum"])]

    verdeling = _verdeling(uren, contacten, extra)
    opbrengst = _opbrengst(cfg, contacten, peildatum)
    overig = _overig(cfg, peildatum, eerste)
    targets = _targets(cfg, contacten, peildatum)
    dq = _datakwaliteit(cfg, contacten, uren,
                        bestanden if bestanden is not None else pd.DataFrame(columns=["naam"]),
                        verdeling, uren_raw["te_betalen_s"].sum())
    dq["controles"].append({
        "controle": "Kosten: verdeelsleutel = kosten per beller (facturen / uren x tarief + vaste vergoeding)",
        "dashboard": round(verdeling["kosten"].sum(), 2),
        "bron": round(uren["kosten"].sum() + (extra["kosten"].sum() if len(extra) else 0), 2),
        "ok": bool(abs(verdeling["kosten"].sum() - uren["kosten"].sum()
                       - (extra["kosten"].sum() if len(extra) else 0)) < 0.01)})
    dq["bron_contacten"] = sorted(contacten["bron"].unique().tolist())
    dq["factuurvergelijking"] = _factuurvergelijking(uren, facturen, cfg)
    dq["facturen"] = [{"afzender": r.afzender, "beller": r.beller or "niet gekoppeld", "factuurnr": r.factuurnr,
                       "factuurdatum": str(r.factuurdatum), "week": f"{r.week_start.isocalendar()[0]}-W{r.week_start.isocalendar()[1]:02d}",
                       "week_bron": r.week_bron, "uren": r.uren, "bedrag_excl": r.bedrag_excl}
                      for r in facturen.itertuples()]
    if len(facturen):
        gekoppeld = facturen.dropna(subset=["beller"])["bedrag_excl"].sum()
        in_model = (uren.loc[uren["kostenbasis"] == "factuur", "kosten_uur"].sum()
                    + (extra_f["kosten"].sum() if len(extra_f) else 0))
        dq["controles"].append({"controle": "Facturen: kosten in model = som gekoppelde facturen",
                                "dashboard": round(in_model, 2), "bron": round(gekoppeld, 2),
                                "ok": bool(abs(in_model - gekoppeld) < 0.01)})
    return Model(contacten, uren, facturen, verdeling, opbrengst, overig, targets, peildatum, dq)


def resultaten_per_klant(model: Model) -> pd.Series:
    c = model.contacten
    return c[c["is_resultaat"]].groupby("klant_label").size()

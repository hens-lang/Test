"""Bouwt de schone tabellen en KPI-basis uit data/link.db + config.

Alle bedragen en tellingen komen hier vandaan: het dashboard, de CSV-export en de tests
lezen dezelfde `Model`-tabellen. Het dashboard aggregeert ze alleen (filters, periodes).

Tabellen in Model:
  contacten   één regel per contactmoment, met beller, klant, groep en resultaatvlag
  uren        één regel per beller per dag, met uren, tarief en kosten
              (kostenbasis: factuur, geschat = uren x tarief, of vast = vaste vergoeding)
  facturen    facturen van bellers, met toegewezen week
  verdeling   verdeelsleutel: uren, pogingen en kosten per dag x beller x klant
  opbrengst   per dag x klant: gefactureerd (verkoopfactuur over zijn periode) of geschat (fee / 28)
              plus leadfee
  overig      overige kosten per dag, per kostenpost (factuur of geschat)
  verkoop     verkoopfacturen aan opdrachtgevers
  targets     stand van de huidige werkperiode per klant
  dq          datakwaliteit (lijsten en controles)
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import codes
from .config import Config

NIET_TOEGEREKEND = "Niet toegerekend"
MEMO_STEMPEL = re.compile(r"\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}:\d{2}")


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
    verkoop: pd.DataFrame = field(default_factory=pd.DataFrame)
    stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    pogingen: pd.DataFrame = field(default_factory=pd.DataFrame)
    werkdagen: pd.DataFrame = field(default_factory=pd.DataFrame)


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
    # Effectieve code: bij memo_classificatie wordt een resultaat met afspraak in de memo 100, anders 101.
    if "memo" not in df:
        df["memo"] = None
    patronen = [re.compile(p, re.I) for p in (cfg.instellingen.get("memo_afspraak_patronen") or [])]
    memo_klanten = {k.naam for k in cfg.klanten.values() if k.memo_classificatie}
    eff, reden = [], []
    for c, k, memo, res in zip(df["code"], df["klant"], df["memo"], df["is_resultaat"]):
        if k in memo_klanten and res:
            tekst = MEMO_STEMPEL.sub(" ", str(memo or ""))
            hit = next((m.group(0) for p in patronen for m in [p.search(tekst)] if m), None)
            eff.append(100 if (hit or c == 100) else 101)
            kort = hit if hit and len(hit) <= 30 else (f"{hit[:12]} … {hit[-14:]}" if hit else None)
            reden.append(f"memo: '{kort}'" if hit else ("code 100" if c == 100 else "geen afspraak in memo"))
        else:
            eff.append(c)
            reden.append("")
    df["code_eff"] = eff
    df["code_reden"] = reden
    df["is_lead"] = df["code_eff"] == codes.LEAD
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


def _uren_buiten_steam(uren: pd.DataFrame, pogingen: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Uren die niet in de urenexport staan (bellers.yaml: uren_buiten_steam) verdelen over de dagen met
    belpogingen van die beller, naar rato van het aantal pogingen."""
    uren["bron"] = "urenexport"
    extra = []
    for b in cfg.bellers.values():
        ub = b.uren_buiten_steam or {}
        if not ub.get("totaal") or not len(pogingen):
            continue
        tot = ub.get("tot")
        tot = dt.date.fromisoformat(str(tot)) if tot else None
        van = ub.get("van")
        van = dt.date.fromisoformat(str(van)) if van else None
        p = pogingen[(pogingen["beller"] == b.naam)]
        if tot:
            p = p[p["datum"] <= tot]
        if van:
            p = p[p["datum"] >= van]
        n = p.groupby("datum").size()
        if n.empty:
            continue
        for d, k in n.items():
            u = float(ub["totaal"]) * k / n.sum()
            extra.append({"datum": d, "agent_raw": b.naam, "beller": b.naam, "afdeling": "buiten Steam",
                          "pogingen": int(k), "te_betalen_s": int(round(u * 3600)), "uren": u,
                          "tarief": b.tarief_op(d), "kosten_uur": u * (b.tarief_op(d) or 0), "kosten_vast": 0.0,
                          "bron": "uren_buiten_steam"})
    if not extra:
        return uren
    return pd.concat([uren, pd.DataFrame(extra)], ignore_index=True).fillna(
        {c: 0 for c in uren.columns if c.endswith("_s") or c in ("records", "hits", "afgehandeld")})


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


def _pas_facturen_toe(uren: pd.DataFrame, facturen: pd.DataFrame, cfg: Config):
    """Weken met een factuur: kosten = gefactureerd bedrag, verdeeld over de Steam-uren van die week.
    Weken zonder factuur van een beller met uren_per_week_afspraak: afspraak x tarief."""
    uren["kostenbasis"] = np.where(uren["tarief"].fillna(0) > 0, "geschat", "geen")
    uren["week_start"] = [_maandag(d) for d in uren["datum"]]
    for b in cfg.bellers.values():
        if not b.uren_per_week_afspraak:
            continue
        for w, g in uren[(uren["beller"] == b.naam) & (uren["kostenbasis"] == "geschat")].groupby("week_start"):
            tot = g["te_betalen_s"].sum()
            if tot > 0:
                uren.loc[g.index, "kosten_uur"] = (b.uren_per_week_afspraak * g["tarief"] * g["te_betalen_s"] / tot)
                uren.loc[g.index, "kostenbasis"] = "afspraak"
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
    afspraak = {b.naam: b.uren_per_week_afspraak for b in cfg.bellers.values() if b.uren_per_week_afspraak}
    u = (uren[uren["beller"].isin(zzp)]
         .assign(geschat=lambda x: np.where(x["beller"].isin(afspraak), x["kosten_uur"], x["uren"] * x["tarief"]))
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
        if status == "nog geen factuur" and r.beller in afspraak:
            status = f"nog geen factuur (geschat {afspraak[r.beller]:g} u/week)"
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


def _stats(st: pd.DataFrame | None, cfg: Config) -> pd.DataFrame:
    kol = ["peildatum", "agent_raw", "campagne", "project", "contactpogingen", "calls", "hits", "afgehandeld",
           "recordtijd_s", "gesprek_s", "beller", "klant"]
    if st is None or st.empty:
        return pd.DataFrame(columns=kol)
    st = st[st["peildatum"] == st["peildatum"].max()].copy()   # nieuwste stand
    st["beller"] = st["agent_raw"].map(cfg.beller_voor)
    st["klant"] = st["campagne"].map(cfg.klant_voor_campagne)
    return st


def _kalibreer(v: pd.DataFrame, stats: pd.DataFrame, rondes: int = 2000, eps: float = 0.02) -> pd.DataFrame:
    """Iterative proportional fitting per beller: de dagverdeling (uit belregels) wordt zo geschaald dat
    het totaal per klant gelijk is aan het aandeel beltijd per campagne in de Steam-contactstatistieken,
    terwijl elke dag optelt tot 100%. Startwaarde per dag = aandeel belregels, plus een klein deel (eps)
    van het Steam-aandeel, zodat ook campagnes zonder overgebleven belregels (overschreven door een latere
    poging) tijd kunnen krijgen."""
    sl = (stats.dropna(subset=["beller"]).assign(klant=lambda x: x["klant"].fillna(NIET_TOEGEREKEND))
          .groupby(["beller", "klant"])["recordtijd_s"].sum())
    uit = []
    for b, g in v.groupby("beller"):
        if b not in sl.index.get_level_values(0):
            uit.append(g)
            continue
        doel = (sl.loc[b] / sl.loc[b].sum())
        m = g.pivot_table(index="datum", columns="klant_label", values="aandeel", aggfunc="sum", fill_value=0.0)
        m = m.reindex(columns=sorted(set(m.columns) | set(doel.index)), fill_value=0.0)
        if NIET_TOEGEREKEND in m.columns and NIET_TOEGEREKEND not in doel.index:
            m = m.drop(columns=NIET_TOEGEREKEND)
        w = g.groupby("datum")["uren"].first().reindex(m.index).fillna(0).values  # uren per dag
        rij = m.sum(axis=1).replace(0, 1)
        m = m.div(rij, axis=0)
        prior = doel.reindex(m.columns).fillna(0).values
        m = m * (1 - eps) + eps * prior[None, :]
        col_doel = doel.reindex(m.columns).fillna(0).values * w.sum()
        X = m.values * w[:, None]
        for _ in range(rondes):
            cs = X.sum(axis=0)
            f = np.divide(col_doel, cs, out=np.ones_like(cs), where=cs > 0)
            X = X * f
            rs = X.sum(axis=1)
            X = X * np.divide(w, rs, out=np.zeros_like(rs), where=rs > 0)[:, None]
        aandeel = pd.DataFrame(np.divide(X, w[:, None], out=np.zeros_like(X), where=w[:, None] > 0),
                               index=m.index, columns=m.columns)
        lang = aandeel.stack().rename("aandeel").reset_index().rename(columns={"level_1": "klant_label"})
        lang = lang[lang["aandeel"] > 1e-9]
        basis = g.drop_duplicates("datum").set_index("datum")[["beller", "uren", "pogingen", "kosten"]]
        r = lang.join(basis, on="datum")
        oud = g.set_index(["datum", "klant_label"])["basis"]
        r["basis"] = [oud.get((d, k), "steam-statistiek") for d, k in zip(r["datum"], r["klant_label"])]
        r["basis"] = r["basis"].replace({"belregels": "belregels, gekalibreerd op Steam-beltijd"})
        uit.append(r)
    return pd.concat(uit, ignore_index=True)


def _verdeling(uren: pd.DataFrame, contacten: pd.DataFrame, extra: pd.DataFrame,
               stats: pd.DataFrame | None = None, kalibreren: bool = True,
               pogingen: pd.DataFrame | None = None) -> pd.DataFrame:
    """Verdeelsleutel: uren/kosten per beller per dag naar rato van contactmomenten per klant.
    Dagen zonder belregels: naar rato van de beltijd per campagne uit de Steam-contactstatistieken."""
    tel = (contacten.dropna(subset=["beller"]).groupby(["datum", "beller", "klant_label"])
           .size().rename("n").reset_index())
    if pogingen is not None and len(pogingen):
        # Dagen zonder belregels: verdelen naar rato van de belpogingen per klant die dag
        pt = (pogingen.dropna(subset=["beller"]).assign(klant_label=lambda x: x["klant"].fillna(NIET_TOEGEREKEND))
              .groupby(["datum", "beller", "klant_label"]).size().rename("n").reset_index())
        al = set(zip(tel["datum"], tel["beller"]))
        pt = pt[[(d, b) not in al for d, b in zip(pt["datum"], pt["beller"])]]
        tel = pd.concat([tel, pt], ignore_index=True)
    tel["aandeel"] = tel["n"] / tel.groupby(["datum", "beller"])["n"].transform("sum")
    u = uren.dropna(subset=["beller"]).groupby(["datum", "beller"], as_index=False).agg(
        uren=("uren", "sum"), pogingen=("pogingen", "sum"), kosten=("kosten", "sum"))
    v = u.merge(tel[["datum", "beller", "klant_label", "aandeel"]], on=["datum", "beller"], how="left")
    v["basis"] = np.where(v["klant_label"].isna(), "geen belregels", "belregels")
    if stats is not None and len(stats):
        sl = (stats.dropna(subset=["beller"]).assign(klant=lambda x: x["klant"].fillna(NIET_TOEGEREKEND))
              .groupby(["beller", "klant"])["recordtijd_s"].sum())
        sl = (sl / sl.groupby(level=0).transform("sum")).rename("aandeel_s").reset_index()
        leeg = v[v["basis"] == "geen belregels"].drop(columns=["klant_label", "aandeel"])
        gevuld = leeg.merge(sl, on="beller", how="inner").rename(columns={"klant": "klant_label", "aandeel_s": "aandeel"})
        gevuld["basis"] = "steam-statistiek"
        rest = leeg[~leeg["beller"].isin(sl["beller"])].assign(klant_label=None, aandeel=1.0)
        v = pd.concat([v[v["basis"] != "geen belregels"], gevuld, rest], ignore_index=True)
    v["klant_label"] = v["klant_label"].fillna(NIET_TOEGEREKEND)
    v["aandeel"] = v["aandeel"].fillna(1.0)
    if stats is not None and len(stats) and kalibreren:
        v = _kalibreer(v, stats)
    for c in ("uren", "pogingen", "kosten"):
        v[c] = v[c] * v["aandeel"]
    v = v.rename(columns={"klant_label": "klant"})
    if not extra.empty:
        v = pd.concat([v, extra], ignore_index=True)
    return v[["datum", "beller", "klant", "aandeel", "uren", "pogingen", "kosten", "basis"]]


def _verkoop(v: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    kol = ["factuurnr", "klant_naam", "factuurdatum", "omschrijving", "werkperiode_nr", "periode_van",
           "periode_tot", "bedrag_excl", "is_lead", "klant", "bron", "periode_afgeleid", "status"]
    if v is None or v.empty:
        return pd.DataFrame(columns=kol)
    v = v.copy()
    v["klant"] = v["klant_naam"].map(cfg.klant_voor_debiteur)
    for c in ("factuurdatum", "periode_van", "periode_tot"):
        v[c] = pd.Series([x.date() if pd.notna(x) else None for x in pd.to_datetime(v[c])], index=v.index,
                         dtype=object)
    v["is_lead"] = v["is_lead"].fillna(False).astype(bool)
    if "status" not in v:
        v["status"] = None
    v["status"] = v["status"].fillna("onbekend")
    # Een klaarstaande (concept)factuur vervalt zodra de echte factuur er is:
    # zelfde klant, zelfde bedrag, factuurdatum binnen 7 dagen.
    echt = v[v["status"] != "te_versturen"]
    weg = []
    for i, r in v[v["status"] == "te_versturen"].iterrows():
        k = r["klant"] if pd.notna(r["klant"]) else None
        m = echt[((echt["klant"] == k) if k else (echt["klant_naam"] == r["klant_naam"]))
                 & ((echt["bedrag_excl"] - r["bedrag_excl"]).abs() < 0.01)
                 & ((pd.to_datetime(echt["factuurdatum"]) - pd.Timestamp(r["factuurdatum"])).abs().dt.days <= 7)]
        if len(m):
            weg.append(i)
    v = v.drop(index=weg)
    # Geen periode op de factuur (bv. alleen bekend uit de mail): 28 dagen vanaf de factuurdatum.
    zonder = v["periode_van"].isna()
    v["periode_afgeleid"] = zonder
    v.loc[zonder, "periode_van"] = v.loc[zonder, "factuurdatum"]
    v.loc[zonder, "periode_tot"] = [d + dt.timedelta(days=27) for d in v.loc[zonder, "factuurdatum"]]
    return v.sort_values(["klant_naam", "factuurdatum"]).reset_index(drop=True)


def _start_uit_factuur(klant: str, verkoop: pd.DataFrame):
    v = verkoop[(verkoop["klant"] == klant) & verkoop["werkperiode_nr"].notna() & ~verkoop["periode_afgeleid"]]
    if v.empty:
        return None
    r = v.iloc[0]
    return r.periode_van - dt.timedelta(days=28 * (int(r.werkperiode_nr) - 1))


def _startdatum(klant, contacten, verkoop=None) -> tuple[dt.date | None, str]:
    if klant.belstart:
        return klant.belstart, "config"
    if verkoop is not None and len(verkoop):
        s = _start_uit_factuur(klant.naam, verkoop)
        if s:
            return s, "verkoopfactuur"
    eigen = contacten[contacten["klant"] == klant.naam]
    if not eigen.empty:
        return eigen["datum"].min(), "eerste belregel"
    return None, "ontbreekt"


def _opbrengst(cfg: Config, contacten: pd.DataFrame, peildatum: dt.date, verkoop: pd.DataFrame) -> pd.DataFrame:
    """Per dag: gefactureerd (verkoopfactuur, verdeeld over de periode) of geschat (fee / 28)."""
    rijen = []
    for k in cfg.klanten.values():
        eigen = verkoop[(verkoop["klant"] == k.naam) & ~verkoop["is_lead"]]
        gedekt = set()
        for r in eigen.itertuples():
            if pd.notna(r.periode_van) and pd.notna(r.periode_tot):
                dagen = pd.date_range(r.periode_van, r.periode_tot).date
                for d in dagen:
                    gedekt.add(d)
                    if d <= peildatum:
                        rijen.append({"datum": d, "klant": k.naam, "fee": r.bedrag_excl / len(dagen),
                                      "leads_eur": 0.0, "leads": 0, "gefactureerd": True})
            elif r.factuurdatum <= peildatum:
                rijen.append({"datum": r.factuurdatum, "klant": k.naam, "fee": r.bedrag_excl, "leads_eur": 0.0,
                              "leads": 0, "gefactureerd": True})
        start, _ = _startdatum(k, contacten, verkoop)
        schatten = cfg.instellingen.get("opbrengst_basis", "facturen") != "facturen" or (
            eigen.empty and cfg.instellingen.get("schatten_zonder_enige_factuur", False))
        if schatten and k.fee_per_4wk and start and start <= peildatum:
            for d in pd.date_range(start, peildatum).date:
                if d not in gedekt:
                    rijen.append({"datum": d, "klant": k.naam, "fee": k.fee_per_4wk / 28, "leads_eur": 0.0,
                                  "leads": 0, "gefactureerd": False})
        lead_f = verkoop[(verkoop["klant"] == k.naam) & verkoop["is_lead"]]
        for r in lead_f.itertuples():
            if r.factuurdatum <= peildatum:
                rijen.append({"datum": r.factuurdatum, "klant": k.naam, "fee": 0.0, "leads_eur": r.bedrag_excl,
                              "leads": 0, "gefactureerd": True})
        if schatten and k.extra_per_lead and lead_f.empty:
            leads = contacten[(contacten["klant"] == k.naam) & (contacten["code_eff"] == k.extra_code)].groupby("datum").size()
            for d, n in leads.items():
                rijen.append({"datum": d, "klant": k.naam, "fee": 0.0,
                              "leads_eur": n * k.extra_per_lead, "leads": int(n), "gefactureerd": False})
    df = pd.DataFrame(rijen, columns=["datum", "klant", "fee", "leads_eur", "leads", "gefactureerd"])
    return df.groupby(["datum", "klant", "gefactureerd"], as_index=False).sum()


def _overig(cfg: Config, peildatum: dt.date, eerste: dt.date) -> pd.DataFrame:
    """Overige kosten per dag per kostenpost.
    Maanden met een factuur (config/kosten.yaml): het factuurbedrag excl. btw, over de maand verdeeld.
    Maanden zonder factuur: het vaste maandbedrag uit instellingen.yaml, of anders het laatst
    bekende factuurbedrag van die post (geschat)."""
    kol = ["datum", "post", "bedrag", "basis"]
    van = cfg.instellingen.get("overige_kosten_vanaf") or eerste
    vast = {p: b for p, b in (cfg.instellingen.get("overige_kosten_per_maand") or {}).items()}
    alle = cfg.kosten
    rijen = []
    # Facturen met een periode (jaarlicentie, abonnement): per dag over de periode.
    for f in [f for f in alle if f.get("periode_van") and f.get("periode_tot")]:
        n = (f["periode_tot"] - f["periode_van"]).days + 1
        for d in pd.date_range(max(f["periode_van"], van), min(f["periode_tot"], peildatum)).date:
            rijen.append({"datum": d, "post": f["post"], "bedrag": f["bedrag_excl"] / n, "basis": "factuur"})
    met_periode = {f["post"] for f in alle if f.get("periode_van")}
    facturen = [f for f in alle if not f.get("periode_van")]
    niet_doorschatten = {f["post"] for f in alle if f.get("doorschatten") is False} | met_periode
    posten = sorted((set(vast) | {f["post"] for f in facturen}) - met_periode)
    m = dt.date(van.year, van.month, 1)
    while m <= peildatum:
        dim = _dagen_in_maand(m)
        laatste = min(dt.date(m.year, m.month, dim), peildatum)
        for post in posten:
            deze = [f for f in facturen if f["post"] == post and f["maand"] == (m.year, m.month)]
            eerder = sorted([f for f in facturen if f["post"] == post and f["maand"] < (m.year, m.month)],
                            key=lambda f: f["maand"])
            if deze:
                bedrag, basis = sum(f["bedrag_excl"] for f in deze), "factuur"
            elif vast.get(post):
                bedrag, basis = vast[post], "vast bedrag (config)"
            elif eerder and cfg.instellingen.get("kosten_doorschatten", True) and post not in niet_doorschatten:
                bedrag, basis = eerder[-1]["bedrag_excl"], "geschat (laatste factuur)"
            else:
                continue
            for d in range(max(1, van.day if m == dt.date(van.year, van.month, 1) else 1), laatste.day + 1):
                rijen.append({"datum": dt.date(m.year, m.month, d), "post": post, "bedrag": bedrag / dim,
                              "basis": basis})
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return pd.DataFrame(rijen, columns=kol)


def _kosten_overzicht(overig: pd.DataFrame) -> list:
    if overig.empty:
        return []
    o = overig.assign(maand=pd.to_datetime(overig["datum"]).dt.strftime("%Y-%m"))
    g = o.groupby(["post", "maand", "basis"], as_index=False)["bedrag"].sum()
    return [{"post": r.post, "maand": r.maand, "bedrag_excl": round(r.bedrag, 2), "basis": r.basis}
            for r in g.sort_values(["post", "maand"]).itertuples()]


def klant_perioden(cfg: Config, contacten: pd.DataFrame, verkoop: pd.DataFrame, peildatum: dt.date) -> dict:
    """Werkperiodes per opdrachtgever: blokken van 28 dagen vanaf de startdatum (config, factuur of eerste
    belregel) t/m de periode waarin de peildatum valt. Een pilot is één periode van zijn looptijd."""
    uit = {}
    for k in cfg.klanten.values():
        start, bron = _startdatum(k, contacten, verkoop)
        if not start:
            continue
        if k.pilot_weken:
            uit[k.naam] = [{"nr": 1, "van": start, "tot": start + dt.timedelta(days=7 * int(k.pilot_weken) - 1),
                            "label": f"Pilot {k.pilot_weken} weken"}]
            continue
        p, nr, lijst = start, 1, []
        eind = max(peildatum, start)
        while p <= eind:
            t = p + dt.timedelta(days=27)
            lijst.append({"nr": nr, "van": p, "tot": t, "label": f"WP {nr}"})
            p, nr = t + dt.timedelta(days=1), nr + 1
        uit[k.naam] = lijst
    return uit


def _targets(cfg: Config, contacten: pd.DataFrame, peildatum: dt.date, verkoop: pd.DataFrame) -> pd.DataFrame:
    groen = cfg.instellingen.get("stoplicht_groen", 1.0)
    oranje = cfg.instellingen.get("stoplicht_oranje", 0.8)
    rijen = []
    for k in cfg.klanten.values():
        start, bron = _startdatum(k, contacten, verkoop)
        r = {"klant": k.naam, "target": k.target_per_4wk, "start": start, "start_bron": bron,
             "telt_als": "+".join(map(str, k.telt_als_resultaat)), "status": k.status}
        eigen = contacten[(contacten["klant"] == k.naam) & contacten["is_resultaat"]]
        fp = verkoop[(verkoop["klant"] == k.naam) & ~verkoop["periode_afgeleid"]]
        fp = fp[(fp["periode_van"] <= peildatum) & (fp["periode_tot"] >= peildatum)]
        if start and start <= peildatum:
            nr = (peildatum - start).days // 28
            p_van = start + dt.timedelta(days=28 * nr)
            p_tot = p_van + dt.timedelta(days=27)
            r["periode_bron"] = "berekend"
            if k.pilot_weken:
                nr, p_van = 0, start
                p_tot = start + dt.timedelta(days=7 * int(k.pilot_weken) - 1)
                r["periode_bron"] = f"pilot {k.pilot_weken} weken"
                r["target"] = k.pilot_target
            elif len(fp):
                p_van, p_tot = fp.iloc[0].periode_van, fp.iloc[0].periode_tot
                if pd.notna(fp.iloc[0].werkperiode_nr):
                    nr = int(fp.iloc[0].werkperiode_nr) - 1
                r["periode_bron"] = f"factuur {fp.iloc[0].factuurnr}"
            res = int(((eigen["datum"] >= p_van) & (eigen["datum"] <= p_tot)).sum())
            verstreken = werkdagen(p_van, peildatum)
            totaal = werkdagen(p_van, p_tot)
            rest = werkdagen(peildatum + dt.timedelta(days=1), p_tot)
            prognose = res / verstreken * totaal if verstreken else None
            r.update(periode_nr=nr + 1, periode_van=p_van, periode_tot=p_tot, resultaten=res,
                     werkdagen_verstreken=verstreken, werkdagen_rest=rest, prognose=prognose)
            if k.targets_per_code and verstreken:
                in_p = contacten[(contacten["klant"] == k.naam) & (contacten["datum"] >= p_van) & (contacten["datum"] <= p_tot)]
                delen, ratios = [], []
                for code, t in sorted(k.targets_per_code.items()):
                    n = int(((in_p["code_eff"] == code) & in_p["is_resultaat"]).sum())
                    prog = n / verstreken * totaal
                    delen.append(f"{code}: {n} van {t:g} (prognose {prog:.1f})")
                    ratios.append(prog / t if t else 1)
                r["detail"] = " · ".join(delen)
            if not k.actief:
                r["stoplicht"] = k.status
            elif k.targets_per_code and verstreken:
                ratio = min(ratios)
                r["stoplicht"] = "groen" if ratio >= groen else "oranje" if ratio >= oranje else "rood"
                rest_nodig = sum(max(0, t - int(((in_p["code_eff"] == c) & in_p["is_resultaat"]).sum()))
                                 for c, t in k.targets_per_code.items())
                r["benodigd_per_werkdag"] = rest_nodig / rest if rest else None
            elif r.get("target") or k.target_per_4wk:
                doel = r.get("target") or k.target_per_4wk
                ratio = (prognose or 0) / doel
                r["stoplicht"] = "groen" if ratio >= groen else "oranje" if ratio >= oranje else "rood"
                r["benodigd_per_werkdag"] = (max(0, doel - res) / rest) if rest else None
            else:
                r["stoplicht"] = "geen target"
        else:
            if k.pilot_weken and start:
                r.update(periode_van=start, periode_tot=start + dt.timedelta(days=7 * int(k.pilot_weken) - 1),
                         periode_bron=f"pilot {k.pilot_weken} weken", target=k.pilot_target)
            r.update(stoplicht=(k.status if not k.actief else "nog niet gestart" if start
                                else "startdatum ontbreekt"), resultaten=int(len(eigen)))
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

    # Somcontroles (uren buiten Steam tellen apart)
    totaal_model = verdeling["uren"].sum()
    extra_uren = uren.loc[uren.get("bron", pd.Series("urenexport", index=uren.index)) == "uren_buiten_steam", "uren"].sum()
    dq["controles"] = [
        {"controle": "Betaalde uren: dashboard = som urenexport",
         "dashboard": round(totaal_model - extra_uren, 2), "bron": round(ruwe_uren_s / 3600, 2),
         "ok": bool(abs(totaal_model - extra_uren - ruwe_uren_s / 3600) < 0.01)},
    ]
    return dq


def _dq_verkoop(cfg, verkoop, contacten, peildatum, opbrengst) -> dict:
    dq = {}
    dq["verkoopfacturen"] = [
        {"factuurnr": r.factuurnr, "debiteur": r.klant_naam, "klant": r.klant or "niet gekoppeld",
         "factuurdatum": str(r.factuurdatum), "werkperiode": int(r.werkperiode_nr) if pd.notna(r.werkperiode_nr) else None,
         "periode": f"{r.periode_van} t/m {r.periode_tot}" + (" (aangenomen)" if r.periode_afgeleid else ""),
         "bedrag_excl": r.bedrag_excl, "bron": r.bron, "status": r.status}
        for r in verkoop.itertuples()]
    verstuurd = verkoop[verkoop["status"] != "te_versturen"]
    per = {k: g for k, g in verstuurd.assign(k=verstuurd["klant"].fillna(verstuurd["klant_naam"])).groupby("k")}
    dq["verkoop_per_klant"] = []
    for k in sorted(set(per) | {kl.naam for kl in cfg.klanten.values() if kl.omzet_boekhouding}):
        g = per.get(k, verkoop.iloc[0:0])
        kl = cfg.klanten.get(k)
        tot = round(g["bedrag_excl"].sum(), 2)
        bk = kl.omzet_boekhouding if kl else None
        dq["verkoop_per_klant"].append({
            "debiteur": k, "facturen": len(g), "totaal_excl": tot,
            "boekhouding": bk, "verschil": round(bk - tot, 2) if bk is not None else None,
            "eerste": str(g["factuurdatum"].min()) if len(g) else "-",
            "laatste": str(g["factuurdatum"].max()) if len(g) else "-",
            "klant": (g["klant"].iloc[0] if len(g) else k) or "niet gekoppeld"})
    # Verstreken werkperiodes zonder verkoopfactuur (mogelijk niet gefactureerd)
    zonder = []
    verschil = []
    for k in cfg.klanten.values():
        start, bron = _startdatum(k, contacten, verkoop)
        if not (start and k.fee_per_4wk) or start > peildatum or not k.actief:
            continue
        eigen = verkoop[(verkoop["klant"] == k.naam) & verkoop["periode_van"].notna()]
        p = start
        nr = 1
        while p <= peildatum:
            t = p + dt.timedelta(days=27)
            if eigen[(eigen["periode_van"] <= t) & (eigen["periode_tot"] >= p)].empty:
                zonder.append({"klant": k.naam, "werkperiode": nr, "van": str(p), "tot": str(t),
                               "verwacht_bedrag": k.fee_per_4wk, "start_volgens": bron})
            p, nr = t + dt.timedelta(days=1), nr + 1
        for r in eigen[eigen["status"] != "te_versturen"].itertuples():
            if abs(r.bedrag_excl - k.fee_per_4wk) > 0.01:
                verschil.append({"klant": k.naam, "factuurnr": r.factuurnr, "factuurbedrag": r.bedrag_excl,
                                 "fee_in_config": k.fee_per_4wk})
    dq["werkperiodes_zonder_verkoopfactuur"] = zonder
    # Debiteuren: openstaand, vervallen en klaarstaand om te versturen (bedragen incl. btw zoals in de boekhouding)
    deb = []
    for k, g in verkoop[verkoop["status"].isin(["open", "vervallen", "te_versturen"])].assign(
            k=lambda x: x["klant"].fillna(x["klant_naam"])).groupby("k"):
        r = {"klant": k}
        for st in ("open", "vervallen", "te_versturen"):
            r[st] = round(g.loc[g["status"] == st, "bedrag_excl"].sum() * 1.21, 2)
        r["facturen"] = ", ".join(f"{f} ({s})" for f, s in zip(g["factuurnr"], g["status"]) if not str(f).startswith("concept"))
        deb.append(r)
    dq["debiteuren"] = deb
    # Mogelijke dubbele facturen: zelfde klant, zelfde bedrag, binnen 7 dagen, ander nummer
    dub = []
    w = verkoop[verkoop["bedrag_excl"] > 0].assign(k=lambda x: x["klant"].fillna(x["klant_naam"]))
    for k, g in w.groupby("k"):
        g = g.sort_values("factuurdatum")
        rows = list(g.itertuples())
        for a, b in zip(rows, rows[1:]):
            if abs(a.bedrag_excl - b.bedrag_excl) < 0.01 and (b.factuurdatum - a.factuurdatum).days <= 7 \
                    and a.factuurnr != b.factuurnr:
                dub.append({"klant": k, "factuur_1": a.factuurnr, "factuur_2": b.factuurnr,
                            "datum_1": str(a.factuurdatum), "datum_2": str(b.factuurdatum), "bedrag_excl": a.bedrag_excl})
    dq["mogelijk_dubbel"] = dub
    dq["fee_afwijkingen"] = verschil
    totaal_gef = opbrengst.loc[opbrengst["gefactureerd"].astype(bool), ["fee", "leads_eur"]].sum().sum()
    verwacht = 0.0
    for r in verkoop[verkoop["klant"].notna()].itertuples():
        if pd.notna(r.periode_van):
            n = (r.periode_tot - r.periode_van).days + 1
            binnen = max(0, (min(r.periode_tot, peildatum) - r.periode_van).days + 1)
            verwacht += r.bedrag_excl * binnen / n
        elif r.factuurdatum <= peildatum:
            verwacht += r.bedrag_excl
    dq["verkoop_controle"] = {"controle": "Opbrengst: gefactureerd in model = verkoopfacturen t/m peildatum (naar rato)",
                              "dashboard": round(totaal_gef, 2), "bron": round(verwacht, 2),
                              "ok": bool(abs(totaal_gef - verwacht) < 0.01)}
    dq["vooruitgefactureerd"] = round(verkoop["bedrag_excl"].sum() - verwacht, 2) if len(verkoop) else 0
    return dq


def _pogingen(p: pd.DataFrame | None, cfg: Config) -> pd.DataFrame:
    if p is None or p.empty:
        return pd.DataFrame(columns=["datum", "uur", "beller", "klant", "verbonden", "agent_raw", "campagne"])
    p = p.copy()
    p["beller"] = p["agent_raw"].map(cfg.beller_voor)
    p["klant"] = p["campagne"].map(cfg.klant_voor_campagne)
    # Steam levert deze export in UTC; omrekenen naar lokale tijd.
    bron_tz = cfg.instellingen.get("belpogingen_tijdzone", "UTC")
    lokaal = (pd.to_datetime(p["poging_dt"]).dt.tz_localize(bron_tz)
              .dt.tz_convert(cfg.instellingen.get("tijdzone", "Europe/Amsterdam")).dt.tz_localize(None))
    p["poging_dt"] = lokaal.astype(str)
    p["datum"] = lokaal.dt.date
    p["uur"] = lokaal.dt.hour
    p["verbonden"] = p["verbonden"].astype(bool)
    return p


def _werkdagen(sessies: pd.DataFrame | None, pogingen: pd.DataFrame, cfg: Config,
               laat_uur: int = 20) -> pd.DataFrame:
    """Werkdag per beller per dag uit de agent-sessies: van de eerste inlog tot de laatste uitlog.
    Een uitlog na laat_uur of op een andere dag (niet uitgelogd, automatisch uitgelogd) wordt vervangen
    door het tijdstip van de laatste belpoging die dag."""
    kol = ["datum", "beller", "start", "eind", "eind_bron"]
    if sessies is None or sessies.empty:
        return pd.DataFrame(columns=kol)
    s = sessies.copy()
    s = s[s["functie"].fillna("Agent").str.lower() == "agent"]
    s["beller"] = s["agent_raw"].map(cfg.beller_voor)
    s = s.dropna(subset=["beller"])
    s["in"] = pd.to_datetime(s["ingelogd"])
    s["uit"] = pd.to_datetime(s["uitgelogd"])
    s["datum"] = s["in"].dt.date
    if len(pogingen) and "poging_dt" in pogingen:
        laatste = pogingen.assign(t=pd.to_datetime(pogingen["poging_dt"])).groupby(["beller", "datum"])["t"].max()
    else:
        laatste = pd.Series(dtype="datetime64[ns]")
    uur = lambda t: t.hour + t.minute / 60 + t.second / 3600
    rijen = []
    for (b, d), g in s.groupby(["beller", "datum"]):
        start = g["in"].min()
        geldig = g["uit"][(g["uit"].notna()) & (g["uit"].dt.date == d) & (g["uit"].dt.hour < laat_uur)]
        eind, bron = (geldig.max(), "uitlog") if len(geldig) else (pd.NaT, None)
        lp = laatste.get((b, d))
        twijfel = g["uit"].isna().any() or ((g["uit"].dt.date != d) | (g["uit"].dt.hour >= laat_uur)).any()
        if lp is not None and pd.notna(lp) and (pd.isna(eind) or (twijfel and lp > eind)):
            eind, bron = lp, "laatste belpoging"
        if pd.isna(eind) or eind <= start:
            continue
        rijen.append({"datum": d, "beller": b, "start": round(uur(start), 3), "eind": round(uur(eind), 3),
                      "eind_bron": bron})
    return pd.DataFrame(rijen, columns=kol)


def _campagnerapport(cr: pd.DataFrame | None, cfg: Config, contacten, verdeling, overig) -> list:
    """Per opdrachtgever: alle pogingen en resultaten uit het Steam-rapport Contactresultaten, voorraad van
    de bellijst, en kosten per resultaat over dezelfde (hele) periode."""
    if cr is None or cr.empty:
        return []
    cr = cr[cr["exportdatum"] == cr.groupby("campagne")["exportdatum"].transform("max")].copy()
    cr["klant"] = cr["campagne"].map(cfg.klant_voor_campagne)
    kost = verdeling.groupby("klant")["kosten"].sum()
    ov = overig["bedrag"].sum() if len(overig) else 0
    ov_k = kost / kost.sum() * ov if kost.sum() else kost * 0
    rijen = []
    for camp, g in cr.groupby("campagne"):
        k = g["klant"].iloc[0]
        kl = cfg.klanten.get(k)
        telt = set(kl.telt_als_resultaat) if kl else {100, 101}
        n = lambda cs: int(g.loc[g["code"].isin(cs), "aantal"].sum())
        pog = int(g["contactpogingen"].iloc[0])
        res = n(telt)
        dash = int(contacten[(contacten["klant"] == k) & contacten["is_resultaat"]].shape[0])
        kosten = float(kost.get(k, 0) + ov_k.get(k, 0)) if k else 0.0
        rijen.append({
            "klant": k or camp, "status": kl.status if kl else "onbekend", "campagne": camp,
            "periode": f"{g['periode_van'].iloc[0]} t/m {g['periode_tot'].iloc[0]}", "agentfilter": g["agentfilter"].iloc[0],
            "adressen": int(g["adressen"].iloc[0]), "onaangeraakt": int(g["onaangeraakt"].iloc[0]),
            "niet_afgehandeld": int(g["niet_afgehandeld"].iloc[0]), "pogingen": pog,
            "bereikt": n(codes.BEREIKT), "afspraken_100": n([100]), "overdrachten_101": n([101]),
            "resultaten_steam": res, "resultaten_dashboard": dash, "data_fout": n([300]),
            "kosten": round(kosten, 2), "kosten_per_resultaat": round(kosten / res, 2) if res else None})
    return sorted(rijen, key=lambda r: (r["status"] != "actief", r["klant"]))


def _dq_stats(stats, contacten, uren, verdeling) -> dict:
    if stats is None or stats.empty:
        return {"stats_peildatum": None, "stats_controle": []}
    peil = stats["peildatum"].iloc[0]
    tot = stats.groupby("beller")[["contactpogingen", "hits"]].sum()
    u = uren.groupby("beller")["pogingen"].sum()
    r = contacten[contacten["is_resultaat"]].groupby("beller").size()
    rijen = [{"beller": b, "contactpogingen_steam": int(t.contactpogingen), "pogingen_urenexport": int(u.get(b, 0)),
              "hits_steam": int(t.hits), "resultaten_dashboard": int(r.get(b, 0))} for b, t in tot.iterrows()]
    # beltijd per klant (Steam) tegenover uren in de verdeelsleutel
    sk = stats.assign(klant=stats["klant"].fillna("?")).groupby("klant")["recordtijd_s"].sum() / 3600
    vk = verdeling.groupby("klant")["uren"].sum()
    tijd = [{"klant": k, "beltijd_steam_uur": round(sk.get(k, 0), 1), "uren_verdeelsleutel": round(vk.get(k, 0), 1)}
            for k in sorted(set(sk.index) | set(vk.index))]
    return {"stats_peildatum": peil, "stats_controle": rijen, "stats_tijd_per_klant": tijd,
            "stats_niet_gekoppeld": sorted(stats.loc[stats["klant"].isna(), "campagne"].unique().tolist())}


# ---------------------------------------------------------------- publiek

def bouw(cfg: Config, contacten_raw: pd.DataFrame, uren_raw: pd.DataFrame,
         bestanden: pd.DataFrame | None = None, facturen_raw: pd.DataFrame | None = None,
         verkoop_raw: pd.DataFrame | None = None, stats_raw: pd.DataFrame | None = None,
         campagne_raw: pd.DataFrame | None = None, pogingen_raw: pd.DataFrame | None = None,
         sessies_raw: pd.DataFrame | None = None) -> Model:
    contacten = _contacten(contacten_raw, cfg)
    uren = _uren(uren_raw, cfg)
    pogingen = _pogingen(pogingen_raw, cfg)
    uren = _uren_buiten_steam(uren, pogingen, cfg)
    facturen = _facturen(facturen_raw if facturen_raw is not None else pd.DataFrame(), cfg)
    verkoop = _verkoop(verkoop_raw, cfg)
    stats = _stats(stats_raw, cfg)
    extra_f = _pas_facturen_toe(uren, facturen, cfg)
    # Peildatum = laatste dag met uren: kosten en opbrengst lopen dan over dezelfde periode.
    if len(uren):
        peildatum = uren["datum"].max()
    elif len(contacten):
        peildatum = contacten["datum"].max()
    else:
        peildatum = dt.date.today()
    # Eén peildatum voor alles: belregels en belpogingen van na de laatste urendag tellen pas mee
    # zodra de urenexport die dagen ook bevat (anders resultaten zonder kosten in dezelfde week).
    na = {"peildatum": peildatum.isoformat(), "bronnen": {}, "resultaten": {}, "belregels": 0}
    if len(uren):
        laat = contacten[contacten["datum"] > peildatum]
        na["belregels"] = int(len(laat))
        na["resultaten"] = {str(k): int(v) for k, v in laat[laat["is_resultaat"]].groupby("klant_label").size().items()}
        for naam, df in (("belexport", contacten), ("belpogingen", pogingen)):
            if len(df) and df["datum"].max() > peildatum:
                na["bronnen"][naam] = df["datum"].max().isoformat()
        contacten = contacten[contacten["datum"] <= peildatum].copy()
        if len(pogingen):
            pogingen = pogingen[pogingen["datum"] <= peildatum].copy()
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

    verdeling = _verdeling(uren, contacten, extra, stats,
                           cfg.instellingen.get("verdeelsleutel", "steam_gekalibreerd") == "steam_gekalibreerd",
                           pogingen)
    opbrengst = _opbrengst(cfg, contacten, peildatum, verkoop)
    overig = _overig(cfg, peildatum, eerste)
    targets = _targets(cfg, contacten, peildatum, verkoop)
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
    mc = contacten[contacten["code_reden"] != ""]
    dq["memo_classificatie"] = [{"klant": r.klant, "datum": str(r.datum), "beller": r.beller, "code_steam": int(r.code),
                                 "telt_als": "afspraak" if r.code_eff == 100 else "lead", "reden": r.code_reden}
                                for r in mc.sort_values("datum").itertuples()]
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
    dq.update(_dq_verkoop(cfg, verkoop, contacten, peildatum, opbrengst))
    dq["klant_perioden"] = {k: [{**p, "van": str(p["van"]), "tot": str(p["tot"])} for p in v]
                            for k, v in klant_perioden(cfg, contacten, verkoop, peildatum).items()}
    if len(verkoop):
        dq["controles"].append(dq["verkoop_controle"])
    dq["kostenposten"] = _kosten_overzicht(overig)
    dq.update(_dq_stats(stats, contacten, uren, verdeling))
    dq["campagnerapport"] = _campagnerapport(campagne_raw, cfg, contacten, verdeling, overig)
    if len(pogingen):
        bekend = {r["agent"] for r in dq["niet_gekoppelde_agents"]}
        for a, g in pogingen[pogingen["beller"].isna()].groupby("agent_raw"):
            if a not in bekend:
                dq["niet_gekoppelde_agents"].append({"agent": a, "bron": "belpogingen", "rijen": len(g)})
    werkdagen_ = _werkdagen(sessies_raw, pogingen, cfg)
    if len(werkdagen_):
        werkdagen_ = werkdagen_[pd.to_datetime(werkdagen_["datum"]).dt.date <= peildatum]
    dq["na_peildatum"] = na
    dq["werkdag_bron"] = "in- en uitlogtijden" if len(werkdagen_) else "eerste en laatste belpoging"
    dq["pogingen_dekking"] = [
        {"klant": k, "pogingen": len(g), "van": str(g["datum"].min()), "tot": str(g["datum"].max()),
         "bellers": ", ".join(sorted(g["beller"].fillna(g["agent_raw"]).unique()))}
        for k, g in pogingen.assign(k=pogingen["klant"].fillna(pogingen["campagne"])).groupby("k")] if len(pogingen) else []
    return Model(contacten, uren, facturen, verdeling, opbrengst, overig, targets, peildatum, dq, verkoop, stats,
                 pogingen, werkdagen_)


def resultaten_per_klant(model: Model) -> pd.Series:
    c = model.contacten
    return c[c["is_resultaat"]].groupby("klant_label").size()

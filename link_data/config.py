"""Leest config/*.yaml. Dit is de enige plek waar configuratie wordt ingelezen."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

STANDAARD_RESULTAAT = [100, 101]


def _datum(v):
    if v in (None, ""):
        return None
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v))


@dataclass
class Klant:
    naam: str
    pids: list
    fee_per_4wk: float | None
    extra_per_lead: float | None
    target_per_4wk: float | None
    deliverable: str | None
    telt_als_resultaat: list
    belstart: dt.date | None
    factuur_namen: list = field(default_factory=list)
    status: str = "actief"

    @property
    def actief(self) -> bool:
        return self.status == "actief"

    def herkent(self, debiteur: str) -> bool:
        """Hoort een naam op een verkoopfactuur bij deze klant? Expliciete namen, anders de
        klantnaam (zonder toevoeging tussen haakjes) als begin van de debiteurnaam."""
        norm = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower())
        d = norm(debiteur)
        if d in [norm(n) for n in self.factuur_namen]:
            return True
        kern = norm(self.naam.split("(")[0])
        return bool(kern) and d.startswith(kern)


@dataclass
class Beller:
    naam: str
    aliassen: list
    type: str
    tarief_nu: float | None
    tarief_nieuw: float | None
    ingang_nieuw: dt.date | None
    actief: bool = True
    vertrokken_per: dt.date | None = None
    vaste_vergoeding_per_maand: float | None = None
    vaste_vergoeding_vanaf: dt.date | None = None
    factuur_afzenders: list = field(default_factory=list)
    uren_per_week_afspraak: float | None = None

    def tarief_op(self, datum: dt.date) -> float | None:
        if self.ingang_nieuw and datum >= self.ingang_nieuw:
            return self.tarief_nieuw
        return self.tarief_nu


@dataclass
class Config:
    klanten: dict
    bellers: dict
    instellingen: dict
    ontbrekend: list = field(default_factory=list)  # (onderwerp, veld)
    kosten: list = field(default_factory=list)       # facturen overige kosten (kosten.yaml)

    @property
    def pid_naar_klant(self) -> dict:
        return {int(p): k.naam for k in self.klanten.values() for p in k.pids}

    @property
    def alias_naar_beller(self) -> dict:
        m = {}
        for b in self.bellers.values():
            m[b.naam.strip().lower()] = b.naam
            for a in b.aliassen:
                m[str(a).strip().lower()] = b.naam
        return m

    def beller_voor_afzender(self, afzender) -> str | None:
        if not afzender:
            return None
        a = str(afzender).strip().lower()
        for b in self.bellers.values():
            if a in [x.strip().lower() for x in b.factuur_afzenders]:
                return b.naam
        return self.beller_voor(afzender)

    def klant_voor_debiteur(self, naam) -> str | None:
        treffers = [k.naam for k in self.klanten.values() if k.herkent(naam)]
        return treffers[0] if len(treffers) == 1 else None

    def beller_voor(self, agent_raw) -> str | None:
        if agent_raw is None:
            return None
        return self.alias_naar_beller.get(str(agent_raw).strip().lower())


def laad(config_dir: Path | str = CONFIG_DIR) -> Config:
    config_dir = Path(config_dir)
    rk = yaml.safe_load((config_dir / "klanten.yaml").read_text(encoding="utf-8"))["klanten"]
    rb = yaml.safe_load((config_dir / "bellers.yaml").read_text(encoding="utf-8"))["bellers"]
    inst = yaml.safe_load((config_dir / "instellingen.yaml").read_text(encoding="utf-8")) or {}
    ontbrekend = []

    klanten = {}
    for naam, v in rk.items():
        v = v or {}
        actief = str(v.get("status") or "actief").lower() == "actief"
        for veld in (("fee_per_4wk", "extra_per_lead", "target_per_4wk", "deliverable", "belstart") if actief else ()):
            if v.get(veld) is None:
                ontbrekend.append((f"Klant: {naam}", veld))
        if not v.get("pids") and actief:
            ontbrekend.append((f"Klant: {naam}", "pids"))
        telt = v.get("telt_als_resultaat") or STANDAARD_RESULTAAT
        klanten[naam] = Klant(
            naam=naam,
            pids=[int(p) for p in (v.get("pids") or [])],
            fee_per_4wk=v.get("fee_per_4wk"),
            extra_per_lead=v.get("extra_per_lead"),
            target_per_4wk=v.get("target_per_4wk"),
            deliverable=v.get("deliverable"),
            telt_als_resultaat=[int(c) for c in telt],
            belstart=_datum(v.get("belstart")),
            factuur_namen=list(v.get("factuur_namen") or []),
            status=str(v.get("status") or "actief").lower(),
        )

    bellers = {}
    for naam, v in rb.items():
        v = v or {}
        if not v.get("aliassen") and v.get("actief", True):
            ontbrekend.append((f"Beller: {naam}", "aliassen"))
        for veld in ("tarief_nu", "tarief_nieuw"):
            if v.get(veld) is None:
                ontbrekend.append((f"Beller: {naam}", veld))
        bellers[naam] = Beller(
            naam=naam,
            aliassen=list(v.get("aliassen") or []),
            type=v.get("type") or "ZZP",
            tarief_nu=v.get("tarief_nu"),
            tarief_nieuw=v.get("tarief_nieuw"),
            ingang_nieuw=_datum(v.get("ingang_nieuw")),
            actief=v.get("actief", True),
            vertrokken_per=_datum(v.get("vertrokken_per")),
            vaste_vergoeding_per_maand=v.get("vaste_vergoeding_per_maand"),
            vaste_vergoeding_vanaf=_datum(v.get("vaste_vergoeding_vanaf")),
            factuur_afzenders=list(v.get("factuur_afzenders") or []),
            uren_per_week_afspraak=v.get("uren_per_week_afspraak"),
        )

    for post, bedrag in (inst.get("overige_kosten_per_maand") or {}).items():
        if bedrag is None:
            ontbrekend.append(("Overige kosten", post))
    # (posten met facturen in kosten.yaml worden hieronder weer uit 'ontbrekend' gehaald)

    kosten = []
    kp = config_dir / "kosten.yaml"
    if kp.exists():
        for f in (yaml.safe_load(kp.read_text(encoding="utf-8")) or {}).get("facturen") or []:
            d = _datum(f.get("datum"))
            bedrag = float(f["bedrag"])
            if str(f.get("valuta", "EUR")).upper() == "USD":
                bedrag *= float(inst.get("wisselkoers_usd_eur") or 1)
            btw = f.get("btw_pct", 21) if f.get("incl_btw") else 0
            maand = _datum(f.get("maand")) if f.get("maand") else d
            kosten.append({**f, "datum": d, "maand": (maand.year, maand.month),
                           "periode_van": _datum(f.get("periode_van")), "periode_tot": _datum(f.get("periode_tot")),
                           "bedrag_excl": round(bedrag / (1 + btw / 100), 2)})

    met_factuur = {f["post"] for f in kosten}
    ontbrekend = [(o, v) for o, v in ontbrekend if not (o == "Overige kosten" and v in met_factuur)]
    inst["werkperiode_anker"] = _datum(inst.get("werkperiode_anker")) or dt.date(2026, 8, 3)
    inst["overige_kosten_vanaf"] = _datum(inst.get("overige_kosten_vanaf"))
    return Config(klanten=klanten, bellers=bellers, instellingen=inst, ontbrekend=ontbrekend, kosten=kosten)

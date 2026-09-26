#!/usr/bin/env python3
"""Leest de Steam Connect belexport van Moyee Coffee en schrijft content/moyee-stats.json.

Die JSON is de enige bron voor de cijfers in content/moyee.json (de deck) en in
build/moyee-brew.html (de webpresentatie). Eén export erin, overal dezelfde cijfers.

    python3 build/analyse-moyee.py <export.xls>
"""
import sys, json, datetime, collections
from pathlib import Path

SKILL = '/root/.claude/skills/synced/ea5fa97d-cac5-44ce-9425-11301012d2d0_6104e3c7-5338-4cb2-a56c-1efc3ce42e69/link-rapportage/scripts'
sys.path.insert(0, SKILL)
import funnel  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# resultaatcodes
AFSPRAAK, OVERDRACHT = 100, 101
LEAD = [100, 101]
GESPROKEN = [100, 101, 200, 201, 202, 500]
PIJPLIJN = [500, 501, 502]

# Een beldag is een dag waarop echt een blok gebeld is. Dagen met een handvol
# opvolgpogingen tellen niet mee als beldag, maar de leads eruit tellen wel mee.
VOLLE_BELDAG = 30

# Norm die we in het voorstel hanteren: wat we per verkochte beldag minimaal doen.
# Het historische gemiddelde op een volle beldag is 87 pogingen, de beste dagen
# zaten rond de 100 tot 180. Een verkochte beldag is er een van minimaal 100, en
# dat is precies wat het nieuwe model voor Moyee gelijk of gunstiger maakt.
NORM_POGINGEN_PER_BELDAG = 100

# Tastings die onder resultaatcode 101 (overdracht) zijn weggeschreven, beoordeeld
# op de memo: er staat een datum of een expliciet ingeplande proeverij in.
TASTINGS_ONDER_101 = {
    'Wij Zijn MEO B.V.', 'MEO', 'DPI Consultancy B.V.', 'iPort',
    'AMS Sourcing B.V.', 'Quintel Intelligence B.V.', 'Contentoo B.V.',
}

# Wat een klant van dit formaat oplevert. Voorbeeld uit een kantoor waar we een
# tasting hebben ingepland: 300 kilo koffie per jaar, zakelijk tarief van Moyee.
KLANT_KG_PER_JAAR = 300
KLANT_OMZET_PER_JAAR = 6192.75
PERIODES_PER_JAAR = 13

NL_DAG = ['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag']


def parse_dt(x):
    d, t = str(x).split(' ', 1)
    dd, mm, yy = d.split('-')
    return datetime.date(int(yy), int(mm), int(dd)), int(t.split(':')[0])


def main(path):
    df = funnel.load(path).copy()
    df[['datum', 'uur']] = df['dt'].apply(lambda x: pd.Series(parse_dt(x)))
    df['dow'] = df['datum'].map(lambda d: d.weekday())
    df = df.sort_values('datum')

    start, eind = df['datum'].min(), df['datum'].max()
    weken = (eind - start).days / 7
    periodes = weken / 4

    pogingen = len(df)
    bedrijven = df['Bedrijf'].nunique()
    uniek = lambda codes: df[df['code'].isin(codes)]['Bedrijf'].nunique()

    gesproken = uniek(GESPROKEN)
    leads = uniek(LEAD)
    afspraken = uniek([AFSPRAAK])
    overdrachten = uniek([OVERDRACHT])

    # tastings: alle code 100 plus de beoordeelde 101-regels
    tast = df[(df['code'] == AFSPRAAK) | (df['Bedrijf'].isin(TASTINGS_ONDER_101) & (df['code'] == OVERDRACHT))]
    tastings = tast['Bedrijf'].nunique()

    perdag = df.groupby('datum').size()
    volle = perdag[perdag >= VOLLE_BELDAG]
    pog_per_beldag = float(volle.mean())

    leads_per_1000 = leads / pogingen * 1000
    tast_per_1000 = tastings / pogingen * 1000

    # open pijplijn: de laatste status per bedrijf
    laatst = df.groupby('Bedrijf').tail(1)
    status = laatst['code'].value_counts().to_dict()
    open_pijplijn = sum(status.get(c, 0) for c in PIJPLIJN)
    al_voorzien = status.get(201, 0)
    nooit_bereikt = sum(status.get(c, 0) for c in (400, 401, 402))

    # per weekdag en per dagdeel
    dagen = []
    for d in range(5):
        s = df[df['dow'] == d]
        if not len(s):
            continue
        g = len(s[s['code'].isin(GESPROKEN)])
        dagen.append({
            'dag': NL_DAG[d], 'pogingen': len(s), 'bereik': round(g / len(s) * 100, 1),
            'leads': int(s[s['code'].isin(LEAD)]['Bedrijf'].nunique()),
            'leads_per_1000': round(s[s['code'].isin(LEAD)]['Bedrijf'].nunique() / len(s) * 1000, 1),
        })

    dagdelen = []
    for lbl, lo, hi in [('ochtend', 8, 12), ('middag', 12, 15), ('eind van de middag', 15, 19)]:
        s = df[(df['uur'] >= lo) & (df['uur'] < hi)]
        if not len(s):
            continue
        g = len(s[s['code'].isin(GESPROKEN)])
        dagdelen.append({
            'deel': lbl, 'van': lo, 'tot': hi, 'pogingen': len(s),
            'bereik': round(g / len(s) * 100, 1),
            'leads_per_1000': round(s[s['code'].isin(LEAD)]['Bedrijf'].nunique() / len(s) * 1000, 1),
        })

    maanden = []
    for m, g in df.groupby(df['datum'].map(lambda d: d.strftime('%Y-%m'))):
        maanden.append({
            'maand': m, 'pogingen': len(g),
            'beldagen': int((g.groupby('datum').size() >= VOLLE_BELDAG).sum()),
            'leads': int(g[g['code'].isin(LEAD)]['Bedrijf'].nunique()),
        })

    # wat een verkochte beldag oplevert bij de norm
    leads_per_beldag = leads_per_1000 * NORM_POGINGEN_PER_BELDAG / 1000
    tast_per_beldag = tast_per_1000 * NORM_POGINGEN_PER_BELDAG / 1000

    huidig = {
        'pogingen_per_periode': round(pogingen / periodes),
        'beldagen_per_periode': round(pogingen / periodes / NORM_POGINGEN_PER_BELDAG, 1),
        'leads_per_periode': round(leads / periodes, 1),
        'tastings_per_periode': round(tastings / periodes, 1),
    }

    staffel = []
    for dagen_n, prijs in [(4, 600), (6, 550), (8, 500), (10, 500)]:
        lp = dagen_n * leads_per_beldag
        staffel.append({
            'beldagen': dagen_n, 'dagprijs': prijs, 'periode': dagen_n * prijs,
            'pogingen': dagen_n * NORM_POGINGEN_PER_BELDAG,
            'leads': round(lp, 1), 'leads_afgerond': int(lp),
            'tastings': round(dagen_n * tast_per_beldag, 1),
            'per_lead': round(dagen_n * prijs / lp),
        })

    acht = next(r for r in staffel if r['beldagen'] == 8)
    klant = {
        'kg_per_jaar': KLANT_KG_PER_JAAR,
        'omzet_per_jaar': KLANT_OMZET_PER_JAAR,
        'prijs_per_kilo': round(KLANT_OMZET_PER_JAAR / KLANT_KG_PER_JAAR, 2),
        'periodes_per_jaar': PERIODES_PER_JAAR,
        'leads_per_jaar': round(acht['leads'] * PERIODES_PER_JAAR),
        'investering_per_jaar': acht['periode'] * PERIODES_PER_JAAR,
        'leads_per_klant': round(KLANT_OMZET_PER_JAAR / acht['per_lead']),
        'klanten_break_even': round(acht['periode'] * PERIODES_PER_JAAR / KLANT_OMZET_PER_JAAR, 1),
    }

    stats = {
        'bron': Path(path).name,
        'klantwaarde': klant,
        'periode': {'van': str(start), 'tot': str(eind), 'weken': round(weken, 1), 'periodes': round(periodes, 2)},
        'volume': {
            'pogingen': pogingen, 'bedrijven': bedrijven, 'gesproken': gesproken,
            'bereikbaarheid': round(gesproken / pogingen * 100, 1),
            'dagen_actief': int(perdag.size), 'volle_beldagen': int(volle.size),
            'pogingen_per_beldag': round(pog_per_beldag),
            'drukste_dag': int(perdag.max()),
        },
        'resultaat': {
            'leads': leads, 'afspraken': afspraken, 'overdrachten': overdrachten,
            'tastings': tastings, 'tastings_onder_101': len(TASTINGS_ONDER_101),
            'leads_per_1000': round(leads_per_1000, 1),
            'tastings_per_1000': round(tast_per_1000, 1),
            'leads_per_beldag': round(leads_per_beldag, 1),
            'tastings_per_beldag': round(tast_per_beldag, 1),
        },
        'pijplijn': {
            'open_warm': open_pijplijn, 'al_voorzien': al_voorzien,
            'nooit_bereikt': nooit_bereikt,
            'terugbelafspraak': status.get(500, 0), 'infomail': status.get(501, 0),
        },
        'norm_pogingen_per_beldag': NORM_POGINGEN_PER_BELDAG,
        'huidig': huidig,
        'staffel': staffel,
        'weekdagen': dagen,
        'dagdelen': dagdelen,
        'maanden': maanden,
    }

    out = ROOT / 'content' / 'moyee-stats.json'
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{out} geschreven')
    print(json.dumps({k: stats[k] for k in ('periode', 'volume', 'resultaat', 'pijplijn', 'huidig', 'klantwaarde')},
                     ensure_ascii=False, indent=2))
    for r in staffel:
        print(f"  {r['beldagen']:>2} beldagen  EUR {r['dagprijs']}  per 4 wk EUR {r['periode']:>5}  "
              f"{r['pogingen']:>4} pogingen  {r['leads']:>4} leads  {r['tastings']:>4} tastings  "
              f"EUR {r['per_lead']}/lead")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'data' / 'moyee-export.xls'))

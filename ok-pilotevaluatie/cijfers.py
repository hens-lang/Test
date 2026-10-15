# -*- coding: utf-8 -*-
"""
Cijfers pilotevaluatie OK Creative Agency x LINK.

Eén bron van waarheid: deck, sprekersnotities en one-pager lezen allemaal
uit compute(). Elk getal is te herleiden tot een van de drie bronnen:
  - data/portaal.csv          leads en afspraken uit het OK-portaal
  - belexport (.xls)          laatste status per record (Belstat)
  - contactstatistieken (.xls) pogingen, calls en uren over de hele pilot
"""
import re, csv, datetime as dt
from pathlib import Path
import pandas as pd
import warnings; warnings.filterwarnings('ignore')

HERE = Path(__file__).parent
PEILDATUM = dt.date(2026, 10, 15)   # dag van de evaluatie; de exports zijn van 14-10-2026
BELSTART = dt.date(2026, 8, 3)
UITSLUITEN = {'TC Productions'}          # was al bekend bij OK

WP = [  # (naam, start, eind)
    ('WP1', dt.date(2026, 8, 3),  dt.date(2026, 8, 30)),
    ('WP2', dt.date(2026, 8, 31), dt.date(2026, 9, 27)),
    ('WP3', dt.date(2026, 9, 28), dt.date(2026, 10, 25)),
]
PILOT = dict(prijs_wp=2000, doel_wp=6, wps=3)

# Vervolg: KPI = 2 afspraken per beldag x aantal beldagen
KPI_PER_BELDAG = 2
OPTIES = [  # (beldagen, prijs per beldag, aanbevolen): staffel 600 / 575 / 550, geen advies: OK kiest zelf
    (4, 600, False),
    (6, 575, False),
    (8, 550, False),
]
START_VERVOLG = dt.date(2026, 10, 26)
UREN_PER_BELDAG = 8

# Status in het portaal die betekent: gesprek heeft plaatsgevonden
# Portaalstatussen die betekenen: het gesprek heeft plaatsgevonden. Wat OK daarna doet
# (offerte, vervolg) is aan OK; in het deck heet elk gehouden gesprek 'Gesprek geweest'.
GEHOUDEN = {'Offerte maken', 'Vervolg gepland', 'Gekwalificeerd', 'Afspraak geweest', 'Geen match'}

# Het concrete vraagstuk per lead, uit de belnotities (zonder persoonsnamen)
KANSEN = {
    'Zorgwerk': 'Nam na ons contact zelf contact op met OK en wilde kennismaken.',
    'Rotterdam Leisure Group': 'Hoe bezoekers van één activiteit ook de andere 15 activiteiten van de groep ontdekken.',
    'ING': 'Wil online sparren over sponsorships en events.',
    'Danieli Corus': 'Concreet vraagstuk rond hun corporate presentaties, waar ze handen tekort komen.',
    'BNU Groep': 'Wilde horen hoe OK naar marketing en communicatie kijkt en wat dat voor BNU betekent.',
    'AAme': 'Belde zelf terug en wilde kennismaken.',
    "Doen'r": 'Kennismaking ingepland na afstemming per mail.',
    'Moyee Coffee Nederland': 'Positionering rond het FairChain-verhaal achter de koffie.',
    'IV': 'Employer branding: hun brand marketeer wil kennismaken.',
    'Hunebedcentrum': 'Een blik van buiten op hun communicatie, en een ingang in de museale wereld.',
    'Aluwdoors': 'Een merk dat voor particulieren, zakelijke klanten en nieuwe collega’s tegelijk moet werken.',
    'Hotel Specials': 'Branding, op locatie in Haarlem. Bookerzzz zit erachter, dus mogelijk meer merken.',
    'Safecourt': 'Groeiend merk met een volle campagnekalender, in 2027 behoefte aan extra creatieve ondersteuning.',
    'Focus Engineering': 'Wil de marketing vanaf Q2 uitbesteden. Gesprek in maart over campagnes.',
    'Randstad Groep': 'Veel campagnes en openstaande vacatures, wil weten wat OK voor hen kan betekenen.',
}
SPOKEN = [100, 101, 200, 201, 202, 500]


def wp_van(d):
    for naam, s, e in WP:
        if s <= d <= e:
            return naam
    return None


def euro(n):
    if abs(n - round(n)) > 0.004:   # bedragen met centen, bijv. € 287,50
        return '€\xa0' + f'{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return '€\xa0' + f'{n:,.0f}'.replace(',', '.')


def num(n):
    return f'{n:,.0f}'.replace(',', '.')


def pct(a, b):
    return round(100 * a / b) if b else 0


def d(s):
    return s.strftime('%d-%m-%Y')


# --- bronnen -----------------------------------------------------------------
def load_portaal(path=HERE / 'data' / 'portaal.csv'):
    rows = []
    with open(path, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter=';'):
            r['aangemaakt'] = dt.datetime.strptime(r['aangemaakt'], '%d-%m-%Y').date()
            r['gesprek_dt'] = dt.datetime.strptime(r['gesprek'], '%d-%m-%Y %H:%M')
            r['gesprek_d'] = r['gesprek_dt'].date()
            r['wp'] = wp_van(r['aangemaakt'])
            r['telt'] = r['bedrijf'] not in UITSLUITEN
            r['gehouden'] = r['status'] in GEHOUDEN
            r['gepland'] = (not r['gehouden']) and r['gesprek_d'] > PEILDATUM
            rows.append(r)
    return rows


def load_belexport(path):
    t = pd.read_html(path, flavor='bs4')[0]
    t.columns = [str(c).replace('\xa0', ' ').strip() for c in t.columns]
    t['code'] = t['Resultaatcode'].astype(str).str.extract(r'(\d+)')[0].astype(int)
    t['dt'] = pd.to_datetime(t['Contactmoment datum & tijd'], dayfirst=True)
    # dubbele exportregels (zelfde record) eruit
    return t.drop_duplicates('CTPID').copy()


def _hm(s):
    m = re.search(r'(\d+):(\d{2})', s)
    return int(m.group(1)) + int(m.group(2)) / 60


def load_stats(path):
    s = open(path, encoding='utf-8').read()
    rows = []
    for r in re.findall(r'<Row[^>]*>(.*?)</Row>', s, re.S):
        cells = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip()
                 for c in re.findall(r'<Data[^>]*>(.*?)</Data>', r, re.S)]
        rows.append(cells)
    head = rows[0]
    tot = next(r for r in rows if r and r[0].startswith('Records:') and 'Tijdsduur' in r[0])
    col = {h: i for i, h in enumerate(head)}
    return {
        'pogingen': int(tot[col['Contactpog.']]),
        'calls': int(tot[col['Calls']]),
        'hits': int(tot[col['Hits']]),
        'uren_record': _hm(tot[col['Record tijd']]),
        'uren_record_txt': tot[col['Record tijd']],
        'uren_ingelogd': _hm(tot[0].split('Tijdsduur')[1]),
        'uren_ingelogd_txt': tot[0].split('Tijdsduur')[1].strip(),
    }


# --- berekening ----------------------------------------------------------------
def compute(belexport, stats):
    P = load_portaal()
    B = load_belexport(belexport)
    S = load_stats(stats)
    tellen = [r for r in P if r['telt']]

    # Leads per werkperiode, op aanmaakdatum
    per_wp = {n: [r for r in tellen if r['wp'] == n] for n, _, _ in WP}
    gehouden = [r for r in tellen if r['gehouden']]
    gepland = sorted([r for r in tellen if r['gepland']], key=lambda r: r['gesprek_dt'])
    open_lead = [r for r in tellen if not r['gehouden'] and not r['gepland']]

    # Belexport: alles vanaf belstart. Records van voor de start (24-07) zijn
    # bestaande relaties van OK die bij het opschonen zijn uitgesloten.
    pre = B[B.dt.dt.date < BELSTART]
    Bc = B[B.dt.dt.date >= BELSTART].copy()
    Bc['wp'] = Bc.dt.dt.date.map(wp_van)
    spoken = Bc[Bc.code.isin(SPOKEN)]
    hits_bel = Bc[Bc.code.isin([100, 101]) & ~Bc.Bedrijf.isin(UITSLUITEN)]

    wp_bel = {}
    for n, _, _ in WP:
        g = Bc[Bc.wp == n]
        sp = g[g.code.isin(SPOKEN)]
        wp_bel[n] = dict(
            records=len(g),
            gesproken=len(sp),
            niet_geschikt=int((g.code == 202).sum()),
            geen_interesse=int(g.code.isin([200, 201]).sum()),
            terugbel=int((g.code == 500).sum()),
            infomail=int((g.code == 501).sum()),
            niet_geschikt_pct=pct(int((g.code == 202).sum()), len(sp)),
        )

    # Lijsten van OK zelf vs de brede lijst
    lijst = {}
    for code, label in [('OK Project 1', 'Brede lijst zakelijke dienstverlening'),
                        ('OK Project 2', 'New Business-lijst van OK')]:
        g = Bc[Bc.Projectcode == code]
        sp = g[g.code.isin(SPOKEN)]
        h = g[g.code.isin([100, 101]) & ~g.Bedrijf.isin(UITSLUITEN)]
        lijst[code] = dict(label=label, gesproken=len(sp), hits=len(h),
                           pct=round(100 * len(h) / len(sp), 1))

    moyee = next(r for r in tellen if r['bedrijf'].startswith('Moyee'))

    c = dict(
        peildatum=PEILDATUM,
        portaal=P, tellen=tellen, per_wp=per_wp,
        gehouden=gehouden,
        gepland=gepland, open_lead=open_lead, moyee=moyee,
        n_leads=len(tellen),
        n_afspraak=sum(r['type'] == 'Afspraak' for r in tellen),
        n_lead=sum(r['type'] == 'Lead' for r in tellen),
        doel_totaal=PILOT['doel_wp'] * PILOT['wps'],
        pilot_totaal=PILOT['prijs_wp'] * PILOT['wps'],
        pilot_per_afspraak=round(PILOT['prijs_wp'] / PILOT['doel_wp']),
        pogingen=S['pogingen'], calls=S['calls'],
        bereik=pct(S['calls'], S['pogingen']),
        gesproken=int(spoken.Bedrijf.nunique()),
        terugbel_open=int((Bc.code == 500).sum()),
        infomail=int((Bc.code == 501).sum()),
        uitgesloten_vooraf=len(pre),
        wp_bel=wp_bel, lijst=lijst,
        uren_record=S['uren_record'], uren_record_txt=S['uren_record_txt'],
        uren_ingelogd=S['uren_ingelogd'], uren_ingelogd_txt=S['uren_ingelogd_txt'],
        beldagen=S['uren_record'] / UREN_PER_BELDAG,
        # Plaud 14-10-2026: OK-tarief voor een middelgroot traject is 20K; Moyee krijgt korting
        # omdat Moyee al veel had aangeleverd. Het exacte offertebedrag is nog niet bekend.
        tarief_moyee=20000,
    )
    c['beldagen_per_lead'] = c['n_leads'] / c['beldagen']
    c['opties'] = [dict(beldagen=b, prijs=b * pd, aanbevolen=a, kpi=b * KPI_PER_BELDAG,
                        per_afspraak=b * pd / (b * KPI_PER_BELDAG),
                        per_beldag=pd) for b, pd, a in OPTIES]
    wp4_eind = START_VERVOLG + dt.timedelta(days=27)
    c['wp4'] = (START_VERVOLG, wp4_eind)
    c['wp5_start'] = wp4_eind + dt.timedelta(days=1)

    # --- consistentiechecks: de bronnen moeten op elkaar aansluiten ---------
    assert len(P) == 16
    assert c['n_leads'] == 15, c['n_leads']
    assert [len(per_wp[n]) for n, _, _ in WP] == [5, 3, 7]
    assert B['Aantal contactpogingen'].sum() == S['pogingen'], 'belexport en stats wijken af'
    # belexport-hits (zonder TC) + Moyee (niet in Belstat) = portaal
    assert len(hits_bel) + 1 == c['n_leads'], len(hits_bel)
    assert S['hits'] == len(hits_bel) + len(UITSLUITEN)
    assert len(gehouden) == 5
    assert all(r['bedrijf'] in KANSEN for r in tellen), [r['bedrijf'] for r in tellen if r['bedrijf'] not in KANSEN]
    assert len(gepland) == 9
    assert sum(len(v) for v in per_wp.values()) == c['n_leads']
    assert len(gehouden) + len(gepland) + len(open_lead) == c['n_leads']
    for o in c['opties']:
        assert o['kpi'] == o['beldagen'] * KPI_PER_BELDAG
    assert [o['prijs'] for o in c['opties']] == [2400, 3450, 4400]
    assert [o['per_afspraak'] for o in c['opties']] == [300, 287.5, 275]
    return c


if __name__ == '__main__':
    import sys, pprint
    c = compute(sys.argv[1], sys.argv[2])
    for k in ['n_leads', 'n_afspraak', 'n_lead', 'pogingen', 'calls', 'bereik', 'gesproken',
              'terugbel_open', 'infomail', 'uitgesloten_vooraf', 'uren_record_txt',
              'uren_ingelogd_txt', 'beldagen', 'beldagen_per_lead']:
        print(k, c[k])
    pprint.pprint(c['wp_bel']); pprint.pprint(c['lijst']); pprint.pprint(c['opties'])
    print([(r['bedrijf'], d(r['gesprek_d'])) for r in c['gepland']])
    print([r['bedrijf'] for r in c['open_lead']])

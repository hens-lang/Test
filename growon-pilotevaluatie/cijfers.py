# -*- coding: utf-8 -*-
"""
Cijfers pilotevaluatie GrowOn Agency x LINK.

Eén bron van waarheid: deck, sprekersnotities en one-pager lezen allemaal
uit compute(). Elk getal is te herleiden tot een van de drie bronnen:
  - data/portaal.csv           leads en afspraken uit het portaal (stand 15-10-2026)
  - belexport (.xls)           laatste status per record (Belstat)
  - contactstatistieken (.xls) pogingen, calls en uren over de hele pilot
Pilotafspraak: mail 14-07-2026 (8 gekwalificeerde leads per 4 weken à 200 euro,
succesfee 5% over 12 maanden), facturen 2026-0052, -0070, -0079, -0096.
"""
import re, csv, datetime as dt
from pathlib import Path
import pandas as pd
import warnings; warnings.filterwarnings('ignore')

HERE = Path(__file__).parent
KLANT = 'GrowOn Agency'
PEILDATUM = dt.date(2026, 10, 16)   # dag van de evaluatie; de exports zijn van 15-10-2026
DATASTAND = dt.date(2026, 10, 15)
BELSTART = dt.date(2026, 8, 3)
UITSLUITEN = set()

WP = [  # (naam, start, eind)
    ('WP1', dt.date(2026, 8, 3),  dt.date(2026, 8, 30)),
    ('WP2', dt.date(2026, 8, 31), dt.date(2026, 9, 27)),
    ('WP3', dt.date(2026, 9, 28), dt.date(2026, 10, 25)),
]
PILOT = dict(prijs_wp=1600, doel_wp=8, wps=3, per_lead=200, succesfee='5% over de eerste 12 maanden')

# Vervolg: KPI = 2,5 afspraken per beldag x aantal beldagen (keuze Hens, 15-10-2026)
KPI_PER_BELDAG = 2.5
KPI_TXT = '2,5'
OPTIES = [  # (beldagen, prijs per beldag, aanbevolen): staffel 600 / 575 / 550, geen advies
    (4, 600, False),
    (6, 575, False),
    (8, 550, False),
]
START_VERVOLG = dt.date(2026, 10, 26)
UREN_PER_BELDAG = 8

# Gesprek geweest = datum voorbij en niet verzet of nog open. Statussen van GrowOn zelf
# (offerte, vervolg) tonen we niet; 'Gewonnen' wel, daar loopt de succesfee over.
NIET_GEHOUDEN = {'Afspraak verplaatsen', 'Nieuw'}
GEEN_MATCH = 'Geen match'
GEWONNEN = 'Gewonnen'

# Het concrete vraagstuk per lead, uit de belnotities (zonder persoonsnamen)
KANSEN = {
    'Goodnight Slaapkamers': 'Slaapkamerspecialist met winkel en webshop, kennismaking binnen vier weken.',
    'Bahlmann': 'Veel budget voor online ads, maar de online verkoop loopt achter op de winkel. Huidige bureau levert niet.',
    'Gents': 'Groot, veel winkels en 8 Meta-ads. Ontevreden over de huidige partner, wil uitbesteden aan kwaliteit.',
    'Fauna Hengelsport': 'Grote speler in hengelsport met webshop. Ziet dat de huidige partij er niet alles uithaalt.',
    'Köster Fashion': 'Dure merken en een webshop die achterloopt. Budget voor meer ads.',
    'Messermeister Europe': 'Bezoekers haken af op de site en de ads liggen stil. Groot bedrijf met veel budget.',
    'Cartouche Fashion': 'Grote webshop met veel Meta-ads en een hoge omloopsnelheid. Wil sparren over betere ads.',
    'Kip Aloha damesmode': 'Doet de ads zelf, met een fors maandbudget. Wil eerst een paar inzichten per mail.',
    'Teddy Days': 'Warme lead, rechtstreeks door GrowOn opgepakt.',
    'OSKA Nederland': 'Ontevreden over het huidige bureau, dat contract loopt af. Een nieuwe online collega schuift aan.',
    'Catwalk Junkie': 'Kan al twee jaar niet adverteren door een gehackt Meta-account. Het budget ligt klaar.',
    'Interieurbeplanting De Klerk': 'Werkt met een ander bureau en is net begonnen op Meta. Wil de verbeterpunten horen.',
    'Green Earth': 'Lead uit de pilot, inmiddels klant van GrowOn.',
    'Van Zuilen Mode': 'Niet tevreden over de huidige partner: zwakke ads en een matige website.',
    'Hippe Kippe': 'Van 280 naar 37 ads online en nog niet tevreden over de huidige partner.',
    'Klein Kleding': 'Direct beslissend, adverteert slim met AI-tools via Google Ads.',
    'BBQtime.nl': 'Zocht via LinkedIn een partner, kreeg bijna 200 reacties en koos voor dit gesprek.',
    'De Schans': 'Vorige partner net opgezegd, nieuwe online marketeer. Precies het goede moment.',
    'Qpro': 'Opvolging in december, als het voor hen past.',
    'Antilope Outdoor': 'Uit de eerdere contactlijst van GrowOn, kennismaking op 15-10.',
    'P. Ris': 'Groot advertentiebudget, nu vooral billboards, radio en krant. Wil meer online.',
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
            r['gehouden'] = r['gesprek_d'] <= PEILDATUM and r['status'] not in NIET_GEHOUDEN
            r['gepland'] = (not r['gehouden']) and r['gesprek_d'] > PEILDATUM
            r['geen_match'] = r['status'] == GEEN_MATCH
            r['gewonnen'] = r['status'] == GEWONNEN
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

    # Eerder aangeraakte adressen (contactlijst van GrowOn) tegenover de SBI-lijsten
    lijst = {}
    eigen = Bc['Naam project'] == 'Eerder aangeraakte adressen'
    for key, mask, label in [('eigen', eigen, 'Eerdere contactlijst van GrowOn'), ('breed', ~eigen, 'SBI-lijsten retail en webshops')]:
        g = Bc[mask]
        sp = g[g.code.isin(SPOKEN)]
        h = g[g.code.isin([100, 101])]
        lijst[key] = dict(label=label, gesproken=len(sp), hits=len(h), pct=round(100 * len(h) / len(sp), 1))

    c = dict(
        peildatum=PEILDATUM,
        portaal=P, tellen=tellen, per_wp=per_wp,
        gehouden=gehouden,
        gepland=gepland, open_lead=open_lead,
        geen_match=[r for r in tellen if r['geen_match']], gewonnen=[r for r in tellen if r['gewonnen']],
        n_leads=len(tellen),
        n_afspraak=sum(r['type'] == 'Afspraak' for r in tellen),
        n_lead=sum(r['type'] == 'Lead' for r in tellen),
        doel_totaal=PILOT['doel_wp'] * PILOT['wps'],
        pilot_totaal=PILOT['prijs_wp'] * PILOT['wps'],
        pilot_per_afspraak=PILOT['prijs_wp'] / PILOT['doel_wp'],
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
    )
    c['beldagen_per_lead'] = c['n_leads'] / c['beldagen']
    c['opties'] = [dict(beldagen=b, prijs=b * pd, aanbevolen=a, kpi=round(b * KPI_PER_BELDAG),
                        per_afspraak=b * pd / (b * KPI_PER_BELDAG),
                        per_beldag=pd) for b, pd, a in OPTIES]
    wp4_eind = START_VERVOLG + dt.timedelta(days=27)
    c['wp4'] = (START_VERVOLG, wp4_eind)
    c['wp5_start'] = wp4_eind + dt.timedelta(days=1)

    # --- consistentiechecks: de bronnen moeten op elkaar aansluiten ---------
    assert len(P) == 24
    assert c['n_leads'] == 24, c['n_leads']
    assert [len(per_wp[n]) for n, _, _ in WP] == [10, 9, 5]
    assert B['Aantal contactpogingen'].sum() == S['pogingen'], 'belexport en stats wijken af'
    # belexport-hits + Green Earth (niet in Belstat) = portaal
    assert len(hits_bel) + 1 == c['n_leads'], len(hits_bel)
    assert len(gehouden) == 19 and len(gepland) == 2 and len(open_lead) == 3, (len(gehouden), len(gepland), len(open_lead))
    assert all(r['bedrijf'] in KANSEN for r in tellen if not r['geen_match'])
    assert all(r['wp'] == 'WP1' for r in c['geen_match'])
    assert sum(len(v) for v in per_wp.values()) == c['n_leads']
    assert [o['kpi'] for o in c['opties']] == [10, 15, 20]
    assert [o['prijs'] for o in c['opties']] == [2400, 3450, 4400]
    assert [o['per_afspraak'] for o in c['opties']] == [240, 230, 220]
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

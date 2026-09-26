#!/usr/bin/env python3
"""Schrijft de cijfers uit content/moyee-stats.json in content/moyee.json.

Zo staat er nergens een getal met de hand ingetypt: de belexport is de bron,
analyse-moyee.py rekent het door en dit script zet het in de deck.

    python3 build/analyse-moyee.py data/moyee-export.xls
    python3 build/sync-moyee.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / 'content' / 'moyee-stats.json').read_text(encoding='utf-8'))
DECK = ROOT / 'content' / 'moyee.json'
d = json.loads(DECK.read_text(encoding='utf-8'))
by_id = {s['id']: s for s in d['slides']}

vol, res, pij, hui = S['volume'], S['resultaat'], S['pijplijn'], S['huidig']
norm = S['norm_pogingen_per_beldag']
eur = lambda n: '€ ' + f'{n:,.0f}'.replace(',', '.')
nl = lambda x: str(x).replace('.', ',')
dui = lambda n: f'{n:,.0f}'.replace(',', '.')

# kosten van het huidige model: vaste fee plus tastingfee per periode
VAST, TASTINGFEE = 1500, 150
nu_kosten = VAST + hui['tastings_per_periode'] * TASTINGFEE
nu_per_lead = nu_kosten / hui['leads_per_periode']

# ---------- 05 cijfers ----------
c = by_id['cijfers']
c['eyebrow'] = 'Wat er tot nu toe gebeld is'
c['cards'] = [
    {
        'value': dui(vol['pogingen']),
        'unit': 'gesprekspogingen',
        'label': f"Tussen maart en september 2026, verdeeld over {vol['volle_beldagen']} volle beldagen.",
    },
    {
        'value': dui(vol['gesproken']),
        'unit': 'bedrijven gesproken',
        'label': f"Van de {dui(vol['bedrijven'])} benaderde bedrijven kregen we bij zeven op de tien de juiste persoon aan de lijn.",
    },
    {
        'value': str(res['leads']),
        'unit': 'gekwalificeerde leads',
        'label': f"{res['afspraken']} tastingafspraken en {res['overdrachten']} bedrijven die wilden proeven of bestellen.",
    },
    {
        'value': str(res['tastings']),
        'unit': 'tastings ingepland',
        'label': f"Waarvan er {res['tastings_onder_101']} onder de overdrachten stonden. Samen {nl(res['tastings_per_beldag'])} tasting per beldag.",
        'highlight': True,
    },
]
c['closing'] = (
    f"Uit die {dui(vol['pogingen'])} pogingen komt het kengetal waar het voorstel op rust: "
    f"{nl(res['leads_per_1000'])} gekwalificeerde leads per duizend gesprekspogingen."
)

# ---------- 06 de juiste dagen ----------
och = next(x for x in S['dagdelen'] if x['deel'] == 'ochtend')
laat = next(x for x in S['dagdelen'] if x['deel'] == 'eind van de middag')
beste = max(S['weekdagen'], key=lambda x: x['bereik'])
slechtste = min(S['weekdagen'], key=lambda x: x['bereik'])
dg = by_id['dagen']
dg['cards'] = [
    {
        'title': 'Alles is geteld',
        'text': f"Van elke van de {dui(vol['pogingen'])} pogingen ligt vast wanneer hij gevoerd is en wat hij opleverde. Per dag, per dagdeel en per soort bedrijf.",
    },
    {
        'title': "'s Ochtends zit de beslisser er",
        'text': f"Tussen {och['van']} en {och['tot']} uur krijgen we {nl(och['bereik'])} procent van de gebelde bedrijven te spreken. Na {laat['van']} uur zakt dat naar {nl(laat['bereik'])} procent.",
    },
    {
        'title': 'Ook de dag maakt verschil',
        'text': f"{beste['dag'].capitalize()} levert de hoogste bereikbaarheid op met {nl(beste['bereik'])} procent, {slechtste['dag']} de laagste met {nl(slechtste['bereik'])} procent.",
    },
    {
        'title': 'Beldagen op de beste momenten',
        'text': 'We plannen de beldagen op de dagen en dagdelen die in jullie eigen cijfers het hoogste scoren, en na elke periode kijken we of dat nog klopt.',
        'highlight': True,
    },
]
dg['closing'] = f"Per duizend pogingen levert de ochtend {nl(och['leads_per_1000'])} leads op en het eind van de middag {nl(laat['leads_per_1000'])}. Daar plannen we op."

# ---------- 09 staffel ----------
lpb = res['leads_per_beldag']
st = by_id['staffel']
st['columns'] = ['Beldagen per 4 weken', 'Prijs per beldag', 'Per 4 weken', 'Verwachte leads']
tier = {r['beldagen']: r for r in S['staffel']}
per_dag = res['leads_per_1000'] * norm / 1000
st['rows'] = [
    {'cells': ['4 beldagen', eur(600), eur(2400), f"± {round(tier[4]['leads'])} leads"]},
    {'cells': ['5 tot 7 beldagen', eur(550), f'{eur(2750)} tot {eur(3850)}',
               f'± {round(5*per_dag)} tot {round(7*per_dag)} leads']},
    {'cells': ['8 beldagen of meer', eur(500), f'vanaf {eur(4000)}',
               f"vanaf ± {round(tier[8]['leads'])} leads"],
     'note': 'ons advies', 'highlight': True},
]
st['closing'] = (
    f"De aantallen zijn een indicatie, gebaseerd op {nl(res['leads_per_1000'])} gekwalificeerde leads per duizend "
    f"gesprekspogingen over {dui(vol['pogingen'])} gesprekken voor Moyee, bij ongeveer {norm} pogingen per beldag. "
    'Minimaal vier beldagen per periode, prijzen excl. btw.'
)

# ---------- 10 vergelijking ----------
v = by_id['vergelijking']
v['columns'][0].update({
    'tag': f"Nu · ± {nl(hui['beldagen_per_periode'])} beldagen",
    'head': f'{eur(VAST)} per maand plus {eur(TASTINGFEE)} per gekwalificeerde tasting',
    'rows': [
        {'key': 'Kosten per 4 weken', 'value': f'± {eur(nu_kosten)}'},
        {'key': 'Gesprekspogingen', 'value': f"± {dui(hui['pogingen_per_periode'])}"},
        {'key': 'Verwachte leads', 'value': f"± {round(hui['leads_per_periode'])}"},
        {'key': 'Prijs per lead', 'value': f'± {eur(nu_per_lead)}'},
    ],
})
acht = next(x for x in S['staffel'] if x['beldagen'] == 8)
v['columns'][1].update({
    'tag': 'Voorstel · acht beldagen',
    'head': f"{eur(500)} per beldag, verder niets",
    'rows': [
        {'key': 'Kosten per 4 weken', 'value': eur(acht['periode'])},
        {'key': 'Gesprekspogingen', 'value': f"± {dui(acht['pogingen'])}"},
        {'key': 'Verwachte leads', 'value': f"± {round(acht['leads'])}"},
        {'key': 'Prijs per lead', 'value': eur(acht['per_lead'])},
    ],
})
groei = (acht['pogingen'] / hui['pogingen_per_periode'] - 1) * 100
verschil = acht['per_lead'] - nu_per_lead
if verschil < -5:
    prijszin = 'en de prijs per lead gaat omlaag'
elif verschil <= 5:
    prijszin = 'tegen vrijwel dezelfde prijs per lead'
else:
    prijszin = f'tegen {eur(verschil)} meer per lead'
v['title'] = ([{'t': 'Bijna twee keer zoveel gesprekken, voor '}, {'t': 'dezelfde prijs', 'accent': True}, {'t': ' per lead.'}]
              if verschil <= 5 else
              [{'t': 'Meer beldagen, en toch een lagere prijs '}, {'t': 'per lead', 'accent': True}, {'t': '.'}])
v['closing'] = (
    f"Acht beldagen is {round(groei)} procent meer gesprekken dan we nu per periode voeren, "
    f"{prijszin}. En jullie weten vooraf wat een periode kost, in plaats van achteraf."
)

# ---------- pijplijn (nieuw, vóór de staffel) ----------
pijl = {
    'id': 'pijplijn', 'type': 'figures', 'theme': 'light',
    'eyebrow': 'Wat er nog klaarstaat',
    'title': [{'t': 'De pijplijn is nog lang niet '}, {'t': 'leeg', 'accent': True}, {'t': '.'}],
    'cards': [
        {'value': str(pij['open_warm']), 'unit': 'warme contacten open',
         'label': f"{pij['terugbelafspraak']} terugbelafspraken en {pij['infomail']} bedrijven die informatie kregen."},
        {'value': str(pij['al_voorzien']), 'unit': 'zitten aan een contract',
         'label': 'Die zijn nu voorzien, maar hun contract loopt een keer af. Wij houden ze vast.'},
        {'value': str(pij['nooit_bereikt']), 'unit': 'nog niet bereikt',
         'label': 'Wel benaderd, nog geen contact gehad. Daar is nog volledige winst te halen.'},
        {'value': dui(vol['bedrijven']), 'unit': 'bedrijven benaderd',
         'label': 'En dat is nog maar een fractie van de markt. Er kan hier nog jaren op gebeld worden.',
         'highlight': True},
    ],
    'closing': 'Elke periode die we bellen groeit deze lijst mee. Opschalen betekent dus ook sneller terug bij de bedrijven die er al in zitten.',
}
d['slides'] = [s for s in d['slides'] if s['id'] != 'pijplijn']
idx = next(i for i, s in enumerate(d['slides']) if s['id'] == 'staffel')
d['slides'].insert(idx, pijl)

wkn = round(S['periode']['weken'])
by_id['cover']['sub'] = (
    f'Wat bijna zes maanden bellen voor Moyee heeft opgeleverd, hoe wij werken en '
    f'het voorstel om vanaf nu met vaste beldagen per vier weken te draaien.'
)
by_id['wie']['paragraphs'][1] = (
    f'Voor Moyee bellen we sinds eind maart. In die tijd hebben we geleerd welke bedrijven '
    f'openstaan voor een gesprek, welke ingang werkt en wanneer de juiste persoon bereikbaar is. '
    f'Die kennis zit nu in de bellijst en in het script.'
)
by_id['wie']['stats'][1] = {
    'value': str(wkn),
    'label': 'weken samen onderweg',
    'detail': 'Van eind maart tot en met september 2026, elke week gebeld en elke week teruggekoppeld.',
}
by_id['bekendheid']['cards'][0]['text'] = (
    f"In een half jaar hebben we {dui(vol['bedrijven'])} bedrijven benaderd en {dui(vol['pogingen'])} keer gebeld. "
    f'Dat is nog maar een fractie van de markt, en elk gesprek is ook een moment waarop iemand de naam Moyee hoort.'
)
by_id['vergelijking']['columns'][0]['head'] = f'{eur(VAST)} per maand plus {eur(TASTINGFEE)} per tasting'

DECK.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'{DECK} bijgewerkt, {len(d["slides"])} slides')
print(f"  nu:      {eur(nu_kosten)} per 4 weken, {round(hui['leads_per_periode'])} leads, {eur(nu_per_lead)} per lead")
print(f"  acht:    {eur(acht['periode'])} per 4 weken, {round(acht['leads'])} leads, {eur(acht['per_lead'])} per lead")
print(f"  volume:  +{round(groei)}% gesprekspogingen")

#!/usr/bin/env python3
"""Vult build/moyee-brew.tpl.html met de cijfers uit content/moyee-stats.json.

Dezelfde bron als de deck: één belexport, één analyse, overal dezelfde getallen.

    python3 build/analyse-moyee.py data/moyee-export.xls
    python3 build/brew-moyee.py
"""
import json, base64, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = json.loads((ROOT / 'content' / 'moyee-stats.json').read_text(encoding='utf-8'))
vol, res, pij, hui, per = S['volume'], S['resultaat'], S['pijplijn'], S['huidig'], S['periode']
kl = S['klantwaarde']
norm = S['norm_pogingen_per_beldag']
tier = {r['beldagen']: r for r in S['staffel']}

dui = lambda n: f'{n:,.0f}'.replace(',', '.')
def eur(n):
    if n < 100 and n != int(n):
        return '&euro; ' + f'{n:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return '&euro; ' + f'{n:,.0f}'.replace(',', '.')
nl = lambda x: str(x).replace('.', ',')

VAST, TASTINGFEE = 1500, 150
nu_kosten = VAST + hui['tastings_per_periode'] * TASTINGFEE
nu_per_lead = nu_kosten / hui['leads_per_periode']
acht = tier[8]
groei = round((acht['pogingen'] / hui['pogingen_per_periode'] - 1) * 100)
verschil = acht['per_lead'] - nu_per_lead

MAAND = {3: 'mrt', 4: 'apr', 5: 'mei', 6: 'jun', 7: 'jul', 8: 'aug', 9: 'sep'}
MAAND_VOL = {3: 'maart', 4: 'april', 5: 'mei', 6: 'juni', 7: 'juli', 8: 'augustus', 9: 'september'}
m1 = int(per['van'].split('-')[1]); m2 = int(per['tot'].split('-')[1])


# ---------- koffie-eigen visuals ----------

BEAN = ('<g transform="translate({x},{y}) rotate({r})">'
        '<ellipse rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"/>'
        '<path d="M0,-{c} C{b},-{d} {b},{d} 0,{c}" fill="none" stroke="{seam}" stroke-width="1.3" stroke-linecap="round"/>'
        '</g>')


def bean(x, y, r, on):
    return BEAN.format(x=x, y=y, r=r, rx=11.5, ry=16,
                       fill='#38b6ff' if on else 'none',
                       stroke='#38b6ff' if on else 'rgba(242,239,230,.3)',
                       seam='#0d1420' if on else 'rgba(242,239,230,.3)',
                       c=12, b=6.4, d=4.6)


CUP = ('<svg viewBox="0 0 24 24" class="lad-cup" aria-hidden="true">'
       '<path d="M4,6 L5.6,17 Q5.9,20 8.4,20 L14.6,20 Q17.1,20 17.4,17 L19,6 Z"/>'
       '<path d="M19,9 Q22.6,9.8 22.2,13 Q21.9,15.8 18.4,16"/>'
       '<path d="M2.6,6 L20.4,6"/></svg>')


def cups_ladder(omzet, steps=(1, 5, 10)):
    rows = []
    for n in steps:
        cups = ''.join(f'<span class="lad-u" style="--i:{i}">{CUP}</span>' for i in range(n))
        rows.append(
            f'<div class="lad">'
            f'<div class="lad-k">{n} klant{"" if n == 1 else "en"}</div>'
            f'<div class="lad-c">{cups}</div>'
            f'<div class="lad-v">{eur(omzet * n)}</div>'
            f'<div class="lad-n">per jaar, alleen de koffie</div></div>')
    return '<div class="ladder">' + ''.join(rows) + '</div>'


def pour_funnel(pogingen, gesproken, leads, tastings):
    """Een volautomaat die koffie zet, met de cijfers ernaast op schaal."""
    stages = [
        ('Gesprekspogingen', pogingen, False),
        ('Bedrijven gesproken', gesproken, False),
        ('Gekwalificeerde leads', leads, True),
        ('Tastings ingepland', tastings, True),
    ]
    rows = ''.join(
        f'<div class="pst{" out" if out else ""}">'
        f'<div class="pst-k">{label}</div>'
        f'<div class="pst-v">{dui(value)}</div>'
        f'<div class="pst-t"><div class="pst-f" style="width:{max(value / pogingen * 100, 0.45):.2f}%"></div></div></div>'
        for label, value, out in stages)

    art = f'''<svg class="pour" viewBox="0 0 360 400" role="img"
     aria-label="Een volautomaat die koffie zet: de gesprekken gaan erin, de leads komen eruit">
  <defs>
    <linearGradient id="machineBody" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#252d3f"/><stop offset="1" stop-color="#12161f"/>
    </linearGradient>
    <linearGradient id="screenGlow" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#0d1a26"/><stop offset="1" stop-color="#08101a"/>
    </linearGradient>
    <clipPath id="cupClip">
      <path d="M140,264 L149,300 Q151,308 160,308 L200,308 Q209,308 211,300 L220,264 Z"/>
    </clipPath>
  </defs>

  <rect x="58" y="22" width="244" height="326" rx="26" fill="url(#machineBody)"
        stroke="rgba(242,239,230,.28)" stroke-width="2"/>
  <rect x="96" y="12" width="168" height="24" rx="12" fill="#1a2030"
        stroke="rgba(242,239,230,.22)" stroke-width="2"/>

  <rect x="90" y="56" width="112" height="54" rx="11" fill="url(#screenGlow)"
        stroke="rgba(56,182,255,.4)" stroke-width="1.6"/>
  <text class="mdisp" x="146" y="84" data-brewcount="{pogingen}">0</text>
  <text class="msub" x="146" y="100">gesprekken</text>

  <g class="mbtn">
    <circle cx="240" cy="66" r="8"/><circle cx="240" cy="90" r="8"/>
    <circle cx="240" cy="114" r="8" class="on"/>
  </g>

  <rect x="90" y="128" width="180" height="36" rx="11" fill="#0f141d"
        stroke="rgba(242,239,230,.18)" stroke-width="1.6"/>
  <g class="mbeans">
    <ellipse cx="116" cy="146" rx="7" ry="9.5"/><ellipse cx="142" cy="147" rx="7" ry="9.5"/>
    <ellipse cx="168" cy="145" rx="7" ry="9.5"/><ellipse cx="194" cy="147" rx="7" ry="9.5"/>
    <ellipse cx="220" cy="146" rx="7" ry="9.5"/><ellipse cx="246" cy="147" rx="7" ry="9.5"/>
  </g>

  <rect x="104" y="180" width="152" height="140" rx="12" fill="#090d14"
        stroke="rgba(242,239,230,.14)" stroke-width="1.6"/>
  <rect x="136" y="178" width="88" height="38" rx="9" fill="#1a2030"
        stroke="rgba(242,239,230,.26)" stroke-width="2"/>
  <rect x="157" y="214" width="11" height="13" rx="3.5" fill="#1a2030"
        stroke="rgba(242,239,230,.26)" stroke-width="1.6"/>
  <rect x="192" y="214" width="11" height="13" rx="3.5" fill="#1a2030"
        stroke="rgba(242,239,230,.26)" stroke-width="1.6"/>

  <line class="stream" x1="162.5" y1="230" x2="162.5" y2="266" stroke="#7a4526"
        stroke-width="5" stroke-linecap="round"/>
  <line class="stream s2" x1="197.5" y1="230" x2="197.5" y2="266" stroke="#7a4526"
        stroke-width="5" stroke-linecap="round"/>

  <g clip-path="url(#cupClip)">
    <rect class="fill" x="136" y="266" width="88" height="44" fill="url(#brewgrad)"/>
    <ellipse class="crema" cx="180" cy="268" rx="42" ry="7" fill="#c89464"/>
  </g>
  <path class="ln" d="M140,264 L149,300 Q151,308 160,308 L200,308 Q209,308 211,300 L220,264 Z" fill="none"/>
  <path class="ln" d="M134,264 L226,264" fill="none" stroke-linecap="round"/>
  <path class="ln" d="M220,272 Q243,278 240,291 Q238,302 214,301" fill="none"/>

  <g class="steamc">
    <path d="M152,258 C144,244 158,238 150,224"/>
    <path d="M180,256 C172,242 186,236 178,220"/>
    <path d="M208,258 C200,244 214,238 206,224"/>
  </g>

  <rect x="112" y="316" width="136" height="9" rx="4" fill="#1a2030"
        stroke="rgba(242,239,230,.2)" stroke-width="1.6"/>
</svg>'''
    out = (f'<div class="brew-out">'
           f'<svg viewBox="0 0 24 24" aria-hidden="true" class="bo-cup">'
           f'<path d="M4,6 L5.6,17 Q5.9,20 8.4,20 L14.6,20 Q17.1,20 17.4,17 L19,6 Z"/>'
           f'<path d="M19,9 Q22.6,9.8 22.2,13 Q21.9,15.8 18.4,16"/>'
           f'<path d="M2.6,6 L20.4,6"/></svg>'
           f'<span><b>Tasting ingepland</b>{tastings} keer in deze periode</span></div>')
    return f'<div class="pourwrap"><div class="pourcol">{art}{out}</div><div class="pstages">{rows}</div></div>'


def bars_to_scale(items, total):
    rows = []
    for label, value, note in items:
        rows.append(
            f'<div class="sbar"><div class="sbar-k">{label}</div>'
            f'<div class="sbar-t"><div class="sbar-f" style="width:{value / total * 100:.1f}%"></div></div>'
            f'<div class="sbar-v">{dui(value)}</div><div class="sbar-n">{note}</div></div>')
    return '<div class="sbars">' + ''.join(rows) + '</div>'


def spec(value, unit, label, hi=False):
    return (f'        <div class="spec{" hi" if hi else ""}">\n'
            f'          <div class="fig">{value}</div>\n'
            f'          <div class="unit">{unit}</div>\n'
            f'          <div class="note">{label}</div>\n'
            f'        </div>')


SPECS = '      <div class="specs s6">\n' + '\n'.join([
    spec(f'<span data-count="{vol["pogingen"]}" data-sep="1">{dui(vol["pogingen"])}</span>',
         'gesprekspogingen',
         f'Verdeeld over {vol["volle_beldagen"]} volle beldagen tussen {MAAND_VOL[m1]} en {MAAND_VOL[m2]} 2026.'),
    spec(f'<span data-count="{vol["bedrijven"]}" data-sep="1">{dui(vol["bedrijven"])}</span>',
         'bedrijven benaderd',
         'Elk bedrijf met bedrijfsinfo, contactpersoon en de uitkomst van het gesprek vastgelegd.'),
    spec(f'<span data-count="{vol["gesproken"]}" data-sep="1">{dui(vol["gesproken"])}</span>',
         'bedrijven gesproken',
         'Bij zeven op de tien benaderde bedrijven kregen we de juiste persoon aan de lijn.'),
    spec(f'<span data-count="{res["leads"]}">{res["leads"]}</span>',
         'gekwalificeerde leads',
         f'{res["afspraken"]} tastingafspraken en {res["overdrachten"]} bedrijven die wilden proeven of bestellen.'),
    spec(f'<span data-count="{res["tastings"]}">{res["tastings"]}</span>',
         'tastings ingepland',
         f'Waarvan er {res["tastings_onder_101"]} onder de overdrachten stonden, herkend aan de belnotitie.', hi=True),
    spec(f'<span data-count="{res["leads_per_1000"]}" data-dec="1">{nl(res["leads_per_1000"])}</span>',
         'leads per 1.000 pogingen',
         'Het kengetal waar het hele voorstel op rust. Niet geschat, maar geteld.'),
]) + '\n      </div>\n' + f'''      <figure class="viz viz-pour">
        {pour_funnel(vol['pogingen'], vol['gesproken'], res['leads'], res['tastings'])}
        <figcaption>Alle vier de balken staan op schaal ten opzichte van de {dui(vol['pogingen'])} gesprekspogingen. Zo klein is de laatste stap, en precies daar zit het werk.</figcaption>
      </figure>'''

PIJPLIJN = f'''    <section id="pijplijn">
      <p class="eyebrow">Wat er nog klaarstaat</p>
      <h2>De pijplijn is nog lang niet <em>leeg</em>.</h2>
      <p class="lede">Elk bedrijf houdt een status. Dit is wat er op dit moment openstaat en waar we zonder nieuwe lijst al verder kunnen.</p>
      <div class="specs s4">
{spec(f'<span data-count="{pij["open_warm"]}">{pij["open_warm"]}</span>', "warme contacten open", f"{pij['terugbelafspraak']} terugbelafspraken en {pij['infomail']} bedrijven die informatie kregen.")}
{spec(f'<span data-count="{pij["al_voorzien"]}">{pij["al_voorzien"]}</span>', "zitten aan een contract", "Nu voorzien, maar elk contract loopt een keer af. Wij houden ze vast tot dat moment.")}
{spec(f'<span data-count="{pij["nooit_bereikt"]}">{pij["nooit_bereikt"]}</span>', "nog niet bereikt", "Wel benaderd, nog geen gesprek gehad. Daar staat de volledige winst nog open.")}
{spec(f'<span data-count="{vol["bedrijven"]}" data-sep="1">{dui(vol["bedrijven"])}</span>', "bedrijven in de database", "En dat is een fractie van de markt. Er kan hier nog jaren op gebeld worden.", hi=True)}
      </div>
      {bars_to_scale([
        ('Warme contacten open', pij['open_warm'], 'terugbellen of opvolgen'),
        ('Zitten aan een contract', pij['al_voorzien'], 'komen later terug'),
        ('Nog niet bereikt', pij['nooit_bereikt'], 'volledige winst nog open'),
      ], vol['bedrijven'])}
      <p class="fine">De balken staan op schaal ten opzichte van de {dui(vol['bedrijven'])} benaderde bedrijven. Elke periode die we bellen groeit deze lijst mee. Opschalen betekent dus ook sneller terug bij de bedrijven die er al in zitten.</p>
    </section>'''

WAARDE = f'''    <section id="waarde">
      <p class="eyebrow">Wat een klant oplevert</p>
      <h2>Elke tasting is een kans op een klant die <em>jaren blijft</em>.</h2>
      <p class="lede">Bij een van de kantoren waar we een tasting inplanden gaat 300 kilo koffie per jaar doorheen. Dat is {eur(kl['omzet_per_jaar'])} aan omzet, alleen aan koffie. Geen uitschieter, gewoon een normaal kantoor.</p>
      <div class="specs s4">
{spec(f"{kl['kg_per_jaar']} kg", "koffie per jaar", "Het verbruik van dat ene kantoor. Cross- en upsell zitten daar nog niet in.")}
{spec(eur(kl['omzet_per_jaar']), "per klant per jaar", f"Tegen {eur(kl['prijs_per_kilo'])} per kilo. En dat komt elk jaar opnieuw binnen zolang ze bestellen.", hi=True)}
{spec(str(res['tastings']), "tastings staan er al", "Uit de periode die achter ons ligt. Elke tasting die klant wordt, telt vanaf dat moment mee.")}
{spec(f"&plusmn; {round(acht['tastings'])}", "tastings per periode", "Bij acht beldagen. Meer beldagen betekent meer tastings, en dus meer kansen op zo'n klant.")}
      </div>
      <figure class="viz viz-ladder">
        {cups_ladder(kl['omzet_per_jaar'])}
        <figcaption>Daarom sturen we op zoveel mogelijk tastings. Een klant die blijft bestellen telt niet één keer mee, maar elk jaar opnieuw.</figcaption>
      </figure>
    </section>'''

rows = []
for d in S['weekdagen']:
    rows.append(f'''          <tr><th scope="row">{d['dag'].capitalize()}</th>'''
                f'''<td>{dui(d['pogingen'])}</td><td class="meter"><span class="m"><i style="--v:{d['bereik']}"></i>{nl(d['bereik'])}%</span></td><td>{nl(d['leads_per_1000'])}</td></tr>''')
for d in S['dagdelen']:
    rows.append(f'''          <tr class="part"><th scope="row">{d['deel'].capitalize()} ({d['van']}&ndash;{d['tot']} uur)</th>'''
                f'''<td>{dui(d['pogingen'])}</td><td class="meter"><span class="m"><i style="--v:{d['bereik']}"></i>{nl(d['bereik'])}%</span></td><td>{nl(d['leads_per_1000'])}</td></tr>''')

och = next(x for x in S['dagdelen'] if x['deel'] == 'ochtend')
laat = next(x for x in S['dagdelen'] if x['deel'] == 'eind van de middag')
beste = max(S['weekdagen'], key=lambda x: x['bereik'])
slecht = min(S['weekdagen'], key=lambda x: x['bereik'])

WANNEER = f'''    <section id="wanneer">
      <p class="eyebrow">Wanneer we bellen</p>
      <h2>De beste momenten staan in <em>jullie cijfers</em>.</h2>
      <p class="lede">Van elke gesprekspoging ligt vast wanneer hij gevoerd is en wat hij opleverde. Zo weten we per dag en per dagdeel waar de beslisser echt zit.</p>
      <div class="tablewrap">
        <table class="data">
          <caption>Bereikbaarheid en opbrengst per dag en per dagdeel, over {dui(vol['pogingen'])} gesprekspogingen</caption>
          <thead><tr><th scope="col">Moment</th><th scope="col">Pogingen</th><th scope="col">Bereik</th><th scope="col">Leads per 1.000</th></tr></thead>
          <tbody>
{chr(10).join(rows)}
          </tbody>
        </table>
      </div>
      <p class="fine">In de ochtend krijgen we {nl(och['bereik'])} procent van de gebelde bedrijven te spreken, na {laat['van']} uur nog {nl(laat['bereik'])} procent. {beste['dag'].capitalize()} scoort het hoogst, {slecht['dag']} het laagst. Daar plannen we de beldagen op.</p>
    </section>'''


def cup(fill_top, fill_h):
    return (f'<svg class="cup" viewBox="0 0 100 120" aria-hidden="true">'
            f'<rect x="18" y="{fill_top}" width="64" height="{fill_h}" fill="url(#brewgrad)" clip-path="url(#cupclip-s)"></rect>'
            f'<use href="#cupshape"></use></svg>')


TIERS_BTN = [
    (0, '4 beldagen', 600, 'per beldag', 80, 28, False),
    (1, '5 tot 7 beldagen', 550, 'per beldag', 55, 53, False),
    (2, '8 tot 12 beldagen', 500, 'per beldag', 34, 74, True),
]
TIERS = '      <div class="tiers" role="group" aria-label="Beldagenstaffel">\n' + '\n'.join(
    f'''        <button class="tier" type="button" aria-pressed="{'true' if on else 'false'}" data-tier="{i}">
          {cup(ft, fh)}
          <div>
            <div class="days">{label}</div>
            <div class="price">{eur(prijs)}</div>
            <div class="per">{per_lbl}</div>
          </div>
        </button>''' for i, label, prijs, per_lbl, ft, fh, on in TIERS_BTN
) + f'''
      </div>

      <div class="tier-out" id="tierout" aria-live="polite">
        <div><span class="k">Per 4 weken</span><span class="v" id="t-cost">{eur(4000)} tot {eur(6000)}</span></div>
        <div><span class="k">Gesprekspogingen</span><span class="v" id="t-calls">&plusmn; {dui(800)} tot {dui(1200)}</span></div>
        <div><span class="k">Verwachte leads</span><span class="v" id="t-leads">&plusmn; {round(acht['leads'])} tot {round(12*res['leads_per_1000']*norm/1000)}</span></div>
        <div><span class="k">Waarvan tastings</span><span class="v" id="t-tast">&plusmn; {round(acht['tastings'])} tot {round(12*res['tastings_per_1000']*norm/1000)}</span></div>
        <div><span class="k">Prijs per lead</span><span class="v" id="t-lead">{eur(acht['per_lead'])}</span></div>
      </div>
      '''

vier, zes = tier[4], tier[6]
per_dag = res['leads_per_1000'] * norm / 1000
tast_dag = res['tastings_per_1000'] * norm / 1000
drie = {'periode': 12 * 500, 'pogingen': 12 * norm, 'leads': 12 * per_dag,
        'tastings': 12 * tast_dag, 'per_lead': round(12 * 500 / (12 * per_dag))}


def kolom(tag, head, rows, hl=False):
    r = '\n'.join(f'            <div class="r"><span>{k}</span><b>{v}</b></div>' for k, v in rows)
    return (f'        <div class="col{" new" if hl else " now"}">\n'
            f'          <div class="tag">{tag}</div>\n'
            f'          <h3>{head}</h3>\n          <dl>\n{r}\n          </dl>\n        </div>')


VERGELIJK = '      <div class="vs vs-3">\n' + '\n'.join([
    kolom('Nu', f"&plusmn; {nl(hui['beldagen_per_periode'])} beldagen per 4 weken", [
        ('Kosten per 4 weken', f'&plusmn; {eur(nu_kosten)}'),
        ('Gesprekspogingen', f"&plusmn; {dui(hui['pogingen_per_periode'])}"),
        ('Verwachte leads', f"&plusmn; {round(hui['leads_per_periode'])}"),
        ('Waarvan tastings', f"&plusmn; {round(hui['tastings_per_periode'])}"),
        ('Prijs per lead', f'&plusmn; {eur(nu_per_lead)}'),
    ]),
    kolom('Twee keer', '8 beldagen per 4 weken', [
        ('Kosten per 4 weken', eur(acht['periode'])),
        ('Gesprekspogingen', f"&plusmn; {dui(acht['pogingen'])}"),
        ('Verwachte leads', f"&plusmn; {round(acht['leads'])}"),
        ('Waarvan tastings', f"&plusmn; {round(acht['tastings'])}"),
        ('Prijs per lead', eur(acht['per_lead'])),
    ]),
    kolom('Drie keer', '12 beldagen per 4 weken', [
        ('Kosten per 4 weken', eur(drie['periode'])),
        ('Gesprekspogingen', f"&plusmn; {dui(drie['pogingen'])}"),
        ('Verwachte leads', f"&plusmn; {round(drie['leads'])}"),
        ('Waarvan tastings', f"&plusmn; {round(drie['tastings'])}"),
        ('Prijs per lead', eur(drie['per_lead'])),
    ], hl=True),
]) + f'''
      </div>
      <div class="bars">
        <div class="barrow">
          <div class="k">Nu</div>
          <div class="track"><div class="fill a" style="width:{hui['pogingen_per_periode']/drie['pogingen']*100:.1f}%"><b>&plusmn; {dui(hui['pogingen_per_periode'])}</b></div></div>
        </div>
        <div class="barrow">
          <div class="k">Twee keer</div>
          <div class="track"><div class="fill a" style="width:{acht['pogingen']/drie['pogingen']*100:.1f}%"><b>&plusmn; {dui(acht['pogingen'])} gesprekken</b></div></div>
        </div>
        <div class="barrow">
          <div class="k">Drie keer</div>
          <div class="track"><div class="fill b" style="width:100%"><b>&plusmn; {dui(drie['pogingen'])} gesprekken per 4 weken</b></div></div>
        </div>
      </div>
      '''

if verschil < -5:
    slotzin = f'de prijs per lead zakt van {eur(nu_per_lead)} naar {eur(acht["per_lead"])}'
elif verschil <= 5:
    slotzin = f'tegen vrijwel dezelfde prijs per lead, {eur(nu_per_lead)} nu tegen {eur(acht["per_lead"])} straks'
else:
    slotzin = f'tegen {eur(verschil)} meer per lead'
VERGELIJK_SLOT = ('De bezetting en de bellijst liggen er al. Verdubbelen kan vanaf de eerstvolgende periode, '
                  f"verdriedubbelen ook, en de prijs per lead blijft rond {eur(acht['per_lead'])}. "
                  f'Dat is {groei} procent meer gesprekken dan nu, {slotzin}.')

logo = 'data:image/png;base64,' + base64.b64encode((ROOT / 'assets' / 'moyee-logo-web.png').read_bytes()).decode()

TOK = {
    'LOGO': logo,
    'PERIODE_KORT': f'{MAAND[m1]} &ndash; {MAAND[m2]} 2026',
    'PERIODE_LANG': f'{MAAND_VOL[m1]} tot en met {MAAND_VOL[m2]} 2026',
    'WEKEN': str(round(per['weken'])),
    'POGINGEN': dui(vol['pogingen']),
    'BEDRIJVEN': dui(vol['bedrijven']),
    'LEADS': str(res['leads']),
    'TASTINGS': str(res['tastings']),
    'NORM': str(norm),
    'LEADS_PER_1000': nl(res['leads_per_1000']),
    'LEADS_PER_BELDAG': nl(res['leads_per_beldag']),
    'TAST_PER_BELDAG': nl(res['tastings_per_beldag']),
    'SPECS': SPECS,
    'PIJPLIJN': PIJPLIJN,
    'WANNEER': WANNEER,
    'WAARDE': WAARDE,
    'TIERS': TIERS,
    'VERGELIJK': VERGELIJK,
    'VERGELIJK_SLOT': VERGELIJK_SLOT,
}

tpl = (ROOT / 'build' / 'moyee-brew.tpl.html').read_text(encoding='utf-8')

# staffelknoppen in de JS met dezelfde cijfers
js = ',\n    '.join(
    "{cost:'%s', calls:'%s', leads:'%s', tast:'%s', per:'%s'}" % (
        eur(t['periode']) if n != 8 else eur(4000) + ' tot ' + eur(6000),
        ('&plusmn; ' + dui(t['pogingen'])) if n != 8 else '&plusmn; %s tot %s' % (dui(800), dui(1200)),
        ('&plusmn; %d' % round(t['leads'])) if n != 8 else '&plusmn; %d tot %d' % (round(t['leads']), round(12*per_dag)),
        ('&plusmn; %d' % round(t['tastings'])) if n != 8 else '&plusmn; %d tot %d' % (round(t['tastings']), round(12*tast_dag)),
        eur(t['per_lead']),
    ) for n, t in ((4, vier), (6, zes), (8, acht))
)
tpl = tpl.replace("""  var TIERS = [
    {cost:'&euro; 2.400', leads:'&plusmn; 10', tast:'&plusmn; 4', per:'&euro; 250'},
    {cost:'&euro; 2.750 tot &euro; 3.850', leads:'&plusmn; 12 tot 17', tast:'&plusmn; 5 tot 7', per:'&euro; 229'},
    {cost:'vanaf &euro; 4.000', leads:'vanaf &plusmn; 19', tast:'&plusmn; 8', per:'&euro; 208'}
  ];""", "  var TIERS = [\n    " + js + "\n  ];")
tpl = tpl.replace("""    document.getElementById('t-cost').innerHTML  = t.cost;""",
                  """    document.getElementById('t-cost').innerHTML  = t.cost;
    document.getElementById('t-calls').innerHTML = t.calls;""")
# de middelste schijf is een bereik
tpl = tpl.replace("{cost:'%s'" % eur(zes['periode']),
                  "{cost:'%s tot %s'" % (eur(2750), eur(3850)), 1)
tpl = tpl.replace("leads:'&plusmn; %d'" % round(zes['leads']),
                  "leads:'&plusmn; %d tot %d'" % (round(5 * res['leads_per_1000'] * norm / 1000),
                                                  round(7 * res['leads_per_1000'] * norm / 1000)), 1)
tpl = tpl.replace("calls:'%s'" % dui(zes['pogingen']),
                  "calls:'%s tot %s'" % (dui(5 * norm), dui(7 * norm)), 1)

for k, v in TOK.items():
    tpl = tpl.replace('{{%s}}' % k, v)

assert '{{' not in tpl, [x for x in tpl.split('{{')[1:3]]
out = ROOT / 'build' / 'moyee-brew.html'
out.write_text(tpl, encoding='utf-8')
print(f'{out} geschreven, {round(len(tpl.encode())/1024)} KB')
print(f"  nu {eur(nu_kosten)} / {round(hui['leads_per_periode'])} leads / {eur(nu_per_lead)} per lead")
print(f"  acht beldagen {eur(acht['periode'])} / {round(acht['leads'])} leads / {eur(acht['per_lead'])} per lead  (+{groei}% volume)")

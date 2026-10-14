# -*- coding: utf-8 -*-
"""
Bouwt de pilotevaluatie OK Creative Agency x LINK. uit één set cijfers:
  - Pilotevaluatie OK Creative Agency.html / .pdf   (deck, 16:9)
  - Sprekersnotities pilotevaluatie OK.pdf
  - Vervolgvoorstel OK Creative Agency.pdf          (one-pager voor Mees)

Gebruik:
  python3 build.py --belexport <custom_...xls> --stats <contactstatistics_...xls> [--out output]
"""
import argparse
from pathlib import Path
from weasyprint import HTML
import base64
import cijfers as C

ASSETS = Path(__file__).parent / 'assets'
_LOGO = {k: 'data:image/png;base64,' + base64.b64encode((ASSETS / f'logo_{k}.png').read_bytes()).decode()
         for k in ('zwart', 'wit')}


def logo(h, wit=False, style=''):
    # officieel logo uit 'LINK. LOGO's.zip' (Drive), bijgesneden; wit voor donkere achtergronden
    return f'<img src="{_LOGO["wit" if wit else "zwart"]}" alt="LINK." style="height:{h}px;width:auto;display:inline-block;vertical-align:baseline;{style}">'
from cijfers import euro, num, d, pct

# --- huisstijl (zelfde tokens als gen.py van de weekrapportage) -----------------
CSS_BASE = """
:root { --ink:#1c2230; --blue:#38b6ff; --muted:#6f6a5c; --card:#f8f4eb; --bar:#e4dcc8; --cream:#e9e0cd; }
* { box-sizing:border-box; }
body { margin:0; font-family: Helvetica, Arial, "Liberation Sans", sans-serif; color:var(--ink); background:var(--cream); }
.serif { font-family: Georgia, "Liberation Serif", serif; font-style:italic; font-weight:400; }
.blue { color:var(--blue); }
.logotext { font-weight:800; letter-spacing:-0.6px; }
.logotext .dot, .dot { color:var(--blue); }
"""

CSS_DECK = CSS_BASE + """
@page { size: 1280px 720px; margin:0; }
@media screen { body { background:#cfc6b2; padding:24px 0; } .slide { margin:0 auto 24px; box-shadow:0 6px 24px rgba(0,0,0,.18); } }
.slide { width:1280px; height:720px; position:relative; overflow:hidden; background:var(--cream);
         padding:56px 72px 0; page-break-after:always; break-after:page; }
.slide.dark { background:#000; color:#fff; }
.top { position:absolute; top:26px; left:72px; right:72px; display:flex; justify-content:space-between;
       font-size:13px; color:#a79f8b; }
.top .logotext { font-size:18px; color:var(--ink); }
.dark .top .logotext { color:#fff; }
.foot { position:absolute; bottom:22px; left:72px; right:72px; display:flex; justify-content:space-between;
        font-size:11.5px; color:#a79f8b; }
.eyebrow { color:var(--blue); font-size:13px; font-weight:700; letter-spacing:.22em; margin:22px 0 10px; text-transform:uppercase; }
h2 { font-size:38px; line-height:1.12; font-weight:800; margin:0 0 26px; max-width:1136px; letter-spacing:-0.4px; }
.dark h2 { color:#fff; }
.card { background:var(--card); border-radius:16px; padding:22px 24px; flex-shrink:0; }
.dark .card { background:#15181f; }
.card.black { background:#000; color:#fff; }
.lbl { color:var(--blue); font-size:12px; font-weight:700; letter-spacing:.16em; text-transform:uppercase; margin-bottom:8px; }
.row { display:flex; gap:18px; }
.col { flex:1; }
.big { font-size:64px; font-weight:800; line-height:1; letter-spacing:-1.5px; }
.cap { font-size:17px; font-weight:700; margin-top:10px; }
.sub { font-size:14px; color:var(--muted); margin-top:6px; line-height:1.45; }
.dark .sub, .black .sub { color:#a9a9a9; }
p, li { font-size:17px; line-height:1.5; }
ul { margin:0; padding-left:20px; }
li { margin-bottom:8px; }
.note { font-size:12.5px; color:var(--muted); }
.dark .note { color:#8d8d8d; }
.chip { display:inline-block; border-radius:10px; padding:4px 11px; font-size:12.5px; font-weight:700; }
.chip.ok { background:var(--blue); color:#08293c; }
.chip.neutral { background:var(--bar); color:var(--ink); }
.chip.dark { background:#000; color:#fff; }
.chip.line { border:1.5px solid var(--blue); color:var(--blue); }
table.t { width:100%; border-collapse:collapse; font-size:13.5px; }
table.t th { text-align:left; font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); padding:6px 8px; border-bottom:1.5px solid #cfc6b2; }
table.t td { padding:6px 8px; border-bottom:1px solid #ddd3bd; }
table.t td.r, table.t th.r { text-align:right; }
table.t tr.tot td { font-weight:800; border-top:1.5px solid var(--ink); border-bottom:none; }
table.t tr.muted td { color:#9a9381; }
"""


def top(dark=False):
    return (f'<div class="top">{logo(17, dark)}'
            '<span>Pilotevaluatie OK Creative Agency</span></div>')


def foot(n):
    return (f'<div class="foot"><span>LINK.  ·  OK Creative Agency  ·  15-10-2026</span>'
            f'<span>{n}</span></div>')


def slide(n, eyebrow, title, body, dark=False):
    cls = 'slide dark' if dark else 'slide'
    return (f'<section class="{cls}" id="s{n}">{top(dark)}<div class="eyebrow">{eyebrow}</div>'
            f'<h2>{title}</h2>{body}{foot(n)}</section>')


# --- grafieken (inline SVG, twee kleuren: inkt en blauw) ---------------------------
def svg_wp(c, w=640, h=380):
    vals = [len(c['per_wp'][n]) for n, _, _ in C.WP]
    doel = C.PILOT['doel_wp']
    top_v = 8
    pl, pr, pt, pb = 40, 20, 30, 56
    ih = h - pt - pb
    bw, gap = 120, (w - pl - pr - 3 * 120) / 3
    y = lambda v: pt + ih - ih * v / top_v
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, Liberation Sans, sans-serif">']
    for v in range(0, top_v + 1, 2):
        s.append(f'<line x1="{pl}" x2="{w-pr}" y1="{y(v)}" y2="{y(v)}" stroke="#d6ccb6" stroke-width="1"/>')
        s.append(f'<text x="{pl-10}" y="{y(v)+5}" text-anchor="end" font-size="14" fill="#8d8571">{v}</text>')
    for i, (n, st, en) in enumerate(C.WP):
        x = pl + gap / 2 + i * (bw + gap)
        v = vals[i]
        col = '#38b6ff' if i == 2 else '#000'
        r = 6
        yy = y(v)
        s.append(f'<path d="M{x},{y(0)} L{x},{yy+r} Q{x},{yy} {x+r},{yy} L{x+bw-r},{yy} Q{x+bw},{yy} {x+bw},{yy+r} L{x+bw},{y(0)} Z" fill="{col}"><title>{n}: {v} leads en afspraken</title></path>')
        s.append(f'<text x="{x+bw/2}" y="{yy-12}" text-anchor="middle" font-size="30" font-weight="800" fill="#1c2230">{v}</text>')
        s.append(f'<text x="{x+bw/2}" y="{h-pb+24}" text-anchor="middle" font-size="16" font-weight="700" fill="#1c2230">{n}</text>')
        s.append(f'<text x="{x+bw/2}" y="{h-pb+44}" text-anchor="middle" font-size="12.5" fill="#8d8571">{st:%d-%m} t/m {en:%d-%m}</text>')
    s.append(f'<line x1="{pl}" x2="{w-pr}" y1="{y(doel)}" y2="{y(doel)}" stroke="#1c2230" stroke-width="2" stroke-dasharray="7 6"/>')
    s.append(f'<text x="{pl+4}" y="{y(doel)-9}" font-size="14" font-weight="700" fill="#1c2230">doel {doel}</text>')
    s.append(f'<line x1="{pl}" x2="{w-pr}" y1="{y(0)}" y2="{y(0)}" stroke="#1c2230" stroke-width="1.5"/>')
    s.append('</svg>')
    return ''.join(s)


def svg_niet_geschikt(c, w=470, h=200):
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, Liberation Sans, sans-serif">']
    rows = [(n, c['wp_bel'][n]['niet_geschikt_pct']) for n, _, _ in C.WP]
    lw, maxw = 52, w - 52 - 60
    for i, (n, p) in enumerate(rows):
        yy = 18 + i * 60
        col = '#38b6ff' if i == 2 else '#000'
        bw = max(maxw * p / 100, 8)
        s.append(f'<text x="0" y="{yy+22}" font-size="16" font-weight="700" fill="#1c2230">{n}</text>')
        s.append(f'<rect x="{lw}" y="{yy}" width="{maxw}" height="32" rx="6" fill="#e4dcc8"/>')
        s.append(f'<rect x="{lw}" y="{yy}" width="{bw}" height="32" rx="6" fill="{col}"><title>{n}: {p}% niet passend</title></rect>')
        s.append(f'<text x="{lw+maxw+10}" y="{yy+23}" font-size="20" font-weight="800" fill="#1c2230">{p}%</text>')
    s.append('</svg>')
    return ''.join(s)


def svg_timeline(c, w=1136, h=330):
    items = c['gepland']
    start, end = C.dt.date(2026, 9, 24), C.dt.date(2027, 3, 31)
    span = (end - start).days
    pl, pr = 10, 10
    x = lambda dd: pl + (w - pl - pr) * (dd - start).days / span
    ym = 170
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, Liberation Sans, sans-serif">']
    s.append(f'<line x1="{pl}" x2="{w-pr}" y1="{ym}" y2="{ym}" stroke="#1c2230" stroke-width="2"/>')
    maanden = ['okt', 'nov', 'dec', 'jan', 'feb', 'mrt']
    for i, m in enumerate(maanden):
        yr, mo = (2026, 10 + i) if 10 + i <= 12 else (2027, 10 + i - 12)
        mx = x(C.dt.date(yr, mo, 1))
        s.append(f'<line x1="{mx}" x2="{mx}" y1="{ym-6}" y2="{ym+6}" stroke="#1c2230" stroke-width="1.5"/>')
        s.append(f'<text x="{mx+6}" y="{ym+24}" font-size="13" fill="#8d8571">{m}{" 2027" if yr == 2027 and mo == 1 else ""}</text>')
    # vandaag en start vervolg
    for dd, col in [(C.PEILDATUM, '#8d8571'), (C.START_VERVOLG, '#38b6ff')]:
        xx = x(dd)
        s.append(f'<line x1="{xx}" x2="{xx}" y1="{ym-16}" y2="{ym+44}" stroke="{col}" stroke-width="1.5" stroke-dasharray="4 4"/>')
    s.append(f'<text x="{x(C.PEILDATUM)-6}" y="{ym+56}" text-anchor="end" font-size="12" fill="#8d8571">vandaag 14-10</text>')
    s.append(f'<text x="{x(C.START_VERVOLG)+6}" y="{ym+56}" font-size="12" font-weight="700" fill="#38b6ff">start vervolg 26-10</text>')
    # labels boven (negatief) of onder (positief) de lijn, vaste hoogte per item
    niveaus = [-118, 98, -52, 136, -92, 98, -52, 136, -92]
    for i, r in enumerate(items):
        xx = x(r['gesprek_d'])
        lv = niveaus[i % len(niveaus)]
        name = r['bedrijf']
        if lv < 0:
            ly = ym + lv
            s.append(f'<line x1="{xx}" x2="{xx}" y1="{ly+6}" y2="{ym-9}" stroke="#1c2230" stroke-width="1"/>')
            s.append(f'<text x="{xx}" y="{ly-14}" text-anchor="middle" font-size="15" font-weight="700" fill="#1c2230">{name}</text>')
            s.append(f'<text x="{xx}" y="{ly+2}" text-anchor="middle" font-size="12.5" fill="#6f6a5c">{d(r["gesprek_d"])}</text>')
        else:
            ly = ym + lv
            s.append(f'<line x1="{xx}" x2="{xx}" y1="{ym+9}" y2="{ly-30}" stroke="#1c2230" stroke-width="1"/>')
            s.append(f'<text x="{xx}" y="{ly-12}" text-anchor="middle" font-size="15" font-weight="700" fill="#1c2230">{name}</text>')
            s.append(f'<text x="{xx}" y="{ly+4}" text-anchor="middle" font-size="12.5" fill="#6f6a5c">{d(r["gesprek_d"])}</text>')
        s.append(f'<circle cx="{xx}" cy="{ym}" r="8" fill="#38b6ff" stroke="#f8f4eb" stroke-width="2"><title>{name}: {d(r["gesprek_d"])}</title></circle>')
    s.append('</svg>')
    return ''.join(s)


def svg_prijs(c, w=1136, h=150):
    rows = [('Pilot', c['pilot_per_afspraak'], False)] + \
           [(f'{o["beldagen"]} beldagen', o['per_afspraak'], o['aanbevolen']) for o in c['opties']]
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, Liberation Sans, sans-serif">']
    colw = (w - 3 * 18) / 4
    maxv = 360
    for i, (lab, v, aan) in enumerate(rows):
        x0 = i * (colw + 18)
        bw = colw * v / maxv
        col = '#38b6ff' if aan else ('#b9b09b' if i == 0 else '#000')
        s.append(f'<rect x="{x0}" y="40" width="{colw}" height="26" rx="6" fill="#e4dcc8"/>')
        s.append(f'<rect x="{x0}" y="40" width="{bw}" height="26" rx="6" fill="{col}"><title>{lab}: {euro(v)} per afspraak</title></rect>')
        s.append(f'<text x="{x0}" y="26" font-size="14" fill="#6f6a5c">{lab}</text>')
        s.append(f'<text x="{x0}" y="100" font-size="26" font-weight="800" fill="#1c2230">{euro(v)}</text>')
        s.append(f'<text x="{x0}" y="122" font-size="13" fill="#6f6a5c">per afspraak</text>')
    s.append('</svg>')
    return ''.join(s)


# --- slides ---------------------------------------------------------------------
def slides(c):
    S = []
    wp = lambda n: len(c['per_wp'][n])
    o4, o6, o8 = c['opties']

    # 1 Titel: de lijn van de pilot loopt door naar het vervolg
    vals = [len(c['per_wp'][n]) for n, _, _ in C.WP]
    tw, th = 470, 250
    px = [40, 150, 260, 420]
    py = lambda v: th - 40 - v * 13
    pts = list(zip(px[:3], [py(v) for v in vals]))
    traj = [f'<svg width="{tw}" height="{th}" viewBox="0 0 {tw} {th}" xmlns="http://www.w3.org/2000/svg" font-family="Helvetica, Arial, Liberation Sans, sans-serif">']
    traj.append(f'<line x1="20" x2="{tw-10}" y1="{th-40}" y2="{th-40}" stroke="#ffffff" stroke-opacity=".18" stroke-width="1"/>')
    traj.append(f'<line x1="20" x2="{tw-10}" y1="{py(C.PILOT["doel_wp"])}" y2="{py(C.PILOT["doel_wp"])}" stroke="#ffffff" stroke-opacity=".28" stroke-width="1" stroke-dasharray="3 5"/>')
    traj.append(f'<text x="{tw-10}" y="{py(C.PILOT["doel_wp"])-8}" text-anchor="end" font-size="11" fill="#8a8a8a" letter-spacing="1.5">DOEL {C.PILOT["doel_wp"]}</text>')
    traj.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="#ffffff" stroke-width="2"/>')
    traj.append(f'<line x1="{pts[2][0]}" y1="{pts[2][1]}" x2="{px[3]}" y2="{py(12)}" stroke="#38b6ff" stroke-width="2" stroke-dasharray="6 6"/>')
    for (x, y), v, (n, _, _) in zip(pts, vals, C.WP):
        traj.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#000" stroke="#ffffff" stroke-width="2"/>')
        traj.append(f'<text x="{x}" y="{y-14}" text-anchor="middle" font-size="15" font-weight="700" fill="#ffffff">{v}</text>')
        traj.append(f'<text x="{x}" y="{th-18}" text-anchor="middle" font-size="11" fill="#8a8a8a" letter-spacing="1.5">{n}</text>')
    traj.append(f'<circle cx="{px[3]}" cy="{py(12)}" r="7" fill="#38b6ff"/>')
    traj.append(f'<text x="{px[3]}" y="{th-18}" text-anchor="middle" font-size="11" fill="#38b6ff" letter-spacing="1.5">26-10</text>')
    traj.append(f'<text x="{px[3]-14}" y="{py(12)+5}" text-anchor="end" font-size="13" font-weight="700" fill="#38b6ff">het vervolg</text>')
    traj.append(f'<text x="20" y="14" font-size="11" fill="#8a8a8a" letter-spacing="1.5">LEADS EN AFSPRAKEN PER WERKPERIODE</text>')
    traj.append('</svg>')
    S.append(f'''<section class="slide dark" id="s1" style="padding:0;background:#000">
<div style="position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);background-size:80px 80px"></div>
<div style="position:absolute;right:-260px;bottom:-320px;width:900px;height:900px;border-radius:50%;background:radial-gradient(circle, rgba(56,182,255,.30) 0%, rgba(56,182,255,.08) 38%, rgba(0,0,0,0) 68%)"></div>
<div style="position:absolute;left:88px;right:88px;top:60px;display:flex;justify-content:space-between;align-items:center">
  {logo(30, True)}
  <span style="font-size:12px;letter-spacing:.22em;color:#9a9a9a">PILOTEVALUATIE  ·  15-10-2026</span>
</div>
<div style="position:absolute;left:88px;top:232px;width:640px">
  <div style="font-size:78px;font-weight:800;line-height:.98;letter-spacing:-2.5px;color:#fff">OK Creative<br>Agency <span style="font-weight:300;color:#38b6ff">x</span> {logo(56, True, 'margin-left:6px')}</div>
  <div class="serif" style="font-size:30px;margin-top:22px;color:#fff">Van kennismaken naar een vaste samenwerking.</div>
</div>
<div style="position:absolute;right:76px;top:226px">{''.join(traj)}</div>
<div style="position:absolute;left:88px;right:88px;bottom:54px;border-top:1px solid rgba(255,255,255,.18);padding-top:16px;display:flex;justify-content:space-between;font-size:14px;color:#9a9a9a">
  <span>Google Meet  ·  10:00</span><span>Rob Hoogeveen, Mees Hoogeveen en Hens Boer</span><span>www.linkgrp.nl</span>
</div></section>''')

    # 2 Agenda
    ag = [('De afspraak en de cijfers', 'Wat we afspraken en wat er is geleverd', 10),
          ('Wat de gesprekken opleveren', 'Gehouden gesprekken, Moyee Coffee en de pijplijn', 10),
          ('Wat we geleerd hebben', 'Tien weken bellen voor OK: wat werkt en wat minder', 10),
          ('Waarom de kwaliteit omhoog gaat', 'En hoe we vanaf nu samenwerken', 10),
          ('Het vervolg vanaf 26-10-2026', 'Beldagen, KPI, drie opties en onze garantie', 15),
          ('Volgende stappen', 'Akkoord, overeenkomst en start', 5)]
    rows = ''.join(f'''<div style="display:flex;align-items:center;padding:13px 0;border-bottom:1px solid #d6ccb6">
<span class="serif blue" style="font-size:26px;width:56px">{i+1:02d}</span>
<span style="font-size:21px;font-weight:700;width:430px">{a}</span><span style="font-size:16px;color:#6f6a5c;flex:1">{b}</span>
<span style="font-size:15px;color:#6f6a5c">{m} min</span></div>''' for i, (a, b, m) in enumerate(ag))
    S.append(slide(2, 'Agenda', 'In een uur van terugblik naar een vaste samenwerking.', rows))

    # 3 De afspraak van de pilot
    body = f'''<div class="row" style="margin-bottom:18px">
<div class="card col"><div class="lbl">Belstart</div><div class="big" style="font-size:44px">{d(C.BELSTART)}</div><div class="sub">Bellen namens OK, in de naam van OK</div></div>
<div class="card col"><div class="lbl">Looptijd</div><div class="big" style="font-size:44px">3 x 4 weken</div><div class="sub">{' · '.join(f'{n} {s:%d-%m} t/m {e:%d-%m}' for n, s, e in C.WP)}</div></div>
<div class="card col"><div class="lbl">Investering</div><div class="big" style="font-size:44px">{euro(c['pilot_totaal'])}</div><div class="sub">{euro(C.PILOT['prijs_wp'])} per werkperiode</div></div>
</div>
<div class="row">
<div class="card col"><div class="lbl">Doel</div><div class="big" style="font-size:44px">{c['doel_totaal']} afspraken</div><div class="sub">{C.PILOT['doel_wp']} per werkperiode</div></div>
<div class="card black col"><div class="lbl">Prijs per afspraak</div><div class="big blue" style="font-size:44px">{euro(c['pilot_per_afspraak'])}</div><div class="sub">{euro(C.PILOT['prijs_wp'])} gedeeld door {C.PILOT['doel_wp']} afspraken</div></div>
<div class="card col"><div class="lbl">Doelgroep</div><p style="margin:0;font-size:16px">Zakelijke dienstverlening: IT, accountancy, verzekeringen, detachering en advies. Vanaf 50 medewerkers. Beslisser is directie, MT of marketing en brand.</p></div>
</div>'''
    S.append(slide(3, 'De afspraak', 'We spraken een pilot af van drie werkperiodes, met een helder doel per periode.', body))

    # 4 In cijfers
    body = f'''<div class="row" style="margin-bottom:18px">
<div class="card col"><div class="big">{num(c['pogingen'])}</div><div class="cap">contactpogingen</div><div class="sub">van 03-08 tot en met 14-10-2026</div></div>
<div class="card col"><div class="big">{num(c['calls'])}</div><div class="cap">keer iemand aan de lijn</div><div class="sub">{c['bereik']}% van alle pogingen</div></div>
<div class="card col"><div class="big">{num(c['gesproken'])}</div><div class="cap">bedrijven gesproken</div><div class="sub">uniek, na ontdubbelen</div></div>
</div>
<div class="row">
<div class="card black col" style="flex:1.2"><div class="big blue" style="font-size:84px">{c['n_leads']}</div><div class="cap">leads en afspraken voor OK</div><div class="sub">{pct(c['n_leads'], c['doel_totaal'])}% van het doel van {c['doel_totaal']}, met nog anderhalve week te gaan. {c['n_afspraak']} afspraken en {c['n_lead']} leads.</div></div>
<div class="card col"><div class="big">{c['terugbel_open']}</div><div class="cap">terugbelafspraken lopen nog</div><div class="sub">beslissers die later in gesprek willen</div></div>
<div class="card col"><div class="big">{len(c['gepland'])}</div><div class="cap">gesprekken en contactmomenten gepland</div><div class="sub">tot en met {d(c['gepland'][-1]['gesprek_d'])}</div></div>
</div>
<div class="note" style="margin-top:14px">Stand 14-10-2026. Bronnen: Belstat en het OK-portaal. TC Productions telt niet mee, die lead was al bekend bij OK.</div>'''
    S.append(slide(4, 'In cijfers', f'In tien weken spraken we {num(c["gesproken"])} bedrijven en leverden we {c["n_leads"]} leads en afspraken op.', body))

    # 5 Per werkperiode
    wb = c['wp_bel']
    body = f'''<div class="row" style="align-items:stretch">
<div class="card" style="flex:1.45;padding:18px 20px 6px">{svg_wp(c)}</div>
<div class="col" style="display:flex;flex-direction:column;gap:16px">
 <div class="card black"><div class="lbl">Totaal tot nu toe</div><div class="big blue">{c['n_leads']} <span style="font-size:30px;color:#fff">van {c['doel_totaal']}</span></div><div class="sub">WP3 loopt nog tot en met 25-10-2026</div></div>
 <div class="card" style="flex:1"><div class="lbl">De trend</div><p style="margin:0;font-size:16px">WP2 bleef achter met {wp('WP2')}: de lijst bevatte veel holdings en bedrijven die niet pasten. In WP3 bellen we met de Frits-insteek en scherpere lijsten, en zitten we na 2,5 week al op {wp('WP3')}.</p></div>
</div></div>
<div class="note" style="margin-top:12px">Geteld op aanmaakdatum van de lead in het OK-portaal, exclusief TC Productions.</div>'''
    S.append(slide(5, 'Resultaten per werkperiode', f'WP3 zit met {wp("WP3")} leads en afspraken al boven het doel van {C.PILOT["doel_wp"]}.', body))

    # 6 Wat de gesprekken opleveren
    order = ['Offerte maken', 'Vervolg gepland', 'Gekwalificeerd', 'Geen match']
    geh = sorted(c['gehouden'], key=lambda r: order.index(r['status']))
    cards = ''.join(f'''<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 0;border-bottom:1px solid #ddd3bd">
<div><div style="font-size:19px;font-weight:700">{r['bedrijf']}</div><div class="note">gesprek {d(r['gesprek_d'])}</div></div>
<span class="chip {'ok' if C.UITKOMST[r['status']][1] else 'neutral'}">{C.UITKOMST[r['status']][0]}</span></div>''' for r in geh)
    stap = lambda n, l, s, hl=False: f'<div class="card{" black" if hl else ""}" style="flex:1;text-align:left"><div class="big{" blue" if hl else ""}">{n}</div><div class="cap">{l}</div><div class="sub">{s}</div></div>'
    body = f'''<div class="row" style="align-items:stretch">
<div class="col" style="display:flex;flex-direction:column;gap:14px">
 <div class="row">{stap(c['n_leads'], 'geleverd', 'leads en afspraken')}{stap(len(c['gehouden']), 'gehouden', 'gesprek heeft plaatsgevonden')}{stap(len(c['met_resultaat']), 'met resultaat', 'offerte of vervolggesprek', True)}</div>
 <div class="card" style="flex:1"><div class="lbl">Nog te gaan</div><p style="margin:0;font-size:16px">{len(c['gepland'])} gesprekken en contactmomenten staan gepland. {c['open_lead'][0]['bedrijf']} wil eerst de punten van Frits per mail ontvangen en bespreekt die intern.</p></div>
</div>
<div class="card" style="flex:1.05;padding:14px 24px"><div class="lbl" style="margin-top:6px">Status per gehouden gesprek</div>{cards}</div>
</div>'''
    S.append(slide(6, 'Wat de gesprekken opleveren', f'Van de {len(c["gehouden"])} gehouden gesprekken leverden er {len(c["met_resultaat"])} een concreet vervolg op.', body))

    # 7 Moyee
    m = c['moyee']
    stap = lambda dd, t, s, hl=False: f'''<div style="flex:1;position:relative;padding-top:34px">
<div style="position:absolute;top:0;left:0;width:22px;height:22px;border-radius:50%;background:{'#38b6ff' if hl else '#000'}"></div>
<div style="font-size:15px;color:#6f6a5c">{dd}</div><div style="font-size:21px;font-weight:800;margin-top:4px">{t}</div><div class="sub">{s}</div></div>'''
    body = f'''<div class="card" style="margin-bottom:18px;padding:26px 30px">
<div style="position:relative"><div style="position:absolute;top:10px;left:10px;right:40px;height:2px;background:#1c2230"></div>
<div class="row" style="gap:30px">{stap(d(m['aangemaakt']), 'Afspraak ingepland', 'Lead aangemaakt in het OK-portaal, in werkperiode 2')}{stap(d(m['gesprek_d']), 'Gesprek gehouden', 'Kennismaking met OK, het FairChain-verhaal als kern')}{stap('nu', 'Offerte in de maak', 'OK werkt een offerte uit in twee varianten', True)}</div></div></div>
<div class="row">
<div class="card black col"><div class="lbl">De offerte</div><div class="big blue" style="font-size:44px">2 varianten</div><div class="sub">Op basis van een traject van {euro(c['tarief_moyee'])}, met korting omdat Moyee al veel heeft aangeleverd</div></div>
<div class="card col"><div class="lbl">Investering hele pilot</div><div class="big" style="font-size:44px">{euro(c['pilot_totaal'])}</div><div class="sub">3 werkperiodes van {euro(C.PILOT['prijs_wp'])}</div></div>
<div class="card col"><div class="lbl">En daarna</div><div class="big" style="font-size:44px">Lange termijn</div><div class="sub">Er ligt ook een kans op een doorlopende samenwerking</div></div>
</div>'''
    S.append(slide(7, 'Uitgelicht: Moyee Coffee', 'Eén lead kan meer opleveren dan de hele pilot: Moyee Coffee krijgt een offerte in twee varianten.', body))

    # 8 Pijplijn
    body = f'''<div class="card" style="padding:16px 20px 8px">{svg_timeline(c)}</div>
<div class="row" style="margin-top:16px">
<div class="card col" style="padding:16px 22px"><span class="big" style="font-size:36px">{len(c['gepland'])}</span> <span class="cap">gepland, waarvan {sum(r['gesprek_d'] < C.dt.date(2027,1,1) for r in c['gepland'])} nog in 2026</span></div>
<div class="card col" style="padding:16px 22px"><span class="big" style="font-size:36px">{c['terugbel_open']}</span> <span class="cap">terugbelafspraken lopen daarnaast</span></div>
</div>'''
    S.append(slide(8, 'De pijplijn', f'De meeste waarde moet nog komen: tot en met maart 2027 staan nog {len(c["gepland"])} gesprekken en contactmomenten gepland.', body))

    # 9 Wat werkt
    werkt = [('De insteek met Frits', '“Frits, oprichter en al zo’n 30 jaar merkstrateeg, volgt jullie al langer en heeft een aantal punten voorbereid over jullie communicatie naar buiten.” We komen iets brengen in plaats van iets vragen.'),
             ('Niet weggeven aan de telefoon', 'De punten bewaren we voor het gesprek. We stellen direct twee momenten voor.'),
             ('Vooraf de beslisser opzoeken', 'Per bedrijf zoeken we op wie over marketing en communicatie gaat, en we vragen gericht naar die persoon.'),
             ('Mail als tussenstap', 'Een intro per mail is een geldige stap. Binnen 3 werkdagen bellen we na.'),
             ('De juiste snaar per organisatie', 'Elke organisatie vraagt een eigen haakje. Randstad Groep is het voorbeeld: de marketeer kende OK al en wil kijken wat OK kan betekenen voor hun campagnes en vacatures.')]
    cards = ''.join(f'<div class="card" style="flex:1;padding:20px"><div class="serif blue" style="font-size:24px">{i+2:02d}</div><div style="font-size:18px;font-weight:800;margin:6px 0 8px">{a}</div><div style="font-size:14.5px;line-height:1.5">{b}</div></div>' for i, (a, b) in enumerate(werkt[1:]))
    body = f'''<div class="card black" style="margin-bottom:16px;padding:22px 28px;display:flex;gap:26px;align-items:center">
<div class="serif blue" style="font-size:30px">01</div><div><div style="font-size:20px;font-weight:800;margin-bottom:6px">{werkt[0][0]}</div><div style="font-size:17px;line-height:1.5;color:#e6e6e6">{werkt[0][1]}</div></div></div>
<div class="row" style="gap:14px">{cards}</div>'''
    S.append(slide(9, 'Wat we geleerd hebben', 'We komen iets brengen in plaats van iets vragen, en dat werkt.', body))

    # 10 Wat minder werkt
    minder = [('De receptie als drempel', 'We vragen gericht naar de persoon die we vooraf hebben opgezocht, en gebruiken mail als tweede ingang.'),
              ('De nieuwe naam is nog onbekend', 'We zeggen “OK Creative Agency, voorheen Onze Kapel”. Dat geeft direct herkenning.'),
              ('Brede lijsten met holdings', 'We bellen alleen zelfstandige Nederlandse vestigingen, zonder holdings, buitenlandse hoofdkantoren of dubbele records.'),
              ('“We doen alles zelf”', 'We vragen door. Vrijwel niemand heeft echt alles in huis, en daar zit de ingang voor OK.')]
    rows = ''.join(f'<div style="display:flex;gap:18px;padding:12px 0;border-bottom:1px solid #ddd3bd"><div style="width:250px;font-size:17px;font-weight:800">{a}</div><div style="flex:1;font-size:15.5px;line-height:1.45"><span class="blue" style="font-weight:700">Wat we doen: </span>{b}</div></div>' for a, b in minder)
    wb = c['wp_bel']
    body = f'''<div class="row" style="align-items:stretch">
<div class="card" style="flex:1.35;padding:14px 24px">{rows}</div>
<div class="card col"><div class="lbl">Het effect van scherpere lijsten</div><div style="font-size:15px;margin-bottom:14px">Aandeel gesproken bedrijven dat niet bij OK paste</div>{svg_niet_geschikt(c)}
<div class="note">{wb['WP1']['niet_geschikt']} van {wb['WP1']['gesproken']} in WP1, {wb['WP2']['niet_geschikt']} van {wb['WP2']['gesproken']} in WP2, {wb['WP3']['niet_geschikt']} van {wb['WP3']['gesproken']} in WP3. Ingedeeld op datum van het laatste contact.</div></div>
</div>'''
    S.append(slide(10, 'Wat minder werkt', 'Waar het schuurde, hebben we de aanpak al aangepast.', body))

    # 11 Waarom de kwaliteit omhoog gaat
    l1, l2 = c['lijst']['OK Project 1'], c['lijst']['OK Project 2']
    punten = [('We kennen het verhaal van OK', 'De propositie, de cases en de toon. We vertellen het nu zoals OK het zelf vertelt.'),
              ('De Frits-insteek is bewezen', f'Sinds WP3 de vaste opening. Resultaat: {wp("WP3")} leads en afspraken in 2,5 week.'),
              ('Scherpere lijsten', 'We weten wie de beslisser is en welke bedrijven passen. Alleen zelfstandige Nederlandse vestigingen.'),
              ('New Business-lijsten van OK', 'OK levert warme contacten aan uit websitebezoekers en LinkedIn. De basisdata regelen wij. Warmere contacten geven betere gesprekken.'),
              ('Een uitsluitlijst', 'Wat OK zelf al benadert, bellen wij niet. Nooit dubbel aan de lijn.'),
              ('Een vaste feedbackloop', 'Elke vrijdag de rapportage naar Mees, met een lijst van gebelde bedrijven en de uitkomst. OK ziet wat werkt en stuurt mee.'),
              ('Een duo naar elke afspraak', 'Bij OK gaan een ervaren en een jonge collega samen. Dat geeft betere opvolging van wat wij inplannen.')]
    cards = ''.join(f'<div class="card" style="width:calc(25% - 11px);padding:16px 18px"><div class="serif blue" style="font-size:20px">{i+1:02d}</div><div style="font-size:16px;font-weight:800;margin:4px 0 6px">{a}</div><div style="font-size:13.5px;line-height:1.45">{b}</div></div>' for i, (a, b) in enumerate(punten))
    proof = f'''<div class="card black" style="width:calc(25% - 11px);padding:16px 18px"><div class="lbl">Bewijs uit de pilot</div>
<div style="font-size:42px;font-weight:800;color:#38b6ff;line-height:1">{str(l2['pct']).replace('.', ',')}%</div><div style="font-size:13.5px;margin:4px 0 8px">van de gesproken bedrijven op de lijst van OK met relaties en gewenste klanten werd een lead</div>
<div style="font-size:24px;font-weight:800;line-height:1">{str(l1['pct']).replace('.', ',')}%</div><div style="font-size:13.5px;color:#bdbdbd">op de brede lijst</div></div>'''
    body = f'<div style="display:flex;flex-wrap:wrap;gap:14px">{cards}{proof}</div>'
    S.append(slide(11, 'Waarom de kwaliteit omhoog gaat', 'De kwaliteit gaat omhoog, omdat we OK, het verhaal en de markt nu veel beter kennen.', body))

    # 12 Samenwerking
    blok = [('Vast aanspreekpunt', 'Mees Hoogeveen is vanaf nu ons vaste aanspreekpunt bij OK.'),
            ('Elke vrijdag de rapportage', 'Cijfers, wat werkt, wat we terughoren en de warme leads. Plus de lijst met gebelde bedrijven en hun uitkomst.'),
            ('Lijsten van OK', 'OK levert New Business-lijsten met warme contacten aan, wij regelen de basisdata. In de weekrapportage geven we per lead terugkoppeling.'),
            ('Uitsluitlijst', 'OK geeft door wie het zelf benadert. Die bedrijven slaan wij over.'),
            ('Evaluatie na werkperiode 4', 'Samen kijken we naar de cijfers, de kwaliteit van de afspraken en de doelgroep. Daarna eventueel uitbreiden naar musea en evenementen.')]
    rows = ''.join(f'<div class="card" style="flex:1;padding:20px"><div class="serif blue" style="font-size:24px">{i+1:02d}</div><div style="font-size:18px;font-weight:800;margin:6px 0 8px">{a}</div><div style="font-size:14.5px;line-height:1.5">{b}</div></div>' for i, (a, b) in enumerate(blok))
    flow = '''<div class="card black" style="margin-top:18px;display:flex;align-items:center;justify-content:space-between;padding:20px 30px;font-size:15px;font-weight:700">
<span>OK levert New Business-lijsten en uitsluitingen</span><span class="blue">→</span><span>LINK. belt en plant in</span><span class="blue">→</span><span>OK voert het gesprek, met een duo</span><span class="blue">→</span><span>vrijdag: rapportage en bijsturen</span></div>'''
    S.append(slide(12, 'Samenwerking vanaf nu', 'Vanaf nu werken we als één team, met Mees als vast aanspreekpunt.', f'<div class="row" style="gap:14px">{rows}</div>{flow}'))

    # 13 Het vervolg
    kpirow = ''.join(f'''<div class="card" style="flex:1;text-align:center;padding:22px">
<div style="font-size:15px;color:#a9a9a9">{o['beldagen']} beldagen x {C.KPI_PER_BELDAG}</div><div class="big blue" style="margin-top:6px">{o['kpi']}</div><div class="cap">afspraken per werkperiode</div></div>''' for o in c['opties'])
    body = f'''<div class="row" style="margin-bottom:18px">
<div class="card col"><div class="lbl">Eenheid</div><div style="font-size:30px;font-weight:800">Hele beldagen</div><div class="sub">1 beldag is {C.UREN_PER_BELDAG} uur bellen voor OK, per werkperiode van 4 weken</div></div>
<div class="card col"><div class="lbl">KPI</div><div style="font-size:30px;font-weight:800">{C.KPI_PER_BELDAG} afspraken per beldag</div><div class="sub">gekwalificeerde afspraken met een beslisser</div></div>
<div class="card col"><div class="lbl">Start</div><div style="font-size:30px;font-weight:800">{d(C.START_VERVOLG)}</div><div class="sub">direct na werkperiode 3, zonder gat</div></div>
</div>
<div class="row">{kpirow}</div>'''
    S.append(slide(13, 'Het vervolg', f'Vanaf {d(C.START_VERVOLG)} werken we in hele beldagen, met een KPI van {C.KPI_PER_BELDAG} afspraken per beldag.', body, dark=True))

    # 14 De opties
    def optie(titel, prijs, kpi, per, sub, cls='', badge=''):
        return f'''<div class="card {cls}" style="flex:1;padding:22px 22px 18px;position:relative">
{badge}<div style="font-size:20px;font-weight:800">{titel}</div><div class="sub" style="margin-top:2px">{sub}</div>
<div style="font-size:40px;font-weight:800;margin-top:14px;line-height:1">{euro(prijs)}</div><div class="sub">per 4 weken</div>
<div style="font-size:19px;font-weight:700;margin-top:12px">{kpi} afspraken</div>
<div style="font-size:15px;margin-top:10px;padding-top:10px;border-top:1px solid {'#333' if cls=='black' else '#ddd3bd'}"><b class="{'blue' if cls=='black' else ''}">{euro(per)}</b> per afspraak</div></div>'''
    cards = optie('Pilot', C.PILOT['prijs_wp'], C.PILOT['doel_wp'], c['pilot_per_afspraak'], 'ter vergelijking', 'pilot').replace('class="card pilot"', 'class="card" style="opacity:.6"')
    for o in c['opties']:
        if o['aanbevolen']:
            cards += optie(f'{o["beldagen"]} beldagen', o['prijs'], o['kpi'], o['per_afspraak'], f'{euro(o["per_beldag"])} per beldag', 'black',
                           '<span class="chip ok" style="position:absolute;top:-12px;right:18px">Aanbevolen</span>')
        else:
            cards += optie(f'{o["beldagen"]} beldagen', o['prijs'], o['kpi'], o['per_afspraak'], f'{euro(o["per_beldag"])} per beldag')
    body = f'''<div class="row" style="gap:16px;margin-top:6px">{cards}</div>
<div class="card" style="margin-top:22px;padding:16px 24px;font-size:18px;font-weight:700">De prijs per afspraak daalt van {euro(c['pilot_per_afspraak'])} in de pilot naar <span class="blue">{euro(o6['per_afspraak'])}</span> bij {o6['beldagen']} beldagen en {euro(o8['per_afspraak'])} bij {o8['beldagen']} beldagen.</div>'''
    S.append(slide(14, 'De opties', f'Meer afspraken voor een lagere prijs per afspraak: wij adviseren {o6["beldagen"]} beldagen.', body))

    # 15 Garantie
    ex_n = o6['kpi'] - 2
    body = f'''<div class="row" style="align-items:stretch">
<div class="card black" style="flex:1.2;padding:30px 34px"><div class="lbl">Onze garantie</div>
<div style="font-size:30px;font-weight:800;line-height:1.25">Halen we in een werkperiode de KPI van {C.KPI_PER_BELDAG} afspraken per beldag niet, dan krijgt OK in de volgende werkperiode een beldag gratis.</div>
<div class="sub" style="font-size:16px;margin-top:18px">Voorbeeld: bij {o6['beldagen']} beldagen is de KPI {o6['kpi']} afspraken. Worden het er {ex_n}, dan bellen we de volgende werkperiode {o6['beldagen']+1} dagen voor de prijs van {o6['beldagen']}.</div></div>
<div class="col">
<div class="card" style="margin-bottom:16px"><div class="lbl">Wat telt als afspraak</div><p style="margin:0;font-size:16px">Een gekwalificeerde afspraak: de gesprekspartner is een beslisser (directie, MT of marketing en brand) bij een organisatie die in de afgesproken doelgroep past.</p></div>
<div class="card"><div class="lbl">Wat het voor OK betekent</div><p style="margin:0;font-size:16px">OK betaalt voor resultaat. Het risico van een tegenvallende periode ligt bij ons.</p></div>
</div></div>'''
    S.append(slide(15, 'Onze garantie', 'Halen we de KPI niet, dan krijgt OK een beldag gratis.', body))

    # 16 Volgende stappen
    stappen = [('15-10-2026', 'Evaluatie', 'Vandaag: keuze voor het aantal beldagen'),
               ('Deze week', 'Akkoord', 'OK bevestigt de keuze per mail aan Hens'),
               ('Voor 26-10', 'Overeenkomst', 'Op de Algemene Voorwaarden LINK. versie 5'),
               (d(C.START_VERVOLG), 'Start werkperiode 4', f'Loopt tot en met {d(c["wp4"][1])}'),
               (d(c['wp5_start']), 'Evaluatie na WP4', 'Cijfers, kwaliteit en doelgroep samen bekijken')]
    st = ''.join(f'''<div style="flex:1;position:relative;padding-top:40px">
<div style="position:absolute;top:0;left:0;width:26px;height:26px;border-radius:50%;background:{'#38b6ff' if i == 3 else '#000'}"></div>
<div style="font-size:15px;color:#6f6a5c">{a}</div><div style="font-size:21px;font-weight:800;margin-top:4px">{b}</div><div class="sub">{s}</div></div>''' for i, (a, b, s) in enumerate(stappen))
    body = f'''<div class="card" style="padding:30px 32px 26px;margin-bottom:18px"><div style="position:relative"><div style="position:absolute;top:12px;left:12px;right:60px;height:2px;background:#1c2230"></div><div class="row" style="gap:22px">{st}</div></div></div>
<div class="row">
<div class="card col"><div class="lbl">Opzegbaar</div><p style="margin:0;font-size:16px">Per werkperiode van 4 weken. Geen lange verplichting.</p></div>
<div class="card col"><div class="lbl">Doorlopend</div><p style="margin:0;font-size:16px">De pijplijn en de {c['terugbel_open']} terugbelafspraken lopen zonder onderbreking door.</p></div>
<div class="card black col"><div class="lbl">De vraag van vandaag</div><p style="margin:0;font-size:17px;font-weight:700">Starten we op {d(C.START_VERVOLG)} met {o6['beldagen']} of met {o8['beldagen']} beldagen?</p></div>
</div>'''
    S.append(slide(16, 'Volgende stappen', f'Met een akkoord deze week starten we op {d(C.START_VERVOLG)}, zonder gat na de pilot.', body))

    # Bijlage A: leads
    rws = ''
    for r in sorted(c['portaal'], key=lambda r: r['aangemaakt']):
        if r['gehouden']:
            st = C.UITKOMST[r['status']][0]
        elif r['gepland']:
            st = 'Gesprek gepland' if r['type'] == 'Afspraak' else 'Contactmoment gepland'
        else:
            st = 'Ontvangt eerst de punten per mail'
        cls = ' class="muted"' if not r['telt'] else ''
        wpn = r['wp'] if r['telt'] else 'telt niet mee'
        rws += f'<tr{cls}><td>{r["bedrijf"]}</td><td>{r["type"]}</td><td>{d(r["aangemaakt"])}</td><td>{wpn}</td><td>{r["gesprek_dt"]:%d-%m-%Y %H:%M}</td><td>{st}</td></tr>'
    body = f'''<div class="card" style="padding:12px 20px"><table class="t"><tr><th>Bedrijf</th><th>Type</th><th>Aangemaakt</th><th>Werkperiode</th><th>Gesprek</th><th>Status</th></tr>{rws}</table></div>
<div class="note" style="margin-top:8px">Bron: OK-portaal, stand 14-10-2026. TC Productions staat erin maar telt niet mee: die lead was al bekend bij OK. Totaal meetellend: {c['n_leads']}.</div>'''
    S.append(slide('A', 'Bijlage A', 'Alle leads en afspraken met hun status.', body).replace('<h2>', '<h2 style="font-size:28px;margin-bottom:12px">').replace('<div class="eyebrow">', '<div class="eyebrow" style="margin-top:14px">'))

    # Bijlage B: cijfers per werkperiode
    keys = [('Leads en afspraken (portaal)', None), ('Gesproken contactpersonen', 'gesproken'), ('waarvan niet passend', 'niet_geschikt'),
            ('waarvan geen interesse of al voorzien', 'geen_interesse'), ('waarvan terugbelafspraak', 'terugbel'), ('Informatiemail verstuurd', 'infomail')]
    rws = ''
    for lab, k in keys:
        vals = [len(c['per_wp'][n]) if k is None else wb[n][k] for n, _, _ in C.WP]
        rws += f'<tr><td>{lab}</td>' + ''.join(f'<td class="r">{num(v)}</td>' for v in vals) + f'<td class="r"><b>{num(sum(vals))}</b></td></tr>'
    rws += '<tr><td>Aandeel niet passend van gesproken</td>' + ''.join(f'<td class="r">{wb[n]["niet_geschikt_pct"]}%</td>' for n, _, _ in C.WP) + f'<td class="r">{pct(sum(wb[n]["niet_geschikt"] for n,_,_ in C.WP), sum(wb[n]["gesproken"] for n,_,_ in C.WP))}%</td></tr>'
    gsum = sum(wb[n]['gesproken'] for n, _, _ in C.WP)
    body = f'''<div class="row" style="align-items:flex-start">
<div class="card" style="flex:1.6;padding:12px 20px"><table class="t"><tr><th></th>{''.join(f'<th class="r">{n}</th>' for n,_,_ in C.WP)}<th class="r">Totaal</th></tr>{rws}</table>
<div class="note" style="margin-top:8px">Belstat, laatste status per record, ingedeeld op datum van het laatste contact. {gsum} gesproken contactpersonen bij {c['gesproken']} unieke bedrijven. Een uitsplitsing per week is in deze export niet beschikbaar.</div></div>
<div class="col">
<div class="card" style="margin-bottom:14px"><div class="lbl">Hele pilot</div><table class="t">
<tr><td>Contactpogingen</td><td class="r">{num(c['pogingen'])}</td></tr>
<tr><td>Iemand aan de lijn</td><td class="r">{num(c['calls'])}</td></tr>
<tr><td>Bereik</td><td class="r">{c['bereik']}%</td></tr>
<tr><td>Unieke bedrijven gesproken</td><td class="r">{num(c['gesproken'])}</td></tr>
<tr><td>Terugbelafspraken open</td><td class="r">{c['terugbel_open']}</td></tr></table></div>
<div class="card"><div class="lbl">Vooraf uitgesloten</div><p style="margin:0;font-size:14px">{c['uitgesloten_vooraf']} bestaande relaties van OK zijn op 24-07-2026 uit de lijst gehaald en niet gebeld.</p></div>
</div></div>'''
    S.append(slide('B', 'Bijlage B', 'De belcijfers per werkperiode.', body).replace('<h2>', '<h2 style="font-size:28px;margin-bottom:12px">').replace('<div class="eyebrow">', '<div class="eyebrow" style="margin-top:14px">'))
    return S


def deck_html(c):
    return (f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=1320">'
            f'<title>Pilotevaluatie OK Creative Agency</title><style>{CSS_DECK}</style></head><body>'
            + ''.join(slides(c)) + '</body></html>')


# --- sprekersnotities ------------------------------------------------------------
def notities(c):
    wp = lambda n: len(c['per_wp'][n])
    o4, o6, o8 = c['opties']
    m = c['moyee']
    N = [
        (1, 'Titel', 'Welkom. Dit is de eerste keer dat jullie het hele beeld zien, dus we nemen de tijd.',
         ['Bedank Rob en Mees voor de tijd. Benoem dat Mees vanaf nu het vaste aanspreekpunt is.',
          'Zet de toon: jullie zien de eerste drie maanden als kennismaken. Wij ook. Vandaag gaat het over de stap naar een vaste samenwerking.'],
         'Hoe kijken jullie zelf terug op de afspraken die tot nu toe zijn ingepland?', 'Geen getal. Laat hen eerst praten.'),
        (2, 'Agenda', 'Een uur, zes onderdelen, en aan het eind een keuze.',
         ['Loop de agenda kort door. Zeg vooraf dat we eindigen met het vervolg en een concrete keuze.'],
         'Is er iets wat jullie vandaag zeker besproken willen hebben?', '60 minuten, het vervolg krijgt de meeste tijd.'),
        (3, 'De afspraak', 'Dit spraken we af, zodat we eerlijk kunnen afrekenen.',
         ['Belstart 03-08-2026, drie werkperiodes van 4 weken.', f'{euro(C.PILOT["prijs_wp"])} per werkperiode, {euro(c["pilot_totaal"])} totaal. Doel {C.PILOT["doel_wp"]} per periode, {c["doel_totaal"]} totaal.',
          'Doelgroep zakelijke dienstverlening vanaf 50 medewerkers, beslisser directie, MT of marketing.'],
         None, f'{euro(c["pilot_per_afspraak"])} per afspraak. Daar vergelijken we straks het vervolg mee.'),
        (4, 'In cijfers', 'Er is hard gewerkt en het levert op.',
         [f'{num(c["pogingen"])} contactpogingen, {num(c["calls"])} keer iemand aan de lijn, {num(c["gesproken"])} unieke bedrijven gesproken.',
          f'{c["n_leads"]} leads en afspraken: {c["n_afspraak"]} afspraken en {c["n_lead"]} leads. Dat is {pct(c["n_leads"], c["doel_totaal"])}% van het doel, en WP3 loopt nog anderhalve week.',
          f'Daarnaast lopen {c["terugbel_open"]} terugbelafspraken: beslissers die later in gesprek willen.',
          'TC Productions tellen we bewust niet mee, die kende OK al.'],
         None, f'{c["n_leads"]} leads en afspraken, en {len(c["gepland"])} gesprekken en contactmomenten die nog komen.'),
        (5, 'Per werkperiode', 'Eerlijk: WP2 bleef achter. WP3 laat zien wat de nieuwe insteek doet.',
         [f'WP1 {wp("WP1")}, WP2 {wp("WP2")}, WP3 nu al {wp("WP3")}.',
          'WP2: de lijst had te veel holdings en bedrijven die niet pasten. Dat hebben we aangepakt.',
          f'WP3: Frits-insteek en scherpere lijsten. {wp("WP3")} leads en afspraken in 2,5 week, boven het doel van {C.PILOT["doel_wp"]}. Daarvan zijn {sum(r["type"]=="Afspraak" for r in c["per_wp"]["WP3"])} afspraken en {sum(r["type"]=="Lead" for r in c["per_wp"]["WP3"])} leads, zeg dat er eerlijk bij als ernaar gevraagd wordt.'],
         None, f'{wp("WP3")} in WP3, met nog anderhalve week te gaan.'),
        (6, 'Wat de gesprekken opleveren', 'Het gaat niet om afspraken, het gaat om wat ze opleveren.',
         [f'{len(c["gehouden"])} gesprekken zijn al gehouden. {len(c["met_resultaat"])} daarvan leverden een concreet vervolg op: een offerte en twee vervolggesprekken.',
          'Alle leads zijn gekwalificeerd, dus dat noemen we niet als uitkomst. Bij Danieli Corus ligt een concreet vraagstuk rond hun corporate presentaties.',
          'BNU Groep was geen match. Dat hoort erbij en het helpt ons scherper te kiezen.',
          f'{len(c["gepland"])} gesprekken en contactmomenten moeten nog komen. Rotterdam Leisure Group en Safecourt zijn contactmomenten, de rest zijn afspraken.'],
         'Doorvragen: wat zijn de vervolggesprekken met Zorgwerk en AAme waard voor jullie? Wat is een gemiddelde opdracht bij een klant als Danieli Corus?',
         f'{len(c["met_resultaat"])} van de {len(c["gehouden"])}.'),
        (7, 'Moyee Coffee', 'Eén lead kan de hele pilot terugverdienen, en meer.',
         [f'Afspraak ingepland op {d(m["aangemaakt"])}, gesprek op {d(m["gesprek_d"])}. OK maakt nu een offerte in twee varianten, af te ronden rond 17-10.',
          f'Basis is het OK-tarief van {euro(c["tarief_moyee"])} voor een middelgroot traject. Moyee krijgt korting, omdat ze al veel hadden aangeleverd.',
          f'Ook met korting is één opdracht al snel meer dan de {euro(c["pilot_totaal"])} van de hele pilot. Noem geen bedrag dat OK zelf nog niet heeft genoemd.',
          'Niet overdrijven: het is een offerte, nog geen opdracht.'],
         'Doorvragen: wat wordt het bedrag van de offerte, en hoe groot is de kans dat Moyee tekent? En als dit het niveau is, wat is dan één extra afspraak per maand waard?',
         f'Eén lead tegenover {euro(c["pilot_totaal"])} voor de hele pilot.'),
        (8, 'De pijplijn', 'De meeste waarde van de pilot moet nog komen.',
         ['Loop de tijdlijn van links naar rechts: ' + ', '.join(f'{r["bedrijf"]} {d(r["gesprek_d"])}' for r in c['gepland']) + '.',
          'Benoem ING en Randstad Groep als grote namen. Safecourt pakt OK begin januari zelf op.',
          'Als we stoppen na WP3, lopen deze gesprekken wel door, maar komt er niets nieuws bij. Daarom willen we zonder gat door.'],
         None, f'{len(c["gepland"])} gesprekken gepland, tot en met {d(c["gepland"][-1]["gesprek_d"])}.'),
        (9, 'Wat werkt', 'We hebben de opening gevonden die werkt voor OK.',
         ['Lees de Frits-opening letterlijk voor. Leg uit waarom die werkt: we komen iets brengen.',
          'We geven de punten niet weg aan de telefoon en stellen direct twee momenten voor.',
          'Randstad Groep als voorbeeld: de marketeer kende OK al en wil weten wat OK kan betekenen voor campagnes en vacatures.'],
         'Herkennen jullie dit in de gesprekken die jullie hebben gevoerd?', None),
        (10, 'Wat minder werkt', 'We benoemen wat schuurde, en laten zien wat we al hebben veranderd.',
         ['Receptie, nieuwe naam, brede lijsten en het bezwaar dat ze alles zelf doen.',
          f'Het effect van scherpere lijsten: het aandeel gesprekken dat niet bij OK paste daalde van {c["wp_bel"]["WP1"]["niet_geschikt_pct"]}% in WP1 en {c["wp_bel"]["WP2"]["niet_geschikt_pct"]}% in WP2 naar {c["wp_bel"]["WP3"]["niet_geschikt_pct"]}% in WP3.'],
         'Mogen we in het gesprek vaker "voorheen Onze Kapel" gebruiken?', f'Van {c["wp_bel"]["WP1"]["niet_geschikt_pct"]}% naar {c["wp_bel"]["WP3"]["niet_geschikt_pct"]}% niet passend.'),
        (11, 'Waarom de kwaliteit omhoog gaat', 'Vertrouwen: het vervolg wordt beter dan de pilot.',
         ['Loop de zeven punten kort door, de nadruk op de New Business-lijsten en de feedbackloop.',
          'OK levert soms New Business-lijsten aan, de basisdata regelen wij. Die leads zijn warm en fijn om te bellen, en we koppelen ze voortaan structureel terug in de rapportage.',
          f'Bewijs: van de gesproken bedrijven op de lijst van OK met relaties en gewenste klanten werd {str(c["lijst"]["OK Project 2"]["pct"]).replace(".", ",")}% een lead, op de brede lijst {str(c["lijst"]["OK Project 1"]["pct"]).replace(".", ",")}%. Warmere lijsten werken.',
          'Het duo bij OK: dat is hun eigen verbetering. Benoem het als sterk punt.'],
         'Hoe vaak kunnen jullie de New Business-lijst aanvullen met websitebezoekers en LinkedIn? Wij geven er in de weekrapportage structureel terugkoppeling op.',
         f'{str(c["lijst"]["OK Project 2"]["pct"]).replace(".", ",")}% tegenover {str(c["lijst"]["OK Project 1"]["pct"]).replace(".", ",")}%.'),
        (12, 'Samenwerking', 'Zo werken we vanaf nu samen.',
         ['Mees is het vaste aanspreekpunt. Elke vrijdag de rapportage met de lijst van gebelde bedrijven.',
          'Uitsluitlijst: wat OK zelf benadert, bellen wij niet.', 'Na WP4 evalueren we, en kijken we of musea en evenementen erbij kunnen.'],
         'Mees, past vrijdag voor jou als vast moment?', None),
        (13, 'Het vervolg', 'We gaan van een pilot naar een vaste eenheid: de beldag.',
         [f'Vanaf {d(C.START_VERVOLG)}, direct na WP3.', f'KPI: {C.KPI_PER_BELDAG} afspraken per beldag, dus {o4["kpi"]}, {o6["kpi"]} of {o8["kpi"]} per werkperiode.',
          'Achtergrond, niet delen: in de pilot is '
          f'{c["uren_record_txt"]} uur aan records gebeld, dat is {str(round(c["beldagen"],1)).replace(".", ",")} beldagen. '
          f'Gemiddeld {str(round(c["beldagen_per_lead"],2)).replace(".", ",")} lead per beldag over de hele pilot, inclusief de opstart. De pilot is per werkperiode afgerekend, niet per beldag.'],
         None, f'{C.KPI_PER_BELDAG} per beldag.'),
        (14, 'De opties', 'Meer afspraken, hogere kwaliteit, en de prijs per afspraak daalt.',
         [f'Pilot {euro(c["pilot_per_afspraak"])} per afspraak. 4 beldagen {euro(o4["per_afspraak"])}, 6 beldagen {euro(o6["per_afspraak"])}, 8 beldagen {euro(o8["per_afspraak"])}.',
          f'Ons advies is 6 beldagen: {o6["kpi"]} afspraken per werkperiode, dat is het dubbele van de pilot.',
          'Geen ja of nee vragen. Laat ze kiezen tussen 6 en 8.'],
         f'Willen jullie starten met {o6["beldagen"]} beldagen, of meteen met {o8["beldagen"]} om het tempo van WP3 vast te houden?',
         f'{euro(o6["per_afspraak"])} per afspraak bij 6 beldagen, {o6["kpi"]} afspraken.'),
        (15, 'Garantie', 'Het risico ligt bij ons.',
         [f'Halen we de KPI van {C.KPI_PER_BELDAG} per beldag in een werkperiode niet, dan een beldag gratis in de volgende periode.',
          'Een afspraak telt als de gesprekspartner een beslisser is bij een organisatie in de doelgroep.', 'Opzegbaar per werkperiode.'],
         'Is er iets dat jullie nog nodig hebben om hier ja op te zeggen?', 'Een beldag gratis.'),
        (16, 'Volgende stappen', 'Concreet afsluiten.',
         [f'Akkoord deze week per mail, overeenkomst op de Algemene Voorwaarden LINK. versie 5, start {d(C.START_VERVOLG)}.',
          f'WP4 loopt tot en met {d(c["wp4"][1])}. Evaluatie in de week van {d(c["wp5_start"])}.', 'Zeg toe dat de one-pager vandaag naar Mees gaat.'],
         f'Zullen we {d(C.START_VERVOLG)} vastzetten met {o6["beldagen"]} of {o8["beldagen"]} beldagen?', f'Start {d(C.START_VERVOLG)}, zonder gat.'),
    ]
    blocks = ''
    for n, t, kern, zeg, vraag, nadruk in N:
        blocks += f'''<div class="nb"><div class="nh"><span class="nn">{n:02d}</span><span class="nt">{t}</span></div>
<div class="kern">{kern}</div><div class="lb">Wat ik zeg</div><ul>{''.join(f'<li>{x}</li>' for x in zeg)}</ul>
{f'<div class="lb">Vraag</div><p class="q">{vraag}</p>' if vraag else ''}
{f'<div class="lb">Nadruk op</div><p class="em">{nadruk}</p>' if nadruk else ''}</div>'''
    css = CSS_BASE + """
@page { size:A4; margin:1.4cm 1.5cm 1.3cm; background:#e9e0cd;
  @bottom-left { content:"LINK.   ·   Sprekersnotities pilotevaluatie OK   ·   intern"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; }
  @bottom-right { content: counter(page) "  /  " counter(pages); font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; } }
body { font-size:9.6pt; line-height:1.5; background:none; }
.hero { background:#000; color:#fff; margin:-1.4cm -1.5cm 16px; padding:26px 1.5cm 22px; }
.hero h1 { font-size:24pt; margin:6px 0 4px; } .hero .e { color:#38b6ff; font-size:8pt; font-weight:700; letter-spacing:.22em; }
.nb { background:#f8f4eb; border-radius:12px; padding:12px 16px; margin-bottom:10px; break-inside:avoid; }
.nh { display:flex; align-items:baseline; gap:10px; margin-bottom:4px; }
.nn { font-family:Georgia, serif; font-style:italic; color:#38b6ff; font-size:14pt; } .nt { font-weight:800; font-size:12pt; }
.kern { font-weight:700; margin-bottom:6px; }
.lb { color:#38b6ff; font-size:7.4pt; font-weight:700; letter-spacing:.14em; text-transform:uppercase; margin-top:6px; }
ul { margin:2px 0 0; padding-left:15px; } li { font-size:9.4pt; margin-bottom:3px; line-height:1.45; }
p { margin:2px 0 0; font-size:9.4pt; } .q { font-style:italic; } .em { font-weight:700; }
"""
    return (f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><title>Sprekersnotities pilotevaluatie OK</title><style>{css}</style></head><body>'
            f'<div class="hero">{logo(20, True)}<div class="e" style="margin-top:14px">SPREKERSNOTITIES  ·  INTERN</div>'
            f'<h1>Pilotevaluatie OK Creative Agency</h1><div style="font-size:9pt;color:#cfcfcf">15-10-2026, 10:00, Google Meet. Met Rob en Mees Hoogeveen. Per slide: wat ik zeg, welke vraag ik stel en waar de nadruk ligt.</div></div>'
            f'{blocks}</body></html>')


# --- one-pager -------------------------------------------------------------------
def onepager(c):
    o4, o6, o8 = c['opties']
    rij = lambda o: f'''<div class="op{' rec' if o['aanbevolen'] else ''}">{'<span class="tag">Aanbevolen</span>' if o['aanbevolen'] else ''}
<div class="ot">{o['beldagen']} beldagen</div><div class="opr">{euro(o['prijs'])}</div><div class="os">per werkperiode van 4 weken</div>
<div class="ok">{o['kpi']} afspraken</div><div class="os">{euro(o['per_afspraak'])} per afspraak  ·  {euro(o['per_beldag'])} per beldag</div></div>'''
    css = CSS_BASE + """
@page { size:A4; margin:1.3cm 1.5cm 1.2cm; background:#e9e0cd;
  @bottom-left { content:"LINK.   ·   Vervolgvoorstel OK Creative Agency   ·   15-10-2026"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; }
  @bottom-right { content:"www.linkgrp.nl"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; } }
body { font-size:9.2pt; line-height:1.45; background:none; }
.hero { background:#000; color:#fff; margin:-1.3cm -1.5cm 14px; padding:20px 1.5cm 18px; }
.hero h1 { font-size:24pt; margin:8px 0 6px; line-height:1.05; } .e { color:#38b6ff; font-size:8pt; font-weight:700; letter-spacing:.22em; }
.card { background:#f8f4eb; border-radius:12px; padding:13px 16px; }
.lbl { color:#38b6ff; font-size:7.4pt; font-weight:700; letter-spacing:.15em; text-transform:uppercase; margin-bottom:5px; }
.row { display:flex; gap:10px; margin-bottom:10px; } .col { flex:1; }
.op { flex:1; background:#f8f4eb; border-radius:12px; padding:14px 16px; position:relative; }
.op.rec { background:#000; color:#fff; } .op.rec .os { color:#b3b3b3; } .op.rec .opr { color:#38b6ff; }
.tag { position:absolute; top:-9px; right:12px; background:#38b6ff; color:#08293c; font-size:7pt; font-weight:700; border-radius:8px; padding:2px 9px; }
.ot { font-weight:800; font-size:12pt; } .opr { font-size:22pt; font-weight:800; line-height:1.1; margin-top:6px; } .ok { font-weight:800; font-size:11pt; margin-top:8px; }
.os { font-size:8pt; color:#6f6a5c; }
.big { font-size:20pt; font-weight:800; line-height:1; }
p { margin:0; } ul { margin:0; padding-left:15px; } li { margin-bottom:3px; }
"""
    body = f'''<div class="hero"><div style="display:flex;justify-content:space-between">{logo(22, True)}<span style="font-size:7.5pt;color:#bdbdbd;text-align:right">B2B sales partner<br>Alphen aan den Rijn  ·  www.linkgrp.nl</span></div>
<div class="e" style="margin-top:16px">VERVOLGVOORSTEL</div><h1>OK Creative Agency <span style="font-weight:300;color:#38b6ff">x</span> {logo(24, True, 'margin-left:3px')}<br><span class="serif" style="font-size:18pt">van pilot naar een vaste samenwerking</span></h1>
<div style="font-size:8.6pt;color:#cfcfcf">Naar aanleiding van de pilotevaluatie op 15-10-2026, voor Mees Hoogeveen.</div></div>

<div class="lbl" style="margin-bottom:6px">De pilot in het kort</div>
<div class="row">
<div class="card col"><div class="big">{c['n_leads']}</div><div class="os">leads en afspraken, doel {c['doel_totaal']}</div></div>
<div class="card col"><div class="big">{len(c['met_resultaat'])} van {len(c['gehouden'])}</div><div class="os">gehouden gesprekken met resultaat</div></div>
<div class="card col"><div class="big">{len(c['gepland'])}</div><div class="os">gesprekken en contactmomenten gepland tot en met {d(c['gepland'][-1]['gesprek_d'])}</div></div>
<div class="card col"><div class="big">{len(c['per_wp']['WP3'])}</div><div class="os">leads en afspraken in WP3, boven het doel van {C.PILOT['doel_wp']}</div></div>
</div>

<div class="lbl" style="margin:12px 0 12px">Het voorstel: hele beldagen per werkperiode van 4 weken</div>
<div class="row" style="margin-top:4px">{''.join(rij(o) for o in c['opties'])}</div>
<p class="os" style="margin:-4px 0 14px">Ter vergelijking, de pilot: {euro(C.PILOT['prijs_wp'])} per werkperiode voor {C.PILOT['doel_wp']} afspraken, {euro(c['pilot_per_afspraak'])} per afspraak. Meer afspraken, hogere kwaliteit, en de prijs per afspraak daalt.</p>

<div class="row">
<div class="card col"><div class="lbl">KPI</div><p><b>{C.KPI_PER_BELDAG} gekwalificeerde afspraken per beldag</b>, dus {o4['kpi']}, {o6['kpi']} of {o8['kpi']} per werkperiode. 1 beldag is {C.UREN_PER_BELDAG} uur bellen voor OK.</p></div>
<div class="card col" style="background:#000;color:#fff"><div class="lbl">Garantie</div><p>Halen we de KPI in een werkperiode niet, dan krijgt OK in de volgende werkperiode <b style="color:#38b6ff">een beldag gratis</b>.</p></div>
</div>
<div class="row">
<div class="card col"><div class="lbl">Wat telt als afspraak</div><p>De gesprekspartner is een beslisser (directie, MT of marketing en brand) bij een organisatie die in de afgesproken doelgroep past.</p></div>
<div class="card col"><div class="lbl">Voorwaarden</div><ul><li>Start {d(C.START_VERVOLG)}, direct na de pilot, zonder gat</li><li>Opzegbaar per werkperiode</li><li>Evaluatie na werkperiode 4 (t/m {d(c['wp4'][1])})</li><li>Nieuwe overeenkomst op de Algemene Voorwaarden LINK. versie 5</li></ul></div>
</div>
<div class="card" style="margin-bottom:10px"><div class="lbl">Zo werken we samen</div><p>Mees is het vaste aanspreekpunt. Elke vrijdag de rapportage, met een lijst van gebelde bedrijven en hun uitkomst. De basisdata regelen wij. OK levert aanvullend New Business-lijsten met warme contacten (websitebezoekers, LinkedIn), waar we in de rapportage structureel terugkoppeling op geven, en een uitsluitlijst, zodat we nooit dubbel bellen.</p></div>
<div class="card" style="background:#000;color:#fff"><div class="lbl">Volgende stap</div><p>Laat per mail weten met hoeveel beldagen jullie starten. Dan sturen wij de overeenkomst, zodat we op {d(C.START_VERVOLG)} beginnen. Hens Boer, LINK.</p></div>'''
    return f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><title>Vervolgvoorstel OK Creative Agency</title><style>{css}</style></head><body>{body}</body></html>'


def deck_artifact(c):
    """Webversie voor claude.ai: zelfde slides, geschaald naar de schermbreedte."""
    css = CSS_DECK.replace('@page { size: 1280px 720px; margin:0; }', '').replace(
        '@media screen { body { background:#cfc6b2; padding:24px 0; } .slide { margin:0 auto 24px; box-shadow:0 6px 24px rgba(0,0,0,.18); } }', '')
    css += """
:root { color-scheme: light; }
body { background:#cfc6b2; padding-block:24px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
.deck { display:flex; flex-direction:column; gap:20px; max-width:1280px; margin:0 auto; }
.frame { position:relative; width:100%; max-width:100%; aspect-ratio:16/9; overflow:hidden; border-radius:6px; box-shadow:0 6px 24px rgba(0,0,0,.18); }
.frame > .slide { position:absolute; top:0; left:0; transform-origin:0 0; }
"""
    js = """<script>
(function(){function fit(){document.querySelectorAll('.frame').forEach(function(f){var k=f.clientWidth/1280;f.firstElementChild.style.transform='scale('+k+')';});}
window.addEventListener('resize',fit);fit();})();
</script>"""
    body = ''.join(f'<div class="frame">{x}</div>' for x in slides(c))
    return (f'<title>Pilotevaluatie OK Creative Agency</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<style>{css}</style><div class="deck">{body}</div>{js}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--belexport', required=True)
    ap.add_argument('--stats', required=True)
    ap.add_argument('--out', default=str(Path(__file__).parent / 'output'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    c = C.compute(a.belexport, a.stats)
    deck = deck_html(c)
    (out / 'Pilotevaluatie OK Creative Agency.html').write_text(deck, encoding='utf-8')
    HTML(string=deck).write_pdf(out / 'Pilotevaluatie OK Creative Agency.pdf')
    (out / 'deck-online.html').write_text(deck_artifact(c), encoding='utf-8')
    HTML(string=notities(c)).write_pdf(out / 'Sprekersnotities pilotevaluatie OK.pdf')
    HTML(string=onepager(c)).write_pdf(out / 'Vervolgvoorstel OK Creative Agency.pdf')
    print('klaar:', out)


if __name__ == '__main__':
    main()

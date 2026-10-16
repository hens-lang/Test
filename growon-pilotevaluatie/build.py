# -*- coding: utf-8 -*-
"""
Bouwt de pilotevaluatie GrowOn Agency x LINK. uit één set cijfers:
  - Pilotevaluatie GrowOn Agency.html / .pdf   (deck, 16:9)
  - Sprekersnotities pilotevaluatie GrowOn.pdf
  - Vervolgvoorstel GrowOn Agency.pdf   (one-pager voor Jaap)

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

FONTS = ASSETS / 'fonts'
_FONTFILES = [l.split(';') for l in (FONTS / 'fonts.txt').read_text().splitlines()]


def font_css(web=False):
    # lettertypes van linkgrp.nl: Inter Tight (koppen), Instrument Serif cursief (accent), Open Sans (tekst, huisstijl)
    if web:
        return "@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@500;700;800;900&family=Instrument+Serif:ital@0;1&family=Open+Sans:wght@400;600;700&display=swap');\n"
    return ''.join(f"@font-face {{ font-family:'{fam}'; font-style:{sty}; font-weight:{w}; src:url('{(FONTS / fn).as_uri()}'); }}\n"
                   for fam, sty, w, fn in _FONTFILES)

# --- huisstijl (zelfde tokens als gen.py van de weekrapportage) -----------------
CSS_BASE = """
:root { --ink:#1c2230; --blue:#38b6ff; --muted:#6f6a5c; --card:#f6f1e7; --bar:#e4dcc8; --cream:#e9e0cd; --night:#131a24; --night2:#222c3c; }
* { box-sizing:border-box; }
body { margin:0; font-family:'Open Sans', Arial, sans-serif; color:var(--ink); background:var(--cream); }
.serif, .it { font-family:'Instrument Serif', Georgia, serif; font-style:italic; font-weight:400; letter-spacing:0; }
.disp, h1, h2, .big, .cap, [style*="font-weight:800"], [style*="font-weight:900"] { font-family:'Inter Tight', 'Open Sans', Arial, sans-serif; }
.blue { color:var(--blue); }
.logotext { font-weight:800; letter-spacing:-0.6px; }
.logotext .dot, .dot { color:var(--blue); }
"""

CSS_DECK = CSS_BASE + """
@page { size: 1280px 720px; margin:0; }
@media screen { body { background:#cfc6b2; padding:24px 0; } .slide { margin:0 auto 24px; box-shadow:0 6px 24px rgba(0,0,0,.18); } }
.slide { width:1280px; height:720px; position:relative; overflow:hidden; background:var(--cream);
         padding:56px 72px 0; page-break-after:always; break-after:page; }
.slide.dark { background:linear-gradient(140deg, var(--night) 0%, var(--night2) 100%); color:#fff; }
.top { position:absolute; top:26px; left:72px; right:72px; display:flex; justify-content:space-between;
       font-size:13px; color:#a79f8b; }
.top .logotext { font-size:18px; color:var(--ink); }
.dark .top .logotext { color:#fff; }
.foot { position:absolute; bottom:22px; left:72px; right:72px; display:flex; justify-content:space-between;
        font-size:11.5px; color:#a79f8b; }
.eyebrow { color:var(--muted); font-size:12.5px; font-weight:700; letter-spacing:.24em; margin:22px 0 12px; text-transform:uppercase; }
.eyebrow::before { content:""; display:inline-block; width:26px; height:1.5px; background:var(--blue); vertical-align:middle; margin-right:12px; }
.dark .eyebrow { color:#9aa3b2; }
h2 { font-size:40px; line-height:1.08; font-weight:800; margin:0 0 28px; max-width:1136px; letter-spacing:-0.5px; }
h2 .it { font-size:1.12em; letter-spacing:-.2px; }
.dark h2 { color:#fff; }
.card { background:var(--card); border-radius:16px; padding:22px 24px; flex-shrink:0; }
.dark .card { background:rgba(255,255,255,.06); }
.card.black { background:linear-gradient(140deg, var(--night) 0%, var(--night2) 100%); color:#fff; border-radius:20px; }
.lbl { color:var(--blue); font-size:12px; font-weight:700; letter-spacing:.16em; text-transform:uppercase; margin-bottom:8px; }
.row { display:flex; gap:18px; }
.col { flex:1; }
.big { font-size:64px; font-weight:800; line-height:1; letter-spacing:-2px; }
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
table.t td { padding:4.5px 8px; border-bottom:1px solid #ddd3bd; }
table.t td.r, table.t th.r { text-align:right; }
table.t tr.tot td { font-weight:800; border-top:1.5px solid var(--ink); border-bottom:none; }
table.t tr.muted td { color:#9a9381; }
"""


def top(dark=False):
    return (f'<div class="top">{logo(17, dark)}'
            '<span>Pilotevaluatie GrowOn Agency</span></div>')


def foot(n):
    return (f'<div class="foot"><span>LINK.  ·  GrowOn Agency  ·  {d(C.PEILDATUM)}</span>'
            f'<span>{n}</span></div>')


def slide(n, eyebrow, title, body, dark=False):
    import re
    title = re.sub(r'\*(.+?)\*', r'<span class="it">\1</span>', title)
    cls = 'slide dark' if dark else 'slide'
    return (f'<section class="{cls}" id="s{n}">{top(dark)}<div class="eyebrow">{eyebrow}</div>'
            f'<h2>{title}</h2>{body}{foot(n)}</section>')


# --- grafieken (inline SVG, twee kleuren: inkt en blauw) ---------------------------
def svg_wp(c, w=640, h=380):
    vals = [len(c['per_wp'][n]) for n, _, _ in C.WP]
    doel = C.PILOT['doel_wp']
    top_v = 12
    pl, pr, pt, pb = 40, 20, 30, 56
    ih = h - pt - pb
    bw, gap = 120, (w - pl - pr - 3 * 120) / 3
    y = lambda v: pt + ih - ih * v / top_v
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter Tight, Open Sans, Arial, sans-serif">']
    for v in range(0, top_v + 1, 2):
        s.append(f'<line x1="{pl}" x2="{w-pr}" y1="{y(v)}" y2="{y(v)}" stroke="#d6ccb6" stroke-width="1"/>')
        s.append(f'<text x="{pl-10}" y="{y(v)+5}" text-anchor="end" font-size="14" fill="#8d8571">{v}</text>')
    for i, (n, st, en) in enumerate(C.WP):
        x = pl + gap / 2 + i * (bw + gap)
        v = vals[i]
        col = '#38b6ff' if i == 2 else '#1c2230'
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
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter Tight, Open Sans, Arial, sans-serif">']
    rows = [(n, c['wp_bel'][n]['niet_geschikt_pct']) for n, _, _ in C.WP]
    lw, maxw = 52, w - 52 - 60
    for i, (n, p) in enumerate(rows):
        yy = 18 + i * 60
        col = '#38b6ff' if i == 2 else '#1c2230'
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
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter Tight, Open Sans, Arial, sans-serif">']
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
    s.append(f'<text x="{x(C.PEILDATUM)-6}" y="{ym+56}" text-anchor="end" font-size="12" fill="#8d8571">vandaag {C.PEILDATUM:%d-%m}</text>')
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
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Inter Tight, Open Sans, Arial, sans-serif">']
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
    K = C.KPI_TXT
    wb = c['wp_bel']
    eigen, breed = c['lijst']['eigen'], c['lijst']['breed']
    pct1 = lambda x: str(x).replace('.', ',')

    # 1 Titel: Jaap wilde "bouwen en gas geven", wij beloofden "samen opschalen"
    stat = lambda n, t, kleur='#fff': f'<div style="padding:16px 0;border-top:1px solid rgba(255,255,255,.12)"><div style="font-family:\'Inter Tight\';font-weight:500;font-size:46px;letter-spacing:-1.5px;line-height:1;color:{kleur}">{n}</div><div style="font-size:14px;color:#9aa3b2;margin-top:6px">{t}</div></div>'
    paneel = (stat(f'{c["n_leads"]} / {c["doel_totaal"]}', 'leads, doel gehaald') + stat(len(c['gehouden']), 'gesprekken al geweest')
              + stat(d(C.START_VERVOLG), 'start van het vervolg', '#38b6ff'))
    S.append(f'''<section class="slide" id="s1" style="padding:0">
<div style="position:absolute;left:88px;top:58px">{logo(30)}</div>
<div style="position:absolute;left:88px;top:196px;width:790px">
  <div class="eyebrow" style="margin:0 0 26px">Pilotevaluatie  ·  {d(C.PEILDATUM)}</div>
  <div style="font-family:'Inter Tight';font-weight:900;font-size:84px;line-height:.95;letter-spacing:-3px;color:#1c2230;white-space:nowrap">Van pilot</div>
  <div class="it" style="font-size:100px;line-height:1;color:#1c2230;margin-top:4px;white-space:nowrap">naar opschalen<span style="color:#38b6ff">.</span></div>
  <div style="font-family:'Inter Tight';font-weight:800;font-size:27px;letter-spacing:-.6px;margin-top:34px;color:#1c2230">GrowOn Agency <span class="it" style="font-size:31px;color:#38b6ff;padding:0 4px">x</span> {logo(21, False, 'margin-left:2px')}</div>
</div>
<div style="position:absolute;right:88px;top:150px;width:300px;padding:24px 30px 14px;border-radius:28px;background:linear-gradient(150deg,#131a24 0%,#222c3c 100%);color:#fff">
  <div style="font-size:12px;font-weight:700;letter-spacing:.22em;color:#9aa3b2;margin-bottom:12px"><span style="display:inline-block;width:22px;height:1.5px;background:#38b6ff;vertical-align:middle;margin-right:10px"></span>DE PILOT IN HET KORT</div>
  {paneel}
</div>
<div style="position:absolute;left:88px;right:88px;bottom:44px;display:flex;justify-content:space-between;font-size:13px;color:#8d8571;border-top:1px solid #d3c9b3;padding-top:14px">
  <span>Google Meet</span><span>GrowOn Agency en LINK.</span><span>www.linkgrp.nl</span>
</div>
</section>''')

    # 2 Agenda
    ag = [('De afspraak en de cijfers', 'Wat we afspraken en wat er is geleverd', 10),
          ('Wat de leads opleveren', 'Concrete kansen per lead en de pijplijn', 10),
          ('Wat we geleerd hebben', 'Tien weken bellen voor GrowOn: wat werkt en wat minder', 10),
          ('Waarom de kwaliteit omhoog gaat', 'En hoe we vanaf nu samenwerken', 10),
          ('Het vervolg vanaf 26-10-2026', 'Beldagen, KPI, drie opties en onze garantie', 15),
          ('Volgende stappen', 'Akkoord, overeenkomst en start', 5)]
    rows = ''.join(f'''<div style="display:flex;align-items:center;padding:13px 0;border-bottom:1px solid #d6ccb6">
<span class="serif blue" style="font-size:26px;width:56px">{i+1:02d}</span>
<span style="font-size:21px;font-weight:700;width:430px">{a}</span><span style="font-size:16px;color:#6f6a5c;flex:1">{b}</span>
<span style="font-size:15px;color:#6f6a5c">{m} min</span></div>''' for i, (a, b, m) in enumerate(ag))
    S.append(slide(2, 'Agenda', 'In een uur van terugblik *naar opschalen.*', rows))

    # 3 De afspraak van de pilot
    def feit(l, v, sub, eerste=False, hl=False):
        rand = '' if eerste else 'border-left:1px solid #ddd3bd;'
        pad = 'padding:0 22px 0 0' if eerste else 'padding:0 22px'
        kleur = 'color:#38b6ff;' if hl else ''
        return f'<div style="flex:1;{pad};{rand}"><div class="lbl">{l}</div><div style="font-size:29px;font-weight:800;letter-spacing:-.5px;white-space:nowrap;{kleur}">{v}</div><div class="sub">{sub}</div></div>'
    strip = (feit('Belstart', d(C.BELSTART), 'in de naam van GrowOn', True) + feit('Looptijd', '3 x 4 weken', 'drie werkperiodes')
             + feit('Investering', euro(c['pilot_totaal']), f'3 x {euro(C.PILOT["prijs_wp"])} plus {euro(C.PILOT["opstart"])} opstart')
             + feit('Doel', f'{c["doel_totaal"]} leads', f'{C.PILOT["doel_wp"]} per werkperiode')
             + feit('Per lead', euro(c['pilot_per_lead_incl']), f'inclusief opstart, plus {C.PILOT["succesfee"].split(" ")[0]} succesfee', hl=True))
    t0, t1 = C.WP[0][1], C.WP[-1][2]
    span = (t1 - t0).days + 1
    seg = ''
    for i, (n, st, en) in enumerate(C.WP):
        w = 100 * ((en - st).days + 1) / span
        rand = '' if i == 2 else 'border-right:3px solid #e9e0cd;'
        seg += f'<div style="width:{w}%;padding:14px 16px;background:#1c2230;color:#fff;{rand}"><div style="font-size:16px;font-weight:800">{n}</div><div style="font-size:13px;color:#bdbdbd">{st:%d-%m} t/m {en:%d-%m}</div></div>'
    today = 100 * ((C.PEILDATUM - t0).days + 0.5) / span
    body = f'''<div class="card" style="display:flex;padding:24px 26px;margin-bottom:46px">{strip}</div>
<div style="position:relative"><div style="display:flex;border-radius:12px;overflow:hidden">{seg}</div>
<div style="position:absolute;left:{today}%;top:-10px;bottom:-10px;border-left:2px solid #38b6ff"></div>
<div style="position:absolute;left:{today}%;top:-30px;margin-left:-44px;font-size:12.5px;font-weight:700;color:#38b6ff">vandaag {C.PEILDATUM:%d-%m}</div></div>
<div style="display:flex;gap:40px;margin-top:30px">
<div style="flex:1"><div class="lbl">Doelgroep</div><p style="margin:0;font-size:17px">Retail en webshops: wonen en slapen, mode, sport en outdoor. Met een eigen advertentiebudget.</p></div>
<div style="flex:1"><div class="lbl">Beslisser</div><p style="margin:0;font-size:17px">Eigenaar, directie of marketing en e-commerce. Met die persoon plannen we het gesprek met Jaap.</p></div>
</div>'''
    S.append(slide(3, 'De afspraak', 'We spraken een pilot af van drie werkperiodes, met een vaste prijs per lead.', body))

    # 4 In cijfers
    body = f'''<div class="row" style="margin-bottom:18px">
<div class="card col"><div class="big">{num(c['pogingen'])}</div><div class="cap">contactpogingen</div><div class="sub">van 03-08 tot en met {d(C.DATASTAND)}</div></div>
<div class="card col"><div class="big">{num(c['calls'])}</div><div class="cap">keer iemand aan de lijn</div><div class="sub">{c['bereik']}% van alle pogingen</div></div>
<div class="card col"><div class="big">{num(c['gesproken'])}</div><div class="cap">bedrijven gesproken</div><div class="sub">uniek, na ontdubbelen</div></div>
</div>
<div class="row">
<div class="card black col" style="flex:1.2"><div class="big blue" style="font-size:84px">{c['n_leads']}</div><div class="cap">leads en afspraken voor GrowOn</div><div class="sub">Het doel van {c['doel_totaal']} is gehaald, met nog anderhalve week te gaan. {c['n_afspraak']} afspraken en {c['n_lead']} leads.</div></div>
<div class="card col"><div class="big">{len(c['gehouden'])}</div><div class="cap">gesprekken al geweest</div><div class="sub">met een beslisser, bij Jaap aan tafel</div></div>
<div class="card col"><div class="big">{c['terugbel_open']}</div><div class="cap">terugbelafspraken lopen nog</div><div class="sub">beslissers die later in gesprek willen</div></div>
</div>
<div class="note" style="margin-top:14px">Stand {d(C.DATASTAND)}. Bronnen: Belstat en het portaal.</div>'''
    S.append(slide(4, 'In cijfers', f'In tien weken spraken we {num(c["gesproken"])} bedrijven en leverden we {c["n_leads"]} leads en afspraken op.', body))

    # 5 Per werkperiode
    body = f'''<div class="row" style="align-items:stretch">
<div class="card" style="flex:1.45;padding:18px 20px 6px">{svg_wp(c)}</div>
<div class="col" style="display:flex;flex-direction:column;gap:16px">
 <div class="card black"><div class="lbl">Totaal tot nu toe</div><div class="big blue">{c['n_leads']} <span style="font-size:30px;color:#fff">van {c['doel_totaal']}</span></div><div class="sub">WP3 loopt nog tot en met 25-10-2026</div></div>
 <div class="card" style="flex:1"><div class="lbl">De trend</div><p style="margin:0;font-size:16px">WP1 en WP2 zaten boven het doel. WP3 staat nu op {wp('WP3')}, maar uit deze periode lopen {wb['WP3']['terugbel']} terugbelafspraken: beslissers die later willen praten.</p></div>
</div></div>
<div class="note" style="margin-top:12px">Geteld op aanmaakdatum van de lead in het portaal.</div>'''
    S.append(slide(5, 'Resultaten per werkperiode', f'Het doel van {c["doel_totaal"]} is *al gehaald*, met nog anderhalve week te gaan.', body))

    # 6 Concrete kansen (geen statussen van GrowOn, behalve klant geworden)
    def kaart(r):
        if r['gewonnen']:
            status, kleur = 'klant geworden', '#38b6ff'
        elif r['gehouden']:
            status, kleur = 'gesprek geweest', '#1c2230'
        elif r['gepland']:
            status, kleur = 'gepland ' + d(r['gesprek_d']), '#8d8571'
        else:
            status, kleur = 'loopt', '#8d8571'
        return (f'<div style="padding:5px 0 5px 12px;border-left:2px solid {kleur}">'
                f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px"><span style="font-family:\'Inter Tight\';font-weight:800;font-size:14px">{r["bedrijf"]}</span>'
                f'<span style="font-size:10.5px;color:{"#38b6ff" if r["gewonnen"] else "#8d8571"};font-weight:{700 if r["gewonnen"] else 400};white-space:nowrap">{status}</span></div>'
                f'<div style="font-size:11.8px;line-height:1.32;margin-top:1px">{C.KANSEN[r["bedrijf"]]}</div></div>')
    volg = sorted([r for r in c['tellen'] if not r['geen_match']],
                  key=lambda r: (0 if r['gewonnen'] else 1 if r['gehouden'] else 2, r['gesprek_dt']))
    kol = [volg[i::3] for i in range(3)]
    grid = ''.join(f'<div style="flex:1;display:flex;flex-direction:column;gap:6px">{"".join(kaart(r) for r in k)}</div>' for k in kol)
    legenda = ('<div style="display:flex;gap:22px;font-size:12px;color:#6f6a5c;margin-top:12px">'
               f'<span><span style="display:inline-block;width:10px;height:10px;background:#38b6ff;margin-right:6px"></span>{len(c["gewonnen"])} al klant geworden</span>'
               f'<span><span style="display:inline-block;width:10px;height:10px;background:#1c2230;margin-right:6px"></span>gesprek geweest</span>'
               f'<span>{len(c["geen_match"])} leads zonder match staan hier niet bij, die kwamen allemaal uit de eerste twee weken</span></div>')
    body = f'<div style="display:flex;gap:24px">{grid}</div>{legenda}'
    S.append(slide(6, 'Concrete kansen', 'Achter de leads zit *budget en een reden om te wisselen.*', body).replace('<h2>', '<h2 style="margin-bottom:14px">', 1).replace('<div class="eyebrow">', '<div class="eyebrow" style="margin-top:16px">', 1))

    # 7 De pijplijn: wat gepland staat, wat loopt, en de terugbelafspraken
    loopt_txt = {'Bahlmann': 'Gesprek wordt verzet', 'Kip Aloha damesmode': 'Ontvangt eerst inzichten per mail', 'Teddy Days': 'Door GrowOn zelf opgepakt'}
    regel = lambda a, b: f'<div style="display:flex;justify-content:space-between;gap:12px;padding:11px 0;border-bottom:1px solid #ddd3bd"><span style="font-weight:700;font-size:16px">{a}</span><span style="font-size:14.5px;color:#6f6a5c">{b}</span></div>'
    gepland = ''.join(regel(r['bedrijf'], ('gesprek ' if r['type'] == 'Afspraak' else 'contactmoment ') + d(r['gesprek_d'])) for r in c['gepland'])
    loopt = ''.join(regel(r['bedrijf'], loopt_txt.get(r['bedrijf'], 'loopt')) for r in c['open_lead'])
    tb = [wb[n]['terugbel'] for n, _, _ in C.WP]
    mx = max(tb)
    bars = ''.join(f'<div style="display:flex;align-items:center;gap:12px;margin-top:12px"><span style="width:44px;font-weight:700;font-size:15px">{n}</span><div style="flex:1;background:rgba(255,255,255,.08);border-radius:6px;height:26px"><div style="width:{max(100*v/mx,3)}%;height:26px;border-radius:6px;background:{"#38b6ff" if i == 2 else "#5b6577"}"></div></div><span style="width:36px;text-align:right;font-weight:800;font-size:18px">{v}</span></div>' for i, ((n, _, _), v) in enumerate(zip(C.WP, tb)))
    body = f'''<div class="row" style="align-items:stretch">
<div class="card black" style="flex:1.1;padding:26px 30px"><div class="lbl">Terugbelafspraken</div><div class="big blue">{c['terugbel_open']}</div><div class="sub" style="font-size:15px">beslissers die later in gesprek willen, per werkperiode van het laatste contact</div>{bars}</div>
<div class="col" style="display:block">
<div class="card" style="margin-bottom:16px;padding:18px 24px"><div class="lbl">Gepland</div>{gepland}</div>
<div class="card" style="padding:18px 24px"><div class="lbl">Loopt</div>{loopt}</div>
</div></div>'''
    S.append(slide(7, 'De pijplijn', f'De pijplijn is gevuld: *{c["terugbel_open"]} beslissers* willen later in gesprek.', body))

    # 8 Wat werkt
    lessen = [('Doorvragen op de huidige partner', 'Veel retailers hebben al een bureau. De vraag is of ze tevreden zijn. Bij Gents, OSKA, Van Zuilen en Hippe Kippe was het antwoord nee.'),
              ('Het juiste moment', 'Een opgezegde partner, een nieuwe marketeer, een oproep op LinkedIn: bij De Schans en BBQtime viel het gesprek precies goed.'),
              ('Inzichten per mail als tussenstap', 'Wie sceptisch is over bureaus, krijgt eerst een paar concrete punten per mail.'),
              ('De warme contactlijst van GrowOn', f'{pct1(eigen["pct"])}% van de gesproken bedrijven op die lijst werd een lead, tegenover {pct1(breed["pct"])}% op de brede lijsten.')]
    lijst = ''.join(f'<div style="padding:13px 0;border-bottom:1px solid #d6ccb6"><div style="font-size:18px;font-weight:800">{a}</div><div style="font-size:15px;line-height:1.45;margin-top:3px">{b}</div></div>' for a, b in lessen)
    body = f'''<div style="display:flex;gap:44px;align-items:flex-start">
<div class="card black" style="flex:1.1;padding:30px 34px">
<div class="lbl">De insteek die werkt</div>
<div style="font-size:25px;line-height:1.38;font-weight:700;color:#fff;margin-top:8px">We bellen met iets concreets: Jaap heeft naar de ads en de webshop gekeken en ziet verbeterpunten.</div>
<div style="margin-top:22px;padding-top:16px;border-top:1px solid #333;font-size:16px;color:#bdbdbd">Waarom het werkt: we komen iets <span class="blue" style="font-weight:700">brengen</span> in plaats van iets verkopen.</div>
</div>
<div style="flex:1;border-top:1.5px solid #1c2230">{lijst}</div>
</div>'''
    S.append(slide(8, 'Wat we geleerd hebben', 'Retailers praten graag *als we iets concreets meebrengen.*', body))

    # 9 Wat minder werkt
    minder = [('Brede SBI-lijsten', f'In WP1 paste {wb["WP1"]["niet_geschikt_pct"]}% van de gesproken bedrijven niet. We bellen nu gericht retailers en webshops met eigen advertentiebudget.'),
              ('Leads zonder match', f'{len(c["geen_match"])} leads uit de eerste twee weken bleken geen match. Daarom leggen we vooraf scherp vast wat een lead is.'),
              ('Bedrijven die alles zelf doen', 'Wie de ads zelf goed op orde heeft, is lastig. We vragen door en sturen eerst inzichten per mail.'),
              ('Scepsis over bureaus', 'Wie eerder slechte ervaringen had, wil bewijs. We beloven niets aan de telefoon en laten Jaap het in het gesprek laten zien.')]
    rows = ''.join(f'<div style="display:flex;gap:18px;padding:12px 0;border-bottom:1px solid #ddd3bd"><div style="width:230px;font-size:17px;font-weight:800">{a}</div><div style="flex:1;font-size:15.5px;line-height:1.45"><span class="blue" style="font-weight:700">Wat we doen: </span>{b}</div></div>' for a, b in minder)
    body = f'''<div class="row" style="align-items:stretch">
<div class="card" style="flex:1.35;padding:14px 24px">{rows}</div>
<div class="card col"><div class="lbl">Het effect van scherpere lijsten</div><div style="font-size:15px;margin-bottom:14px">Aandeel gesproken bedrijven dat niet bij GrowOn paste</div>{svg_niet_geschikt(c)}
<div class="note">{wb['WP1']['niet_geschikt']} van {wb['WP1']['gesproken']} in WP1, {wb['WP2']['niet_geschikt']} van {wb['WP2']['gesproken']} in WP2, {wb['WP3']['niet_geschikt']} van {wb['WP3']['gesproken']} in WP3. Ingedeeld op datum van het laatste contact.</div></div>
</div>'''
    S.append(slide(9, 'Wat minder werkt', 'Waar het schuurde, hebben we de aanpak al aangepast.', body))

    # 10 Waarom de kwaliteit omhoog gaat: augustus tegenover nu
    vgl = [('De lijsten', f'Brede SBI-lijsten, {wb["WP1"]["niet_geschikt_pct"]}% niet passend', f'Retail en webshops met eigen budget, {wb["WP3"]["niet_geschikt_pct"]}% niet passend'),
           ('Wat een lead is', 'Interesse in een gesprek', 'Een beslisser, advertentiebudget en een concrete aanleiding'),
           ('De insteek', 'Een algemene introductie', 'Concreet: Jaap heeft naar de ads en de webshop gekeken'),
           ('Warme contacten', '', f'De eerdere contactlijst van GrowOn gaat voor ({pct1(eigen["pct"])}% werd een lead)'),
           ('Dubbel bellen', 'Klantenlijst van GrowOn uitgesloten', 'Klanten en lopende gesprekken van GrowOn uitgesloten'),
           ('Terugkoppeling', 'Een weekrapportage met de cijfers', 'Elke vrijdag naar Jaap, met de lijst van gebelde bedrijven')]
    rows = ''.join(f'<tr><td style="font-weight:800;width:150px">{a}</td><td style="color:#8d8571">{b if b else "<span class=\"chip neutral\">nieuw</span>"}</td><td style="font-weight:600">{n_}</td></tr>' for a, b, n_ in vgl)
    body = f'''<div style="display:flex;gap:22px;align-items:flex-start">
<div class="card" style="flex:1;padding:10px 22px 6px"><table class="t" style="font-size:14.5px"><tr><th></th><th>Augustus</th><th style="color:#38b6ff">Nu</th></tr>{rows}</table></div>
<div class="card black" style="width:250px;padding:22px"><div class="lbl">Bewijs uit de pilot</div>
<div style="font-size:50px;font-weight:800;color:#38b6ff;line-height:1;margin-top:6px">{wb["WP3"]["niet_geschikt_pct"]}%</div><div style="font-size:14px;margin:6px 0 16px;line-height:1.4">niet passend in WP3, tegenover {wb["WP1"]["niet_geschikt_pct"]}% in WP1</div>
<div style="font-size:30px;font-weight:800;line-height:1">{len(c["geen_match"])}</div><div style="font-size:14px;color:#bdbdbd;margin-top:4px">leads zonder match, allemaal uit de eerste twee weken</div></div>
</div>'''
    S.append(slide(10, 'Waarom de kwaliteit omhoog gaat', 'De rommel gaat eruit: *elke afspraak voldoet aan een vaste definitie.*', body))

    # 11 Samenwerking: het ritme van een werkperiode van 4 weken
    s4, e4 = c['wp4']
    weken = ''
    for k in range(4):
        maandag = s4 + C.dt.timedelta(days=7 * k)
        dagen = ''.join(f'<div style="flex:1;height:44px;border-radius:7px;background:{"#38b6ff" if j == 4 else "#f8f4eb"};text-align:center;line-height:44px;font-size:12.5px;font-weight:700;color:{"#08293c" if j == 4 else "#8d8571"}">{dn}</div>' for j, dn in enumerate(['ma', 'di', 'wo', 'do', 'vr']))
        weken += f'<div style="flex:1"><div style="font-size:13px;color:#6f6a5c;margin-bottom:6px">week {maandag.isocalendar()[1]}  ·  {maandag:%d-%m}</div><div style="display:flex;gap:5px">{dagen}</div></div>'
    weken += '<div style="width:120px"><div style="font-size:13px;color:#6f6a5c;margin-bottom:6px">na week 4</div><div style="height:44px;border-radius:7px;background:#1c2230;color:#fff;text-align:center;line-height:44px;font-size:12.5px;font-weight:700">evaluatie</div></div>'
    blok = [('Jaap is het aanspreekpunt', 'Jaap voert de gesprekken. Bijsturing en vragen lopen rechtstreeks via hem.'),
            ('Elke vrijdag de rapportage', 'Cijfers, wat werkt, wat we terughoren en de warme leads, met de lijst van gebelde bedrijven en hun uitkomst.'),
            ('Lijsten', 'De basisdata regelen wij. GrowOn levert warme contacten en een uitsluitlijst met klanten en lopende gesprekken aan.'),
            ('Evaluatie na werkperiode 4', 'Cijfers, kwaliteit van de afspraken en de doelgroep. Daarna samen verder opschalen.')]
    tekst = ''.join(f'<div style="flex:1;border-top:1.5px solid #1c2230;padding-top:12px"><div style="font-size:17px;font-weight:800">{a}</div><div style="font-size:14.5px;line-height:1.45;margin-top:4px">{b}</div></div>' for a, b in blok)
    body = f'''<div class="card" style="padding:20px 24px 22px;background:#e4dcc8"><div style="display:flex;justify-content:space-between;margin-bottom:12px"><div class="lbl" style="margin:0">Het ritme van werkperiode 4: {d(s4)} t/m {d(e4)}</div><div style="font-size:13px;font-weight:700;color:#1c2230"><span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:#38b6ff;margin-right:6px"></span>vrijdag: rapportage en bellijst naar Jaap</div></div>
<div style="display:flex;gap:16px">{weken}</div></div>
<div style="display:flex;gap:26px;margin-top:26px">{tekst}</div>'''
    S.append(slide(11, 'Samenwerking vanaf nu', 'Elke week weten jullie *precies wat er gebeld is en wat het opleverde.*', body))

    # 12 Het vervolg
    term = lambda big, small, hl=False: f'<div><div style="font-size:54px;font-weight:800;letter-spacing:-1.5px;line-height:1;color:{"#38b6ff" if hl else "#fff"}">{big}</div><div style="font-size:15px;color:#a9a9a9;margin-top:8px">{small}</div></div>'
    op = lambda t: f'<div style="font-size:40px;font-weight:300;color:#38b6ff;padding:0 34px">{t}</div>'
    som = (term('1 beldag', 'per werkperiode van 4 weken') + op('=') + term(f'{C.UREN_PER_BELDAG} uur', 'bellen namens GrowOn, in de naam van GrowOn')
           + op('=') + term(f'{K} afspraken', 'met een beslisser met budget', True))
    regels = ''.join(f'<div style="display:flex;align-items:baseline;padding:14px 0;border-top:1px solid #2a2a2a"><div style="width:260px;font-size:22px;font-weight:700;color:#fff">{o["beldagen"]} beldagen</div><div style="width:120px;font-size:15px;color:#8a8a8a">x {K}</div><div style="font-size:30px;font-weight:800;color:#38b6ff;width:80px">{o["kpi"]}</div><div style="font-size:17px;color:#d0d0d0">afspraken per werkperiode</div></div>' for o in c['opties'])
    body = f'''<div style="display:flex;align-items:flex-start;margin:10px 0 40px">{som}</div>
<div style="border-bottom:1px solid #2a2a2a">{regels}</div>
<div style="margin-top:18px;font-size:16px;color:#a9a9a9">Start {d(C.START_VERVOLG)}, direct na werkperiode 3, zonder gat. Opzegbaar per werkperiode.</div>'''
    S.append(slide(12, 'Het vervolg', f'Vanaf {d(C.START_VERVOLG)} werken we in hele beldagen, met een KPI van {K} afspraken per beldag.', body, dark=True))

    # 13 De opties
    def optie(titel, prijs, kpi, per, sub, eenheid='afspraken', cls=''):
        return f'''<div class="card {cls}" style="flex:1;padding:22px 22px 18px;position:relative">
<div style="font-size:20px;font-weight:800">{titel}</div><div class="sub" style="margin-top:2px">{sub}</div>
<div style="font-size:40px;font-weight:800;margin-top:14px;line-height:1">{euro(prijs)}</div><div class="sub">per 4 weken</div>
<div style="font-size:19px;font-weight:700;margin-top:12px">{kpi} {eenheid}</div>
<div style="font-size:15px;margin-top:10px;padding-top:10px;border-top:1px solid #ddd3bd"><b>{euro(per)}</b> per {'afspraak' if eenheid == 'afspraken' else 'lead'}</div></div>'''
    cards = optie('Pilot', C.PILOT['prijs_wp'], C.PILOT['doel_wp'], c['pilot_per_lead_incl'], f'plus {euro(C.PILOT["opstart"])} opstart', 'leads', 'pilot').replace('class="card pilot"', 'class="card" style="opacity:.6"')
    for o in c['opties']:
        cards += optie(f'{o["beldagen"]} beldagen', o['prijs'], o['kpi'], o['per_afspraak'], f'{euro(o["per_beldag"])} per beldag')
    body = f'''<div class="row" style="gap:16px;margin-top:6px">{cards}</div>
<div class="card" style="margin-top:22px;padding:16px 24px;font-size:17px;font-weight:600;line-height:1.45">Inclusief de opstartkosten kostte een lead in de pilot {euro(c['pilot_per_lead_incl'])}. In het vervolg zijn er geen opstartkosten, voldoet elke afspraak aan de vaste definitie en geldt de garantie.</div>'''
    S.append(slide(13, 'De opties', 'Meer afspraken per werkperiode, *en elke afspraak telt.*', body))

    # 14 Garantie
    ex_n = o6['kpi'] - 2
    body = f'''<div class="row" style="align-items:stretch">
<div class="card black" style="flex:1.2;padding:30px 34px"><div class="lbl">Onze garantie</div>
<div style="font-size:30px;font-weight:800;line-height:1.25">Halen we in een werkperiode de KPI van {K} afspraken per beldag niet, dan krijgt GrowOn in de volgende werkperiode een beldag gratis.</div>
<div class="sub" style="font-size:16px;margin-top:18px">Voorbeeld: bij {o6['beldagen']} beldagen is de KPI {o6['kpi']} afspraken. Worden het er {ex_n}, dan bellen we de volgende werkperiode {o6['beldagen']+1} dagen voor de prijs van {o6['beldagen']}.</div></div>
<div class="col">
<div class="card" style="margin-bottom:16px"><div class="lbl">Wat telt als afspraak</div><p style="margin:0;font-size:16px">Een gesprek met een beslisser (eigenaar, directie of marketing en e-commerce) bij een retailer of webshop met eigen advertentiebudget, binnen de afgesproken doelgroep.</p></div>
<div class="card"><div class="lbl">Wat het voor GrowOn betekent</div><p style="margin:0;font-size:16px">GrowOn betaalt voor afspraken die passen. Het risico van een tegenvallende periode ligt bij ons.</p></div>
</div></div>'''
    S.append(slide(14, 'Onze garantie', 'Halen we de KPI niet, dan krijgt GrowOn *een beldag gratis.*', body))

    # 15 Volgende stappen
    stappen = [(d(C.PEILDATUM), 'Evaluatie', 'Vandaag: keuze voor het aantal beldagen'),
               ('Volgende week', 'Akkoord', 'GrowOn bevestigt de keuze per mail aan Hens'),
               ('Voor 26-10', 'Overeenkomst', 'Op de Algemene Voorwaarden LINK. versie 5'),
               (d(C.START_VERVOLG), 'Start werkperiode 4', f'Loopt tot en met {d(c["wp4"][1])}'),
               (d(c['wp5_start']), 'Evaluatie na WP4', 'Cijfers, kwaliteit en opschalen samen bekijken')]
    st = ''.join(f'''<div style="flex:1;position:relative;padding-top:40px">
<div style="position:absolute;top:0;left:0;width:26px;height:26px;border-radius:50%;background:{'#38b6ff' if i == 3 else '#1c2230'}"></div>
<div style="font-size:15px;color:#6f6a5c">{a}</div><div style="font-size:21px;font-weight:800;margin-top:4px">{b}</div><div class="sub">{s}</div></div>''' for i, (a, b, s) in enumerate(stappen))
    body = f'''<div class="card" style="padding:30px 32px 26px;margin-bottom:18px"><div style="position:relative"><div style="position:absolute;top:12px;left:12px;right:60px;height:2px;background:#1c2230"></div><div class="row" style="gap:22px">{st}</div></div></div>
<div class="row">
<div class="card col"><div class="lbl">Opzegbaar</div><p style="margin:0;font-size:16px">Per werkperiode van 4 weken. Geen lange verplichting.</p></div>
<div class="card col"><div class="lbl">Doorlopend</div><p style="margin:0;font-size:16px">De {c['terugbel_open']} terugbelafspraken lopen zonder onderbreking door.</p></div>
<div class="card black col"><div class="lbl">De vraag van vandaag</div><p style="margin:0;font-size:17px;font-weight:700">Met hoeveel beldagen per werkperiode starten jullie op {d(C.START_VERVOLG)}?</p></div>
</div>'''
    S.append(slide(15, 'Volgende stappen', f'Met een akkoord starten we op {d(C.START_VERVOLG)}, *zonder gat* na de pilot.', body))

    # Bijlage A: leads
    loopt_txt = {'Bahlmann': 'Wordt verzet', 'Kip Aloha damesmode': 'Ontvangt eerst inzichten per mail', 'Teddy Days': 'Door GrowOn opgepakt'}
    rws = ''
    for r in sorted(c['portaal'], key=lambda r: r['aangemaakt']):
        if r['gewonnen']:
            st = 'Klant geworden'
        elif r['gehouden']:
            st = 'Gesprek geweest'
        elif r['gepland']:
            st = 'Gesprek gepland' if r['type'] == 'Afspraak' else 'Contactmoment gepland'
        else:
            st = loopt_txt.get(r['bedrijf'], 'Loopt')
        rws += f'<tr><td>{r["bedrijf"]}</td><td>{r["type"]}</td><td>{d(r["aangemaakt"])}</td><td>{r["wp"]}</td><td>{r["gesprek_dt"]:%d-%m-%Y %H:%M}</td><td>{st}</td></tr>'
    body = f'''<div class="card" style="padding:4px 20px"><table class="t ta" style="font-size:11px"><tr><th>Bedrijf</th><th>Type</th><th>Aangemaakt</th><th>Werkperiode</th><th>Gesprek</th><th>Status</th></tr>{rws}</table></div>
<div class="note" style="margin-top:6px">Bron: portaal, stand {d(C.DATASTAND)}. Totaal: {c['n_leads']}. Bij leads is de datum het moment van overdracht of het geplande contactmoment.</div>'''
    S.append(slide('A', 'Bijlage A', 'Alle leads en afspraken met hun status.', body).replace('<h2>', '<h2 style="font-size:26px;margin-bottom:8px">').replace('<div class="eyebrow">', '<div class="eyebrow" style="margin-top:12px;margin-bottom:6px">'))

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
<div class="card"><div class="lbl">Uitgesloten</div><p style="margin:0;font-size:14px">De klantenlijst die GrowOn op 17-07-2026 aanleverde, is niet gebeld.</p></div>
</div></div>'''
    S.append(slide('B', 'Bijlage B', 'De belcijfers per werkperiode.', body).replace('<h2>', '<h2 style="font-size:28px;margin-bottom:12px">').replace('<div class="eyebrow">', '<div class="eyebrow" style="margin-top:14px">'))
    return S


def deck_html(c):
    return (f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=1320">'
            f'<title>Pilotevaluatie GrowOn Agency</title><style>{font_css()}{CSS_DECK}table.ta td {{ padding:1.6px 8px; }} table.ta th {{ padding:3px 8px; }}</style></head><body>'
            + ''.join(slides(c)) + '</body></html>')


# --- sprekersnotities ------------------------------------------------------------
def notities(c):
    wp = lambda n: len(c['per_wp'][n])
    o4, o6, o8 = c['opties']
    K = C.KPI_TXT
    wb = c['wp_bel']
    eigen, breed = c['lijst']['eigen'], c['lijst']['breed']
    pct1 = lambda x: str(x).replace('.', ',')
    N = [
        (1, 'Titel', 'Welkom. Vandaag gaat het over de stap van pilot naar opschalen.',
         ['Bedank Jaap (en Ivo als hij aanschuift) voor de tijd.',
          'Haak in op hun eigen woorden uit juli: een partij waarmee je kunt bouwen en gas kunt geven. En onze belofte: als het goed loopt, schalen we samen op.'],
         'Hoe kijken jullie zelf terug op de gesprekken van de afgelopen tien weken?', 'Geen getal. Laat Jaap eerst praten.'),
        (2, 'Agenda', 'Een uur, zes onderdelen, en aan het eind een keuze.',
         ['Loop de agenda kort door. Zeg vooraf dat we eindigen met het vervolg en een concrete keuze.'],
         'Is er iets wat jullie vandaag zeker besproken willen hebben?', '60 minuten, het vervolg krijgt de meeste tijd.'),
        (3, 'De afspraak', 'Dit spraken we af in juli.',
         [f'Belstart 03-08-2026, drie werkperiodes van 4 weken, {C.PILOT["doel_wp"]} gekwalificeerde leads per periode.',
          f'{euro(C.PILOT["per_lead"])} per lead, dus {euro(C.PILOT["prijs_wp"])} per werkperiode, plus {euro(C.PILOT["opstart"])} opstartkosten. Samen {euro(c["pilot_totaal"])}, dat is {euro(c["pilot_per_lead_incl"])} per lead. Plus {C.PILOT["succesfee"]} op klanten die hieruit komen.',
          'Jaap vroeg toen zelf om goed te kaderen waar een lead aan moet voldoen. Daar komen we op terug bij de kwaliteit.'],
         None, f'{euro(c["pilot_totaal"])} totaal, {euro(c["pilot_per_lead_incl"])} per lead inclusief opstart.'),
        (4, 'In cijfers', 'Het doel is gehaald.',
         [f'{num(c["pogingen"])} contactpogingen, {num(c["calls"])} keer iemand aan de lijn, {num(c["gesproken"])} unieke bedrijven gesproken.',
          f'{c["n_leads"]} leads en afspraken: het doel van {c["doel_totaal"]} is gehaald, met nog anderhalve week te gaan.',
          f'{len(c["gehouden"])} gesprekken zijn al geweest. Daarnaast lopen {c["terugbel_open"]} terugbelafspraken.'],
         None, f'{c["n_leads"]} van {c["doel_totaal"]}.'),
        (5, 'Per werkperiode', 'Eerlijk: WP3 loopt achter op tempo, maar de pijplijn is voller dan ooit.',
         [f'WP1 {wp("WP1")}, WP2 {wp("WP2")}, WP3 nu {wp("WP3")}.',
          f'In WP3 is minder gebeld voor GrowOn. Tegelijk staan uit WP3 al {wb["WP3"]["terugbel"]} terugbelafspraken open, tegenover {wb["WP1"]["terugbel"]} in WP1.',
          'Niet goedpraten. Benoem het en laat zien dat het vervolg met vaste beldagen dit oplost.'],
         None, f'{c["n_leads"]} van {c["doel_totaal"]} gehaald.'),
        (6, 'Concrete kansen', 'De kracht zit in alle leads samen: budget en een reden om te wisselen.',
         [f'{len(c["gewonnen"])} leads zijn al klant geworden: Messermeister, Green Earth en P. Ris. Daar loopt de succesfee over.',
          'Loop voorbeelden door: Gents en OSKA ontevreden over hun bureau, Catwalk Junkie kan al twee jaar niet adverteren, BBQtime koos uit bijna 200 reacties voor dit gesprek, De Schans heeft net opgezegd.',
          f'De {len(c["geen_match"])} leads zonder match benoemen we zelf: allemaal uit de eerste twee weken.'],
         'Welke van deze gesprekken voelt voor jullie als de beste kans, en wat is zo\'n klant gemiddeld waard per jaar?',
         f'{len(c["gewonnen"])} klanten binnen tien weken.'),
        (7, 'De pijplijn', 'Wat er nog komt.',
         [f'{c["terugbel_open"]} terugbelafspraken, waarvan {wb["WP3"]["terugbel"]} uit WP3.',
          'Gepland: De Schans 20-10, Qpro in december. Bahlmann wordt verzet, Kip Aloha krijgt eerst inzichten per mail, Teddy Days pakt GrowOn zelf op.',
          'Als we stoppen, blijven die terugbelafspraken liggen. Daarom zonder gat door.'],
         None, f'{c["terugbel_open"]} beslissers willen later praten.'),
        (8, 'Wat werkt', 'We bellen met iets concreets in de hand.',
         ['De insteek: Jaap heeft naar de ads en de webshop gekeken en ziet verbeterpunten.',
          'Doorvragen op de huidige partner levert het meeste op. Ontevredenheid is de ingang.',
          f'De eerdere contactlijst van GrowOn: {pct1(eigen["pct"])}% van de gesproken bedrijven werd een lead, tegenover {pct1(breed["pct"])}% op de brede lijsten.'],
         'Herkennen jullie dit in de gesprekken die Jaap heeft gevoerd?', f'{pct1(eigen["pct"])}% op de eigen contactlijst.'),
        (9, 'Wat minder werkt', 'We benoemen wat schuurde, en wat we al hebben veranderd.',
         [f'In WP1 paste {wb["WP1"]["niet_geschikt_pct"]}% van de gesproken bedrijven niet. In WP3 nog {wb["WP3"]["niet_geschikt_pct"]}%.',
          f'De {len(c["geen_match"])} leads zonder match zaten allemaal in de eerste twee weken.',
          'Wie de ads zelf doet of sceptisch is, krijgt eerst inzichten per mail.'],
         'Zijn er segmenten waar jullie juist meer of minder van willen?', f'Van {wb["WP1"]["niet_geschikt_pct"]}% naar {wb["WP3"]["niet_geschikt_pct"]}% niet passend.'),
        (10, 'Waarom de kwaliteit omhoog gaat', 'Dit is het antwoord op de hogere prijs per afspraak.',
         ['Loop augustus tegenover nu door. De kern: een vaste definitie van een lead, zoals Jaap in juli zelf vroeg.',
          'Een lead is straks: een beslisser, advertentiebudget en een concrete aanleiding. Geen rommel meer.',
          'GrowOn levert een uitsluitlijst met klanten en lopende gesprekken, zodat we nooit dubbel bellen.'],
         'Klopt deze definitie voor jullie, of willen jullie er iets aan toevoegen, zoals een minimaal advertentiebudget?',
         'Elke afspraak voldoet aan de definitie.'),
        (11, 'Samenwerking', 'Zo werken we vanaf nu samen.',
         ['Elke vrijdag de rapportage naar Jaap, met de lijst van gebelde bedrijven en hun uitkomst.',
          'GrowOn levert warme contacten aan. Op die leads geven we per lead terugkoppeling.',
          'Na WP4 evalueren we en kijken we hoe we verder opschalen.'],
         'Wie moet de rapportage naast Jaap nog ontvangen?', None),
        (12, 'Het vervolg', 'Van leads per stuk naar vaste beldagen.',
         [f'Vanaf {d(C.START_VERVOLG)}, direct na WP3.', f'KPI: {K} afspraken per beldag, dus {o4["kpi"]}, {o6["kpi"]} of {o8["kpi"]} per werkperiode.',
          'Achtergrond, niet delen: in de pilot is '
          f'{c["uren_record_txt"]} uur aan records gebeld, dat is {str(round(c["beldagen"],1)).replace(".", ",")} beldagen. '
          f'Gemiddeld {str(round(c["beldagen_per_lead"],2)).replace(".", ",")} lead per beldag, inclusief de opstart en de leads zonder match. {K} is dus een stap omhoog: dat vraagt de scherpere lijsten en de warme contacten van GrowOn.'],
         None, f'{K} per beldag.'),
        (13, 'De opties', 'Duurder per afspraak, beter per afspraak.',
         [f'Pilot {euro(c["pilot_per_lead_incl"])} per lead inclusief de {euro(C.PILOT["opstart"])} opstartkosten. Nu {euro(o4["per_afspraak"])}, {euro(o6["per_afspraak"])} of {euro(o8["per_afspraak"])} per afspraak, zonder opstartkosten.',
          'Bij 8 beldagen is het per afspraak zelfs goedkoper dan de pilot. Bij 4 en 6 beldagen iets duurder: zeg dat zelf voordat Jaap het zegt. Daar staat tegenover: geen leads zonder match meer, een vaste definitie en de garantie.',
          'Rekenvoorbeeld voor jezelf: één klant met een retainer levert GrowOn veel meer op dan het verschil per afspraak.',
          'Geen advies geven. Laat de keuze bij GrowOn.'],
         'Hoeveel nieuwe gesprekken per maand kan Jaap goed opvolgen: 10, 15 of 20?',
         f'{euro(o4["per_afspraak"])} tot {euro(o8["per_afspraak"])} per afspraak, met garantie.'),
        (14, 'Garantie', 'Het risico ligt bij ons.',
         [f'Halen we de KPI van {K} per beldag in een werkperiode niet, dan een beldag gratis in de volgende periode.',
          'Een afspraak telt als de gesprekspartner een beslisser is bij een retailer of webshop met eigen advertentiebudget.', 'Opzegbaar per werkperiode.'],
         'Is er iets dat jullie nog nodig hebben om hier ja op te zeggen?', 'Een beldag gratis.'),
        (15, 'Volgende stappen', 'Concreet afsluiten.',
         [f'Akkoord volgende week per mail, overeenkomst op de Algemene Voorwaarden LINK. versie 5, start {d(C.START_VERVOLG)}.',
          'De succesfee van 5% over de eerste 12 maanden blijft staan zoals in juli afgesproken, tenzij je dat anders wilt.',
          f'WP4 loopt tot en met {d(c["wp4"][1])}. Evaluatie in de week van {d(c["wp5_start"])}.', 'Zeg toe dat de one-pager vandaag naar Jaap gaat.'],
         f'Met hoeveel beldagen zetten we {d(C.START_VERVOLG)} vast?', f'Start {d(C.START_VERVOLG)}, zonder gat.'),
    ]
    blocks = ''
    for n, t, kern, zeg, vraag, nadruk in N:
        blocks += f'''<div class="nb"><div class="nh"><span class="nn">{n:02d}</span><span class="nt">{t}</span></div>
<div class="kern">{kern}</div><div class="lb">Wat ik zeg</div><ul>{''.join(f'<li>{x}</li>' for x in zeg)}</ul>
{f'<div class="lb">Vraag</div><p class="q">{vraag}</p>' if vraag else ''}
{f'<div class="lb">Nadruk op</div><p class="em">{nadruk}</p>' if nadruk else ''}</div>'''
    css = CSS_BASE + """
@page { size:A4; margin:1.4cm 1.5cm 1.3cm; background:#e9e0cd;
  @bottom-left { content:"LINK.   ·   Sprekersnotities pilotevaluatie GrowOn   ·   intern"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; }
  @bottom-right { content: counter(page) "  /  " counter(pages); font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; } }
body { font-size:9.6pt; line-height:1.5; background:none; }
.hero { background:linear-gradient(140deg,#131a24,#222c3c); color:#fff; margin:-1.4cm -1.5cm 16px; padding:26px 1.5cm 22px; }
.hero h1 { font-family:'Inter Tight',Arial,sans-serif; letter-spacing:-.5px; font-size:24pt; margin:6px 0 4px; } .hero .e { color:#38b6ff; font-size:8pt; font-weight:700; letter-spacing:.22em; }
.nb { background:#f8f4eb; border-radius:12px; padding:12px 16px; margin-bottom:10px; break-inside:avoid; }
.nh { display:flex; align-items:baseline; gap:10px; margin-bottom:4px; }
.nn { font-family:Georgia, serif; font-style:italic; color:#38b6ff; font-size:14pt; } .nt { font-weight:800; font-size:12pt; }
.kern { font-weight:700; margin-bottom:6px; }
.lb { color:#38b6ff; font-size:7.4pt; font-weight:700; letter-spacing:.14em; text-transform:uppercase; margin-top:6px; }
ul { margin:2px 0 0; padding-left:15px; } li { font-size:9.4pt; margin-bottom:3px; line-height:1.45; }
p { margin:2px 0 0; font-size:9.4pt; } .q { font-style:italic; } .em { font-weight:700; }
"""
    return (f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><title>Sprekersnotities pilotevaluatie GrowOn</title><style>{font_css()}{css}</style></head><body>'
            f'<div class="hero">{logo(20, True)}<div class="e" style="margin-top:14px">SPREKERSNOTITIES  ·  INTERN</div>'
            f'<h1>Pilotevaluatie GrowOn Agency</h1><div style="font-size:9pt;color:#cfcfcf">{d(C.PEILDATUM)}, Google Meet. Met Jaap Meijer. Per slide: wat ik zeg, welke vraag ik stel en waar de nadruk ligt.</div></div>'
            f'{blocks}</body></html>')


# --- one-pager -------------------------------------------------------------------
def onepager(c):
    o4, o6, o8 = c['opties']
    K = C.KPI_TXT
    rij = lambda o: f'''<div class="op">
<div class="ot">{o['beldagen']} beldagen</div><div class="opr">{euro(o['prijs'])}</div><div class="os">per werkperiode van 4 weken</div>
<div class="ok">{o['kpi']} afspraken</div><div class="os">{euro(o['per_afspraak'])} per afspraak<br>{euro(o['per_beldag'])} per beldag</div></div>'''
    css = CSS_BASE + f"""
@page {{ size:A4; margin:1.3cm 1.5cm 1.2cm; background:#e9e0cd;
  @bottom-left {{ content:"LINK.   ·   Vervolgvoorstel GrowOn Agency   ·   {d(C.PEILDATUM)}"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; }}
  @bottom-right {{ content:"www.linkgrp.nl"; font-family:Helvetica, Arial, sans-serif; font-size:7.4pt; color:#a79f8b; }} }}
""" + """
body { font-size:9.2pt; line-height:1.45; background:none; }
.hero { background:linear-gradient(140deg,#131a24,#222c3c); color:#fff; margin:-1.3cm -1.5cm 14px; padding:20px 1.5cm 18px; }
.hero h1 { font-family:'Inter Tight',Arial,sans-serif; letter-spacing:-.5px; font-size:24pt; margin:8px 0 6px; line-height:1.05; } .e { color:#38b6ff; font-size:8pt; font-weight:700; letter-spacing:.22em; }
.card { background:#f8f4eb; border-radius:12px; padding:13px 16px; }
.lbl { color:#38b6ff; font-size:7.4pt; font-weight:700; letter-spacing:.15em; text-transform:uppercase; margin-bottom:5px; }
.row { display:flex; gap:10px; margin-bottom:10px; } .col { flex:1; }
.op { flex:1; background:#f8f4eb; border-radius:12px; padding:14px 16px; position:relative; }
.ot { font-weight:800; font-size:12pt; } .opr { font-size:22pt; font-weight:800; line-height:1.1; margin-top:6px; } .ok { font-weight:800; font-size:11pt; margin-top:8px; }
.os { font-size:8pt; color:#6f6a5c; }
.big { font-size:20pt; font-weight:800; line-height:1; }
p { margin:0; } ul { margin:0; padding-left:15px; } li { margin-bottom:3px; }
"""
    body = f'''<div class="hero"><div style="display:flex;justify-content:space-between">{logo(22, True)}<span style="font-size:7.5pt;color:#bdbdbd;text-align:right">B2B sales partner<br>Alphen aan den Rijn  ·  www.linkgrp.nl</span></div>
<div class="e" style="margin-top:16px">VERVOLGVOORSTEL</div><h1>GrowOn Agency <span style="font-weight:300;color:#38b6ff">x</span> {logo(24, True, 'margin-left:3px')}<br><span class="serif" style="font-size:18pt">van pilot naar opschalen</span></h1>
<div style="font-size:8.6pt;color:#cfcfcf">Naar aanleiding van de pilotevaluatie op {d(C.PEILDATUM)}, voor Jaap Meijer.</div></div>

<div class="lbl" style="margin-bottom:6px">De pilot in het kort</div>
<div class="row">
<div class="card col"><div class="big">{c['n_leads']}</div><div class="os">leads en afspraken, doel {c['doel_totaal']} gehaald</div></div>
<div class="card col"><div class="big">{len(c['gehouden'])}</div><div class="os">gesprekken al geweest</div></div>
<div class="card col"><div class="big">{len(c['gewonnen'])}</div><div class="os">leads al klant geworden</div></div>
<div class="card col"><div class="big">{c['terugbel_open']}</div><div class="os">terugbelafspraken lopen nog</div></div>
</div>

<div class="lbl" style="margin:12px 0 12px">Het voorstel: hele beldagen per werkperiode van 4 weken</div>
<div class="row" style="margin-top:4px">{''.join(rij(o) for o in c['opties'])}</div>
<p class="os" style="margin:-4px 0 14px">Ter vergelijking, de pilot: {euro(c['pilot_totaal'])} voor {c['doel_totaal']} leads inclusief {euro(C.PILOT['opstart'])} opstartkosten, dus {euro(c['pilot_per_lead_incl'])} per lead. In het vervolg geen opstartkosten, geen leads zonder match en elke afspraak voldoet aan de vaste definitie.</p>

<div class="row">
<div class="card col"><div class="lbl">KPI</div><p><b>{K} gekwalificeerde afspraken per beldag</b>, dus {o4['kpi']}, {o6['kpi']} of {o8['kpi']} per werkperiode. 1 beldag is {C.UREN_PER_BELDAG} uur bellen voor GrowOn.</p></div>
<div class="card col" style="background:linear-gradient(140deg,#131a24,#222c3c);color:#fff"><div class="lbl">Garantie</div><p>Halen we de KPI in een werkperiode niet, dan krijgt GrowOn in de volgende werkperiode <b style="color:#38b6ff">een beldag gratis</b>.</p></div>
</div>
<div class="row">
<div class="card col"><div class="lbl">Wat telt als afspraak</div><p>Een gesprek met een beslisser (eigenaar, directie of marketing en e-commerce) bij een retailer of webshop met eigen advertentiebudget, binnen de afgesproken doelgroep.</p></div>
<div class="card col"><div class="lbl">Voorwaarden</div><ul><li>Start {d(C.START_VERVOLG)}, direct na de pilot, zonder gat</li><li>Opzegbaar per werkperiode</li><li>Succesfee van 5% over de eerste 12 maanden, zoals afgesproken</li><li>Evaluatie na werkperiode 4 (t/m {d(c['wp4'][1])})</li><li>Nieuwe overeenkomst op de Algemene Voorwaarden LINK. versie 5</li></ul></div>
</div>
<div class="card" style="margin-bottom:10px"><div class="lbl">Zo werken we samen</div><p>Jaap is het aanspreekpunt. Elke vrijdag de rapportage, met een lijst van gebelde bedrijven en hun uitkomst. De basisdata regelen wij. GrowOn levert warme contacten en een uitsluitlijst met klanten en lopende gesprekken aan, zodat we nooit dubbel bellen.</p></div>
<div class="card" style="background:linear-gradient(140deg,#131a24,#222c3c);color:#fff"><div class="lbl">Volgende stap</div><p>Laat per mail weten met hoeveel beldagen jullie starten. Dan sturen wij de overeenkomst, zodat we op {d(C.START_VERVOLG)} beginnen. Hens Boer, LINK.</p></div>'''
    return f'<!DOCTYPE html><html lang="nl"><head><meta charset="utf-8"><title>Vervolgvoorstel GrowOn Agency</title><style>{font_css()}{css}</style></head><body>{body}</body></html>'


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
    return (f'<title>Pilotevaluatie GrowOn Agency</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<style>{font_css(True)}{css}</style><div class="deck">{body}</div>{js}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--belexport', required=True)
    ap.add_argument('--stats', required=True)
    ap.add_argument('--out', default=str(Path(__file__).parent / 'output'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    c = C.compute(a.belexport, a.stats)
    deck = deck_html(c)
    (out / 'Pilotevaluatie GrowOn Agency.html').write_text(deck, encoding='utf-8')
    HTML(string=deck).write_pdf(out / 'Pilotevaluatie GrowOn Agency.pdf')
    (out / 'deck-online.html').write_text(deck_artifact(c), encoding='utf-8')
    HTML(string=notities(c)).write_pdf(out / 'Sprekersnotities pilotevaluatie GrowOn.pdf')
    HTML(string=onepager(c)).write_pdf(out / 'Vervolgvoorstel GrowOn Agency.pdf')
    print('klaar:', out)


if __name__ == '__main__':
    main()

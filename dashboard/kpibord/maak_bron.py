"""Maakt kpibord-bron.json uit de dashboard-database (projecten + resultaten).

Gebruik: python3 maak_bron.py <map met projecten/ en resultaten/> > kpibord-bron.json
De map is wat ArtifactData 'list' met out_dir wegschrijft. Het KPI-bord (Apps Script)
leest het nieuwste bestand uit de Drive-map "LINK. KPI-bord bron".
"""
import datetime as dt, glob, json, os, sys

# id op het bord (blijft gelijk zodat de handmatige tellingen bewaard blijven) -> project in het dashboard
BORD_ID = {
    'p-mostware': 'mostware', 'p-moyee': 'moyee', 'p-okcreative': 'ok', 'p-growon': 'growon',
    'p-pivot': 'pivot', 'p-greenearth': 'greenearth', 'p-bloei': 'bloei',
    'p-buildingbricks': 'bb', 'p-secondlife': 'slt', 'p-mostwarenext': 'mwnext', 'p-kubus': 'kubus',
}

def lees(map_, coll):
    out = []
    for f in sorted(glob.glob(os.path.join(map_, coll, '*.json'))):
        d = json.load(open(f))
        d = d.get('data', d)
        d['id'] = os.path.basename(f)[:-5]
        out.append(d)
    return out

def telt(p, r):
    a, o = r.get('afspraak') or 0, r.get('overdracht') or 0
    return {'100': a, '101': o}.get(p.get('teltAls') or '100+101', a + o)

def main(map_):
    projecten = {p['id']: p for p in lees(map_, 'projecten')}
    klanten, steam = [], {}
    for pid, bid in BORD_ID.items():
        p = projecten.get(pid)
        if not p or p.get('status') != 'actief' or not p.get('belstart'):
            continue
        weken = int(p.get('periodeWeken') or 4)
        anker = p.get('periodeAnker') or p['belstart']
        nr = int(p.get('periodeAnkerNr') or 1) if p.get('periodeAnker') else 1
        klanten.append({
            'id': bid, 'name': p.get('naam'), 'target': round((p.get('doelPerWeek') or 0) * weken),
            'weken': weken, 'wp': nr, 'wpStart': anker, 'telt': p.get('teltAls') or '100+101',
            'pilot': weken > 4,
        })
    for r in lees(map_, 'resultaten'):
        bid = BORD_ID.get(r.get('projectId'))
        p = projecten.get(r.get('projectId'))
        if not bid or not p:
            continue
        wk = '%d-W%02d' % (r['jaar'], r['week'])
        steam.setdefault(wk, {})[bid] = steam.get(wk, {}).get(bid, 0) + telt(p, r)
    # pilots onderaan, verder de vaste volgorde van het bord
    klanten.sort(key=lambda k: k['pilot'])
    t_steam = max(steam) if steam else None
    json.dump({'gemaakt': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               'bron': 'LINK. management dashboard', 'steamTot': t_steam,
               'klanten': klanten, 'steam': steam}, sys.stdout, ensure_ascii=False, separators=(',', ':'))

if __name__ == '__main__':
    main(sys.argv[1])

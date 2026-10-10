"""Points for the card's Nearby section: raw/nearby/ + docs/toronto/data/institutions.geojson
-> docs/toronto/data/nearby.json

  {"groups": {"library": [[lon, lat, name], ...], "centre": [...], "er": [...],
              "park": [[lon, lat], ...], "playground": [...], "tennis": [...], "offleash": [...]}}

library   Toronto Public Library branches with a building (PhysicalBranch = 1).
centre    City community recreation centres. The City's file also lists schools whose gyms it
          programs as "Community Centre"; those are left out, so this is the centres themselves.
er        Hospitals with an emergency department, from the institutions layer.
park, playground, tennis, offleash
          City parks, and the parks listing a playground, tennis courts or a dog off-leash area
          (one point per park, so a park with six courts counts once). Toronto's open data has no
          pool or rink locations, so they aren't counted here.
Describe only: the card names the nearest of each and counts what's within 1 km; nothing is ranked."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'nearby')
DATA = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data')
r5 = lambda c: [round(c[0], 5), round(c[1], 5)]
SMALL = {'and', 'of', 'the', 'at', 'on', 'in', 'for', 'de', 'la'}


def title(s):
    words = re.sub(r'\s+', ' ', s.strip()).lower().split(' ')
    out = []
    for i, w in enumerate(words):
        w = '-'.join(p[:1].upper() + p[1:] for p in w.split('-')) if (i == 0 or w not in SMALL) else w
        out.append(re.sub(r"^(O'|Mc)(\w)", lambda m: m.group(1) + m.group(2).upper(), w))
    return ' '.join(out).replace("'S ", "'s ").replace("'S", "'s")


groups = {k: [] for k in ('library', 'centre', 'er', 'park', 'playground', 'tennis', 'offleash')}
for r in json.load(open(os.path.join(RAW, 'tpl_branches.json'))):
    if str(r.get('PhysicalBranch')) == '1' and r.get('Lat') and r.get('Long'):
        groups['library'].append(r5([float(r['Long']), float(r['Lat'])]) + [r['BranchName'] + ' branch'])
for f in json.load(open(os.path.join(RAW, 'parks_rec.geojson')))['features']:
    p, g = f['properties'], f['geometry']
    if not g: continue
    c = r5(g['coordinates'][0] if g['type'] == 'MultiPoint' else g['coordinates'])
    am = set((p.get('AMENITIES') or '').split(', '))
    if p['TYPE'] == 'Community Centre' and not re.search(r'SCHOOL|COLLEGIATE|INSTITUTE|ACADEMY', p['ASSET_NAME']):
        groups['centre'].append(c + [title(p['ASSET_NAME'])])
    if p['TYPE'] == 'Park':
        groups['park'].append(c)
        if 'Playground' in am: groups['playground'].append(c)
        if 'Tennis Court' in am: groups['tennis'].append(c)
        if 'Dog Off-Leash Area' in am: groups['offleash'].append(c)
for f in json.load(open(os.path.join(DATA, 'institutions.geojson')))['features']:
    if f['properties'].get('ed'): groups['er'].append(f['geometry']['coordinates'] + [f['properties']['name']])

json.dump({'groups': groups}, open(os.path.join(DATA, 'nearby.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('nearby:', {k: len(v) for k, v in groups.items()})

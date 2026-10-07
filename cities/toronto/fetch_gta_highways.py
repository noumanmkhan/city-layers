"""Fetch the GTA's 400-series highways (and the QEW and 407 ETR) from OpenStreetMap via the
Overpass API into raw/gta_motorways.json. Run from GitHub Actions (or any machine that can
reach overpass-api.de).

Inside Toronto the map uses the City's own expressway centrelines; this file supplies the parts
that run beyond the city limits, so the highways can be followed across Halton, Peel, York and
Durham. Only carriageways tagged highway=motorway are fetched (no ramps), with their ref and name.
The box matches the map's pan limits."""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (43.05, -80.6, 44.75, -78.2)   # south, west, north, east
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
QUERY = f"""
[out:json][timeout:240];
way["highway"="motorway"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out tags geom;
"""


def fetch():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'toronto-layers-pipeline (github.com/noumanmkhan/toronto-layers)'})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:
            print('  retry', attempt + 1, url, e)
            time.sleep(15 * (attempt + 1))
    raise SystemExit('Overpass request failed')


res = fetch()
ways = []
for el in res.get('elements', []):
    if el.get('type') != 'way' or 'geometry' not in el:
        continue
    t = el.get('tags', {})
    ways.append({'ref': t.get('ref', ''), 'name': t.get('name', ''),
                 'coords': [[round(p['lon'], 5), round(p['lat'], 5)] for p in el['geometry']]})
os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
with open(os.path.join(HERE, 'raw', 'gta_motorways.json'), 'w') as f:
    json.dump({'source': 'OpenStreetMap contributors (ODbL) via Overpass API', 'bbox': BBOX, 'ways': ways}, f, separators=(',', ':'))
refs = {}
for w in ways:
    refs[w['ref']] = refs.get(w['ref'], 0) + 1
print('wrote raw/gta_motorways.json:', len(ways), 'ways; refs:', dict(sorted(refs.items())))

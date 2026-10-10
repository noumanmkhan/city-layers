"""Fetch rail lines and stations under construction from OpenStreetMap (Overpass) for one city's
regional box into cities/<city>/raw/construction/osm.json. Run from GitHub Actions (the *Fetch
transit construction lines* workflow); the sandbox can't reach Overpass.

Grabs everything tagged as rail under construction (railway=construction with construction=subway /
light_rail / rail / monorail, or the construction:railway=* lifecycle prefix), stations under
construction, and route relations marked as under construction. Nothing is chosen here: the build
(engine/construction.py) keeps only the projects listed in cities/<city>/construction.json, matched
by name, ref or operator, so new OSM mapping can't add a line to the map by itself.

Usage: python3 engine/fetch_construction.py <city>
"""
import json, os, sys, time, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
city = sys.argv[1]
cfg = json.load(open(os.path.join(ROOT, 'cities', city, 'city.json')))
(s, w), (n, e) = cfg['view']['region']
BOX = f'{s},{w},{n},{e}'
OUT = os.path.join(ROOT, 'cities', city, 'raw', 'construction')
os.makedirs(OUT, exist_ok=True)
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
QUERY = f"""
[out:json][timeout:600];
(
  way["railway"="construction"]({BOX});
  way["construction:railway"]({BOX});
  way["railway"]["construction"~"^(subway|light_rail|rail|monorail|tram)$"]({BOX});
  node["railway"="station"]["construction"="yes"]({BOX});
  node["construction:railway"="station"]({BOX});
  node["railway"="construction"]({BOX});
  node["public_transport"="station"]["construction"]({BOX});
  node["construction"="station"]({BOX});
);
out geom tags;
rel["route"~"^(subway|light_rail|train|tram|monorail)$"]["state"~"construction|proposed"]({BOX});
out geom tags;
rel["construction:route"]({BOX});
out geom tags;
"""


def fetch():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except Exception as ex:
            print('  retry', attempt + 1, url, ex)
            time.sleep(20 * (attempt + 1))
    raise SystemExit('Overpass request failed')


res = fetch()
els = res.get('elements', [])
slim = []
for el in els:
    o = {'type': el['type'], 'id': el['id'], 'tags': el.get('tags', {})}
    if el['type'] == 'node':
        o['lat'], o['lon'] = el['lat'], el['lon']
    elif el['type'] == 'way':
        o['geom'] = [[round(p['lon'], 6), round(p['lat'], 6)] for p in el.get('geometry', [])]
    else:
        o['members'] = [{'type': m['type'], 'ref': m['ref'], 'role': m.get('role', ''),
                         **({'geom': [[round(p['lon'], 6), round(p['lat'], 6)] for p in m['geometry']]} if m.get('geometry') else {}),
                         **({'lat': m['lat'], 'lon': m['lon']} if 'lat' in m else {})} for m in el.get('members', [])]
    slim.append(o)
json.dump({'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'box': BOX, 'elements': slim},
          open(os.path.join(OUT, 'osm.json'), 'w'), separators=(',', ':'))

# A short inventory for picking projects: names/refs/operators and what they are.
from collections import Counter
inv = Counter()
for o in slim:
    t = o['tags']
    kind = t.get('construction') or t.get('construction:railway') or t.get('railway') or t.get('route') or t.get('construction:route') or ''
    label = t.get('name') or t.get('ref') or t.get('operator') or '(unnamed)'
    inv[f"{o['type']:8} {kind:12} {label} | op={t.get('operator', '')}"] += 1
with open(os.path.join(OUT, 'inventory.txt'), 'w') as f:
    for k, v in sorted(inv.items()):
        f.write(f'{v:4}  {k}\n')
print(city, len(slim), 'elements;', len(inv), 'distinct labels')

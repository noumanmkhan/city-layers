"""Fetch universities, colleges and hospitals in and around Toronto from OpenStreetMap (Overpass API)
into raw/institutions_osm.json, to place and check the curated list in institutions.py. Run from
GitHub Actions (the *Fetch institutions* workflow); the sandbox can't reach Overpass.

Each element keeps its name, OSM id, centre and the tags that matter for the rules (operator,
operator:type, healthcare, emergency, website)."""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (43.57, -79.65, 43.87, -79.10)   # the City of Toronto plus a margin (Shouldice, just north of Steeles)
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
QUERY = f"""
[out:json][timeout:240];
nwr["amenity"~"^(university|college|hospital)$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out tags center;
"""
KEEP = ('name', 'alt_name', 'official_name', 'short_name', 'amenity', 'operator', 'operator:type', 'healthcare',
        'emergency', 'website', 'addr:street', 'addr:housenumber')


def fetch():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except Exception as e:
            print('  retry', attempt + 1, url, e)
            time.sleep(20 * (attempt + 1))
    raise SystemExit('Overpass request failed')


els = []
for el in fetch().get('elements', []):
    t = el.get('tags', {})
    c = el if el.get('type') == 'node' else el.get('center')
    if not t.get('name') or not c or 'lat' not in c: continue
    els.append({'osm': el['type'][0] + str(el['id']), 'at': [round(c['lon'], 5), round(c['lat'], 5)],
                **{k: t[k] for k in KEEP if k in t}})
els.sort(key=lambda e: (e['amenity'], e['name']))
json.dump({'source': 'OpenStreetMap contributors (ODbL) via Overpass API', 'bbox': BBOX, 'elements': els},
          open(os.path.join(HERE, 'raw', 'institutions_osm.json'), 'w'), ensure_ascii=False, indent=0)
print(len(els), 'elements:', {a: sum(1 for e in els if e['amenity'] == a) for a in ('university', 'college', 'hospital')})

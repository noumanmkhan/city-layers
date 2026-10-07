"""Fetch the named communities of the GTA (Meadowvale, Port Credit, Woodbridge, Unionville,
Brooklin...) from OpenStreetMap via the Overpass API into raw/gta_places.json. Run from GitHub
Actions (or any machine that can reach overpass-api.de).

Most GTA municipalities don't publish neighbourhood boundaries the way Toronto does, but their
communities are well known by name, and OpenStreetMap records them as place points (or areas,
reduced here to their centre): towns, villages and hamlets, suburbs, quarters and
neighbourhoods. gta_places.py keeps the ones inside the 24 surrounding municipalities, for
search suggestions. The box covers Halton, Peel, York and Durham with a margin."""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BBOX = (43.25, -80.30, 44.50, -78.55)   # south, west, north, east
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
QUERY = f"""
[out:json][timeout:240];
nwr["place"~"^(town|village|hamlet|suburb|quarter|neighbourhood)$"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out tags center;
"""


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
            time.sleep(15 * (attempt + 1))
    raise SystemExit('Overpass request failed')


res = fetch()
places = []
for el in res.get('elements', []):
    t = el.get('tags', {})
    c = el if el.get('type') == 'node' else el.get('center')
    if not c or 'lat' not in c: continue
    places.append({'name': t['name'], 'place': t['place'], 'osm': el['type'][0] + str(el['id']),
                   'alt': [t[k] for k in ('alt_name', 'old_name', 'official_name') if t.get(k)],
                   'at': [round(c['lon'], 5), round(c['lat'], 5)]})
os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
with open(os.path.join(HERE, 'raw', 'gta_places.json'), 'w') as f:
    json.dump({'source': 'OpenStreetMap contributors (ODbL) via Overpass API', 'bbox': BBOX, 'places': places}, f, ensure_ascii=False, separators=(',', ':'))
kinds = {}
for p in places: kinds[p['place']] = kinds.get(p['place'], 0) + 1
print('wrote raw/gta_places.json:', len(places), 'places;', kinds)

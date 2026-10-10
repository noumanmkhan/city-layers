"""Fetch an accurate outline of the lakes around the GTA (Lake Ontario, Lake Simcoe, Lake Scugog)
from OpenStreetMap via the Overpass API into raw/gta_lakes.geojson. Run from GitHub Actions
(the *Fetch GTA shoreline* workflow); the sandbox can't reach Overpass.

Why: beyond the city limits the map used Natural Earth's 10m lakes, which are drawn for a whole-
continent scale. Its Lake Ontario shore sits up to a kilometre or two inland in places, so Port
Credit, Port Credit GO, Frenchman's Bay and Ajax's waterfront looked like they were in the lake.
OpenStreetMap's lake polygons follow the real shore.

Each lake is an OSM multipolygon relation (natural=water). Its outer ways are joined into rings
with shapely's polygonize, inner ways (islands) are cut out, and the result is clipped to a box
a little larger than the map's pan limits and lightly simplified (about 5 m), which keeps the
raw file small."""
import json, os, time, urllib.parse, urllib.request
from shapely.geometry import LineString, box, mapping
from shapely.ops import polygonize, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'gta_lakes.geojson')
CLIP = box(-80.8, 42.9, -78.0, 44.9)       # west, south, east, north: the map's max bounds plus a margin
LAKES = ['Lake Ontario', 'Lake Simcoe', 'Lake Scugog']
ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
QUERY = """
[out:json][timeout:600][maxsize:1073741824];
rel["natural"="water"]["name"~"^(%s)$"](43.0,-80.6,44.8,-78.2);
out geom;
""" % '|'.join(LAKES)


def fetch():
    data = urllib.parse.urlencode({'data': QUERY}).encode()
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.load(r)
        except Exception as e:
            print('  retry', attempt + 1, url, e)
            time.sleep(20 * (attempt + 1))
    raise SystemExit('Overpass request failed')


def rnd(c):
    if isinstance(c[0], (int, float)): return [round(c[0], 5), round(c[1], 5)]
    return [rnd(x) for x in c]


res = fetch()
feats, seen = [], set()
for rel in res.get('elements', []):
    if rel.get('type') != 'relation': continue
    name = rel.get('tags', {}).get('name')
    if name not in LAKES or name in seen: continue
    lines = {'outer': [], 'inner': []}
    for m in rel.get('members', []):
        if m.get('type') == 'way' and m.get('geometry') and len(m['geometry']) > 1:
            lines['inner' if m.get('role') == 'inner' else 'outer'].append(LineString([(p['lon'], p['lat']) for p in m['geometry']]))
    outer = unary_union(list(polygonize(unary_union(lines['outer']))))
    inner = unary_union(list(polygonize(unary_union(lines['inner'])))) if lines['inner'] else None
    g = outer.difference(inner) if inner is not None and not inner.is_empty else outer
    g = g.buffer(0).intersection(CLIP).simplify(0.00005, preserve_topology=True)
    if g.is_empty:
        print('  !', name, 'came out empty'); continue
    seen.add(name)
    m = mapping(g)
    feats.append({'type': 'Feature', 'properties': {'name': name, 'osm': 'r%d' % rel['id']},
                  'geometry': {'type': m['type'], 'coordinates': rnd(m['coordinates'])}})
    print(name, 'r%d' % rel['id'], 'outer ways', len(lines['outer']), 'inner', len(lines['inner']), 'area deg2', round(g.area, 4))
missing = [n for n in LAKES if n not in seen]
if missing: raise SystemExit('lakes not found: ' + ', '.join(missing))
json.dump({'type': 'FeatureCollection', 'source': 'OpenStreetMap contributors (ODbL) via Overpass API', 'features': feats},
          open(OUT, 'w'), separators=(',', ':'))
print('wrote', OUT, os.path.getsize(OUT) // 1024, 'KB')

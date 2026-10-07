"""Named communities in the GTA's 24 surrounding municipalities, for search suggestions:
type "Meadowvale" and the map switches to the regional view and flies there.
Input: raw/gta_places.json (fetched by fetch_gta_places.py), the municipal boundaries in
raw/neighbours/, and their names from ../../docs/toronto/data/base.geojson. Output: ../../docs/toronto/data/region_places.json
  [{"name", "muni", "region", "kind", "at": [lon, lat], "alt": [...]}]

Kept: places inside one of the 24 municipalities (Toronto has its own neighbourhoods and
known-as names). Dropped: a place that just repeats its municipality's name (Oakville in
Oakville), and repeats of the same name in the same municipality within 3 km (OSM often has
both a point and an area), keeping the larger kind of place."""
import json, os, math
from shapely.geometry import shape, Point
from shapely.prepared import prep

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data')
RANK = {'town': 0, 'village': 1, 'suburb': 2, 'quarter': 3, 'neighbourhood': 4, 'hamlet': 5}
LABEL = {'town': 'Town', 'village': 'Village', 'suburb': 'Community', 'quarter': 'Community',
         'neighbourhood': 'Neighbourhood', 'hamlet': 'Hamlet'}

# Test against each municipality's true boundary (raw/neighbours/, from OpenStreetMap). The map's
# copies are trimmed to a coarse lake outline, which shaves off shoreline places like Port Credit.
base = [f for f in json.load(open(os.path.join(DOCS, 'base.geojson')))['features'] if f['properties'].get('kind') == 'neighbour']
munis = []
NB = os.path.join(HERE, 'raw', 'neighbours')
for fn in sorted(os.listdir(NB)):
    g = shape(json.load(open(os.path.join(NB, fn)))['geometry']).buffer(0)
    # Name it after the map's municipality whose label point falls inside it.
    m = next((f['properties'] for f in base if g.contains(Point(f['properties']['lp']))), None)
    if m: munis.append((m['name'], m['region'], prep(g)))
assert len(munis) == len(base), 'could not match every municipality boundary'


def muni_of(pt):
    return next(((n, r) for n, r, g in munis if g.contains(pt)), None)


raw = json.load(open(os.path.join(HERE, 'raw', 'gta_places.json')))['places']


def km(a, b):
    return math.hypot((a[0] - b[0]) * 80.5, (a[1] - b[1]) * 111.2)


out = []
for p in sorted(raw, key=lambda p: RANK[p['place']]):
    pt = Point(p['at'])
    m = muni_of(pt)
    if not m or p['name'].strip().lower() == m[0].lower(): continue
    if any(o['name'] == p['name'] and o['muni'] == m[0] and km(o['at'], p['at']) < 3 for o in out): continue
    out.append({'name': p['name'], 'muni': m[0], 'region': m[1], 'kind': LABEL[p['place']], 'at': p['at'],
                **({'alt': p['alt']} if p['alt'] else {})})
out.sort(key=lambda o: (o['name'], o['muni']))
json.dump(out, open(os.path.join(DOCS, 'region_places.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
from collections import Counter
print('region places:', len(out), dict(Counter(o['kind'] for o in out)))

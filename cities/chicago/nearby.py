"""Points for the card's Nearby section: raw/nearby/ + docs/chicago/data/institutions.geojson
-> docs/chicago/data/nearby.json (same shape as Toronto's).

library   Chicago Public Library branches (City Data Portal).
centre    Named community centres in OpenStreetMap (many are Park District field houses).
er        Hospitals with an emergency department, from the institutions layer.
park, playground, tennis
          From OpenStreetMap, inside the city: named parks; playgrounds; tennis courts, merged so
          courts within 80 m of each other count as one place. Anything tagged private, customers-
          or members-only was left out at fetch time. The Park District's own facility list on the
          City portal was retired in 2016, hence OSM. Pools and rinks were tried and left out: OSM
          has only about 30 public pools named in the city against the Park District's 70-plus, so
          a count of "0 pools" nearby would often be wrong.
Describe only: the card names the nearest of each and counts what's within 1 km; nothing is ranked."""
import json, math, os
from shapely.geometry import shape, Point
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'nearby')
DATA = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data')
CITY = unary_union([shape(f['geometry']) for f in json.load(open(os.path.join(DATA, 'sides.geojson')))['features']]).buffer(0.002)
inside = lambda c: CITY.contains(Point(c))
metres = lambda a, b: math.hypot((a[0] - b[0]) * 83000, (a[1] - b[1]) * 111000)

groups = {k: [] for k in ('library', 'centre', 'er', 'park', 'playground', 'tennis')}
for r in json.load(open(os.path.join(RAW, 'cpl_branches.json'))):
    loc = r.get('location') or {}
    if loc.get('latitude'):
        groups['library'].append([round(float(loc['longitude']), 5), round(float(loc['latitude']), 5), r['branch_'].strip() + ' branch'])
courts = []
for e in json.load(open(os.path.join(RAW, 'osm_amenities.json'))):
    c = e['at']
    if not inside(c): continue
    kind = e.get('leisure') or e.get('amenity')
    if kind == 'community_centre' and e.get('name'): groups['centre'].append(c + [e['name']])
    elif kind == 'park' and e.get('name'): groups['park'].append(c)
    elif kind == 'playground': groups['playground'].append(c)
    elif kind == 'pitch': courts.append(c)
for c in courts:   # one point per group of courts
    if not any(metres(c, t) < 80 for t in groups['tennis']): groups['tennis'].append(c)
for f in json.load(open(os.path.join(DATA, 'institutions.geojson')))['features']:
    if f['properties'].get('ed'): groups['er'].append(f['geometry']['coordinates'] + [f['properties']['name']])

json.dump({'groups': groups}, open(os.path.join(DATA, 'nearby.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('nearby:', {k: len(v) for k, v in groups.items()})

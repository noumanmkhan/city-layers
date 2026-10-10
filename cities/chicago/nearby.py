"""Points for the card's Nearby section: raw/nearby/ + docs/chicago/data/institutions.geojson
-> docs/chicago/data/nearby.json (same shape as Toronto's).

library   Chicago Public Library branches (City Data Portal).
centre    Publicly run community centres open to everyone (rule agreed October 10, 2026): Chicago Park
          District fieldhouses (the Park District's current list, placed by the Census geocoder, or
          by the same-named park in OpenStreetMap when the geocoder misses) and the City's six DFSS
          Community Service Centers. Beach houses, visitor and nature centres are left out. OSM's
          community_centre tag is no longer used: it mixes in churches, clubs and advocacy groups.
er        Hospitals with an emergency department, from the institutions layer.
park, playground, tennis
          From OpenStreetMap, inside the city: named parks; playgrounds; tennis courts, merged so
          courts within 80 m of each other count as one place. Anything tagged private, customers-
          or members-only was left out at fetch time. The Park District's own facility list on the
          City portal was retired in 2016, hence OSM. Pools and rinks were tried and left out: OSM
          has only about 30 public pools named in the city against the Park District's 70-plus, so
          a count of "0 pools" nearby would often be wrong.
Describe only: the card names the nearest of each and counts what is within the radius in city.json; nothing is ranked."""
import json, math, os, re
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
        name = r['branch_'].strip().replace('Washtington', 'Washington')   # typo in the City's file
        groups['library'].append([round(float(loc['longitude']), 5), round(float(loc['latitude']), 5),
                                  name if 'Library Center' in name else name + ' branch'])
courts = []
for e in json.load(open(os.path.join(RAW, 'osm_amenities.json'))):
    c = e['at']
    if not inside(c): continue
    kind = e.get('leisure') or e.get('amenity')
    if kind == 'park' and e.get('name'): groups['park'].append(c)
    elif kind == 'playground': groups['playground'].append(c)
    elif kind == 'pitch': courts.append(c)
# Community centres: Park District fieldhouses and DFSS Community Service Centers.
C = os.path.join(RAW, 'centres')
osm_parks = {}
for e in json.load(open(os.path.join(RAW, 'osm_amenities.json'))):
    if e.get('leisure') == 'park' and e.get('name') and inside(e['at']): osm_parks.setdefault(e['name'].lower(), e['at'])
SKIP = re.compile(r'beach house|visitor center|environmental center|southfield', re.I)
def tidy(n):
    n = re.sub(r'\s*\(Park No\. ?\d+\)', '', n.replace('FIeldhouse', 'Fieldhouse'))
    return re.sub(r'\s*Park\s*\|\s*Fieldhouse$', ' Fieldhouse', n).strip()
def same_place(asked, got):
    # The geocoder can settle for a near miss (S. Washtenaw -> N. Washtenaw, Olcott -> Wolcott in
    # another ZIP); keep a match only if house number, direction and ZIP agree.
    def key(a):
        a = re.sub(r'\b(NORTH|SOUTH|EAST|WEST)\b', lambda m: m.group(1)[0], a.upper().replace('.', ''))
        num = re.match(r'\s*(\d+)\s+([NSEW])?\b', a); zipc = re.findall(r'\b(6\d{4})\b', a)
        return (num.group(1), num.group(2)) if num else None, zipc[-1] if zipc else None
    return bool(got) and key(asked) == key(got)
placed, fell_back, dropped = 0, [], []
for f in json.load(open(os.path.join(C, 'fieldhouses.json'))):
    name = tidy(f['name'])
    if SKIP.search(name): continue
    at = f.get('at') if same_place(f['address'], f.get('matched', '')) else None
    if not at:   # geocoder missed (or matched a different address): the same-named park in OSM, inside the city
        k = re.sub(r'\s*(fieldhouse|park)\b.*', '', name, flags=re.I).strip().lower()
        at = next((osm_parks[n] for n in (k + ' park', k + ' playlot park', k) if n in osm_parks), None)
        (fell_back if at else dropped).append(name)
    if at and inside(at): groups['centre'].append([round(at[0], 5), round(at[1], 5), name]); placed += 1
for r in json.load(open(os.path.join(C, 'dfss_community_service_centers.json'))):
    loc = r.get('location') or {}
    if loc.get('latitude'):
        groups['centre'].append([round(float(loc['longitude']), 5), round(float(loc['latitude']), 5),
                                 r['site'].strip().replace(' Center', ' Community Service Center')])
print('centres: fieldhouses', placed, '(by park name:', ', '.join(fell_back) + ')', 'not placed:', dropped)
for c in courts:   # one point per group of courts
    if not any(metres(c, t) < 80 for t in groups['tennis']): groups['tennis'].append(c)
for f in json.load(open(os.path.join(DATA, 'institutions.geojson')))['features']:
    if f['properties'].get('ed'): groups['er'].append(f['geometry']['coordinates'] + [f['properties']['name']])

json.dump({'groups': groups}, open(os.path.join(DATA, 'nearby.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('nearby:', {k: len(v) for k, v in groups.items()})

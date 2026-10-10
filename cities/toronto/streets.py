"""raw/streets.json (from fetch_streets.py) -> tmp/streets.geojson and tmp/collectors.geojson.

Main streets: major and minor arterials (the streets people navigate by: King, Queen,
Eglinton, Don Mills...), each street's segments merged into one feature per name and class.
Collectors: the City's "Collector" class (the next tier down, where many bus routes run),
for their own layer, merged per name; stretches that sit on a main street are left out."""
import json, os
from shapely.geometry import shape, mapping
from shapely.ops import linemerge, unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(HERE, 'raw', 'streets.json')))
CLASSES = {'Major Arterial': 'major', 'Minor Arterial': 'minor'}

segs = {}
for layer, cls in CLASSES.items():
    for f in raw[layer]['features']:
        name = (f['properties'].get('LINEAR_NAME_FULL') or '').strip()
        if not name or 'ramp' in name.lower() or not f.get('geometry'):
            continue
        segs.setdefault((name, cls), []).append(shape(f['geometry']))

feats = []
for (name, cls), gs in segs.items():
    u = unary_union(gs)
    m = linemerge(u) if u.geom_type == "MultiLineString" else u
    feats.append({'type': 'Feature', 'properties': {'name': name, 'cls': cls, 'len': round(m.length * 1000, 1)},
                  'geometry': mapping(m)})
# Longest first, majors before minors: the page labels streets in this order.
feats.sort(key=lambda f: (f['properties']['cls'] != 'major', -f['properties']['len']))
os.makedirs(os.path.join(HERE, 'tmp'), exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, 'tmp', 'streets.geojson'), 'w'))
print('streets', len(feats), 'features:', sum(f['properties']['cls'] == 'major' for f in feats), 'major')

# Collectors, minus anything within ~12 m of a main street (a street can change class along its length).
mains = unary_union([shape(f['geometry']) for f in feats]).buffer(0.00012)
cols = {}
for f in raw['Collector']['features']:
    name = (f['properties'].get('LINEAR_NAME_FULL') or '').strip()
    if not name or 'ramp' in name.lower() or not f.get('geometry'):
        continue
    cols.setdefault(name, []).append(shape(f['geometry']))
cf = []
for name, gs in cols.items():
    u = unary_union(gs).difference(mains)
    if u.is_empty: continue
    m = linemerge(u) if u.geom_type == 'MultiLineString' else u
    parts = [p for p in getattr(m, 'geoms', [m]) if p.geom_type == 'LineString' and p.length > 0.0008]   # ~80 m
    if not parts: continue
    g = parts[0] if len(parts) == 1 else {'type': 'MultiLineString', 'coordinates': [list(p.coords) for p in parts]}
    length = sum(p.length for p in parts)
    cf.append({'type': 'Feature', 'properties': {'name': name, 'cls': 'coll', 'len': round(length * 1000, 1)},
               'geometry': g if isinstance(g, dict) else mapping(g)})
cf.sort(key=lambda f: -f['properties']['len'])
json.dump({'type': 'FeatureCollection', 'features': cf}, open(os.path.join(HERE, 'tmp', 'collectors.geojson'), 'w'))
print('collectors', len(cf), 'streets')

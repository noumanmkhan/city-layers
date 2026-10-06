"""raw/streets.json (from fetch_streets.py) -> tmp/streets.geojson.

Keeps major and minor arterials (the streets people navigate by: King, Queen,
Eglinton, Don Mills...) and merges each street's segments into one feature per
name and class. Collectors are fetched but not drawn yet."""
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

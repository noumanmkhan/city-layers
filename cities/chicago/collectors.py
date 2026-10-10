"""Collector streets for their own layer: OpenStreetMap's tertiary roads inside the city (raw/osm_arterials.json,
fetched by fetch.py with the main streets), merged per name -> tmp/collectors.geojson. Stretches within ~12 m of
a drawn main street are left out (OSM can tag parts of one street differently). Run after the main streets are
built and simplified (needs docs/chicago/data/streets.geojson and base.geojson)."""
import json, os
from shapely.geometry import LineString, shape, mapping
from shapely.ops import linemerge, unary_union
from names import street_name

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data')
city = unary_union([shape(f['geometry']) for f in json.load(open(os.path.join(DATA, 'base.geojson')))['features'] if f['properties']['kind'] == 'city'])
mains = unary_union([shape(f['geometry']) for f in json.load(open(os.path.join(DATA, 'streets.geojson')))['features']]).buffer(0.00013)
by = {}
for w in json.load(open(os.path.join(HERE, 'raw', 'osm_arterials.json')))['elements']:
    t = w['tags']
    if t.get('highway') != 'tertiary' or len(w.get('geometry', [])) < 2 or not t.get('name'):
        continue
    by.setdefault(street_name(t['name']), []).append(LineString([(p['lon'], p['lat']) for p in w['geometry']]))
feats = []
for name, gs in by.items():
    u = unary_union(gs).intersection(city).difference(mains)
    if u.is_empty: continue
    u = unary_union([p for p in getattr(u, 'geoms', [u]) if p.geom_type == 'LineString'])
    if u.is_empty: continue
    m = linemerge(u) if u.geom_type == 'MultiLineString' else u
    parts = [p for p in getattr(m, 'geoms', [m]) if p.length > 0.001]   # ~80 m
    if not parts: continue
    g = parts[0] if len(parts) == 1 else {'type': 'MultiLineString', 'coordinates': [list(p.coords) for p in parts]}
    feats.append({'type': 'Feature', 'properties': {'name': name, 'cls': 'coll', 'len': round(sum(p.length for p in parts) * 1000, 1)},
                  'geometry': g if isinstance(g, dict) else mapping(g)})
feats.sort(key=lambda f: -f['properties']['len'])
os.makedirs(os.path.join(HERE, 'tmp'), exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(HERE, 'tmp', 'collectors.geojson'), 'w'))
print('collectors', len(feats), 'streets')

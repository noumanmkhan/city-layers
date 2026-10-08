"""Outlines for "Focus on a county / region" in the regional view: one shape per region around the city.
Usage: python3 engine/regions.py <city>   (run after the city's base.geojson is built)

Region keys are the "region" property of the municipalities in docs/<city>/data/base.geojson ("Peel",
"DuPage County"); the page names them with outside.regionPill from city.json.
- If the city's build wrote cities/<city>/tmp/region_areas.geojson (real boundaries, such as Chicagoland's
  county lines), that is used.
- Otherwise each region is the union of its municipalities (the GTA's four regional municipalities).
Output: docs/<city>/data/region_areas.geojson  {region, lp}
"""
import json, os, sys
from shapely.geometry import shape, mapping
from shapely.ops import unary_union, polylabel

HERE = os.path.dirname(os.path.abspath(__file__))
city = sys.argv[1] if len(sys.argv) > 1 else sys.exit('usage: regions.py <city>')
DATA = os.path.join(HERE, '..', 'docs', city, 'data')
override = os.path.join(HERE, '..', 'cities', city, 'tmp', 'region_areas.geojson')
base = json.load(open(os.path.join(DATA, 'base.geojson')))
keys = []
for f in base['features']:
    r = f['properties'].get('region')
    if f['properties'].get('kind') == 'neighbour' and r and r not in keys:
        keys.append(r)

if os.path.exists(override):
    shapes = {f['properties']['region']: shape(f['geometry']).buffer(0) for f in json.load(open(override))['features']}
else:
    shapes = {}
    for r in keys:
        parts = [shape(f['geometry']).buffer(0) for f in base['features'] if f['properties'].get('region') == r]
        shapes[r] = unary_union([p.buffer(0.0006) for p in parts]).buffer(-0.0006)   # close slivers between neighbours


def lp(g):
    big = max(getattr(g, 'geoms', [g]), key=lambda p: p.area)
    try: p = polylabel(big, tolerance=0.001)
    except Exception: p = big.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


feats = []
for r in keys:
    g = shapes.get(r)
    if g is None or g.is_empty:
        print('no outline for', r); continue
    g = g.simplify(0.0004, preserve_topology=True)
    feats.append({'type': 'Feature', 'properties': {'region': r, 'lp': lp(g)},
                  'geometry': json.loads(json.dumps(mapping(g)), parse_float=lambda v: round(float(v), 5))})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(DATA, 'region_areas.geojson'), 'w'), separators=(',', ':'))
print('region outlines:', city, [f['properties']['region'] for f in feats], os.path.getsize(os.path.join(DATA, 'region_areas.geojson')) // 1024, 'KB')

"""Chicago Landmark Districts: raw/heritage_districts.geojson -> tmp/heritage.geojson.

The City's boundary file dates from 2012, so districts designated since then are missing (noted in
the layer and in SOURCES.md). Names are tidied: a trailing "District" is dropped (the card adds
"Chicago Landmark District"), and two names cut short in the shapefile are written out in full,
following the City's list of districts (raw/landmark_districts.json)."""
import json, os, re
from shapely.geometry import shape, mapping
from shapely.ops import polylabel

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
FULL = {'Chatham-Greater Grand Crossing Com': 'Chatham-Greater Grand Crossing Commercial',
        'Beverly/Morgan Park Railroad Station': 'Beverly/Morgan Park Railroad Stations',
        'Ukrainian Village District Ext II': 'Ukrainian Village District Extension II'}


def label_pt(g):
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda p: p.area)
    try:
        p = polylabel(g, tolerance=0.0002)
    except Exception:
        p = g.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def nice(name):
    name = FULL.get(name.strip(), name.strip())
    return re.sub(r'\s+District(?=$|\s+Ext)', '', name).strip()


src = json.load(open('raw/heritage_districts.geojson'))
out = []
for f in src['features']:
    p = f['properties']
    if not f.get('geometry') or not p.get('NAME'):
        continue
    g = shape(f['geometry']).buffer(0)
    props = {'name': nice(p['NAME']), 'lp': label_pt(g)}
    if p.get('DATE_'):
        props['since'] = int(p['DATE_'][:4])
    out.append({'type': 'Feature', 'properties': props, 'geometry': mapping(g)})

out.sort(key=lambda f: f['properties']['name'])
os.makedirs('tmp', exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': out}, open('tmp/heritage.geojson', 'w'), separators=(',', ':'))
print(f'heritage: {len(out)} landmark districts')

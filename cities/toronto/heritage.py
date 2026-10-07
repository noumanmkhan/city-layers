"""Heritage Conservation Districts: raw/heritage_districts.geojson -> tmp/heritage.geojson.

Keeps only districts in force ("Designated District"). Ones "Under Study" or "Under Appeal" are left
out, so the map and the card never present them as protected. Phased districts keep their phase,
written "Harbord Village (Phase I)". The source marks a missing designation date as 1899-11-30."""
import json, os
from shapely.geometry import shape, mapping
from shapely.ops import polylabel

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)


def label_pt(g):
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda p: p.area)
    try:
        p = polylabel(g, tolerance=0.0002)
    except Exception:
        p = g.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def nice(name):
    base, _, phase = name.partition(' | ')
    phase = phase.replace(' (', ', ').rstrip(')')   # "Phase I (Madison Avenue)" -> "Phase I, Madison Avenue"
    return f'{base} ({phase})' if phase else base


src = json.load(open('raw/heritage_districts.geojson'))
out, skipped = [], []
for f in src['features']:
    p = f['properties']
    if p.get('HCD_TYPE') != 'Designated District' or not f.get('geometry'):
        skipped.append(f"{p.get('HCD_NAME')} ({p.get('HCD_TYPE')})")
        continue
    g = shape(f['geometry']).buffer(0)
    year = (p.get('HCD_DESDAT') or '')[:4]
    props = {'name': nice(p['HCD_NAME']), 'lp': label_pt(g)}
    if year and year > '1900':
        props['since'] = int(year)
    out.append({'type': 'Feature', 'properties': props, 'geometry': mapping(g)})

out.sort(key=lambda f: f['properties']['name'])
os.makedirs('tmp', exist_ok=True)
json.dump({'type': 'FeatureCollection', 'features': out}, open('tmp/heritage.geojson', 'w'), separators=(',', ':'))
print(f'heritage: {len(out)} districts in force; left out: {", ".join(skipped) or "none"}')

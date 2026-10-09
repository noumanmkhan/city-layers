"""School board trustee wards: raw/school_wards_2026.json + docs/toronto/data/wards.geojson
-> docs/toronto/data/school_wards.geojson.

Every 2026 trustee ward, for all four boards, is a group of whole City wards (the City Clerk's
reference chart), so each one is the union of those wards. It runs on the published, already
simplified wards so trustee-ward lines sit exactly on the City-ward lines.

Each feature: board ("tdsb", "tcdsb", "viamonde", "monavenir"), num (the board's ward number, a
string, as the election results file has it), area (Viamonde and MonAvenir's ward names, e.g.
"Est"), wards (the City wards it is made of) and lp (label point). The script stops if a board
leaves a City ward out or uses one twice."""
import json, os
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union, polylabel

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data')


def label_pt(g):
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda p: p.area)
    try:
        p = polylabel(g, tolerance=0.0002)
    except Exception:
        p = g.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def rounded(geom):
    def r(c):
        if isinstance(c[0], (int, float)): return [round(c[0], 5), round(c[1], 5)]
        return [r(x) for x in c]
    m = mapping(geom)
    return {'type': m['type'], 'coordinates': r(m['coordinates'])}


def parts(g): return list(g.geoms) if g.geom_type == 'MultiPolygon' else [g]


def merge(gs):
    """Union of neighbouring wards. Their simplified edges don't always meet exactly, which leaves
    hairline gaps inside the union; fill every hole except the wards' own (a pond, say)."""
    g = unary_union(gs).buffer(0)
    out = []
    for p in parts(g):
        keep = [r for r in p.interiors if Polygon(r).intersection(OWN_HOLES).area > 0.5 * Polygon(r).area]
        out.append(Polygon(p.exterior, keep))
    return out[0] if len(out) == 1 else MultiPolygon(out)


chart = json.load(open(os.path.join(HERE, 'raw', 'school_wards_2026.json')))
wards = {f['properties']['num']: shape(f['geometry']).buffer(0)
         for f in json.load(open(os.path.join(DOCS, 'wards.geojson')))['features']}
OWN_HOLES = unary_union([Polygon(r) for g in wards.values() for p in parts(g) for r in p.interiors])
out = []
for board, b in chart['boards'].items():
    used = sorted(n for ns in b['wards'].values() for n in ns)
    if used != sorted(wards):
        raise SystemExit(f'{board}: the chart must use each of the {len(wards)} City wards once; it uses {used}')
    for num, ns in b['wards'].items():
        g = merge([wards[n] for n in ns])
        props = {'board': board, 'num': num}
        if b.get('area', {}).get(num): props['area'] = b['area'][num]
        props.update(wards=sorted(ns), lp=label_pt(g))
        out.append({'type': 'Feature', 'properties': props, 'geometry': rounded(g)})

json.dump({'type': 'FeatureCollection', 'features': out}, open(os.path.join(DOCS, 'school_wards.geojson'), 'w'), separators=(',', ':'))
print('school wards:', ', '.join(f"{k} {len(v['wards'])}" for k, v in chart['boards'].items()))

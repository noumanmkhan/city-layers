"""GO Transit rail lines and UP Express, plus their stations.
Inputs: raw/go_routes.geojson, raw/go_stops.geojson (from Metrolinx's GTFS via agcghub/toronto-bus-map)
Outputs: tmp/go_lines.geojson (simplified later by mapshaper), ../docs/toronto/data/go_stations.geojson

One geometry per line (the full outbound route from Union). Each line gets an 'offset' rank so
the page can fan out lines that share track near Union instead of drawing them on top of each other.
Station names get a "GO" suffix on the map so they aren't confused with subway stations that share
a name (Kipling, Kennedy, Eglinton, Mount Pleasant...)."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw'); TMP = os.path.join(HERE, 'tmp'); OUT = os.path.join(HERE, '..', 'docs', 'toronto', 'data')
os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

# name shown, colour (Metrolinx), offset rank (lines leaving Union westward, then eastward;
# positive = right of the direction of travel from Union)
LINES = {
    'Lakeshore West': ('Lakeshore West', '#98002E', -2),
    'Milton':         ('Milton',         '#F57F25', -1),
    'Barrie':         ('Barrie',         '#003767',  0),
    'Kitchener':      ('Kitchener',      '#00853E',  1),
    'UP':             ('UP Express',     '#1F4E9C',  2),
    'Lakeshore East': ('Lakeshore East', '#FF0D00',  1),
    'Stouffville':    ('Stouffville',    '#794500',  0),
    'Richmond Hill':  ('Richmond Hill',  '#0099C7', -1),
}
PREFER = {'Kitchener': 'Kitchener', 'Lakeshore West': 'Niagara Falls'}   # skip seasonal/special variants



def thin(coords, min_m=60):
    """Drop points closer than min_m to the last kept one. The page shifts GO lines sideways by a few
    pixels to fan out shared track, and very short segments fold into small knots when offset."""
    out = [coords[0]]
    for p in coords[1:-1]:
        q = out[-1]
        if ((p[0] - q[0]) * 80000) ** 2 + ((p[1] - q[1]) * 111000) ** 2 >= min_m ** 2:
            out.append(p)
    out.append(coords[-1])
    return out


routes = json.load(open(os.path.join(RAW, 'go_routes.geojson')))['features']
lines = []
for key, (name, colour, off) in LINES.items():
    cands = [f for f in routes if f['properties']['line'] == key and f['properties']['dir'] == '0']
    if key in PREFER:
        cands = [f for f in cands if f['properties']['headsign'] == PREFER[key]] or cands
    best = max(cands, key=lambda f: len(f['geometry']['coordinates']))
    coords = thin([[round(x, 5), round(y, 5)] for x, y in best['geometry']['coordinates']])
    lines.append({'type': 'Feature', 'properties': {'line': key, 'name': name, 'color': colour, 'offset': off,
                                                    'to': best['properties']['headsign']},
                  'geometry': {'type': 'LineString', 'coordinates': coords}})

stops = json.load(open(os.path.join(RAW, 'go_stops.geojson')))['features']
st = collections.OrderedDict()
for f in stops:
    arr = [l for l in f['properties']['arr'] if l in LINES]
    n = f['properties']['name'].strip()
    n = n if n == 'Hamilton GO Centre' else n.replace(' GO', '')
    e = st.setdefault(n, {'lines': set(), 'pts': []})
    e['lines'] |= set(arr); e['pts'].append(f['geometry']['coordinates'])
pts = []
for n, e in st.items():
    x = sum(p[0] for p in e['pts']) / len(e['pts']); y = sum(p[1] for p in e['pts']) / len(e['pts'])
    label = {'Union Station': 'Union Station', 'Pearson Airport': 'Pearson Airport (UP)', 'Hamilton GO Centre': 'Hamilton GO Centre'}.get(n, n + ' GO')
    pts.append({'type': 'Feature', 'properties': {'name': label, 'lines': sorted(LINES[l][0] for l in e['lines']),
                                                  'hub': n == 'Union Station'},
                'geometry': {'type': 'Point', 'coordinates': [round(x, 5), round(y, 5)]}})

json.dump({'type': 'FeatureCollection', 'features': lines}, open(os.path.join(TMP, 'go_lines.geojson'), 'w'), separators=(',', ':'))

# Toronto-only version for the page's "Toronto (416)" mode: each line clipped at the city limits.
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
city = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(os.path.join(RAW, 'city_bundle1.json')))['formermun']['features']]).buffer(0.0008)
inside = []
for f in lines:
    g = shape(f['geometry']).intersection(city)
    if not g.is_empty:
        inside.append({'type': 'Feature', 'properties': f['properties'], 'geometry': mapping(g)})
json.dump({'type': 'FeatureCollection', 'features': inside}, open(os.path.join(TMP, 'go_lines_416.geojson'), 'w'), separators=(',', ':'))
json.dump({'type': 'FeatureCollection', 'features': pts}, open(os.path.join(OUT, 'go_stations.geojson'), 'w'), separators=(',', ':'))
print('go:', len(lines), 'lines,', len(pts), 'stations')

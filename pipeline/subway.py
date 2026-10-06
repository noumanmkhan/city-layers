"""Subway and LRT lines + stations from the TTC's GTFS-derived geometry.
Inputs: raw/ttc_rapid_routes.geojson, raw/ttc_rapid_stops.geojson
Outputs: tmp/subway_lines.geojson (simplified later), ../docs/data/subway_stations.geojson
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw'); TMP = os.path.join(HERE, 'tmp'); OUT = os.path.join(HERE, '..', 'docs', 'data')
os.makedirs(TMP, exist_ok=True); os.makedirs(OUT, exist_ok=True)

r = json.load(open(os.path.join(RAW, 'ttc_rapid_routes.geojson')))
s = json.load(open(os.path.join(RAW, 'ttc_rapid_stops.geojson')))
L = {'1': ('Line 1 Yonge–University', '#FFC425'), '2': ('Line 2 Bloor–Danforth', '#00A64F'),
     '4': ('Line 4 Sheppard', '#A8518A'), '5': ('Line 5 Eglinton', '#F58426'), '6': ('Line 6 Finch West', '#959595')}

lines = []
for f in r['features']:
    p = f['properties']
    if p['line'] in L and p['dir'] == '0':
        c = [[round(x, 5), round(y, 5)] for x, y in f['geometry']['coordinates']]
        lines.append({'type': 'Feature', 'properties': {'line': p['line'], 'name': L[p['line']][0], 'color': L[p['line']][1]},
                      'geometry': {'type': 'LineString', 'coordinates': c}})

# Merge platforms into one point per station; GTFS splits Bloor-Yonge into "Bloor" and "Yonge".
st = collections.OrderedDict()
for f in s['features']:
    arr = set(f['properties']['arr']) & set(L)
    if not arr: continue
    n = f['properties']['name']
    if n in ('Finch', 'Vaughan Metropolitan Centre'): n += ' Station'
    if n == 'York University': n = 'York University Station'
    n = re.sub(r' - Subway Platform$', '', n).replace(' Station', '')
    n = {'Bloor': 'Bloor-Yonge', 'Yonge': 'Bloor-Yonge'}.get(n, n)
    e = st.setdefault(n, {'lines': set(), 'pts': []}); e['lines'] |= arr; e['pts'].append(f['geometry']['coordinates'])
st['Union'] = {'lines': {'1'}, 'pts': [[-79.3806, 43.6453]]}  # missing from the source stop list

pts = []
for n, e in st.items():
    x = sum(p[0] for p in e['pts']) / len(e['pts']); y = sum(p[1] for p in e['pts']) / len(e['pts'])
    pts.append({'type': 'Feature', 'properties': {'name': n, 'lines': sorted(e['lines'])},
                'geometry': {'type': 'Point', 'coordinates': [round(x, 5), round(y, 5)]}})

json.dump({'type': 'FeatureCollection', 'features': lines}, open(os.path.join(TMP, 'subway_lines.geojson'), 'w'), separators=(',', ':'))
json.dump({'type': 'FeatureCollection', 'features': pts}, open(os.path.join(OUT, 'subway_stations.geojson'), 'w'), separators=(',', ':'))
print('subway:', len(lines), 'lines,', len(pts), 'stations')

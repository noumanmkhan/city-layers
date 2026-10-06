"""Subway and LRT lines + stations from the TTC's GTFS-derived geometry.
Inputs: raw/ttc_rapid_routes.geojson, raw/ttc_rapid_stops.geojson
Outputs: tmp/subway_lines.geojson (simplified later), ../docs/toronto/data/subway_stations.geojson
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw'); TMP = os.path.join(HERE, 'tmp'); OUT = os.path.join(HERE, '..', 'docs', 'toronto', 'data')
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
    raw = f['properties']['name']
    n = 'York University Station' if raw == 'York University' else raw
    n = re.sub(r' - Subway Platform$', '', n).replace(' Station', '')
    n = {'Bloor': 'Bloor-Yonge', 'Yonge': 'Bloor-Yonge'}.get(n, n)
    e = st.setdefault(n, {'lines': set(), 'pts': [], 'real': []})
    e['lines'] |= arr
    # GTFS also has headsign stops named after a terminus (a "Finch" stop that is really a platform at
    # Union). Entries named "... Station" are the station itself, so prefer them when they exist.
    (e['real'] if 'Station' in raw or raw == 'York University' else e['pts']).append(f['geometry']['coordinates'])
st['Union'] = {'lines': {'1'}, 'pts': [], 'real': [[-79.3806, 43.6453]]}  # missing from the source stop list

ends = [c for l in lines for c in (l['geometry']['coordinates'][0], l['geometry']['coordinates'][-1])]
pts = []
for n, e in st.items():
    use = e['real'] or e['pts']
    x = sum(p[0] for p in use) / len(use); y = sum(p[1] for p in use) / len(use)
    term = any(abs(x - a) < 0.004 and abs(y - b) < 0.003 for a, b in ends)
    pts.append({'type': 'Feature', 'properties': {'name': n, 'lines': sorted(e['lines']), 'terminus': term},
                'geometry': {'type': 'Point', 'coordinates': [round(x, 5), round(y, 5)]}})

json.dump({'type': 'FeatureCollection', 'features': lines}, open(os.path.join(TMP, 'subway_lines.geojson'), 'w'), separators=(',', ':'))
json.dump({'type': 'FeatureCollection', 'features': pts}, open(os.path.join(OUT, 'subway_stations.geojson'), 'w'), separators=(',', ':'))
print('subway:', len(lines), 'lines,', len(pts), 'stations')

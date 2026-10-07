"""Fetch Toronto's arterial and collector road centrelines from the City's GIS server
into raw/streets.json. Run from GitHub Actions (or any machine that can reach gis.toronto.ca).

The cot_geospatial MapServer holds one layer per road class (Provincial Expressway,
City Expressway, Major Arterial, ...). We list its layers, keep the arterial and
collector ones, and page through each one at a time (the server rejects bursts)."""
import json, os, re, time, urllib.parse, urllib.request

BASE = 'https://gis.toronto.ca/arcgis/rest/services/cot_geospatial/MapServer'
HERE = os.path.dirname(os.path.abspath(__file__))
WANT = re.compile(r'(major arterial|minor arterial|collector)', re.I)


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:
            print('  retry', i + 1, e)
            time.sleep(5 * (i + 1))
    raise SystemExit('failed: ' + url)


svc = get(BASE + '?f=json')
layers = svc.get('layers', [])
print('Layers in cot_geospatial:')
for l in layers:
    print(' ', l['id'], l['name'])

out = {}
for l in layers:
    if not WANT.search(l['name']):
        continue
    feats, off = [], 0
    while True:
        q = urllib.parse.urlencode({'where': '1=1', 'outFields': 'LINEAR_NAME_FULL', 'outSR': 4326, 'f': 'geojson',
                                    'geometryPrecision': 5, 'maxAllowableOffset': 0.00003,
                                    'resultOffset': off, 'resultRecordCount': 1000})
        page = get(f"{BASE}/{l['id']}/query?{q}")
        fs = page.get('features', [])
        feats += fs
        print(f"  {l['name']}: {len(feats)}")
        if len(fs) < 1000 and not page.get('exceededTransferLimit'):
            break
        off += len(fs)
        time.sleep(1)
    out[l['name']] = {'type': 'FeatureCollection', 'features': feats}
    time.sleep(2)

if not out:
    raise SystemExit('No arterial or collector layers found; see the layer list above.')
os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
with open(os.path.join(HERE, 'raw', 'streets.json'), 'w') as f:
    json.dump(out, f, separators=(',', ':'))
print('wrote raw/streets.json:', {k: len(v['features']) for k, v in out.items()})

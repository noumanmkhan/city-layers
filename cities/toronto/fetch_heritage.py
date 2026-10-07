"""Fetch Toronto's Heritage Conservation Districts into raw/heritage_districts.geojson.
Runs in GitHub Actions (.github/workflows/fetch-heritage.yml): the sandbox can't reach the City's servers.

Source: City of Toronto Open Data, "Heritage Conservation Districts" (a shapefile, refreshed quarterly).
The shapefile is converted to WGS84 GeoJSON with mapshaper. The log lists every field and, for
fields with few distinct values (such as a status), every value, so the build can pick the ones in force."""
import io, json, os, subprocess, sys, tempfile, time, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
CKAN = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=heritage-conservation-districts'
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, e)
            time.sleep(5 * (i + 1))
    raise SystemExit('failed: ' + url)


pkg = json.loads(get(CKAN))['result']
print('Package:', pkg['title'], '· refreshed', pkg.get('last_refreshed'))
print('Notes:', (pkg.get('notes') or '').strip()[:1500])
res = [r for r in pkg['resources'] if (r.get('format') or '').upper() in ('SHP', 'ZIP')]
for r in pkg['resources']:
    print('  resource:', r['name'], r.get('format'), r.get('url'))
if not res:
    raise SystemExit('No shapefile resource found')
blob = get(res[0]['url'])

with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(io.BytesIO(blob)).extractall(tmp)
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp) for f in fs]
    print('Zip contents:', [os.path.relpath(f, tmp) for f in files])
    for f in files:  # the readme describes the fields
        if f.lower().endswith(('.txt', '.md')) or 'readme' in f.lower():
            try: print('---', os.path.basename(f), '---\n' + open(f, errors='replace').read()[:4000])
            except Exception: pass
    shp = [f for f in files if f.lower().endswith('.shp')]
    if not shp:
        raise SystemExit('No .shp in the zip')
    os.makedirs(RAW, exist_ok=True)
    out = os.path.join(RAW, 'heritage_districts.geojson')
    subprocess.run(['npx', '--no-install', 'mapshaper', '-i', shp[0], 'encoding=utf8', '-proj', 'wgs84',
                    '-o', 'format=geojson', 'precision=0.000001', out], check=True)

fc = json.load(open(out))
props = [f['properties'] for f in fc['features']]
print(len(props), 'features')
for k in (props[0].keys() if props else []):
    vals = sorted({str(p.get(k)) for p in props})
    print(f'  {k}: ' + (repr(vals) if len(vals) <= 40 else f'{len(vals)} distinct, e.g. {vals[:5]}'))

"""Fetch Chicago's Landmark Districts into raw/heritage_districts.geojson, plus the City's list of
districts (names and designation dates) into raw/landmark_districts.json.
Runs in GitHub Actions (.github/workflows/fetch-heritage.yml): the sandbox can't reach the City's servers.

Sources: City of Chicago Data Portal, "Boundaries - Landmark Districts" (t8pq-wu86, a zipped shapefile,
boundaries as of 2012) and "Landmark Districts" (zidz-sdfj, the list). The shapefile is converted to
WGS84 GeoJSON with mapshaper. The log lists every field so the build can pick the name field."""
import io, json, os, subprocess, tempfile, time, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
SHAPES = ['https://data.cityofchicago.org/download/t8pq-wu86/application%2Fzip',
          'https://data.cityofchicago.org/api/views/t8pq-wu86/files/LandmarkDistricts_nov2012.zip']
LIST = 'https://data.cityofchicago.org/resource/zidz-sdfj.json?$limit=500'


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e)
            time.sleep(5 * (i + 1))
    return None


os.makedirs(RAW, exist_ok=True)
lst = get(LIST)
if lst:
    rows = json.loads(lst)
    json.dump(rows, open(os.path.join(RAW, 'landmark_districts.json'), 'w'), indent=1)
    print(len(rows), 'districts in the list; fields:', sorted({k for r in rows for k in r}))
    for r in rows: print('  ', {k: v for k, v in r.items() if not isinstance(v, (dict, list))})

blob = next((b for b in (get(u) for u in SHAPES) if b and b[:2] == b'PK'), None)
if not blob:
    raise SystemExit('Could not download the Landmark Districts shapefile')
with tempfile.TemporaryDirectory() as tmp:
    zipfile.ZipFile(io.BytesIO(blob)).extractall(tmp)
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp) for f in fs]
    print('Zip contents:', [os.path.relpath(f, tmp) for f in files])
    shp = [f for f in files if f.lower().endswith('.shp')]
    out = os.path.join(RAW, 'heritage_districts.geojson')
    subprocess.run(['npx', '--no-install', 'mapshaper', '-i', shp[0], '-proj', 'wgs84',
                    '-o', 'format=geojson', 'precision=0.000001', out], check=True)

fc = json.load(open(out))
props = [f['properties'] for f in fc['features']]
print(len(props), 'features')
for k in (props[0].keys() if props else []):
    vals = sorted({str(p.get(k)) for p in props})
    print(f'  {k}: ' + (repr(vals) if len(vals) <= 80 else f'{len(vals)} distinct, e.g. {vals[:5]}'))

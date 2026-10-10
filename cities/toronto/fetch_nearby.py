"""Fetch the City's parks and recreation facilities and Toronto Public Library branches for the card's
Nearby section, into raw/nearby/. Run from GitHub Actions (the *Fetch nearby places* workflow); the
sandbox can't download from Toronto Open Data.

  parks_rec.geojson   "Parks and Recreation Facilities" (Parks, Forestry & Recreation; refreshed monthly):
                      every City park and community recreation centre, with up to 20 listed amenities
                      (pools, rinks, tennis, playgrounds...) in one comma-separated AMENITIES field.
  tpl_branches.json   "Library Branch General Information" (Toronto Public Library): the 100-odd
                      branches with name, address, position and whether it's a physical branch."""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'nearby'); os.makedirs(OUT, exist_ok=True)
CKAN = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/'
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(10 * (i + 1))
    raise SystemExit('failed: ' + url)


def resource(package, want):
    pkg = json.loads(get(CKAN + 'package_show?id=' + package))['result']
    for r in pkg['resources']:
        if want(r): return r['url'], pkg.get('last_refreshed')
    raise SystemExit(f'{package}: no matching resource')


url, refreshed = resource('parks-and-recreation-facilities', lambda r: r['name'].endswith('4326.geojson'))
open(os.path.join(OUT, 'parks_rec.geojson'), 'wb').write(get(url))
fc = json.load(open(os.path.join(OUT, 'parks_rec.geojson')))
am = {}
for f in fc['features']:
    for a in (f['properties'].get('AMENITIES') or '').split(', '):
        am[a] = am.get(a, 0) + 1
print('parks and recreation:', len(fc['features']), 'locations, refreshed', refreshed)
print('  amenities:', sorted(am.items(), key=lambda kv: -kv[1]))
print('  types:', sorted({f['properties'].get('TYPE') for f in fc['features']}))

url, refreshed = resource('library-branch-general-information', lambda r: r.get('datastore_active'))
rows = json.loads(get(CKAN + 'datastore_search?resource_id=' + url.rstrip('/').split('/')[-1] + '&limit=1000'))['result']['records']
json.dump(rows, open(os.path.join(OUT, 'tpl_branches.json'), 'w'), ensure_ascii=False, indent=0)
print('library branches:', len(rows), 'refreshed', refreshed)

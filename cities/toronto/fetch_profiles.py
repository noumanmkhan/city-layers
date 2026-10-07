"""Fetch the City of Toronto's 2021 Neighbourhood Profiles (2021 Census, 158 neighbourhoods)
from the City's open data portal (CKAN) into raw/. Run from GitHub Actions (or any machine that
can reach the portal).

Writes:
  raw/neighbourhood_profiles_2021.xlsx  - the profile table as published
  raw/neighbourhood_profiles_resources.txt - every resource in the dataset, for the record
"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CKAN = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=neighbourhood-profiles'
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}


def get(url, binary=False, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except Exception as e:
            print('  retry', i + 1, e)
            time.sleep(5 * (i + 1))
    raise SystemExit('failed: ' + url)


pkg = get(CKAN)['result']
res = pkg['resources']
os.makedirs(os.path.join(HERE, 'raw'), exist_ok=True)
with open(os.path.join(HERE, 'raw', 'neighbourhood_profiles_resources.txt'), 'w') as f:
    for r in res:
        f.write(f"{r.get('name')} | {r.get('format')} | {r.get('last_modified') or r.get('created')} | {r.get('url')}\n")
for r in res:
    print(r.get('name'), r.get('format'), r.get('url'))

# The 2021 profile on the 158-neighbourhood model, as a spreadsheet.
def score(r):
    n = (r.get('name') or '').lower() + ' ' + (r.get('url') or '').lower()
    return ('2021' in n) * 4 + ('158' in n) * 4 + ((r.get('format') or '').lower() in ('xlsx', 'xls')) * 2 + ('full' in n)
best = max(res, key=score)
if score(best) < 8:
    raise SystemExit('No 2021 / 158-neighbourhood resource found; see raw/neighbourhood_profiles_resources.txt')
print('downloading', best.get('name'), best.get('url'))
data = get(best['url'], binary=True)
with open(os.path.join(HERE, 'raw', 'neighbourhood_profiles_2021.xlsx'), 'wb') as f:
    f.write(data)
print('wrote raw/neighbourhood_profiles_2021.xlsx', len(data), 'bytes')

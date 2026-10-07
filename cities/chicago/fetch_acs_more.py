"""More ACS 5-year tables for every Cook County tract, for the "What's here" card's housing rows.
Runs in GitHub Actions (.github/workflows/fetch-chicago.yml); the sandbox can't reach census.gov.

- B25036 Tenure by year structure built (occupied homes; Toronto's Census counts occupied dwellings too)
- B25032 Tenure by units in structure (occupied homes)
- C16001 Language spoken at home by ability to speak English (population 5 years and over). The detailed
  table (B16001, which separates Polish, Hindi, Urdu...) isn't published for tracts, only these 12 broad groups

Writes raw/acs_more.json: {year, source, labels: {var: label}, tracts: {GEOID: {var: count}}}. Labels come
from the Census API's variable list (no key needed for metadata); the build reads bracket and language
names from them rather than from hard-coded positions."""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
GROUPS = ['B25036', 'B25032', 'C16001']
SF = 'https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/'


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url[:140], e)
            time.sleep(10 * (i + 1))
    raise RuntimeError('failed: ' + url)


def labels_for(year, g):
    d = json.loads(get(f'https://api.census.gov/data/{year}/acs/acs5/groups/{g}.json'))['variables']
    # API names look like B16001_002E; the summary file's columns look like B16001_E002.
    return {k[:-1].replace('_', '_E', 1): v['label'] for k, v in d.items() if k.endswith('E') and k.startswith(g + '_')}


for year in (2024, 2023):
    root = SF.format(y=year)
    try:
        get(root + 'data/5YRData/', tries=1)
    except Exception as e:
        print('ACS', year, 'not available:', e); continue
    tracts, labels = {}, {}
    for g in GROUPS:
        try:
            labels.update(labels_for(year, g))
        except Exception as e:
            print('labels for', g, 'failed:', e)
        body = get(root + f'data/5YRData/acsdt5y{year}-{g.lower()}.dat').decode('utf8', 'replace').splitlines()
        head = body[0].split('|')
        for line in body[1:]:
            if not line.startswith('1400000US17031'): continue
            row = dict(zip(head, line.split('|')))
            t = tracts.setdefault(row['GEO_ID'][9:], {})
            for k, v in row.items():
                if k.startswith(g + '_E'):
                    try: t[k] = int(float(v)) if float(v) >= 0 else None
                    except ValueError: t[k] = None
        print(g, 'tracts so far', len(tracts), '· columns', sum(1 for k in head if k.startswith(g + '_E')))
        time.sleep(2)
    for k in sorted(labels): print(' ', k, labels[k])
    os.makedirs(RAW, exist_ok=True)
    json.dump({'year': year, 'source': root, 'labels': labels, 'tracts': tracts},
              open(os.path.join(RAW, 'acs_more.json'), 'w'), separators=(',', ':'))
    print('wrote acs_more.json')
    break
else:
    raise SystemExit('no ACS year available')

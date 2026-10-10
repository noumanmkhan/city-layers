"""Fetch Chicago Public Schools attendance boundaries and school profiles from the City's Data Portal.
Run from GitHub Actions (the *Fetch Chicago data* workflow runs it when this file changes on main);
the sandbox can't reach data.cityofchicago.org.

Looks up the newest school year in the portal's catalog, so a later year is picked up when it appears.
Falls back to the SY2025-26 ids found while scouting (October 2026).

  attendance/elementary.geojson   CPS Elementary School Attendance Boundaries (x72b-38qv for SY2526)
  attendance/middle.geojson       CPS Middle School Attendance Boundaries (fyff-53xy; few schools have one)
  attendance/high.geojson         CPS High School Attendance Boundaries (xg7c-d8rm)
  attendance/profiles.json        CPS School Profile Information, same year (full names, addresses, grades)
  attendance/sources.json         Which dataset id, name and update time each file came from
"""
import json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'attendance')
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}
PORTAL = 'https://data.cityofchicago.org'
CATALOG = 'https://api.us.socrata.com/api/catalog/v1'
FALLBACK = {'elementary': 'x72b-38qv', 'middle': 'fyff-53xy', 'high': 'xg7c-d8rm'}
LEVELS = {'elementary': 'Elementary School Attendance Boundaries',
          'middle': 'Middle School Attendance Boundaries',
          'high': 'High School Attendance Boundaries'}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(5 * (i + 1))
    raise SystemExit('could not download ' + url)


def year(name):
    m = re.search(r'SY ?(\d{2})(\d{2})\b', name)
    return int(m.group(1)) if m else -1


def catalog(q):
    url = CATALOG + '?' + urllib.parse.urlencode({'domains': 'data.cityofchicago.org', 'q': q, 'limit': 100})
    try:
        res = json.loads(get(url, tries=2))['results']
    except SystemExit:
        print('  catalog unavailable'); return []
    return [(r['resource']['id'], r['resource']['name'], r['resource'].get('data_updated_at')) for r in res]


os.makedirs(OUT, exist_ok=True)
sources = {}
for level, phrase in LEVELS.items():
    hits = [h for h in catalog('Chicago Public Schools ' + phrase) if phrase.lower() in h[1].lower() and year(h[1]) >= 0]
    hits.sort(key=lambda h: year(h[1]), reverse=True)
    for h in hits:
        print(level, h)
    ds = hits[0][0] if hits else FALLBACK[level]
    meta = json.loads(get(f'{PORTAL}/api/views/{ds}.json'))
    print(level, '->', ds, meta.get('name'), meta.get('rowsUpdatedAt'))
    body = get(f'{PORTAL}/resource/{ds}.geojson?$limit=5000')
    gj = json.loads(body)
    print('  features', len(gj['features']))
    if not gj['features']:
        raise SystemExit('no features in ' + ds)
    open(os.path.join(OUT, level + '.geojson'), 'wb').write(body)
    sources[level] = {'id': ds, 'name': meta.get('name'), 'updated': meta.get('rowsUpdatedAt')}
    time.sleep(2)

# School profiles for the same year as the elementary boundaries (names, address, grades, website).
want = year(sources['elementary']['name'] or '')
hits = [h for h in catalog('Chicago Public Schools School Profile Information')
        if 'school profile information' in h[1].lower()]
hits.sort(key=lambda h: (year(h[1]) == want, year(h[1])), reverse=True)
for h in hits:
    print('profile', h)
if hits:
    ds = hits[0][0]
    rows = json.loads(get(f'{PORTAL}/resource/{ds}.json?$limit=5000'))
    print('profiles ->', ds, hits[0][1], len(rows))
    json.dump(rows, open(os.path.join(OUT, 'profiles.json'), 'w'), indent=0)
    sources['profiles'] = {'id': ds, 'name': hits[0][1], 'updated': hits[0][2]}
else:
    print('no school profile dataset found')

json.dump(sources, open(os.path.join(OUT, 'sources.json'), 'w'), indent=1)
print(json.dumps(sources, indent=1))

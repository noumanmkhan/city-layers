"""One-off: list candidate sources for Chicago so the real fetcher can name exact IDs.
Writes cities/chicago/raw/discovery/. Run in GitHub Actions (the sandbox can't reach these hosts)."""
import json, os, urllib.request, urllib.parse
OUT = os.path.join(os.path.dirname(__file__), 'raw', 'discovery'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
def get(url, n=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            return r.status, r.read() if n is None else r.read(n)
    except Exception as e:
        return 'ERR ' + str(e)[:200], b''
log = {}
cat = {}
for q in ['community areas', 'neighborhoods boundaries', 'wards 2023', 'special service areas', 'city boundary',
          'CTA L rail lines', 'L stops', 'major streets', 'street center lines', 'ward offices', 'aldermen',
          'metra', 'park district parks', 'libraries locations', 'chicago landmarks', 'lakefront']:
    s, b = get('https://api.us.socrata.com/api/catalog/v1?domains=data.cityofchicago.org&limit=12&q=' + urllib.parse.quote(q))
    try:
        cat[q] = [[r['resource']['id'], r['resource']['name'], r['resource'].get('type'), r['resource'].get('data_updated_at')] for r in json.loads(b)['results']]
    except Exception as e:
        cat[q] = str(s)
json.dump(cat, open(f'{OUT}/socrata.json', 'w'), indent=1)
tw = {}
s, b = get('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb?f=json'); tw['services'] = json.loads(b or b'{}').get('services', s)
for svc in ['Legislative', 'Places_CouSub_ConCity_SubMCD', 'State_County', 'Tracts_Blocks']:
    s, b = get(f'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/{svc}/MapServer?f=json')
    try: tw[svc] = [[l['id'], l['name']] for l in json.loads(b)['layers']]
    except Exception: tw[svc] = str(s)
json.dump(tw, open(f'{OUT}/tigerweb.json', 'w'), indent=1)
cm = {}
for q in ['community data snapshots', 'community area']:
    s, b = get('https://datahub.cmap.illinois.gov/api/3/action/package_search?rows=8&q=' + urllib.parse.quote(q))
    try: cm[q] = [[p['name'], p['title'], [[r.get('name'), r.get('format'), r.get('url')] for r in p['resources']]] for p in json.loads(b)['result']['results']]
    except Exception: cm[q] = [str(s), b[:300].decode('utf8', 'replace')]
json.dump(cm, open(f'{OUT}/cmap.json', 'w'), indent=1)
probe = {}
for name, url in [('metra_gtfs', 'https://schedules.metrarail.com/gtfs/schedule.zip'),
                  ('cta_gtfs', 'https://www.transitchicago.com/downloads/sch_data/google_transit.zip'),
                  ('house_clerk', 'https://clerk.house.gov/xml/lists/MemberData.xml'),
                  ('ilga_house', 'https://www.ilga.gov/House/Members'),
                  ('ilga_senate', 'https://www.ilga.gov/Senate/Members'),
                  ('ilga_house_old', 'https://www.ilga.gov/house/default.asp'),
                  ('chicago_aldermen', 'https://www.chicago.gov/city/en/about/wards.html')]:
    s, b = get(url, 400000)
    probe[name] = [str(s), len(b)]
    if name.startswith(('ilga', 'chicago')) and b: open(f'{OUT}/{name}.html', 'wb').write(b)
json.dump(probe, open(f'{OUT}/probe.json', 'w'), indent=1)
print(json.dumps(probe))

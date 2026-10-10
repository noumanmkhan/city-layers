"""Fetch public community centres for the card's Nearby section, into raw/nearby/centres/.
Run from GitHub Actions (the *Fetch Chicago data* workflow runs it when this file changes on main).

Rule (agreed October 10, 2026): a "Community centre" on the card is publicly funded and open to
everyone, like Toronto's City-run centres. OpenStreetMap's community_centre tag mixes in churches,
clubs and advocacy groups, so it is no longer used. Sources:

  fieldhouses.json         Chicago Park District, Facilities: Fieldhouses (chicagoparkdistrict.com):
                           name, page and address from every list page, placed by the U.S. Census
                           Bureau's batch geocoder. The Park District is a public body; its fieldhouses
                           run programs open to all. Current list.
  cpd_facilities.json      City Data Portal, CPD_Facilities (eix4-gf83): Park District facilities with
                           positions, as of November 2016. A fallback for fieldhouses the geocoder misses.
  dfss_*.json              City Data Portal datasets from the Department of Family and Support Services
                           (community service centers, senior centers), found through the catalog.
  catalog.json             What the catalog searches returned, for checking.
"""
import csv, html, io, json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'nearby', 'centres'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}
PORTAL = 'https://data.cityofchicago.org'


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(5 * (i + 1))
    return None


# Park District fieldhouses: list pages ?page=0.. carry 8 cards each (name, link, address); walk them
# until a page has no new cards. (Every page also repeats a full A-Z link list without addresses.)
CARD = re.compile(r'<h3 class="facility--title">\s*<a href="([^"]+)"[^>]*><span[^>]*>([^<]+)</span>.*?href="https://google.com/maps\?q=([^"]+)"', re.S)
cards, page = {}, 0
while page < 60:
    body = get(f'https://www.chicagoparkdistrict.com/facilities/fieldhouses?page={page}')
    if not body: print('page', page, 'failed'); break
    got = CARD.findall(body.decode('utf-8', 'replace'))
    new = [c for c in got if c[0] not in cards]
    print('page', page, 'cards', len(got), 'new', len(new))
    if not new: break
    for link, name, addr in new: cards[link] = {'link': link, 'name': html.unescape(name).strip(), 'address': html.unescape(addr).strip()}
    page += 1; time.sleep(1)
print('fieldhouses', len(cards))

# Place them with the U.S. Census Bureau's batch geocoder (built for bulk lookups of U.S. addresses).
rows = []
for i, c in enumerate(cards.values()):
    street, city, zipc = (c['address'].split(',') + ['', '', ''])[:3]
    rows.append(f'{i},"{street.strip()}",Chicago,IL,{zipc.strip()}')
boundary = 'cityLayersBoundary'
parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="benchmark"\r\n\r\nPublic_AR_Current\r\n',
         f'--{boundary}\r\nContent-Disposition: form-data; name="addressFile"; filename="a.csv"\r\nContent-Type: text/csv\r\n\r\n' + '\n'.join(rows) + '\r\n',
         f'--{boundary}--\r\n']
req = urllib.request.Request('https://geocoding.geo.census.gov/geocoder/locations/addressbatch', data=''.join(parts).encode(),
                             headers=dict(UA, **{'Content-Type': f'multipart/form-data; boundary={boundary}'}))
try:
    with urllib.request.urlopen(req, timeout=600) as r: res = r.read().decode('utf-8', 'replace')
except Exception as e:
    res = ''; print('geocoder failed', e)
vals = list(cards.values())
for line in csv.reader(io.StringIO(res)):
    if len(line) >= 6 and line[2] == 'Match' and line[5]:
        lon, lat = line[5].split(',')
        vals[int(line[0])]['at'] = [round(float(lon), 5), round(float(lat), 5)]
        vals[int(line[0])]['matched'] = line[4]
print('geocoded', sum('at' in c for c in vals), 'of', len(vals))
json.dump(vals, open(os.path.join(OUT, 'fieldhouses.json'), 'w'), indent=1, ensure_ascii=False)

body = get(f'{PORTAL}/resource/eix4-gf83.json?$limit=10000')
if body:
    json.dump(json.loads(body), open(os.path.join(OUT, 'cpd_facilities.json'), 'w'), indent=0)
    print('cpd facilities', len(json.loads(body)))

found = {}
for q in ('community service centers', 'senior centers', 'DFSS', 'Family and Support Services'):
    url = 'https://api.us.socrata.com/api/catalog/v1?' + urllib.parse.urlencode({'domains': 'data.cityofchicago.org', 'q': q, 'limit': 40})
    b = get(url, tries=2)
    res = json.loads(b)['results'] if b else []
    found[q] = [(r['resource']['id'], r['resource']['name'], r['resource'].get('data_updated_at'), r['resource'].get('type')) for r in res]
    for h in found[q]: print(q, '|', h)
json.dump(found, open(os.path.join(OUT, 'catalog.json'), 'w'), indent=1)

for q, hits in found.items():
    for ds, name, upd, typ in hits:
        n = name.lower()
        if typ == 'dataset' and ('community service center' in n or 'senior center' in n):
            b = get(f'{PORTAL}/resource/{ds}.json?$limit=2000')
            if b:
                fn = 'dfss_' + re.sub(r'[^a-z0-9]+', '_', n).strip('_')[:60] + '.json'
                open(os.path.join(OUT, fn), 'wb').write(b); print('saved', fn, len(json.loads(b)))

"""Fetch public community centres for the card's Nearby section, into raw/nearby/centres/.
Run from GitHub Actions (the *Fetch Chicago data* workflow runs it when this file changes on main).

Rule (agreed October 10, 2026): a "Community centre" on the card is publicly funded and open to
everyone, like Toronto's City-run centres. OpenStreetMap's community_centre tag mixes in churches,
clubs and advocacy groups, so it is no longer used. Sources:

  fieldhouses_page_N.html  Chicago Park District, Facilities: Fieldhouses (chicagoparkdistrict.com),
                           every list page. The Park District is a public body; its fieldhouses run
                           programs open to all. Current list, with addresses.
  cpd_facilities.json      City Data Portal, CPD_Facilities (eix4-gf83): Park District facilities with
                           positions, as of November 2016. Used to place the fieldhouses.
  dfss_*.json              City Data Portal datasets from the Department of Family and Support Services
                           (community service centers, senior centers), found through the catalog.
  catalog.json             What the catalog searches returned, for checking.
"""
import json, os, re, time, urllib.parse, urllib.request

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


# Park District fieldhouses: walk ?page=0.. until a page has no new facility links.
seen, page = set(), 0
while page < 60:
    body = get(f'https://www.chicagoparkdistrict.com/facilities/fieldhouses?page={page}')
    if not body: print('page', page, 'failed'); break
    links = set(re.findall(rb'href="(/parks-facilities/[^"#?]+|/node/\d+)"', body))
    new = links - seen
    print('page', page, len(body), 'links', len(links), 'new', len(new))
    open(os.path.join(OUT, f'fieldhouses_page_{page}.html'), 'wb').write(body)
    if not new: break
    seen |= links; page += 1; time.sleep(2)

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

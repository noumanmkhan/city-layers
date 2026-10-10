"""Fetch Chicago Public Library branches and nearby amenities for the card's Nearby section, into
raw/nearby/. Run from GitHub Actions (the *Fetch Chicago data* workflow runs it when it changes).

  cpl_branches.json   City of Chicago Data Portal, "Libraries - Locations, Contact Information, and Usual
                      Hours of Operation" (x8fc-8rcq): every branch with its position.
  osm_amenities.json  OpenStreetMap (Overpass): public parks, playgrounds, swimming pools, ice rinks and
                      tennis courts in the city, plus community centres. The Park District's own facility
                      list on the City portal was retired in 2016, so OSM stands in; private pools and
                      courts (access=private, or inside a condo or club) are left out."""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'nearby'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}


def get(url, data=None, tries=6):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(15 * (i + 1))
    raise SystemExit('failed: ' + url)


rows = json.loads(get('https://data.cityofchicago.org/resource/x8fc-8rcq.json?$limit=500'))
json.dump(rows, open(os.path.join(OUT, 'cpl_branches.json'), 'w'), ensure_ascii=False, indent=0)
print('library branches:', len(rows))

BBOX = '41.64,-87.95,42.03,-87.52'
Q = f"""
[out:json][timeout:300];
(
  nwr["leisure"="park"]["name"]({BBOX});
  nwr["leisure"="playground"]({BBOX});
  nwr["leisure"="swimming_pool"]["access"!~"private|customers|members"]({BBOX});
  nwr["leisure"="sports_centre"]["sport"="swimming"]["access"!~"private|customers|members"]({BBOX});
  nwr["leisure"="ice_rink"]["access"!~"private|customers|members"]({BBOX});
  nwr["leisure"="pitch"]["sport"~"tennis"]["access"!~"private|customers|members"]({BBOX});
  nwr["amenity"="community_centre"]["name"]({BBOX});
);
out tags center;
"""
res = json.loads(get('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data': Q}).encode()))
els = []
for el in res.get('elements', []):
    t = el.get('tags', {}); c = el if el.get('type') == 'node' else el.get('center')
    if not c or 'lat' not in c: continue
    keep = {k: t[k] for k in ('name', 'leisure', 'amenity', 'sport', 'access', 'operator', 'indoor', 'location', 'covered') if k in t}
    els.append({'osm': el['type'][0] + str(el['id']), 'at': [round(c['lon'], 5), round(c['lat'], 5)], **keep})
json.dump(els, open(os.path.join(OUT, 'osm_amenities.json'), 'w'), ensure_ascii=False, indent=0)
kinds = {}
for e in els:
    k = e.get('leisure') or e.get('amenity'); kinds[k] = kinds.get(k, 0) + 1
print('OSM amenities:', len(els), kinds)

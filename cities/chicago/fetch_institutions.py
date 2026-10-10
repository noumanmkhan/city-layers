"""Fetch the data behind Chicago's universities, colleges and ERs toggles. Run from GitHub Actions
(the *Fetch institutions* workflow); the sandbox can't reach these hosts. Writes raw/institutions/:

  ipeds_hd.csv        IPEDS institutional characteristics (U.S. Department of Education, NCES), the
                      latest "HD" directory file: every college and university with its control (public /
                      private nonprofit / for-profit), level, degree-granting status, size category and
                      coordinates. Only the Illinois rows are kept.
  cms_hospitals.csv   CMS Hospital General Information (data.cms.gov provider data, xubh-q36u): every
                      Medicare-certified hospital with its type, ownership and whether it has emergency
                      services. Only the Chicago rows are kept.
  cms_geocoded.json   The Chicago hospitals' addresses placed by the U.S. Census Bureau geocoder.
  osm.json            OpenStreetMap's universities, colleges and hospitals in Chicago (Overpass), plus a
                      few campuses by name, to place campuses IPEDS lists only by their main address and
                      hospitals the geocoder missed.
"""
import csv, io, json, os, time, urllib.parse, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'institutions'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            print('  retry', i + 1, url, e); time.sleep(10 * (i + 1))
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(10 * (i + 1))
    return None


# IPEDS: newest directory file that exists.
for year in (2025, 2024, 2023):
    z = get(f'https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip')
    if z and z[:2] == b'PK': break
else:
    raise SystemExit('no IPEDS HD file found')
zf = zipfile.ZipFile(io.BytesIO(z))
name = [n for n in zf.namelist() if n.lower().endswith('.csv')][0]
rows = list(csv.DictReader(io.TextIOWrapper(zf.open(name), encoding='utf-8-sig', errors='replace')))
il = [r for r in rows if r.get('STABBR') == 'IL']
with open(os.path.join(OUT, 'ipeds_hd.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(il[0].keys())); w.writeheader(); w.writerows(il)
print(f'IPEDS HD{year}:', len(rows), 'institutions,', len(il), 'in Illinois')

# CMS Hospital General Information.
raw = get('https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv')
if not raw: raise SystemExit('CMS hospital file not found')
hosp = [r for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if (r.get('State') == 'IL') and (r.get('City/Town') or '').upper() == 'CHICAGO']
with open(os.path.join(OUT, 'cms_hospitals.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(hosp[0].keys())); w.writeheader(); w.writerows(hosp)
print('CMS hospitals in Chicago:', len(hosp))

# Census geocoder, one address at a time.
geo = {}
for r in hosp:
    addr = f"{r['Address']}, Chicago, IL {r['ZIP Code']}"
    q = urllib.parse.urlencode({'address': addr, 'benchmark': 'Public_AR_Current', 'format': 'json'})
    body = get('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + q)
    m = json.loads(body)['result']['addressMatches'] if body else []
    geo[r['Facility ID']] = {'address': addr, 'at': [round(m[0]['coordinates']['x'], 5), round(m[0]['coordinates']['y'], 5)] if m else None,
                             'matched': m[0]['matchedAddress'] if m else None}
    time.sleep(0.5)
json.dump(geo, open(os.path.join(OUT, 'cms_geocoded.json'), 'w'), indent=1)
print('geocoded', sum(1 for g in geo.values() if g['at']), 'of', len(geo))

# OpenStreetMap, for campus and hospital positions. (Overpass refuses browser-like user agents with a 406.)
BBOX = (41.64, -87.95, 42.03, -87.52)
QUERY = f"""
[out:json][timeout:240];
(
  nwr["amenity"~"^(university|college|hospital)$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  nwr["name"~"Northwestern|DePaul|Loyola|Rush University|Swedish",i]["building"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags center;
"""
data = urllib.parse.urlencode({'data': QUERY}).encode()
res = None
for attempt in range(6):
    url = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'][attempt % 2]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}), timeout=300) as r:
            res = json.load(r); break
    except Exception as e:
        print('  retry', attempt + 1, url, e); time.sleep(20 * (attempt + 1))
if res is None: raise SystemExit('Overpass request failed')
els = []
for el in res.get('elements', []):
    t = el.get('tags', {}); c = el if el.get('type') == 'node' else el.get('center')
    if not t.get('name') or not c or 'lat' not in c: continue
    els.append({'osm': el['type'][0] + str(el['id']), 'at': [round(c['lon'], 5), round(c['lat'], 5)], 'name': t['name'],
                'amenity': t.get('amenity') or 'other', 'operator': t.get('operator'), 'emergency': t.get('emergency')})
json.dump(sorted(els, key=lambda e: (e['amenity'], e['name'])), open(os.path.join(OUT, 'osm.json'), 'w'), ensure_ascii=False, indent=0)
print('OSM:', len(els), 'elements')

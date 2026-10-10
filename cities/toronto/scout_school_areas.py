"""Scouting (October 10, 2026): do the City of Toronto's GIS services hold school attendance areas?

The City's map server (gis.toronto.ca) has layers named "English Public School District" and
"English Separate School District" (cot_geospatial28, layers 19-22). They could be trustee wards or
attendance areas. This lists every layer of that service and any other service whose layers mention
schools, and for each school-looking layer saves its metadata, feature count and a few sample records
(attributes only), into raw/scouting/school_areas/. Nothing here feeds the map.
"""
import json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'scouting', 'school_areas'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}
ROOT = 'https://gis.toronto.ca/arcgis/rest/services'


def get(url, **q):
    q.setdefault('f', 'json')
    url = url + '?' + urllib.parse.urlencode(q)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return json.loads(r.read())
        except Exception as e:
            print('  retry', i + 1, url[:140], e); time.sleep(5 * (i + 1))
    return None


def save(name, obj):
    json.dump(obj, open(os.path.join(OUT, name), 'w'), indent=1)


SCHOOL = re.compile(r'school|trustee|catchment|attendance|tdsb|tcdsb|education', re.I)

# 1. Every service on the server (root and folders).
services = []
root = get(ROOT) or {}
for s in root.get('services', []): services.append(s)
for folder in root.get('folders', []):
    sub = get(f'{ROOT}/{folder}') or {}
    services += sub.get('services', [])
    time.sleep(1)
print('services:', len(services))
save('services.json', services)

# 2. Each MapServer/FeatureServer's layer list; keep school-looking layers.
hits = []
for s in services:
    if s.get('type') not in ('MapServer', 'FeatureServer'): continue
    url = f"{ROOT}/{s['name']}/{s['type']}"
    info = get(url)
    time.sleep(1)   # the server rejects bursts
    if not info: print('no info', url); continue
    layers = info.get('layers', []) + info.get('tables', [])
    if s['name'].endswith('cot_geospatial28'):
        save('cot_geospatial28_layers.json', layers)
    for l in layers:
        if SCHOOL.search(l.get('name', '')):
            hits.append((url, l['id'], l['name']))
            print('HIT', url, l['id'], l['name'])

# 3. Each hit: metadata, count, sample attributes.
summary = []
for url, lid, name in hits:
    meta = get(f'{url}/{lid}') or {}
    cnt = get(f'{url}/{lid}/query', where='1=1', returnCountOnly='true') or {}
    sample = get(f'{url}/{lid}/query', where='1=1', outFields='*', returnGeometry='false', resultRecordCount=8) or {}
    rec = {'url': f'{url}/{lid}', 'name': name, 'geometryType': meta.get('geometryType'),
           'description': meta.get('description'), 'copyright': meta.get('copyrightText'),
           'fields': [f.get('name') for f in meta.get('fields') or []], 'count': cnt.get('count'),
           'sample': [f.get('attributes') for f in sample.get('features', [])],
           'editInfo': meta.get('editingInfo')}
    summary.append(rec)
    print(json.dumps(rec, default=str)[:1500])
    time.sleep(1)
save('summary.json', summary)
print('done:', len(hits), 'school-looking layers')

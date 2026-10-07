"""Fetch Lake Michigan's outline near Chicago from Census TIGERweb's area hydrography, into
raw/lake_michigan.geojson. TIGER's water areas follow the surveyed shoreline (harbours, piers,
Northerly Island), unlike Natural Earth's coarse lake. Runs in GitHub Actions."""
import json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
SVC = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Hydro/MapServer'


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url[:140], e)
            time.sleep(10 * (i + 1))
    raise RuntimeError('failed: ' + url)


layers = json.loads(get(SVC + '?f=json'))['layers']
print('Hydro layers:', [(l['id'], l['name']) for l in layers])
area = next(l for l in layers if 'area' in l['name'].lower())
feats, off = [], 0
while True:
    q = {'where': "NAME LIKE 'Lake Michigan%'", 'outFields': 'NAME,MTFCC,OBJECTID', 'outSR': 4326, 'f': 'geojson', 'geometryPrecision': 5,
         'maxAllowableOffset': 0.00004, 'geometry': '-89.4,40.8,-86.3,42.9', 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326,
         'spatialRel': 'esriSpatialRelIntersects', 'resultOffset': off, 'resultRecordCount': 200}
    d = json.loads(get(f"{SVC}/{area['id']}/query?" + urllib.parse.urlencode(q)))
    feats += d.get('features', [])
    if len(d.get('features', [])) < 200: break
    off += 200
    time.sleep(2)
json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(RAW, 'lake_michigan.geojson'), 'w'), separators=(',', ':'))
print('wrote lake_michigan.geojson', len(feats), 'features from layer', area['name'])

"""Third Chicago fetch: the shoreline, and a position check for the hand-placed points.
Runs in GitHub Actions (.github/workflows/fetch-chicago.yml).

- raw/landmass.geojson: Census TIGERweb USLandmass around Chicagoland. The map's water is everything
  in the frame that isn't land, which follows the real shoreline (harbours, piers, Northerly Island).
- raw/point_check.json: OpenStreetMap Nominatim's position for each landmark and added known-as name,
  one request every 1.5 seconds (Nominatim's usage policy allows one per second).
"""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RAW = os.path.join(HERE, 'raw')
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
FAILED = []


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url[:140], e)
            time.sleep(10 * (i + 1))
    raise RuntimeError('failed: ' + url)


def landmass():
    q = {'where': '1=1', 'outFields': '*', 'outSR': 4326, 'f': 'geojson', 'geometryPrecision': 5, 'maxAllowableOffset': 0.00008,
         'geometry': '-89.4,40.8,-86.3,42.9', 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects'}
    svc = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/USLandmass/MapServer'
    layers = json.loads(get(svc + '?f=json'))['layers']
    print('USLandmass layers:', [(l['id'], l['name']) for l in layers])
    d = json.loads(get(f"{svc}/{layers[0]['id']}/query?" + urllib.parse.urlencode(q)))
    json.dump(d, open(os.path.join(RAW, 'landmass.geojson'), 'w'), separators=(',', ':'))
    print('wrote landmass.geojson', len(d.get('features', [])), 'features')


def points():
    from landmarks import LANDMARKS
    from names import KNOWN_AS_EXTRA
    out = {}
    for name, query in [(n, n) for n, *_ in LANDMARKS] + [(n, n + ', Chicago') for n, *_ in KNOWN_AS_EXTRA]:
        u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
            {'q': query, 'format': 'jsonv2', 'limit': 3, 'viewbox': '-87.95,42.03,-87.52,41.64', 'bounded': 1})
        try:
            out[name] = [{'name': r.get('display_name', '')[:90], 'type': r.get('type'), 'lat': float(r['lat']), 'lon': float(r['lon'])}
                         for r in json.loads(get(u, tries=2))]
        except Exception as e:
            out[name] = str(e)
        time.sleep(1.5)
    json.dump(out, open(os.path.join(RAW, 'point_check.json'), 'w'), indent=1)
    print('wrote point_check.json', len(out))


for label, fn in [('landmass', landmass), ('points', points)]:
    try:
        fn()
    except Exception as e:
        import traceback
        print('FAILED', label, repr(e)); traceback.print_exc(); FAILED.append(label)
print('failed:', FAILED or 'none')

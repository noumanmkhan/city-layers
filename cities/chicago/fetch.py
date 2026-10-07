"""Fetch Chicago's raw inputs into cities/chicago/raw/. Runs in GitHub Actions
(.github/workflows/fetch-chicago.yml); the sandbox can't reach these hosts.

- City of Chicago Data Portal (Socrata): boundaries, SSAs, the 'L', ward offices, ACS by community area
- Census TIGERweb: municipalities and counties around Chicago, state legislative and congressional districts
- OpenStreetMap via Overpass: expressways across the region, arterial streets inside the city
- Metra GTFS: line shapes, stations and which lines stop at each
Each source is fetched one request at a time, with a pause, to stay polite.
"""
import csv, io, json, os, time, urllib.parse, urllib.request, zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
os.makedirs(RAW, exist_ok=True)
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
REGION = (-88.75, 41.15, -86.85, 42.55)   # the six Illinois collar counties, Cook, and NW Indiana
CITY = (-87.95, 41.64, -87.52, 42.03)


def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url[:120], e)
            time.sleep(10 * (i + 1))
    raise RuntimeError('failed: ' + url)


FAILED = []


def step(label, fn):
    """Run one fetch; log a failure and carry on, so one bad source doesn't lose the rest."""
    try:
        fn()
    except Exception as e:
        import traceback
        print('FAILED', label, repr(e)); traceback.print_exc()
        FAILED.append(label)


def save(name, obj):
    with open(os.path.join(RAW, name), 'w') as f:
        json.dump(obj, f, separators=(',', ':'))
    print('wrote', name)


# ---------- City of Chicago Data Portal ----------
PORTAL = 'https://data.cityofchicago.org/resource/'
for name, ds in [('community_areas', 'igwz-8jzy'), ('neighborhoods', 'y6yq-dbs2'), ('wards', 'p293-wvbd'),
                 ('ssa', 'cmr6-dn8c'), ('city', 'qqq8-j68g'), ('cta_lines', 'xbyr-jnvx')]:
    step(name, lambda: save(name + '.geojson', json.loads(get(PORTAL + ds + '.geojson?$limit=50000'))))
    time.sleep(2)
for name, ds in [('cta_stops', '8pix-ypme'), ('ward_offices', 'htai-wnw4'), ('acs_community_areas', 't68z-cikk')]:
    step(name, lambda: save(name + '.json', json.loads(get(PORTAL + ds + '.json?$limit=50000'))))
    time.sleep(2)

# ---------- Census TIGERweb ----------
TW = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/'


def tiger(path, where, box, offset):
    feats, start = [], 0
    while True:
        q = {'where': where, 'outFields': '*', 'outSR': 4326, 'f': 'geojson', 'geometryPrecision': 5,
             'maxAllowableOffset': offset, 'geometry': ','.join(map(str, box)), 'geometryType': 'esriGeometryEnvelope',
             'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects', 'resultOffset': start, 'resultRecordCount': 500}
        d = json.loads(get(TW + path + '/query?' + urllib.parse.urlencode(q)))
        feats += d.get('features', [])
        if len(d.get('features', [])) < 500:
            return {'type': 'FeatureCollection', 'features': feats}
        start += 500
        time.sleep(2)


for name, path, where, box, off in [
        ('places', 'Places_CouSub_ConCity_SubMCD/MapServer/4', "STATE IN ('17','18')", REGION, 0.0002),
        ('counties', 'State_County/MapServer/1', "STATE IN ('17','18')", REGION, 0.0005),
        ('congress', 'Legislative/MapServer/0', "STATE='17'", CITY, 0.00005),
        ('il_senate', 'Legislative/MapServer/1', "STATE='17'", CITY, 0.00005),
        ('il_house', 'Legislative/MapServer/2', "STATE='17'", CITY, 0.00005)]:
    step(name, lambda: save(name + '.geojson', tiger(path, where, box, off)))
    time.sleep(3)

# ---------- OpenStreetMap (Overpass) ----------
OVERPASS = 'https://overpass-api.de/api/interpreter'


def overpass(query, name):
    d = json.loads(get(OVERPASS, data=urllib.parse.urlencode({'data': query}).encode()))
    save(name, d)
    time.sleep(10)


s, w, n, e = REGION[1], REGION[0], REGION[3], REGION[2]
q1 = f'[out:json][timeout:240];way["highway"~"^(motorway|trunk)$"]({s},{w},{n},{e});out tags geom;'
step('expressways', lambda: overpass(q1, 'osm_expressways.json'))
s, w, n, e = CITY[1], CITY[0], CITY[3], CITY[2]
q2 = f'[out:json][timeout:240];way["highway"~"^(primary|secondary|tertiary)$"]["name"]({s},{w},{n},{e});out tags geom;'
step('arterials', lambda: overpass(q2, 'osm_arterials.json'))

# ---------- Metra GTFS ----------
def metra():
    z = zipfile.ZipFile(io.BytesIO(get('https://schedules.metrarail.com/gtfs/schedule.zip')))
    rows = lambda f: list(csv.DictReader(io.TextIOWrapper(z.open(f), encoding='utf-8-sig')))
    routes = {r['route_id']: r for r in rows('routes.txt')}
    trips = rows('trips.txt')
    shape_count = defaultdict(Counter)
    trip_route = {}
    for t in trips:
        trip_route[t['trip_id']] = t['route_id']
        if t.get('shape_id'):
            shape_count[(t['route_id'], t.get('direction_id', ''))][t['shape_id']] += 1
    pts = defaultdict(list)
    for r in rows('shapes.txt'):
        pts[r['shape_id']].append((int(r['shape_pt_sequence']), round(float(r['shape_pt_lon']), 5), round(float(r['shape_pt_lat']), 5)))
    stop_routes = defaultdict(set)
    with z.open('stop_times.txt') as fh:
        for r in csv.DictReader(io.TextIOWrapper(fh, encoding='utf-8-sig')):
            rt = trip_route.get(r['trip_id'])
            if rt: stop_routes[r['stop_id']].add(rt)
    out = {'routes': {}, 'stops': []}
    for rid, r in routes.items():
        shapes = {}
        for (route, d), c in shape_count.items():
            if route != rid: continue
            for sid, _ in c.most_common(4):   # main patterns and branches
                shapes[sid] = [[x, y] for _, x, y in sorted(pts[sid])]
        out['routes'][rid] = {'short': r.get('route_short_name'), 'long': r.get('route_long_name'), 'color': r.get('route_color'), 'shapes': shapes}
    for s_ in rows('stops.txt'):
        if s_['stop_id'] in stop_routes:
            out['stops'].append({'id': s_['stop_id'], 'name': s_['stop_name'], 'lon': float(s_['stop_lon']), 'lat': float(s_['stop_lat']),
                                 'routes': sorted(stop_routes[s_['stop_id']])})
    save('metra.json', out)


step('metra', metra)
print('failed:', FAILED or 'none')

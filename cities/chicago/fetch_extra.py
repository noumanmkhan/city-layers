"""Second Chicago fetch: Metra's GTFS and the Census tract figures behind the neighbourhood lens.
Runs in GitHub Actions (.github/workflows/fetch-chicago.yml).

- raw/metra.json: line shapes (main patterns and branches), stations and the lines stopping at each
- raw/acs_tracts.json: ACS 5-year tables for every Cook County tract (tenure, commute mode, home value
  and gross rent brackets), plus the variable labels so the build can read the bracket edges
- raw/tracts.json: each Cook County tract's internal point (TIGERweb), used to place it in a community area
"""
import csv, io, json, os, time, urllib.parse, urllib.request, zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
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


def save(name, obj):
    json.dump(obj, open(os.path.join(RAW, name), 'w'), separators=(',', ':'))
    print('wrote', name)


def step(label, fn):
    try:
        fn()
    except Exception as e:
        import traceback
        print('FAILED', label, repr(e)); traceback.print_exc()
        FAILED.append(label)


def metra():
    z = zipfile.ZipFile(io.BytesIO(get('https://schedules.metrarail.com/gtfs/schedule.zip')))
    print('metra files:', z.namelist())

    def rows(f):
        # Metra's files pad the header and values with spaces: strip both.
        rd = csv.reader(io.TextIOWrapper(z.open(f), encoding='utf-8-sig'))
        head = [h.strip() for h in next(rd)]
        for r in rd:
            yield dict(zip(head, (v.strip() for v in r)))

    routes = {r['route_id']: r for r in rows('routes.txt')}
    trip_route, shape_count = {}, defaultdict(Counter)
    for t in rows('trips.txt'):
        trip_route[t['trip_id']] = t['route_id']
        if t.get('shape_id'):
            shape_count[t['route_id']][t['shape_id']] += 1
    pts = defaultdict(list)
    for r in rows('shapes.txt'):
        pts[r['shape_id']].append((int(r['shape_pt_sequence']), round(float(r['shape_pt_lon']), 5), round(float(r['shape_pt_lat']), 5)))
    stop_routes = defaultdict(set)
    for r in rows('stop_times.txt'):
        rt = trip_route.get(r['trip_id'])
        if rt: stop_routes[r['stop_id']].add(rt)
    out = {'routes': {}, 'stops': []}
    for rid, r in routes.items():
        shapes = {sid: [[x, y] for _, x, y in sorted(pts[sid])] for sid, _ in shape_count[rid].most_common(6)}
        out['routes'][rid] = {'short': r.get('route_short_name'), 'long': r.get('route_long_name'), 'color': r.get('route_color'),
                              'counts': dict(shape_count[rid].most_common(6)), 'shapes': shapes}
    for s in rows('stops.txt'):
        if s['stop_id'] in stop_routes:
            out['stops'].append({'id': s['stop_id'], 'name': s['stop_name'], 'lon': float(s['stop_lon']), 'lat': float(s['stop_lat']),
                                 'routes': sorted(stop_routes[s['stop_id']])})
    save('metra.json', out)


GROUPS = ['B25003', 'B08301', 'B25075', 'B25063']
SF = 'https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/'


def acs():
    """ACS 5-year table-based summary files (no API key needed): one pipe-delimited file per table
    covering every geography; keep Cook County tracts (GEO_ID 1400000US17031...)."""
    for year in (2024, 2023):
        root = SF.format(y=year)
        try:
            get(root + 'data/5YRData/', tries=1)
        except Exception as e:
            print('ACS', year, 'not available:', e); continue
        tracts, labels = {}, {}
        for g in GROUPS:
            body = get(root + f'data/5YRData/acsdt5y{year}-{g.lower()}.dat').decode('utf8', 'replace').splitlines()
            head = body[0].split('|')
            for line in body[1:]:
                if not line.startswith('1400000US17031'): continue
                row = dict(zip(head, line.split('|')))
                t = tracts.setdefault(row['GEO_ID'][9:], {})
                for k, v in row.items():
                    if k.endswith(tuple(f'_E{n:03d}' for n in range(1, 60))):
                        try: t[k] = int(float(v)) if float(v) >= 0 else None
                        except ValueError: t[k] = None
            print(g, 'tracts so far', len(tracts))
            time.sleep(2)
        try:
            shells = get(root + f'documentation/ACS{year}5YR_Table_Shells.txt' if False else root + 'documentation/', tries=1)
            open(os.path.join(RAW, 'acs_documentation_listing.html'), 'wb').write(shells)
        except Exception as e:
            print('no documentation listing', e)
        save('acs_tracts.json', {'year': year, 'source': root, 'tracts': tracts})
        return
    raise RuntimeError('no ACS year available')


def tracts():
    q = {'where': "STATE='17' AND COUNTY='031'", 'outFields': 'GEOID,INTPTLAT,INTPTLON', 'returnGeometry': 'false', 'f': 'json',
         'resultRecordCount': 2000}
    feats, off = [], 0
    while True:
        q['resultOffset'] = off
        d = json.loads(get('https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0/query?' + urllib.parse.urlencode(q)))
        feats += d['features']
        if not d.get('exceededTransferLimit') and len(d['features']) < 2000: break
        off += len(d['features'])
    save('tracts.json', {f['attributes']['GEOID']: [float(f['attributes']['INTPTLON']), float(f['attributes']['INTPTLAT'])] for f in feats})


step('acs', acs)
print('failed:', FAILED or 'none')

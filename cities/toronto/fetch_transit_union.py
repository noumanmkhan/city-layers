"""Travel time by transit from every Toronto neighbourhood to Union Station, on a weekday morning.
Run from GitHub Actions (needs Java 21, r5py and internet access); writes raw/transit_union.json.

How it works:
  1. Download the schedules (GTFS) for the TTC (City of Toronto open data), GO Transit and
     UP Express (Metrolinx open data), and an OpenStreetMap extract for walking.
  2. Scatter origin points about 400 m apart inside each of the 158 neighbourhoods
     (raw/nbhd158.geojson), so a big neighbourhood isn't judged by one spot.
  3. Route every point to Union with r5py (Conveyal R5): walk + any transit, leaving between
     8:00 and 9:00 on a regular weekday, taking the median trip over that hour.
  4. A neighbourhood's figure is the median over its points.

Driving is deliberately not computed: free routing tools assume empty roads, which badly
understates a Toronto rush hour."""
import datetime as dt, io, json, os, statistics, subprocess, sys, time, urllib.request, zipfile

sys.argv += ['--max-memory', '12G']   # r5py reads its JVM settings from the command line
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, 'tmp', 'transit'); os.makedirs(WORK, exist_ok=True)
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}
UNION = (-79.3806, 43.6453)
TTC_CKAN = 'https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=ttc-routes-and-schedules'
GO = ['https://assets.metrolinx.com/raw/upload/Documents/Metrolinx/Open%20Data/GO-GTFS.zip']
UP = ['https://assets.metrolinx.com/raw/upload/Documents/Metrolinx/Open%20Data/UP-GTFS.zip']
OSM = 'https://download.bbbike.org/osm/bbbike/Toronto/Toronto.osm.pbf'
ONTARIO = 'https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf'
BBOX = '-79.70,43.55,-79.05,43.90'    # west,south,east,north: the city plus a margin


def download(url, path, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r, open(path, 'wb') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            print('  got', url, os.path.getsize(path), 'bytes'); return path
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(10 * (i + 1))
    return None


def gtfs_ok(path):
    try:
        with zipfile.ZipFile(path) as z:
            return 'stop_times.txt' in z.namelist()
    except Exception:
        return False


feeds, log = [], []
# TTC: find the GTFS zip in the City's open data package.
pkg = json.load(urllib.request.urlopen(urllib.request.Request(TTC_CKAN, headers=UA), timeout=120))['result']
for r in pkg['resources']:
    print('  ttc resource:', r.get('name'), r.get('format'), r.get('url'))
zips = [r for r in pkg['resources'] if (r.get('format') or '').lower() == 'zip' or (r.get('url') or '').lower().endswith('.zip')]
for r in zips:
    p = download(r['url'], os.path.join(WORK, 'ttc.zip'))
    if p and gtfs_ok(p):
        feeds.append(p); log.append('TTC: ' + r['url']); break
else:
    raise SystemExit('No TTC GTFS found')
for name, urls in (('go', GO), ('up', UP)):
    for u in urls:
        p = download(u, os.path.join(WORK, name + '.zip'))
        if p and gtfs_ok(p):
            feeds.append(p); log.append(name.upper() + ': ' + u); break
    else:
        print('WARNING: no', name, 'feed')

# Walking network.
pbf = os.path.join(WORK, 'toronto.osm.pbf')
if not download(OSM, pbf):
    big = download(ONTARIO, os.path.join(WORK, 'ontario.osm.pbf'))
    subprocess.run(['osmium', 'extract', '-b', BBOX, big, '-o', pbf, '--overwrite'], check=True)
    log.append('OSM: Geofabrik Ontario, cut to ' + BBOX)
else:
    log.append('OSM: ' + OSM)


# A regular weekday that every feed covers: the second Tuesday from today, checked against calendars.
def service_range(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist(); lo, hi = [], []
        for fn in ('calendar.txt', 'calendar_dates.txt'):
            if fn not in names: continue
            rows = io.TextIOWrapper(z.open(fn), encoding='utf-8-sig').read().splitlines()
            head = [h.strip() for h in rows[0].split(',')]
            for line in rows[1:]:
                v = dict(zip(head, [c.strip() for c in line.split(',')]))
                for k in ('start_date', 'date'):
                    if v.get(k): lo.append(v[k])
                for k in ('end_date', 'date'):
                    if v.get(k): hi.append(v[k])
        return min(lo), max(hi)


ranges = [service_range(f) for f in feeds]
print('feed ranges', ranges)
start = max(dt.datetime.strptime(a, '%Y%m%d').date() for a, b in ranges)
end = min(dt.datetime.strptime(b, '%Y%m%d').date() for a, b in ranges)
day = max(start, dt.date.today()) + dt.timedelta(days=7)
while day.weekday() != 1: day += dt.timedelta(days=1)          # Tuesday
if day > end:
    day = start
    while day.weekday() != 1: day += dt.timedelta(days=1)
depart = dt.datetime.combine(day, dt.time(8, 0))
print('departure', depart)

# Origin points.
import geopandas as gpd
from shapely.geometry import Point, shape
pts = []
for f in json.load(open(os.path.join(HERE, 'raw', 'nbhd158.geojson')))['features']:
    code = int(f['properties']['AREA_SHORT_CODE']); g = shape(f['geometry']).buffer(0)
    x0, y0, x1, y1 = g.bounds; dx, dy = 400 / 80500, 400 / 111000
    mine = []
    y = y0 + dy / 2
    while y < y1:
        x = x0 + dx / 2
        while x < x1:
            if g.contains(Point(x, y)): mine.append((x, y))
            x += dx
        y += dy
    if len(mine) < 3:
        rp = g.representative_point(); mine.append((rp.x, rp.y))
    for i, (x, y) in enumerate(mine):
        pts.append({'id': code * 1000 + i, 'code': code, 'geometry': Point(x, y)})
origins = gpd.GeoDataFrame(pts, crs='EPSG:4326')
dest = gpd.GeoDataFrame([{'id': 0, 'geometry': Point(*UNION)}], crs='EPSG:4326')
print(len(origins), 'origin points')

import r5py
from r5py import TransportNetwork, TransportMode
net = TransportNetwork(pbf, feeds)
kw = dict(origins=origins[['id', 'geometry']], destinations=dest, departure=depart,
          departure_time_window=dt.timedelta(hours=1), transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
          max_time=dt.timedelta(minutes=180))
try:
    tt = r5py.TravelTimeMatrix(net, **kw)
except (AttributeError, TypeError):
    tt = r5py.TravelTimeMatrixComputer(net, **kw).compute_travel_times()
col = 'travel_time' if 'travel_time' in tt.columns else [c for c in tt.columns if c.startswith('travel_time')][0]
times = dict(zip(tt['from_id'], tt[col]))

out, points = {}, []
for code, grp in origins.groupby('code'):
    vals = [times.get(i) for i in grp['id']]
    vals = [float(v) for v in vals if v is not None and v == v]
    for (_, r) in grp.iterrows():
        v = times.get(r['id'])
        points.append([round(r.geometry.x, 4), round(r.geometry.y, 4), None if v is None or v != v else int(v)])
    out[str(code)] = {'minutes': round(statistics.median(vals)) if vals else None,
                      'best': round(min(vals)) if vals else None, 'points': len(grp), 'reached': len(vals)}
json.dump({'to': 'Union Station', 'departure': depart.isoformat(), 'window_minutes': 60,
           'modes': 'walk + transit (TTC, GO, UP Express)', 'sources': log,
           'neighbourhoods': out, 'points': points},
          open(os.path.join(HERE, 'raw', 'transit_union.json'), 'w'), separators=(',', ':'))
mins = sorted(v['minutes'] for v in out.values() if v['minutes'] is not None)
print('wrote raw/transit_union.json:', len(out), 'neighbourhoods; minutes min/median/max',
      mins[0], mins[len(mins) // 2], mins[-1])

"""Fetch a city's streetcar and bus routes, stops and schedule counts from its transit agency's
GTFS into cities/<city>/raw/surface/ (routes.json, stops.json). Run from GitHub Actions (the
*Fetch streetcar and bus routes* workflow); the sandbox can't reach the agencies' servers.

Where the GTFS comes from is in cities/<city>/surface.json ("gtfs": a CKAN package or a zip URL).
Nothing is decided here about what the map shows: the build (engine/surface.py) picks families
(frequent, express, overnight) from the counts written here.

What it keeps, per route (streetcar or bus; route numbers in "skip" are left out):
  - the shapes that carry at least 10% of a direction's trips over the coming week, simplified ~5 m;
  - trips per hour of first departure, per direction, on one weekday, one Saturday and one Sunday
    (hours 0-29: GTFS writes after-midnight trips of a service day as 24:xx, 25:xx...).
Per stop: id, name, position and the route numbers that serve it during that week.

When the downloaded feed is the one already fetched (same checksum), nothing is written.

Usage: python3 engine/fetch_surface.py <city>
"""
import collections, csv, datetime as dt, hashlib, io, json, os, sys, time, urllib.request, zipfile
from shapely.geometry import LineString

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
city = sys.argv[1]
CFG = json.load(open(os.path.join(ROOT, 'cities', city, 'surface.json')))
OUT = os.path.join(ROOT, 'cities', city, 'raw', 'surface')
WORK = os.path.join(ROOT, 'cities', city, 'tmp', 'surface')
os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
UA = {'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'}
SKIP = set(CFG.get('skip', []))


def download(url, path, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r, open(path, 'wb') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            print('  got', url, os.path.getsize(path), 'bytes'); return True
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(10 * (i + 1))
    return False


def ok(path):
    try:
        with zipfile.ZipFile(path) as z: return 'stop_times.txt' in z.namelist()
    except Exception: return False


ZIP = os.path.join(WORK, 'gtfs.zip')
src = CFG['gtfs']
if 'ckan' in src:
    pkg = json.load(urllib.request.urlopen(urllib.request.Request(src['ckan'], headers=UA), timeout=120))['result']
    urls = [r['url'] for r in pkg['resources'] if (r.get('format') or '').lower() == 'zip' or (r.get('url') or '').lower().endswith('.zip')]
else:
    urls = [src['url']]
feed_url = next((u for u in urls if download(u, ZIP) and ok(ZIP)), None)
if not feed_url: raise SystemExit('No GTFS found')

# The job runs weekly; agencies publish a new feed every few weeks. Same feed as last time: nothing to do,
# so the repo only changes when the schedule does.
SHA = hashlib.sha256(open(ZIP, 'rb').read()).hexdigest()[:16]
try:
    if json.load(open(os.path.join(OUT, 'routes.json'))).get('sha') == SHA:
        print('feed unchanged (sha', SHA + '); keeping the files from last time'); sys.exit(0)
except (OSError, ValueError):
    pass

z = zipfile.ZipFile(ZIP)


def rows(name):
    if name not in z.namelist(): return
    with z.open(name) as f:
        r = csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig'))
        head = [h.strip() for h in next(r)]   # some agencies pad headers and fields with spaces
        for row in r:
            yield {h: (row[i].strip() if i < len(row) else '') for i, h in enumerate(head)}


def mode(t):
    t = int(t or -1)
    if t == 0 or 900 <= t <= 906: return 'tram'
    if t == 3 or 700 <= t <= 716: return 'bus'
    return None


routes = {}
for r in rows('routes.txt'):
    m = mode(r.get('route_type'))
    short = r.get('route_short_name') or r['route_id']
    if not m or short in SKIP: continue
    routes[r['route_id']] = {'id': r['route_id'], 'short': short, 'long': r.get('route_long_name', ''), 'mode': m,
                             'color': r.get('route_color', ''), 'text': r.get('route_text_color', '')}
print('routes kept:', len(routes))

# Service calendar.
D = lambda s: dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))
cal, extra = {}, collections.defaultdict(dict)
for r in rows('calendar.txt'):
    cal[r['service_id']] = (D(r['start_date']), D(r['end_date']), [r[d] == '1' for d in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')])
for r in rows('calendar_dates.txt'):
    extra[r['service_id']][D(r['date'])] = r['exception_type'] == '1'
def active(sid, day):
    if day in extra.get(sid, {}): return extra[sid][day]
    c = cal.get(sid)
    return bool(c and c[0] <= day <= c[1] and c[2][day.weekday()])
starts = [c[0] for c in cal.values()] + [d for e in extra.values() for d in e]
ends = [c[1] for c in cal.values()] + [d for e in extra.values() for d in e]
first, last = min(starts), max(ends)
services = set(cal) | set(extra)
def busy(day): return sum(active(s, day) for s in services)

# A typical week: start on a Monday at or after tomorrow (or the feed's first day), skipping weeks
# whose Wednesday runs noticeably fewer services than usual (a holiday).
day = max(dt.date.today() + dt.timedelta(days=1), first)
day += dt.timedelta(days=(7 - day.weekday()) % 7)
for _ in range(6):
    if day + dt.timedelta(days=6) > last: break
    wed = day + dt.timedelta(days=2)
    if busy(wed) >= max(busy(wed + dt.timedelta(days=7)), 1) * 0.9: break
    day += dt.timedelta(days=7)
WEEK = [day + dt.timedelta(days=i) for i in range(7)]
PICK = {'wk': WEEK[2], 'sat': WEEK[5], 'sun': WEEK[6]}
print('feed', first, '-', last, '· week from', day, '· days', {k: str(v) for k, v in PICK.items()})

trips = {}
for r in rows('trips.txt'):
    if r['route_id'] not in routes: continue
    days = [active(r['service_id'], d) for d in WEEK]
    if not any(days): continue
    trips[r['trip_id']] = (r['route_id'], r.get('direction_id') or '0', r.get('shape_id', ''), days)
print('trips in the week:', len(trips))

first_dep = {}                     # trip -> (stop_sequence, hour)
stop_routes = collections.defaultdict(set)
for r in rows('stop_times.txt'):
    t = trips.get(r['trip_id'])
    if not t: continue
    stop_routes[r['stop_id']].add(t[0])
    seq = int(r['stop_sequence']); tm = r.get('departure_time') or r.get('arrival_time')
    if tm and (r['trip_id'] not in first_dep or seq < first_dep[r['trip_id']][0]):
        first_dep[r['trip_id']] = (seq, int(tm.split(':')[0]))

# Counts per hour and shape use.
idx = {d: i for i, d in enumerate(WEEK)}
counts = {rid: {k: collections.defaultdict(lambda: [0] * 30) for k in PICK} for rid in routes}
shape_use = collections.defaultdict(collections.Counter)   # (route, dir) -> shape -> trips in the week
for tid, (rid, d, sh, days) in trips.items():
    shape_use[(rid, d)][sh] += sum(days)
    h = first_dep.get(tid, (0, None))[1]
    if h is None: continue
    for k, day_ in PICK.items():
        if days[idx[day_]]: counts[rid][k][d][min(h, 29)] += 1

need = {sh for c in shape_use.values() for sh, n in c.items() if sh and n >= 0.1 * sum(c.values())}
pts = collections.defaultdict(list)
for r in rows('shapes.txt'):
    if r['shape_id'] in need:
        pts[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
def line(sh):
    p = [(x, y) for _, x, y in sorted(pts.get(sh, []))]
    if len(p) < 2: return None
    s = LineString(p).simplify(0.00005)
    return [[round(x, 5), round(y, 5)] for x, y in s.coords]

out_routes = []
for rid, rt in routes.items():
    shapes = []
    for d in ('0', '1'):
        c = shape_use.get((rid, d))
        if not c: continue
        tot = sum(c.values())
        for sh, n in c.most_common():
            if sh in need:
                g = line(sh)
                if g: shapes.append({'dir': d, 'share': round(n / tot, 2), 'trips': n, 'coords': g})
    if not shapes: continue
    out_routes.append(dict(rt, shapes=shapes, **{k: dict(v) for k, v in counts[rid].items()}))
out_routes.sort(key=lambda r: (len(r['short']), r['short']))

names = {}
for r in rows('stops.txt'):
    if r['stop_id'] in stop_routes and r.get('stop_lat'):
        names[r['stop_id']] = [r['stop_id'], r.get('stop_name', ''), round(float(r['stop_lon']), 5), round(float(r['stop_lat']), 5),
                               sorted({routes[x]['short'] for x in stop_routes[r['stop_id']]}, key=lambda s: (len(s), s))]

meta = {'source': feed_url, 'sha': SHA, 'fetched': dt.date.today().isoformat(), 'feed': [str(first), str(last)], 'week': str(day),
        'days': {k: str(v) for k, v in PICK.items()}}
json.dump(dict(meta, routes=out_routes), open(os.path.join(OUT, 'routes.json'), 'w'), separators=(',', ':'))
json.dump(dict(meta, stops=list(names.values())), open(os.path.join(OUT, 'stops.json'), 'w'), separators=(',', ':'))
print('routes written:', len(out_routes), '· trams', sum(r['mode'] == 'tram' for r in out_routes), '· stops', len(names))
for r in out_routes:
    wk = r['wk']; mid = max(sum(v[10:15]) for v in wk.values()) if wk else 0
    night = sum(sum(v[1:5]) + sum(v[25:29]) for v in wk.values())
    print(f"  {r['mode']:4} {r['short']:>5} {r['long'][:34]:34} shapes {len(r['shapes'])}  midday/5h {mid:3}  1-5am {night}")

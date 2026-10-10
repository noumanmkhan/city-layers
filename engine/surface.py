"""Build a city's streetcar and bus layers from cities/<city>/raw/surface/ (engine/fetch_surface.py).

Writes into docs/<city>/data/:
  - streetcars.geojson: streetcar routes with daytime service, one feature per route (if the city has any);
  - transit_routes.geojson: every streetcar and bus route, one feature per route, for the bus families and
    for a route someone picks (loaded on demand);
  - transit.json: the route list (number, name, mode, families, midday frequency, bounds) and every stop
    (position, name, routes), for the card's Nearby rows, stops on the map and search.

Families, all described from the schedule, never ranked (thresholds in cities/<city>/surface.json):
  - freq: a weekday trip every 10 minutes or better from 7 am to 7 pm, in each direction;
  - exp: routes the agency names as express;
  - night: at least one trip each way in every hour from 2 to 4 am on a weekday night;
  - reg: every other route with daytime service (neither frequent nor express), e.g. community and branch routes.

Usage: python3 engine/surface.py <city>
"""
import json, os, re, sys
from shapely.geometry import LineString, MultiLineString, mapping
from shapely.ops import linemerge, unary_union

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
city = sys.argv[1]
CFG = json.load(open(os.path.join(ROOT, 'cities', city, 'surface.json')))
RAW = os.path.join(ROOT, 'cities', city, 'raw', 'surface')
OUT = os.path.join(ROOT, 'docs', city, 'data')
R = json.load(open(os.path.join(RAW, 'routes.json')))
S = json.load(open(os.path.join(RAW, 'stops.json')))
FREQ = CFG.get('frequent', {'perHour': 6, 'from': 7, 'to': 19})
NIGHT = CFG.get('overnight', {'from': 2, 'to': 4})
EXPRESS = re.compile(CFG.get('express', r'\bExpress\b'), re.I)


def dirs(counts):
    """The directions with trips: one for a loop route, usually two."""
    return [v for v in counts.values() if sum(v)] or [[0] * 30]


def per_hour(v, h):
    # GTFS writes a service day's after-midnight trips as 24:xx, 25:xx...; agencies differ on which they use.
    return v[h] + (v[h + 24] if h + 24 < len(v) else 0)


def frequent(r):
    ds = dirs(r.get('wk', {}))
    lo, hi, need = FREQ['from'], FREQ['to'], FREQ['perHour']
    # Every 3-hour block of the span averages the target in each direction (single hours are jittery:
    # a 10-minute service starts 5 trips in some hours and 7 in others).
    blocks = [(a, min(a + 3, hi)) for a in range(lo, hi, 3)]
    return all(sum(v[a:b]) / (b - a) >= need - 0.25 for v in ds for a, b in blocks)


def overnight(r):
    ds = dirs(r.get('wk', {}))
    return all(per_hour(v, h) >= 1 for v in ds for h in range(NIGHT['from'], NIGHT['to']))


def daytime(r):
    # Weekdays or Saturday, 9 am to 9 pm (Sundays aside: some night routes run on into Sunday morning).
    return any(sum(v[9:21]) for k in ('wk', 'sat') for v in r.get(k, {}).values())


def midday(r):
    """Typical wait on a weekday between 10 am and 3 pm, in minutes (busier direction), or None."""
    ds = [v for v in r.get('wk', {}).values() if sum(v[10:15])]
    if not ds: return None
    n = max(sum(v[10:15]) for v in ds)
    return round(300 / n) if n >= 5 else None   # under one an hour: too sparse to call a frequency


def geometry(r):
    """One line set per route: its busiest pattern whole, then, from the other patterns and the other
    direction (busiest first), only the stretches more than ~35 m from what's already drawn and longer than
    ~100 m (branches, one-way pairs, loops). Overlapping patterns are never unioned: their tiny offsets
    would split the line at every crossing into dozens of pieces. Simplified to about 8 m."""
    shapes = sorted(r['shapes'], key=lambda s: (s['dir'] != '0', -s['trips']))
    lines = [LineString(shapes[0]['coords'])]
    for s in shapes[1:]:
        near = unary_union(lines).buffer(0.0004)
        d = LineString(s['coords']).difference(near)
        lines += [p for p in getattr(d, 'geoms', [d]) if p.geom_type == 'LineString' and p.length > 0.0012]
    g = linemerge(lines) if len(lines) > 1 else lines[0]
    g = g.simplify(0.00008, preserve_topology=False)
    parts = [l for l in getattr(g, 'geoms', [g]) if l.length > 0]
    return MultiLineString([[(round(x, 5), round(y, 5)) for x, y in l.coords] for l in parts])


routes, feats, cars = [], [], []
for r in R['routes']:
    fam = [k for k, ok in (('freq', frequent(r)), ('exp', bool(EXPRESS.search(r['long']))), ('night', overnight(r))) if ok]
    day = daytime(r)
    if day and 'freq' not in fam and 'exp' not in fam: fam.append('reg')
    g = geometry(r)
    minx, miny, maxx, maxy = g.bounds
    entry = {'r': r['short'], 'n': r['long'], 'm': r['mode'], 'f': fam, 'day': day, 'h': midday(r),
             'b': [round(minx, 4), round(miny, 4), round(maxx, 4), round(maxy, 4)]}
    routes.append(entry)
    props = {k: entry[k] for k in ('r', 'n', 'm', 'f', 'day', 'h')}
    feat = {'type': 'Feature', 'properties': props, 'geometry': mapping(g)}
    feats.append(feat)
    if r['mode'] == 'tram' and day: cars.append(feat)

idx = {e['r']: i for i, e in enumerate(routes)}
stops = [[s[2], s[3], s[1], [idx[x] for x in s[4] if x in idx]] for s in S['stops']]
stops = [s for s in stops if s[3]]


def dump(name, fc):
    path = os.path.join(OUT, name)
    open(path, 'w').write(json.dumps(fc, separators=(',', ':')))
    print(f'  {name}: {len(fc.get("features", fc.get("routes", [])))} · {os.path.getsize(path) // 1024} KB')


meta = {'asof': R['fetched'], 'week': R['week']}
dump('transit_routes.geojson', dict(meta, type='FeatureCollection', features=feats))
if cars: dump('streetcars.geojson', dict(meta, type='FeatureCollection', features=cars))
dump('transit.json', dict(meta, routes=routes, stops=stops))
fams = {k: sum(k in e['f'] for e in routes) for k in ('freq', 'exp', 'reg', 'night')}
print(f'{city}: {len(routes)} routes ({len(cars)} streetcar routes in daytime) · {len(stops)} stops · families {fams}')
for k in fams:
    print(f'  {k}:', ' '.join(e['r'] for e in routes if k in e['f']))

"""Suburban lens: typical free-flow drive time from the suburbs to a city's downtown hub.
Shared by every city; the hub comes from the "drive" entry in cities/<city>/city.json.

  python3 engine/drive.py points <city>
      Lays a grid of points about 1.5 km apart over the municipalities around the city (the
      "neighbour" shapes in docs/<city>/data/base.geojson) -> cities/<city>/raw/drive_points.json.
      engine/fetch_drive_times.py then times each point to the hub in GitHub Actions.

  python3 engine/drive.py build <city>
      Reads cities/<city>/raw/drive_times.json and
      - gives each municipality in base.geojson "drive": the median minutes of its grid points
        (left out for "rest" shapes, such as unincorporated county land, which stay grey on the map)
      - writes docs/<city>/data/drive_grid.json, the minutes at every point, so the What's here card
        can give the time from the spot that was tapped.
Times are free-flow (posted speeds, empty roads): good for comparing places, not for planning a trip.
"""
import json, math, os, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
cmd, city = (sys.argv[1:3] + [None, None])[:2]
if cmd not in ('points', 'build') or not city:
    sys.exit('usage: drive.py points|build <city>')
RAW = os.path.join(ROOT, 'cities', city, 'raw')
DATA = os.path.join(ROOT, 'docs', city, 'data')
SPACING_KM = 1.5

base = json.load(open(os.path.join(DATA, 'base.geojson')))
neighbours = [f for f in base['features'] if f['properties'].get('kind') == 'neighbour']

if cmd == 'points':
    from shapely.geometry import shape, Point
    from shapely.ops import unary_union
    from shapely.prepared import prep
    area = unary_union([shape(f['geometry']).buffer(0) for f in neighbours])
    inside = prep(area)
    w, s, e, n = area.bounds
    dy = SPACING_KM / 111.0
    dx = SPACING_KM / (111.0 * math.cos(math.radians((s + n) / 2)))
    pts, y = [], s + dy / 2
    while y < n:
        x = w + dx / 2
        while x < e:
            if inside.contains(Point(x, y)):
                pts.append([round(x, 4), round(y, 4)])
            x += dx
        y += dy
    json.dump({'spacing_km': SPACING_KM, 'points': pts}, open(os.path.join(RAW, 'drive_points.json'), 'w'), separators=(',', ':'))
    print('drive points:', len(pts), 'for', city)
    sys.exit()

# ---------- build ----------
from shapely.geometry import shape, Point
from shapely.prepared import prep
src = json.load(open(os.path.join(RAW, 'drive_times.json')))
times = [(x, y, sec / 60) for x, y, sec in src['points'] if sec is not None]
shapes = [(f, prep(shape(f['geometry']).buffer(0))) for f in neighbours]
per = {id(f): [] for f in neighbours}
for x, y, m in times:
    p = Point(x, y)
    for f, g in shapes:
        if g.contains(p):
            per[id(f)].append(m); break
missing = []
for f in neighbours:
    p = f['properties']
    p.pop('drive', None)
    if p.get('rest'):
        continue
    ms = per[id(f)]
    if not ms:
        # a small municipality the grid stepped over: use the nearest point to its label point
        lx, ly = p['lp']
        ms = [min(times, key=lambda t: (t[0] - lx) ** 2 + (t[1] - ly) ** 2)[2]]
        missing.append(p['name'])
    p['drive'] = round(statistics.median(ms))
json.dump(base, open(os.path.join(DATA, 'base.geojson'), 'w'), separators=(',', ':'))
grid = {'hub': src['hub'], 'date': src.get('fetched', ''), 'spacing_km': SPACING_KM,
        'points': [[round(x, 3), round(y, 3), round(m)] for x, y, m in times]}
json.dump(grid, open(os.path.join(DATA, 'drive_grid.json'), 'w'), separators=(',', ':'))
ds = [f['properties']['drive'] for f in neighbours if 'drive' in f['properties']]
band = lambda m: '<30' if m < 30 else '30-60' if m < 60 else '60-90' if m < 90 else '90+'
from collections import Counter
print('drive lens:', len(ds), 'municipalities,', dict(Counter(band(m) for m in ds)), '· range', min(ds), '-', max(ds), 'min ·',
      len(missing), 'placed by nearest point', '·', len(times), 'grid points')

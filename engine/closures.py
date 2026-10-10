"""Build docs/<city>/data/closures.geojson: road closures and lane restrictions caused by transit
construction, from cities/<city>/raw/closures/permits.json (written daily by the city's
fetch_closures.py) and the city's construction.json.

What it does, in order:
  1. Keeps permits in force today or starting within the next 7 days (the city's own time zone).
  2. Says which project each permit belongs to, by where it is: the nearest line under construction
     (docs/<city>/data/construction.geojson) within closures.near metres; otherwise the nearest line
     being upgraded (construction.json "upgrades", e.g. GO lines); otherwise, if it sits on an open
     line listed in "existing" (aftercare on a line that has opened), it is dropped; otherwise "other".
  3. Marks it as on a drawn arterial (same street name, within 35 m of docs/<city>/data/streets.geojson,
     or Toronto's roadClass Major/Minor Arterial). Lane restrictions on local streets are dropped;
     full closures on local streets are kept (the page shows them only when zoomed in).
  4. Merges permits for the same stretch and kind (overlapping renewals), keeping the latest end date.

Usage: python3 engine/closures.py <city>
"""
import json, math, os, re, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
city = sys.argv[1]
CDIR, DATA = os.path.join(ROOT, 'cities', city), os.path.join(ROOT, 'docs', city, 'data')
cfg = json.load(open(os.path.join(CDIR, 'construction.json')))
cc = cfg['closures']
TZ = ZoneInfo(cc['tz'])
NEAR = cc.get('near', 500)
src = json.load(open(os.path.join(CDIR, 'raw', 'closures', 'permits.json')))
today = datetime.now(TZ).date()
horizon = today + timedelta(days=7)

lat0 = cfg.get('lat0', 43.7)
KX, KY = 111320 * math.cos(math.radians(lat0)), 110540
P = lambda c: (c[0] * KX, c[1] * KY)


def parts(geom):
    t = geom['type']
    if t == 'LineString': return [geom['coordinates']]
    if t == 'MultiLineString': return geom['coordinates']
    return []


def seg_d(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0 if not L2 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def index(features, key):
    """[(key, [[projected points], ...], bbox)] for quick nearest-line checks."""
    out = []
    for f in features:
        for ln in parts(f['geometry']):
            pts = [P(c) for c in ln]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out.append((key(f), pts, (min(xs), min(ys), max(xs), max(ys))))
    return out


def nearest(pts, idx, limit):
    best = (None, limit + 1)
    for k, line, (x0, y0, x1, y1) in idx:
        if not any(x0 - limit <= p[0] <= x1 + limit and y0 - limit <= p[1] <= y1 + limit for p in pts):
            continue
        for i in range(len(line) - 1):
            d = min(seg_d(p, line[i], line[i + 1]) for p in pts)
            if d < best[1]:
                best = (k, d)
    return best if best[1] <= limit else (None, None)


def load(name):
    p = os.path.join(DATA, name + '.geojson')
    return json.load(open(p))['features'] if os.path.exists(p) else []


lines = load('construction')
LINES = index([f for f in lines if f['properties'].get('part') != 'station'], lambda f: f['properties']['id'])
NAMES = {f['properties']['id']: f['properties']['name'] for f in lines if f['properties'].get('part') != 'station'}
up = cfg.get('upgrades')
UPG = index([f for f in load(up['file']) if not up.get('only') or f['properties'][up['field']] in up['only']],
            lambda f: f['properties'][up['field']]) if up else []
EXIST = index([f for n in cfg.get('existing', []) for f in load(n)], lambda f: 'existing')
streets = load('streets')
STREETS = index(streets, lambda f: f['properties']['name'])


def norm(s):
    s = (s or '').upper()
    s = re.sub(r'\b(N|S|E|W|NORTH|SOUTH|EAST|WEST)\b', ' ', s)
    s = re.sub(r'\b(AVE|AVENUE|ST|STREET|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE|PKWY|PARKWAY|HWY|PL|PLACE|CT|CRT|TER|WAY|CRES|TRL)\b', ' ', s)
    return re.sub(r'[^A-Z0-9]+', ' ', s).strip()


def on_arterial(p, pts):
    if p.get('roadClass') in ('Major Arterial Road', 'Minor Arterial Road'):
        return True
    want = norm(p['street'])
    for name, line, (x0, y0, x1, y1) in STREETS:
        if norm(name) != want or not any(x0 - 35 <= q[0] <= x1 + 35 and y0 - 35 <= q[1] <= y1 + 35 for q in pts):
            continue
        if any(seg_d(q, line[i], line[i + 1]) <= 35 for q in pts for i in range(len(line) - 1)):
            return True
    return False


def day(s):
    return datetime.strptime(s[:10], '%Y-%m-%d').date() if s else None


kept, dropped = {}, {'dates': 0, 'existing line': 0, 'local lane work': 0}
for p in src['permits']:
    s, e = day(p['start']), day(p['end'])
    if not s or not e or e < today or s > horizon:
        dropped['dates'] += 1
        continue
    pts = [P(c) for c in p['coords']]
    pid, d = nearest(pts, LINES, NEAR)
    if pid:
        proj, pname = pid, NAMES[pid]
    else:
        uname, _ = nearest(pts, UPG, NEAR) if UPG else (None, None)
        if uname:
            proj, pname = 'up', up['label'].format(name=uname)
        elif EXIST and nearest(pts, EXIST, NEAR)[0]:
            dropped['existing line'] += 1
            continue
        else:
            proj, pname = 'other', cc.get('otherLabel', 'Other transit work')
    art = on_arterial(p, pts)
    if not art and p['kind'] != 'closed':
        dropped['local lane work'] += 1
        continue
    key = (norm(p['street']), p['kind'], tuple(sorted(tuple(round(v, 4) for v in c) for c in p['coords'][:1] + p['coords'][-1:])))   # either direction
    props = {'proj': proj, 'name': pname, 'street': p['street'], 'extent': p['extent'], 'kind': p['kind'], 'art': art,
             'start': p['start'], 'end': p['end'], 'hours': p.get('hours'), 'days': p.get('days'), 'both': p.get('both', False),
             'who': p.get('who'), 'desc': (p.get('desc') or '')[:220]}
    old = kept.get(key)
    if old and old['properties']['end'] >= props['end']:
        continue
    coords = p['coords']
    geom = {'type': 'Point', 'coordinates': coords[0]} if len(coords) == 1 else {'type': 'LineString', 'coordinates': coords}
    kept[key] = {'type': 'Feature', 'properties': props, 'geometry': geom}

feats = sorted(kept.values(), key=lambda f: (f['properties']['kind'] != 'closed', f['properties']['street']))
out = {'type': 'FeatureCollection', 'asof': src['fetched'], 'today': str(today), 'features': feats}
json.dump(out, open(os.path.join(DATA, 'closures.geojson'), 'w'), separators=(',', ':'), ensure_ascii=False)
from collections import Counter
print(city, 'closures:', len(feats), 'kept of', len(src['permits']), '· dropped', dropped,
      '· by project', dict(Counter(f['properties']['name'] for f in feats)),
      '· closed', sum(f['properties']['kind'] == 'closed' for f in feats), '· on arterials', sum(f['properties']['art'] for f in feats))

"""Fetch road restrictions caused by transit construction from the City of Toronto's live Road
Restrictions feed (v3 JSON, refreshed in real time) into raw/closures/permits.json, in the common
shape engine/closures.py reads. Run daily from GitHub Actions (*Fetch transit closures*); the
sandbox can't reach secure.toronto.ca.

Kept: every permit whose source / work event type / permit type is "Metrolinx", plus permits from
the transit consortiums in construction.json "closures.contractors" (a few Ontario Line permits
are filed as "Other"). Which project a permit belongs to is decided later, by where it is.

The feed isn't strict JSON (stray backslashes in free text), so lone backslashes are escaped first.
"""
import json, os, re, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'https://secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json'
TZ = ZoneInfo('America/Toronto')
cfg = json.load(open(os.path.join(HERE, 'construction.json')))
CONTRACTORS = [c.lower() for c in cfg['closures'].get('contractors', [])]
OUT = os.path.join(HERE, 'raw', 'closures')
os.makedirs(OUT, exist_ok=True)

req = urllib.request.Request(URL, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
raw = urllib.request.urlopen(req, timeout=180).read().decode('utf-8', 'replace')
raw = re.sub(r'\\(["\\/bfnrtu]?)', lambda m: m.group(0) if m.group(1) else '\\\\', raw)
data = json.loads(raw, strict=False)
recs = [r for v in data.values() if isinstance(v, list) for r in v]


def is_transit(r):
    if any('metrolinx' in str(r.get(k) or '').lower() for k in ('source', 'workEventType', 'permitType')):
        return True
    c = (r.get('contractor') or '').lower()
    return any(k in c for k in CONTRACTORS)


def local(ms):
    return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).astimezone(TZ).strftime('%Y-%m-%dT%H:%M') if ms else None


def hours(r):
    """'24h', '21:00–05:00', or per-day text; days: daily / weekdays / weekends / custom."""
    ev = r.get('scheduleEveryday')
    days = [r.get('schedule' + d) for d in ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')]
    if ev:
        h, d = ev, 'daily'
    elif any(days):
        wk, we = days[:5], days[5:]
        vals = {x for x in days if x}
        h = vals.pop() if len(vals) == 1 else None
        d = 'weekdays' if all(wk) and not any(we) else 'weekends' if all(we) and not any(wk) else 'daily' if all(days) else 'some days'
    else:
        return None, None
    if h in ('00:00-23:59', '00:00-24:00'):
        h = '24h'
    elif h:
        h = h.replace('-', '–')
    return h, d


out = []
for r in recs:
    if not is_transit(r):
        continue
    try:
        pts = json.loads('[' + r['geoPolyline'] + ']') if r.get('geoPolyline') else [[float(r['longitude']), float(r['latitude'])]]
    except Exception:
        continue
    h, d = hours(r)
    kind = 'closed' if r.get('type') == 'ROAD_CLOSED' else 'narrowed'
    out.append({
        'id': r['id'],
        'street': r.get('road'),
        'extent': (r.get('name') or '').strip(),
        'kind': kind,
        'both': r.get('directionsAffected') == 'BOTH_DIRECTIONS',
        'start': local(r.get('startTime')), 'end': local(r.get('endTime')),
        'hours': h, 'days': d,
        'who': (r.get('contractor') or '').strip(),
        'desc': re.sub(r'\s+', ' ', (r.get('description') or '').replace('Toronto-TMC:', '')).strip(),
        'roadClass': r.get('roadClass'),
        'coords': [[round(x, 6), round(y, 6)] for x, y in pts],
    })

json.dump({'fetched': datetime.now(TZ).strftime('%Y-%m-%dT%H:%M'), 'source': URL, 'permits': out},
          open(os.path.join(OUT, 'permits.json'), 'w'), indent=0)
print('Toronto:', len(recs), 'restrictions in feed;', len(out), 'from transit construction')

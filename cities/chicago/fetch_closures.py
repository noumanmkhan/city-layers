"""Fetch street closures caused by transit construction from CDOT's Transportation Department Permits
(Chicago Data Portal, Socrata pubx-yq2d, updated daily) into raw/closures/permits.json, in the common
shape engine/closures.py reads. Run daily from GitHub Actions (*Fetch transit closures*); the sandbox
can't reach the portal.

Kept: open permits active now or within the next week whose application name, comments or detail name
a project in construction.json "closures.keywords" (Red Line Extension: "RLE"; Red and Purple
Modernization: "RPM"), matched as whole words, and whose street closure is Full, Partial or Curblane.
Sidewalk-only and unstated closures are left out (the map draws roads).

CDOT gives a point at the start of an address range plus the house numbers. Chicago's grid puts 800
numbers in a mile, counted from State St (east-west) and Madison St (north-south), so the far end of the
range is placed from the "to" number along the street's direction. A one-address range gets a short stub.
"""
import json, math, os, re, urllib.parse, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
API = 'https://data.cityofchicago.org/resource/pubx-yq2d.json'
TZ = ZoneInfo('America/Chicago')
cfg = json.load(open(os.path.join(HERE, 'construction.json')))['closures']
WORDS = re.compile(r'\b(' + '|'.join(re.escape(k) for k in cfg['keywords']) + r')\b', re.I)
KIND = {'Full': 'closed', 'Partial': 'narrowed', 'Curblane': 'narrowed'}
OUT = os.path.join(HERE, 'raw', 'closures')
os.makedirs(OUT, exist_ok=True)

now = datetime.now(TZ)
today, week = now.date(), (now + timedelta(days=8)).date()
where = (f"applicationstatus = 'Open' AND applicationenddate >= '{today}T00:00:00' AND applicationstartdate <= '{week}T00:00:00' "
         "AND streetclosure in ('Full', 'Partial', 'Curblane') AND ("
         + ' OR '.join(f"upper({f}) like '%{k.upper()}%'" for f in ('applicationname', 'comments', 'detail') for k in cfg['keywords'])
         + ')')
url = API + '?' + urllib.parse.urlencode({'$where': where, '$limit': 5000})
req = urllib.request.Request(url, headers={'User-Agent': 'city-layers-pipeline (github.com/noumanmkhan/city-layers)'})
rows = json.load(urllib.request.urlopen(req, timeout=180))

M_PER_NUM = 1609.344 / 800
KX = 111320 * math.cos(math.radians(41.85))


def far_end(lon, lat, direction, n_from, n_to):
    """Point n_to - n_from address numbers along the street, in its grid direction."""
    d = (n_to - n_from) * M_PER_NUM
    if not d:
        d = 30                                      # a single address: draw a short stub
    d = max(-2500, min(2500, d))
    dx, dy = {'N': (0, 1), 'S': (0, -1), 'E': (1, 0), 'W': (-1, 0)}.get(direction, (0, 0))
    if not (dx or dy):
        return None
    return [round(lon + dx * d / KX, 6), round(lat + dy * d / 110540, 6)]


def street_name(r):
    s = ' '.join(x for x in (r.get('direction'), (r.get('streetname') or '').title(), (r.get('suffix') or '').title()) if x)
    return re.sub(r'\b(\d+)(St|Nd|Rd|Th)\b', lambda m: m.group(1) + m.group(2).lower(), s)


out, skipped = [], 0
for r in rows:
    text = ' '.join(r.get(k) or '' for k in ('applicationname', 'comments', 'detail'))
    if not WORDS.search(text):
        continue                                    # "RLE" inside Harlem, Orleans, Charles...
    try:
        lon, lat = float(r['longitude']), float(r['latitude'])
        a, b = int(float(r.get('streetnumberfrom') or 0)), int(float(r.get('streetnumberto') or 0))
    except (KeyError, TypeError, ValueError):
        skipped += 1
        continue
    end = far_end(lon, lat, r.get('direction'), a, b or a)
    if not end:
        skipped += 1
        continue
    extent = f"{a}–{b} {street_name(r)}" if b and b != a else f"{a} {street_name(r)}"
    out.append({
        'id': f"{r.get('applicationnumber')}:{a}-{b}:{r.get('streetname')}",
        'street': street_name(r),
        'extent': extent,
        'kind': KIND[r['streetclosure']],
        'both': r['streetclosure'] == 'Full',
        'start': (r.get('applicationstartdate') or '')[:10], 'end': (r.get('applicationenddate') or '')[:10],
        'hours': None, 'days': None,
        'who': (r.get('primarycontactlast') or '').rstrip('*').strip(),
        'desc': re.sub(r'<[^>]+>|\s+', ' ', r.get('comments') or r.get('detail') or r.get('applicationname') or '').strip(),
        'project': r.get('applicationname'),
        'coords': [[round(lon, 6), round(lat, 6)], end],
    })

json.dump({'fetched': now.strftime('%Y-%m-%dT%H:%M'), 'source': API, 'permits': out},
          open(os.path.join(OUT, 'permits.json'), 'w'), indent=0)
print('Chicago:', len(rows), 'permits matched the query;', len(out), 'kept;', skipped, 'without a usable location')

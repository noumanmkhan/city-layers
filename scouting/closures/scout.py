"""Scouting run for a "Transit under construction" layer's road closures (Toronto and Chicago).

Not a city build. Question to answer: can each city's open permit data give us the road closures
caused by building transit, limited to the arterials the map already draws (docs/<city>/data/
streets.geojson: major and minor arterials in Toronto, OSM primary/secondary in Chicago)?

  Toronto: the City's live Road Restrictions feed (v3 JSON). One snapshot: current and upcoming
           permits, each with a polyline, roadClass, type (CONSTRUCTION / ROAD_CLOSED), daily hours,
           and source/workEventType/permitType (Metrolinx work says "Metrolinx").
  Chicago: CDOT Transportation Department Permits (Socrata pubx-yq2d, updated daily). Point at the
           start of an address range, a street-closure field, dates only. Transit work is found by
           applicant (Walsh-VINCI builds the Red Line Extension; the CTA itself) and by keywords.

For each city it writes out/<city>.json (the transit-related records, trimmed) and a summary:
counts by type, by applicant/contractor, on a drawn arterial or not, and the street names.
Also records each feed's CORS header (could a browser read it live?).

Run by .github/workflows/scout-closures.yml (the sandbox can't reach these hosts).
Nothing here feeds the map.
"""
import json, math, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'scouting', 'closures', 'out')
os.makedirs(OUT, exist_ok=True)
UA = 'city-layers-scout/1.0 (+https://maps.noumankhan.ca; one-off road-closure data check)'
NOW = datetime.now(timezone.utc)
TODAY = NOW.date()
NEAR_M = 40          # a permit counts as "on a drawn arterial" if within this distance of one (streets are simplified)


def http(url, timeout=180):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)


def retry(fn, tries=4, label=''):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f'  {label} attempt {i + 1} failed: {e}')
            time.sleep(5 * (i + 1))
    raise SystemExit(f'{label}: gave up')


# ---------- drawn arterials ----------
def load_streets(city):
    """Return (list of (name, cls, [segments as lists of (x,y) metres])), projection fn."""
    d = json.load(open(os.path.join(ROOT, 'docs', city, 'data', 'streets.geojson')))
    lat0 = 43.7 if city == 'toronto' else 41.85
    kx = 111320 * math.cos(math.radians(lat0))
    proj = lambda lon, lat: (lon * kx, lat * 110540)
    out = []
    for f in d['features']:
        g = f['geometry']
        lines = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
        out.append((f['properties']['name'], f['properties']['cls'], [[proj(*p) for p in ln] for ln in lines]))
    return out, proj


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def nearest_street(pts, streets):
    """pts in metres. Return (name, cls, metres) of the drawn street closest to the record's points."""
    best = (None, None, 1e9)
    for name, cls, lines in streets:
        for ln in lines:
            # cheap box reject
            xs = [q[0] for q in ln]; ys = [q[1] for q in ln]
            if not any(min(xs) - 200 < p[0] < max(xs) + 200 and min(ys) - 200 < p[1] < max(ys) + 200 for p in pts):
                continue
            for i in range(len(ln) - 1):
                d = min(seg_dist(p, ln[i], ln[i + 1]) for p in pts)
                if d < best[2]:
                    best = (name, cls, d)
    return best


def norm_street(s):
    s = (s or '').upper()
    s = re.sub(r'\b(N|S|E|W|NORTH|SOUTH|EAST|WEST)\b', ' ', s)
    s = re.sub(r'\b(AVE|AVENUE|ST|STREET|RD|ROAD|BLVD|BOULEVARD|DR|DRIVE|PKWY|PARKWAY|HWY|PL|CT|TER|WAY)\b', ' ', s)
    return re.sub(r'[^A-Z0-9]+', ' ', s).strip()


def cors(h):
    return {k: v for k, v in h.items() if k.lower().startswith('access-control')} or 'none'


# ---------- Toronto ----------
TRANSIT_WORDS = re.compile(r'METROLINX|ONTARIO LINE|ONTARIO TRANSIT GROUP|EGLINTON (CROSSTOWN )?WEST|SCARBOROUGH SUBWAY|'
                           r'LINE 2 EAST|YONGE NORTH|SUBWAY EXTENSION|\bOLE?\b|\bECWE\b|\bSSE\b|\bYNSE\b|LRT|TUNNEL|STATION', re.I)


def toronto():
    print('Toronto: road restrictions feed')
    raw, hdr = retry(lambda: http('https://secure.toronto.ca/opendata/cart/road_restrictions/v3?format=json'), label='toronto feed')
    # The feed isn't strict JSON: some text fields hold stray backslashes. Escape them before parsing.
    text = re.sub(r'\\(["\\/bfnrtu]?)', lambda m: m.group(0) if m.group(1) else '\\\\', raw.decode('utf-8', 'replace'))
    data = json.loads(text, strict=False)
    recs = [r for k, v in data.items() if isinstance(v, list) for r in v]
    print('  groups:', {k: len(v) for k, v in data.items() if isinstance(v, list)}, 'records', len(recs))
    streets, proj = load_streets('toronto')

    def is_mx(r):
        return any('metrolinx' in str(r.get(k) or '').lower() for k in ('source', 'workEventType', 'permitType'))

    mx, maybe = [], []
    for r in recs:
        if is_mx(r):
            mx.append(r)
        elif TRANSIT_WORDS.search(' '.join(str(r.get(k) or '') for k in ('description', 'contractor', 'name'))):
            maybe.append(r)

    def trim(r):
        pts = json.loads('[' + (r.get('geoPolyline') or '') + ']') if r.get('geoPolyline') else []
        pm = [proj(*p) for p in pts] or [proj(float(r['longitude']), float(r['latitude']))]
        near = nearest_street(pm, streets)
        ms = lambda t: datetime.fromtimestamp(int(t) / 1000, timezone.utc).strftime('%Y-%m-%d %H:%M') if t else None
        return {
            'id': r['id'], 'road': r.get('road'), 'name': r.get('name'), 'from': r.get('fromRoad'), 'to': r.get('toRoad'),
            'roadClass': r.get('roadClass'), 'type': r.get('type'), 'subType': r.get('subType'),
            'directions': r.get('directionsAffected'), 'start_utc': ms(r.get('startTime')), 'end_utc': ms(r.get('endTime')),
            'workPeriod': r.get('workPeriod'), 'everyday': r.get('scheduleEveryday'), 'monday': r.get('scheduleMonday'),
            'source': r.get('source'), 'contractor': r.get('contractor'), 'maxImpact': r.get('maxImpact'),
            'description': (r.get('description') or '').replace('Toronto-TMC: ', ''),
            'nearest_drawn': near[0], 'nearest_cls': near[1], 'nearest_m': round(near[2]),
            'on_drawn': near[2] <= NEAR_M and norm_street(near[0]) == norm_street(r.get('road')),
            'polyline': pts,
        }

    mxt, mayt = [trim(r) for r in mx], [trim(r) for r in maybe]
    on = [r for r in mxt if r['on_drawn']]
    summ = {
        'records_in_feed': len(recs),
        'cors': cors(hdr),
        'metrolinx': {
            'count': len(mxt),
            'by_type': Counter(f"{r['type']}/{r['subType']}" for r in mxt),
            'by_roadClass': Counter(r['roadClass'] for r in mxt),
            'by_contractor': Counter(r['contractor'] for r in mxt),
            'by_workPeriod': Counter(r['workPeriod'] for r in mxt),
            'on_drawn_arterial': len(on),
            'on_drawn_by_type': Counter(f"{r['type']}/{r['subType']}" for r in on),
            'on_drawn_roads': Counter(r['road'] for r in on),
            'off_drawn_roads': Counter(r['road'] for r in mxt if not r['on_drawn']),
            'class_vs_drawn': Counter(f"{r['roadClass']} -> {'drawn' if r['on_drawn'] else 'not drawn'}" for r in mxt),
            'active_today': sum(1 for r in mxt if r['start_utc'] and r['start_utc'][:10] <= str(TODAY) <= (r['end_utc'] or '9')[:10]),
            'end_dates': sorted({(r['end_utc'] or '')[:7] for r in mxt}),
        },
        'not_metrolinx_but_transit_words': {
            'count': len(mayt),
            'by_source': Counter(r['source'] for r in mayt),
            'by_contractor': Counter(r['contractor'] for r in mayt),
            'examples': [{k: r[k] for k in ('road', 'source', 'contractor', 'type', 'description')} for r in mayt[:25]],
        },
    }
    json.dump({'metrolinx': mxt, 'transit_words': mayt}, open(os.path.join(OUT, 'toronto.json'), 'w'), indent=1)
    return summ


# ---------- Chicago ----------
SOCRATA = 'https://data.cityofchicago.org/resource/pubx-yq2d.json'
CHI_TRANSIT = re.compile(r'WALSH|VINCI|CHICAGO TRANSIT|\bCTA\b|RED LINE|\bRLE\b|TRANSIT AUTH', re.I)


def soql(params):
    url = SOCRATA + '?' + urllib.parse.urlencode(params)
    raw, hdr = retry(lambda: http(url), label='socrata')
    return json.loads(raw), hdr


def chicago():
    print('Chicago: CDOT permits')
    lo = (TODAY - timedelta(days=7)).isoformat()
    hi = (TODAY + timedelta(days=60)).isoformat()
    active = f"applicationenddate >= '{lo}T00:00:00' AND applicationstartdate <= '{hi}T00:00:00'"

    # 1. who holds active permits, and what closure values exist
    top, hdr = soql({'$select': 'primarycontactlast, count(*) AS n', '$where': active,
                     '$group': 'primarycontactlast', '$order': 'n DESC', '$limit': 80})
    closures, _ = soql({'$select': 'streetclosure, count(*) AS n', '$where': active, '$group': 'streetclosure', '$order': 'n DESC', '$limit': 50})
    status, _ = soql({'$select': 'applicationstatus, count(*) AS n', '$where': active, '$group': 'applicationstatus', '$order': 'n DESC', '$limit': 20})
    total, _ = soql({'$select': 'count(*) AS n', '$where': active})
    print('  active rows:', total)

    # 2. transit-related rows: by applicant or by keyword in name/comments/detail
    kw = ("(upper(primarycontactlast) like '%WALSH%' OR upper(primarycontactlast) like '%VINCI%' OR "
          "upper(primarycontactlast) like '%CHICAGO TRANSIT%' OR upper(primarycontactlast) like '%CTA%' OR "
          "upper(applicationname) like '%RED LINE%' OR upper(applicationname) like '%RLE%' OR "
          "upper(comments) like '%RED LINE%' OR upper(comments) like '%RLE%' OR upper(detail) like '%RED LINE%')")
    rows, _ = soql({'$where': f'{active} AND {kw}', '$limit': 5000})
    print('  transit-related rows:', len(rows))

    streets, proj = load_streets('chicago')
    keep = []
    for r in rows:
        try:
            pm = [proj(float(r['longitude']), float(r['latitude']))]
        except (KeyError, ValueError):
            pm = None
        near = nearest_street(pm, streets) if pm else (None, None, 1e9)
        street = ' '.join(x for x in (r.get('direction'), r.get('streetname'), r.get('suffix')) if x)
        keep.append({
            'app': r.get('applicationnumber'), 'applicant': r.get('primarycontactlast'), 'project': r.get('applicationname'),
            'type': r.get('applicationdescription'), 'worktype': r.get('worktypedescription'), 'status': r.get('applicationstatus'),
            'closure': r.get('streetclosure'), 'street': street, 'from_no': r.get('streetnumberfrom'), 'to_no': r.get('streetnumberto'),
            'placement': r.get('placement'), 'start': (r.get('applicationstartdate') or '')[:10], 'end': (r.get('applicationenddate') or '')[:10],
            'comments': (r.get('comments') or '')[:300], 'detail': (r.get('detail') or '')[:300], 'ward': r.get('ward'),
            'lat': r.get('latitude'), 'lon': r.get('longitude'),
            'nearest_drawn': near[0], 'nearest_m': round(near[2]) if near[2] < 1e8 else None,
            'on_drawn': near[2] <= NEAR_M and norm_street(near[0]) == norm_street(r.get('streetname')),
        })
    on = [r for r in keep if r['on_drawn']]
    summ = {
        'active_window': [lo, hi],
        'active_rows_citywide': total,
        'cors': cors(hdr),
        'citywide_streetclosure_values': closures,
        'citywide_status_values': status,
        'top_applicants_citywide': top,
        'transit': {
            'count': len(keep),
            'by_applicant': Counter(r['applicant'] for r in keep),
            'by_project': Counter(r['project'] for r in keep),
            'by_type': Counter(f"{r['type']} / {r['worktype']}" for r in keep),
            'by_closure': Counter(r['closure'] for r in keep),
            'by_status': Counter(r['status'] for r in keep),
            'by_ward': Counter(r['ward'] for r in keep),
            'with_point': sum(1 for r in keep if r['lat']),
            'with_range': sum(1 for r in keep if r['from_no'] and r['to_no'] and r['from_no'] != r['to_no']),
            'on_drawn_arterial': len(on),
            'on_drawn_by_closure': Counter(r['closure'] for r in on),
            'on_drawn_streets': Counter(r['street'] for r in on),
            'off_drawn_streets': Counter(r['street'] for r in keep if not r['on_drawn']).most_common(40),
        },
    }
    json.dump(keep, open(os.path.join(OUT, 'chicago.json'), 'w'), indent=1)
    return summ


summary = {'run_utc': NOW.isoformat(timespec='seconds')}
for name, fn in (('toronto', toronto), ('chicago', chicago)):
    try:
        summary[name] = fn()
    except SystemExit as e:
        summary[name] = {'error': str(e)}
        print('  ', e)
    except Exception as e:
        summary[name] = {'error': repr(e)}
        print('  error', repr(e))
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
print(json.dumps(summary, indent=1, default=str)[:6000])

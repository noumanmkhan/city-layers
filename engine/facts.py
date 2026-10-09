"""Facts engine: what makes each neighbourhood / community area stand out, for the "What's here" card.
Usage: python3 engine/facts.py <city>   (run after the city's profiles file is built)

Each unit is ranked against its peers on figures the map already has, and its strongest standing
becomes a short sentence ("Highest rents in North York", "Quickest trip to the Loop on the South
Side"). Peers are the whole city and the unit's own areas: "facts.peers" in city.json lists one or
more fill layers (Toronto: Old Toronto's Downtown/Midtown/… and the former cities; Chicago: the
sides). Areas with fewer than MIN_PEERS units aren't used as a peer group.

Rules (see app-contract/DATA_CONTRACT.md, "Describe, don't rank"):
- Only non-demographic figures: housing cost, tenure, getting to work, home types, age of homes,
  transit time downtown. Language and anything like it never feed facts.
- Money facts are worded softly at the low end ("Among the most affordable rents"), never
  "cheapest" or "lowest value".
- A fact needs a top-3 (or bottom-3) place. Strength is place / group size, so third of 158 beats
  first of 22; ties in a figure share a place, and a place shared by more than 3 units doesn't count.
- "Longest transit trip downtown" is kept but ranked last when choosing which fact leads.
- It must also stand out: at least 20% away from the group's median (and, for shares, at least
  5 points), so "top 3 for biking at 4%" doesn't count.

Writes "facts" into docs/<city>/data/<lens.file>: up to 3 per unit, strongest first:
  [{"text", "field", "end": "high"|"low", "scope": "city"|"peers", "rank", "of", "value"}]
"""
import json, os, sys
from shapely.geometry import shape

HERE = os.path.dirname(os.path.abspath(__file__))
city = sys.argv[1] if len(sys.argv) > 1 else sys.exit('usage: facts.py <city>')
ROOT = os.path.join(HERE, '..')
cfg = json.load(open(os.path.join(ROOT, 'cities', city, 'city.json')))
F = cfg['facts']
DATA = os.path.join(ROOT, 'docs', city, 'data')
PROF = os.path.join(DATA, cfg['lens']['file'])
MIN_PEERS, TOP, KEEP = 6, 3, 3

layers = {it['id']: it for g in cfg['groups'] for it in g[1]}
units_file = next(it['file'] for it in layers.values() if it['kind'] == 'units')
peer_files = [layers[p]['file'] for p in ([F['peers']] if isinstance(F['peers'], str) else F['peers'])]
hub_lens = next((l for l in cfg['lens']['lenses'] if l.get('minutes')), None)
hub = hub_lens['minutes'] if hub_lens else None
built = cfg['card']['living']['built']['bands']

# What each figure is, and how to say it. (field, getter, high text, high "among" text, low text, low "among" text, unit)
# None skips that end. {where} is filled with "in Toronto" or "in Etobicoke" / "on the South Side".
pct = lambda v: f'{v}%'
FIELDS = [
    ('value', lambda d: d.get('value'), 'Highest home values {where}', 'Among the highest home values {where}',
     'Among the most affordable homes {where}', 'Among the most affordable homes {where}', lambda v: f'median ${v / 1e6:.1f}M' if v >= 1e6 else f'median ${round(v / 1e3)}K'),
    ('rent', lambda d: d.get('rent'), 'Highest rents {where}', 'Among the highest rents {where}',
     'Among the most affordable rents {where}', 'Among the most affordable rents {where}', lambda v: f'median ${v:,}/mo'),
    ('renterPct', lambda d: d.get('renterPct'), 'Highest share of renters {where}', 'Among the highest shares of renters {where}',
     'Highest share of homeowners {where}', 'Among the highest shares of homeowners {where}', lambda v: f'{v}% rent'),
    ('transitPct', lambda d: d.get('transitPct'), 'Most likely to take transit to work {where}', 'Among the likeliest to take transit to work {where}',
     None, None, lambda v: f'{v}% of commuters'),
    ('walkBikePct', lambda d: d.get('walkBikePct'), 'Most likely to walk or bike to work {where}', 'Among the likeliest to walk or bike to work {where}',
     None, None, lambda v: f'{v}% of commuters'),
    ('carPct', lambda d: d.get('carPct'), 'Most likely to drive to work {where}', 'Among the likeliest to drive to work {where}',
     None, None, lambda v: f'{v}% of commuters'),
    ('detached', lambda d: (d.get('homes') or [None])[0], 'Most detached houses {where}', 'Among the most detached houses {where}',
     None, None, lambda v: f'{v}% of homes'),
    ('large', lambda d: (d.get('homes') or [None] * 4)[3], 'Most homes in large apartment buildings {where}', 'Among the most homes in large apartment buildings {where}',
     None, None, lambda v: f'{v}% of homes'),
    ('oldest', lambda d: (d.get('built') or [None])[0], 'Oldest housing {where}', 'Among the oldest housing {where}',
     None, None, lambda v: f'{v}% built {built[0].lower()}'),
    ('newest', lambda d: (d.get('built') or [None] * 4)[3], 'Newest housing {where}', 'Among the newest housing {where}',
     None, None, lambda v: f'{v}% built {built[3]}'),
]
if hub:
    FIELDS.append(('hub', lambda d: d.get(hub), 'Longest transit trip to ' + F['hub'] + ' {where}', 'Among the longest transit trips to ' + F['hub'] + ' {where}',
                   'Quickest transit trip to ' + F['hub'] + ' {where}', 'Among the quickest transit trips to ' + F['hub'] + ' {where}', lambda v: f'about {v} min'))

prof = json.load(open(PROF))
units = {str(f['properties']['code']): shape(f['geometry']).buffer(0) for f in json.load(open(os.path.join(DATA, units_file + '.geojson')))['features']}
scopes = {'city': {k: 'city' for k in prof}}
where = {'city': lambda k: F['city']}
for i, pf in enumerate(peer_files):
    groups = [(f['properties']['name'], shape(f['geometry']).buffer(0)) for f in json.load(open(os.path.join(DATA, pf + '.geojson')))['features']]
    po = {}
    for k, u in units.items():   # the area holding most of the unit, if it holds at least half
        best = max(groups, key=lambda g: g[1].intersection(u).area)
        if best[1].intersection(u).area >= .5 * u.area: po[k] = best[0]
    scopes['peers%d' % i] = {k: po.get(k) for k in prof}
    # "in {name}", or a name's own wording from facts.inNames ("in the West End").
    where['peers%d' % i] = (lambda po: lambda k: F.get('inNames', {}).get(po[k]) or F['in'].replace('{name}', po[k]))(po)

found = {k: [] for k in prof}
for field, get, hi1, hi3, lo1, lo3, fmt in FIELDS:
    for scope, member in scopes.items():
        groups_ = {}
        for k in prof:
            if member[k] is not None and get(prof[k]) is not None:
                groups_.setdefault(member[k], []).append(k)
        for g, ks in groups_.items():
            if len(ks) < MIN_PEERS or (scope != 'city' and len(ks) == len(prof)):
                continue
            vals = [get(prof[k]) for k in ks]
            mid = sorted(vals)[len(vals) // 2]
            share = field not in ('value', 'rent', 'hub')
            for k in ks:
                v = get(prof[k])
                for end, t1, t3 in (('high', hi1, hi3), ('low', lo1, lo3)):
                    if not t1: continue
                    better = sum(x > v for x in vals) if end == 'high' else sum(x < v for x in vals)
                    same = sum(x == v for x in vals)
                    rank = better + 1
                    if rank > TOP or same > TOP:
                        continue
                    if abs(v - mid) < .2 * mid or (share and abs(v - mid) < 5):   # not really standing out
                        continue
                    text = (t1 if rank == 1 and same == 1 else t3).replace('{where}', where[scope](k))
                    found[k].append({'text': text, 'field': field, 'end': end, 'scope': 'city' if scope == 'city' else 'peers', 'rank': rank, 'of': len(ks),
                                     'value': fmt(v), '_s': rank / len(ks)})

order = {f[0]: i for i, f in enumerate(FIELDS)}
n = 0
for k, fs in found.items():
    # Strongest first; one fact per figure (a city-wide place beats the same figure within the peers).
    # "Longest trip downtown" is true but a dull first thing to read: it leads only when nothing else stands out.
    fs.sort(key=lambda f: (f['_s'] * (3 if f['field'] == 'hub' and f['end'] == 'high' else 1), order[f['field']]))
    seen, keep = set(), []
    for f in fs:
        if f['field'] in seen: continue
        seen.add(f['field']); f.pop('_s'); keep.append(f)
        if len(keep) == KEEP: break
    if keep:
        prof[k]['facts'] = keep; n += 1
    else:
        prof[k].pop('facts', None)
json.dump(prof, open(PROF, 'w'), separators=(',', ':'))
print('facts:', city, n, 'of', len(prof), 'units have one;', 'examples:')
for k in list(prof)[:: max(1, len(prof) // 8)]:
    f = prof[k].get('facts')
    print('  ', prof[k]['name'], '->', f[0]['text'] + ' (' + f[0]['value'] + ')' if f else '(none)')

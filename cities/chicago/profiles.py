"""Community-area lenses from the American Community Survey (5-year estimates, Cook County tracts).
Inputs: raw/acs_tracts.json and raw/tracts.json (fetched by fetch_extra.py), raw/community_areas.geojson
Output: docs/chicago/data/ca_profiles.json  {community area number: {...figures and tiers...}}

Each Census tract is placed in the community area containing its internal point (Chicago's 77
community areas were drawn from tracts, so nearly all nest), and its counts are summed:
- Households by tenure (B25003), commuting mode (B08301), and the bracketed counts of owner home values
  (B25075) and cash rents (B25063). Medians are read from the summed brackets by linear interpolation,
  the standard way to get a median for an area made of several tracts.
Tiers follow Toronto's map so the two read alike:
Housing cost: median home value and median rent ranked against all 77; the two ranks are averaged,
  weighted by the area's share of owners and renters, then split into thirds.
Getting to work: share of commuters (people who don't work from home) who drive: mostly car 68%+,
  mixed 50-68%, mostly transit / walk / bike under 50%.
Renters and owners: share of households that rent: mostly owners under 35%, a mix 35-60%, mostly renters over 60%.

Card-only descriptions (no tiers, never ranked), from raw/acs_more.json (fetch_acs_more.py), read by label:
- Homes by building size (B25032, occupied homes, owners and renters together): detached houses; attached
  houses (one-unit attached: rowhouses and townhouses); 2 to 19 units (two-flats, three-flats, courtyard
  buildings); 20 or more units. Mobile homes and boats make up any gap. The housing-type lens shades
  community areas by one type's share.
- When it was built (B25036, occupied homes): 1939 or earlier, 1940-1979, 1980-1999, 2000 or later.
- Language spoken at home (C16001, everyone 5 and over): "English only", or the language a person speaks
  at home besides English, so the shares add up to 100%. Tracts only get 12 broad groups (Polish shares a
  group with Russian and other Slavic languages; Hindi, Urdu, Italian and Greek are among "other
  Indo-European"). "Other and unspecified languages" is left out.
"""
import json, os
from collections import Counter
from shapely.geometry import shape, Point

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data', 'ca_profiles.json')
from names import ca_name

acs = json.load(open(os.path.join(RAW, 'acs_tracts.json')))
pts = json.load(open(os.path.join(RAW, 'tracts.json')))
cas = [(int(f['properties']['area_numbe']), ca_name(f['properties']['community']), shape(f['geometry']).buffer(0))
       for f in json.load(open(os.path.join(RAW, 'community_areas.geojson')))['features']]

# Bracket lower edges (dollars), in table order.
VALUE = [0, 10e3, 15e3, 20e3, 25e3, 30e3, 35e3, 40e3, 50e3, 60e3, 70e3, 80e3, 90e3, 100e3, 125e3, 150e3, 175e3,
         200e3, 250e3, 300e3, 400e3, 500e3, 750e3, 1e6, 1.5e6, 2e6]                      # B25075_E002..E027
RENT = [0, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 900, 1000, 1250, 1500,
        2000, 2500, 3000, 3500]                                                          # B25063_E003..E026


def median(counts, edges):
    total = sum(counts)
    if not total: return None
    half, run = total / 2, 0
    for i, c in enumerate(counts):
        if run + c >= half:
            if i == len(edges) - 1: return edges[i]          # open-ended top bracket
            return edges[i] + (half - run) / c * (edges[i + 1] - edges[i])
        run += c


sums = {}
placed = Counter()
for geoid, t in acs['tracts'].items():
    p = pts.get(geoid)
    if not p: continue
    pt = Point(p)
    ca = next((n for n, _, g in cas if g.contains(pt)), None)
    if ca is None: continue
    placed[ca] += 1
    s = sums.setdefault(ca, Counter())
    for k, v in t.items():
        if v: s[k] += v

# The extra tables: summed per community area the same way, then read by their Census labels.
MORE = json.load(open(os.path.join(RAW, 'acs_more.json')))
msums = {}
for geoid, t in MORE['tracts'].items():
    p = pts.get(geoid)
    if not p: continue
    ca = next((n for n, _, g in cas if g.contains(Point(p))), None)
    if ca is None: continue
    s = msums.setdefault(ca, Counter())
    for k, x in t.items():
        if x: s[k] += x
LAB = {k: lab.split('!!') for k, lab in MORE['labels'].items()}
leaf = lambda k: LAB[k][-1].rstrip(':')


def vars_where(table, test):
    return [k for k in sorted(LAB) if k.startswith(table + '_') and test(LAB[k])]


UNITS = {'1, detached': 0, '1, attached': 1, '2': 2, '3 or 4': 2, '5 to 9': 2, '10 to 19': 2, '20 to 49': 3, '50 or more': 3}
UNIT_VARS = [(k, UNITS[leaf(k)]) for k in vars_where('B25032', lambda l: len(l) == 4 and l[-1] in UNITS)]
def band(year_label):
    y = int(year_label.split()[1]) if year_label.split()[1].isdigit() else 0   # "Built 1939 or earlier" -> 1939
    return 0 if y <= 1939 else 1 if y < 1980 else 2 if y < 2000 else 3
BUILT_VARS = [(k, band(leaf(k))) for k in vars_where('B25036', lambda l: len(l) == 4 and l[-1].startswith('Built '))]
LANG_VARS = vars_where('C16001', lambda l: len(l) == 3 and (l[-1].endswith(':') or l[-1] == 'Speak only English'))
LANG_NAME = {'Speak only English': 'English only', 'French, Haitian, or Cajun': 'French or Haitian Creole',
             'German or other West Germanic languages': 'German or other West Germanic',
             'Russian, Polish, or other Slavic languages': 'Polish, Russian or other Slavic',
             'Other Indo-European languages': 'Other Indo-European (e.g. Hindi, Urdu)',
             'Other Asian and Pacific Island languages': 'Other Asian or Pacific Island',
             'Chinese (incl. Mandarin, Cantonese)': 'Chinese', 'Tagalog (incl. Filipino)': 'Tagalog (Filipino)'}
assert len(UNIT_VARS) == 16 and len(BUILT_VARS) == 20 and len(LANG_VARS) >= 10, (len(UNIT_VARS), len(BUILT_VARS), len(LANG_VARS))


def shares(s, pairs, n):
    tot = sum(s[k] for k, _ in pairs)
    if not tot: return None
    out = [0] * n
    for k, i in pairs: out[i] += s[k]
    return [round(100 * x / tot) for x in out]


v = lambda s, tbl, n: s.get(f'{tbl}_E{n:03d}', 0)
data = {}
for n, name, _ in sorted(cas):
    s = sums[n]
    hh = v(s, 'B25003', 1)
    com = v(s, 'B08301', 1) - v(s, 'B08301', 21)
    value = median([v(s, 'B25075', i) for i in range(2, 28)], VALUE)
    rent = median([v(s, 'B25063', i) for i in range(3, 27)], RENT)
    data[str(n)] = {
        'name': name,
        'value': int(round(value, -4)) if value else None, 'rent': int(round(rent, -1)) if rent else None,
        'renterPct': round(100 * v(s, 'B25003', 3) / hh) if hh else None,
        'carPct': round(100 * v(s, 'B08301', 2) / com) if com else None,
        'transitPct': round(100 * v(s, 'B08301', 10) / com) if com else None,
        'walkBikePct': round(100 * (v(s, 'B08301', 18) + v(s, 'B08301', 19)) / com) if com else None,
    }
    m, d = msums.get(n, Counter()), data[str(n)]
    # Shares of all occupied homes (the denominator includes mobile homes and boats, as Toronto's includes movable dwellings).
    tot = v(m, 'B25032', 1)
    d['homes'] = [round(100 * x / tot) for x in [sum(m[k] for k, i in UNIT_VARS if i == j) for j in range(4)]] if tot else None
    d['built'] = shares(m, BUILT_VARS, 4)
    tot = v(m, 'C16001', 1)
    if tot:
        names = [(LANG_NAME.get(leaf(k), leaf(k)), m[k]) for k in LANG_VARS if m[k] and not leaf(k).startswith('Other and unspecified')]
        d['lang'] = [[nm, round(100 * x / tot)] for nm, x in sorted(names, key=lambda a: -a[1])[:5]]


def pct_rank(key):
    vals = sorted(d[key] for d in data.values() if d[key] is not None)
    return {k: (sum(x < d[key] for x in vals) + 0.5 * sum(x == d[key] for x in vals)) / len(vals)
            for k, d in data.items() if d[key] is not None}


rv, rr = pct_rank('value'), pct_rank('rent')
score = {k: (1 - d['renterPct'] / 100) * rv.get(k, rr.get(k, .5)) + (d['renterPct'] / 100) * rr.get(k, rv.get(k, .5)) for k, d in data.items()}
order = sorted(score, key=score.get)
for i, k in enumerate(order):
    data[k]['cost'] = 'lower' if i < len(order) / 3 else 'middle' if i < 2 * len(order) / 3 else 'higher'
for d in data.values():
    d['commute'] = 'car' if d['carPct'] >= 68 else 'mixed' if d['carPct'] >= 50 else 'transit'
    d['tenure'] = 'owners' if d['renterPct'] < 35 else 'mix' if d['renterPct'] <= 60 else 'renters'

json.dump(data, open(OUT, 'w'), separators=(',', ':'))
for k in ('24', '31', '8'):
    print('example', k, data[k]['name'], data[k]['homes'], data[k]['built'], data[k]['lang'])
print('languages ever in a top 3:', sorted({l[0] for d in data.values() for l in d.get('lang', [])[:3]}))
print('profiles:', len(data), 'community areas from', sum(placed.values()), 'tracts, ACS', acs['year'], ';',
      dict(Counter(d['cost'] for d in data.values())), dict(Counter(d['commute'] for d in data.values())),
      dict(Counter(d['tenure'] for d in data.values())))

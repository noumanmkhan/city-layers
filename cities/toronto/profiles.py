"""Neighbourhood lenses from the City's 2021 Neighbourhood Profiles (2021 Census, 158 neighbourhoods).
Input: raw/neighbourhood_profiles_2021.xlsx (fetched by fetch_profiles.py)
Output: docs/toronto/data/nbhd_profiles.json  {neighbourhood number: {...figures and tiers...}}

Three lenses, each a simple, labelled tier rather than a precise figure. The point is the feel
of a neighbourhood relative to the rest of Toronto, not a price list.

Housing cost: what households there pay, combining owners and renters. Each neighbourhood's median
  home value and median rent are ranked against all 158; the two ranks are averaged, weighted by
  its share of owners and renters, then split into thirds (lower / middle / higher).
Getting to work: share of commuters who drive (car, truck or van, as driver or passenger).
  Mostly car 68%+, mixed 50-68%, mostly transit / walk / bike under 50%.
Renters and owners: share of households that rent. Mostly owners under 35%, a mix 35-60%,
  mostly renters over 60%.

To Union by transit: if raw/transit_union.json is present (computed by fetch_transit_union.py in
  GitHub Actions), each neighbourhood also gets its typical weekday-morning transit time to Union
  Station, banded under 30, 30-45, 45-60 and over 60 minutes.

Card-only descriptions (no tiers, never ranked):
- Homes by type (occupied private dwellings by structural type): detached; semi and row (semi-detached,
  row, other single-attached); low-rise apartments (duplex flats and buildings under five storeys);
  towers (five or more storeys). Shares of all occupied dwellings, so movable dwellings make up any gap.
  The housing-type lens shades neighbourhoods by one type's share.
- When it was built (occupied dwellings by period of construction): 1960 or before, 1961-1980,
  1981-2000, 2001-2021.
- Language spoken most often at home (single responses), as shares of everyone in private households.
  Up to five languages are kept; the page shows three. People naming two or more languages equally
  (multiple responses) aren't split between them; their share is kept as langMulti for a note.

Caveats shown on the page: Census figures are from 2021; commuting was counted in May 2021,
during the pandemic, when transit use was unusually low everywhere."""
import json, os
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'neighbourhood_profiles_2021.xlsx')
OUT = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data', 'nbhd_profiles.json')

rows = list(openpyxl.load_workbook(SRC, read_only=True)['hd2021_census_profile'].iter_rows(values_only=True))
label_raw = {i: str(r[0]) for i, r in enumerate(rows)}
label = {i: label_raw[i].strip() for i in label_raw}


def find(text, after=0):
    """Row index of the first row at or after `after` whose label is exactly `text`."""
    for i in range(after, len(rows)):
        if label[i] == text:
            return i
    raise SystemExit('row not found: ' + text)


R = {}
R['num'] = find('Neighbourhood Number')
R['hh'] = find('Total - Private households by tenure - 25% sample data')
R['owner'] = find('Owner', R['hh']); R['renter'] = find('Renter', R['hh'])
R['value'] = find('Median value of dwellings ($)')
R['rent'] = find('Median monthly shelter costs for rented dwellings ($)')
R['commuters'] = find('Total - Main mode of commuting for the employed labour force aged 15 years and over with a usual place of work or no fixed workplace address - 25% sample data') \
    if any(label[i].startswith('Total - Main mode of commuting') and label[i].endswith('25% sample data') for i in label) else \
    next(i for i in label if label[i].startswith('Total - Main mode of commuting'))
R['car'] = find('Car, truck or van', R['commuters'])
R['transit'] = find('Public transit', R['commuters'])
R['walk'] = find('Walked', R['commuters'])
R['bike'] = find('Bicycle', R['commuters'])

# Housing type, period of construction and home language: row indices by label within each section.
def section(title, labels):
    top = find(title)
    return top, [find(l, top) for l in labels]

TYPE_T, TYPE_R = section('Total - Occupied private dwellings by structural type of dwelling - 25% sample data',
    ['Single-detached house', 'Semi-detached house', 'Row house', 'Other single-attached house',
     'Apartment or flat in a duplex', 'Apartment in a building that has fewer than five storeys',
     'Apartment in a building that has five or more storeys'])
TYPE_GROUPS = [[0], [1, 2, 3], [4, 5], [6]]            # detached, semi & row, low-rise, towers
BUILT_T, BUILT_R = section('Total - Occupied private dwellings by period of construction - 25% sample data',
    ['1960 or before', '1961 to 1980', '1981 to 1990', '1991 to 2000', '2001 to 2005', '2006 to 2010',
     '2011 to 2015', '2016 to 2021'])
BUILT_GROUPS = [[0], [1], [2, 3], [4, 5, 6, 7]]         # before 1961, 1961-80, 1981-2000, 2001-21
LANG_T = find('Total - Language spoken most often at home for the population in private households - 25% sample data')
LANG_SINGLE = find('Single responses', LANG_T)
LANG_MULTI = find('Multiple responses', LANG_T)
indent = lambda i: len(label_raw[i]) - len(label_raw[i].lstrip(' '))
# Leaf languages: rows between "Single responses" and "Multiple responses" with nothing nested under them.
LANG_LEAVES = [i for i in range(LANG_SINGLE + 1, LANG_MULTI) if indent(i + 1) <= indent(i)]
LANG_NAME = {'Punjabi (Panjabi)': 'Punjabi', 'Tagalog (Pilipino, Filipino)': 'Tagalog (Filipino)', 'Yue (Cantonese)': 'Cantonese', 'Iranian Persian': 'Persian (Farsi)'}

num = lambda v: v if isinstance(v, (int, float)) else None
cols = range(1, len(rows[0]))
data = {}
for c in cols:
    g = lambda k: num(rows[R[k]][c])
    hh, com = g('hh'), g('commuters')
    data[str(g('num'))] = {
        'name': rows[0][c],
        'value': g('value'), 'rent': g('rent'),
        'renterPct': round(100 * g('renter') / hh) if hh else None,
        'carPct': round(100 * g('car') / com) if com else None,
        'transitPct': round(100 * g('transit') / com) if com else None,
        'walkBikePct': round(100 * (g('walk') + g('bike')) / com) if com else None,
    }
    d = data[str(g('num'))]
    v = lambda i: num(rows[i][c]) or 0
    tot = v(TYPE_T)
    d['homes'] = [round(100 * sum(v(TYPE_R[j]) for j in grp) / tot) for grp in TYPE_GROUPS] if tot else None
    tot = v(BUILT_T)
    d['built'] = [round(100 * sum(v(BUILT_R[j]) for j in grp) / tot) for grp in BUILT_GROUPS] if tot else None
    tot = v(LANG_T)
    if tot:
        langs = sorted(((LANG_NAME.get(label[i], label[i]), v(i)) for i in LANG_LEAVES if v(i)), key=lambda x: -x[1])[:5]
        d['lang'] = [[n, round(100 * k / tot)] for n, k in langs]
        d['langMulti'] = round(100 * v(LANG_MULTI) / tot)


def pct_rank(key):
    vals = sorted(d[key] for d in data.values() if d[key] is not None)
    return {k: (sum(v < d[key] for v in vals) + 0.5 * sum(v == d[key] for v in vals)) / len(vals)
            for k, d in data.items() if d[key] is not None}


rv, rr = pct_rank('value'), pct_rank('rent')
score = {k: (1 - d['renterPct'] / 100) * rv[k] + (d['renterPct'] / 100) * rr[k] for k, d in data.items()}
order = sorted(score, key=score.get)
n = len(order)
for i, k in enumerate(order):
    data[k]['cost'] = 'lower' if i < n / 3 else 'middle' if i < 2 * n / 3 else 'higher'
for d in data.values():
    d['commute'] = 'car' if d['carPct'] >= 68 else 'mixed' if d['carPct'] >= 50 else 'transit'
    d['tenure'] = 'owners' if d['renterPct'] < 35 else 'mix' if d['renterPct'] <= 60 else 'renters'

TU = os.path.join(HERE, 'raw', 'transit_union.json')
if os.path.exists(TU):
    tu = json.load(open(TU))['neighbourhoods']
    for k, d in data.items():
        m = (tu.get(k) or {}).get('minutes')
        d['union'] = m
        d['unionBand'] = None if m is None else 'under30' if m < 30 else '30to45' if m < 45 else '45to60' if m <= 60 else 'over60'

json.dump(data, open(OUT, 'w'), separators=(',', ':'))
from collections import Counter
ex = data['71']
print('example #71:', ex['name'], ex['homes'], ex['built'], ex['lang'], ex['langMulti'])
print('languages ever in a top 3:', sorted({l[0] for d in data.values() for l in d['lang'][:3]}))
print('profiles:', len(data), 'neighbourhoods;',
      dict(Counter(d['cost'] for d in data.values())), dict(Counter(d['commute'] for d in data.values())),
      dict(Counter(d['tenure'] for d in data.values())), dict(Counter(d.get('unionBand') for d in data.values())))

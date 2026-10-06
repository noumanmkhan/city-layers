"""Neighbourhood lenses from the City's 2021 Neighbourhood Profiles (2021 Census, 158 neighbourhoods).
Input: raw/neighbourhood_profiles_2021.xlsx (fetched by fetch_profiles.py)
Output: ../docs/toronto/data/nbhd_profiles.json  {neighbourhood number: {...figures and tiers...}}

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

Caveats shown on the page: Census figures are from 2021; commuting was counted in May 2021,
during the pandemic, when transit use was unusually low everywhere."""
import json, os
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'neighbourhood_profiles_2021.xlsx')
OUT = os.path.join(HERE, '..', 'docs', 'toronto', 'data', 'nbhd_profiles.json')

rows = list(openpyxl.load_workbook(SRC, read_only=True)['hd2021_census_profile'].iter_rows(values_only=True))
label = {i: str(r[0]).strip() for i, r in enumerate(rows)}


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
print('profiles:', len(data), 'neighbourhoods;',
      dict(Counter(d['cost'] for d in data.values())), dict(Counter(d['commute'] for d in data.values())),
      dict(Counter(d['tenure'] for d in data.values())), dict(Counter(d.get('unionBand') for d in data.values())))

"""Assign each of the City's 158 neighbourhoods to a broad area.

The five Old Toronto areas (Downtown, Midtown, Uptown, West End, East End) are an
informal split, not an official boundary. It is defined once on the City's older
140-neighbourhood map (by neighbourhood number, below) and carried over to the
current 158 neighbourhoods by largest overlap.
Output: raw/nbhd_region.json  {neighbourhood code: area}
"""
import json, os
from shapely.geometry import shape

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')

EAST_END = {62, 63, 64, 65, 66, 67, 68, 69, 70}
DOWNTOWN = {71, 72, 73, 74, 75, 76, 77, 78, 79}
WEST_END = set(range(80, 95))
UPTOWN = {100, 102, 103, 105}
MIDTOWN = {95, 96, 97, 98, 99, 101, 104}


def area_of(n):
    if 1 <= n <= 20: return 'Etobicoke'
    if 21 <= n <= 53: return 'North York'
    if 54 <= n <= 61: return 'East York'
    if 106 <= n <= 115: return 'York'
    if 116 <= n <= 140: return 'Scarborough'
    for name, s in [('East End', EAST_END), ('Downtown', DOWNTOWN), ('West End', WEST_END),
                    ('Uptown', UPTOWN), ('Midtown', MIDTOWN)]:
        if n in s: return name
    raise ValueError(n)


old = json.load(open(os.path.join(RAW, 'nbhd140.geojson')))
olds = [(area_of(int(f['properties']['AREA_S_CD'])), shape(f['geometry']).buffer(0)) for f in old['features']]
new = json.load(open(os.path.join(RAW, 'nbhd158.geojson')))
out = {}
for f in new['features']:
    g = shape(f['geometry']).buffer(0)
    best = max(olds, key=lambda o: o[1].intersection(g).area)
    out[f['properties']['AREA_SHORT_CODE']] = best[0]
json.dump(out, open(os.path.join(RAW, 'nbhd_region.json'), 'w'), indent=0)
print('regions:', len(out), 'neighbourhoods assigned')

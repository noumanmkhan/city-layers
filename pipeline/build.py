"""Build web-ready layer files for the Toronto layers map.
Inputs in raw/, outputs in site/data/. Polygons are simplified later by mapshaper."""
import json, os, re, sys, subprocess
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import unary_union, linemerge, polylabel
sys.path.insert(0, os.path.dirname(__file__))
from cultural import CULTURAL

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'raw') + '/'; OUT = os.path.join(HERE, '..', 'docs', 'data') + '/'; TMP = os.path.join(HERE, 'tmp') + '/'
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
ZIP = R


def fc(feats): return {'type': 'FeatureCollection', 'features': feats}


def feat(geom, props): return {'type': 'Feature', 'properties': props, 'geometry': mapping(geom)}


def label_pt(g):
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda p: p.area)
    try:
        p = polylabel(g, tolerance=0.0002)
    except Exception:
        p = g.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def dump(name, obj):
    json.dump(obj, open(TMP + name + '.geojson', 'w'), separators=(',', ':'))


def title(s):
    s = s.title().replace("'S", "'s")
    return s


bundle = json.load(open(R + 'city_bundle1.json'))

# Land only: the City's "Toronto Land And Water Area" layer (2xxx = land, incl. each island;
# 1xxx = Toronto Harbour, Grenadier Pond, etc.). Admin boundaries run out into the lake and
# across the harbour, so every polygon layer is clipped to this.
LAND = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(R + 'landwater.geojson'))['features']
                    if f['properties']['AREA_SHORT_CODE'].startswith('2')]).buffer(0)


def land(g):
    g = g.intersection(LAND)
    if g.geom_type == 'GeometryCollection':
        g = unary_union([x for x in g.geoms if x.geom_type in ('Polygon', 'MultiPolygon')])
    return g


# ---------- City outline + former municipalities ----------
FM_NAMES = {'TORONTO': 'Old Toronto', 'YORK': 'York', 'NORTH YORK': 'North York',
            'EAST YORK': 'East York', 'ETOBICOKE': 'Etobicoke', 'SCARBOROUGH': 'Scarborough'}
fm = {}
for f in bundle['formermun']['features']:
    fm[FM_NAMES[f['properties']['AREA_NAME']]] = land(shape(f['geometry']).buffer(0))
CITY = unary_union(list(fm.values())).buffer(0.00005).buffer(-0.00005)
FM_INFO = {
    'Old Toronto': 'The original City of Toronto, incorporated in 1834.',
    'York': 'Former City of York (a township until 1967, a borough until 1983).',
    'North York': 'Former City of North York, incorporated as a city in 1979.',
    'East York': 'Former Borough of East York, the only borough until amalgamation.',
    'Etobicoke': 'Former City of Etobicoke, incorporated as a city in 1983.',
    'Scarborough': 'Former City of Scarborough, incorporated as a city in 1983.',
}
dump('boroughs', fc([feat(g, {'name': n, 'info': FM_INFO[n], 'lp': label_pt(g)}) for n, g in fm.items()]))

# ---------- Neighbourhoods (158) ----------
nb = json.load(open(R + 'nbhd158.geojson'))
region_of = json.load(open(R + 'nbhd_region.json'))
nb_feats, nb_geoms = [], []
for f in nb['features']:
    p = f['properties']; g = land(shape(f['geometry']).buffer(0))
    code = p['AREA_SHORT_CODE']
    nb_geoms.append((code, g))
    nb_feats.append(feat(g, {'name': p['AREA_NAME'], 'code': int(code), 'lp': label_pt(g),
                             'nia': p.get('CLASSIFICATION_CODE')}))
dump('neighbourhoods', fc(nb_feats))

# ---------- Areas: Downtown / Midtown / Uptown / West End / East End ----------
AREAS = ['Downtown', 'Midtown', 'Uptown', 'West End', 'East End']
AREA_INFO = {
    'Downtown': 'The central core: Financial District, waterfront and the dense grid south of Bloor.',
    'Midtown': 'Bloor to roughly Eglinton: the Annex, Yonge & St. Clair, Davisville.',
    'Uptown': 'Around and north of Yonge & Eglinton up to the 401.',
    'West End': 'Old Toronto west of Bathurst: Parkdale, the Junction, Roncesvalles, Little Italy.',
    'East End': 'Old Toronto east of the Don: Riverdale, Leslieville, the Danforth, the Beaches.',
}
area_geom = {}
for code, g in nb_geoms:
    a = region_of[code]
    if a in AREAS:
        area_geom.setdefault(a, []).append(g)
oldt = fm['Old Toronto']
af = []
for a in AREAS:
    g = unary_union(area_geom[a]).buffer(0.0001).buffer(-0.0001).intersection(oldt.buffer(0.0005))
    af.append(feat(g, {'name': a, 'info': AREA_INFO[a], 'lp': label_pt(g)}))
dump('areas', fc(af))

# ---------- Wards (25) = provincial ridings ----------
prov = json.load(open(R + 'prov2015.geojson'))
prov_g = [(f['properties']['name'], shape(f['geometry']).buffer(0)) for f in prov['features']]
wf = []
for f in bundle['wards']['features']:
    p = f['properties']; g = land(shape(f['geometry']).buffer(0))
    best = max(prov_g, key=lambda t: t[1].intersection(g).area)
    wf.append(feat(g, {'num': int(p['AREA_SHORT_CODE']), 'name': p['AREA_NAME'],
                       'prov': best[0], 'lp': label_pt(g)}))
wf.sort(key=lambda x: x['properties']['num'])
dump('wards', fc(wf))

# ---------- Federal ridings (2023 Representation Order) ----------
fed = json.load(open(R + 'fed2023.geojson'))
ff = []
for f in fed['features']:
    g = shape(f['geometry']).buffer(0)
    if g.intersection(CITY).area / g.area < 0.5:  # keep ridings mostly inside the city limits
        continue
    inside = land(g)
    ff.append(feat(inside, {'name': f['properties']['name'], 'lp': label_pt(inside)}))
ff.sort(key=lambda x: x['properties']['name'])
dump('federal', fc(ff))
print('federal ridings', len(ff))

# ---------- BIAs (85) ----------
bia = json.load(open(R + 'bia.geojson'))
bf = []
for f in bia['features']:
    p = f['properties']; g = land(shape(f['geometry']).buffer(0))
    yr = (p.get('YearCreated') or '')[:4]
    bf.append(feat(g, {'name': p['AREA_NAME'], 'since': yr, 'link': p.get('Link') or '', 'lp': label_pt(g)}))
dump('bia', fc(bf))

# ---------- Highways ----------
def route_of(n):
    n0 = n
    if 'Ramp' in n:
        return None
    n = n.lower()
    rules = [('401', r'(highway 401|^401 [cx] [ew] 401|^dvp 401$)'), ('400', r'highway 400'), ('404', r'highway 404'),
             ('409', r'highway 409'), ('427', r'(highway 427|^427 [cx] [ns] 427)'), ('QEW', r'^qew'),
             ('2A', r'highway 2a'), ('DVP', r'don valley parkway'),
             ('Gardiner', r'^(f g gardiner|gardiner [cx] [ew] gardiner|gardiner x w gardiner)'), ('Allen', r'allen rd')]
    for k, rx in rules:
        if re.search(rx, n):
            return k
    return None


ROUTES = {'401': ('Highway 401', 'provincial'), '400': ('Highway 400', 'provincial'),
          '404': ('Highway 404', 'provincial'), '409': ('Highway 409', 'provincial'),
          '427': ('Highway 427', 'provincial'), 'QEW': ('Queen Elizabeth Way', 'provincial'),
          '2A': ('Highway 2A', 'city'), 'DVP': ('Don Valley Parkway', 'city'),
          'Gardiner': ('Gardiner Expressway', 'city'), 'Allen': ('Allen Road', 'city')}
segs = {}
for key in ('provexp', 'cityexp'):
    for f in bundle[key]['features']:
        r = route_of(f['properties']['LINEAR_NAME_FULL'] or '')
        if r:
            segs.setdefault(r, []).append(shape(f['geometry']))
hf = []
for r, gs in segs.items():
    m = linemerge(unary_union(gs))
    hf.append(feat(m, {'route': r, 'name': ROUTES[r][0], 'kind': ROUTES[r][1]}))
dump('highways', fc(hf))
print('highways', sorted(segs))

# ---------- Cultural names ----------
cf = [{'type': 'Feature', 'properties': {'name': n, 'kind': k},
       'geometry': {'type': 'Point', 'coordinates': [x, y]}} for n, x, y, k in CULTURAL]
json.dump(fc(cf), open(OUT + 'cultural.geojson', 'w'), separators=(',', ':'))

# ---------- Base: city land, neighbouring municipalities ----------
NEIGH = {'1954127': 'Mississauga', '2407358': 'Brampton', '324212': 'Vaughan', '324213': 'Markham',
         '2407259': 'Richmond Hill', '2408836': 'Pickering', '2407500': 'Oakville', '2408837': 'Ajax'}
lake = None
for f in json.load(open(R + 'lake_ontario.geojson'))['features']:
    if f['properties'].get('name') == 'Lake Ontario':
        lake = shape(f['geometry']).buffer(0)
FRAME = box(-79.85, 43.45, -78.95, 44.0)
base = [feat(LAND, {'kind': 'city', 'name': 'City of Toronto'})]
for fid, name in NEIGH.items():
    j = json.load(open(R + f'neighbours/{fid}.geojson'))
    g = shape(j['geometry']).buffer(0).difference(lake).difference(CITY.buffer(0.0003)).intersection(FRAME)
    if not g.is_empty:
        base.append(feat(g, {'kind': 'neighbour', 'name': name, 'lp': label_pt(g)}))
dump('base', fc(base))
print('done')

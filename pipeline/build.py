"""Build web-ready layer files for the Toronto layers map.
Inputs in raw/, outputs in site/data/. Polygons are simplified later by mapshaper."""
import json, os, re, sys, subprocess
from shapely.geometry import shape, mapping, Point, box, LineString, MultiLineString
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
# Ridings renamed by Parliament after the 2023 boundaries were drawn (the House of Commons uses the new names).
RENAMED = {'York Centre': 'North York'}
ff = []
for f in fed['features']:
    g = shape(f['geometry']).buffer(0)
    if g.intersection(CITY).area / g.area < 0.5:  # keep ridings mostly inside the city limits
        continue
    inside = land(g)
    ff.append(feat(inside, {'name': RENAMED.get(f['properties']['name'], f['properties']['name']), 'lp': label_pt(inside)}))
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
    low = n.lower()
    # Highway 427's last stretch into the QEW/Gardiner interchange is coded as 427<->QEW/Gardiner
    # connector "ramps"; keep those so the 427 meets the QEW instead of stopping at Browns Line.
    if 'ramp' in low and '427' in low and ('qew' in low or 'gardiner' in low) \
            and not any(s in low for s in ('browns', 'evans', 'queensway', 'sherway', 'west mall')):
        return '427'
    if 'Ramp' in n:
        return None
    n = low
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

# ---------- Base: Toronto, the rest of the GTA, and land beyond ----------
# GTA = Toronto + the regional municipalities of Halton, Peel, York and Durham (OpenStreetMap boundaries).
GTA = {
    '2407500': ('Oakville', 'Halton'), '2407513': ('Burlington', 'Halton'), '2414122': ('Milton', 'Halton'),
    '2414222': ('Halton Hills', 'Halton'),
    '1954127': ('Mississauga', 'Peel'), '2407358': ('Brampton', 'Peel'), '4198908': ('Caledon', 'Peel'),
    '324212': ('Vaughan', 'York'), '324213': ('Markham', 'York'), '2407259': ('Richmond Hill', 'York'),
    '2407406': ('Newmarket', 'York'), '2401094': ('Aurora', 'York'), '2407380': ('King', 'York'),
    '2416081': ('Whitchurch-Stouffville', 'York'), '2408845': ('East Gwillimbury', 'York'), '2408844': ('Georgina', 'York'),
    '2408836': ('Pickering', 'Durham'), '2408837': ('Ajax', 'Durham'), '2408838': ('Whitby', 'Durham'),
    '333748': ('Oshawa', 'Durham'), '2408839': ('Clarington', 'Durham'), '2408842': ('Uxbridge', 'Durham'),
    '2408840': ('Scugog', 'Durham'), '2408841': ('Brock', 'Durham'),
}
WATER = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(R + 'lakes.geojson'))['features']])
FRAME = box(-82.5, 41.5, -75.5, 46.5)  # far beyond the map's pan limits, so no edge ever shows
base = [feat(LAND, {'kind': 'city', 'name': 'City of Toronto'})]
munis = []
for fid, (name, region) in GTA.items():
    g = shape(json.load(open(R + f'neighbours/{fid}.geojson'))['geometry']).buffer(0)
    g = g.difference(WATER).difference(CITY.buffer(0.0003))
    if g.geom_type == 'MultiPolygon':  # drop slivers left in the lake
        big = max(p.area for p in g.geoms)
        g = unary_union([p for p in g.geoms if p.area > big * 0.002])
    munis.append(g)
    base.append(feat(g, {'kind': 'neighbour', 'name': name, 'region': region, 'lp': label_pt(g)}))
# Land outside the GTA (Hamilton, Simcoe County, Kawartha Lakes...) as plain land so it isn't drawn as water.
outside = FRAME.difference(WATER).difference(unary_union(munis + [CITY]).buffer(0.0005))
base.insert(0, feat(outside, {'kind': 'outside', 'name': ''}))
# One label point per region, shown when zoomed out to the whole GTA (points, so written unsimplified).
regions = {}
for i, (fid, (name, region)) in enumerate(GTA.items()):
    regions.setdefault(region, []).append(munis[i])
rl = [{'type': 'Feature', 'properties': {'name': region + ' Region'},
       'geometry': {'type': 'Point', 'coordinates': label_pt(unary_union(gs).buffer(0.002))}}
      for region, gs in regions.items()]
json.dump(fc(rl), open(OUT + 'regions.geojson', 'w'), separators=(',', ':'))
dump('base', fc(base))

# ---------- GTA highways beyond the city limits (OpenStreetMap) ----------
# Inside Toronto the City's centrelines above are used. Here: the 400-series, QEW and 407 outside it,
# overlapping the city limit by ~50 m so the two sources join without a gap.
GTA_ROUTES = {'401': 'Highway 401', '407': 'Highway 407 (toll)', 'QEW': 'Queen Elizabeth Way', '403': 'Highway 403',
              '400': 'Highway 400', '427': 'Highway 427', '404': 'Highway 404', '410': 'Highway 410',
              '406': 'Highway 406', '409': 'Highway 409', '405': 'Highway 405', '412': 'Highway 412',
              '418': 'Highway 418', '420': 'Highway 420'}
osm = json.load(open(R + 'gta_motorways.json'))
inner = CITY.buffer(-0.0006)
gseg = {}
for w in osm['ways']:
    ref = (w['ref'] or '').split(';')[0].strip().replace('407 ETR', '407')
    if ref not in GTA_ROUTES or len(w['coords']) < 2:
        continue
    g = LineString(w['coords']).difference(inner)
    if not g.is_empty:
        gseg.setdefault(ref, []).append(g)
GTA_AREA = unary_union(munis + [CITY]).buffer(0.01)
gh, shields = [], []
for ref, gs in gseg.items():
    m = linemerge(unary_union(gs))
    parts = [p for p in getattr(m, 'geoms', [m]) if p.length * 80000 > 300]
    if not parts:
        continue
    m = MultiLineString(parts) if len(parts) > 1 else parts[0]
    gh.append(feat(m, {'route': ref, 'name': GTA_ROUTES[ref], 'toll': ref == '407'}))
    # Shields every ~20 km along each long stretch (lengths in degrees; ~80 km per degree east-west here)
    for p in parts:
        km = p.length * 80
        if km < 8:
            continue
        for d in [x for x in range(8, int(km) - 3, 35)] or [km / 2]:
            pt = p.interpolate(d / 80)
            if not GTA_AREA.contains(pt):  # highways are drawn beyond the GTA, shields only inside it
                continue
            # each direction of a divided highway is its own line; skip near-duplicates
            if any(s['properties']['route'] == ref and Point(s['geometry']['coordinates']).distance(pt) * 80 < 20 for s in shields):
                continue
            shields.append({'type': 'Feature', 'properties': {'route': ref, 'toll': ref == '407'},
                            'geometry': {'type': 'Point', 'coordinates': [round(pt.x, 5), round(pt.y, 5)]}})
dump('gta_highways', fc(gh))
json.dump(fc(shields), open(OUT + 'gta_shields.geojson', 'w'), separators=(',', ':'))
print('gta highways', sorted(gseg), len(shields), 'shields')

print('done')

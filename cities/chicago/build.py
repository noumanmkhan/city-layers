"""Build the Chicago map's layer files from cities/chicago/raw/ (see SOURCES.md).
Polygons and lines go to tmp/ and are simplified by mapshaper in run.sh; points go straight to
docs/chicago/data/. Output shapes match Toronto's, so the shared engine draws both."""
import json, math, os, re, sys
from collections import Counter, defaultdict
from shapely.geometry import shape, mapping, Point, LineString, MultiLineString, box
from shapely.ops import unary_union, linemerge, polylabel

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from names import (ca_name, SIDES, SIDE_INFO, KNOWN_AS_RENAME, KNOWN_AS_DROP, KNOWN_AS_EXTRA, known_as_kind,
                   street_name, MAJOR_STREETS, SSA_NAMES)

R = os.path.join(HERE, 'raw') + '/'
OUT = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data') + '/'
TMP = os.path.join(HERE, 'tmp') + '/'
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
load = lambda f: json.load(open(R + f))
fc = lambda feats: {'type': 'FeatureCollection', 'features': feats}
feat = lambda g, p: {'type': 'Feature', 'properties': p, 'geometry': mapping(g)}
KM = 83.0   # km per degree of longitude at Chicago's latitude (111 per degree of latitude)


def label_pt(g):
    if g.geom_type == 'MultiPolygon':
        g = max(g.geoms, key=lambda p: p.area)
    try:
        p = polylabel(g, tolerance=0.0002)
    except Exception:
        p = g.representative_point()
    return [round(p.x, 5), round(p.y, 5)]


def polys(g):
    """Keep only the polygon parts of a shapely result."""
    if g.geom_type in ('Polygon', 'MultiPolygon'): return g
    return unary_union([x for x in getattr(g, 'geoms', []) if x.geom_type in ('Polygon', 'MultiPolygon')])


def dump(name, feats):
    json.dump(fc(feats), open(TMP + name + '.geojson', 'w'), separators=(',', ':'))


def write(name, feats):
    json.dump(fc(feats), open(OUT + name + '.geojson', 'w'), separators=(',', ':'))


# ---------- The city, community areas and the nine sides ----------
# Water: Lake Michigan as surveyed by the Census Bureau (TIGER area hydrography tiles) along
# Chicagoland's shore, and Natural Earth's coarser lake farther away. The City's boundary takes in its
# harbours; clipping to land leaves them as water, like the lake around them.
FRAME = box(-91.5, 39.5, -84.0, 44.5)  # far beyond the map's pan limits, so no edge ever shows
SHORE = box(-87.95, 41.55, -86.80, 42.55)   # where the TIGER tiles were fetched (fetch_lake.py)
NE_LAKE = unary_union([shape(f['geometry']).buffer(0) for f in load('lakes.geojson')['features']])
if os.path.exists(R + 'lake_michigan.geojson'):
    WATER = unary_union([shape(f['geometry']).buffer(0) for f in load('lake_michigan.geojson')['features']] + [NE_LAKE.difference(SHORE)])
else:
    WATER = NE_LAKE
CITY = polys(unary_union([shape(f['geometry']).buffer(0) for f in load('city.geojson')['features']]).buffer(0).difference(WATER))
inside = lambda g: polys(g.intersection(CITY))

cas = {}
for f in load('community_areas.geojson')['features']:
    n = int(f['properties']['area_numbe'])
    cas[n] = (ca_name(f['properties']['community']), inside(shape(f['geometry']).buffer(0)))
dump('community_areas', [feat(g, {'name': name, 'code': n, 'lp': label_pt(g)}) for n, (name, g) in sorted(cas.items())])

sides = []
for side, nums in SIDES.items():
    g = unary_union([cas[n][1] for n in nums]).buffer(0.00002).buffer(-0.00002)
    sides.append(feat(g, {'name': side, 'info': SIDE_INFO[side], 'lp': label_pt(g)}))
dump('sides', sides)

# ---------- Known-as names: the City's Neighborhoods layer plus a few common names it lacks ----------
ca_names = {name for name, _ in cas.values()}
known = []
for f in load('neighborhoods.geojson')['features']:
    n = f['properties']['pri_neigh'].strip()
    n = KNOWN_AS_RENAME.get(n, n)
    if n in KNOWN_AS_DROP or ca_name(n) in ca_names:
        continue
    known.append((n, label_pt(inside(shape(f['geometry']).buffer(0)))))
known += [(n, [x, y]) for n, x, y in KNOWN_AS_EXTRA if n not in {k for k, _ in known}]
write('knownas', [{'type': 'Feature', 'properties': {'name': n, 'kind': known_as_kind(n)},
                   'geometry': {'type': 'Point', 'coordinates': p}} for n, p in sorted(known)])

# ---------- Representation: wards, Illinois House districts (two per Senate district), Congress, SSAs ----------
def districts(fname, key, props, min_share=0.002):
    out = []
    for f in load(fname)['features']:
        g = inside(shape(f['geometry']).buffer(0))
        if g.is_empty or g.area < CITY.area * min_share:   # drop slivers along the city limits
            continue
        p = props(f['properties'])
        p['lp'] = label_pt(g)
        out.append(feat(g, p))
    return sorted(out, key=lambda f: f['properties'][key])


dump('wards', districts('wards.geojson', 'num', lambda p: {'num': int(p['ward'])}))
# Illinois Senate district N is House districts 2N-1 and 2N, so one layer carries both.
dump('il_house', districts('il_house.geojson', 'num', lambda p: {'num': int(p['BASENAME']), 'senate': (int(p['BASENAME']) + 1) // 2}))
dump('congress', districts('congress.geojson', 'num', lambda p: {'num': int(p['BASENAME'])}))
ssa = []
for f in load('ssa.geojson')['features']:
    p = f['properties']
    if (p.get('status') or 'Active').lower() != 'active':
        continue
    g = inside(shape(f['geometry']).buffer(0))
    if g.is_empty: continue
    num = re.search(r'\d+', p.get('ref_no') or '')   # "SSA# 1-2015" is SSA 1 (re-established in 2015)
    ssa.append(feat(g, {'name': SSA_NAMES.get(p['name'].strip(), p['name'].strip()), 'num': int(num.group()) if num else None, 'lp': label_pt(g)}))
dump('ssa', sorted(ssa, key=lambda f: f['properties']['num'] or 0))

# ---------- Base: Chicago, the rest of Chicagoland, and land beyond ----------
# Chicagoland here = CMAP's seven Illinois counties plus Lake and Porter in northwest Indiana.
COUNTIES = {'17031': 'Cook', '17043': 'DuPage', '17089': 'Kane', '17093': 'Kendall', '17097': 'Lake', '17111': 'McHenry',
            '17197': 'Will', '18089': 'Lake', '18127': 'Porter'}
STATE = {'17': 'IL', '18': 'IN'}
counties = {}
for f in load('counties.geojson')['features']:
    gid = f['properties']['GEOID']
    if gid in COUNTIES:
        counties[gid] = shape(f['geometry']).buffer(0)
county_name = lambda gid: COUNTIES[gid] + ' County' + (', Indiana' if gid.startswith('18') else '')
base, munis = [feat(CITY, {'kind': 'city', 'name': 'City of Chicago'})], []
cutout = CITY.buffer(0.0003)


def neighbour(g, name, gid, rest=False):
    g = polys(g.difference(WATER).difference(cutout))
    if g.is_empty: return
    if g.geom_type == 'MultiPolygon':   # drop slivers left in the lake or along the city limits
        big = max(p.area for p in g.geoms)
        g = unary_union([p for p in g.geoms if p.area > big * 0.01])
    munis.append(g)
    p = {'kind': 'neighbour', 'name': name, 'region': county_name(gid), 'lp': label_pt(g)}
    if rest: p['rest'] = True   # unincorporated land: part of the region, but not a place to colour by town
    base.append(feat(g, p))


places = defaultdict(list)
for f in load('places.geojson')['features']:
    p = f['properties']
    if p['GEOID'] == '1714000' or not f.get('geometry'):   # Chicago itself
        continue
    g = shape(f['geometry']).buffer(0)
    home = next((gid for gid, cg in counties.items() if cg.contains(g.representative_point())), None)
    if home:
        places[home].append(g)
        neighbour(g, p['BASENAME'], home)
# Enclosed harbours (Burnham, Diversey...) are left out of both the City's boundary and the Census
# lake tiles. Pieces along the lakefront that no municipality claims are those harbours: leave them
# out of the base so they show as water.
all_places = unary_union([g for gs in places.values() for g in gs])
extra = box(-87.70, 41.64, -87.50, 42.03).difference(WATER).difference(CITY).difference(all_places.buffer(0.0003))
extra = [p for p in getattr(extra, 'geoms', [extra]) if p.geom_type == 'Polygon' and p.area > 2e-7 and p.centroid.x > -87.66]
print('lakefront harbours shown as water:', len(extra))
# What's left of each county is unincorporated land, still part of the region.
for gid, cg in counties.items():
    rest = cg.difference(unary_union(places[gid]).buffer(0.0002)) if places[gid] else cg
    neighbour(rest, 'Unincorporated ' + county_name(gid).replace(', Indiana', ''), gid, rest=True)
# Land beyond the region: the frame minus the lake and the region's counties (which hold every municipality
# and the city), so it's one simple shape rather than a lacework of gaps between suburbs.
outside = FRAME.difference(WATER).difference(unary_union(list(counties.values()) + [CITY]).buffer(0.0005))
base.insert(0, feat(outside, {'kind': 'outside', 'name': ''}))
dump('base', base)
write('regions', [{'type': 'Feature', 'properties': {'name': county_name(gid)},
                   'geometry': {'type': 'Point', 'coordinates': label_pt(cg.difference(CITY.buffer(0.01)))}}
                  for gid, cg in counties.items()])
REGION = unary_union(list(counties.values())).buffer(0.01)
# Real county lines for "Focus on a county" (engine/regions.py): clipped to land, since Cook and Lake run out into the lake.
dump('region_areas', [feat(polys(cg.difference(WATER)), {'region': county_name(gid)}) for gid, cg in counties.items()])

# ---------- Expressways: inside the city by name, across the region by route ----------
EXPRESSWAYS = {  # the names Chicagoans use, by OpenStreetMap name fragment
    'Kennedy': 'Kennedy Expressway', 'Edens': 'Edens Expressway', 'Dan Ryan': 'Dan Ryan Expressway',
    'Eisenhower': 'Eisenhower Expressway', 'Stevenson': 'Stevenson Expressway', 'Bishop Ford': 'Bishop Ford Freeway',
    'Skyway': 'Chicago Skyway', 'Tri-State': 'Tri-State Tollway', 'Jane Addams': 'Jane Addams Tollway',
    'Lake Shore': 'Lake Shore Drive', 'Calumet Expressway': 'Bishop Ford Freeway', 'Kingery': 'Kingery Expressway',
}


def refs_of(tags):
    out = []
    for r in (tags.get('ref') or '').split(';'):
        m = re.match(r'\s*I\s*-?\s*(\d+)', r)
        if m: out.append(m.group(1))
    return out


def way_line(w):
    return LineString([(round(p['lon'], 5), round(p['lat'], 5)) for p in w['geometry']])


ways = load('osm_expressways.json')['elements']
inner = CITY.buffer(-0.0006)
in_city, outer = defaultdict(list), defaultdict(list)
for w in ways:
    t = w['tags']
    if len(w.get('geometry', [])) < 2 or 'link' in t.get('highway', ''):
        continue
    line = way_line(w)
    name = t.get('name', '')
    refs = refs_of(t)
    lsd = 'Lake Shore' in name
    if not refs and not lsd:
        continue
    if '94' in refs and '41' in refs: refs.remove('41')   # I-41 just shares the Edens' route into Wisconsin
    route = 'LSD' if lsd else '/'.join(sorted(set(refs), key=int))
    if line.intersects(CITY):
        g = line.intersection(CITY.buffer(0.0005))
        if not g.is_empty:
            label = next((v for k, v in EXPRESSWAYS.items() if k in name), None) or ('Interstate ' + refs[0] if refs else name)
            in_city[(route, label)].append(g)
    if refs:
        g = line.difference(inner)
        if not g.is_empty:
            outer[refs[0]].append(g)


def lines_of(g):
    if g.geom_type == 'LineString': return [g]
    return [x for p in getattr(g, 'geoms', []) for x in lines_of(p)]


def merged(gs, min_km=0.3):
    u = lines_of(unary_union(gs))
    m = linemerge(u) if len(u) > 1 else (u[0] if u else LineString())
    parts = [p for p in getattr(m, 'geoms', [m]) if p.geom_type == 'LineString' and p.length * KM > min_km]
    return (MultiLineString(parts) if len(parts) > 1 else parts[0]) if parts else None


hw = []
by_name = defaultdict(list)
for (route, label), gs in in_city.items():
    by_name[label].append((route, gs))
for label, parts in by_name.items():   # one feature (and one shield) per expressway, under its main route
    m = merged([g for _, gs in parts for g in gs])
    if m is None: continue
    route = max(parts, key=lambda p: sum(g.length for g in p[1]))[0]
    hw.append(feat(m, {'route': route, 'name': label + ('' if route == 'LSD' else ' (I-' + route.replace('/', '/I-') + ')'),
                       'kind': 'city' if route == 'LSD' else 'provincial'}))
dump('highways', hw)

gh, shields = [], []
for ref, gs in outer.items():
    m = merged(gs, 1)
    if m is None: continue
    gh.append(feat(m, {'route': ref, 'name': 'Interstate ' + ref, 'toll': False}))
    for p in getattr(m, 'geoms', [m]):
        km = p.length * KM
        if km < 8: continue
        for d in [x for x in range(8, int(km) - 3, 35)] or [km / 2]:
            pt = p.interpolate(d / KM)
            if not REGION.contains(pt): continue
            if any(s['properties']['route'] == ref and Point(s['geometry']['coordinates']).distance(pt) * KM < 20 for s in shields):
                continue
            shields.append({'type': 'Feature', 'properties': {'route': ref, 'toll': False},
                            'geometry': {'type': 'Point', 'coordinates': [round(pt.x, 5), round(pt.y, 5)]}})
dump('region_highways', gh)
write('region_shields', shields)

# ---------- Main streets: OpenStreetMap primary and secondary roads inside the city ----------
segs = defaultdict(list)
for w in load('osm_arterials.json')['elements']:
    t = w['tags']
    if t['highway'] == 'tertiary' or len(w.get('geometry', [])) < 2:
        continue
    name = street_name(t['name'])
    if 'Lake Shore' in name or 'Wacker' in name and t.get('layer') == '-1':
        continue
    g = way_line(w).intersection(CITY)
    if g.is_empty: continue
    segs[(name, 'major' if name in MAJOR_STREETS else 'minor')].append(g)
streets = []
for (name, cls), gs in segs.items():
    m = merged(gs, 0.15)
    if m is None or m.length * KM < (0.8 if cls == 'major' else 1.5):
        continue
    streets.append(feat(m, {'name': name, 'cls': cls, 'len': round(m.length * 1000, 1)}))
streets.sort(key=lambda f: (f['properties']['cls'] != 'major', -f['properties']['len']))
dump('streets', streets)

# ---------- Metra ----------
METRA = {  # display name, outer terminus, sideways offset near downtown (lines sharing track fan out)
    'BNSF': ('BNSF', 'Aurora', 0), 'HC': ('Heritage Corridor', 'Joliet', -1), 'SWS': ('SouthWest Service', 'Manhattan', 1),
    'MD-N': ('Milwaukee District North', 'Fox Lake', -1), 'NCS': ('North Central Service', 'Antioch', 0),
    'MD-W': ('Milwaukee District West', 'Elgin', 1), 'UP-N': ('UP North', 'Kenosha', -1), 'UP-NW': ('UP Northwest', 'Harvard', 0),
    'UP-W': ('UP West', 'Elburn', 1), 'RI': ('Rock Island', 'Joliet', 0), 'ME': ('Metra Electric', 'University Park', 0),
}
ME_BRANCH = {'ME_OB_2': 'Blue Island', 'ME_OB_3': 'South Chicago', 'UP-NW_OB_2': 'McHenry'}
HUBS = {'CUS': 'Union Station', 'OTC': 'Ogilvie', 'LSS': 'LaSalle Street', 'MILLENNIUM': 'Millennium Station'}
metra = load('metra.json')
lines, lines_in = [], []
for rid, r in metra['routes'].items():
    name, to, off = METRA[rid]
    for sid, pts in r['shapes'].items():
        if '_OB_' not in sid or r['counts'].get(sid, 0) < 20:   # one outbound pattern per branch: it ends at the far terminus
            continue
        g = LineString(pts)
        p = {'line': rid, 'name': name, 'color': '#' + r['color'], 'offset': off, 'to': ME_BRANCH.get(sid, to)}
        lines.append(feat(g, p))
        gi = g.intersection(CITY.buffer(0.002))
        if not gi.is_empty:
            lines_in.append(feat(gi, p))
dump('metra_lines', lines)
dump('metra_lines_inner', lines_in)
write('metra_stations', [{'type': 'Feature', 'properties': {'name': HUBS.get(s['id'], s['name']), 'lines': [METRA[x][0] for x in s['routes']],
                                                            **({'hub': True} if s['id'] in HUBS else {})},
                          'geometry': {'type': 'Point', 'coordinates': [round(s['lon'], 5), round(s['lat'], 5)]}}
                         for s in metra['stops']])

# ---------- The 'L' ----------
CTA = [('red', 'Red'), ('blue', 'Blue'), ('brown', 'Brown'), ('green', 'Green'), ('orange', 'Orange'),
       ('pink', 'Pink'), ('purple', 'Purple'), ('yellow', 'Yellow')]
FLAG = {'red': 'red', 'blue': 'blue', 'brown': 'brn', 'green': 'g', 'orange': 'o', 'pink': 'pnk', 'purple': 'p', 'yellow': 'y'}
TERMINI = {'Howard', '95th/Dan Ryan', "O'Hare", 'Forest Park', 'Kimball', 'Harlem/Lake', 'Ashland/63rd', 'Cottage Grove',
           'Midway', '54th/Cermak', 'Linden', 'Dempster-Skokie'}
segs = defaultdict(list)
for f in load('cta_lines.geojson')['features']:
    for lid, word in CTA:
        if re.search(r'\b' + word + r'\b', f['properties']['lines']):
            segs[lid].append(shape(f['geometry']))
cta = []
for lid, word in CTA:   # Purple and Yellow last, so the busier lines draw on top where tracks are shared
    m = linemerge(unary_union(segs[lid]))
    cta.append(feat(m, {'line': lid, 'name': word + ' Line'}))
order = ['yellow', 'purple', 'pink', 'orange', 'brown', 'green', 'blue', 'red']
dump('cta_lines', sorted(cta, key=lambda f: order.index(f['properties']['line'])))
stations = {}
for s in load('cta_stops.json'):
    st = stations.setdefault(s['map_id'], {'name': s['station_name'], 'pts': [], 'lines': set()})
    st['pts'].append((float(s['location']['longitude']), float(s['location']['latitude'])))
    st['lines'] |= {word for lid, word in CTA if s.get(FLAG[lid])}
write('cta_stations', [{'type': 'Feature', 'properties': {'name': st['name'], 'lines': [w for _, w in CTA if w in st['lines']],
                                                          'terminus': st['name'] in TERMINI},
                        'geometry': {'type': 'Point', 'coordinates': [round(sum(p[0] for p in st['pts']) / len(st['pts']), 5),
                                                                      round(sum(p[1] for p in st['pts']) / len(st['pts']), 5)]}}
                       for st in stations.values()])

print('community areas', len(cas), '· sides', len(sides), '· known-as', len(known), '· SSAs', len(ssa),
      '· neighbours', len(munis), '· city expressways', sorted(k for k in in_city), '· region routes', sorted(outer),
      len(shields), 'shields · streets', len(streets), sum(f['properties']['cls'] == 'major' for f in streets), 'major',
      '· metra', len(lines), '· L stations', len(stations))

"""Build docs/<city>/data/construction.geojson: transit lines under construction and their stations,
from cities/<city>/raw/construction/osm.json (engine/fetch_construction.py) and the curated list in
cities/<city>/construction.json.

Lines: OSM ways whose name matches a project's 'match'. OSM usually maps each track separately, so a
way lying within 25 m of a longer one already kept is dropped (one dashed line per route), then the
rest are merged. Stations: OSM stations under construction near the line (stationsFromOsm), else the
point where the line crosses the street named in 'stations' (from docs/<city>/data/streets.geojson).

Line features carry the card facts (name, owner, opens, length, about, link, color); stations carry
part="station", the line id and the name.

Usage: python3 engine/construction.py <city>
"""
import json, math, os, re, sys
from shapely.geometry import LineString, MultiLineString, Point, mapping, shape
from shapely.ops import linemerge, unary_union, nearest_points
from shapely import affinity

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
city = sys.argv[1]
CDIR, DATA = os.path.join(ROOT, 'cities', city), os.path.join(ROOT, 'docs', city, 'data')
cfg = json.load(open(os.path.join(CDIR, 'construction.json')))
osm = json.load(open(os.path.join(CDIR, 'raw', 'construction', 'osm.json')))['elements']
streets = json.load(open(os.path.join(DATA, 'streets.geojson')))['features']

# Work in a local metric plane (equirectangular around the city), back to degrees at the end.
K = math.cos(math.radians(cfg.get('lat0', 43.7)))
fwd = lambda g: affinity.scale(g, xfact=111320 * K, yfact=110540, origin=(0, 0))
back = lambda g: affinity.scale(g, xfact=1 / (111320 * K), yfact=1 / 110540, origin=(0, 0))


def is_station(t):
    return 'station' in (t.get('construction'), t.get('construction:railway'), t.get('railway'), t.get('public_transport')) or \
        (t.get('public_transport') == 'construction' and t.get('name'))


def rnd(c):
    return [round(c[0], 5), round(c[1], 5)] if isinstance(c[0], (int, float)) else [rnd(x) for x in c]


feats, report = [], []
for L in cfg['lines']:
    rx = re.compile(L['match'])
    ways = [fwd(LineString(o['geom'])) for o in osm if o['type'] == 'way' and len(o.get('geom', [])) > 1
            and not is_station(o['tags']) and rx.search(o['tags'].get('name', ''))]
    if not ways:
        report.append(f"{L['name']}: no OSM geometry yet, left off")
        continue
    kept = []
    for w in sorted(ways, key=lambda g: -g.length):          # longest first; keep only what isn't already drawn
        if kept:
            w = w.difference(unary_union(kept).buffer(25))   # a twin track, or the overlapping part of one
            if w.is_empty or w.length < 60:
                continue
            w = linemerge(w) if w.geom_type == 'MultiLineString' else w
            w = max(w.geoms, key=lambda g: g.length) if hasattr(w, 'geoms') else w
            if w.length < 60:
                continue
        kept.append(w)
    u = unary_union(kept)
    merged = linemerge(u) if u.geom_type == 'MultiLineString' else u
    line_m = merged
    geom = back(merged)
    if geom.geom_type == 'LineString':
        coords = [rnd(list(geom.coords))]
    else:
        coords = [rnd(list(g.coords)) for g in geom.geoms]
    props = {k: L[k] for k in ('id', 'name', 'short', 'mode', 'color', 'owner', 'opens', 'length', 'about', 'link') if L.get(k)}
    feats.append({'type': 'Feature', 'properties': props,
                  'geometry': {'type': 'MultiLineString', 'coordinates': coords} if len(coords) > 1 else {'type': 'LineString', 'coordinates': coords[0]}})

    stns = []
    if L.get('stationsFromOsm'):
        seen = set()
        for o in osm:
            t = o['tags']
            if not is_station(t) or not t.get('name') or t['name'] in seen:
                continue
            pt = fwd(Point(o['lon'], o['lat'])) if o['type'] == 'node' else fwd(LineString(o['geom'])).centroid if len(o.get('geom', [])) > 1 else None
            if pt is None or pt.distance(line_m) > 250:
                continue
            seen.add(t['name'])
            stns.append((t['name'], pt))
    for s in L.get('stations', []):
        pt = None
        if s.get('cross'):
            st = unary_union([fwd(shape(f['geometry'])) for f in streets if f['properties']['name'] == s['cross']])
            x = line_m.intersection(st) if not st.is_empty else None
            if x is not None and not x.is_empty:
                pts = [x] if x.geom_type == 'Point' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'Point']
                pt = pts[0] if pts else x.centroid
            elif not st.is_empty and st.distance(line_m) < 400:   # street stops just short of the line
                pt = nearest_points(line_m, st)[0]
        if pt is None and s.get('at'):
            pt = nearest_points(line_m, fwd(Point(*s['at'])))[0]
        if pt is None:
            report.append(f"{L['name']}: station {s['name']} not placed (no crossing with {s.get('cross')})")
            continue
        stns.append((s['name'], pt))
    for name, pt in stns:
        p = back(pt)
        feats.append({'type': 'Feature', 'properties': {'part': 'station', 'id': L['id'], 'name': name},
                      'geometry': {'type': 'Point', 'coordinates': [round(p.x, 5), round(p.y, 5)]}})
    report.append(f"{L['name']}: {len(ways)} OSM ways -> {len(kept)} kept, {round(line_m.length / 1000, 1)} km, {len(stns)} stations")

json.dump({'type': 'FeatureCollection', 'features': feats}, open(os.path.join(DATA, 'construction.geojson'), 'w'),
          separators=(',', ':'), ensure_ascii=False)
print(city, 'construction:', *report, sep='\n  ')

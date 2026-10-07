"""Scouting run for a possible Hyderabad map: is the boundary data current and good enough?

Not a city build. It looks for each source the narrow Hyderabad scope needs and writes what it
found to scouting/hyderabad/out/ (report.json, a readable report.md, and any boundaries found as
GeoJSON). Run by .github/workflows/scout-hyderabad.yml, because the sandbox can't reach these hosts.

What it checks
  1. OpenStreetMap (Overpass): administrative boundaries around the city: the three corporations
     (GHMC, Cyberabad, Malkajgiri), Secunderabad Cantonment, districts, HMDA, the 300 new wards.
     Areas are compared with the published figures; edit dates show whether they were redrawn
     after the December 2025 / February 2026 changes.
  2. OpenStreetMap place names: are the names people use (Madhapur, Tolichowki...) mapped?
  3. OpenCity's CKAN catalogue and Telangana's open data portal: any ward, zone or corporation files.
  4. The corporations', the Cantonment Board's and HMDA's own websites: links to maps or GIS files.
  5. PIN code boundaries (Department of Posts on data.gov.in).
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(os.path.join(OUT, 'osm'), exist_ok=True)
UA = 'city-layers-scout/1.0 (+https://maps.noumankhan.ca; one-off data availability check)'
REPORT = {'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}

# Region: out to roughly the Regional Ring Road. Core: roughly the ORR.
REGION = (16.85, 77.55, 18.15, 79.45)   # south, west, north, east
CORE = (17.20, 78.20, 17.65, 78.75)

# Published figures to compare against (km²).
EXPECTED = {
    'Greater Hyderabad Municipal Corporation (since Feb 2026)': 689,
    'Cyberabad Municipal Corporation': 630,      # reported as 630 to 637
    'Malkajgiri Municipal Corporation': 727,     # reported as 727 to 734
    'GHMC before the Dec 2025 merger': 650,
    'GHMC Dec 2025 to Feb 2026 (merged, 300 wards)': 2053,
    'HMDA (2025 expansion)': 10472,
    'HMDA (before 2025)': 7257,
    'Hyderabad district': 217,
}


def log(*a):
    print(*a, flush=True)


def get(url, data=None, timeout=90, binary=False, headers=None):
    h = {'User-Agent': UA}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        info = {'status': r.status, 'url': r.geturl(), 'type': r.headers.get('Content-Type', ''),
                'length': len(body)}
        return (body if binary else body.decode('utf-8', 'replace')), info


def safe(name, fn):
    log(f'\n== {name}')
    try:
        return fn()
    except Exception as e:  # keep going: every section is independent
        log(f'   FAILED: {type(e).__name__}: {e}')
        REPORT.setdefault('errors', {})[name] = f'{type(e).__name__}: {e}'
        return None


# ---------------------------------------------------------------- OSM / Overpass
OVERPASS = ['https://overpass-api.de/api/interpreter',
            'https://overpass.kumi.systems/api/interpreter',
            'https://maps.mail.ru/osm/tools/overpass/api/interpreter']


def overpass(q):
    last = None
    for ep in OVERPASS:
        for attempt in range(2):
            try:
                body, _ = get(ep, data=urllib.parse.urlencode({'data': q}).encode(), timeout=300)
                return json.loads(body)
            except Exception as e:
                last = e
                log(f'   overpass {ep} attempt {attempt + 1}: {e}')
                time.sleep(20)
    raise last


def bbox(b):
    return ','.join(str(x) for x in b)


def km2(geom):
    from pyproj import Transformer
    from shapely.ops import transform
    t = Transformer.from_crs('EPSG:4326', 'EPSG:32644', always_xy=True).transform
    return round(transform(t, geom).area / 1e6, 1)


def rel_polygon(el):
    """Assemble a relation's outer/inner member ways (from `out geom`) into a polygon."""
    from shapely.geometry import LineString
    from shapely.ops import polygonize, unary_union
    outer, inner = [], []
    for m in el.get('members', []):
        if m.get('type') != 'way' or not m.get('geometry'):
            continue
        line = LineString([(p['lon'], p['lat']) for p in m['geometry']])
        (inner if m.get('role') == 'inner' else outer).append(line)
    if not outer:
        return None
    polys = list(polygonize(unary_union(outer)))
    if not polys:
        return None
    shape_ = unary_union(polys)
    holes = list(polygonize(unary_union(inner))) if inner else []
    if holes:
        shape_ = shape_.difference(unary_union(holes))
    return shape_


KEYWORDS = re.compile(r'hyderabad|cyberabad|malkajgiri|secunderabad|cantonment|ghmc|hmda|'
                      r'metropolitan|rangareddy|ranga reddy|medchal|sangareddy|ward|zone|circle|'
                      r'municipal|corporation', re.I)


def osm_boundaries():
    q = f"""[out:json][timeout:240];
    (rel["boundary"~"^(administrative|local_authority|political|postal_code|police|census)$"]({bbox(REGION)}););
    out tags meta;"""
    d = overpass(q)
    rels = d.get('elements', [])
    by_level = {}
    for r in rels:
        t = r.get('tags', {})
        k = f"{t.get('boundary')}/{t.get('admin_level', '-')}"
        by_level[k] = by_level.get(k, 0) + 1
    log('   relations by boundary/admin_level:', json.dumps(by_level, sort_keys=True))
    rows = []
    for r in rels:
        t = r.get('tags', {})
        name = t.get('name:en') or t.get('name', '')
        lvl = t.get('admin_level', '')
        interesting = (t.get('boundary') != 'administrative' or (lvl and lvl.isdigit() and int(lvl) <= 8)
                       or KEYWORDS.search(name or ''))
        if interesting:
            rows.append({'id': r['id'], 'name': name, 'name_local': t.get('name', ''),
                         'boundary': t.get('boundary'), 'admin_level': lvl,
                         'type_tags': {k: v for k, v in t.items() if k in (
                             'border_type', 'designation', 'ref', 'wikidata', 'start_date',
                             'source', 'note', 'postal_code', 'official_name')},
                         'last_edit': r.get('timestamp'), 'version': r.get('version')})
    rows.sort(key=lambda x: (x['boundary'] or '', x['admin_level'] or '99', x['name']))
    for x in rows:
        log(f"   {x['boundary']:<15} L{x['admin_level']:<3} {x['name'][:60]:<60} edited {x['last_edit']} v{x['version']} {x['type_tags']}")
    # Wards: names or tags that look like wards
    wards = [x for x in rows if re.search(r'\bward\b|division', x['name'], re.I)]
    REPORT['osm_boundaries'] = {'counts_by_boundary_level': by_level, 'listed': rows,
                                'ward_like_count': len(wards)}
    return rows


CANDIDATE = re.compile(r'cyberabad|malkajgiri|greater hyderabad|hyderabad municipal|ghmc|'
                       r'secunderabad|cantonment|hmda|metropolitan|^hyderabad$|hyderabad district|'
                       r'ranga ?reddy|medchal|sangareddy|corporation', re.I)


def osm_geometries(rows):
    if not rows:
        return
    from shapely.geometry import mapping
    picks = [x for x in rows if x['boundary'] in ('administrative', 'local_authority', 'police')
             and (CANDIDATE.search(x['name']) or CANDIDATE.search(x['name_local']))][:40]
    log(f'   fetching geometry for {len(picks)} candidates')
    results = []
    for x in picks:
        try:
            d = overpass(f'[out:json][timeout:240];rel({x["id"]});out geom;')
            el = d['elements'][0]
            g = rel_polygon(el)
            area = km2(g) if g is not None else None
            valid = bool(g is not None and g.is_valid)
            fn = re.sub(r'[^a-z0-9]+', '_', (x['name'] or str(x['id'])).lower()).strip('_')[:50]
            if g is not None:
                with open(os.path.join(OUT, 'osm', f'{x["id"]}_{fn}.geojson'), 'w') as f:
                    json.dump({'type': 'Feature', 'properties': {'osm_id': x['id'], **x},
                               'geometry': mapping(g.simplify(0.0002))}, f)
            res = {**x, 'area_km2': area, 'closed_polygon': valid}
            results.append(res)
            log(f"   {x['name'][:55]:<55} L{x['admin_level']:<3} area {area} km²  closed={valid}  edited {x['last_edit']}")
        except Exception as e:
            log(f"   {x['name']}: geometry failed: {e}")
        time.sleep(3)
    REPORT['osm_candidate_areas'] = results
    REPORT['expected_areas_km2'] = EXPECTED


NAMES = ['Madhapur', 'HITEC City', 'Hitech City', 'Gachibowli', 'Kondapur', 'Financial District',
         'Nanakramguda', 'Kokapet', 'Narsingi', 'Manikonda', 'Banjara Hills', 'Jubilee Hills',
         'Film Nagar', 'Tolichowki', 'Mehdipatnam', 'Masab Tank', 'Charminar', 'Falaknuma',
         'Abids', 'Nampally', 'Ameerpet', 'Begumpet', 'Secunderabad', 'Sindhi Colony', 'Tarnaka',
         'Kukatpally', 'Miyapur', 'Kompally', 'Uppal', 'LB Nagar', 'Dilsukhnagar', 'Malakpet',
         'Attapur', 'Shamshabad', 'Kothaguda', 'Somajiguda', 'Lakdikapul', 'Malakpet', 'Tellapur']


def osm_places():
    d = overpass(f"""[out:json][timeout:180];
    node["place"~"^(suburb|quarter|neighbourhood|locality|village|town|hamlet|city)$"]({bbox(CORE)});
    out tags;""")
    els = d.get('elements', [])
    counts = {}
    names = {}
    for e in els:
        t = e.get('tags', {})
        counts[t.get('place')] = counts.get(t.get('place'), 0) + 1
        for k in ('name', 'name:en', 'alt_name'):
            if t.get(k):
                names[t[k].lower()] = t.get('place')
    found = {n: names.get(n.lower()) for n in NAMES}
    missing = [n for n, v in found.items() if not v]
    log(f'   place nodes inside the ORR box: {counts}')
    log(f'   checklist found {len(NAMES) - len(missing)}/{len(NAMES)}; missing: {missing}')
    d2 = overpass(f"""[out:json][timeout:120];
    nwr["name"~"HITEC|Hitec|Hi-Tec|Hitech|Financial District|Cyber Towers|Cyberabad",i]({bbox(CORE)});
    out tags center;""")
    hitec = [{'type': e['type'], 'id': e['id'], 'name': e.get('tags', {}).get('name'),
              'tags': {k: v for k, v in e.get('tags', {}).items()
                       if k in ('place', 'landuse', 'boundary', 'amenity', 'building', 'office', 'railway', 'highway')}}
             for e in d2.get('elements', [])][:80]
    for h in hitec:
        log(f"   {h['type']} {h['id']} {h['name']} {h['tags']}")
    REPORT['osm_places'] = {'counts': counts, 'checklist': found, 'missing': missing,
                            'hitec_named_features': hitec}


# ---------------------------------------------------------------- catalogues
CAT_KW = re.compile(r'ward|zone|circle|boundar|delimit|corporation|cyberabad|malkajgiri|cantonment|'
                    r'hmda|metropolitan|pin ?code|postal|constituen|assembly|mandal|district', re.I)


def ckan_search(base, label, queries):
    seen = {}
    for q in queries:
        url = f'{base}/api/3/action/package_search?' + urllib.parse.urlencode(q)
        body, _ = get(url)
        res = json.loads(body)['result']
        for p in res['results']:
            seen[p['name']] = p
        time.sleep(1)
    rows = []
    for p in seen.values():
        text = ' '.join([p.get('title', ''), p.get('notes') or ''] + [r.get('name') or '' for r in p.get('resources', [])])
        if not CAT_KW.search(text):
            continue
        rows.append({'title': p.get('title'), 'name': p.get('name'),
                     'modified': p.get('metadata_modified'),
                     'resources': [{'name': r.get('name'), 'format': r.get('format'),
                                    'modified': r.get('last_modified') or r.get('created'),
                                    'url': r.get('url')} for r in p.get('resources', [])]})
    rows.sort(key=lambda x: x['modified'] or '', reverse=True)
    for r in rows:
        log(f"   {r['modified'][:10] if r['modified'] else '?'}  {r['title']}  [{', '.join(sorted({(x['format'] or '?') for x in r['resources']}))}]")
    REPORT[label] = {'total_packages_seen': len(seen), 'relevant': rows}


def opencity():
    ckan_search('https://data.opencity.in', 'opencity',
                [{'fq': 'groups:hyderabad', 'rows': 1000},
                 {'q': 'hyderabad ward', 'rows': 200}, {'q': 'cyberabad', 'rows': 200},
                 {'q': 'malkajgiri', 'rows': 200}, {'q': 'telangana boundary', 'rows': 200},
                 {'q': 'pincode', 'rows': 200}, {'q': 'telangana constituency', 'rows': 200}])


def telangana_portal():
    out = {}
    for base in ('https://data.telangana.gov.in', 'https://opendata.telangana.gov.in'):
        try:
            body, info = get(base + '/api/3/action/package_search?q=ward&rows=50', timeout=60)
            out[base] = {'ckan': True, 'status': info['status']}
            try:
                ckan_search(base, 'telangana_portal_' + base.split('//')[1].split('.')[0],
                            [{'q': q, 'rows': 200} for q in ('ward', 'GHMC', 'boundary', 'cyberabad',
                                                               'malkajgiri', 'HMDA', 'shapefile', 'kml')])
            except Exception as e:
                out[base]['search_error'] = str(e)
        except Exception as e:
            out[base] = {'ckan': False, 'error': str(e)}
            try:
                _, info = get(base, timeout=60)
                out[base]['homepage'] = info
            except Exception as e2:
                out[base]['homepage_error'] = str(e2)
        log(f'   {base}: {out[base]}')
    REPORT['telangana_portal_access'] = out


# ---------------------------------------------------------------- official websites
LINK_KW = re.compile(r'ward|zone|circle|map|kml|kmz|shp|geojson|gis|boundar|delimit|jurisdiction|'
                     r'master ?plan|extended|notification|gazette|g\.?o', re.I)
FILE_EXT = re.compile(r'\.(kml|kmz|geojson|json|zip|shp|pdf)(\?|$)', re.I)


def wikidata_sites():
    sites = {}
    for label in ('Cyberabad Municipal Corporation', 'Malkajgiri Municipal Corporation',
                  'Greater Hyderabad Municipal Corporation', 'Secunderabad Cantonment Board',
                  'Hyderabad Metropolitan Development Authority'):
        body, _ = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'wbsearchentities', 'search': label, 'language': 'en', 'format': 'json', 'limit': 3}))
        hits = json.loads(body).get('search', [])
        urls = []
        for h in hits:
            body, _ = get('https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode(
                {'action': 'wbgetentities', 'ids': h['id'], 'props': 'claims', 'format': 'json'}))
            claims = json.loads(body)['entities'][h['id']].get('claims', {})
            for c in claims.get('P856', []):
                v = c['mainsnak'].get('datavalue', {}).get('value')
                if v:
                    urls.append(v)
            # P402: OSM relation id, if Wikidata knows one
            for c in claims.get('P402', []):
                v = c['mainsnak'].get('datavalue', {}).get('value')
                if v:
                    urls.append(f'osm-relation:{v}')
        sites[label] = {'wikidata': [h['id'] for h in hits], 'links': urls}
        log(f'   {label}: {sites[label]}')
        time.sleep(1)
    REPORT['wikidata'] = sites
    return sites


def crawl_site(label, start_urls, max_pages=25):
    """Shallow crawl: homepages plus same-site pages whose link text or URL suggests maps or wards."""
    seen, queue, pages, files = set(), list(start_urls), [], []
    host_ok = {urllib.parse.urlparse(u).netloc.split(':')[0].removeprefix('www.') for u in start_urls}
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            body, info = get(url, timeout=45)
        except Exception as e:
            pages.append({'url': url, 'error': str(e)[:200]})
            continue
        pages.append({'url': info['url'], 'status': info['status'], 'type': info['type'][:40]})
        if 'html' not in info['type']:
            continue
        for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', body, re.I | re.S):
            href = urllib.parse.urljoin(info['url'], m.group(1).strip())
            text = re.sub(r'<[^>]+>|\s+', ' ', m.group(2)).strip()[:120]
            if not href.startswith('http'):
                continue
            if FILE_EXT.search(href) and LINK_KW.search(href + ' ' + text):
                files.append({'url': href, 'text': text})
            elif LINK_KW.search(href + ' ' + text):
                host = urllib.parse.urlparse(href).netloc.split(':')[0].removeprefix('www.')
                if host in host_ok and href not in seen:
                    queue.append(href)
        time.sleep(1)
    uniq = {f['url']: f for f in files}
    files = list(uniq.values())
    for p in pages:
        log(f"   page {p.get('status', 'ERR')} {p['url'][:110]} {p.get('error', '')[:80]}")
    for f in files[:120]:
        log(f"   file  {f['url'][:120]}  «{f['text'][:60]}»")
    REPORT.setdefault('websites', {})[label] = {'pages': pages, 'files': files[:300]}


def official_sites():
    sites = REPORT.get('wikidata') or {}
    def from_wd(label, fallback):
        urls = [u for u in sites.get(label, {}).get('links', []) if u.startswith('http')]
        return urls or fallback
    crawl_site('GHMC', from_wd('Greater Hyderabad Municipal Corporation', ['https://www.ghmc.gov.in/']))
    crawl_site('Cyberabad MC', from_wd('Cyberabad Municipal Corporation',
                                       ['https://cmc.telangana.gov.in/', 'https://www.cyberabadmc.gov.in/']), 15)
    crawl_site('Malkajgiri MC', from_wd('Malkajgiri Municipal Corporation',
                                        ['https://mmc.telangana.gov.in/', 'https://www.malkajgirimc.gov.in/']), 15)
    crawl_site('Secunderabad Cantonment Board', from_wd('Secunderabad Cantonment Board',
                                                        ['https://scb.cantt.gov.in/']), 12)
    crawl_site('HMDA', from_wd('Hyderabad Metropolitan Development Authority', ['https://www.hmda.gov.in/']))


# ---------------------------------------------------------------- PIN codes
def pincodes():
    out = {}
    for url in ('https://www.data.gov.in/resource/delivery-post-office-pincode-boundary',
                'https://www.data.gov.in/catalog/all-india-pincode-boundary-geo-json'):
        try:
            body, info = get(url, timeout=60)
            links = sorted(set(re.findall(r'https?://[^"\'\s<>]+?\.(?:geojson|json|zip)(?:\?[^"\'\s<>]*)?', body)))
            ids = sorted(set(re.findall(r'"(?:index_name|resource_id|nid|id)"\s*:\s*"?([0-9a-f-]{8,})', body)))[:20]
            out[url] = {'status': info['status'], 'length': info['length'], 'download_like_links': links[:30],
                        'ids_seen': ids, 'mentions_form': bool(re.search(r'captcha|purpose of download|name of user', body, re.I))}
        except Exception as e:
            out[url] = {'error': str(e)[:200]}
        log(f'   {url}: {out[url]}')
    # DataMeet's older NIC-derived PIN polygons, as a fallback reference
    try:
        body, info = get('https://api.github.com/repos/datameet/PincodeBoundary/contents/', timeout=60)
        out['datameet_PincodeBoundary'] = [{'path': x['path'], 'size': x.get('size')} for x in json.loads(body)]
    except Exception as e:
        out['datameet_PincodeBoundary'] = {'error': str(e)[:200]}
    log(f"   datameet: {out['datameet_PincodeBoundary']}")
    REPORT['pincodes'] = out


# ---------------------------------------------------------------- report
def write_report():
    with open(os.path.join(OUT, 'report.json'), 'w') as f:
        json.dump(REPORT, f, indent=1, ensure_ascii=False)
    L = [f"# Hyderabad scouting report\n\nRun {REPORT['run_at']} by `scouting/hyderabad/scout.py`. "
         "Raw details in `report.json`; boundaries found are in `osm/`.\n"]
    ob = REPORT.get('osm_boundaries')
    if ob:
        L.append('## OpenStreetMap boundary relations in the region\n')
        L.append('Counts by boundary/admin_level: ' + ', '.join(f'{k}: {v}' for k, v in sorted(ob['counts_by_boundary_level'].items())) + '\n')
        L.append(f"Ward-like names: {ob['ward_like_count']}\n")
    ca = REPORT.get('osm_candidate_areas')
    if ca:
        L.append('\n## Candidate boundaries: area and last edit\n')
        L.append('| Name | Level | km² | Closed | Last edit |\n|---|---|---|---|---|')
        for x in ca:
            L.append(f"| {x['name']} | {x['boundary']} {x['admin_level']} | {x['area_km2']} | {x['closed_polygon']} | {(x['last_edit'] or '')[:10]} |")
        L.append('\nPublished areas for comparison (km²): ' + '; '.join(f'{k} {v}' for k, v in EXPECTED.items()) + '\n')
    op = REPORT.get('osm_places')
    if op:
        L.append(f"\n## Place names\n\nPlace nodes inside the ORR box: {op['counts']}. Checklist missing: {', '.join(op['missing']) or 'none'}.\n")
    for key in [k for k in REPORT if k == 'opencity' or k.startswith('telangana_portal_')]:
        L.append(f'\n## Catalogue: {key}\n')
        for r in REPORT[key]['relevant'][:60]:
            fm = ', '.join(sorted({(x['format'] or '?') for x in r['resources']}))
            L.append(f"- {(r['modified'] or '?')[:10]} {r['title']} [{fm}]")
    for label, w in (REPORT.get('websites') or {}).items():
        ok = sum(1 for p in w['pages'] if 'status' in p)
        L.append(f"\n## Website: {label}\n\n{ok}/{len(w['pages'])} pages loaded; {len(w['files'])} map-like file links.\n")
        for fl in w['files'][:40]:
            L.append(f"- {fl['url']} «{fl['text']}»")
    if REPORT.get('pincodes'):
        L.append('\n## PIN codes\n\n```\n' + json.dumps(REPORT['pincodes'], indent=1)[:4000] + '\n```')
    if REPORT.get('errors'):
        L.append('\n## Sections that failed\n')
        for k, v in REPORT['errors'].items():
            L.append(f'- {k}: {v}')
    with open(os.path.join(OUT, 'report.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    rows = safe('OSM boundary relations', osm_boundaries)
    safe('OSM candidate geometries', lambda: osm_geometries(rows))
    safe('OSM place names', osm_places)
    safe('OpenCity catalogue', opencity)
    safe('Telangana open data portal', telangana_portal)
    safe('Wikidata websites', wikidata_sites)
    safe('Official websites', official_sites)
    safe('PIN codes', pincodes)
    write_report()
    log('\nwrote', os.path.join(OUT, 'report.md'))

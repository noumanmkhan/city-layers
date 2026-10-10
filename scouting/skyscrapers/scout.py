"""Scouting run for a Skyscrapers layer (Toronto and Chicago): how complete is the open data?

Not a city build. For each city it pulls three sources and saves them to scouting/skyscrapers/out/,
so coverage can be compared before deciding how to build the layer:

  1. Wikidata (CC0), the planned main source: every item with coordinates inside the city's box and a
     height of 140 m or more (a margin under the 150 m cut-off), with height method, floors, inception,
     opening date, state of use, use and type. Plus a second query for items typed as skyscrapers
     that have no height at all, to see what the first query misses.
  2. English Wikipedia's "List of tallest buildings in <city>" (CC BY-SA), the cross-check: every table
     on the page (completed, under construction, approved...) with its headers.
  3. OpenStreetMap (ODbL) via Overpass: buildings tagged height >= 140 or building:levels >= 40, with
     their wikidata tag, for placing points on footprints.

Run by .github/workflows/scout-skyscrapers.yml (the sandbox can't reach these hosts).
Nothing here feeds the map.
"""
import io, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
UA = 'city-layers-scout/1.0 (+https://maps.noumankhan.ca; one-off skyscraper data check)'

# west, south, east, north
CITIES = {
    'toronto': {'box': (-79.64, 43.58, -79.11, 43.86), 'wiki': 'List of tallest buildings in Toronto'},
    'chicago': {'box': (-87.95, 41.64, -87.52, 42.03), 'wiki': 'List of tallest buildings in Chicago'},
}
MIN_H = 140


def http(url, data=None, timeout=180, accept='application/json'):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept': accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def retry(fn, tries=5, label=''):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f'  {label} attempt {i + 1} failed: {e}')
            time.sleep(10 * (i + 1))
    return None


def sparql(q):
    body = urllib.parse.urlencode({'query': q, 'format': 'json'}).encode()
    raw = retry(lambda: http('https://query.wikidata.org/sparql', data=body,
                             accept='application/sparql-results+json'), label='wikidata')
    if raw is None:
        return None
    return [{k: v['value'] for k, v in b.items()} for b in json.loads(raw)['results']['bindings']]


def box_clause(box):
    w, s, e, n = box
    return f'''SERVICE wikibase:box {{
      ?item wdt:P625 ?coord .
      bd:serviceParam wikibase:cornerSouthWest "Point({w} {s})"^^geo:wktLiteral ;
                      wikibase:cornerNorthEast "Point({e} {n})"^^geo:wktLiteral .
    }}'''


def wikidata(box):
    # One row per combination; aggregated per item in Python.
    q = f'''SELECT ?item ?itemLabel ?coord ?h ?methodLabel ?floors ?inception ?opening ?stateLabel
                   ?useLabel ?typeLabel ?enwiki ?osmway WHERE {{
      {box_clause(box)}
      ?item p:P2048 ?hs . ?hs psn:P2048/wikibase:quantityAmount ?h .
      FILTER(?h >= {MIN_H})
      OPTIONAL {{ ?hs pq:P459 ?method }}
      OPTIONAL {{ ?item wdt:P1101 ?floors }}
      OPTIONAL {{ ?item wdt:P571 ?inception }}
      OPTIONAL {{ ?item wdt:P1619 ?opening }}
      OPTIONAL {{ ?item wdt:P5817 ?state }}
      OPTIONAL {{ ?item wdt:P366 ?use }}
      OPTIONAL {{ ?item wdt:P31 ?type }}
      OPTIONAL {{ ?item wdt:P10689 ?osmway }}
      OPTIONAL {{ ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}'''
    rows = sparql(q)
    if rows is None:
        return None
    items = {}
    for r in rows:
        it = items.setdefault(r['item'].rsplit('/', 1)[1], {
            'name': r.get('itemLabel'), 'coord': r.get('coord'), 'heights': set(), 'methods': set(),
            'floors': set(), 'inception': set(), 'opening': set(), 'state': set(), 'use': set(),
            'type': set(), 'enwiki': r.get('enwiki'), 'osm_way': r.get('osmway')})
        it['heights'].add(round(float(r['h']), 1))
        for k, src in (('methods', 'methodLabel'), ('floors', 'floors'), ('inception', 'inception'),
                       ('opening', 'opening'), ('state', 'stateLabel'), ('use', 'useLabel'),
                       ('type', 'typeLabel')):
            if r.get(src):
                it[k].add(r[src])
    for it in items.values():
        for k, v in it.items():
            if isinstance(v, set):
                it[k] = sorted(v, key=str)
    return items


def wikidata_no_height(box):
    q = f'''SELECT DISTINCT ?item ?itemLabel ?floors WHERE {{
      {box_clause(box)}
      ?item wdt:P31/wdt:P279* wd:Q11303 .
      FILTER NOT EXISTS {{ ?item wdt:P2048 ?x }}
      OPTIONAL {{ ?item wdt:P1101 ?floors }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}'''
    return sparql(q)


def wikipedia_tables(title):
    import pandas as pd
    url = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'parse', 'page': title, 'prop': 'text|revid', 'format': 'json', 'redirects': 1})
    raw = retry(lambda: http(url), label='wikipedia')
    if raw is None:
        return None
    p = json.loads(raw)['parse']
    html = p['text']['*']
    tables = []
    for t in pd.read_html(io.StringIO(html)):
        if isinstance(t.columns, pd.MultiIndex):
            t.columns = [' / '.join(dict.fromkeys(str(c) for c in col)) for col in t.columns]
        tables.append({'columns': [str(c) for c in t.columns], 'rows': len(t),
                       'records': json.loads(t.to_json(orient='records', force_ascii=False))})
    # Section headings, to tell which table is which.
    sec_url = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'parse', 'page': title, 'prop': 'sections', 'format': 'json', 'redirects': 1})
    secs = json.loads(retry(lambda: http(sec_url), label='sections') or b'{"parse":{"sections":[]}}')
    return {'title': p['title'], 'revid': p.get('revid'),
            'sections': [s['line'] for s in secs['parse']['sections']], 'tables': tables}


def osm(box):
    w, s, e, n = box
    q = f'''[out:json][timeout:180];
    (
      way["building"]["height"]({s},{w},{n},{e});
      relation["building"]["height"]({s},{w},{n},{e});
      way["building"]["building:levels"]({s},{w},{n},{e});
      relation["building"]["building:levels"]({s},{w},{n},{e});
    );
    out center tags;'''
    body = urllib.parse.urlencode({'data': q}).encode()
    for i in range(6):
        ep = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'][i % 2]
        try:
            els = json.loads(http(ep, data=body, timeout=240))['elements']
            break
        except Exception as e:
            print(f'  overpass attempt {i + 1} ({ep}) failed: {e}')
            time.sleep(20)
    else:
        return None

    def num(v):
        try:
            return float(str(v).replace('m', '').replace(',', '.').split(';')[0].strip())
        except ValueError:
            return None
    keep = []
    for el in els:
        t = el.get('tags', {})
        h, lv = num(t.get('height')), num(t.get('building:levels'))
        if (h and h >= MIN_H) or (lv and lv >= 40):
            c = el.get('center', {})
            keep.append({'osm': f"{el['type']}/{el['id']}", 'name': t.get('name'), 'height': h, 'levels': lv,
                         'building': t.get('building'), 'wikidata': t.get('wikidata'),
                         'start_date': t.get('start_date'), 'lat': c.get('lat'), 'lon': c.get('lon')})
    return keep


summary = {'run_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'min_height_m': MIN_H}
for city, cfg in CITIES.items():
    print('==', city)
    res = {}
    wd = wikidata(cfg['box']); res['wikidata'] = wd
    print('wikidata items >=', MIN_H, 'm:', None if wd is None else len(wd)); time.sleep(5)
    nh = wikidata_no_height(cfg['box']); res['wikidata_skyscrapers_without_height'] = nh
    print('wikidata skyscrapers without height:', None if nh is None else len(nh)); time.sleep(5)
    try:
        wp = wikipedia_tables(cfg['wiki'])
    except Exception as e:
        print('wikipedia parse failed:', e); wp = None
    res['wikipedia'] = wp
    if wp:
        print('wikipedia tables:', [(t['rows'], t['columns'][:6]) for t in wp['tables']])
    o = osm(cfg['box']); res['osm'] = o
    print('osm buildings:', None if o is None else len(o))
    json.dump(res, open(os.path.join(OUT, f'{city}.json'), 'w'), indent=1, ensure_ascii=False)
    summary[city] = {'wikidata': None if wd is None else len(wd),
                     'wikidata_no_height': None if nh is None else len(nh),
                     'wikipedia_tables': None if not wp else [t['rows'] for t in wp['tables']],
                     'osm': None if o is None else len(o)}
    time.sleep(10)

json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))

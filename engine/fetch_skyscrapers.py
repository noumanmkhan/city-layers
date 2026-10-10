"""Fetch a city's tallest-buildings list from English Wikipedia into cities/<city>/raw/skyscrapers/wiki.json.

Usage: python3 engine/fetch_skyscrapers.py <city>   (reads cities/<city>/skyscrapers.json for the page title)

Run from GitHub Actions (.github/workflows/fetch-skyscrapers.yml): the sandbox can't reach Wikipedia.
Saves every wikitable on the page with the section it sits under, each cell's text and the first article
link in each cell, plus each linked article's coordinates and Wikidata id (from the Wikipedia API), and the
street addresses listed in skyscrapers.json geocoded with Nominatim (for towers with no coordinates).
engine/skyscrapers.py turns this into docs/<city>/data/skyscrapers.geojson. Wikipedia text is CC BY-SA 4.0.
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from lxml import html as lhtml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
city = sys.argv[1]
cfg = json.load(open(os.path.join(ROOT, 'cities', city, 'skyscrapers.json')))
OUT = os.path.join(ROOT, 'cities', city, 'raw', 'skyscrapers'); os.makedirs(OUT, exist_ok=True)
API = 'https://en.wikipedia.org/w/api.php'
UA = {'User-Agent': 'city-layers/1.0 (+https://maps.noumankhan.ca; github.com/noumanmkhan/city-layers)'}


def api(**q):
    q.update(format='json', formatversion=2)
    url = API + '?' + urllib.parse.urlencode(q)
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            print('  retry', i + 1, e); time.sleep(5 * (i + 1))
    raise SystemExit('Wikipedia API request failed: ' + url[:160])


page = api(action='parse', page=cfg['wiki'], prop='text|revid', redirects=1)['parse']
doc = lhtml.fromstring(page['text'])


def text(el):
    for s in el.xpath('.//sup[contains(@class,"reference")] | .//style | .//span[contains(@class,"sortkey")]'):
        s.drop_tree()
    return re.sub(r'\s+', ' ', el.text_content().replace('﻿', '')).strip()


def link(el):
    for a in el.xpath('.//a[@href]'):
        h = a.get('href')
        if h.startswith('/wiki/') and ':' not in h[6:].split('#')[0]:
            return urllib.parse.unquote(h[6:].split('#')[0]).replace('_', ' ')
    return None


def parse_table(t):
    """Rows of cells with rowspan/colspan expanded. Header rows are the leading rows made only of <th>."""
    grid, carry = [], {}
    for tr in t.xpath('./tr | ./tbody/tr | ./thead/tr'):
        row, col = [], 0
        cells = tr.xpath('./th | ./td')
        k = 0
        while k < len(cells) or col in carry:
            if col in carry:
                cell, left = carry[col]
                row.append(cell)
                if left > 1: carry[col] = (cell, left - 1)
                else: del carry[col]
                col += 1; continue
            c = cells[k]; k += 1
            cell = {'text': text(c), 'link': link(c), 'th': c.tag == 'th'}
            for _ in range(int(c.get('colspan', '1') or 1)):
                rs = int(re.sub(r'\D', '', c.get('rowspan', '1')) or 1)
                if rs > 1: carry[col] = (cell, rs - 1)
                row.append(cell); col += 1
        grid.append(row)
    head = []
    while grid and all(c['th'] for c in grid[0]):
        head.append([c['text'] for c in grid.pop(0)])
    cols = [' / '.join(dict.fromkeys(h[i] for h in head if i < len(h))) for i in range(max((len(h) for h in head), default=0))]
    return cols, [[{'text': c['text'], 'link': c['link']} for c in r] for r in grid if r]


tables, section = [], []
for el in doc.iter():
    if el.tag in ('h2', 'h3', 'h4'):
        lvl = int(el.tag[1]) - 2
        section = section[:lvl] + [text(el)]
    elif el.tag == 'table' and 'wikitable' in (el.get('class') or ''):
        cols, rows = parse_table(el)
        tables.append({'section': ' > '.join(section), 'columns': cols, 'rows': rows})
print('tables:', [(t['section'], len(t['rows'])) for t in tables])

# Coordinates and Wikidata ids of every linked article.
titles = sorted({c['link'] for t in tables for r in t['rows'] for c in r if c['link']})
pages = {}
for i in range(0, len(titles), 50):
    batch = titles[i:i + 50]
    r = api(action='query', prop='coordinates|pageprops', ppprop='wikibase_item', redirects=1, titles='|'.join(batch))['query']
    norm = {n['from']: n['to'] for n in r.get('normalized', [])}
    redir = {n['from']: n['to'] for n in r.get('redirects', [])}
    info = {p['title']: p for p in r.get('pages', [])}
    for t in batch:
        final = redir.get(norm.get(t, t), norm.get(t, t))
        p = info.get(final, {})
        c = (p.get('coordinates') or [None])[0]
        pages[t] = {'title': final, 'missing': bool(p.get('missing')),
                    'lat': c and c['lat'], 'lon': c and c['lon'], 'qid': (p.get('pageprops') or {}).get('wikibase_item')}
    time.sleep(1)
print('linked articles:', len(pages), 'with coordinates:', sum(1 for p in pages.values() if p['lat'] is not None))

# Towers with no coordinates in the list or an article (mostly ones under construction): their street
# addresses from skyscrapers.json, geocoded with OpenStreetMap Nominatim (one request a second, per its policy).
geo = cfg.get('geocode', {})
geocoded = {}
for name, addr in (geo.get('addresses') or {}).items():
    q = urllib.parse.urlencode({'q': addr + ', ' + geo['suffix'], 'format': 'jsonv2', 'limit': 1})
    try:
        with urllib.request.urlopen(urllib.request.Request('https://nominatim.openstreetmap.org/search?' + q, headers=UA), timeout=60) as r:
            hits = json.loads(r.read())
    except Exception as e:
        print('  geocode failed', name, e); hits = []
    geocoded[name] = {'address': addr, 'lat': hits and float(hits[0]['lat']), 'lon': hits and float(hits[0]['lon']),
                      'found': hits and hits[0].get('display_name')}
    print('  geocoded', name, '->', geocoded[name]['found'])
    time.sleep(1.2)

json.dump({'fetched': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'page': page['title'], 'revid': page['revid'],
           'license': 'CC BY-SA 4.0, Wikipedia contributors', 'tables': tables, 'pages': pages, 'geocoded': geocoded},
          open(os.path.join(OUT, 'wiki.json'), 'w'), indent=1, ensure_ascii=False)

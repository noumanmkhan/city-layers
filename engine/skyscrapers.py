"""Build docs/<city>/data/skyscrapers.geojson: every building 150 m or taller, from the Wikipedia list
fetched by engine/fetch_skyscrapers.py (cities/<city>/raw/skyscrapers/wiki.json) and the city's curated
settings (cities/<city>/skyscrapers.json).

Usage: python3 engine/skyscrapers.py <city>

Each tower: name, height (m and ft), floors, year, use (res / com / mix), whether it's still under
construction (uc), whether it's supertall (300 m+), its rank by height in the city, and up to a few
facts. Rules:
  - Use: Residential → res; Office and Hotel → com; Mixed-use → mix.
  - Under construction (drawn hollow): every row of the list's under-construction table; a row of the
    main table with a year after this one (Wikipedia lists towers once they top out); and a row with
    this year's date unless skyscrapers.json "open" says it's open for occupancy. Rows dated this year
    that aren't settled either way are printed, to be checked.
  - Rank: by height among the main table's rows (built or topped out), ties sharing a rank. A tower still
    in the under-construction table gets "will be the Nth-tallest … when finished" instead.
  - Facts, most telling first: curated lines from skyscrapers.json (country and world records, in our own
    words); "Tallest building in <city> from A to B" from the list's timeline table (matched by name, by
    skyscrapers.json "timelineNames", or by article when only one tower links to it); a top-10 rank; tallest
    completed in its decade; top-3 of its use (built or topped out); otherwise its rank. The card shows the first two.
Heights are the list's (architectural, spires but not antennas). Text: CC BY-SA 4.0, Wikipedia contributors.
"""
import json, os, re, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
city = sys.argv[1]
CDIR = os.path.join(ROOT, 'cities', city)
cfg = json.load(open(os.path.join(CDIR, 'skyscrapers.json')))
raw = json.load(open(os.path.join(CDIR, 'raw', 'skyscrapers', 'wiki.json')))
OUT = os.path.join(ROOT, 'docs', city, 'data', 'skyscrapers.geojson')
THIS_YEAR = date.today().year
SUPERTALL = 300
CITY = cfg['city']
USE = {'residential': 'res', 'office': 'com', 'hotel': 'com', 'mixed-use': 'mix'}
PURPOSE = {'residential': 'Residential', 'office': 'Office', 'hotel': 'Hotel', 'mixed-use': 'Mixed-use'}
PURPOSE_OF = {'res': 'Residential', 'com': 'Office', 'mix': 'Mixed-use'}
USE_WORD = {'res': 'residential tower', 'com': 'office or hotel tower', 'mix': 'mixed-use tower'}
USE_WORD_COM = {'Office': 'office tower', 'Hotel': 'hotel'}


def table(key):
    want = cfg['tables'][key]
    for t in raw['tables']:
        if t['section'] == want:
            return t
    raise SystemExit(f'No table under "{want}" in {raw["page"]} (sections: {[t["section"] for t in raw["tables"]]})')


def rows(t):
    cols = t['columns']
    def col(*names):
        for i, c in enumerate(cols):
            if any(c.lower().replace(' ', '').startswith(n) for n in names):
                return i
        return None
    idx = {'name': col('name'), 'loc': col('location'), 'h': col('height', 'std.height'), 'floors': col('floors'),
           'year': col('year'), 'purpose': col('purpose'), 'notes': col('notes'), 'tallest': col('yearsastallest')}
    for r in t['rows']:
        yield {k: (r[i] if i is not None and i < len(r) else {'text': '', 'link': None}) for k, i in idx.items()}


def heights(s):
    """'351.8 (1,154)' or '1,451 (442)' → (metres, feet), in the order skyscrapers.json "heights" gives."""
    nums = [float(x.replace(',', '')) for x in re.findall(r'\d[\d,]*(?:\.\d+)?', s)]
    if not nums:
        return None, None
    a = nums[0]; b = nums[1] if len(nums) > 1 else None
    if cfg['heights'][0] == 'm':
        return a, b if b is not None else round(a / 0.3048)
    return (b if b is not None else round(a * 0.3048, 1)), a


def coords(cell):
    m = re.search(r'(-?\d+\.\d+)°([NS])\s*(-?\d+\.\d+)°([EW])', cell)
    if m:
        lat = float(m.group(1)) * (1 if m.group(2) == 'N' else -1)
        lon = float(m.group(3)) * (1 if m.group(4) == 'E' else -1)
        return [round(lon, 6), round(lat, 6)]
    return None


def article(link):
    p = raw['pages'].get(link) if link else None
    return p['title'] if p and not p.get('missing') else None


def clean_name(n):
    """'Concord Sky (385 Yonge Street)' → ('Concord Sky', '385 Yonge Street'); other brackets stay."""
    m = re.match(r'^(.*?)\s*\((\d[^)]*(?:Street|Avenue|Boulevard|Road|Drive|Way|Quay)[^)]*)\)$', n)
    return (m.group(1), m.group(2)) if m else (n, None)


def ordinal(n):
    return f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def tallest(n, what):
    return f'Tallest {what}' if n == 1 else f'{ordinal(n)}-tallest {what}'


open_cfg = {k: v for k, v in cfg.get('open', {}).items() if not k.startswith('_')}
exclude = cfg.get('exclude', {})
towers, missing, to_check = [], [], []
for key, uc_table in (('built', False), ('uc', True)):
    for r in rows(table(key)):
        raw_name = r['name']['text']
        if not raw_name or raw_name in exclude:
            continue
        name, address = clean_name(raw_name)
        h, ft = heights(r['h']['text'])
        if h is None:
            print('  no height, skipped:', raw_name); continue
        if h < 150:
            continue
        year_txt = r['year']['text'].strip()
        year = int(year_txt) if year_txt.isdigit() else None
        if uc_table or year is None or year > THIS_YEAR:
            uc = True
        elif year == THIS_YEAR:
            if raw_name in open_cfg: uc = not open_cfg[raw_name]
            else: uc = True; to_check.append(raw_name)
        else:
            uc = False
        purpose = r['purpose']['text']
        use = cfg.get('use', {}).get(raw_name) or USE.get(purpose.lower().replace(' ', ''))
        if not use:
            print('  unknown use', repr(purpose), 'for', raw_name, '- shown as mixed-use'); use = 'mix'
        wiki = article(r['name']['link'])
        at = coords(r['loc']['text'])
        if not at and wiki:
            p = raw['pages'].get(r['name']['link'])
            if p and p.get('lat') is not None: at = [round(p['lon'], 6), round(p['lat'], 6)]
        if not at and raw_name in cfg.get('coords', {}):
            at = cfg['coords'][raw_name]
        if not at:
            g = raw.get('geocoded', {}).get(raw_name)
            if g and g.get('lat'): at = [round(g['lon'], 6), round(g['lat'], 6)]; address = address or g['address']
        if not at:
            missing.append(raw_name); continue
        floors = r['floors']['text']
        towers.append({'name': name, 'raw': raw_name, 'address': address, 'h': round(h, 1), 'ft': int(round(ft)),
                       'floors': int(floors) if floors.isdigit() else None, 'year': year, 'use': use,
                       'purpose': purpose, 'uc': uc, 'inMain': not uc_table, 'wiki': wiki, 'at': at})

# Timeline of tallest buildings: "Tallest building in <city> from A to B", matched by article, then by name.
timeline = {}
for r in rows(table('timeline')):
    span = re.sub(r'\s*\(\d+\)\s*$', '', r['tallest']['text']).replace('present', '').strip()
    span = re.sub(r'\(.*?\)|\[.*?\]', '', span).strip()
    years = re.findall(r'\d{4}', span)
    if not years: continue
    if len(years) == 1 and span.endswith(('–', '-')): text = f'Tallest building in {CITY} since {years[0]}'
    elif len(years) == 1: text = f'Briefly the tallest building in {CITY}, in {years[0]}'
    else: text = f'Tallest building in {CITY} from {years[0]} to {years[1]}'
    nm = re.sub(r'\[.*?\]', '', r['name']['text']).strip()
    timeline[cfg.get('timelineNames', {}).get(nm, nm)] = text
    if article(r['name']['link']): timeline['wiki:' + article(r['name']['link'])] = text

wiki_count = {}
for t in towers:
    if t['wiki']: wiki_count[t['wiki']] = wiki_count.get(t['wiki'], 0) + 1

# Ranks, among the main table's towers (built or topped out), ties sharing a rank.
main = sorted([t for t in towers if t['inMain']], key=lambda t: -t['h'])
for t in main:
    t['rank'] = 1 + sum(1 for o in main if o['h'] > t['h'])
n_main = len(main)
for t in towers:
    if not t['inMain']:
        t['rank'] = 1 + sum(1 for o in main if o['h'] > t['h'])

# Tallest completed in each decade (open towers only), and the top 3 of each use (built or topped out).
built = [t for t in main if not t['uc']]
decade_top = {}
for t in built:
    if t['year']:
        d = t['year'] // 10 * 10
        if d not in decade_top or t['h'] > decade_top[d]['h']: decade_top[d] = t
use_rank = {}
for u in ('res', 'com', 'mix'):
    group = sorted([t for t in main if t['use'] == u], key=lambda t: -t['h'])   # like the overall rank: built or topped out
    for t in group: use_rank[id(t)] = 1 + sum(1 for o in group if o['h'] > t['h'])

curated = {k: v for k, v in cfg.get('facts', {}).items() if not k.startswith('_')}
aka = cfg.get('aka', {})
used_curated = set()
for t in towers:
    facts = list(curated.get(t['raw'], []))
    if t['raw'] in curated: used_curated.add(t['raw'])
    # By name, else by article when only this tower links to it (towers in a complex share one article).
    tl = timeline.get(t['raw']) or timeline.get(t['name']) or (t['wiki'] and wiki_count[t['wiki']] == 1 and timeline.get('wiki:' + t['wiki']))
    if tl and t['inMain']: facts.append(tl)
    if not t['inMain']:
        facts.append(f'Will be the {"tallest" if t["rank"] == 1 else ordinal(t["rank"]) + "-tallest"} building in {CITY} when finished')
    else:
        if t['rank'] <= 10 and not (t['rank'] == 1 and tl): facts.append(f'{tallest(t["rank"], "building in " + CITY)}')
        if not t['uc'] and t['year']:
            d = t['year'] // 10 * 10
            if decade_top.get(d) is t:
                facts.append(f'Tallest building completed in {CITY} in the {d}s' + (' so far' if d + 10 > THIS_YEAR else ''))
        if use_rank.get(id(t), 99) <= 3:
            word = USE_WORD_COM.get(t['purpose'], 'office tower') if t['use'] == 'com' else USE_WORD[t['use']]
            if t['use'] == 'com' and t['purpose'] == 'Hotel': word = 'hotel'
            facts.append(f'{tallest(use_rank[id(t)], word + " in " + CITY)}')
        if t['rank'] > 10: facts.append(f'{ordinal(t["rank"])}-tallest of the {n_main} skyscrapers in {CITY}')
    seen, t['facts'] = set(), []
    for f in facts:
        k = f.lower()
        if k not in seen: seen.add(k); t['facts'].append(f)

unused = set(curated) - used_curated
if unused: print('  curated facts for towers not in the list (check names):', sorted(unused))
for k in list(open_cfg) + list(cfg.get('use', {})) + list(aka) + [c for c in cfg.get('coords', {}) if not c.startswith('_')]:
    if not any(t['raw'] == k for t in towers): print('  skyscrapers.json names a tower not in the list:', k)

feats = []
for t in sorted(towers, key=lambda t: -t['h']):
    p = {'name': t['name'], 'h': t['h'], 'ft': t['ft'], 'floors': t['floors'], 'year': t['year'], 'use': t['use'],
         'purpose': PURPOSE.get(t['purpose'].lower().replace(' ', ''), PURPOSE_OF[t['use']]),
         'uc': t['uc'], 'super': t['h'] >= SUPERTALL, 'rank': t['rank'], 'facts': t['facts'][:3]}
    if t['address']: p['address'] = t['address']
    if t['raw'] in aka: p['aka'] = aka[t['raw']]
    if t['wiki']: p['wiki'] = t['wiki']
    feats.append({'type': 'Feature', 'properties': p, 'geometry': {'type': 'Point', 'coordinates': t['at']}})

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({'type': 'FeatureCollection', 'source': f'Wikipedia, "{raw["page"]}" (revision {raw["revid"]}, fetched {raw["fetched"][:10]}), CC BY-SA 4.0',
           'features': feats}, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
uc = sum(1 for t in towers if t['uc'])
print(f'skyscrapers: {len(feats)} ({len(feats) - uc} open, {uc} under construction, '
      f'{sum(1 for t in towers if t["h"] >= SUPERTALL)} supertall)')
if missing: print('  no coordinates, left out:', missing)
if to_check: print(f'  dated {THIS_YEAR} and not marked open or not in skyscrapers.json "open"; drawn hollow until checked:', to_check)

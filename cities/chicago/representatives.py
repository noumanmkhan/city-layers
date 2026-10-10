"""Match the current officeholders in raw/representatives/ (fetched by fetch_representatives.py) to the
map's wards and districts. Output: docs/chicago/data/representatives.json

{"updated": date of the last change, "wards": {"1": {"name", "url"}}, "house": {...}, "senate": {...}, "congress": {...}}
House, Senate and Congress entries also carry "party". A seat with no current holder is left out, and
the page shows it as vacant. "updated" only moves when a name, party or link actually changes.

"trustees": {"cps": {"1a": {candidates, leader?, winner?}, ..., "president": {...}}} is the Chicago Board
of Education race on November 3, 2026: candidates in ballot order from raw/school_board/candidates.json
(school_board_candidates.py); once the election board posts results (raw/school_board/results.json,
from fetch_school_board_results.py), "leader" names whoever leads the count, and "winner" is set once
the board has proclaimed the results official.
"""
import csv, datetime, html, json, os, re, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'representatives')
DATA = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data')
OUT = os.path.join(DATA, 'representatives.json')
nums = lambda f, key='num': {str(x['properties'][key]) for x in json.load(open(os.path.join(DATA, f)))['features']}
PARTY = {'D': 'Democrat', 'R': 'Republican', 'Democratic': 'Democrat', 'Republican': 'Republican', 'I': 'Independent'}

wards = {}
for o in json.load(open(os.path.join(SRC, 'ward_offices.json'))):
    n = str(int(o['ward']))
    last, _, first = (o.get('alderman') or '').partition(',')
    if not last.strip(): continue
    url = (o.get('website') or {}).get('url') or 'https://www.chicago.gov/city/en/about/wards/%02d.html' % int(n)
    wards[n] = {'name': (first.strip() + ' ' + last.strip()).strip(), 'url': url}

house, senate = {}, {}
for r in csv.DictReader(open(os.path.join(SRC, 'il.csv'), encoding='utf-8')):
    links = [l for l in r['links'].split(';') if 'ilga.gov' in l]
    url = next((l for l in links if '/Members/Details/' in l), links[-1] if links else '')
    entry = {'name': r['name'], 'url': url, 'party': PARTY.get(r['current_party'], r['current_party'])}
    (house if r['current_chamber'] == 'lower' else senate)[str(int(r['current_district']))] = entry

congress = {}
for m in ET.parse(os.path.join(SRC, 'house.xml')).getroot().find('members'):
    sd = m.findtext('statedistrict') or ''
    name = m.findtext('member-info/official-name')
    if not sd.startswith('IL') or not name:
        continue
    bio = m.findtext('member-info/bioguideID')
    congress[str(int(sd[2:]))] = {'name': name, 'url': 'https://clerk.house.gov/members/' + bio,
                                  'party': PARTY.get(m.findtext('member-info/party'), m.findtext('member-info/party'))}

# Only the seats the map shows.
house_n = nums('il_house.geojson')
out = {'wards': {k: v for k, v in wards.items() if k in nums('wards.geojson')},
       'house': {k: v for k, v in house.items() if k in house_n},
       'senate': {k: v for k, v in senate.items() if str(int(k) * 2) in house_n or str(int(k) * 2 - 1) in house_n},
       'congress': {k: v for k, v in congress.items() if k in nums('congress.geojson')}}

# Chicago Board of Education, 2026.
SB = os.path.join(HERE, 'raw', 'school_board')
if os.path.exists(os.path.join(SB, 'candidates.json')):
    cand = json.load(open(os.path.join(SB, 'candidates.json')))
    cps = {k: {'candidates': v} for k, v in cand['districts'].items()}
    cps['president'] = {'candidates': cand['president']}
    rp = os.path.join(SB, 'results.json')
    if os.path.exists(rp):
        res = json.load(open(rp))
        clean = lambda t: re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', t))).strip()
        for contest, frag in res['contests'].items():
            m = re.search(r'Subdistrict (\d+)([AB])', contest)
            key = m.group(1) + m.group(2).lower() if m else ('president' if contest.startswith('President') else None)
            t = re.search(r'<table.*?</table>', frag, re.S)   # the first table is the contest's totals
            if key not in cps or not t: continue
            heads = [clean(h) for h in re.findall(r'<th[^>]*>(.*?)</th>', t.group(0), re.S)]
            cells = [clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', t.group(0), re.S)]
            votes = sorted(((int(cells[i].replace(',', '') or 0), h) for i, h in enumerate(heads)
                            if i and h not in ('%', 'Total Votes') and i < len(cells)), reverse=True)
            if not votes or votes[0][0] == 0: continue
            if len(votes) > 1 and votes[0][0] == votes[1][0]:
                print('  ! tie in', contest); continue
            cps[key]['leader'] = votes[0][1]
            if res.get('official'): cps[key]['winner'] = votes[0][1]
    out['trustees'] = {'cps': cps}

old = json.load(open(OUT)) if os.path.exists(OUT) else {}
same = {k: v for k, v in old.items() if k != 'updated'} == out
out = {'updated': old['updated'] if same and old.get('updated') else datetime.date.today().isoformat(), **out}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=0)
print('representatives:', {k: len(v) for k, v in out.items() if k != 'updated'}, 'updated', out['updated'],
      '· missing wards', sorted(nums('wards.geojson') - set(out['wards'])), 'house', sorted(house_n - set(out['house'])))

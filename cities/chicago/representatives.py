"""Match the current officeholders in raw/representatives/ (fetched by fetch_representatives.py) to the
map's wards and districts. Output: docs/chicago/data/representatives.json

{"updated": date of the last change, "wards": {"1": {"name", "url"}}, "house": {...}, "senate": {...}, "congress": {...}}
House, Senate and Congress entries also carry "party". A seat with no current holder is left out, and
the page shows it as vacant. "updated" only moves when a name, party or link actually changes.
"""
import csv, datetime, json, os, xml.etree.ElementTree as ET

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
old = json.load(open(OUT)) if os.path.exists(OUT) else {}
same = {k: v for k, v in old.items() if k != 'updated'} == out
out = {'updated': old['updated'] if same and old.get('updated') else datetime.date.today().isoformat(), **out}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=0)
print('representatives:', {k: len(v) for k, v in out.items() if k != 'updated'}, 'updated', out['updated'],
      '· missing wards', sorted(nums('wards.geojson') - set(out['wards'])), 'house', sorted(house_n - set(out['house'])))

"""Who represents each part of Toronto, with a link to their official page.
Inputs: raw/representatives/ (fetched by fetch_representatives.py), and the map's ward and
federal riding files for the names to match against.
Output: ../docs/toronto/data/representatives.json
  {"updated": date, "wards": {"11": {name, url}}, "prov": {"University—Rosedale": {name, party, url}},
   "fed": {"University—Rosedale": {name, party, url}}}

Provincial ridings in Toronto share the wards' lines, so a ward's 'prov' name is the riding.
Councillors have no party: Toronto's municipal elections are non-partisan."""
import html, json, os, re, sys, unicodedata, datetime as dt
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'representatives')
DOCS = os.path.join(HERE, '..', 'docs', 'toronto', 'data')


def key(s):
    """Riding names differ in dashes, accents and apostrophes between sources; compare loosely."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', s)


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


wards = json.load(open(os.path.join(DOCS, 'wards.geojson')))['features']
feds = [f['properties']['name'] for f in json.load(open(os.path.join(DOCS, 'federal.geojson')))['features']]
provs = sorted({f['properties']['prov'] for f in wards})
problems = []

# City councillors: "Councillor Dianne Saxe – City of Toronto"
tor = json.load(open(os.path.join(RAW, 'toronto.json')))
out_w = {}
for n, v in tor.items():
    m = re.match(r'Councillor\s+(.+?)\s+[–\-|]', html.unescape(v['title']))
    if m: out_w[n] = {'name': m.group(1).strip(), 'url': v['url']}
    else: out_w[n] = {'name': None, 'url': v['url']}; problems.append('ward %s: no name in %r' % (n, v['title']))

# MPPs: cards with a link, a name, a party and a riding.
page = open(os.path.join(RAW, 'ola.html'), encoding='utf-8').read()
ola = {}
clean = lambda t: re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', t))).strip()
for card in page.split('class="mpp-card-link"')[1:]:
    name = re.search(r'<h3[^>]*>(.*?)</h3>', card, re.S)
    party = re.search(r'current-members-party">(.*?)</p>', card, re.S)
    riding = re.search(r'current-members-riding">(.*?)</p>', card, re.S)
    if not (name and party and riding): continue
    ola.setdefault(key(clean(riding.group(1))), {'name': clean(name.group(1)), 'party': clean(party.group(1)), 'href': None})
# The link sits just before each card's class attribute, so pair them up separately.
for href, card in re.findall(r'<a href="(/en/members/all/[^"]+)" class="mpp-card-link">(.{0,3000}?)</a>', page, re.S):
    riding = re.search(r'current-members-riding">(.*?)</p>', card, re.S)
    if riding and key(clean(riding.group(1))) in ola:
        ola[key(clean(riding.group(1)))]['url'] = 'https://www.ola.org' + href
for v in ola.values(): v.pop('href', None)
out_p = {}
for r in provs:
    if key(r) in ola: out_p[r] = ola[key(r)]
    else: out_p[r] = None; problems.append('MPP not found: ' + r)

# MPs: the House of Commons' list of current members.
root = ET.parse(os.path.join(RAW, 'ourcommons.xml')).getroot()
com = {}
for m in root.iter('MemberOfParliament'):
    g = lambda t: (m.findtext(t) or '').strip()
    if g('ConstituencyProvinceTerritoryName') != 'Ontario': continue
    name = g('PersonOfficialFirstName') + ' ' + g('PersonOfficialLastName')
    com[key(g('ConstituencyName'))] = {'name': name, 'party': g('CaucusShortName'),
                                       'url': 'https://www.ourcommons.ca/Members/en/%s(%s)' % (slug(name), g('PersonId'))}
out_f = {}
for r in feds:
    if key(r) in com: out_f[r] = com[key(r)]
    else: out_f[r] = None; problems.append('MP not found (seat may be vacant): ' + r)

# 'updated' is the date the list last changed, so a weekly run with no news leaves the file untouched.
OUT = os.path.join(DOCS, 'representatives.json')
new = {'wards': out_w, 'prov': out_p, 'fed': out_f}
try:
    old = json.load(open(OUT))
except Exception:
    old = {}
updated = old.get('updated') if {k: v for k, v in old.items() if k != 'updated'} == new else dt.date.today().isoformat()
json.dump(dict(updated=updated, **new), open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('representatives:', sum(1 for v in out_w.values() if v['name']), 'councillors,',
      sum(1 for v in out_p.values() if v), 'MPPs,', sum(1 for v in out_f.values() if v), 'MPs')
for p in problems: print('  !', p)
# A partial list is still useful (a vacant seat is real), but an empty source means the page changed.
if not ola or not com or not any(v['name'] for v in out_w.values()):
    sys.exit('a source came back empty; the page format may have changed')

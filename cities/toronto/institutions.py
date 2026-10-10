"""Universities, colleges and hospitals for the institution toggles under Landmarks.
Input: raw/institutions_osm.json (fetch_institutions.py). Output: docs/toronto/data/institutions.geojson

A curated list, placed by OpenStreetMap: each entry names the OSM object whose centre marks it, and the
script stops if one has gone. Describe only: no ratings, rankings or wait times. The rules (decided
October 9, 2026; the same in Chicago):

Universities: public, or private nonprofit with Ontario degree-granting authority and over 1,000
  students (Tyndale). One point per campus in the City of Toronto. Left out: satellite sites of
  universities based elsewhere (Laurier, McMaster, Queen's Smith School, Northeastern) and federated or
  theological colleges inside a campus (Victoria, Trinity, St. Michael's, Regis, Wycliffe, Knox).
Colleges: public only (Ontario's colleges of applied arts and technology, and Collège Boréal). One point
  per campus; small satellite sites left out. Left out on purpose: public-private partnership campuses,
  where a public college's name is on a campus run by a private company (Lambton at Cestar, Canadore at
  Stanford, Loyalist in Toronto, Sault in Toronto). In 2024 Ontario cut their students off from
  post-graduation work permits; this map doesn't point newcomers at them. Private career colleges are
  left out too.
Hospitals: Ontario public hospitals (every site in the city, including rehab, mental health and
  complex care), plus OHIP-funded private hospitals: Shouldice, just north of the city in Markham, which
  shows in the regional view. (The Don Mills Surgical Unit also qualifies but isn't mapped in
  OpenStreetMap, so it isn't placed yet.) "ed" marks a site with an emergency department, as tagged in
  OpenStreetMap (CAMH's are psychiatric emergency departments)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data', 'institutions.geojson')

# (name, sub, OSM id)
UNIVERSITIES = [
    ('University of Toronto', 'St. George campus', 'r18447148'),
    ('University of Toronto Scarborough', 'U of T', 'r21058560'),
    ('York University', 'Keele campus', 'w15396822'),
    ('Glendon College', 'York University', 'w23334883'),
    ('Toronto Metropolitan University', '', 'r16358719'),
    ('OCAD University', '', 'r2995413'),
    ("Université de l'Ontario français", 'French-language public university', 'n9633703338'),
    ('Tyndale University', 'Private nonprofit', 'w702100748'),
]
COLLEGES = [
    ('Centennial College', 'Progress campus', 'w33013888'),
    ('Centennial College', 'Morningside campus', 'w660212115'),
    ('Centennial College', 'Ashtonbee campus', 'w36508437'),
    ('Centennial College', 'Downsview Park campus', 'w1034677780'),
    ('Centennial College', 'Story Arts Centre', 'w775639084'),
    ('George Brown College', 'St. James campus', 'w43808577'),
    ('George Brown College', 'Casa Loma campus', 'w42705254'),
    ('George Brown College', 'Waterfront campus', 'w775640504'),
    ('Humber Polytechnic', 'North campus', 'w220190025'),
    ('Humber Polytechnic', 'Lakeshore campus', 'w505921693'),
    ('Seneca Polytechnic', 'Newnham campus', 'w703666033'),
    ('Seneca Polytechnic', 'Seneca @ York', 'w775641405'),
    ('Collège Boréal', 'Toronto campus · French-language', 'n2681580824'),
]
# (name, sub, OSM id, emergency department)
HOSPITALS = [
    ('Toronto General Hospital', 'University Health Network', 'w712078928', True),
    ('Toronto Western Hospital', 'University Health Network', 'w43805626', True),
    ('Princess Margaret Cancer Centre', 'University Health Network', 'w712078932', False),
    ('Toronto Rehab', 'University Health Network', 'w712078930', False),
    ('Toronto Rehab, Lyndhurst Centre', 'University Health Network', 'w684431221', False),
    ('Toronto Rehab, Rumsey Centre', 'University Health Network', 'w684431220', False),
    ('E.W. Bickle Centre', 'University Health Network · complex care', 'w712078934', False),
    ('Mount Sinai Hospital', 'Sinai Health', 'w712078931', True),
    ('Hennick Bridgepoint Hospital', 'Sinai Health · rehab and complex care', 'w437519686', False),
    ("St. Michael's Hospital", 'Unity Health Toronto', 'w712085020', True),
    ("St. Joseph's Health Centre", 'Unity Health Toronto', 'w152167667', True),
    ('Providence Healthcare', 'Unity Health Toronto · rehab and complex care', 'w26949564', False),
    ('The Hospital for Sick Children', 'SickKids', 'w712078929', True),
    ('Sunnybrook Health Sciences Centre', 'Bayview campus', 'w27006473', True),
    ('Sunnybrook Holland Centre', 'Sunnybrook', 'w712085019', False),
    ("St. John's Rehab", 'Sunnybrook', 'w684426041', False),
    ("Women's College Hospital", 'Urgent care, no emergency department', 'w712085021', False),
    ('North York General Hospital', '', 'w684426043', True),
    ('North York General, Branson site', 'North York General', 'w678430199', False),
    ('Hennick Humber Hospital', 'Humber River Health', 'w673002279', True),
    ('Etobicoke General Hospital', 'William Osler Health System', 'w670281258', True),
    ('Queensway Health Centre', 'Trillium Health Partners', 'w34006717', False),
    ('Michael Garron Hospital', '', 'w447744987', True),
    ('Scarborough General Hospital', 'Scarborough Health Network', 'w681295729', True),
    ('Centenary Hospital', 'Scarborough Health Network', 'w5520155', True),
    ('Birchmount Hospital', 'Scarborough Health Network', 'w681295730', True),
    ('CAMH, Queen Street', 'Centre for Addiction and Mental Health', 'w22793935', True),
    ('CAMH, College Street', 'Centre for Addiction and Mental Health', 'w712078933', True),
    ('Baycrest Hospital', 'Baycrest', 'w678508080', False),
    ('Holland Bloorview Kids Rehabilitation Hospital', '', 'w684431222', False),
    ('West Park Healthcare Centre', 'Rehab and complex care', 'w671599453', False),
    ('Runnymede Healthcare Centre', 'Rehab and complex care', 'w486817681', False),
    ('Toronto Grace Health Centre', 'Salvation Army · complex care', 'w712086304', False),
    ('Casey House', 'HIV/AIDS care', 'w684433261', False),
    ('Shouldice Hospital', 'Private, OHIP-funded · in Markham', 'w684426042', False),
]

osm = {e['osm']: e for e in json.load(open(os.path.join(HERE, 'raw', 'institutions_osm.json')))['elements']}
missing = [i for group in (UNIVERSITIES, COLLEGES, HOSPITALS) for (_, _, i, *_) in group if i not in osm]
if missing: raise SystemExit('not in raw/institutions_osm.json any more: ' + ', '.join(missing))


def feat(name, sub, oid, cat, **extra):
    p = {'name': name, 'cat': cat}
    if sub: p['sub'] = sub
    p.update(extra)
    return {'type': 'Feature', 'properties': p, 'geometry': {'type': 'Point', 'coordinates': osm[oid]['at']}}


feats = ([feat(n, s, i, 'university') for n, s, i in UNIVERSITIES] + [feat(n, s, i, 'college') for n, s, i in COLLEGES] +
         [feat(n, s, i, 'hospital', ed=ed) for n, s, i, ed in HOSPITALS])
json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('institutions:', len(UNIVERSITIES), 'universities,', len(COLLEGES), 'college campuses,', len(HOSPITALS), 'hospitals',
      f'({sum(1 for h in HOSPITALS if h[3])} with an emergency department)')

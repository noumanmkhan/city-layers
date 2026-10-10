"""Universities, colleges and ERs for the institution toggles under Landmarks.
Inputs: raw/institutions/ (fetch_institutions.py). Output: docs/chicago/data/institutions.geojson

The rules (decided October 9, 2026; the same as Toronto's). Describe only: no ratings or rankings.

Universities: from the IPEDS directory, every active, degree-granting, four-year institution in the
  city that is public or private nonprofit, never for-profit, with 1,000 or more students (IPEDS size
  category 2 and up). The size floor keeps out small seminaries and specialty schools. Placed at the
  IPEDS address, except where OpenStreetMap marks the main campus better; DePaul and Loyola also get
  their second big campus, and Northwestern (based in Evanston) its Chicago campus. One point per
  campus; small satellite sites are left out.
Colleges: public only, so the City Colleges of Chicago (7). The district office is left out.
ERs: hospitals with an emergency department (CMS "Emergency Services: Yes"), public or nonprofit.
  For-profit ("Proprietary") hospitals are left out, and so are two Prime Healthcare hospitals that CMS
  still lists as church nonprofits but became for-profit when Prime bought them from Ascension in March
  2025 (Resurrection, and Saint Mary of Nazareth / Saints Mary and Elizabeth). Hospital emergency
  departments only, not freestanding urgent care. Each is placed by its OpenStreetMap outline and shown
  under its current name. The script stops if CMS lists a qualifying hospital this file doesn't name,
  so a new or renamed one gets a look."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'institutions')
DATA = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data')
OUT = os.path.join(DATA, 'institutions.geojson')

osm = {e['osm']: e for e in json.load(open(os.path.join(RAW, 'osm.json')))}

# IPEDS unit id -> (OSM id for a better position, sub). Missing: the IPEDS position as is.
UNI_POS = {'144740': ('r2527861', 'Lincoln Park campus'), '146719': ('r11191827', 'Lake Shore campus'),
           '148511': ('r15652551', '')}
UNI_EXTRA = [('DePaul University', 'Loop campus', 'r15979377'), ('Loyola University Chicago', 'Water Tower campus', 'r17594942'),
             ('Northwestern University', 'Chicago campus · Streeterville', 'r17607254')]
UNI_NAME = {'145600': 'University of Illinois Chicago', '143978': 'The Chicago School'}

# CMS facility id -> (name shown, sub, OSM id)
ERS = {
    '140182': ('Advocate Illinois Masonic Medical Center', 'Advocate Health', 'r18239404'),
    '140048': ('Advocate Trinity Hospital', 'Advocate Health', 'w241870223'),
    '143300': ("Lurie Children's Hospital", "Children's hospital", 'w47055764'),
    '140133': ('Holy Cross Hospital', 'Sinai Chicago', 'w228663039'),
    '140206': ('Humboldt Park Health', '', 'r18907604'),
    '140158': ('Insight Hospital and Medical Center', '', 'w210570610'),
    '140177': ('Jackson Park Hospital', '', 'w222831338'),
    '14003F': ('Jesse Brown VA Medical Center', 'Veterans Affairs', 'w537392585'),
    '140124': ('Stroger Hospital', 'Cook County Health', 'r20590371'),
    '140083': ('Loretto Hospital', '', 'w162513176'),
    '140197': ('Thorek Memorial Hospital Andersonville', 'Formerly Methodist Hospital', 'w134578632'),
    '140018': ('Mount Sinai Hospital', 'Sinai Chicago', 'w242228765'),
    '140281': ('Northwestern Memorial Hospital', 'Northwestern Medicine', 'r17607255'),
    '140224': ('Ascension Saint Joseph', 'Lakeview', 'w211090327'),
    '140300': ('Provident Hospital', 'Cook County Health', 'w244945457'),
    '140068': ('Roseland Community Hospital', '', 'w239938453'),
    '140119': ('Rush University Medical Center', 'Rush', 'r20590975'),
    '140095': ('Saint Anthony Hospital', '', 'w551141105'),
    '140181': ('South Shore Hospital', '', 'w551155326'),
    '140103': ('St. Bernard Hospital', '', 'r21467109'),
    '140114': ('Swedish Hospital', 'Endeavor Health', 'w209730046'),
    '140088': ('University of Chicago Medical Center', 'UChicago Medicine', 'w229438623'),
    '140115': ('Thorek Memorial Hospital', '', 'r14685787'),
    '140150': ('UI Health', 'University of Illinois Hospital', 'r20600200'),
}
NOW_FOR_PROFIT = {'140117', '140180'}   # Prime Healthcare, from March 2025 (see above)

feats = []
pt = lambda p, props: {'type': 'Feature', 'properties': props, 'geometry': {'type': 'Point', 'coordinates': p}}

# Universities and colleges from IPEDS
rows = list(csv.DictReader(open(os.path.join(RAW, 'ipeds_hd.csv'), encoding='utf-8-sig')))
uid = list(rows[0].keys())[0]
n_uni = n_col = 0
for r in rows:
    if r['CITY'].strip().lower() != 'chicago' or r['CYACTIVE'] != '1': continue
    at = [round(float(r['LONGITUD']), 5), round(float(r['LATITUDE']), 5)]
    size = int(r['INSTSIZE'])
    if r['CONTROL'] in ('1', '2') and r['ICLEVEL'] == '1' and r['DEGGRANT'] == '1' and size >= 2:
        name = UNI_NAME.get(r[uid], r['INSTNM'])
        oid, sub = UNI_POS.get(r[uid], (None, ''))
        props = {'name': name, 'cat': 'university'}
        props['sub'] = ' · '.join(x for x in (sub, 'Public' if r['CONTROL'] == '1' else 'Private nonprofit') if x)
        feats.append(pt(osm[oid]['at'] if oid else at, props)); n_uni += 1
    elif r['CONTROL'] == '1' and r['ICLEVEL'] == '2' and size >= 1 and r['INSTNM'].startswith('City Colleges of Chicago-'):
        feats.append(pt(at, {'name': r['INSTNM'].split('-', 1)[1].replace('Harry S Truman', 'Truman').replace('Richard J Daley', 'Daley')
                                            .replace('Wilbur Wright', 'Wright'), 'sub': 'City Colleges of Chicago', 'cat': 'college'})); n_col += 1
for name, sub, oid in UNI_EXTRA:
    feats.append(pt(osm[oid]['at'], {'name': name, 'sub': sub + ' · Private nonprofit', 'cat': 'university'})); n_uni += 1

# ERs from CMS
unknown = []
n_er = 0
for r in csv.DictReader(open(os.path.join(RAW, 'cms_hospitals.csv'), encoding='utf-8')):
    fid = r['Facility ID']
    if r['Emergency Services'] != 'Yes' or r['Hospital Ownership'] == 'Proprietary' or fid in NOW_FOR_PROFIT: continue
    if fid not in ERS:
        unknown.append(f"{fid} {r['Facility Name']} ({r['Hospital Ownership']})"); continue
    name, sub, oid = ERS[fid]
    props = {'name': name, 'cat': 'hospital', 'ed': True}
    if sub: props['sub'] = sub
    feats.append(pt(osm[oid]['at'], props)); n_er += 1
if unknown: raise SystemExit('CMS lists qualifying hospitals not named in institutions.py: ' + '; '.join(unknown))

json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('institutions:', n_uni, 'university campuses,', n_col, 'City Colleges,', n_er, 'ERs')

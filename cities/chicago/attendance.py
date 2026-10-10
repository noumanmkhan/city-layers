"""CPS attendance areas for the card's Schools section: raw/attendance/ -> docs/chicago/data/attendance.geojson.

One file holds all three levels (CPS publishes them as separate datasets):
  es  elementary attendance areas (356 areas; most K-8, some K-5 or K-6 where a middle school takes over)
  ms  middle school attendance areas (22 schools have one)
  hs  high school attendance areas (49)
Each feature: level, grades ("K–8"), the school's full name, its CPS profile page, and the building's
location (x, y) for the card's straight-line distance. Names and locations come from CPS's school
profile file; the boundary's own short name and address are the fallback.

Describe only: which school's area the spot is in, its grades and how far the building is. No ratings,
scores, enrolment or demographics are carried over from the profile file.
"""
import json, os, re, subprocess
from shapely.geometry import shape, mapping

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw', 'attendance')
TMP = os.path.join(HERE, 'tmp')
OUT = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data', 'attendance.geojson')
LEVELS = {'elementary': 'es', 'middle': 'ms', 'high': 'hs'}

sources = json.load(open(os.path.join(RAW, 'sources.json')))
profiles = {r['school_id']: r for r in json.load(open(os.path.join(RAW, 'profiles.json')))}


def grades(s):
    g = [x.strip() for x in s.split(',') if x.strip()]
    return g[0] if len(g) == 1 else g[0] + '–' + g[-1]


def title(s):   # fallback name from the boundary file: "NORTH-GRAND HS" -> "North-Grand HS"
    return ' '.join(w if w in ('HS', 'ES', 'MS') else w.capitalize() for w in s.split())


def where(addr):
    return re.sub(r'\s+', ' ', addr).split(',')[0].split(' Chicago')[0].split(' CHICAGO')[0].strip().title()


feats, missing = [], 0
for name, level in LEVELS.items():
    by = {}
    for f in json.load(open(os.path.join(RAW, name + '.geojson')))['features']:
        p = f['properties']
        key = (p['school_id'], p['boundarygr'])   # a school can have separate areas for different grades
        geom = shape(f['geometry']).buffer(0)
        by[key] = by[key].union(geom) if key in by else geom
    for (sid, gr), geom in by.items():
        prof = profiles.get(sid)
        src = next(f['properties'] for f in json.load(open(os.path.join(RAW, name + '.geojson')))['features'] if f['properties']['school_id'] == sid) if not prof else None
        props = {'level': level, 'grades': grades(gr), 'id': sid}
        if prof and prof.get('school_latitude'):
            props.update(name=prof['long_name'].strip(), url=(prof.get('cps_school_profile') or {}).get('url', ''),
                         x=round(float(prof['school_longitude']), 5), y=round(float(prof['school_latitude']), 5))
        else:
            missing += 1
            props.update(name=title(src.get('short_name') or src.get('school_nam')), url='', addr=where(src['school_add']))
        feats.append({'type': 'Feature', 'properties': props, 'geometry': mapping(geom)})

os.makedirs(TMP, exist_ok=True)
raw_fc, simp = os.path.join(TMP, 'attendance.geojson'), os.path.join(TMP, 'attendance_s.geojson')
json.dump({'type': 'FeatureCollection', 'features': feats}, open(raw_fc, 'w'))
# Simplified together, so neighbouring areas keep their shared edges.
subprocess.run(['npx', 'mapshaper', '-i', raw_fc, '-simplify', 'interval=20', 'keep-shapes',
                '-o', simp, 'precision=0.00001', 'format=geojson', '-quiet'], check=True, cwd=HERE)
fc = json.load(open(simp))
yr = re.search(r'SY ?(\d{2})(\d{2})', sources['elementary']['name'])
fc['year'] = '20' + yr.group(1) + '–' + yr.group(2)
json.dump(fc, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print('attendance:', {lv: sum(f['properties']['level'] == lv for f in feats) for lv in LEVELS.values()},
      'year', fc['year'], 'no profile:', missing, 'size', os.path.getsize(OUT))

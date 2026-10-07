"""Time every suburban grid point (cities/<city>/raw/drive_points.json, from engine/drive.py points) to
the city's downtown hub by car, with no traffic, using OSRM on OpenStreetMap roads.
Writes cities/<city>/raw/drive_times.json. Runs in GitHub Actions (.github/workflows/fetch-drive-times.yml).

OSRM's car profile drives at posted speeds on empty roads: free-flow times, which is what the lens shows.
Uses the public OSRM demo server politely: 100 points per table request, one request every 1.5 seconds.
Points more than 1 km from any road (lakes, fields, forest preserves) are dropped.
Usage: python3 engine/fetch_drive_times.py <city>
"""
import datetime, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
city = sys.argv[1] if len(sys.argv) > 1 else sys.exit('usage: fetch_drive_times.py <city>')
CITY = os.path.join(HERE, '..', 'cities', city)
cfg = json.load(open(os.path.join(CITY, 'city.json')))['drive']
hub_lat, hub_lon = cfg['hub']
pts = json.load(open(os.path.join(CITY, 'raw', 'drive_points.json')))['points']
OSRM = 'https://router.project-osrm.org/table/v1/driving/'
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
CHUNK, MAX_SNAP_M = 100, 1000


def table(chunk):
    coords = ';'.join(f'{x},{y}' for x, y in chunk) + f';{hub_lon},{hub_lat}'
    url = OSRM + coords + '?sources=' + ';'.join(map(str, range(len(chunk)))) + f'&destinations={len(chunk)}&annotations=duration'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                d = json.loads(r.read())
            if d.get('code') == 'Ok':
                return d
            print('  OSRM said', d.get('code'), d.get('message'))
        except Exception as e:
            print('  retry', attempt + 1, e)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError('OSRM table request failed')


out, dropped = [], 0
for i in range(0, len(pts), CHUNK):
    chunk = pts[i:i + CHUNK]
    d = table(chunk)
    for (x, y), row, src in zip(chunk, d['durations'], d['sources']):
        sec = row[0]
        if sec is None or src.get('distance', 0) > MAX_SNAP_M:
            dropped += 1
            continue
        out.append([x, y, round(sec)])
    print(f'{min(i + CHUNK, len(pts))}/{len(pts)} points')
    time.sleep(1.5)
json.dump({'hub': cfg['hubName'], 'hubAt': [hub_lon, hub_lat], 'fetched': datetime.date.today().isoformat(),
           'source': 'OSRM car profile on OpenStreetMap (router.project-osrm.org), free-flow', 'points': out},
          open(os.path.join(CITY, 'raw', 'drive_times.json'), 'w'), separators=(',', ':'))
print('wrote drive_times.json:', len(out), 'points timed,', dropped, 'dropped (off-road or unreachable)')

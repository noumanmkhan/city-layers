"""Fetch who currently holds each office the Chicago map shows, into cities/chicago/raw/representatives/.
Runs in GitHub Actions; meant to be scheduled weekly, like Toronto's.

- ward_offices.json: City of Chicago Data Portal, Ward Offices (htai-wnw4): alderperson and ward website
- il.csv: Open States' current Illinois legislators (data.openstates.org), House and Senate, with district and party
- house.xml: Clerk of the U.S. House member list (current members of Congress, with state and district)
representatives.py matches them to the map's wards and districts.
"""
import os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'representatives')
os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'city-layers/1.0 (https://maps.noumankhan.ca)'}
SOURCES = [
    ('ward_offices.json', 'https://data.cityofchicago.org/resource/htai-wnw4.json?$limit=100'),
    ('il.csv', 'https://data.openstates.org/people/current/il.csv'),
    ('house.xml', 'https://clerk.house.gov/xml/lists/MemberData.xml'),
]
failed = []
for name, url in SOURCES:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                body = r.read()
            open(os.path.join(OUT, name), 'wb').write(body)
            print('wrote', name, len(body))
            break
        except Exception as e:
            print('retry', attempt + 1, name, e)
            time.sleep(15)
    else:
        failed.append(name)
    time.sleep(2)
print('failed:', failed or 'none')
if failed:
    raise SystemExit(1)   # keep last week's files rather than commit a partial set

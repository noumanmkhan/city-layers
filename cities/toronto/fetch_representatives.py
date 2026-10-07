"""Fetch the current elected representatives for Toronto from each government's own website.
Run from GitHub Actions (weekly, and on demand); writes raw/representatives/.

  ourcommons.xml   House of Commons, current members (ourcommons.ca/Members/en/search/XML)
  ola.html         Legislative Assembly of Ontario, current members (ola.org/en/members/current)
  toronto.json     City of Toronto: the <title> of each ward councillor's page on toronto.ca
                   (councillor-ward-1 ... councillor-ward-25), which names the current councillor

Open North's Represent API was considered and not used: its House of Commons list lagged a
by-election by months. Taking names from the same pages the site links to keeps them in step."""
import json, os, re, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'representatives'); os.makedirs(OUT, exist_ok=True)
UA = {'User-Agent': 'toronto-layers-pipeline (github.com/noumanmkhan/toronto-layers)', 'Accept-Language': 'en'}
WARD = 'https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-{}/'


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(5 * (i + 1))
    raise SystemExit('failed: ' + url)


open(os.path.join(OUT, 'ourcommons.xml'), 'wb').write(get('https://www.ourcommons.ca/Members/en/search/XML'))
open(os.path.join(OUT, 'ola.html'), 'wb').write(get('https://www.ola.org/en/members/current'))
wards = {}
for n in range(1, 26):
    html = get(WARD.format(n)).decode('utf-8', 'replace')
    m = re.search(r'<title>(.*?)</title>', html, re.S)
    wards[n] = {'url': WARD.format(n), 'title': re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''}
    print(n, wards[n]['title'])
    time.sleep(1.5)   # one page at a time; the City's servers dislike bursts
json.dump(wards, open(os.path.join(OUT, 'toronto.json'), 'w'), indent=1, ensure_ascii=False)
print('done')

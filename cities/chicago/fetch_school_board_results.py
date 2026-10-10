"""Fetch Chicago Board of Education results from the Chicago Board of Elections' results pages.
Run from GitHub Actions (the *Refresh Chicago representatives* workflow, and by hand); the sandbox
can't reach chicagoelections.gov.

The results page (chicagoelections.gov/elections/results/<id>) is a Drupal form: pick a contest and
the page asks the server for it with an AJAX POST. This does the same: read the page for the form's
build id and the contest list, then post once per school board contest (the president and the 20
subdistricts) and keep the HTML fragment the server returns.

Which election: the one listed as "General Election - 11/3/2026". Until that page exists (the board
adds it close to election day) it fetches the 2024 general election (id 41) into results_probe.json
instead, so the parser in representatives.py can be tested against a real page (not when NO_PROBE
is set, as in the scheduled representatives job). Passing an
election id as the first argument fetches that one into results.json.

Official or not: the count stays unofficial until the board proclaims the results (about three weeks
later, after mail ballots). The index lists a "Proclamation of Official Results (November ..., 2026)"
link then; when it's there, "official" is true.

Writes raw/school_board/results.json: {election, title, fetched, official, contests: {contest name: html}}."""
import datetime as dt, html, json, os, re, sys, time, urllib.parse, urllib.request, http.cookiejar

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'raw', 'school_board', 'results.json')
BASE = 'https://chicagoelections.gov'
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}
TARGET = 'General Election - 11/3/2026'
WANT = re.compile(r'Chicago Board of Education', re.I)

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=dict(UA, **({'X-Requested-With': 'XMLHttpRequest'} if data else {})))
            with opener.open(req, timeout=120) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(5 * (i + 1))
    raise SystemExit('failed: ' + url)


official = False
if len(sys.argv) > 1:
    eid, title = sys.argv[1], 'election ' + sys.argv[1]
else:
    idx = get(BASE + '/elections/results')
    m = None
    for href, text in re.findall(r'<a[^>]*href="(/elections/results/\d+)"[^>]*>(.*?)</a>', idx, re.S):
        if TARGET in re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', text))):
            m = href; title = TARGET; break
    official = any('Proclamation' in t and 'November' in t and '2026' in t
                   for t in (re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', x))) for x in re.findall(r'<a[^>]*>(.*?)</a>', idx, re.S)))
    if m:
        eid = m.rsplit('/', 1)[1]
    else:
        if os.environ.get('NO_PROBE'):
            print('No results page for', TARGET, 'yet; nothing to fetch.'); sys.exit(0)
        print('No results page for', TARGET, 'yet; fetching the 2024 general (41) as a probe.')
        eid, title, OUT = '41', 'General Election - 11/5/2024 (probe)', OUT.replace('results.json', 'results_probe.json')
        official = False

page = get(f'{BASE}/elections/results/{eid}')
build = re.search(r'name="form_build_id" value="([^"]+)"', page).group(1)
contests = [(v, re.sub(r'\s+', ' ', html.unescape(t)).strip()) for v, t in re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]*)</option>', page)]
contests = [(v, t) for v, t in contests if WANT.search(t)]
print('election', eid, '-', len(contests), 'school board contests')
out = {'election': eid, 'title': title, 'fetched': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'official': official, 'contests': {}}
for v, t in contests:
    form = urllib.parse.urlencode({'election_id': eid, 'contest': v, 'ward': '', 'form_build_id': build,
                                   'form_id': 'election_results_form', 'homepage': '',
                                   '_triggering_element_name': 'submit', '_triggering_element_value': 'Submit'}).encode()
    body = get(f'{BASE}/elections/results/{eid}?ajax_form=1&_wrapper_format=drupal_ajax', data=form)
    try:
        frags = [c.get('data') for c in json.loads(body) if isinstance(c, dict) and isinstance(c.get('data'), str)]
        frag = max(frags, key=len) if frags else ''
    except ValueError:
        frag = body
    out['contests'][t] = frag
    print(' ', t, len(frag), 'tables' if '<table' in frag else 'NO TABLE')
    time.sleep(1.5)   # one request at a time
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('wrote', OUT)

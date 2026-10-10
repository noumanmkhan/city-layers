"""Fetch Chicago Board of Education district boundaries and look for the 2026 candidate list.
Run from GitHub Actions (the *Fetch Chicago data* workflow runs it when this file changes on main);
the sandbox can't reach these hosts.

  school_board_20.zip   The 20 sub-district map enacted by Public Act 103-0584 (SB 15, Senate Floor
                        Amendment 1, signed March 18, 2024), from the Illinois Senate Redistricting
                        Committee: ERSB_20_Sub_District_Map_FA1_SB_15.zip. These are the districts
                        on the November 3, 2026 ballot (1a, 1b ... 10b).
  school_board_10.zip   The 10-district map from the same act (each district = two sub-districts),
                        used in 2024. Kept as a cross-check.
  school_board/         Pages fetched while looking for the official candidate list (scouting).
"""
import os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
UA = {'User-Agent': 'Mozilla/5.0 (city-layers-pipeline; github.com/noumanmkhan/city-layers)'}
SHAPES = {
    'school_board_20.zip': 'https://ilsenateredistricting.com/images/shape-files/ERSB_20_Sub_District_Map_FA1_SB_15.zip',
    'school_board_10.zip': 'https://ilsenateredistricting.com/images/shape-files/ERSB_10_District_Map_FA1_SB_15.zip',
}
SCOUT = {
    'cboe_home.html': 'https://chicagoelections.gov/',
    'cboe_candidates.html': 'https://chicagoelections.gov/elections/candidates',
    'cboe_g2026_list.pdf': 'https://app.chicagoelections.gov/documents/news_releases/G2026-Candidate-List.pdf',
    'cboe_results.html': 'https://chicagoelections.gov/elections/results',
}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b''
        except Exception as e:
            print('  retry', i + 1, url, e); time.sleep(5 * (i + 1))
    return None, b''


for name, url in SHAPES.items():
    st, body = get(url)
    print(name, st, len(body))
    if st != 200 or not body.startswith(b'PK'):
        raise SystemExit('could not download ' + url)
    open(os.path.join(RAW, name), 'wb').write(body)

os.makedirs(os.path.join(RAW, 'school_board'), exist_ok=True)
for name, url in SCOUT.items():
    st, body = get(url)
    print(name, st, len(body))
    if st == 200 and body:
        open(os.path.join(RAW, 'school_board', name), 'wb').write(body)
    time.sleep(2)

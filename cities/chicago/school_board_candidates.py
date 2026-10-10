"""Chicago Board of Education candidates on the November 3, 2026 ballot, from the Chicago Board of
Elections' candidate list PDF (raw/school_board/cboe_candidate_list.pdf, fetched by
fetch_school_board.py) -> raw/school_board/candidates.json.

  {"source": ..., "status": "Status as of ...", "president": [names in ballot order],
   "districts": {"1a": [names in ballot order], ..., "10b": [...]}}

Run by hand after a new candidate list is fetched (needs pypdf: pip install pypdf); the JSON is
committed so the regular build doesn't need a PDF reader. Ballot order is the board's lottery order.
Write-in lines are skipped. A candidate who suspended a campaign but stays on the ballot is kept:
this is the ballot, as printed."""
import json, os, re, sys
from pypdf import PdfReader

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'raw', 'school_board', 'cboe_candidate_list.pdf')
OUT = os.path.join(HERE, 'raw', 'school_board', 'candidates.json')

text = '\n'.join(p.extract_text() or '' for p in PdfReader(SRC).pages)
status = re.search(r'Status as of [^\n]+', text)
out = {'source': 'Chicago Board of Elections, Candidate List for the November 3, 2026 General Election',
       'status': status.group(0).strip() if status else None, 'president': [], 'districts': {}}
current = None
for line in text.splitlines():
    line = line.strip()
    if line.startswith('President of the Chicago Board of Education'):
        current = out['president']; continue
    m = re.match(r'Member of the Chicago Board of Education, Subdistrict (\d+)([AB])$', line)
    if m:
        current = out['districts'].setdefault(m.group(1) + m.group(2).lower(), []); continue
    if current is None: continue
    c = re.match(r'\((\d+)\)\s+(.+?)\s+\(Nonpartisan\)\s+Candidate$', line)
    if c:
        current.append(c.group(2)); continue
    if line.startswith(('Vote for', 'Write-in', 'Ballot No.', 'Page ')): continue
    current = None   # the next office has started

missing = [f'{n}{s}' for n in range(1, 11) for s in 'ab' if not out['districts'].get(f'{n}{s}')]
if missing or not out['president']:
    sys.exit('incomplete: missing ' + ', '.join(missing or ['president']))
json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print(out['status'], '| president', len(out['president']), '| districts',
      {k: len(v) for k, v in sorted(out['districts'].items(), key=lambda kv: (int(kv[0][:-1]), kv[0][-1]))})

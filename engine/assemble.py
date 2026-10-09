"""Build one city's map page: engine/template.html + engine/map.js + cities/<city>/city.json and city.css
-> docs/<city>/index.html, plus a copy of the config at docs/<city>/data/city.json.

Usage: python3 engine/assemble.py <city>

The page stays a single file: Leaflet's stylesheet, the city's colours, its config and the engine
script are all inlined (Leaflet's JavaScript still loads from cdnjs). Text in {{double braces}} in the
template is filled from the city config, e.g. {{title}} or {{scope.outer.name}}."""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
city = sys.argv[1] if len(sys.argv) > 1 else sys.exit('usage: assemble.py <city>')
CITY_DIR = os.path.join(ROOT, 'cities', city)
read = lambda *p: open(os.path.join(*p), encoding='utf-8').read()

cfg = json.loads(read(CITY_DIR, 'city.json'))

def lookup(path):
    v = cfg
    for k in path.split('.'):
        v = v[k]   # a KeyError here names the missing config entry
    return html.escape(str(v), quote=True)

t = read(HERE, 'template.html')
t = re.sub(r'\{\{([\w.]+)\}\}', lambda m: lookup(m.group(1)), t)
# The title doubles as a switcher between every city in cities/, plus the maps hub. With one city
# it stays a plain heading.
cities = sorted((json.loads(read(ROOT, 'cities', c, 'city.json')) for c in os.listdir(os.path.join(ROOT, 'cities'))
                 if os.path.isfile(os.path.join(ROOT, 'cities', c, 'city.json'))), key=lambda c: c['title'])
title = html.escape(cfg['title'])
if len(cities) > 1:
    chev = '<svg class="chev" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    opts = ''.join('<option value="../%s/"%s>%s</option>' % (c['id'], ' selected' if c['id'] == cfg['id'] else '', html.escape(c['title'])) for c in cities)
    switch = ('<div class="switch"><h1>%s%s</h1><select id="citySwitch" aria-label="Switch map">%s'
              '<option value="../">All maps</option></select></div>') % (title, chev, opts)
else:
    switch = '<h1>%s</h1>' % title
t = t.replace('<!--CITY_SWITCH-->', switch)
t = t.replace('/*LEAFLET_CSS*/', read(ROOT, 'node_modules', 'leaflet', 'dist', 'leaflet.css'))
t = t.replace('/*CITY_CSS*/', read(CITY_DIR, 'city.css'))
# The config sits inside a <script>; escaping "</" keeps a stray "</script>" in any text from ending it.
t = t.replace('/*CITY_CONFIG*/', json.dumps(cfg, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
t = t.replace('/*ENGINE_JS*/', read(HERE, 'map.js'))
t = '<!doctype html>\n<html lang="en">\n<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + \
    t.replace('<div id="app">', '</head>\n<body>\n<div id="app">', 1) + '\n</body>\n</html>\n'

out = os.path.join(ROOT, 'docs', city, 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf-8').write(t)
print('assembled docs/%s/index.html' % city, len(t), 'bytes')

# The config is also published on its own, beside the data, for apps that read the map's data
# (see DATA_CONTRACT.md). Its "schema" number goes up only on a breaking change.
# The published copy also carries "palette": every colour variable the page defines (engine and city),
# with its light and dark value, so an app can resolve "--bia" or "--b-oldtoronto" without reading CSS.
def colours(css, selector):
    out = {}
    for block in re.findall(re.escape(selector) + r'\{([^{}]*)\}', css):
        out.update(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{3,8})\b', block))
    return out
styles = read(HERE, 'template.html') + '\n' + read(CITY_DIR, 'city.css')
light, dark = colours(styles, ':root'), colours(styles, ':root[data-theme="dark"]')
pub = dict(cfg, palette={k: {'light': v.upper(), 'dark': dark.get(k, v).upper()} for k, v in light.items()})
cfg_out = os.path.join(ROOT, 'docs', city, 'data', 'city.json')
os.makedirs(os.path.dirname(cfg_out), exist_ok=True)
open(cfg_out, 'w', encoding='utf-8').write(json.dumps(pub, ensure_ascii=False, separators=(',', ':')) + '\n')
print('published docs/%s/data/city.json' % city)

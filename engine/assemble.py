"""Build one city's map page: engine/template.html + engine/map.js + cities/<city>/city.json and city.css
-> docs/<city>/index.html.

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

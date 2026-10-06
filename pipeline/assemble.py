"""Inline Leaflet's stylesheet into the page template -> docs/index.html.
(The page loads Leaflet's JavaScript from cdnjs; the CSS is inlined so the page has one stylesheet request fewer.)"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
css = open(os.path.join(HERE, 'node_modules', 'leaflet', 'dist', 'leaflet.css')).read()
t = open(os.path.join(HERE, 'template.html')).read().replace('/*LEAFLET_CSS*/', css)
t = '<!doctype html>\n<html lang="en">\n<head>\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + \
    t.replace('<div id="app">', '</head>\n<body>\n<div id="app">', 1) + '\n</body>\n</html>\n'
open(os.path.join(HERE, '..', 'docs', 'index.html'), 'w').write(t)
print('assembled docs/index.html', len(t), 'bytes')

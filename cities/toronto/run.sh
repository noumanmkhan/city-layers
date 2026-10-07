#!/usr/bin/env bash
# Rebuild docs/toronto/data/*.geojson and docs/toronto/index.html from the inputs in cities/toronto/raw/.
# Needs: python3 with shapely; node (npm install at the repo root brings mapshaper + leaflet).
set -euo pipefail
cd "$(dirname "$0")"
[ -d ../../node_modules ] || (cd ../.. && npm install --silent)
mkdir -p tmp ../../docs/toronto/data
python3 regions.py
python3 subway.py
python3 build.py
python3 streets.py
python3 landmarks.py
python3 go.py
python3 profiles.py
OUT=../../docs/toronto/data
simplify () { npx mapshaper -i "tmp/$1.geojson" -simplify interval="$2" keep-shapes -o "$OUT/$1.geojson" precision=0.00001 format=geojson -quiet; }
simplify areas 10; simplify base 40; simplify bia 5; simplify boroughs 10
simplify federal 10; simplify neighbourhoods 10; simplify wards 10
npx mapshaper -i tmp/highways.geojson -simplify interval=6 -o $OUT/highways.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/streets.geojson -simplify interval=6 keep-shapes -o $OUT/streets.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/gta_highways.geojson -simplify interval=15 -o $OUT/gta_highways.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/go_lines.geojson -simplify interval=40 -o $OUT/go_lines.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/go_lines_416.geojson -simplify interval=40 -o $OUT/go_lines_416.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/subway_lines.geojson -simplify interval=5 -o $OUT/subway_lines.geojson precision=0.00001 -quiet
python3 representatives.py   # after the boundaries above: it matches names against them
python3 ../../engine/assemble.py
echo "Done. Preview: cd docs && python3 -m http.server 8000"

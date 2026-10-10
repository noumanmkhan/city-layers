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
python3 ../../engine/facts.py toronto   # after profiles: what makes each unit stand out
python3 ../../engine/skyscrapers.py toronto   # towers 150 m+ from raw/skyscrapers/wiki.json (fetch-skyscrapers.yml)
python3 heritage.py
python3 institutions.py       # universities, colleges, hospitals: points, written straight to docs
python3 nearby.py             # after institutions: points for the card's Nearby section
OUT=../../docs/toronto/data
simplify () { npx mapshaper -i "tmp/$1.geojson" -simplify interval="$2" keep-shapes -o "$OUT/$1.geojson" precision=0.00001 format=geojson -quiet; }
simplify areas 10; simplify base 40; simplify bia 5; simplify boroughs 10; simplify heritage 3
simplify federal 10; simplify neighbourhoods 10; simplify wards 10
npx mapshaper -i tmp/highways.geojson -simplify interval=6 -o $OUT/highways.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/streets.geojson -simplify interval=6 keep-shapes -o $OUT/streets.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/gta_highways.geojson -simplify interval=15 -o $OUT/gta_highways.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/go_lines.geojson -simplify interval=40 -o $OUT/go_lines.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/go_lines_416.geojson -simplify interval=40 -o $OUT/go_lines_416.geojson precision=0.00001 -quiet
npx mapshaper -i tmp/subway_lines.geojson -simplify interval=5 -o $OUT/subway_lines.geojson precision=0.00001 -quiet
python3 school_wards.py      # after wards are simplified: trustee wards are unions of City wards
python3 representatives.py   # after the boundaries above: it matches names against them
python3 gta_places.py        # likewise: names each community's municipality from base
[ -f raw/drive_times.json ] && python3 ../../engine/drive.py build toronto   # after base is simplified: adds drive times to it
python3 ../../engine/regions.py toronto   # outlines for Focus on a county / region
python3 ../../engine/assemble.py toronto
echo "Done. Preview: cd docs && python3 -m http.server 8000"

#!/usr/bin/env bash
# Rebuild docs/chicago/data/* and docs/chicago/index.html from the inputs in cities/chicago/raw/.
# Needs: python3 with shapely; node (npm install at the repo root brings mapshaper + leaflet).
set -euo pipefail
cd "$(dirname "$0")"
[ -d ../../node_modules ] || (cd ../.. && npm install --silent)
mkdir -p tmp ../../docs/chicago/data
python3 build.py
python3 landmarks.py
python3 profiles.py
python3 ../../engine/facts.py chicago   # after profiles: what makes each unit stand out
python3 heritage.py
OUT=../../docs/chicago/data
simplify () { npx mapshaper -i "tmp/$1.geojson" -simplify interval="$2" keep-shapes -o "$OUT/$1.geojson" precision=0.00001 format=geojson -quiet; }
npx mapshaper -i tmp/base.geojson -simplify interval=80 keep-shapes -filter-slivers min-area=20000m2 -o $OUT/base.geojson precision=0.00005 format=geojson -quiet
simplify sides 10; simplify community_areas 10; simplify wards 10
simplify il_house 10; simplify congress 10; simplify school_board 10; simplify ssa 5; simplify heritage 3
for f in highways streets; do npx mapshaper -i tmp/$f.geojson -simplify interval=6 -o $OUT/$f.geojson precision=0.00001 -quiet; done
npx mapshaper -i tmp/region_highways.geojson -simplify interval=15 -o $OUT/region_highways.geojson precision=0.00001 -quiet
for f in metra_lines metra_lines_inner; do npx mapshaper -i tmp/$f.geojson -simplify interval=40 -o $OUT/$f.geojson precision=0.00001 -quiet; done
npx mapshaper -i tmp/cta_lines.geojson -simplify interval=5 -o $OUT/cta_lines.geojson precision=0.00001 -quiet
[ -d raw/representatives ] && python3 representatives.py   # after the boundaries above: it matches them
[ -f raw/drive_times.json ] && python3 ../../engine/drive.py build chicago   # after base is simplified: adds drive times to it
python3 ../../engine/regions.py chicago   # outlines for Focus on a county / region
python3 ../../engine/assemble.py chicago
echo "Done. Preview: cd docs && python3 -m http.server 8000"

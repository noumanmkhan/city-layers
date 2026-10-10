# Skyscrapers: data scouting (October 10, 2026)

Run: `.github/workflows/scout-skyscrapers.yml` → `scouting/skyscrapers/out/` (toronto.json,
chicago.json, summary.json, scout.log). Cut-off 150 m; the scout pulled 140 m+ for margin.

## Coverage

| Source | Toronto | Chicago |
|---|---|---|
| Wikipedia "List of tallest buildings in …", main table (150 m+) | 118 rows (incl. CN Tower, unranked) | 138 rows |
| Wikipedia, under construction | 13 | 1 |
| Wikidata, 140 m+ with a height | 31 | 55 |
| Wikidata skyscrapers with no height | 40 | 79 |
| OSM buildings, height 140 m+ or 40+ levels | 102 | 154 |

Wikipedia's main tables are complete on every field the card needs: coordinates (all rows),
floors (all but one), year (all), purpose (Residential / Office / Mixed-use / Hotel), and a
Notes column that holds the "fun fact" material on 37 Toronto and 61 Chicago rows.
Wikidata is too thin to be the main source (a quarter to two fifths of the towers have a height).

## Use mix (main tables)
- Toronto: residential 83, office 19, mixed-use 14, hotel 1, CN Tower (communication/observation).
- Chicago: residential 60, office 59, mixed-use 17, hotel 2.
- Chicago's heights are standard (architectural) height; a separate table gives pinnacle heights.

## Supertall (300 m+)
- Toronto: SkyTower at Pinnacle One Yonge (351.8 m, topped off 2026, tallest in Canada),
  One Bloor West (308.9 m, topped off, listed 2028). Concord Sky (300.2 m) under construction.
  CN Tower (553.4 m) is a tower, not a building.
- Chicago: Willis, Trump International, St. Regis, Aon Center, 875 North Michigan,
  Franklin Center, Two Prudential Plaza (7).

## Notes for the build
- Source: Wikipedia tables (CC BY-SA 4.0, attribute "Wikipedia contributors"). Take the facts
  (name, coords, height, floors, year, purpose); write our own fun-fact lines rather than copy Notes.
- Status: Wikipedia's "tallest" table includes topped-out towers with a future year (One Bloor West
  2028). Treat year > current year, or the under-construction table, as under construction.
- Hotel (3 towers in all) folds into commercial, unless a fourth motif is wanted.
- CN Tower stays on Landmarks; Willis Tower is in both Landmarks (Skydeck) and the list.
- Existing Landmarks points with category "campus" (4 Toronto, 6 Chicago) overlap the Universities toggle.
- OSM ids (and Wikidata where present) can link to footprints later if wanted; points are enough.

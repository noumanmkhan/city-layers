# Transit construction road closures: data scouting (October 10, 2026)

Run: `.github/workflows/scout-closures.yml` → `scouting/closures/out/` (toronto.json, chicago.json,
summary.json, scout.log). For a "Transit under construction" layer with closures nested under it,
limited to the arterials the map already draws (`docs/<city>/data/streets.geojson`).

## Headline
- Both cities publish usable permit data, refreshed at least daily, and both send
  `Access-Control-Allow-Origin: *`, so a browser could read them live. A daily snapshot committed by
  Actions is still the better fit (works for the iOS app, one parse, no third-party outage on the page).
- Limiting to arterials keeps the map clean but hides most **full** closures: in both cities those
  are on local side streets crossing the alignment. On arterials it's almost all lane narrowing.

## Toronto: City road restrictions feed (v3 JSON)
- 2,250 records in the live feed. Not strict JSON (stray backslashes); parse after escaping them.
- Metrolinx-permitted work: 99 records (source/workEventType/permitType = "Metrolinx"), 74 active today.
  Each has a polyline, roadClass, type, daily hours, start/end, contractor, description.
- On drawn arterials: roadClass Major/Minor Arterial = 68 records; a geometry match to streets.geojson
  gives 65. roadClass alone is a good filter (Toronto draws major and minor arterials).
  Of those 68, only 3 are full closures (Jane St nightly 21:00–05:00 at Eglinton, Dupont St at Campbell,
  Scarlett Rd at Eglinton); 41 run around the clock (lane or curb occupation).
- "Metrolinx" mixes projects. Contractor tells them apart:
  - Ontario Line: Trillium Guideway Partners (elevated guideway and stations, Carlaw / Don Mills),
    Green Infrastructure Partners (Pape/Danforth instruments), Pape North Connect, Leaside Valley Builders
    (Don Valley crossing), Ontario Transit Group (downtown; some of its Queen St W permits are filed as
    "Other", not Metrolinx).
  - Eglinton West extension: West End Connectors, STRABAG (Jane and Mount Dennis portals), Aecon (Jane St,
    Scarlett Rd).
  - Line 2 East extension: Scarborough Transit Connect (Eglinton Ave E, McCowan).
  - Finch West LRT (opened): Mosaic Transit Group, Entera (aftercare).
  - GO Expansion, not subway/LRT: ONxpress (Birchmount, Stouffville line), Kiewit (Barrie line), Graham
    (St Clair W bridge), Grascan (Sheppard W bridge), Smart Tracks (Finch E grade separation),
    EllisDon LSW RER (Lakeshore West).
- Utility relocations done for these projects are filed under Toronto Hydro / Enbridge and are missed.
- End dates run to March 2027; "very short duration" instrument readings carry six-month permits.

## Chicago: CDOT Transportation Department Permits (Socrata pubx-yq2d)
- 56,685 permits active in a ten-week window. Street closure values: Full 1,409, Partial 574,
  Curblane 5,458, Sidewalk 1,350, None/NA/blank for the rest. Dates only, no hours.
- Red Line Extension: applicant "WALSH CONSTRUCTION COMPANY II, LLC" with application names
  "RLE Closures", "CTA RLE - Closures", "CTA RLE - Permanent Closures", "RLE-QLA Potholing…",
  "RLE - … Sidewalk". Filter: application name matching the word RLE or comments mentioning Red Line
  (plain "RLE" substring also hits Harlem, Orleans, Charles).
- 67 RLE rows (22 full, 3 partial, 7 curb lane; the rest sidewalk or unstated). Full closures are side streets crossing the alignment between 103rd and 116th
  (103rd Pl, 104th–114th, Princeton, Yale, Perry); many are **permanent** (permits to 2030).
  Pairs of overlapping permits cover the same segments (one to May 2027, one to 2030).
- On drawn arterials: 103rd St, 111th St and 116th St at Michigan (curb lane), State St (sidewalk).
  No full arterial closure today.
- Location is a point at the start of an address range plus from/to house numbers, no line. The
  address grid (800 numbers to the mile from State and Madison) can place the far end.
- Also in the data: CTA Red and Purple Modernization (north side, existing line rebuilt), CTA shuttles
  and events. Not new lines.

## Decisions (October 10, with the user) and what was built
- Transit under construction + road closures (October 10, commits 9c4f6df lines, e6da0d5 closures pipeline, 9c9359a page; scouting in closures-scouting.md, both cities):
  - Layer "Transit under construction" (id build, kind construction) after Subway & LRT / the 'L', off by default: dashed lines in the future line's colour, hollow stations (names from zoom 13), tap for owner, length, opening (only owner-published: Ontario Line "Early 2030s", RLE "2030"), about, project link. Toronto: Ontario Line, Line 2 East extension, Eglinton West extension, Hazel McCallion Line (Mississauga/Brampton, regional view). Chicago: Red Line Extension. Geometry from OSM (engine/fetch_construction.py, fetch-construction.yml, monthly) filtered by cities/<city>/construction.json; twin tracks folded; stations from OSM or where the line crosses a named street in streets.geojson. Yonge North isn't in OSM yet: left off until it is.
  - Nested "Road closures" / "Street closures" (id closures, kind closures, optional file): refreshed daily just after midnight New York time (fetch-closures.yml runs at 04:07 and 05:07 UTC and exits unless it's the midnight hour in New York). Toronto: City Road Restrictions live feed, permits filed as Metrolinx plus transit-only consortiums (contractor list in construction.json; Green Infrastructure Partners and Mosaic removed: they pulled in City sewer work and Finch West aftercare). Chicago: CDOT permits naming RLE/RPM as whole words, Full/Partial/Curblane only; far end placed with the 800-numbers-a-mile grid. engine/closures.py: keeps permits active today or starting within 7 days; project = nearest line being built (500 m), else nearest upgraded line (GO lines → "GO Expansion (X line)"; CTA Red/Purple → "Red and Purple Modernization"), else dropped if on an open line in "existing" (Finch West aftercare), else "other"; lane work on local streets dropped, full closures on local streets kept (shown from zoom 15); duplicates merged.
  - Look: red = closed, amber dashes = lanes narrowed, a diamond per permit from zoom 12 to 14, faint if starting within the week; popup with hours, permit dates ("not a forecast of when the road reopens"), project, permit holder, description. Panel note shows "as of <date>".
  - Decisions with the user: arterials plus side-street full closures when zoomed in; include GO Expansion (and, by the same rule, Chicago's Red/Purple Modernization: flag if the user wants it out); Finch West already on Subway & LRT, so not shown as under construction.
  - First run: Toronto 70 shown (Ontario Line 32, Line 2 East 13, Eglinton West 11, GO Expansion 14), Chicago 14 (all RLE; 11 full closures of side streets crossing the alignment).
  - Not done: closures aren't excluded from shared links or image exports (links show that day's data when opened).

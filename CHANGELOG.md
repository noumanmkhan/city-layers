# Changelog

## Since 1.1

### Both cities
- **Every bus route** (October 10): the Bus routes chips are now *All*, *Frequent*, *Express* and
  *Regular* (every other daytime route: 119 TTC, 80 CTA) in any mix, with *Overnight* on a row of its
  own as before. All draws every daytime bus route (183 in Toronto, 123 in Chicago). Route shapes were
  rebuilt so each route is a handful of lines instead of dozens of overlapping pieces (Chicago 8,472
  pieces → 391, Toronto 2,838 → 652), which keeps All quick on phones and made the file smaller.
  For the iOS app: family `reg` in `transit.json`, `allText`/`allNote` on the layer, `bus=all` in
  links; contract sections 3 and 4. Additive, schema stays 1.
- **Tap a route to see it alone** (October 10): tapping a streetcar or bus line, or its number badge,
  shows that route alone in ink with its stops while every other route fades; tapping another route
  switches to it, and the next tap anywhere else (or Escape) brings them all back without opening the
  card. A passing look, so it isn't kept in shared links.
- **Collector streets** (October 10): a toggle under Main streets, off by default,
  drawing the next tier of roads (Toronto's Collector class, 989 streets; Chicago's OSM tertiary
  roads, 272) thinner than the main streets from zoom 13, named from 15. Most bus streets that aren't
  arterials are collectors, so bus lines stop floating: 93% of the TTC's network and 88% of the
  CTA's now sits on a drawn street. Also: at zoom 15 only the stops of routes being drawn show.
  For the iOS app: new file `collectors.geojson`, `labelZoom` and `yieldLabels` on a `streets`
  layer; contract section 3. Additive, schema stays 1.
- **Streetcars and buses** (October 10), from the TTC and CTA schedules (GTFS), refreshed monthly
  by a new Action (`fetch-surface.yml`).
  - Toronto: a **Streetcars** layer after Subway & LRT, off by default: the 11 daytime routes in
    red, numbered along the line, stops from zoom 15.
  - Both cities: a **Bus routes** layer, off by default, with chips for *Frequent* (every 10 minutes
    or better each way on weekdays, 7 am to 7 pm: 43 TTC bus routes, 23 CTA), *Express* (named express
    by the agency: 28 and 20), which can be on together (express then dashed), or *Overnight* on its
    own (at least hourly each way from 2 to 4 am: Toronto's Blue Night network, 35 routes including
    the night streetcars; 17 CTA routes). Daytime streetcars stay on the Streetcars layer. Families
    are worked out from the schedule, not the agency's branding.
  - Card: a **Transit nearby** section (between Schools and Nearby): the nearest subway/'L'
    station, every streetcar and bus route with a stop within 400 m (¼ mile in Chicago), overnight
    routes, and the nearest stop. Frequent routes are filled. Each number is a button that draws the
    route on the map in ink with its stops, whichever layers are on; tapping a line on the map or
    searching a route ("29", "Dufferin", "J14") does the same. Picked routes and the families are kept
    in shared links (`routes=29,504`, `bus=freq+exp`).
- For the iOS app: new files `transit.json`, `transit_routes.geojson` (load on demand) and, in
  Toronto, `streetcars.geojson`; new layer kinds `streetcars` and `buses`, `lazy` on a layer;
  `card.transit`; contract sections 3, 4 and 5. Additive, schema stays 1.
- **Transit under construction**: a new layer after Subway & LRT / the 'L', off by default. Dashed
  lines in the future line's colour with hollow stations: the Ontario Line, the Line 2 East and
  Eglinton West extensions and the Hazel McCallion Line (regional view) in Toronto; the Red Line
  Extension in Chicago. Tap a line or station for who builds it, its length and (where the owner
  has published one) the expected opening. Lines come from OpenStreetMap, filtered by a curated
  list; Yonge North isn't mapped there yet, so it's left off.
- **Road closures** nested under it, refreshed daily just after midnight Eastern: closures (red) and
  lane restrictions (amber) from transit construction, including GO Expansion in Toronto and the
  Red/Purple rebuild in Chicago. Arterials show from zoom 12 as a small diamond, and as the stretch
  itself when zoomed in; full closures of side streets appear from zoom 15. Tap for the hours, the
  permit dates, the project and the permit holder. Toronto from the City's live Road Restrictions
  feed, Chicago from CDOT permits.
- For the iOS app: new files `construction.geojson` and `closures.geojson` (optional), new layer
  kinds `construction` and `closures`, `optional` on a layer; contract section 3. Additive, schema
  stays 1.
- **Skyscrapers**: a toggle under Landmarks with every building 150 m and taller (Toronto 117 plus
  13 under construction, Chicago 138 plus 1), from Wikipedia's tallest-buildings lists. A square
  badge per tower: its glyph and colour show use (residential, office or hotel, mixed); hollow and
  dashed until open for occupancy; a gold ring at 300 m+. Tapping one adds a block to the card:
  use, height, floors, year (or expected year), up to three facts and a Wikipedia link. Search
  finds towers by name and former name ("Vista Tower", "John Hancock").
- **Landmarks**: campus points are gone from the Landmarks layer (the Universities toggle has them,
  and search still finds U of T, TMU, UIC, IIT… through the layer's nicknames). Universities,
  Colleges, Hospitals/ERs and Skyscrapers sit indented under Landmarks, all off by default. Willis
  Tower and 875 North Michigan stay on Landmarks too.
- For the iOS app: new file `skyscrapers.geojson`, new layer kind `towers`, `aliases` on the
  Universities layer, `under` on nested layers, card step 5a; contract sections 3, 4, 5 and 11.
  Additive, schema stays 1.

### Chicago
- **Schools** section on the card: the CPS elementary, middle (where one has its own area) and high
  school whose attendance area holds the spot, with grades, straight-line distance and a link to
  the CPS profile. CPS 2025–26 boundaries from the City's Data Portal. Names and grades only.
- **Miles**: card distances (Nearby and Schools) are in miles, feet when very close, and Nearby
  counts what's within half a mile (805 m, about a 10-minute walk) instead of 1 km. Toronto stays
  in kilometres.
- For the iOS app: new file `attendance.geojson`; new `card.schools` and top-level `distance`
  (`"mi"`) in `city.json`, with `card.nearby.radius` now 805; contract sections 3, 4 and 5.
  Additive, schema stays 1.

## Version 1.1 (October 10, 2026)

Everything up to commit `b69c3a0` (the iOS app section on the maps hub) is version 1.0. Version 1.1
adds the features below to both cities. The data stays at `"schema": 1`: every change is additive,
so the iOS app keeps working as it is. The last section lists what the app would need to show them.

### Toronto
- **School board wards** layer: the 2026 trustee wards of TDSB (12), TCDSB (12), Viamonde (3) and
  MonAvenir (2), one board at a time, built from whole City wards per the City Clerk's reference
  chart. Card: a *School wards* boundary row and a trustee row per board (candidates before the
  October 26 election, then the winner, then the trustee from November 15), from the City's
  election results file, refreshed hourly on election night.
- **Lakeshore** beyond the city limits now follows OpenStreetMap's Lake Ontario, Simcoe and Scugog
  outlines instead of Natural Earth's, so Port Credit and other lakeside places are on land.

### Chicago
- **School board districts** layer: the 20 Chicago Board of Education subdistricts (1a–10b) enacted
  by Public Act 103-0584. Card: a *School board* boundary row, a member row for the district and a
  citywide president row, with candidates from the Chicago Board of Elections' list; from election
  night (November 3) the row names who leads the unofficial count, and the winner once results are
  proclaimed.

### Both cities
- **Universities, colleges and hospitals**: three toggles under Landmarks. Public or nonprofit only;
  no partnership campuses or career colleges; hospitals with an emergency department ringed. Toronto
  curated and placed by OpenStreetMap; Chicago from IPEDS and CMS. Search finds them by name.
- **Nearby** section on the card: nearest library, community centre and emergency department with
  distance, and counts of parks, playgrounds and more within 1 km.

### Engine
- New layer kinds: `boards` (several overlapping ward sets in one file, with a picker) and `places`
  (institution points by category).
- Trustee rows support a leading candidate, a citywide seat and "1 candidate".

### For the iOS app (see `app-contract/DATA_CONTRACT.md`)
- New files: `school_wards.geojson` (Toronto), `school_board.geojson` (Chicago),
  `institutions.geojson`, `nearby.json` (both).
- New in `representatives.json`: `trustees`.
- New in `city.json`: layer kinds `boards` and `places`; card `facts` rows with `boards`;
  `card.reps.trustees`; `card.nearby`.
- Contract sections: 3 (files), 4 (`boards` and `places` kinds), 5 (School wards row, Trustees,
  Nearby), 8 (trustee data), 11 (drawing `boards` and `places`).

# City Layers data contract (schema 1)

This is everything an app needs to rebuild the map's "What's here" card from the published
data, without reading the website's code. The website (this repo) is the only producer; an app is
a read-only consumer. Last updated October 10, 2026 (Nearby section and `nearby.json`; institution points: the `places` layer kind and `institutions.geojson`; school boards in both cities: the `boards` layer kind, a School wards / School board row and trustee rows, with Chicago's leader and citywide president; earlier: map layers and `palette`, section 11; card title names the neighbourhood; profile facts; Chicago's To the Loop fields).

## 1. Ground rules

- **Read only from the published site**, never from GitHub:
  `https://maps.noumankhan.ca/<city>/data/<file>`, where `<city>` is `toronto` or `chicago`.
- **Start with `city.json`** for each city. It says which files exist, which layers the card tests,
  what the card rows say and how lens tiers are labelled. Don't hard-code layer ids, file names or
  labels in the app; read them from `city.json` so a new city works without an app update.
- **Check `schema`.** `city.json` has `"schema": 1`. If an app sees a number it doesn't know, it
  should keep using its last good copy and ask the user to update, not crash.
  - Adding a field, a file, a layer or a card row is **not** a breaking change. Ignore unknown keys.
  - Renaming or removing a field or file, or changing a field's meaning or units, **is**, and bumps
    the number.
- **Caching.** GitHub Pages serves with about a 10-minute cache. The data changes rarely
  (representatives weekly at most, everything else on rebuilds), so caching for a day and
  refreshing in the background is fine. Bundle a copy in the app for offline use.
- **Sizes.** Each city is about 2 MB of JSON in all (largest: Chicago's `base.geojson`, 0.8 MB).

## 2. The rules the data comes with (not negotiable)

- **Describe, don't rank.** The card describes the place the user picked. Demographic fields
  (language at home, and anything similar added later) never feed rankings, colours, filters,
  "best/worst" lists, notifications or comparisons.
- The lens tiers (`cost`, `commute`, `tenure`, `unionBand`, `loopBand`) and the profile `facts`
  (section 7) are the only precomputed comparisons. Show tiers with their labels and notes from
  `city.json`, and facts with their own text. Don't compute other rankings or superlatives in the
  app; facts never use demographic fields, and the app shouldn't either.
- Always show the caveat lines from `city.json` (`card.living.caveat`, `footer`, the language
  `note`) wherever the figures appear, including widgets, even if shortened.
- Show `attribution` from `city.json` somewhere in the app (an About screen is fine).
- No crime, school scores or other evaluative data on the card.

## 3. Files

All coordinates are WGS84. GeoJSON positions are `[longitude, latitude]`; most other places in
`city.json` use `[latitude, longitude]` (noted below). Polygons may be `Polygon` or
`MultiPolygon` and may have holes.

| File | What it is |
|---|---|
| `city.json` | The city's config (section 4). |
| `base.geojson` | Outline shapes. `properties.kind`: `city` (the city itself), `neighbour` (each surrounding municipality, with `name`, `region`, `lp`, `drive`), `outside` (land beyond the region). |
| `regions.geojson` | Label points for regions/counties. Not needed for the card. |
| Layer files | One per map layer, named by `file`/`files` in `city.json` `groups`. Section 5 lists the ones the card uses. |
| `nbhd_profiles.json` / `ca_profiles.json` | Census figures per neighbourhood / community area. File name is `lens.file` in `city.json`. Section 7. |
| `representatives.json` | Who holds each seat. Section 8. |
| `drive_grid.json` | Free-flow drive minutes to the hub on a ~1.5 km grid, outside the city. Section 6. |
| `region_places.json` | Toronto only: ~470 named GTA communities. `[{name, muni, region, kind, at:[lon,lat]}]`. |
| `region_areas.geojson` | Region/county outlines for the regional view. Not needed for the card. |
| `nearby.json` | Points for the card's Nearby section: `{groups: {key: [[lon, lat, name?], …]}}`. Keys and labels come from `card.nearby` (section 5). Named kinds (`library`, `centre`, `er`) carry a name; counted kinds (`park`, `playground`, …) are bare points. |
| `institutions.geojson` | Universities, colleges and hospitals (points) for the `places` layers. `properties`: `name`, `cat` (`university`, `college`, `hospital`), `sub` (campus, network or ownership, optional), `ed` (true for a hospital with an emergency department). Curated by fixed rules (public or nonprofit only; see each city's `institutions.py`). Describe only: no ratings. |

Properties that appear on many features: `name`, `lp` (a label point, `[lon, lat]`), `code`
(a unit number), `num` (a ward or district number).

### Point layers used for search

- **Landmarks** (the `landmarks`-kind layer; file `landmarks.geojson`): ~40 curated points per
  city. Properties: `name`, `cat` (`park`, `music`, `culture`, `sports`, `campus`, `civic`,
  `airport`), `catLabel` (display text, e.g. "Sports venue"), `tier` (display priority; 1 is
  most prominent), `aliases` (other names people search for, e.g. "Air Canada Centre" for
  Scotiabank Arena; may be empty).
- **Known-as names** (the `knownas`-kind layer; `cultural.geojson` in Toronto,
  `knownas.geojson` in Chicago): `name` and `kind` (`district`, `village`, `enclave`).
- **Units** (the `units`-kind layer): `name` and `code`.
- **`region_places.json`** (Toronto only): see the table above; an entry may also have `alt`,
  a list of other names.

How the website's search does it, for an app that wants to match:

- Searched locally as you type: landmarks (name and `aliases`), the names in `fill` layers
  (former cities, Old Toronto areas, Chicago's sides), units, known-as names, neighbouring
  municipalities (`base.geojson` `neighbour` features), and `region_places` (name and `alt`).
- Matching ignores case, spacing and punctuation ("Yonge-St. Clair" finds "Yonge-St.Clair").
  An exact match ranks above a prefix match, which ranks above a match at the start of any word.
  At most 6 results.
- A result found through an alias shows its canonical `name`, with "also called {alias}"
  beneath. Choosing it titles the card with the canonical name.
- Street addresses are looked up only when the user presses Find, never as they type.

## 4. city.json: the parts an app uses

- `id`, `schema`, `title`, `locale` (`en-CA` or `en-US`, for number and date formatting).
- `units.singular` / `units.plural`: what the city calls its units ("Neighbourhood",
  "community areas").
- `footprint`: the id of the layer that outlines the city. A point outside it gets the
  "outside the city" card.
- `groups`: `[[groupName, [layer, …]], …]`. Each layer has `id`, `kind`, `name`, `note`, and
  `file` (one file, add `.geojson`) or `files` (several). Kinds the card tests a point against:
  `fill`, `units`, `outline`, `patches`, `districts`, and `boards` (below). The `knownas` kind is a
  point layer used by distance (step 4 below). Other kinds are map drawing only.
- A `boards` layer (`school` in both cities: Toronto's file `school_wards`, Chicago's `school_board`) holds several overlapping sets of
  wards in one file, one set per school board. Each feature has `board` (an id), `num` (the
  board's ward number, a string), `area` (a ward name, French boards only, e.g. "Est"), `wards`
  (the City wards it is made of) and `lp`. The layer's `boards` lists `[id, short, long]` per board
  in display order (`["tdsb", "TDSB", "Toronto District School Board"]`); the first is the one the
  map shows by default. Chicago has one board (`cps`, the Chicago Board of Education; `num` "1a" …
  "10b"), so there is nothing to pick. Templates on this layer can use `{short}` and `{long}` as well as the
  feature's fields.
- A `places` layer draws the points of `file` whose `cat` equals the layer's `cat` (several layers
  share `institutions.geojson`). `place` names the kind of place ("Hospital", "City College"),
  `edText` the extra hover words for a feature with `ed`. Not part of the card.
- `card`: `pills`, `facts`, `living`, `reps` (section 6).
- `lens.file` (the profiles file) and `lens.lenses`: each has `key` (the profile field holding a
  tier id) and `tiers: [[tierId, label, colourVariable], …]`. Use the label; the colour variable
  resolves through `palette`.
- `palette`: every colour the website uses, keyed by its CSS variable name with the leading `--`
  (`"--bia": {"light": "#E0791A", "dark": "#F39A45"}`). Every colour reference elsewhere in
  `city.json` (a fill layer's `colors`, a pill's `color`, a lens tier) is a key here. Only the
  published copy has it; the website builds it from its stylesheets. Use it rather than copying
  hex values into the app, so a colour change on the website reaches the app with the data.
- `drive`: `hub` (`[lat, lon]`) and `hubName` ("Union Station", "State & Madison").
- `outside`: `beyond` (message when the point is outside the whole region), `regionPill`
  (template for the region name), `note` (shown on outside cards).
- `regionPlaces` (Toronto only): `file`, and `near`, the place kinds used for a "Near …" pill.
- `attribution`.

Pill colours on the card: a `{"layer": A, "else": B}` pill takes the colour of whichever layer
matched, from that layer's `colors[name]`; a `{"layer", "text", "color"}` pill uses its `color`;
a known-as pill is `--cult-enclave`; anything without a colour is `--ink-3`. Outside the city:
"Near …" is `--cult-enclave`, the municipality `--land-out-line`, the region `--muni-label`.
Pill background `--pill-bg`, text `--ink`.

### Text templates

Card text in `city.json` is a template, filled from a feature's properties:

- `{name}` inserts a field. `{f.num}` and `{r.party}` walk into nested objects (`f` = the feature's
  properties, `r` = the representative record).
- A list value becomes `a, b`.
- A part in `[square brackets]` is dropped if any field inside it is missing or empty. A missing
  field outside brackets blanks the whole text (the row then shows its `empty` text, or `—`).

Example: `"{name}[ (designated {since})]"` gives "Cabbagetown South (designated 2005)", or just the
name when `since` is missing.

## 5. Building the "What's here" card for a coordinate

Point-in-polygon: even-odd ray casting on each ring; a point is inside a polygon if it is inside
the outer ring and not inside any hole; inside a MultiPolygon if inside any of its polygons. The
first matching feature in file order wins.

1. **Load** `city.json`, then every file the layers name, the profiles file, `representatives.json`,
   and (if present) `drive_grid.json` and `region_places.json`.
2. **Inside the city?** Test the point against the `footprint` layer.
   - **No:** find the `base.geojson` feature with `kind: "neighbour"` that contains the point.
     - None found: show `outside.beyond`. Done.
     - Found: title is the municipality `name`. Pills: "Near {place}" (Toronto: the nearest
       `region_places` entry whose `kind` is in `regionPlaces.near`, within 2.5 km, skipped if it
       is already the title), the municipality name, and `outside.regionPill` filled with
       `{region}`. Then the drive row (section 6) and `outside.note`. Done.
   - **Yes:** carry on.
3. **Hits.** For every layer whose kind is `fill`, `units`, `outline`, `patches` or `districts`,
   find the feature containing the point. Store as `hits[layerId]` (may be empty). For a `boards`
   layer, find one feature per board instead: `hits[layerId][board]`.
4. **Known-as names.** From the `knownas`-kind layer (points), take those within 650 m, nearest
   first, at most N, where N is the `knownas` number in the pill config (`{"knownas": 2}`).
5. **Pills** (`card.pills`, in order):
   - `{"knownas": N}`: one pill per known-as name from step 4.
   - `{"layer": A, "else": B}`: the name of `hits[A]`, or if none, of `hits[B]`.
   - `{"layer": A, "text": T}`: `T` filled from `hits[A]`, only if there is a hit.
6. **Boundaries** (`card.facts`, in order), each a label and a value:
   - Skip a row with `onlyInside: true` unless its layer has a hit.
   - `knownas: true`: the known-as names from step 4, comma-separated, or `—`.
   - `boards: layerId`: for each board in that layer's `boards` order that has a hit, `text` filled
     from the hit plus `{short}`/`{long}`, joined with " · " ("TDSB 7 · TCDSB 9 · Viamonde 3 ·
     MonAvenir 3"); `—` if none.
   - Hit: `text` filled from the hit.
   - No hit: if `emptyWithin` is `{layerId: name}` and that layer's hit has that name, `—`;
     otherwise `empty`, or `—`.
7. **Standout** (optional line under the pills): if the unit's profile has `facts`, show the first
   one as "{profile name}: {text, first letter lower-cased}" followed by its `value` in smaller
   type. Section 7.
8. **Living here**: look up the profile by `hits[unitsLayerId].properties.code` (as a string key).
   Section 7.
9. **Representatives** (`card.reps.offices`, in order). Skip the whole section if the first
   office's layer has no hit. For each office: `h = hits[office.layer]`;
   `r = representatives[office.table][String(h.properties[office.key])]`. Row label `role`;
   value `r.name` linking to `r.url` (no record or no name: "Seat currently vacant"); subline
   `office.sub` filled with `{f: h.properties, r: r}`. Footer `card.reps.note` with `{date}` =
   `representatives.updated` written as a long date.
   **Trustees** (`card.reps.trustees`, after the offices): skip if
   `representatives[trustees.table]` is missing. For each board of layer `trustees.layer` with a
   hit `h` (in `boards` order): `r = representatives.trustees[board][h.num]`; label `role` filled
   from `h` plus `{short}`; `ward` = `trustees.ward` filled the same way. Value, by date (dates are
   `trustees.election` and `trustees.starts`, `YYYY-MM-DD`, Toronto time):
   - `r.winner` and today ≥ `starts`: the winner's name; subline `ward`.
   - `r.winner` before `starts`: the name; subline `ward` · `acclaimed` (if `r.acclaimed`) or
     `elected`, filled with `{election}` and `{starts}` as short dates ("Oct 26").
   - No winner but `r.leader` and the config has `leading` (Chicago): the leader's name; subline
     `ward` · `leading`.
   - Otherwise: `race` (before `election`) or `counting` (from `election` on), filled with
     `{n}` = number of candidates, `{s}` = "s" unless n is 1 (templates write `candidate[{s}]`) and
     the dates; the candidate names (`r.candidates`, ballot order) on expand; subline `ward`.
   Then, if `trustees.citywide` is set ({board, key, role, sub}) and at least one board row was
   shown: one more row, label `role`, record `representatives.trustees[board][key]` (Chicago's
   board president), subline `sub`, same rules.
   Names are plain text (no official page yet). Append `trustees.note` to the footer.
   **Nearby** (`card.nearby`, both cities): for each `[key, label]` in `nearest`, the nearest point
   of `nearby.groups[key]` by straight-line distance: row `label`, value its name, subline the
   distance ("600 m away"; to the nearest 50 m under a kilometre, then "1.8 km"). Then one row,
   label `within`, value the count of points of each `[key, one, many]` in `counts` within
   `radius` metres, "19 parks · 7 playgrounds …" (`one` when the count is 1). Footer `note`, always
   shown. Counts only: never a score, ranking or "best". The website shows this section between
   Living here and Representatives.
10. **Title**: the searched place's name if there is one. Otherwise (a dropped pin): the name of
   `hits[unitsLayerId]` (the neighbourhood / community area); failing that, the first `fill`-kind
   layer's hit; coordinates (`43.6681° N, 79.3669° W`) only for a spot no layer covers.
   The standout line (step 7) drops its "{profile name}: " prefix when the title is that name.

The website shows the standout line under the pills, then four collapsible sections in this
order: Boundaries, Living here, Nearby, Representatives.

### Worked example (Toronto, 43.66810, -79.36690)

Computed from the October 8, 2026 data. Use it as a first test case.

- **Pills:** Downtown · Cabbagetown · St. James Town · Votes in Toronto Centre (no BIA here).
- **Boundaries:** Former city: Old Toronto · Area: Downtown · Neighbourhood:
  Cabbagetown-South St.James Town (#71) · Known as: Cabbagetown, St. James Town (263 m and
  609 m away) · Heritage district: Cabbagetown (Metcalfe) (designated 2002) · BIA: None ·
  City ward: Ward 13 · Toronto Centre · Provincial: Toronto Centre · Federal: Toronto Centre ·
  School wards: TDSB 7 · TCDSB 9 · Viamonde 3 · MonAvenir 3.
- **Living here** (profile `"71"`): Housing: Middle housing cost, median home $950K · rent
  $1,330/mo · To Union: 30–45 min, about 32 min by transit · Getting to work: Mostly transit,
  walk or bike, 31% drive · 27% transit · 38% walk or bike · Households: A mix, 55% rent ·
  Home types: Detached 3% · Semi & row 18% · Low-rise 28% · Towers 52% · Built: 1960 or before
  41% · 1961–80 27% · 1981–2000 23% · 2001–21 9% · Language at home: English 84%, no other
  language above 5%, "Another 3% name two or more equally."
- **Representatives:** read from `representatives.json` (`wards["13"]`, `prov["Toronto Centre"]`,
  `fed["Toronto Centre"]`), then trustees from `trustees.tdsb["7"]`, `trustees.tcdsb["9"]`,
  `trustees.viamonde["3"]`, `trustees.monavenir["3"]`.

Note the unit's map name (`Cabbagetown-South St.James Town`) and its profile `name`
(`Cabbagetown-South St. James Town`) differ slightly; the Neighbourhood row uses the map's, the
Living here footer the profile's. The live page,
`https://maps.noumankhan.ca/toronto/#pin=43.66810,-79.36690`, shows the same card; if they ever
disagree, the live page is right.

## 6. Drive time (outside the city only)

`drive_grid.json`: `{hub, date, spacing_km, points: [[lon, lat, minutes], …]}`. Take the nearest
point; if it is more than 2 km away, show nothing. Row: "Drive to {hubName}: about {minutes} min
from here", plus "Typical for {municipality}: {drive} min" from the `base.geojson` feature's
`drive` (skip if missing or if the feature has `rest: true`). Always show the caveat: "With no
traffic, at posted speeds. Most trips take longer." Tiers: under 30, 30–60, 60–90, 90+ minutes.

## 7. Profiles (Living here)

Keyed by unit code as a string (`"71"`). Fields:

| Field | Meaning |
|---|---|
| `name` | Unit name. |
| `value` | Median home value, dollars. Shown as `$800K`, `$1.2M`. |
| `rent` | Median rent, dollars per month. |
| `renterPct`, `carPct`, `transitPct`, `walkBikePct` | Whole-number percentages. |
| `cost`, `commute`, `tenure` | Tier ids; labels come from `lens.lenses` (match `key`). |
| `union`, `unionBand` | Toronto only: transit minutes to Union, weekday 8–9 am, and its tier. |
| `loop`, `loopBand` | Chicago only: transit minutes to the Loop (quickest of five Loop arrival points), weekday 8–9 am, and its tier. Same tier ids as `unionBand`. |
| `homes` | 4 shares (%) of home types, in the order of `card.living.homes.types`. |
| `built` | 4 shares (%) by period built, in the order of `card.living.built.bands`. |
| `lang` | Up to 5 `[language, pct]`, largest first. Demographic: card only. |
| `langMulti` | Toronto only: % naming two or more languages equally. |
| `homesTier` | Not stored; the website computes it. Apps don't need it. |
| `facts` | Optional. Up to 3 ways the unit stands out among its peers, strongest first: `[{text, field, end, scope, rank, of, value}]`. `text` is a finished sentence fragment ("Highest rents in North York", "Among the most affordable homes on the South Side"); `value` is the figure behind it ("median $1,660/mo"). `field` is one of `value`, `rent`, `renterPct`, `transitPct`, `walkBikePct`, `carPct`, `detached`, `large`, `oldest`, `newest`, `hub`; `end` `high`/`low`; `scope` `city` or `peers` (the unit's former city, Old Toronto area or side); `rank` (1–3) of `of` units. Built by `engine/facts.py` from non-demographic fields only. Units that don't stand out have no `facts`. |

Rows, in order (labels from `card.living`):

1. **Housing**: cost tier label · "Median home $800K · rent $1,320/mo" · `caveat`.
2. **`hub`** (when the city's transit-time field is present): its tier label · `hubText` with
   `{minutes}`. The field is the lens in `lens.lenses` that has `minutes` (`union` in Toronto,
   `loop` in Chicago); its `key` names the tier field.
3. **Getting to work**: commute tier label · "72% drive · 24% transit · 3% walk or bike".
4. **Households**: tenure tier label · "35% rent".
5. **Home types** and **Built**: a small stacked bar, then each share of 1% or more in words
   ("Detached 37% · Semi & row 16% · …").
6. **Language at home**: the first language always; the 2nd and 3rd only at `floor`% or more
   (5). If only one shows, add "No other language above 5%". Then `note`, filled with
   `{multi}` = `langMulti` (the bracketed part drops when it's missing).
7. Footer: `footer` filled with `{name}`.

Sources: Toronto 2021 Census (City of Toronto Neighbourhood Profiles); Chicago American Community
Survey 2020–2024. Neither is current pricing; the caveat says so and must stay.

## 8. Representatives

`{updated: "YYYY-MM-DD", <table>: {<key>: {name, url, party?}}}`. Tables and keys come from
`card.reps.offices`. Toronto: `wards` (by ward number), `prov` and `fed` (by riding name).
Chicago: `wards`, `house`, `senate`, `congress` (by number). A missing record means a vacant seat.
Checked weekly. Toronto's municipal election is October 26, 2026; new councillors appear within a
week of taking office (November 15).

Toronto also has `trustees: {board: {wardNum: {candidates: [name, …], winner?, acclaimed?}}}` for
the four school boards (`tdsb`, `tcdsb`, `viamonde`, `monavenir`), from the City's election results
file. `winner` appears once every poll in that ward has reported, or straight away for a ward with
one candidate (`acclaimed: true`). Results are unofficial until the City Clerk certifies them.
Around the election the file is refreshed hourly on election night and daily until November 16.
There are no incumbent trustees in this data: TDSB's wards were redrawn for 2026, so the trustees
in office until November 15 sat on different lines.

Chicago has `trustees: {cps: {"1a": …, "10b": …, "president": {candidates, leader?, winner?}}}` for the
Chicago Board of Education election on November 3, 2026 (20 subdistricts and a citywide president;
terms start January 15, 2027). Candidates come from the Chicago Board of Elections' candidate list.
Its results pages give no "all precincts reported" signal and mail ballots are counted for two weeks,
so on and after election night only `leader` is set; `winner` appears once the board proclaims the
results (about three weeks later). Illinois has no acclamation: a sole candidate is still on the
ballot and shows as "1 candidate". The current board (10 elected in 2024, 11 appointed) isn't shown.

## 9. Not in this data

Real-time data (weather, air quality, traffic, beach water quality, transit arrivals) is not
published here. An app fetches it from its own sources and keeps it visibly separate from the
card's census and boundary data, with its own source line.

## 10. Changes

The website's maintainer updates this file whenever the published data changes shape. A breaking
change bumps `schema` in `city.json` and gets a new section at the top of this file saying what
changed and how to migrate.

## 11. Drawing the boundary layers on a map

The website draws its layers with Leaflet on a plain base. This section gives what an app needs
to draw the same boundary layers on another map (Apple's MapKit, for the iOS app): which layers,
their geometry, and how the website styles and labels them. Transit lines, streets, highways,
landmarks and the lenses are not covered here yet.

### Which layers

Every layer in `groups` whose `kind` is `fill`, `units`, `districts`, `outline`, `boards`, `patches`
or `knownas`. Keep the group order and use `name` and `note` for the layer list. A layer with
`"on": true` starts switched on. Today that gives:

| City | Layer (`id`, kind) | File |
|---|---|---|
| Toronto | Former cities (`boroughs`, fill major) | `boroughs` |
| | Old Toronto areas (`areas`, fill minor) | `areas` |
| | Neighbourhoods (`nbhd`, units) | `neighbourhoods` |
| | Known-as names (`cultural`, knownas) | `cultural` |
| | Heritage districts (`heritage`, districts) | `heritage` |
| | City wards (`wards`, outline city) | `wards` |
| | Provincial ridings (`prov`, outline state) | `wards` (see below) |
| | Federal ridings (`fed`, outline national) | `federal` |
| | School board wards (`school`, boards) | `school_wards` (one board at a time, see below) |
| | Business Improvement Areas (`bia`, patches) | `bia` |
| Chicago | The sides (`sides`, fill major) | `sides` |
| | Community areas (`ca`, units) | `community_areas` |
| | Known-as names (`knownas`, knownas) | `knownas` |
| | Landmark districts (`heritage`, districts) | `heritage` |
| | City wards (`wards`, outline city) | `wards` |
| | Illinois House districts (`house`, outline state) | `il_house` |
| | Congressional districts (`congress`, outline national) | `congress` |
| | School board districts (`school`, boards) | `school_board` |
| | Special Service Areas (`ssa`, patches) | `ssa` |

Read these from `city.json`; the table is a snapshot, not a list to hard-code.

### Geometry

- Each layer's `file` plus `.geojson`. Polygons are `Polygon` or `MultiPolygon`, **with holes**
  in every file above (Toronto's `areas` has 10, Chicago's `ssa` 23). Drawing an outer ring alone
  fills the holes and puts the wrong colour over the place inside. In MapKit, `MKGeoJSONDecoder`
  returns `MKPolygon` / `MKMultiPolygon` with `interiorPolygons` set, and each feature's
  properties as JSON `Data`. SwiftUI's `MapPolygon(coordinates:)` takes one ring and cannot
  draw holes.
- Toronto's provincial ridings reuse `wards.geojson`: in Toronto each ward is exactly one
  provincial riding. Same shapes as the ward layer, labelled with `{prov}` and styled as `state`.
- Several layers share edges (wards, ridings, neighbourhoods). The website just strokes each
  polygon; there is no separate line file.
- Sizes: 2,000–13,000 vertices per layer, 4–280 KB. Decode once per city off the main thread
  and keep the shapes; switching a layer on or off adds or removes them, it doesn't re-read.

### How the website draws them

Colours are `palette` keys (light / dark resolved there). Widths are in screen points. Drawing
order, bottom to top, is the table's order.

| Kind | Fill | Stroke | Label (at `lp`) | Label shows from zoom |
|---|---|---|---|---|
| `fill`, size `major` | `colors[name]`, opacity 0.55 | `--city`, 2 (a pale gap between areas) | `name`, 15 pt heavy, `--ink` | 10; fades to 35% from 13 |
| `fill`, size `minor` | `colors[name]`, opacity 0.6 | `--city`, 2 | `name`, 13 pt bold, `--ink` | 11 |
| `patches` | `--bia`, opacity 0.45 | `--bia`, 1.2 | `label` template, 10 pt semibold, `--bia` | 14 |
| `districts` | `--hd`, opacity 0.14 | `--hd`, 1.6, dashed 4 on / 3 off | `label` template, 10 pt semibold italic, `--hd` | 14 |
| `units` | none | `--nbhd`, 0.9, at 70% opacity | `name`, 10.5 pt medium, `--ink-2`, wraps at ~120 pt | 13 |
| `outline`, level `national` | none | `--fed`, 2.2 | `label` template, 11 pt bold, `--fed` | 11 |
| `outline`, level `state` | none | `--prov`, 2, dashed 6 on / 4 off | `label` template, 11 pt bold, `--prov` | 11 |
| `outline`, level `city` | none | `--ward`, 2.2 | `label` template, 11 pt bold, `--ward` | 11 |
| `boards` | none | `--sbw`, 2.6, dashed 9 on / 4 off | `label` template, 11 pt bold, `--sbw` | 11 |
| `knownas` | (points: label only) | | `name`, 11.5 pt semibold italic, `--cult`; `kind: "enclave"` uses `--cult-enclave` | 12 |

- `places` layers (institutions): an icon per point, from zoom 11, the name beside it from zoom 14,
  coloured `--in-university`, `--in-college`, `--in-hospital`; a hospital with `ed` gets a heavier
  ring. Tapping one opens the card for that spot, titled with its name. The website's search also
  suggests them by name.
- A `boards` layer draws only the features of one board at a time, chosen by the user (a row of
  `short` names under the layer; the default is the first). The website keeps the choice in links
  as `board=school:tcdsb`.
- Fill colours come from the layer's `colors` map by feature `name` (the same map that colours the
  first pill on the card). A name missing from the map uses `--ink-3`.
- Labels have no box; the website gives them a soft halo in `--city` so they read over lines.
- **Zoom** is the web-map zoom. From a MapKit region:
  `zoom = log2(360 × mapWidthInPoints / (256 × region.span.longitudeDelta))`.
  On a 390 pt-wide phone, zoom 11 ≈ 0.27° of longitude across, 13 ≈ 0.067°, 14 ≈ 0.034°.
- **Label collisions.** When labels overlap, the website keeps them in this order and hides the
  later one: known-as names, Old Toronto area names, unit names, ward / riding / district / school ward numbers,
  BIA / SSA names, heritage / landmark district names. (Former-city / side names are not in the
  list: they always show.) In MapKit, map this order onto annotation `displayPriority`.
- Tapping anywhere still opens the "What's here" card for that point (section 5); the drawn
  layers never change what the card says.

### Adapting to Apple's map

The website draws on its own pale base; Apple's map has roads, labels and points of interest of
its own. The values above are the website's. These adjustments are the app's to make and tune on
a real phone:

- Add overlays at the `aboveRoads` level so Apple's place and street names stay on top and
  readable. Use the muted map style and hide Apple's points of interest.
- The fill opacities (0.55, 0.6, 0.45) assume a blank base. Over Apple's map, start near 0.25 for
  `fill` and `patches`, and keep strokes as they are.
- Apple already labels many neighbourhoods. Draw unit labels only when the units layer is on,
  give them the lowest priority, and drop any whose text matches the place name Apple shows there,
  if that can be detected; otherwise accept occasional doubles and test.
- Rebuild or redraw overlay renderers when the appearance switches between light and dark, so the
  colours follow; renderers don't always pick up a dynamic colour change on their own.

### Check

Toronto, 43.66810, -79.36690 (the worked example in section 5) sits inside the Downtown fill
(`--a-downtown`), in Ward 13, inside the Cabbagetown (Metcalfe) heritage district, and outside
any BIA. `https://maps.noumankhan.ca/toronto/#pin=43.66810,-79.36690` shows the same; turn the
layers on there to compare.

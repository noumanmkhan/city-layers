# City Layers data contract (schema 1)

This is everything an app needs to rebuild the map's "What's here" card from the published
data, without reading the website's code. The website (this repo) is the only producer; an app is
a read-only consumer. Last updated October 8, 2026 (search: landmark and known-as fields).

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
- The lens tiers (`cost`, `commute`, `tenure`, `unionBand`) are the only precomputed comparisons,
  and they are shown with their labels and notes from `city.json`.
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
  `fill`, `units`, `outline`, `patches`, `districts`. The `knownas` kind is a point layer used by
  distance (step 4 below). Other kinds are map drawing only.
- `card`: `pills`, `facts`, `living`, `reps` (section 6).
- `lens.file` (the profiles file) and `lens.lenses`: each has `key` (the profile field holding a
  tier id) and `tiers: [[tierId, label, colourVariable], …]`. Use the label; the colour variable
  is a website CSS name and can be ignored or mapped to the app's own palette.
- `drive`: `hub` (`[lat, lon]`) and `hubName` ("Union Station", "State & Madison").
- `outside`: `beyond` (message when the point is outside the whole region), `regionPill`
  (template for the region name), `note` (shown on outside cards).
- `regionPlaces` (Toronto only): `file`, and `near`, the place kinds used for a "Near …" pill.
- `attribution`.

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
   find the feature containing the point. Store as `hits[layerId]` (may be empty).
4. **Known-as names.** From the `knownas`-kind layer (points), take those within 650 m, nearest
   first, at most N, where N is the `knownas` number in the pill config (`{"knownas": 2}`).
5. **Pills** (`card.pills`, in order):
   - `{"knownas": N}`: one pill per known-as name from step 4.
   - `{"layer": A, "else": B}`: the name of `hits[A]`, or if none, of `hits[B]`.
   - `{"layer": A, "text": T}`: `T` filled from `hits[A]`, only if there is a hit.
6. **Boundaries** (`card.facts`, in order), each a label and a value:
   - Skip a row with `onlyInside: true` unless its layer has a hit.
   - `knownas: true`: the known-as names from step 4, comma-separated, or `—`.
   - Hit: `text` filled from the hit.
   - No hit: if `emptyWithin` is `{layerId: name}` and that layer's hit has that name, `—`;
     otherwise `empty`, or `—`.
7. **Living here**: look up the profile by `hits[unitsLayerId].properties.code` (as a string key).
   Section 7.
8. **Representatives** (`card.reps.offices`, in order). Skip the whole section if the first
   office's layer has no hit. For each office: `h = hits[office.layer]`;
   `r = representatives[office.table][String(h.properties[office.key])]`. Row label `role`;
   value `r.name` linking to `r.url` (no record or no name: "Seat currently vacant"); subline
   `office.sub` filled with `{f: h.properties, r: r}`. Footer `card.reps.note` with `{date}` =
   `representatives.updated` written as a long date.
9. **Title**: the searched place's name if there is one, otherwise the coordinates
   (`43.6681° N, 79.3669° W`).

The website shows three collapsible sections in this order: Boundaries, Living here,
Representatives, under the pills.

### Worked example (Toronto, 43.66810, -79.36690)

Computed from the October 8, 2026 data. Use it as a first test case.

- **Pills:** Downtown · Cabbagetown · St. James Town · Votes in Toronto Centre (no BIA here).
- **Boundaries:** Former city: Old Toronto · Area: Downtown · Neighbourhood:
  Cabbagetown-South St.James Town (#71) · Known as: Cabbagetown, St. James Town (263 m and
  609 m away) · Heritage district: Cabbagetown (Metcalfe) (designated 2002) · BIA: None ·
  City ward: Ward 13 · Toronto Centre · Provincial: Toronto Centre · Federal: Toronto Centre.
- **Living here** (profile `"71"`): Housing: Middle housing cost, median home $950K · rent
  $1,330/mo · To Union: 30–45 min, about 32 min by transit · Getting to work: Mostly transit,
  walk or bike, 31% drive · 27% transit · 38% walk or bike · Households: A mix, 55% rent ·
  Home types: Detached 3% · Semi & row 18% · Low-rise 28% · Towers 52% · Built: 1960 or before
  41% · 1961–80 27% · 1981–2000 23% · 2001–21 9% · Language at home: English 84%, no other
  language above 5%, "Another 3% name two or more equally."
- **Representatives:** read from `representatives.json` (`wards["13"]`, `prov["Toronto Centre"]`,
  `fed["Toronto Centre"]`).

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
| `homes` | 4 shares (%) of home types, in the order of `card.living.homes.types`. |
| `built` | 4 shares (%) by period built, in the order of `card.living.built.bands`. |
| `lang` | Up to 5 `[language, pct]`, largest first. Demographic: card only. |
| `langMulti` | Toronto only: % naming two or more languages equally. |
| `homesTier` | Not stored; the website computes it. Apps don't need it. |

Rows, in order (labels from `card.living`):

1. **Housing**: cost tier label · "Median home $800K · rent $1,320/mo" · `caveat`.
2. **`hub`** (Toronto only, when `union` is present): `unionBand` tier label · `hubText` with
   `{minutes}`.
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

## 9. Not in this data

Real-time data (weather, air quality, traffic, beach water quality, transit arrivals) is not
published here. An app fetches it from its own sources and keeps it visibly separate from the
card's census and boundary data, with its own source line.

## 10. Changes

The website's maintainer updates this file whenever the published data changes shape. A breaking
change bumps `schema` in `city.json` and gets a new section at the top of this file saying what
changed and how to migrate.

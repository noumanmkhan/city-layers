# Toronto Layers

An interactive map of the City of Toronto where you turn civic and cultural boundaries on and off, then tap any spot to see every boundary it falls inside.

**Live site:** https://maps.noumankhan.ca

![Toronto Layers: the whole city with former cities, highways and rapid transit](assets/screenshot.png)

## Why

Toronto's geography is described in several overlapping ways at once. A single address can be in Old Toronto, "Downtown", the official neighbourhood of Wellington Place, what everyone calls King West, the Toronto Downtown West BIA, Ward 10, the provincial riding of Spadina—Fort York and the federal riding of Spadina—Harbourfront. Each of those lives in a different dataset on a different website. No public site I could find shows them together on one simple map.

## What it does

| Layer | Count | Notes |
|---|---|---|
| Former cities | 6 | The municipalities merged in 1998 |
| Old Toronto areas | 5 | Downtown, Midtown, Uptown,<br>West End, East End |
| Neighbourhoods | 158 | The City's official set (2022) |
| Known-as names | 85 | King West, Little Italy, the Junction… |
| Landmarks | 38 | Arenas, big parks, music venues,<br>civic buildings, campuses, airports |
| City wards | 25 | |
| Provincial ridings | 25 | Same lines as the wards |
| Federal ridings | 24 | 2023 Representation Order |
| Business Improvement Areas | 85 | |
| Neighbourhood lens | 158 | Housing cost, time to Union,<br>getting to work, renters and owners |
| Main streets | 321 streets | Major and minor arterials<br>(King, Queen, Eglinton…), named along the line |
| Highways | 10 in Toronto,<br>14 across the GTA | 400-series, QEW, 407 ETR,<br>DVP, Gardiner, Allen Rd |
| Subway & LRT | 5 lines | Lines 1, 2, 4, 5, 6 with station names |
| GO Transit trains | 7 lines<br>+ UP Express | ~70 stations, Metrolinx<br>line colours |

**Landmarks:** a short, curated list of the places Torontonians give directions by (Scotiabank Arena, High Park, Massey Hall, City Hall, U of T, Exhibition Place…), not an exhaustive points-of-interest database. Big, spread-out anchors appear city-wide; dense downtown venues appear as you zoom in, and overlapping labels are hidden automatically.

**Address search:** type a Toronto address (for example "789 Yonge St") and the map flies there, drops a pin and fills in the readout below. Addresses are matched with OpenStreetMap's Nominatim service, limited to the City of Toronto. Landmarks also suggest themselves as you type, including old names and nicknames (SkyDome, Air Canada Centre, Ryerson, "the Ex"), without any network call.

**Around the city:** zoom out to see every municipality in the Greater Toronto Area (Halton, Peel, York and Durham regions) as plain grey shapes, for context.

**416 or 416 + 905:** a switch at the top of the layer panel picks the extent. *Greater Toronto Area* (the default) shows the highways and GO lines across the region; *Toronto* greys out everything beyond the city limits and clips the GO lines at the boundary, leaving the TTC in full.

**Toronto in the GTA:** the highways continue past the city limits (OpenStreetMap data, joined to the City's centrelines at the boundary) and the GO Train lines run out to Barrie, Kitchener, Niagara Falls and Oshawa. Lines that share track near Union fan out as you zoom in. Tapping a spot outside Toronto names its municipality and region.

**Neighbourhood lens:** for someone new to Toronto, a quick sense of what each neighbourhood is like to live in. One lens at a time shades the 158 neighbourhoods in three plain tiers rather than precise figures:

- *Housing cost:* lower, middle or higher, from median home value and median rent, each ranked against the rest of the city and weighted by how many households own or rent.
- *Getting to work:* mostly transit, walk or bike; mixed; or mostly car, from the share of commuters who drive.
- *Renters and owners:* mostly owners, a mix, or mostly renters.
- *To Union:* the typical transit trip to Union Station on a weekday morning: under 30 minutes, 30–45, 45–60, or over an hour. Computed ahead of time from the TTC, GO and UP Express schedules with [r5py](https://r5py.readthedocs.io/), from points about 400 m apart across each neighbourhood (about 4,000 in all), leaving any time between 8 and 9 am. Walking to the stop and waiting count. Each neighbourhood shows the median of its points.

**Narrow it down:** under the lens legend, pick what you're looking for (say, middle housing cost and up to 45 minutes to Union) and the neighbourhoods that don't fit fade out. The ones that do are listed by name; tap one to fly there. It answers the question a newcomer actually asks: "where should I be looking?"

The What's here card adds a *Living here* section with the same tiers and the figures behind them (median home value and rent, time to Union, how people get to work, share of households renting). The point is the feel of a place relative to the rest of Toronto, not a price list.

**Light or dark:** the page follows your device's setting, or you can pick Light or Dark at the bottom of the layer panel.

**What's here:** click anywhere and a card lists the former city, area, neighbourhood, nearby known-as names, BIA, ward, provincial riding and federal riding for that point. The lookup runs in the browser with point-in-polygon tests against every layer, whether or not the layer is switched on.

![Downtown with areas, neighbourhoods and known-as names switched on](assets/screenshot-downtown.png)

## How it's built

- **Front end:** one static HTML page using [Leaflet](https://leafletjs.com/), with no framework and no build step for the page itself. Colours come from CSS variables, so the map follows the viewer's light or dark setting. The layout works on phones.
- **Data pipeline** (`pipeline/`): Python with Shapely and Node with mapshaper.
  - `regions.py` defines the informal Old Toronto areas on the City's older 140-neighbourhood map, then carries them over to the current 158 by largest overlap.
  - `build.py` cleans every source. It drops ramps from the expressway centrelines and merges what's left into named routes. It clips federal ridings to the city's shoreline, matches each ward to its provincial riding, and computes a label point inside each polygon.
  - mapshaper simplifies the shapes so the site loads quickly. All the data comes to about 800 KB.
- **No server:** everything is static files, so the site can be hosted free on GitHub Pages or Cloudflare Pages.

Rebuild the data:

```bash
cd pipeline
pip install shapely
./run.sh            # writes docs/data/*.geojson and docs/index.html
cd ../docs && python3 -m http.server 8000
```

## Built with AI

I built this with Claude (Anthropic) as the implementation partner. I owned the product side: the problem, which layers matter and how Toronto's informal geography should be described. I also reviewed every output against what I know of the city. Claude handled most of the engineering:

- finding and pulling the official datasets
- writing the geometry pipeline and the front end
- testing the page at desktop and phone sizes

The work was data sourcing as much as it was code. Some examples of the judgment calls involved:

- Federal riding lines changed in 2023, so Toronto now has 24 federal ridings but still 25 provincial ridings. The provincial ridings still match the wards exactly, so they share the wards' official geometry.
- The City's riding layer turned out to hold pre-2018 boundaries. The current ridings come from Elections Canada and Elections Ontario data instead, via Open North.
- There is no official dataset for names like King West or Little Italy. Those are curated by hand and labelled as approximate.

## Known limitations

- Known-as names are approximate centre points, not areas.
- Federal riding shapes are simplified, so a point within a few metres of a riding edge can be misattributed. Wards and provincial ridings use the City's detailed lines.
- There is no street basemap yet, just land and water.
- The neighbourhood lens uses the 2021 Census, so prices are a few years old, and commuting was counted in May 2021, during the pandemic, when transit use was unusually low. The tiers are relative to the rest of Toronto, which is what they're meant to show.
- Times to Union come from published schedules, not real-world delays, and are for one destination. There's no driving time on purpose: free routing tools assume empty roads, which badly understates a Toronto rush hour.
- Address matching depends on OpenStreetMap's address coverage, which is good in Toronto but not complete. The free Nominatim service also asks for no more than one search per second, which the page enforces.

## Roadmap

- Known-as names as drawn areas instead of points.
- An optional street basemap.

## Data sources and licences

- City of Toronto Open Data, under the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-license/): former municipalities, wards, neighbourhoods, Neighbourhood Profiles (2021 Census), BIAs, expressway centrelines and the TTC GTFS feed.
- Electoral boundaries from Elections Canada (2023 Representation Order) and Elections Ontario, via [Open North Represent](https://represent.opennorth.ca/).
- Subway, LRT and GO/UP geometry derived from TTC and Metrolinx GTFS via [agcghub/toronto-bus-map](https://github.com/Miqell24/toronto-bus-map).
- Travel times to Union computed from the TTC schedules and from Metrolinx's GO and UP Express GTFS ([Metrolinx Open Data](https://www.metrolinx.com/en/about-us/open-data)), with walking routes from OpenStreetMap.
- Highways outside Toronto © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), fetched with the Overpass API.
- Neighbouring municipalities © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL). Lake Ontario from [Natural Earth](https://www.naturalearthdata.com/) (public domain).

`pipeline/SOURCES.md` lists the exact queries used to fetch the raw data. The code is MIT-licensed (see `LICENSE`). The data stays under its original licences.

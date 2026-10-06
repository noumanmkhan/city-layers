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
| City wards | 25 | |
| Provincial ridings | 25 | Same lines as the wards |
| Federal ridings | 24 | 2023 Representation Order |
| Business Improvement Areas | 85 | |
| Highways | 10 routes | 400-series, QEW, DVP,<br>Gardiner, Allen Rd, 2A |
| Subway & LRT | 5 lines | Lines 1, 2, 4, 5, 6 with station names |

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

## Roadmap

- Address search: type "620 King St W" and get the readout as pills.
- Known-as names as drawn areas instead of points.
- An optional street basemap.

## Data sources and licences

- City of Toronto Open Data, under the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-license/): former municipalities, wards, neighbourhoods, BIAs, expressway centrelines and the TTC GTFS feed.
- Electoral boundaries from Elections Canada (2023 Representation Order) and Elections Ontario, via [Open North Represent](https://represent.opennorth.ca/).
- Subway and LRT geometry derived from TTC GTFS via [agcghub/toronto-bus-map](https://github.com/Miqell24/toronto-bus-map).
- Neighbouring municipalities © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL). Lake Ontario from [Natural Earth](https://www.naturalearthdata.com/) (public domain).

`pipeline/SOURCES.md` lists the exact queries used to fetch the raw data. The code is MIT-licensed (see `LICENSE`). The data stays under its original licences.

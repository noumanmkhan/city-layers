# City Layers

A city is divided up in a dozen ways at once: official neighbourhoods, council wards, state or provincial and federal electoral districts, business districts, the informal names locals actually use, and the transit lines that tie it together. Each of those lives in a different dataset on a different website. City Layers puts them on one interactive map you can switch on and off, then tap any spot (or search an address or place) to see every boundary it falls inside, what it's like to live there and who represents it. It's built for two kinds of people: a resident learning things they probably didn't know about their own city, and a newcomer getting their bearings.

The maps share one engine, with a folder of data and settings per city:

- **Toronto Layers:** https://maps.noumankhan.ca/toronto/
- **Chicago Layers** (work in progress): https://maps.noumankhan.ca/chicago/

## Toronto Layers

An interactive map of the City of Toronto where you turn civic and cultural boundaries on and off, then tap any spot to see every boundary it falls inside.

![Toronto Layers: the whole city with former cities, highways and rapid transit](assets/screenshot.png)

### Why

Toronto's geography is described in several overlapping ways at once. A single address can be in Old Toronto, "Downtown", the official neighbourhood of Wellington Place, what everyone calls King West, the Toronto Downtown West BIA, Ward 10, the provincial riding of Spadina—Fort York and the federal riding of Spadina—Harbourfront. Each of those lives in a different dataset on a different website. No public site I could find shows them together on one simple map.

### What it does

| Layer | Count | Notes |
|---|---|---|
| Former cities | 6 | The municipalities merged in 1998 |
| Old Toronto areas | 5 | Downtown, Midtown, Uptown,<br>West End, East End |
| Neighbourhoods | 158 | The City's official set (2022) |
| Known-as names | 85 | King West, Little Italy, the Junction… |
| Landmarks | 34 | Arenas, big parks, music venues,<br>museums, civic buildings, airports |
| Skyscrapers | 130 | Every building 150 m and taller:<br>117 built or topped out, 13 under construction |
| City wards | 25 | |
| Provincial ridings | 25 | Same lines as the wards |
| Federal ridings | 24 | 2023 Representation Order |
| Business Improvement Areas | 85 | |
| School board wards | 29 across 4 boards | Trustee wards for TDSB (12), TCDSB (12),<br>Viamonde (3) and MonAvenir (2), one board at a time |
| Heritage districts | 29 | Heritage Conservation Districts in force;<br>ones under study or appeal are left out |
| Neighbourhood lens | 158 | Housing cost, time to Union,<br>getting to work, renters and owners,<br>housing type |
| Main streets | 321 streets | Major and minor arterials<br>(King, Queen, Eglinton…), named along the line |
| Collector streets | 989 streets | The tier below (Dovercourt, Greenwood…),<br>from zoom 13; most non-arterial bus streets |
| Highways | 10 in Toronto,<br>14 across the GTA | 400-series, QEW, 407 ETR,<br>DVP, Gardiner, Allen Rd |
| Subway & LRT | 5 lines | Lines 1, 2, 4, 5, 6 with station names |
| Streetcars | 11 routes | Numbered along the line;<br>stops when zoomed in |
| Bus routes | 230 routes,<br>by family | Frequent, express or overnight;<br>any route on demand |
| GO Transit trains | 7 lines<br>+ UP Express | ~70 stations, Metrolinx<br>line colours |
| Transit under construction | 4 lines | Ontario Line, Line 2 East and<br>Eglinton West extensions,<br>Hazel McCallion Line (GTA view) |
| Road closures | Daily | Closures and lane restrictions from<br>transit and GO construction |

**Universities, colleges and hospitals:** three toggles under Landmarks, off by default, show how these are laid out across the city. They follow fixed rules rather than listing everything: universities are public or nonprofit, one point per campus; colleges are public only, so no private career colleges and no public-private partnership campuses (a public college's name on a campus run by a private company, whose students Ontario cut off from post-graduation work permits in 2024); hospitals are Ontario public hospitals plus OHIP-funded ones like Shouldice, with a heavier ring for an emergency department. Chicago applies the same rules from the federal IPEDS and CMS directories: universities with 1,000 or more students, the seven City Colleges, and public or nonprofit hospitals with an ER (two Prime Healthcare hospitals that turned for-profit in 2025 are left out). Names only: no ratings, rankings or wait times.

**Skyscrapers:** a fourth toggle under Landmarks, off by default, places every building 150 m and taller: 117 in Toronto (plus 13 under construction) and 138 in Chicago. Each badge shows what the tower is for (homes as a grid of windows, offices and hotels as floor bands, mixed use as both), stays hollow until the building is open for occupancy (topping out isn't enough), and gets a gold ring at 300 m and up, the supertalls: SkyTower and One Bloor West in Toronto, Willis, Trump, St. Regis, Aon, the Hancock, Franklin Center and Two Prudential in Chicago. Tap one and the readout gives its height, floors and year with a few facts: where it ranks in the city, whether it was once the city's tallest, the tallest of its decade or its kind, and a handful of written-up records (Willis was the world's tallest building for almost 25 years; First Canadian Place was Canada's tallest for half a century). The list comes from Wikipedia's tallest-buildings pages, refreshed monthly; this year's openings are checked by hand before a tower turns solid.

**Landmarks:** a short, curated list of the places Torontonians give directions by (Scotiabank Arena, High Park, Massey Hall, City Hall, Exhibition Place…), not an exhaustive points-of-interest database. Big, spread-out anchors appear city-wide; dense downtown venues appear as you zoom in, and overlapping labels are hidden automatically.

**Address search:** type an address (for example "789 Yonge St") and the map flies there, drops a pin and fills in the readout below. Addresses are matched with OpenStreetMap's Nominatim service across the GTA, with Toronto matches listed first; an address beyond the city limits switches the map to the regional view. Landmarks and place names also suggest themselves as you type, without any network call: landmarks with their old names and nicknames (SkyDome, Air Canada Centre, Ryerson, "the Ex"), plus every neighbourhood, known-as name, former city and surrounding municipality. Choosing a place like Deer Park or Mississauga frames it on the map and fills in the readout, switching to the regional view for places outside the city. Beyond Toronto, the GTA's named communities suggest themselves too (Meadowvale, Port Credit, Woodbridge, Unionville, Brooklin, Kleinburg…, about 470 in all, from OpenStreetMap's place names): choosing one shows where it is, with its municipality and region, and an address in the GTA gets a "Near Meadowvale"-style pill. Most GTA municipalities don't publish neighbourhood boundaries the way Toronto does, so these are named points for finding your way, not drawn areas. On the Chicago map the same works for community areas, the sides and suburbs like Lombard.

**Shareable links:** the address bar keeps up with the map as you use it: the pin and its name, the layers that are on, the lens and any "Narrow it down" picks, the 416 or 416 + 905 view, and where the map is looking. Copy it, or use the Share button (in the readout, and at the foot of the layer panel; on phones it opens the share sheet), and whoever opens the link sees the same map. Everything sits after the `#`, so it never reaches a server, and anything a link leaves out falls back to the starting setting. Layers are named by short ids that don't change when a layer's label does, so old links keep working. Works the same on the Chicago map.

**Save as an image:** the Image button at the foot of the layer panel saves the map as a 3840 × 2160 PNG, with or without its labels. It's made entirely in the browser: the map is drawn from the site's own shapes rather than third-party tiles, so it can be redrawn in a 16:9 frame covering what's on screen and turned into a picture with [html-to-image](https://github.com/bubkoo/html-to-image), loaded only when first used. The panels, pin and controls are left out, and a small credit line with the map's address and its data sources is stamped in the corner, as the data licences ask. On phones it opens the share sheet.

**More room for the map:** on a computer, the arrow at the top of the layer panel folds it away to a small Layers button; the choice is remembered. On phones the panel already folds down to its title.

**Heritage districts:** a spot inside a protected district gets a line on the readout saying which one and the year it was designated ("Cabbagetown South (designated 2005)"); elsewhere the line doesn't appear. In Toronto these are the Heritage Conservation Districts in force under the Ontario Heritage Act; districts still under study or under appeal aren't shown, so the map never presents them as protected. Chicago's equivalent is its Landmark Districts.

**Around the city:** zoom out to see every municipality in the Greater Toronto Area (Halton, Peel, York and Durham regions) as plain grey shapes, for context.

**416 or 416 + 905:** a switch at the top of the layer panel picks the extent. *Toronto* (the default) greys out everything beyond the city limits and clips the GO lines at the boundary, leaving the TTC in full; *Greater Toronto Area* shows the highways and GO lines across the region.

**Starting view and Reset:** the map opens on Toronto with former cities, Old Toronto areas, neighbourhoods, known-as names, main streets, highways, GO and the subway switched on, and everything else off. *Reset*, at the bottom of the layer panel, returns to that view from wherever you've wandered (it also clears any neighbourhood filter); *Hide all* turns every layer off.

**Toronto in the GTA:** the highways continue past the city limits (OpenStreetMap data, joined to the City's centrelines at the boundary) and the GO Train lines run out to Barrie, Kitchener, Niagara Falls and Oshawa. Lines that share track near Union fan out as you zoom in. Tapping a spot outside Toronto names its municipality and region.

**Neighbourhood lens:** for someone new to Toronto, a quick sense of what each neighbourhood is like to live in. One lens at a time shades the 158 neighbourhoods in three plain tiers rather than precise figures:

- *Housing cost:* lower, middle or higher, from median home value and median rent, each ranked against the rest of the city and weighted by how many households own or rent.
- *Getting to work:* mostly transit, walk or bike; mixed; or mostly car, from the share of commuters who drive.
- *Renters and owners:* mostly owners, a mix, or mostly renters.
- *To Union:* the typical transit trip to Union Station on a weekday morning: under 30 minutes, 30–45, 45–60, or over an hour. Computed ahead of time from the TTC, GO and UP Express schedules with [r5py](https://r5py.readthedocs.io/), from points about 400 m apart across each neighbourhood (about 4,000 in all), leaving any time between 8 and 9 am. Walking to the stop and waiting count. Each neighbourhood shows the median of its points.
- *Housing type:* pick a type (detached, semi and row, low-rise apartments or towers of five storeys and up) and the neighbourhoods are shaded by its share of their homes: under 10%, 10–30%, 30–60%, or 60% and more.

**Suburban lens:** in the Greater Toronto Area view, each municipality is shaded by its typical drive to Union Station with no traffic: under 30 minutes, 30–60, 60–90, or 90 and over. A grid of points about 1.5 km apart covers the suburbs (about 2,900 in the GTA); each is timed with [OSRM](https://project-osrm.org/) on OpenStreetMap roads at posted speeds, and each municipality shows the median of its points. Tapping a spot outside the city adds the time from there, so someone in a big municipality like Caledon sees their own area, not an average. The times are best case on purpose: they compare places, and anyone can add their own rush hour.

**Focus on a region:** in the Greater Toronto Area view, pick Halton, Peel, York or Durham (or type its name in search). The map outlines it, dims everything else, labels its municipalities and lists them in the panel with their drive times; tap one to go there. Tapping a spot outside the city also offers "Show all of" its region, and a shared link keeps the focus.

**Narrow it down:** under the lens legend, pick what you're looking for (say, middle housing cost and up to 45 minutes to Union) and the neighbourhoods that don't fit fade out. The ones that do are listed by name; tap one to fly there. It answers the question a newcomer actually asks: "where should I be looking?"

**What stands out:** under the card's pills, one line says what makes the neighbourhood stand out among its peers, such as "North St. James Town: highest share of renters in Toronto (89% rent)" or "Englemount-Lawrence: among the quickest transit trips to Union in North York". A build step (`engine/facts.py`) ranks every neighbourhood against the whole city and against its own former city and Old Toronto area, on figures the map already has: housing cost, renters and owners, getting to work, home types, age of homes and time to Union. A fact needs a top-3 place and a figure clearly away from the group's middle, so about three in four neighbourhoods get one and the rest show none rather than a forced one. Language and other demographic figures never feed it, and affordable areas are described as "among the most affordable", never "cheapest". Chicago's community areas get the same, compared with the city and their side.

The What's here card adds a *Living here* section with the same tiers and the figures behind them (median home value and rent, time to Union, how people get to work, share of households renting). The point is the feel of a place relative to the rest of Toronto, not a price list.

Three more rows describe the place without ranking it: *Home types* (the mix of detached, semi and row, low-rise and tower homes), *Built* (when its homes went up: 1960 or before, 1961–80, 1981–2000, 2001–21) and *Language at home* (the top three languages people speak most often at home; the second and third show only at 5% or more, so a 1% language never reads as a feature of the place). Language is description only: it never shades the map, filters a shortlist or feeds a ranking. On the Chicago map the same rows come from the American Community Survey: buildings by number of units (detached, attached, 2–19 units, 20 or more), year built (1939 or earlier through 2000 and later), and language at home in the Census's 12 broad groups, which is all it publishes for areas this small.

**Moving between maps:** the map's name at the top of the layer panel is a menu. Pick another city to jump straight to its map, or *All maps* to return to the maps hub; an *All maps* link above the name does the same on wider screens. Each city's menu is built from the cities in the repo, so a new city appears in every map's menu on its next build.

**Light or dark:** the page follows your device's setting, or you can pick Light or Dark at the bottom of the layer panel.

**What's here:** click anywhere and a card sums up the spot in a few coloured pills, then breaks it down in sections you can open and close (the page remembers which you keep open):

- *Boundaries:* former city, area, neighbourhood, nearby known-as names, BIA, ward, provincial riding, federal riding and the spot's ward on each of the four school boards.
- *Living here:* the neighbourhood lens tiers and the figures behind them.
- *Schools (Chicago):* the Chicago Public Schools whose attendance area the spot is in: the elementary school, the middle school where one has its own area (22 do), and the high school, each with its grades, the straight-line distance to the building and a link to its CPS profile. From CPS's 2025–26 boundaries on the City's Data Portal. Names and grades only: no ratings or test scores.
- *Nearby:* the nearest library branch, community centre and emergency department, with the distance, and how many parks, playgrounds, parks with tennis courts and dog off-leash areas are within 1 km (about a 15-minute walk). Counts only, nothing scored. From the City's parks and recreation file and Toronto Public Library; Chicago's uses the Chicago Public Library, the Park District's fieldhouses and the City's community service centers (community centres count only if publicly run and open to everyone) and OpenStreetMap, and works in miles: distances in miles (feet when very close) and counts within half a mile, about a 10-minute walk.
- *Representatives:* the city councillor, MPP and MP for that spot, each name linking to their official page on toronto.ca, ola.org or ourcommons.ca, with party for the MPP and MP (Toronto councillors run without party labels). Then a school trustee row for each board: before the October 26, 2026 election it lists the candidates; once the City's results file has a winner it names them, marked as taking office November 15; from then on, just the trustee.

The boundary lookup runs in the browser with point-in-polygon tests against every layer, whether or not the layer is switched on.

**School board wards:** in April 2026 Ontario capped school boards at 12 trustees, so the TDSB's 22 wards became 12 and the City's open trustee-ward file (2018 lines) went out of date. The City Clerk's reference chart defines every 2026 trustee ward, for all four boards, as a group of whole City wards, so the map builds them by merging City wards rather than waiting for a new file. Which school a given address is zoned for isn't shown for Toronto: none of the boards publishes its attendance boundaries as open data. Chicago's map does show it, because CPS publishes its attendance areas every school year.

**Keeping representatives current:** a GitHub Action runs every Monday, reads the current members straight from the City, the Legislative Assembly and the House of Commons, and republishes the site only if something changed, so by-elections and the new council after an election show up within a week. Names come from the same pages they link to. Open North's representatives data was tried first and dropped: it still listed an MP six months after her by-election.

**Transit under construction and road closures:** lines being built are drawn dashed in their future colour, and nested under them is the one layer on the map that changes every day: road closures and lane restrictions caused by that construction. A GitHub Action runs just after midnight Eastern, reads Toronto's live Road Restrictions feed (permits filed by Metrolinx and the consortiums building its lines) and Chicago's CDOT permits (those naming the Red Line Extension or the Red/Purple rebuild), ties each permit to the nearest line being built or upgraded, and republishes. Arterials always show; full closures of side streets appear when zoomed in, since that's where most actual closures are (the streets crossing a new line). Tapping one gives the hours and the permit dates, labelled as permit dates: permits get padded and renewed, so they aren't a forecast of when a road reopens.

**Streetcars and buses:** there are far too many bus routes to draw at once (230 in Toronto, 124 in Chicago), so the map shows them in families (frequent and express together or apart, overnight on its own) and draws any single route on demand. The families come from the schedule itself rather than the agency's branding: *Frequent* means a trip every 10 minutes or better each way through a weekday from 7 am to 7 pm (Toronto's 43 such bus routes read as a grid across the city, with 10 of the 11 streetcar routes on their own layer); *Express* is what the agency calls express, dashed when shown with the frequent routes; *Overnight* means at least an hourly trip each way between 2 and 4 am, which in Toronto is the Blue Night network. Toronto's 11 streetcar routes get a layer of their own, in red, numbered along the line. So bus lines on smaller streets don't float in space, a *Collector streets* toggle under Main streets draws the next tier of roads from zoom 13: with it on, 93% of Toronto's bus network and 88% of Chicago's sits on a drawn street, rather than 82% and 68% (expressways bring both to 94%). The readout gains a *Transit nearby* section: the nearest subway or 'L' station, every route with a stop within about a 5-minute walk, the overnight routes, and the nearest stop. Frequent routes are filled in; tap any number there (or search "29" or "Dufferin") and that route is drawn in ink with its stops. On the map, tapping a route's line or its number badge shows it alone, with everything else faded, until the next tap elsewhere. A GitHub Action reads the TTC's and the CTA's GTFS each month, keeps each route's main shapes, counts trips per hour, and the build sorts routes into families from those counts. Nothing is ranked: how often a bus comes is described, never scored.

![Downtown with areas, neighbourhoods and known-as names switched on](assets/screenshot-downtown.png)

## Chicago Layers

**Live site (work in progress):** https://maps.noumankhan.ca/chicago/

The second city runs on the same engine with its own data and config (`cities/chicago/`). Chicago's layers line up with Toronto's:

| Layer | Count | Notes |
|---|---|---|
| The sides | 9 | Far North Side to Far Southeast Side,<br>the informal split Chicagoans use |
| Community areas | 77 | The City's official areas |
| Known-as names | 31 | Wicker Park, Gold Coast, Pilsen… |
| City wards | 50 | One alderperson each |
| Illinois House districts | 36 | Each pair makes a Senate district,<br>so one layer gives both |
| Congressional districts | 9 | Illinois seats in the U.S. House |
| Special Service Areas | 58 | Chicago's equivalent of BIAs |
| Landmark districts | 59 | The City's boundary file dates from 2012,<br>so later designations are missing |
| Skyscrapers | 139 | Every building 150 m (about 490 ft)<br>and taller; 7 supertall, 1 under construction |
| Expressways | 11 in Chicago | Kennedy, Dan Ryan, Eisenhower,<br>Stevenson, Lake Shore Drive |
| Collector streets | 272 streets | OpenStreetMap tertiary roads,<br>from zoom 13 |
| Metra | 11 lines | From four downtown terminals |
| The 'L' | 8 lines, 144 stations | CTA rapid transit |
| Bus routes | 124 routes,<br>by family | Frequent, express or overnight;<br>any route on demand |
| Transit under construction | 1 line | Red Line Extension, 95th to 130th Street |
| Street closures | Daily | From the Red Line Extension and<br>the Red/Purple rebuild |

The community area lens uses the American Community Survey (2020–2024 five-year estimates): Census tracts are grouped into community areas, and median home values and rents are read from the summed price brackets. Its tiers use the same cut-offs as Toronto's, so the two maps read alike. In the Chicagoland view, *Focus on a county* does the same for the seven Illinois counties and Lake and Porter in Indiana, using the Census Bureau's county lines: pick DuPage and its 29 towns are outlined, labelled and listed. Chicagoland residents tend to place themselves by county first, so this came straight from a Chicagoan's feedback. The suburban lens works the same way in the Chicagoland view, timed to State & Madison, the zero point of Chicago's address grid, from about 5,300 points; unincorporated county land stays grey but still gets a time on the card. Representatives are the alderperson, state representative, state senator and member of Congress, refreshed weekly from the City's data portal, Open States and the Clerk of the House. The Chicago Board of Education's 20 districts, on the ballot for the first time as a fully elected board on November 3, 2026, are a layer too, from the map the legislature enacted in 2024 (the City's portal doesn't carry it). The card names the spot's district and lists its candidates and the citywide president race from the election board's official candidate list; from election night it names who leads the count, and the winner once the board proclaims the results.

*To the Loop* is Chicago's version of Toronto's time to Union: the typical transit trip on a weekday morning, from about 3,700 points 400 m apart across the 77 community areas, routed with r5py on the CTA, Metra and South Shore Line schedules. Because the Loop is a district rather than one station, each point counts its quickest arrival at any of five spots: Union Station or Ogilvie, LaSalle/Van Buren, Clark/Lake, State & Madison, or Millennium Station. It's banded like Toronto's (under 30 minutes, 30–45, 45–60, over an hour) and works with *Narrow it down*.

## How it's built

- **One engine, one folder per city.** The map page is a shared engine (`engine/`) that knows how to draw kinds of layer: filled areas, official neighbourhoods, representation boundaries, business areas, streets, highways, regional rail and rapid transit. Everything about Toronto lives in `cities/toronto/`: `city.json` holds the layer list, labels, lenses and the rows of the "What's here" card, and `city.css` holds Toronto's colours. Adding a city means adding its data and config, not changing the engine.
- **Front end:** one static HTML page using [Leaflet](https://leafletjs.com/), with no framework. `engine/assemble.py` inlines the city's config and colours into the engine page, so each city's map is a single file. Colours come from CSS variables, so the map follows the viewer's light or dark setting. The layout works on phones.
- **Data pipeline** (`cities/toronto/`): Python with Shapely and Node with mapshaper.
  - `regions.py` defines the informal Old Toronto areas on the City's older 140-neighbourhood map, then carries them over to the current 158 by largest overlap.
  - `build.py` cleans every source. It drops ramps from the expressway centrelines and merges what's left into named routes. It clips federal ridings to the city's shoreline, matches each ward to its provincial riding, and computes a label point inside each polygon.
  - mapshaper simplifies the shapes so the site loads quickly. All the data comes to about 800 KB.
- **No server:** everything is static files, so the site can be hosted free on GitHub Pages or Cloudflare Pages.

Rebuild the data:

```bash
pip install shapely
cities/toronto/run.sh    # writes docs/toronto/data/*.geojson and docs/toronto/index.html
cities/chicago/run.sh    # the same for docs/chicago/
cd docs && python3 -m http.server 8000
```

After a change to the page or the config alone, `python3 engine/assemble.py toronto` is enough.

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
- There's no detailed street basemap: the map draws main streets, highways and transit, but not every local street. That's on purpose, to keep it readable; for street-level detail, use Google Maps or OpenStreetMap.
- The neighbourhood lens uses the 2021 Census, so prices are a few years old, and commuting was counted in May 2021, during the pandemic, when transit use was unusually low. The tiers are relative to the rest of Toronto, which is what they're meant to show.
- Times to Union come from published schedules, not real-world delays, and are for one destination. There's no driving time on purpose: free routing tools assume empty roads, which badly understates a Toronto rush hour.
- Road closures are a daily snapshot of permits, not live traffic: work can finish early, run late or be renewed, and utility work done for a transit project but filed by the utility (Toronto Hydro, Enbridge) isn't included. Lines under construction show only once OpenStreetMap maps them (Yonge North isn't yet).
- Representatives are refreshed weekly, so for a few days after an election or by-election the card can lag. Vacant seats say so.
- Address matching depends on OpenStreetMap's address coverage, which is good in Toronto but not complete. The free Nominatim service also asks for no more than one search per second, which the page enforces.
- Chicago: the sides are a convention, not an official boundary, and the main streets come from OpenStreetMap plus a hand-kept list of the mile-grid arterials and diagonals. Times to the Loop come from published schedules, like Toronto's times to Union.

## Roadmap

- Known-as names as drawn areas instead of points.
- An optional detailed street basemap (every local street), off by default.

## Data sources and licences

- City of Toronto Open Data, under the [Open Government Licence – Toronto](https://open.toronto.ca/open-data-license/): former municipalities, wards, neighbourhoods, Neighbourhood Profiles (2021 Census), BIAs, Heritage Conservation Districts, expressway centrelines and the TTC GTFS feed.
- Elected representatives from [toronto.ca](https://www.toronto.ca/city-government/council/members-of-council/), the [Legislative Assembly of Ontario](https://www.ola.org/en/members/current) and the [House of Commons](https://www.ourcommons.ca/members/en).
- Electoral boundaries from Elections Canada (2023 Representation Order) and Elections Ontario, via [Open North Represent](https://represent.opennorth.ca/).
- Subway, LRT and GO/UP geometry derived from TTC and Metrolinx GTFS via [agcghub/toronto-bus-map](https://github.com/Miqell24/toronto-bus-map).
- Travel times to Union computed from the TTC schedules and from Metrolinx's GO and UP Express GTFS ([Metrolinx Open Data](https://www.metrolinx.com/en/about-us/open-data)), with walking routes from OpenStreetMap.
- Suburban drive times (both cities) routed with [OSRM](https://project-osrm.org/) on © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors' roads (ODbL).
- Highways outside Toronto © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), fetched with the Overpass API.
- Skyscrapers (both cities) from Wikipedia's "List of tallest buildings in Toronto" and "…in Chicago" ([CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)); addresses of towers under construction placed with OpenStreetMap's Nominatim.
- Road closures from the City of Toronto's [Road Restrictions](https://open.toronto.ca/dataset/road-restrictions/) live feed (Open Government Licence – Toronto); lines under construction © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL).
- Neighbouring municipalities © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL). Lake Ontario, Lake Simcoe and Lake Scugog shorelines around the GTA from OpenStreetMap; lakes farther out from [Natural Earth](https://www.naturalearthdata.com/) (public domain).

Chicago:

- [City of Chicago Data Portal](https://data.cityofchicago.org/) ([terms](https://www.chicago.gov/city/en/narr/foia/data_disclaimer.html)): community areas, neighbourhoods, wards, SSAs, Landmark Districts, the city boundary, 'L' lines and stations, and ward offices.
- U.S. Census Bureau (public domain): TIGERweb municipalities, counties, legislative districts, tract points and Lake Michigan's shoreline; American Community Survey 2020–2024 five-year tables.
- [Metra GTFS](https://metra.com/developers) for Metra lines and stations; [CTA GTFS](https://www.transitchicago.com/developers/gtfs/) for bus routes and stops.
- Illinois legislators from [Open States](https://openstates.org/) (public domain); members of Congress from the [Clerk of the U.S. House](https://clerk.house.gov/).
- Streets and expressways © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), fetched with the Overpass API.
- Street closures from CDOT's [Transportation Department Permits](https://data.cityofchicago.org/d/pubx-yq2d) (City of Chicago Data Portal); the Red Line Extension's line © OpenStreetMap contributors (ODbL).

`cities/toronto/SOURCES.md` and `cities/chicago/SOURCES.md` list the exact queries used to fetch the raw data. The code is MIT-licensed (see `LICENSE`). The data stays under its original licences.

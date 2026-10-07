# Hyderabad: scouting findings (October 8, 2026)

Verdict: **tabled.** The boundaries the map is mainly about (which municipal corporation, which
ward) aren't published anywhere in a usable form yet. Everything else is available.

Raw results: `out/report.json` and `out/scout.log`, from `scout.py` (run by hand with the
*Scout Hyderabad data* workflow). Boundaries found in OpenStreetMap are in `out/osm/`.

## Blocked: no current files
| Boundary | What exists | Problem |
|---|---|---|
| GHMC, Cyberabad and Malkajgiri corporations (Feb 2026) | Nothing | Not in OpenStreetMap or OpenCity. The corporations' sites (cmc.telangana.gov.in, ghmc.gov.in) didn't answer from GitHub's servers |
| 300 wards (Dec 2025) | Old 150 wards only | OSM's 149 ward relations were imported in October 2023 from OpenCity's 2022 file. OpenCity's "Wards Info" still holds the 2022 map |
| Secunderabad Cantonment | Nothing | No boundary relation in OSM |
| HMDA after the 2025 expansion (10,472 km²) | Old outline | OSM's HMDA relation is 7,649 km², last edited July 2025, so before the expansion |

Rebuilding the corporations from other layers doesn't work: they're made of the new zones, which
follow the new wards; the merged municipalities aren't in OSM (only mandals, which don't line up).

## Available and current
- **Assembly and Lok Sabha constituencies:** DataMeet (CC BY 4.0) has all 24 core-city assembly
  seats and the surrounding Lok Sabha seats, on the 2008 lines that are still in force. Its file
  still labels the state "Andhra Pradesh". OpenCity also has KMLs (2018 assembly, 2019 Lok Sabha).
- **Districts and mandals:** in OSM from the Telangana government's 2023 shapefiles (GODL),
  edited through 2026. Hyderabad district measures 183 km² in OSM against the usual 217; check before use.
- **PIN codes:** OpenCity's "Hyderabad and Secunderabad Pin Codes Map 2025" (KML, November 2025).
  data.gov.in's Department of Posts files refused GitHub's servers (403).
- **Place names:** 1,434 neighbourhood and 170 suburb nodes inside the ORR. 32 of 39 checklist
  names found; the misses (Charminar, Tarnaka, Kompally, Dilsukhnagar, Lakdikapul, Tellapur,
  "Hitech City") are spelling variants or curation work. HITEC City and Financial District exist
  as suburb points, with no outline.

## When to look again
Ward maps should become public before the corporation elections (reported for December 2026 or
December 2027). Re-run the workflow then, or when OpenCity updates "Hyderabad - Wards Info".

# Changelog

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

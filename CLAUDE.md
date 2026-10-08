# City Layers: notes for Claude sessions

This repo is the **map** (live at https://maps.noumankhan.ca/toronto/) and the small
maps hub page at https://maps.noumankhan.ca/. The landing page for
noumankhan.ca is a separate repo and a separate project. If you were opened to work on
the landing page, stop and say so; don't change this repo.

## Before changing anything
- Other sessions may have pushed since you last looked. Run `git fetch origin main` and
  pull/rebase onto `origin/main` first, and fetch again right before pushing.
- If a push is rejected, rebase onto the new commits and keep both sets of changes.
  Never force-push.
- Before editing a file, read its current version from the repo, not from memory or an
  earlier copy.

## How the site is built
- `docs/` is what GitHub Pages serves (it holds the `CNAME` for maps.noumankhan.ca).
  - `docs/index.html`, `docs/fonts/` and the icons are the **maps hub**, hand-written and
    styled to match the noumankhan.ca landing page. Edit them directly. Print maps get
    added there as cards (a template is commented out in the HTML), with images in `docs/prints/`.
  - `docs/<city>/` is each city's map (Toronto Layers is `docs/toronto/`). Don't hand-edit
    `docs/<city>/index.html` or `docs/<city>/data/*`; they are build output.
- The map is one engine with a folder per city:
  - `engine/template.html` (page and styles) and `engine/map.js` (behaviour) are shared by every
    city. Keep them free of city names, places and data sources.
  - `cities/<city>/city.json` holds everything city-specific on the page: text, layer list and
    files, lenses, "What's here" rows, representatives, search area. `city.css` holds the city's
    own colours (fill layers, transit lines, their swatches).
  - `cities/<city>/` also holds that city's fetch and build scripts, `raw/` inputs, `run.sh` and
    `SOURCES.md`.
- Rebuild a city with `cities/<city>/run.sh` (needs Python with shapely, and Node; it runs
  `npm install` at the repo root for mapshaper and Leaflet). After a page-only or config-only
  change, `python3 engine/assemble.py <city>` is enough.
- An engine change affects every city: rebuild and check each one.
- The City of Toronto GIS server (gis.toronto.ca) can't be reached from most sandboxes.
  `.github/workflows/fetch-streets.yml` shows the pattern: fetch it in GitHub Actions and
  commit the raw file. It also rejects bursts of parallel requests, so fetch one layer at a time.

## Apps that read this data
- An iOS app (separate repo, built in Cursor) reads the published `docs/<city>/data/` files and
  `docs/<city>/data/city.json` (written by `engine/assemble.py`). `app-contract/DATA_CONTRACT.md`
  describes them.
- When a change alters a published file, field or card row, update the contract in the same
  commit. Adding things is fine. Renaming, removing or changing the meaning or units of a field or
  file is a breaking change: bump `"schema"` in every `cities/*/city.json` and add a migration
  note at the top of the contract.

## Conventions
- One change per commit, with a plain-English message saying what changed and why.
- Test in a browser at desktop and phone widths, and in light and dark themes, before pushing.
- Keep the map uncluttered. Landmarks and known-as names are deliberately short, curated
  lists, not exhaustive databases.
- Address search uses OpenStreetMap Nominatim, whose usage policy forbids
  autocomplete-as-you-type. Live suggestions come only from the local landmark list.
- Keep `README.md` current when features change. It doubles as the portfolio write-up.

# Toronto Layers: notes for Claude sessions

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
  - `docs/toronto/` is the **Toronto Layers map**. Don't hand-edit `docs/toronto/index.html`
    or `docs/toronto/data/*`; they are build output.
- Edit `pipeline/template.html` for the page, and the Python scripts in `pipeline/` for data.
- Rebuild with `pipeline/run.sh` (needs Python with shapely, and Node; it runs
  `npm install` for mapshaper and Leaflet). After a page-only change,
  `python3 pipeline/assemble.py` is enough.
- Raw inputs live in `pipeline/raw/`; `pipeline/SOURCES.md` records where each one came from.
- The City of Toronto GIS server (gis.toronto.ca) can't be reached from most sandboxes.
  `.github/workflows/fetch-streets.yml` shows the pattern: fetch it in GitHub Actions and
  commit the raw file. It also rejects bursts of parallel requests, so fetch one layer at a time.

## Conventions
- One change per commit, with a plain-English message saying what changed and why.
- Test in a browser at desktop and phone widths, and in light and dark themes, before pushing.
- Keep the map uncluttered. Landmarks and known-as names are deliberately short, curated
  lists, not exhaustive databases.
- Address search uses OpenStreetMap Nominatim, whose usage policy forbids
  autocomplete-as-you-type. Live suggestions come only from the local landmark list.
- Keep `README.md` current when features change. It doubles as the portfolio write-up.

/* City Layers map engine. Everything city-specific comes from CITY (cities/<city>/city.json),
   inlined above this script by engine/assemble.py, and from the city's data/ folder. */
(() => {
const DATA = 'data/';
const slug = s => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);

/* Text templates from the config: "{name}" fills from a feature's properties, "{f.num}" walks into
   nested objects, a list becomes "a, b". A part in [square brackets] is dropped when a field inside it
   is missing; a missing field outside brackets blanks the whole text. */
function fill(tpl, ctx){
  const val = k => k.split('.').reduce((o, p) => o == null ? undefined : o[p], ctx);
  const sub = (s, miss) => s.replace(/\{([\w.]+)\}/g, (m, k) => {
    const v = val(k);
    if (v == null || v === '') { miss(); return ''; }
    return Array.isArray(v) ? v.join(', ') : v;
  });
  let missing = false;
  const out = sub(tpl.replace(/\[([^\]]*)\]/g, (m, inner) => { let gone = false; const r = sub(inner, () => { gone = true; }); return gone ? '' : r; }), () => { missing = true; });
  return missing ? '' : out;
}

const LAYERS = CITY.groups.flatMap(([, items]) => items);
const byKind = k => LAYERS.find(it => it.kind === k);
const UNITS = byKind('units'), METRO = byKind('metro');
const AREA_KINDS = ['fill', 'units', 'outline', 'patches', 'districts'];   // polygon layers the "What's here" card tests against
/* School board wards ("boards" kind): one file holds every board's wards, each feature tagged with its
   board. The panel shows one board at a time (it.boards: [id, short, long], the first is the default);
   the card looks up the spot's ward in every board. */
const BOARDS = LAYERS.filter(it => it.kind === 'boards');
const boardPick = {};
BOARDS.forEach(it => { boardPick[it.id] = it.boards[0][0]; });
const boardOf = (it, id) => it.boards.find(b => b[0] === id);
const boardCtx = (it, f) => { const b = boardOf(it, f.properties.board) || []; return Object.assign({}, f.properties, {short: b[1], long: b[2]}); };
function boardHits(it, x, y){
  const out = {}, fc = data.layers[it.id]; if (!fc) return out;
  fc.features.forEach(f => { if (!out[f.properties.board] && contains(f.geometry, x, y)) out[f.properties.board] = f; });
  return out;
}

/* Neighbourhood lenses (tiers from the city's profile data). One shows at a time. */
const LENSES = {};
CITY.lens.lenses.forEach(L_ => { LENSES[L_.id] = L_; });
const FILTERS = CITY.lens.filters;
/* A "pick a type" lens (e.g. housing type) shades units by the share of one category the viewer picks:
   d[L_.field] is a list of shares, L_.pick names the categories in the same order, L_.cuts splits a
   share into the lens's tiers. Every other lens reads a precomputed tier, d[L_.key]. */
const pick = {};
CITY.lens.lenses.forEach(L_ => { if (L_.pick) pick[L_.id] = L_.pick[0][0]; });
function keyOf(L_, d){
  if (!d) return null;
  if (!L_.pick) return d[L_.key];
  const i = L_.pick.findIndex(p => p[0] === pick[L_.id]), v = d[L_.field] && d[L_.field][i];
  if (v == null) return null;
  const t = L_.cuts.findIndex(c => v < c);
  return L_.tiers[t < 0 ? L_.tiers.length - 1 : t][0];
}
const FIRST_LENS = CITY.lens.lenses[0].id;
// Each lens tier's fill colour, written once from the config.
const tierCss = document.createElement('style');
tierCss.textContent = CITY.lens.lenses.map(L_ => L_.tiers.map(([k, , v]) => '.lens.' + L_.id + '-' + k + '{fill:var(' + v + ')}').join(' ')).join('\n');
document.head.appendChild(tierCss);
// The shortlist: tiers picked in any lens, plus a maximum for a "minutes" lens. Empty means "any".
const filt = {};
const clearFilters = () => FILTERS.forEach(f => { filt[f.lens] = f.max ? 0 : new Set(); });
clearFilters();
const filtOn = () => FILTERS.some(f => f.max ? filt[f.lens] > 0 : filt[f.lens].size);
const matches = d => !!d && FILTERS.every(f => {
  const L_ = LENSES[f.lens];
  if (f.max) return !filt[f.lens] || (d[L_.minutes] != null && d[L_.minutes] <= filt[f.lens]);
  return !filt[f.lens].size || filt[f.lens].has(keyOf(L_, d));
});
const lensClass = d => { const L_ = LENSES[lens], k = keyOf(L_, d); return 'lens ' + (k ? L_.id + '-' + k : '') + (filtOn() && !matches(d) ? ' out' : ''); };
let lens = FIRST_LENS;
const TIER_LABEL = {};
Object.values(LENSES).forEach(L_ => L_.tiers.forEach(([k, label, v]) => { TIER_LABEL[L_.key + ':' + k] = [label, v]; }));
const tierOf = d => { const L_ = LENSES[lens], k = keyOf(L_, d); if (!k) return '';
  return L_.pick ? pickLabel(L_) + ': ' + TIER_LABEL[L_.key + ':' + k][0] : TIER_LABEL[L_.key + ':' + k][0]; };
const pickOf = L_ => L_.pick.find(p => p[0] === pick[L_.id]) || L_.pick[0];
const pickLabel = L_ => pickOf(L_)[1], pickLong = L_ => pickOf(L_)[2] || pickOf(L_)[1].toLowerCase();

const map = L.map('map', {zoomSnap:.25, zoomDelta:.5, minZoom:8.5, maxZoom:17, attributionControl:true, zoomControl:false, preferCanvas:false});
// Bottom-left, just beside the layer panel: the panel covers the top-left corner and the What's here card the right side. Phones pinch to zoom, so the buttons are hidden there.
L.control.zoom({position:'bottomleft'}).addTo(map);
map.attributionControl.setPrefix(false);
window.cityMap = map;
map.attributionControl.addAttribution(CITY.attribution);
const CITY_BOUNDS = L.latLngBounds(CITY.view.city);
const REGION_VIEW = L.latLngBounds(CITY.view.region);
const wide = () => !matchMedia('(max-width:760px)').matches;
map.fitBounds(CITY_BOUNDS, wide() ? {paddingTopLeft:[330,20], paddingBottomRight:[350,20]} : {paddingTopLeft:[0,150], paddingBottomRight:[0,90]});
map.setMaxBounds(L.latLngBounds(CITY.view.max));  // the region plus a margin

const panes = [['base',200],['fill',350],['lines',420],['streets',400],['civic',430],['hwy',450],['rail',460],['mask',465],['focus',468],['transit',470],['stlbl',475],['pts',480],['pin',620]];
panes.forEach(([n,z]) => { map.createPane(n); map.getPane(n).style.zIndex = z; });
map.getPane('base').style.pointerEvents = 'none';
map.getPane('stlbl').style.pointerEvents = 'none';
map.getPane('mask').style.pointerEvents = 'none';
map.getPane('focus').style.pointerEvents = 'none';

const layers = {}; const data = {layers: {}};
const get = f => fetch(DATA + (f.includes('.') ? f : f + '.geojson')).then(r => { if (!r.ok) throw new Error(f); return r.json(); });

function zoomClasses(){
  const z = map.getZoom(), el = map.getContainer();
  [10,11,12,13,14].forEach(t => el.classList.toggle('z'+t, z >= t - .01));
}
map.on('zoomend', zoomClasses); zoomClasses();

/* Label declutter: after each move, place labels in priority order and hide any that would overlap
   a label already placed. Icons stay; hovering an icon still shows its name. */
const LABEL_PRIORITY = ['.lbl-focus', '.lm.t1 b', '.lm.t2 b', '.lm.inst b', '.lbl-stn.end', '.lbl-go.end', '.shield', '.lbl-stn', '.lbl-go', '.lbl-cult', '.lbl-area', '.lbl-nbhd', '.lbl-ward, .lbl-prov, .lbl-fed, .lbl-sbw', '.lbl-bia', '.lbl-hd'];
let declutterQueued = false;
function declutter(){
  declutterQueued = false;
  const box = map.getContainer().getBoundingClientRect(), kept = [], seen = new Set();
  const el = map.getContainer();
  el.querySelectorAll('.clash').forEach(n => n.classList.remove('clash'));
  LABEL_PRIORITY.forEach(sel => el.querySelectorAll(sel).forEach(n => {
    if (seen.has(n)) return;  // e.g. a line-end label matches both '.lbl-stn.end' and '.lbl-stn'
    seen.add(n);
    const r = n.getBoundingClientRect();
    if (!r.width || r.right < box.left || r.left > box.right || r.bottom < box.top || r.top > box.bottom) return;
    const pad = 2;
    if (kept.some(k => r.left < k.right + pad && r.right > k.left - pad && r.top < k.bottom + pad && r.bottom > k.top - pad)) n.classList.add('clash');
    else kept.push(r);
  }));
}
function queueDeclutter(){ if (!declutterQueued){ declutterQueued = true; requestAnimationFrame(() => requestAnimationFrame(declutter)); } }
map.on('zoomend moveend layeradd layerremove', queueDeclutter);

function label(text, cls, latlng){
  return L.tooltip({permanent:true, direction:'center', className:'lbl ' + cls, pane:'tooltipPane', interactive:false}).setLatLng(latlng).setContent(text);
}
const ll = p => [p[1], p[0]];
function hoverTip(layer, text){ layer.bindTooltip(text, {sticky:true, className:'hover-tip', direction:'top', offset:[0,-8]}); }

function polyLayer(fc, opts){
  const g = L.layerGroup();
  const geo = L.geoJSON(fc, {pane: opts.pane || 'fill', style: f => ({className: opts.cls(f), weight: 1}),
    onEachFeature: (f, lyr) => { if (opts.hover) hoverTip(lyr, opts.hover(f)); lyr.on('click', e => inspect(e.latlng)); }});
  g.addLayer(geo);
  if (opts.label) fc.features.forEach(f => { const t = opts.label(f); if (t) g.addLayer(label(t, opts.lcls(f), ll(f.properties.lp))); });
  return g;
}

/* ---------- geometry helpers for "What's here" ---------- */
function inRing(x, y, r){ let ins = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++){ const xi=r[i][0], yi=r[i][1], xj=r[j][0], yj=r[j][1]; if (((yi>y)!==(yj>y)) && (x < (xj-xi)*(y-yi)/(yj-yi)+xi)) ins = !ins; } return ins; }
function inPoly(x, y, c){ if (!inRing(x, y, c[0])) return false; for (let k = 1; k < c.length; k++) if (inRing(x, y, c[k])) return false; return true; }
function contains(geom, x, y){ if (geom.type === 'Polygon') return inPoly(x, y, geom.coordinates); if (geom.type === 'MultiPolygon') return geom.coordinates.some(c => inPoly(x, y, c)); return false; }
function hit(fc, x, y){ return fc ? fc.features.find(f => contains(f.geometry, x, y)) : null; }
function metres(a, b){ const k = Math.PI/180, dx = (a[0]-b[0])*k*Math.cos(a[1]*k)*6371000, dy = (a[1]-b[1])*k*6371000; return Math.hypot(dx, dy); }

/* ---------- build layers ---------- */
function buildBase(fc, regions){
  const g = L.geoJSON(fc, {pane:'base', interactive:false, style: f => ({className: {city:'base-city', neighbour:'base-out', outside:'base-far'}[f.properties.kind]})});
  g.addTo(map);
  fc.features.filter(f => f.properties.kind === 'neighbour').forEach(f => label(f.properties.name, 'lbl-muni', ll(f.properties.lp)).addTo(map));
  regions.features.forEach(f => label(f.properties.name, 'lbl-region', ll(f.geometry.coordinates)).addTo(map));
  (CITY.water || []).forEach(w => label(w.name, 'lbl-lake ' + w.cls, w.at).addTo(map));
  map.on('click', e => inspect(e.latlng));
}

const GLYPH = {
  university: '<path d="M12 3 1 9l11 6 9-4.9V16h2V9zM5 13.2V17l7 4 7-4v-3.8L12 17z"/>',
  college: '<path d="M2 5.5c3.2-1.6 6.6-1.4 9.2.8V20c-2.6-2.1-6-2.3-9.2-.8zm20 0c-3.2-1.6-6.6-1.4-9.2.8V20c2.6-2.1 6-2.3 9.2-.8z"/>',
  hospital: '<path d="M9.5 3h5v6.5H21v5h-6.5V21h-5v-6.5H3v-5h6.5z"/>',
  sports: '<path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 2.2a7.8 7.8 0 0 1 7.2 4.8H4.8A7.8 7.8 0 0 1 12 4.2zM4.8 15h14.4a7.8 7.8 0 0 1-14.4 0z"/>',
  park: '<path d="M12 2 6.5 9.5h3L5 16h6v6h2v-6h6l-4.5-6.5h3z"/>',
  music: '<path d="M20 2 8 4.3v11.1A3.5 3.5 0 1 0 10 18.5V9.2l8-1.5v5.7a3.5 3.5 0 1 0 2 3.1z"/>',
  civic: '<path d="M12 1.5 2 6.5V9h20V6.5zM4 10.5v7h3v-7zm6.5 0v7h3v-7zm6.5 0v7h3v-7zM2 19v2.5h20V19z"/>',
  campus: '<path d="M12 3 1 9l11 6 9-4.9V16h2V9zM5 13.2V17l7 4 7-4v-3.8L12 17z"/>',
  culture: '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
  airport: '<path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/>',
};
const svg = d => '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' + d + '</svg>';
const SWATCH = {knownas: 'Aa', landmarks: svg(GLYPH.culture)};
const swatchOf = it => it.kind === 'places' ? svg(GLYPH[it.cat] || GLYPH.culture) : (SWATCH[it.kind] || '');
// Representation layers draw in one of three styles, by level of government.
const OUTLINE = {city:'ward', state:'prov', national:'fed'};

/* Suburban lens: free-flow drive time to the downtown hub, by municipality, in the regional view only. */
const DRIVE_TIERS = [['d1', 'Under 30 min', '--drv-1', 30], ['d2', '30–60 min', '--drv-2', 60], ['d3', '60–90 min', '--drv-3', 90], ['d4', '90 min or more', '--drv-4', Infinity]];
const driveTier = m => m == null ? null : DRIVE_TIERS.find(t => m < t[3]);
const SUBURBS = LAYERS.find(it => it.kind === 'suburbs');

/* One builder per kind of layer. Each gets its config entry and its loaded data. */
const KINDS = {
  fill: (it, fc) => {
    const major = it.size === 'major';
    return polyLayer(fc, {cls: f => (major ? 'fill-major ' : 'fill-minor ') + slug(f.properties.name), label: f => f.properties.name, lcls: () => major ? 'lbl-boro' : 'lbl-area', hover: f => f.properties.name});
  },
  units: (it, fc) => polyLayer(fc, {pane:'lines', cls: () => 'nbhd', label: f => f.properties.name, lcls: () => 'lbl-nbhd', hover: f => fill(it.hover || '{name}', f.properties)}),
  outline: (it, fc) => {
    const c = OUTLINE[it.level];
    return polyLayer(fc, {pane:'civic', cls: () => c, label: f => fill(it.label, f.properties), lcls: () => 'lbl-' + c, hover: f => fill(it.hover, f.properties)});
  },
  // Protected districts (heritage, landmark): a dashed outline with a light wash, so the streets inside still read.
  districts: (it, fc) => polyLayer(fc, {pane:'civic', cls: () => 'hd', label: f => fill(it.label, f.properties), lcls: () => 'lbl-hd', hover: f => fill(it.hover, f.properties)}),
  // Trustee wards: only the picked board's wards are drawn; g._pick swaps boards.
  boards: (it, fc) => {
    const g = L.layerGroup(), per = {};
    it.boards.forEach(([b]) => { per[b] = polyLayer({type: 'FeatureCollection', features: fc.features.filter(f => f.properties.board === b)},
      {pane:'civic', cls: () => 'sbw', label: f => fill(it.label, boardCtx(it, f)), lcls: () => 'lbl-sbw', hover: f => fill(it.hover, boardCtx(it, f))}); });
    g.addLayer(per[boardPick[it.id]]);
    g._pick = b => { Object.values(per).forEach(l => g.removeLayer(l)); g.addLayer(per[b]); };
    return g;
  },
  patches: (it, fc) => polyLayer(fc, {pane:'civic', cls: () => 'bia', label: f => fill(it.label, f.properties), lcls: () => 'lbl-bia', hover: f => fill(it.hover, f.properties)}),
  lens: (it, [fc, prof]) => {
    const g = L.geoJSON(fc, {pane:'fill', style: f => {
      return {className: lensClass(prof[String(f.properties.code)])};
    }, onEachFeature: (f, lyr) => {
      lyr.bindTooltip(() => { const t = tierOf(prof[String(f.properties.code)]); return f.properties.name + (t ? ' · ' + t : ''); },
        {sticky:true, className:'hover-tip', direction:'top', offset:[0,-8]});
      lyr.on('click', e => inspect(e.latlng));
    }});
    g._restyle = () => g.eachLayer(l => {
      const d = prof[String(l.feature.properties.code)], el = l.getElement && l.getElement();
      if (el) el.setAttribute('class', lensClass(d) + ' leaflet-interactive');
    });
    return g;
  },
  rail: (it, [lines, stns, linesInner]) => {
    const g = L.layerGroup();
    // Two versions of the lines: the full routes (region view) and clipped at the city limits (city view).
    const full = L.layerGroup(), inner = L.layerGroup();
    // Lines that share track near the hub fan out sideways as you zoom in (offset in screen pixels).
    const gap = () => { const z = map.getZoom(); return z < 11 ? 0 : z < 12 ? 2 : z < 13 ? 3 : 4; };
    const w = () => { const z = map.getZoom(); return z < 11 ? 2.2 : z < 13 ? 3 : 3.5; };
    const segs = [];
    [[lines, full], [linesInner, inner]].forEach(([fc, grp]) => fc.features.forEach(f => {
      const parts = f.geometry.type === 'LineString' ? [f.geometry.coordinates] : f.geometry.coordinates;
      parts.forEach(part => {
        const pl = L.polyline(part.map(ll), {pane:'rail', className:'go-line', color: f.properties.color, weight: w(), offset: f.properties.offset * gap()});
        hoverTip(pl, fill((it.lineHover || {})[f.properties.line] || it.hover, f.properties));
        pl.on('click', e => inspect(e.latlng));
        grp.addLayer(pl); segs.push([pl, f]);
      });
    }));
    g.addLayer(full);
    g._scope = s => { const [on, off] = s === 'inner' ? [inner, full] : [full, inner]; g.removeLayer(off); g.addLayer(on); };
    map.on('zoomend', () => segs.forEach(([pl, f]) => { pl.setStyle({weight: w()}); if (pl.setOffset) pl.setOffset(f.properties.offset * gap()); }));
    // A station is a line end if it is the last stop on any line.
    const ends = lines.features.map(f => f.geometry.coordinates[f.geometry.coordinates.length - 1]);
    stns.features.forEach(f => {
      const c = f.geometry.coordinates, p = f.properties;
      const end = ends.some(e => Math.abs(e[0] - c[0]) < .01 && Math.abs(e[1] - c[1]) < .008);
      const out = !hit(data.footprint, c[0], c[1]) ? ' go-out' : '';
      const m = L.circleMarker(ll(c), {pane:'pts', radius: p.hub ? 6 : end ? 4.5 : 3.5, className: 'go-stn' + (p.hub ? ' hub' : '') + (end ? ' end' : '') + out});
      hoverTip(m, p.name + ' · ' + p.lines.join(', '));
      m.on('click', e => inspect(e.latlng));
      g.addLayer(m);
      g.addLayer(L.tooltip({permanent:true, direction:'right', offset:[6, 0], className:'lbl lbl-go' + (end || p.hub ? ' end' : '') + out, interactive:false}).setLatLng(ll(c)).setContent(esc(p.name)));
    });
    return g;
  },
  // Institutions by category (universities, colleges, hospitals…): one file, one layer per category.
  // Icons from zoom 11, names from 14. Describe only: name and what it is, nothing ranked.
  places: (it, fc) => {
    const g = L.layerGroup();
    fc.features.filter(f => f.properties.cat === it.cat).forEach(f => {
      const p = f.properties;
      const m = L.marker(ll(f.geometry.coordinates), {pane:'pts', keyboard:false, riseOnHover:true,
        icon: L.divIcon({className:'', iconSize:[0, 0], html:'<span class="lm inst in-' + p.cat + (p.ed ? ' ed' : '') + '"><i>' + svg(GLYPH[p.cat] || GLYPH.culture) + '</i><b>' + esc(p.name) + '</b></span>'})});
      hoverTip(m, fill(it.hover || '{name}[ · {sub}]', p) + (p.ed && it.edText ? ' · ' + it.edText : ''));
      m.on('click', () => goTo(L.latLng(f.geometry.coordinates[1], f.geometry.coordinates[0]), p.name, false));
      g.addLayer(m);
    });
    return g;
  },
  landmarks: (it, fc) => {
    const g = L.layerGroup();
    fc.features.forEach(f => {
      const p = f.properties;
      const m = L.marker(ll(f.geometry.coordinates), {pane:'pts', keyboard:false, riseOnHover:true,
        icon: L.divIcon({className:'', iconSize:[0, 0], html:'<span class="lm ' + p.cat + ' t' + p.tier + '"><i>' + svg(GLYPH[p.cat]) + '</i><b>' + esc(p.name) + '</b></span>'})});
      hoverTip(m, p.name + ' · ' + p.catLabel);
      m.on('click', () => goTo(L.latLng(f.geometry.coordinates[1], f.geometry.coordinates[0]), p.name, false));
      g.addLayer(m);
    });
    return g;
  },
  knownas: (it, fc) => {
    const g = L.layerGroup();
    fc.features.forEach(f => g.addLayer(label(f.properties.name, 'lbl-cult' + (f.properties.kind === 'enclave' ? ' enclave' : ''), ll(f.geometry.coordinates))));
    return g;
  },
  streets: (it, fc) => {
    // Arterial roads, with names laid along the line. Labels are re-placed after every
    // move so they never overlap each other; majors win over minors, longer streets first.
    const g = L.layerGroup(), labels = L.layerGroup();
    const w = () => { const z = map.getZoom(); return z < 11 ? [2, 1] : z < 12 ? [3, 1.6] : z < 13 ? [4.2, 2.6] : z < 14 ? [6, 4] : [8, 5.6]; };
    const k = f => f.properties.cls === 'major' ? 1 : .75;
    const cas = L.geoJSON(fc, {pane:'streets', interactive:false, style: f => ({className:'st-case ' + f.properties.cls, weight: w()[0] * k(f)})});
    const core = L.geoJSON(fc, {pane:'streets', style: f => ({className:'st-core ' + f.properties.cls, weight: w()[1] * k(f)}),
      onEachFeature: (f, lyr) => { hoverTip(lyr, f.properties.name); lyr.on('click', e => inspect(e.latlng)); }});
    map.on('zoomend', () => { cas.eachLayer(l => l.setStyle({weight: w()[0] * k(l.feature)})); core.eachLayer(l => l.setStyle({weight: w()[1] * k(l.feature)})); });
    g.addLayer(cas); g.addLayer(core); g.addLayer(labels);
    const streets = fc.features.map(f => {
      const parts = (f.geometry.type === 'LineString' ? [f.geometry.coordinates] : f.geometry.coordinates).map(p => p.map(c => L.latLng(c[1], c[0])));
      return {name: f.properties.name, cls: f.properties.cls, parts: parts.map(p => ({pts: p, b: L.latLngBounds(p)}))};
    });
    const ctx = document.createElement('canvas').getContext('2d');
    const rect = (x, y, hw, hh, r) => ({x, y, hw, hh, ax: [[Math.cos(r), Math.sin(r)], [-Math.sin(r), Math.cos(r)]]});
    const overlap = (A, B) => [...A.ax, ...B.ax].every(([ux, uy]) => {
      const ext = R => R.hw * Math.abs(R.ax[0][0] * ux + R.ax[0][1] * uy) + R.hh * Math.abs(R.ax[1][0] * ux + R.ax[1][1] * uy);
      return Math.abs((B.x - A.x) * ux + (B.y - A.y) * uy) < ext(A) + ext(B);
    });
    const pointAt = (px, d, t) => { let i = 1; while (i < d.length - 1 && d[i] < t) i++; const s = (t - d[i-1]) / ((d[i] - d[i-1]) || 1); return L.point(px[i-1].x + (px[i].x - px[i-1].x) * s, px[i-1].y + (px[i].y - px[i-1].y) * s); };
    function place(){
      labels.clearLayers();
      const z = map.getZoom();
      if (!map.hasLayer(g) || z < 12) return;
      const size = map.getSize(), view = map.getBounds(), boxes = [], seen = {}, fam = getComputedStyle(document.body).fontFamily;
      const SP = z < 13 ? 420 : z < 14 ? 340 : 280;
      // Keep clear of other labels, shields and the panels floating over the map.
      const mr = map.getContainer().getBoundingClientRect();
      document.querySelectorAll('#search, #here, #panel, .leaflet-tooltip.lbl, .shield, .lm i, .lm b, .stn, .leaflet-pin-pane > *').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width && r.height) boxes.push(rect((r.left + r.right) / 2 - mr.left, (r.top + r.bottom) / 2 - mr.top, r.width / 2 + 3, r.height / 2 + 3, 0));
      });
      let count = 0;
      for (const s of streets){
        if ((s.cls === 'minor' && z < 13) || count >= 90) continue;
        ctx.font = (s.cls === 'major' ? '600 11.5px ' : '500 10.5px ') + fam;
        const tw = ctx.measureText(s.name).width + 8, th = s.cls === 'major' ? 15 : 14;
        const mine = seen[s.name] || (seen[s.name] = []);
        for (const part of s.parts){
          if (!view.intersects(part.b)) continue;
          const px = part.pts.map(p => map.latLngToContainerPoint(p));
          const d = [0]; for (let i = 1; i < px.length; i++) d.push(d[i-1] + px[i].distanceTo(px[i-1]));
          const total = d[d.length-1];
          if (total < tw * 1.3) continue;
          for (let at = Math.max(tw / 2, Math.min(SP / 2, total / 2)); at + tw / 2 <= total; at += 40){
            const a = pointAt(px, d, at - tw / 2), b = pointAt(px, d, at + tw / 2), c0 = pointAt(px, d, at);
            if (c0.x < 20 || c0.y < 20 || c0.x > size.x - 20 || c0.y > size.y - 20) continue;
            if (a.distanceTo(b) < tw * .94) continue;               // too curvy here
            if (mine.some(p => p.distanceTo(c0) < SP)) continue;     // same street labelled nearby
            let ang = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI;
            if (ang > 90) ang -= 180; if (ang < -90) ang += 180;     // keep text upright
            const r = ang * Math.PI / 180;
            // On the street if there's room, otherwise just beside it (e.g. where a subway runs along it).
            let c = null, box;
            for (const off of [0, th / 2 + 9, -(th / 2 + 9)]){
              const q = L.point(c0.x - Math.sin(r) * off, c0.y + Math.cos(r) * off);
              const bx = rect(q.x, q.y, tw / 2, th / 2, r);
              if (!boxes.some(o => overlap(o, bx))) { c = q; box = bx; break; }
            }
            if (!c) continue;
            boxes.push(box); mine.push(c0); count++;
            labels.addLayer(L.marker(map.containerPointToLatLng(c), {pane:'stlbl', interactive:false, keyboard:false,
              icon: L.divIcon({className:'', iconSize:null, html:'<span class="st-lbl ' + s.cls + '" style="transform:translate(-50%,-50%) rotate(' + ang.toFixed(1) + 'deg)">' + esc(s.name) + '</span>'})}));
          }
        }
      }
    }
    map.on('moveend', place); g.on('add', () => setTimeout(place));
    return g;
  },
  highways: (it, [fc, outer, outerShields]) => {
    const g = L.layerGroup();
    const w = () => { const z = map.getZoom(); return z < 11 ? [5, 2.4] : z < 13 ? [7, 3.6] : [10, 5.5]; };
    const cas = L.geoJSON(fc, {pane:'hwy', interactive:false, style: f => ({className:'hwy-case', weight: w()[0]})});
    const core = L.geoJSON(fc, {pane:'hwy', style: f => ({className:'hwy-core ' + f.properties.kind, weight: w()[1]}),
      onEachFeature: (f, lyr) => { hoverTip(lyr, f.properties.name); lyr.on('click', e => inspect(e.latlng)); }});
    map.on('zoomend', () => { cas.eachLayer(l => l.setStyle({weight: w()[0]})); core.eachLayer(l => l.setStyle({weight: w()[1]})); });
    g.addLayer(cas); g.addLayer(core);
    // Beyond the city limits (OpenStreetMap): same look, shields stay visible when zoomed out to the region.
    const gcas = L.geoJSON(outer, {pane:'hwy', interactive:false, style: () => ({className:'hwy-case outer', weight: w()[0]})});
    const gcore = L.geoJSON(outer, {pane:'hwy', style: () => ({className:'hwy-core outer', weight: w()[1]}),
      onEachFeature: (f, lyr) => { hoverTip(lyr, f.properties.name); lyr.on('click', e => inspect(e.latlng)); }});
    map.on('zoomend', () => { gcas.eachLayer(l => l.setStyle({weight: w()[0]})); gcore.eachLayer(l => l.setStyle({weight: w()[1]})); });
    g.addLayer(gcas); g.addLayer(gcore);
    outerShields.features.forEach(f => {
      const p = f.properties, html = '<span class="shield outer' + (p.toll ? ' toll' : '') + '">' + esc(p.toll ? it.tollShield : p.route) + '</span>';
      g.addLayer(L.marker(ll(f.geometry.coordinates), {pane:'pts', interactive:false, keyboard:false, icon: L.divIcon({className:'', html, iconSize:null})}));
    });
    fc.features.forEach(f => {
      const parts = f.geometry.type === 'LineString' ? [f.geometry.coordinates] : f.geometry.coordinates;
      const longest = parts.reduce((a, b) => b.length > a.length ? b : a);
      const at = (it.repeat || {})[f.properties.route] || [.5];
      at.forEach((t, i) => {
        const p = longest[Math.floor((longest.length - 1) * t)];
        const html = '<span class="shield ' + (f.properties.kind === 'city' ? 'city' : '') + (i ? ' minor' : '') + '">' + esc(it.shields[f.properties.route] || f.properties.route) + '</span>';
        g.addLayer(L.marker(ll(p), {pane:'pts', interactive:false, keyboard:false, icon: L.divIcon({className:'', html, iconSize:null})}));
      });
    });
    return g;
  },
  suburbs: (it, base) => polyLayer({type: 'FeatureCollection', features: base.features.filter(f => f.properties.kind === 'neighbour')}, {
    cls: f => { const t = driveTier(f.properties.drive); return 'drv ' + (f.properties.rest || !t ? 'rest' : t[0]); },
    hover: f => f.properties.name + (f.properties.drive != null && !f.properties.rest ? ' · about ' + f.properties.drive + ' min' : '')}),
  metro: (it, [lines, stns]) => {
    const g = L.layerGroup();
    const w = () => { const z = map.getZoom(); return z < 11 ? 3 : z < 13 ? 4.5 : 6; };
    const lg = L.geoJSON(lines, {pane:'transit', style: f => ({className:'sub-line l' + f.properties.line, weight: w()}),
      onEachFeature: (f, lyr) => { hoverTip(lyr, f.properties.name); lyr.on('click', e => inspect(e.latlng)); }});
    map.on('zoomend', () => lg.eachLayer(l => l.setStyle({weight: w()})));
    g.addLayer(lg);
    const names = L.layerGroup();
    stns.features.forEach(f => {
      const x = f.properties.lines.length > 1, end = f.properties.terminus;
      const m = L.circleMarker(ll(f.geometry.coordinates), {pane:'pts', radius: x || end ? 5 : 3.5, className: 'stn' + (x ? ' x' : '') + (end ? ' end' : '')});
      hoverTip(m, fill(it.stationHover || '{name}', f.properties));
      m.on('click', e => inspect(e.latlng));
      g.addLayer(m);
      names.addLayer(L.tooltip({permanent:true, direction:'right', offset:[6,0], className:'lbl lbl-stn' + (f.properties.terminus ? ' end' : ''), interactive:false}).setLatLng(ll(f.geometry.coordinates)).setContent(f.properties.name));
    });
    g._names = names;
    return g;
  },
};
// Drawing order: the order layers join the map decides which sits on top within a pane.
const RANK = it => ({fill: it.size === 'major' ? 0 : 1, lens: 2, suburbs: 2, patches: 3, districts: 3, units: 4, boards: 4.5, outline: {national: 5, state: 6, city: 7}[it.level], knownas: 8, streets: 9, highways: 10, rail: 11, metro: 12, landmarks: 13, places: 14})[it.kind];
const ORDER = LAYERS.map(it => it).sort((a, b) => RANK(a) - RANK(b));

/* ---------- panel ---------- */
const state = {};
const host = document.getElementById('layers');
CITY.groups.forEach(([title, items]) => {
  const grp = document.createElement('div'); grp.className = 'grp';
  grp.innerHTML = '<h2>' + title + '</h2>';
  items.forEach(it => {
    const row = document.createElement('label'); row.className = 'row'; row.htmlFor = 'lyr-' + it.id;
    row.innerHTML = '<span class="sw ' + it.id + ' k-' + (it.kind === 'outline' ? it.level : it.kind) + (it.kind === 'places' ? ' in-' + it.cat : '') + '">' + swatchOf(it) + '</span><span class="tx"><b>' + it.name + '</b><span>' + it.note + '</span></span>' +
      '<input type="checkbox" id="lyr-' + it.id + '"' + (it.on ? ' checked' : '') + '><span class="tg" aria-hidden="true"></span>';
    grp.appendChild(row);
    row.querySelector('input').addEventListener('change', e => setLayer(it.id, e.target.checked));
    if (it.kind === 'lens'){
      const box = document.createElement('div'); box.className = 'lensbox'; box.id = 'lensbox'; box.hidden = !it.on;
      box.innerHTML = '<div class="seg" role="radiogroup" aria-label="' + esc(CITY.lens.label) + '">' +
        Object.entries(LENSES).map(([k, L_]) => '<button type="button" role="radio" data-lens="' + k + '" aria-checked="' + (k === lens) + '">' + L_.short + '</button>').join('') +
        '</div><div class="legend" id="legend"></div>' +
        '<div class="finder"><b>Narrow it down</b><span>Pick what you’re looking for. ' + cap(CITY.units.plural) + ' that don’t fit fade out.</span>' +
        FILTERS.map(f => '<div class="frow"><small>' + f.label + '</small><div class="chips">' +
            f.options.map(([v, t]) => '<button type="button" aria-pressed="false" data-f="' + f.lens + '" data-v="' + v + '">' + t + '</button>').join('') + '</div></div>').join('') +
        '<div class="fres" id="fres" hidden><span id="fcount"></span><button type="button" id="fclear">Clear</button></div><div class="flist" id="flist"></div></div>';
      grp.appendChild(box);
      box.querySelectorAll('[data-lens]').forEach(b => b.addEventListener('click', () => setLens(b.dataset.lens)));
      box.querySelectorAll('[data-f]').forEach(b => b.addEventListener('click', () => {
        const k = b.dataset.f, v = b.dataset.v;
        if (typeof filt[k] === 'number') filt[k] = filt[k] === +v ? 0 : +v;
        else filt[k].has(v) ? filt[k].delete(v) : filt[k].add(v);
        applyFilter(); queueHash();
      }));
      box.querySelector('#fclear').addEventListener('click', () => { clearFilters(); applyFilter(); queueHash(); });
    }
    if (it.kind === 'boards' && it.boards.length > 1){   // one board: nothing to pick
      const box = document.createElement('div'); box.className = 'lensbox'; box.id = 'brd-' + it.id; box.hidden = !it.on;
      box.innerHTML = '<div class="chips pick" role="radiogroup" aria-label="' + esc(it.name) + '">' + it.boards.map(([b, short, long]) =>
        '<button type="button" role="radio" data-board="' + b + '" data-layer="' + it.id + '" title="' + esc(long) + '" aria-checked="' + (b === boardPick[it.id]) + '">' + esc(short) + '</button>').join('') +
        '</div><div class="legend"><small id="brdnote-' + it.id + '"></small></div>';
      grp.appendChild(box);
      box.querySelectorAll('[data-board]').forEach(b => b.addEventListener('click', () => setBoard(it.id, b.dataset.board)));
    }
    if (it.kind === 'suburbs'){
      row.classList.add('outer-only'); row.id = 'row-' + it.id;
      const box = document.createElement('div'); box.className = 'lensbox'; box.id = 'drvbox'; box.hidden = true;
      grp.appendChild(box);
    }
    if (it.sub){
      const s = document.createElement('label'); s.className = 'sub';
      s.innerHTML = '<input type="checkbox" id="' + it.sub.id + '"' + (it.sub.on ? ' checked' : '') + '> ' + it.sub.label;
      grp.appendChild(s);
      s.querySelector('input').addEventListener('change', () => { syncStnNames(); queueHash(); });
    }
    state[it.id] = !!it.on;
  });
  host.appendChild(grp);
});
function syncStnNames(){
  const L_ = METRO && layers[METRO.id]; if (!L_) return;
  const want = state[METRO.id] && document.getElementById(METRO.sub.id).checked;
  if (want && !map.hasLayer(L_._names)) L_._names.addTo(map);
  if (!want && map.hasLayer(L_._names)) map.removeLayer(L_._names);
}
function drawDriveLegend(){
  const el = document.getElementById('drvbox'); if (!el || !data.layers) return;
  const subs = (data.outer || {features: []}).features;
  const used = new Set(subs.filter(f => !f.properties.rest).map(f => (driveTier(f.properties.drive) || [])[0]));
  const rest = subs.some(f => f.properties.rest);
  el.innerHTML = '<div class="legend">' + DRIVE_TIERS.filter(t => used.has(t[0])).map(([k, label, v]) => '<div><i style="background:var(' + v + ')"></i>' + label + '</div>').join('') +
    (rest ? '<div><i class="rest"></i>Unincorporated land</div>' : '') +
    '<small>Typical drive to ' + esc(CITY.drive.hubName) + ' with no traffic: the median across each municipality, on empty roads at posted speeds. Most trips take longer; use it to compare places. Tap a spot for the time from there. Source: OpenStreetMap roads, routed with OSRM.</small></div>';
}
function drawLegend(){
  const el = document.getElementById('legend'); if (!el) return;
  const L_ = LENSES[lens];
  const picker = L_.pick ? '<div class="chips pick" role="radiogroup" aria-label="' + esc(L_.short) + '">' + L_.pick.map(([v, t]) =>
    '<button type="button" role="radio" data-pick="' + v + '" aria-checked="' + (pick[L_.id] === v) + '">' + esc(t) + '</button>').join('') + '</div>' : '';
  el.innerHTML = picker + L_.tiers.map(([k, label, v]) => '<div><i style="background:var(' + v + ')"></i>' + label + '</div>').join('') +
    '<small>' + (L_.pick ? fill(L_.note, {type: pickLong(L_)}) : L_.note) + ' Source: ' + (L_.source || CITY.lens.source) + '</small>';
  el.querySelectorAll('[data-pick]').forEach(b => b.addEventListener('click', () => setPick(L_.id, b.dataset.pick)));
}
function setBoard(id, b){
  const it = LAYERS.find(l => l.id === id); if (!it || !boardOf(it, b)) return;
  boardPick[id] = b;
  document.querySelectorAll('[data-layer="' + id + '"][data-board]').forEach(el => el.setAttribute('aria-checked', String(el.dataset.board === b)));
  const n = document.getElementById('brdnote-' + id); if (n) n.textContent = boardOf(it, b)[2] + '. ' + (it.boardNote || '');
  if (layers[id] && layers[id]._pick) layers[id]._pick(b);
  queueHash();
}
function setPick(id, v){
  const L_ = LENSES[id]; if (!L_ || !L_.pick || !L_.pick.some(p => p[0] === v)) return;
  pick[id] = v;
  drawLegend();
  const LL = byKind('lens') && layers[byKind('lens').id];
  if (LL && LL._restyle) LL._restyle();
  queueHash();
}
function applyFilter(){
  document.querySelectorAll('[data-f]').forEach(b => {
    const k = b.dataset.f, v = b.dataset.v;
    b.setAttribute('aria-pressed', String(typeof filt[k] === 'number' ? filt[k] === +v : filt[k].has(v)));
  });
  const LL = byKind('lens') && layers[byKind('lens').id];
  if (LL && LL._restyle) LL._restyle();
  const on = filtOn(), res = document.getElementById('fres'), list = document.getElementById('flist');
  res.hidden = !on; list.innerHTML = '';
  if (!on || !data.profiles) return;
  const hits = data.units.features.filter(f => matches(data.profiles[String(f.properties.code)])).sort((a, b) => a.properties.name.localeCompare(b.properties.name));
  document.getElementById('fcount').textContent = hits.length ? hits.length + ' of ' + data.units.features.length + ' ' + CITY.units.plural + ' fit' : 'No ' + CITY.units.plural + ' fit all of that';
  hits.forEach(f => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = f.properties.name;
    b.addEventListener('click', () => {
      const lp = f.properties.lp, ll_ = L.latLng(lp[1], lp[0]);
      map.flyToBounds(L.geoJSON(f).getBounds(), {padding:[60, 60], maxZoom:14, duration:.8});
      if (matchMedia('(max-width:760px)').matches) panel.classList.add('collapsed');
      inspect(ll_, f.properties.name);
    });
    list.appendChild(b);
  });
}
function setLens(k){
  lens = k;
  document.querySelectorAll('[data-lens]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.lens === k)));
  drawLegend();
  const LL = byKind('lens') && layers[byKind('lens').id];
  if (LL && LL._restyle) LL._restyle();
  queueHash();
}
const kindOf = id => (LAYERS.find(it => it.id === id) || {}).kind;
function setLayer(id, on){
  state[id] = on; queueHash();
  const lyr = layers[id]; if (!lyr) return;
  if (on) { lyr.addTo(map); } else { map.removeLayer(lyr); }
  if (METRO && id === METRO.id) syncStnNames();
  if (kindOf(id) === 'boards'){ const box = document.getElementById('brd-' + id); if (box) box.hidden = !on; if (on) setBoard(id, boardPick[id]); }
  if (kindOf(id) === 'suburbs'){
    document.getElementById('drvbox').hidden = !on;
    if (on && scope === 'inner') map.removeLayer(lyr);   // shown only in the regional view
  }
  if (kindOf(id) === 'lens'){
    document.getElementById('lensbox').hidden = !on;
    drawLegend();
    // Coloured fills on top of each other turn to mud: the lens replaces the other area fills.
    if (on) LAYERS.filter(it => it.kind === 'fill').forEach(o => { const cb = document.getElementById('lyr-' + o.id); if (cb && cb.checked){ cb.checked = false; setLayer(o.id, false); } });
  }
  if (on && kindOf(id) === 'fill'){ const LN = byKind('lens'), cb = LN && document.getElementById('lyr-' + LN.id); if (cb && cb.checked){ cb.checked = false; setLayer(LN.id, false); } }
}
// Reset: back to the starting view (city only, the default layers, the first lens with no filter).
document.getElementById('reset').addEventListener('click', () => {
  LAYERS.forEach(it => {
    const cb = document.getElementById('lyr-' + it.id), want = !!it.on;
    if (cb.checked !== want){ cb.checked = want; setLayer(it.id, want); }
    if (it.sub){ const sb = document.getElementById(it.sub.id); if (sb.checked !== !!it.sub.on){ sb.checked = !!it.sub.on; syncStnNames(); } }
  });
  clearFilters(); applyFilter();
  Object.keys(pick).forEach(id => { pick[id] = LENSES[id].pick[0][0]; });
  BOARDS.forEach(it => setBoard(it.id, it.boards[0][0]));
  setLens(FIRST_LENS);
  setScope('inner', true);
  closeHere();
  // Back to a plain URL; the address bar follows again from the next change.
  clearTimeout(hashTimer); linkReady = false; lastHash = '';
  try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
  armLink();
});
document.getElementById('allOff').addEventListener('click', () => {
  Object.keys(state).forEach(id => { const cb = document.getElementById('lyr-' + id); if (cb.checked){ cb.checked = false; setLayer(id, false); } });
});
const panel = document.getElementById('panel');
document.getElementById('ph').addEventListener('click', () => { if (matchMedia('(max-width:760px)').matches) panel.classList.toggle('collapsed'); });
// The title's city switcher and the hub link: go there, and don't let the tap fold the phone panel.
const citySwitch = document.getElementById('citySwitch');
if (citySwitch){
  const here0 = citySwitch.value;
  citySwitch.addEventListener('change', () => { const to = citySwitch.value; citySwitch.value = here0; location.href = to; });
}
document.querySelectorAll('.ph .switch, .ph .hub-link').forEach(el => el.addEventListener('click', e => e.stopPropagation()));
if (matchMedia('(max-width:760px)').matches) panel.classList.add('collapsed');
// Desktop: fold the panel away for a full view of the map; remembered in this browser.
const unfold = document.getElementById('unfold');
function setFolded(on){
  panel.classList.toggle('folded', on); unfold.hidden = !on;
  try { if (on) localStorage.setItem('panelFolded', '1'); else localStorage.removeItem('panelFolded'); } catch (e) {}
  (on ? unfold : document.getElementById('fold')).focus({preventScroll: true});
}
document.getElementById('fold').addEventListener('click', e => { e.stopPropagation(); setFolded(true); });
unfold.addEventListener('click', () => setFolded(false));
try { if (localStorage.getItem('panelFolded') && wide()){ panel.classList.add('folded'); unfold.hidden = false; } } catch (e) {}

/* ---------- What's here ---------- */
const here = document.getElementById('here');
let pin = null;
const money = v => '$' + (v >= 1e6 ? (v / 1e6).toFixed(v % 1e6 ? 1 : 0) + 'M' : Math.round(v / 1e3) + 'K');
function livingHere(unit){
  const d = unit && data.profiles ? data.profiles[String(unit.properties.code)] : null;
  if (!d) return '';
  const T = CITY.card.living;
  const tier = (key, v) => { const [label, col] = TIER_LABEL[key + ':' + v]; return '<span class="tier"><i style="background:var(' + col + ')"></i>' + esc(label) + '</span>'; };
  const hub = CITY.lens.lenses.find(L_ => L_.minutes);
  return '<div class="live"><dl>' +
    '<dt>Housing</dt><dd>' + tier('cost', d.cost) + '<span>Median home ' + money(d.value) + ' · rent $' + d.rent.toLocaleString(CITY.locale) + '/mo</span><span class="caveat">' + esc(T.caveat) + '</span></dd>' +
    (hub && d[hub.minutes] != null ? '<dt>' + esc(T.hub) + '</dt><dd>' + tier(hub.key, d[hub.key]) + '<span>' + esc(fill(T.hubText, {minutes: d[hub.minutes]})) + '</span></dd>' : '') +
    '<dt>Getting to work</dt><dd>' + tier('commute', d.commute) + '<span>' + d.carPct + '% drive · ' + d.transitPct + '% transit · ' + d.walkBikePct + '% walk or bike</span></dd>' +
    '<dt>Households</dt><dd>' + tier('tenure', d.tenure) + '<span>' + d.renterPct + '% rent</span></dd>' +
    mixRow(T.homes, d.homes, T.homes && T.homes.types.map(t => t[1])) +
    mixRow(T.built, d.built, T.built && T.built.bands) +
    langRow(T.lang, d) +
    '</dl><p>' + esc(fill(T.footer, {name: d.name})) + '</p></div>';
}
/* Description rows (no tiers, never ranked): how homes split by type or by when they were built, as a
   small stacked bar and the shares in words. Shares under 1% are left out of the words. */
function mixRow(cfg, shares, names){
  if (!cfg || !shares || !names) return '';
  const bar = shares.map((v, i) => v > 0 ? '<i style="width:' + v + '%;background:var(--mix-' + (i + 1) + ')"></i>' : '').join('');
  const words = shares.map((v, i) => [names[i], v, i]).filter(x => x[1] >= 1).map(x => '<b class="dot" style="background:var(--mix-' + (x[2] + 1) + ')"></b>' + esc(x[0]) + ' ' + x[1] + '%').join(' · ');
  return '<dt>' + esc(cfg.label) + '</dt><dd><span class="mix" aria-hidden="true">' + bar + '</span><span>' + words + '</span>' +
    (cfg.caveat ? '<span class="caveat">' + esc(cfg.caveat) + '</span>' : '') + '</dd>';
}
/* Home language: the top three, the first always shown and the next two only at 5% or more (the
   config's floor), so a 1% language never reads as a feature of the place. Card only: never a lens,
   a filter or a ranking. */
function langRow(cfg, d){
  if (!cfg || !d.lang || !d.lang.length) return '';
  const floor = cfg.floor == null ? 5 : cfg.floor;
  const top = d.lang.filter((x, i) => i === 0 || x[1] >= floor).slice(0, 3);
  const more = top.length < 2 ? '<span>' + esc(cfg.none || 'No other language above ' + floor + '%') + '</span>' : '';
  return '<dt>' + esc(cfg.label) + '</dt><dd>' + top.map(x => esc(x[0]) + ' ' + x[1] + '%').join(' · ') + more +
    (cfg.note ? '<span class="caveat">' + esc(fill(cfg.note, {multi: d.langMulti})) + '</span>' : '') + '</dd>';
}
// Collapsible card sections. Open/closed is remembered in this browser; phones start with all closed.
const SEC_DEFAULT = matchMedia('(max-width:760px)').matches ? {bounds:false, live:false, reps:false} : {bounds:true, live:true, reps:false};
let secOpen = Object.assign({}, SEC_DEFAULT);
try { Object.assign(secOpen, JSON.parse(localStorage.getItem('cardSections') || '{}')); } catch (e) {}
function section(id, title, body){
  if (!body) return '';
  return '<details class="sec" data-sec="' + id + '"' + (secOpen[id] ? ' open' : '') + '><summary>' + title + '</summary>' + body + '</details>';
}
// Who represents this spot. Names link to their official pages.
function representatives(hits){
  const R = data.reps, cfg = CITY.card.reps; if (!R || !cfg || !hits[cfg.offices[0].layer]) return '';
  const link = r => r && r.name ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.name) + '</a>' : '<span class="vacant">Seat currently vacant</span>';
  const row = (role, r, sub) => '<dt>' + role + '</dt><dd>' + link(r) + (sub ? '<span>' + esc(sub) + '</span>' : '') + '</dd>';
  const date = new Date(...R.updated.split('-').map((v, i) => +v - (i === 1))).toLocaleDateString(CITY.locale, {month:'long', day:'numeric', year:'numeric'});
  return '<div class="live reps"><dl>' +
    cfg.offices.map(o => {
      const h = hits[o.layer]; if (!h) return '';
      const r = R[o.table][String(h.properties[o.key])];
      return row(o.role, r, fill(o.sub, {f: h.properties, r: r || {}}));
    }).join('') + trustees(hits) +
    '</dl><p>' + esc(fill(cfg.note, {date})) + (cfg.trustees && R[cfg.trustees.table] ? ' ' + esc(cfg.trustees.note) : '') + '</p></div>';
}
/* School board trustees: one row per board that covers the spot, plus an optional citywide seat
   (T.citywide, e.g. a board president). Before the election the row lists the candidates; while votes
   are counted it can name who leads (r.leader); once there is a winner (or one candidate was
   acclaimed), the winner, marked as taking office on the start date; from that date, just the trustee.
   Dates and wording come from city.json. */
const isoDate = s => new Date(...s.split('-').map((v, i) => +v - (i === 1)));
const longDate = s => isoDate(s).toLocaleDateString(CITY.locale, {month:'short', day:'numeric'});
function trusteeRow(T, role, r, sub){
  const today = new Date(), started = today >= isoDate(T.starts);
  const dates = {election: longDate(T.election), starts: longDate(T.starts)};
  let dd;
  if (!r) dd = '<span>' + esc(sub) + '</span>';
  else if (r.winner) dd = '<b>' + esc(r.winner) + '</b><span>' + esc(sub + (started ? '' : ' · ' + fill(r.acclaimed ? T.acclaimed : T.elected, dates))) + '</span>';
  else if (r.leader && T.leading) dd = '<b>' + esc(r.leader) + '</b><span>' + esc(sub + ' · ' + fill(T.leading, dates)) + '</span>';
  else {
    const n = r.candidates.length;
    const head = fill(today >= isoDate(T.election) ? T.counting : T.race, Object.assign({n, s: n === 1 ? '' : 's'}, dates));
    dd = '<details class="cands"><summary>' + esc(head) + '</summary><span>' + r.candidates.map(esc).join(' · ') + '</span></details><span>' + esc(sub) + '</span>';
  }
  return '<dt>' + esc(role) + '</dt><dd>' + dd + '</dd>';
}
function trustees(hits){
  const T = CITY.card.reps.trustees, R = data.reps; if (!T || !R || !R[T.table]) return '';
  const it = LAYERS.find(l => l.id === T.layer), bh = hits[T.layer]; if (!it || !bh) return '';
  const rows = it.boards.filter(([b]) => bh[b]).map(([b]) => {
    const ctx = boardCtx(it, bh[b]);
    return trusteeRow(T, fill(T.role, ctx), (R[T.table][b] || {})[String(ctx.num)], fill(T.ward, ctx));
  });
  const C = T.citywide, cb = C && (R[T.table][C.board] || {})[C.key];
  if (cb && rows.length) rows.push(trusteeRow(T, C.role, cb, C.sub));
  return rows.join('');
}
let pinName = '';
function placePin(latlng, name){
  pinName = name || ''; queueHash();
  if (pin) pin.setLatLng(latlng); else pin = L.marker(latlng, {pane:'pin', interactive:false, keyboard:false, icon: L.divIcon({className:'', iconSize:[20, 20], iconAnchor:[10, 10], html:'<span class="pin"></span>'})}).addTo(map);
}
const colorOf = (id, f) => { const it = LAYERS.find(l => l.id === id); return 'var(' + ((it && it.colors && it.colors[f.properties.name]) || '--ink-3') + ')'; };
// Outside the city: the nearest named community (a town, village or larger community, not a small
// neighbourhood), if one is close, as a "Near ..." pill. Skipped when the card is already titled with it.
function nearCommunity(x, y, title){
  if (!data.regionPlaces) return '';
  const big = CITY.regionPlaces.near || [];
  const c = data.regionPlaces.filter(p => big.includes(p.kind)).map(p => [p, metres([x, y], p.at)]).filter(a => a[1] < 2500).sort((a, b) => a[1] - b[1])[0];
  if (!c || c[0].name === title) return '';
  return '<span class="pill"><i style="background:var(--cult-enclave)"></i>Near ' + esc(c[0].name) + '</span>';
}
function inspect(latlng, title, muniName){
  const x = latlng.lng, y = latlng.lat;
  if (!hit(data.footprint, x, y)){
    // A named community already knows its municipality: the map's shapes are trimmed to a coarse
    // shoreline, so a lakeside place can otherwise land just outside them.
    const muni = hit(data.outer, x, y) || (muniName && data.outer.features.find(f => f.properties.name === muniName));
    if (!muni){ here.hidden = false; renderEmpty(CITY.outside.beyond); return; }
    placePin(latlng, title);
    const m = muni.properties;
    here.hidden = false;
    here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>' + esc(title || m.name) + '</strong></div><div class="hb"><button type="button" class="share" aria-label="Share this spot" title="Share a link to this spot">' + SHARE_ICON + '</button><button type="button" aria-label="Close" id="hereX">×</button></div></div>' +
      '<div class="pills">' + nearCommunity(x, y, title) + '<span class="pill"><i style="background:var(--land-out-line)"></i>' + esc(m.name) + '</span><span class="pill"><i style="background:var(--muni-label)"></i>' + esc(fill(CITY.outside.regionPill, m)) + '</span></div>' +
      driveHere(x, y, m) +
      (regionFeature(m.region) && focusKey !== m.region ? '<button type="button" class="focus-go">' + esc(fill(CITY.focus.show, {name: regionName(m.region)})) + '</button>' : '') +
      '<p class="outside-note">' + esc(CITY.outside.note) + '</p>';
    document.getElementById('hereX').onclick = closeHere;
    here.querySelector('.share').onclick = share;
    const fg = here.querySelector('.focus-go'); if (fg) fg.onclick = () => setFocus(m.region, true);
    return;
  }
  placePin(latlng, title);
  const hits = {};
  LAYERS.filter(it => AREA_KINDS.includes(it.kind)).forEach(it => { hits[it.id] = hit(data.layers[it.id], x, y); });
  BOARDS.forEach(it => { hits[it.id] = boardHits(it, x, y); });
  const pillCfg = CITY.card.pills.find(p => p.knownas);
  const near = (data.knownas ? data.knownas.features : []).map(f => [f, metres([x, y], f.geometry.coordinates)]).filter(a => a[1] < 650).sort((a, b) => a[1] - b[1]).slice(0, pillCfg ? pillCfg.knownas : 2);
  const pills = [];
  CITY.card.pills.forEach(p => {
    if (p.knownas) { near.forEach(([f]) => pills.push(['var(--cult-enclave)', f.properties.name])); return; }
    const h = hits[p.layer];
    if (p.else) { if (h) pills.push([colorOf(p.layer, h), h.properties.name]); else if (hits[p.else]) pills.push([colorOf(p.else, hits[p.else]), hits[p.else].properties.name]); return; }
    if (h) pills.push(['var(' + p.color + ')', fill(p.text, h.properties)]);
  });
  const facts = CITY.card.facts.filter(r => !r.onlyInside || hits[r.layer]).map(r => {
    if (r.knownas) return [r.label, near.length ? near.map(a => a[0].properties.name).join(', ') : '—'];
    if (r.boards){ const it = LAYERS.find(l => l.id === r.boards), bh = hits[r.boards] || {};
      const t = it.boards.filter(([b]) => bh[b]).map(([b]) => fill(r.text, boardCtx(it, bh[b]))).join(' · ');
      return [r.label, t || r.empty || '—']; }
    const h = hits[r.layer];
    if (h) return [r.label, fill(r.text, h.properties)];
    if (r.emptyWithin && Object.entries(r.emptyWithin).some(([id, name]) => hits[id] && hits[id].properties.name === name)) return [r.label, '—'];
    return [r.label, r.empty || '—'];
  });
  // Title: a searched place keeps its own name; a dropped pin is named by its neighbourhood (or, failing
  // that, the big area it's in). Coordinates are a last resort, for a spot no layer covers.
  const unit = UNITS && hits[UNITS.id];
  const area = LAYERS.filter(it => it.kind === 'fill').map(it => hits[it.id]).find(Boolean);
  const coords = Math.abs(y).toFixed(4) + '° ' + (y >= 0 ? 'N' : 'S') + ', ' + Math.abs(x).toFixed(4) + '° ' + (x < 0 ? 'W' : 'E');
  const heading = title || (unit && unit.properties.name) || (area && area.properties.name) || coords;
  here.hidden = false;
  here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>' + esc(heading) + '</strong></div><div class="hb"><button type="button" class="share" aria-label="Share this spot" title="Share a link to this spot">' + SHARE_ICON + '</button><button type="button" aria-label="Close" id="hereX">×</button></div></div>' +
    '<div class="pills">' + pills.map(p => '<span class="pill"><i style="background:' + p[0] + '"></i>' + esc(p[1]) + '</span>').join('') + '</div>' +
    standout(unit, heading) +
    section('bounds', 'Boundaries', '<dl class="facts">' + facts.map(f => '<dt>' + f[0] + '</dt><dd>' + esc(f[1]) + '</dd>').join('') + '</dl>') +
    section('live', 'Living here', livingHere(UNITS && hits[UNITS.id])) +
    section('reps', 'Representatives', representatives(hits));
  document.getElementById('hereX').onclick = closeHere;
  here.querySelector('.share').onclick = share;
  here.querySelectorAll('details.sec').forEach(d => d.addEventListener('toggle', () => { secOpen[d.dataset.sec] = d.open; try { localStorage.setItem('cardSections', JSON.stringify(secOpen)); } catch (e) {} }));
}
// What makes the unit stand out among its peers (engine/facts.py, built ahead of time): the strongest fact.
function standout(unit, heading){
  const d = unit && data.profiles ? data.profiles[String(unit.properties.code)] : null;
  const f = d && d.facts && d.facts[0];
  if (!f) return '';
  // The fact is about the unit. When the title already names it, the fact stands alone; otherwise
  // (a searched address or landmark) it says whose it is: "West Town: among the highest home values…".
  const text = heading === d.name ? esc(f.text) : '<b>' + esc(d.name) + ':</b> ' + esc(f.text.charAt(0).toLowerCase() + f.text.slice(1));
  return '<p class="standout"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="m8 1.5 1.9 4 4.4.5-3.3 3 .9 4.3L8 11.1l-3.9 2.2.9-4.3-3.3-3 4.4-.5z"/></svg><span>' +
    text + ' <small>' + esc(f.value) + '</small></span></p>';
}
// Free-flow drive time from the nearest grid point (about 1.5 km apart), and the municipality's typical time.
function driveHere(x, y, m){
  const g = data.driveGrid; if (!g || !CITY.drive) return '';
  let best = null, bd = Infinity;
  g.points.forEach(p => { const d = metres([x, y], p); if (d < bd){ bd = d; best = p; } });
  if (!best || bd > 2000) return '';
  const t = driveTier(best[2]);
  return '<div class="live drive"><dl><dt>Drive to ' + esc(CITY.drive.hubName) + '</dt><dd><span class="tier"><i style="background:var(' + t[2] + ')"></i>About ' + best[2] + ' min from here</span>' +
    (m.drive != null && !m.rest ? '<span>Typical for ' + esc(m.name) + ': ' + m.drive + ' min</span>' : '') +
    '<span class="caveat">With no traffic, at posted speeds. Most trips take longer.</span></dd></dl></div>';
}
function renderEmpty(msg){
  here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>Tap the map</strong></div><button type="button" aria-label="Close" id="hereX">×</button></div><div class="hint">' + esc(msg) + '</div>';
  document.getElementById('hereX').onclick = closeHere;
}
function closeHere(){ here.hidden = true; if (pin){ map.removeLayer(pin); pin = null; queueHash(); } }

/* ---------- Theme: Auto (device setting), Light or Dark; remembered in this browser ---------- */
function applyTheme(choice){
  if (choice === 'light' || choice === 'dark') document.documentElement.dataset.theme = choice;
  else delete document.documentElement.dataset.theme;
  document.querySelectorAll('[data-theme-choice]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.themeChoice === choice)));
  try { if (choice === 'auto') localStorage.removeItem('theme'); else localStorage.setItem('theme', choice); } catch (e) {}
}
let savedTheme = 'auto';
try { savedTheme = localStorage.getItem('theme') || 'auto'; } catch (e) {}
applyTheme(savedTheme);
document.querySelectorAll('[data-theme-choice]').forEach(b => b.addEventListener('click', () => applyTheme(b.dataset.themeChoice)));

/* ---------- Address search (OpenStreetMap Nominatim; one request per search, per its usage policy) ---------- */
const qf = document.getElementById('qf'), q = document.getElementById('q'), go = document.getElementById('go'), results = document.getElementById('results');
let lastSearch = 0;
function showResults(html){ results.innerHTML = html; results.hidden = !html; }
function placeLabel(r){
  const a = r.address || {};
  const street = a.road || a.pedestrian || a.footway || '';
  if (a.house_number && street) return a.house_number + ' ' + street;
  return r.name || street || r.display_name.split(',')[0];
}
function placeSub(r){
  const a = r.address || {};
  const name = r.name && r.name !== placeLabel(r) ? r.name : '';
  const town = data.footprint && !hit(data.footprint, +r.lon, +r.lat) ? (a.city || a.town || a.village || a.municipality) : '';
  return [name, a.neighbourhood || a.suburb || a.quarter, town, a.postcode].filter(Boolean).join(' · ');
}
function choose(r){ goTo(L.latLng(+r.lat, +r.lon), placeLabel(r), true); }
function goTo(latlng, name, fromSearch, minZoom, muniName){
  showResults('');
  if (fromSearch) q.value = name;
  // A spot beyond the city limits isn't visible in city-only mode: switch to the region view.
  if (scope === 'inner' && data.footprint && !hit(data.footprint, latlng.lng, latlng.lat)) setScope('outer', false);
  inspect(latlng, name, muniName);  // fill the card first, so a map-move problem can't hide the result
  const zoom = minZoom || Math.max(map.getZoom(), 15);
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    const size = map.getSize();
    if (calm || !size.x || !size.y) map.setView(latlng, zoom, {animate: false});
    else map.flyTo(latlng, zoom, {duration: .8});
  } catch (err){ try { map.setView(latlng, zoom, {animate: false}); } catch (e2){} }
}
let busy = false;
async function geocode(url){
  // One retry after a pause covers a brief rate-limit (HTTP 429) or network hiccup.
  for (let attempt = 0; ; attempt++){
    try {
      const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 10000);
      const r = await fetch(url, {signal: ctl.signal, headers: {'Accept-Language': 'en'}});
      clearTimeout(timer);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return await r.json();
    } catch (err){
      if (attempt >= 1) throw err;
      await new Promise(r => setTimeout(r, 1500));
    }
  }
}
qf.addEventListener('submit', async e => {
  e.preventDefault();
  const text = q.value.trim();
  if (!text || !data.footprint || busy) return;
  // A place or landmark typed in full goes straight there, without a network search.
  const sugg = suggestions(text), exact = sugg.filter(x => x.s === 0);
  if (exact.length === 1){ exact[0].go(); return; }
  if (exact.length > 1){ showSuggestions(exact, false); return; }
  busy = true;
  const wait = 1100 - (Date.now() - lastSearch);
  if (wait > 0) await new Promise(r => setTimeout(r, wait));
  lastSearch = Date.now();
  go.disabled = true; go.textContent = '…';
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=6&countrycodes=' + CITY.search.country + '&bounded=1' +
    '&viewbox=' + (CITY.search.regionViewbox || CITY.search.viewbox) + '&q=' + encodeURIComponent(text);
  try {
    let list;
    try { list = await geocode(url); }
    catch (err){ showResults('<li class="msg">Address search isn’t responding right now. Try again in a moment, or tap the map instead.</li>'); return; }
    // Keep matches inside the city (and, if the city searches its region too, the municipalities around it,
    // listed after the city's own), and merge repeats of the same address (one per entrance/postcode).
    const inCity = [], inside = r => hit(data.footprint, +r.lon, +r.lat);
    list.filter(r => inside(r) || (CITY.search.regionViewbox && hit(data.outer, +r.lon, +r.lat)))
      .sort((a, b) => inside(b) - inside(a)).forEach(r => {
      const dup = inCity.some(k => placeLabel(k) === placeLabel(r) && metres([+k.lon, +k.lat], [+r.lon, +r.lat]) < 150);
      if (!dup) inCity.push(r);
    });
    if (!inCity.length && sugg.length){
      showSuggestions(sugg, false);   // e.g. a misspelt or partial place name
    } else if (!inCity.length){
      showResults('<li class="msg">' + esc(fill(CITY.search.noMatch, {q: text})) + '</li>');
    } else if (inCity.length === 1){
      choose(inCity[0]);
    } else {
      window.__hits = inCity;
      showResults(inCity.map((r, i) => '<li><button type="button" data-i="' + i + '">' + esc(placeLabel(r)) + (placeSub(r) ? '<span>' + esc(placeSub(r)) + '</span>' : '') + '</button></li>').join(''));
      results.querySelectorAll('button').forEach(b => b.addEventListener('click', () => choose(window.__hits[+b.dataset.i])));
      results.querySelector('button').focus();
    }
  } catch (err){
    console.error(err);
    showResults('<li class="msg">Something went wrong showing that result. Try again, or tap the map instead.</li>');
  } finally { busy = false; go.disabled = false; go.textContent = 'Find'; }
});
q.addEventListener('keydown', e => { if (e.key === 'Escape'){ showResults(''); q.blur(); } });
/* Suggestions as you type: landmarks plus place names (neighbourhoods, known-as names, the city's big
   areas and the municipalities around it). All from data already loaded: instant, no network. Nominatim's
   policy rules out autocomplete-as-you-type, so live suggestions never come from it. */
const norm = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/['’]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
let PLACES = [];
function indexPlaces(base){
  const seen = new Set();
  const add = (f, sub, outside) => {
    const key = f.properties.name + '|' + sub;
    if (!f.properties.name || seen.has(key)) return;
    seen.add(key); PLACES.push({f, name: f.properties.name, sub, outside});
  };
  LAYERS.filter(it => it.kind === 'fill').forEach(it => data.layers[it.id].features.forEach(f => add(f, it.place || it.name, false)));
  if (UNITS) data.units.features.forEach(f => add(f, CITY.units.singular + (f.properties.code != null ? ' #' + f.properties.code : ''), false));
  if (data.knownas) data.knownas.features.forEach(f => add(f, 'Known-as name', false));
  base.features.filter(f => f.properties.kind === 'neighbour').forEach(f => add(f, fill(CITY.outside.regionPill, f.properties) || 'Nearby', true));
  // The counties or regions themselves: choosing one focuses on it.
  // "DuPage" or "Peel" alone is as good as the full name ("Lake" matches two, so it lists both).
  if (data.regionAreas) data.regionAreas.features.forEach(f => PLACES.push({name: regionName(f.properties.region), sub: CITY.focus.noun, outside: true, focus: f.properties.region, rank: 3.5, f,
    alt: [f.properties.region, regionName(f.properties.region).split(/ (?:county|region)\b/i)[0]]}));
  // Named communities in the municipalities around the city (cities/<city> builds region_places.json).
  (data.regionPlaces || []).forEach(p => PLACES.push({name: p.name, alt: p.alt, sub: fill(CITY.regionPlaces.sub, p), outside: true, muni: p.muni,
    community: (CITY.regionPlaces.near || []).includes(p.kind) ? 5 : 6,
    zoom: CITY.regionPlaces.zoom[p.kind] || 13, f: {type: 'Feature', properties: {name: p.name}, geometry: {type: 'Point', coordinates: p.at}}}));
}
function suggestions(text){
  const qq = norm(text), qs = qq.replace(/ /g, '');
  if (qq.length < 2) return [];
  // Spacing and punctuation don't count: "Yonge-St. Clair" finds "Yonge-St.Clair".
  const score = names => {
    let best = null;
    names.forEach((n, i) => {
      const nn = norm(n), ns = nn.replace(/ /g, '');
      const sc = ns === qs ? 0 : ns.startsWith(qs) ? 1 : (' ' + nn).includes(' ' + qq) ? 2 : null;
      if (sc !== null && (!best || sc < best.s)) best = {s: sc, alias: i ? n : null};
    });
    return best;
  };
  const out = [];
  (data.landmarks ? data.landmarks.features : []).forEach(f => {
    const b = score([f.properties.name].concat(f.properties.aliases || []));
    if (b) out.push({s: b.s, rank: f.properties.tier, name: f.properties.name, sub: f.properties.catLabel + (b.alias ? ' · also called ' + b.alias : ''), go: () => goLandmark(f)});
  });
  INSTITUTIONS().forEach(([it, f]) => {
    const p = f.properties, b = score([p.name + (p.sub && /campus|centre|site/i.test(p.sub) ? ' ' + p.sub : ''), p.name]);
    if (b) out.push({s: b.s, rank: 2.5, name: p.name, sub: [it.place || it.name, p.sub].filter(Boolean).join(' · '), go: () => goLandmark(f)});
  });
  PLACES.forEach(p => {
    const b = score([p.name].concat(p.alt || []));
    if (b) out.push({s: b.s, rank: p.rank || p.community || (p.outside ? 4 : 3), name: p.name, sub: p.sub + (b.alias ? ' · also called ' + b.alias : ''), go: () => goPlace(p)});
  });
  return out.sort((a, b) => a.s - b.s || a.rank - b.rank || a.name.localeCompare(b.name)).slice(0, 6);
}
function showSuggestions(list, more){
  window.__sg = list;
  showResults(list.map((x, i) => '<li><button type="button" data-sg="' + i + '">' + esc(x.name) + '<span>' + esc(x.sub) + '</span></button></li>').join('') +
    (more ? '<li class="msg">' + esc(CITY.search.more) + '</li>' : ''));
  results.querySelectorAll('[data-sg]').forEach(b => b.addEventListener('click', () => window.__sg[+b.dataset.sg].go()));
}
// Institutions for search: every feature of every places-kind layer's own category.
const INSTITUTIONS = () => LAYERS.filter(it => it.kind === 'places' && loaded[it.file]).flatMap(it => loaded[it.file].features.filter(f => f.properties.cat === it.cat).map(f => [it, f]));
function goLandmark(f){ goTo(L.latLng(f.geometry.coordinates[1], f.geometry.coordinates[0]), f.properties.name, true); }
// A named area: frame the whole of it and pin its label point. Outside the city, switch to the region view first.
function goPlace(p){
  if (p.focus){ showResults(''); q.value = p.name; setFocus(p.focus, true); return; }
  const g = p.f.geometry;
  if (g.type === 'Point'){ goTo(L.latLng(g.coordinates[1], g.coordinates[0]), p.name, true, p.zoom, p.muni); return; }
  showResults(''); q.value = p.name;
  if (p.outside && scope === 'inner') setScope('outer', false);
  const lp = p.f.properties.lp, bounds = L.geoJSON(p.f).getBounds();
  inspect(lp ? L.latLng(lp[1], lp[0]) : bounds.getCenter(), p.name);
  const opts = Object.assign(wide() ? {paddingTopLeft:[330,40], paddingBottomRight:[350,40]} : {paddingTopLeft:[20,170], paddingBottomRight:[20,110]}, {maxZoom: 15});
  const size = map.getSize(), calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    if (calm || !size.x || !size.y) map.fitBounds(bounds, Object.assign({animate: false}, opts));
    else map.flyToBounds(bounds, Object.assign({duration: .8}, opts));
  } catch (err){ try { map.fitBounds(bounds, Object.assign({animate: false}, opts)); } catch (e2){} }
}
q.addEventListener('input', () => {
  const m = suggestions(q.value);
  if (!m.length){ showResults(''); return; }
  showSuggestions(m, true);
});
q.addEventListener('keydown', e => { if (e.key === 'ArrowDown'){ const b = results.querySelector('button'); if (b){ e.preventDefault(); b.focus(); } } });
results.addEventListener('keydown', e => {
  const bs = [...results.querySelectorAll('button')], i = bs.indexOf(document.activeElement);
  if (e.key === 'ArrowDown' && i < bs.length - 1){ e.preventDefault(); bs[i + 1].focus(); }
  if (e.key === 'ArrowUp'){ e.preventDefault(); (i > 0 ? bs[i - 1] : q).focus(); }
  if (e.key === 'Escape'){ showResults(''); q.focus(); }
});

/* ---------- Scope: the wider region ("outer") or the city alone ("inner") ---------- */
let mask = null, scope = 'outer';
function frame(bounds){
  const opts = wide() ? {paddingTopLeft:[330,20], paddingBottomRight:[350,20]} : {paddingTopLeft:[0,150], paddingBottomRight:[0,90]};
  const size = map.getSize(), calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (calm || !size.x || !size.y) map.fitBounds(bounds, Object.assign({animate:false}, opts));
  else map.flyToBounds(bounds, Object.assign({duration:.8}, opts));
}
function setScope(s, move){
  scope = s;
  document.querySelectorAll('[data-scope]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.scope === s)));
  map.getContainer().classList.toggle('mode-inner', s === 'inner');
  if (mask) { if (s === 'inner') mask.addTo(map); else map.removeLayer(mask); }
  ORDER.forEach(it => { if (layers[it.id] && layers[it.id]._scope) layers[it.id]._scope(s); });
  if (SUBURBS){
    document.getElementById('row-' + SUBURBS.id).hidden = s === 'inner';
    document.getElementById('drvbox').hidden = s === 'inner' || !state[SUBURBS.id];
    const lyr = layers[SUBURBS.id];
    if (lyr){ if (s === 'outer' && state[SUBURBS.id]) lyr.addTo(map); else map.removeLayer(lyr); }
  }
  const fb = document.getElementById('focusBox');
  if (fb) fb.hidden = s === 'inner';
  if (s === 'inner' && focusKey) setFocus(null, false);
  if (move) frame(s === 'inner' ? CITY_BOUNDS : REGION_VIEW);
  queueDeclutter();
  queueHash();
}

/* ---------- Focus on one county or region (regional view) ----------
   Picking one (from the panel, search, or a spot's card) outlines it, dims everything outside it, frames
   the map on it, labels every municipality inside and lists them in the panel. Outlines come from
   region_areas.geojson (engine/regions.py); municipalities belong to the region named on them in base. */
let focusKey = null, focusLayer = null;
const regionName = k => fill(CITY.outside.regionPill, {region: k}) || k;
const regionFeature = k => k && CITY.focus && data.regionAreas ? data.regionAreas.features.find(f => f.properties.region === k) : null;
function buildFocusUI(){
  if (!CITY.focus || !data.regionAreas) return;
  const keys = data.regionAreas.features.map(f => f.properties.region).sort((a, b) => regionName(a).localeCompare(regionName(b)));
  const box = document.createElement('div'); box.className = 'focus'; box.id = 'focusBox'; box.hidden = scope !== 'outer';
  box.innerHTML = '<label for="focusSel">' + esc(CITY.focus.label) + '</label><select id="focusSel"><option value="">' + esc(CITY.focus.all) + '</option>' +
    keys.map(k => '<option value="' + esc(k) + '">' + esc(regionName(k)) + '</option>').join('') + '</select>' +
    '<div class="focus-res" id="focusRes" hidden><span id="focusCount"></span><button type="button" id="focusClear">Show all</button></div><div class="flist focus-list" id="focusList" hidden></div>';
  document.querySelector('.scope').after(box);
  box.querySelector('select').addEventListener('change', e => setFocus(e.target.value || null, true));
  box.querySelector('#focusClear').addEventListener('click', () => setFocus(null, true));
}
function setFocus(key, move){
  const f = regionFeature(key);
  if (key && !f) return;
  if (f && scope === 'inner') setScope('outer', false);
  focusKey = f ? key : null;
  if (focusLayer){ map.removeLayer(focusLayer); focusLayer = null; }
  map.getContainer().classList.toggle('focused', !!f);
  const sel = document.getElementById('focusSel'); if (sel) sel.value = focusKey || '';
  const list = document.getElementById('focusList'), res = document.getElementById('focusRes');
  if (!f){
    if (list){ list.hidden = true; res.hidden = true; list.innerHTML = ''; }
    if (move) frame(REGION_VIEW);
    queueDeclutter(); queueHash(); return;
  }
  focusLayer = L.layerGroup();
  // Dim everything outside: a sheet over the whole map with the region cut out of it.
  const v = CITY.view.max, sheet = [[v[0][0] - 5, v[0][1] - 5], [v[0][0] - 5, v[1][1] + 5], [v[1][0] + 5, v[1][1] + 5], [v[1][0] + 5, v[0][1] - 5]];
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  focusLayer.addLayer(L.polygon([sheet].concat(polys.map(p => p[0].map(ll))), {pane: 'mask', interactive: false, className: 'focus-dim'}));
  focusLayer.addLayer(L.geoJSON(f, {pane: 'focus', interactive: false, style: () => ({className: 'focus-line'})}));
  // Every municipality in it, biggest first so they win the label declutter.
  const size = g => { const b = L.geoJSON(g).getBounds(); return (b.getEast() - b.getWest()) * (b.getNorth() - b.getSouth()); };
  const towns = data.outer.features.filter(t => t.properties.region === key && !t.properties.rest);
  towns.slice().sort((a, b) => size(b) - size(a)).forEach(t => focusLayer.addLayer(label(esc(t.properties.name), 'lbl-focus', ll(t.properties.lp))));
  focusLayer.addTo(map);
  // The list in the panel: tap a name to go there.
  const sorted = towns.slice().sort((a, b) => a.properties.name.localeCompare(b.properties.name));
  document.getElementById('focusCount').textContent = fill(CITY.focus.count, {n: sorted.length, name: regionName(key)});
  list.innerHTML = '';
  sorted.forEach(t => {
    const b = document.createElement('button'); b.type = 'button';
    b.innerHTML = esc(t.properties.name) + (t.properties.drive != null ? '<span>' + t.properties.drive + ' min</span>' : '');
    b.title = t.properties.drive != null ? 'About ' + t.properties.drive + ' min to ' + CITY.drive.hubName + ' with no traffic' : '';
    b.addEventListener('click', () => {
      const p = PLACES.find(x => x.f === t);
      if (matchMedia('(max-width:760px)').matches) panel.classList.add('collapsed');
      if (p) goPlace(p);
    });
    list.appendChild(b);
  });
  list.hidden = false; res.hidden = false;
  if (move){
    frame(L.geoJSON(f).getBounds());
    // On a phone, clear the way: fold the panel (the picker stays) and close the card.
    if (matchMedia('(max-width:760px)').matches){ panel.classList.add('collapsed'); closeHere(); }
  }
  queueDeclutter(); queueHash();
}
document.querySelectorAll('[data-scope]').forEach(b => b.addEventListener('click', () => { if (b.dataset.scope !== scope) setScope(b.dataset.scope, true); }));


/* ---------- Shareable links: the view lives in the address bar's #fragment ----------
   #map=zoom/lat/lng&pin=lat,lng&name=…&view=region&layers=a,b&lens=commute&fit=cost:lower+middle,union:30
   Anything left out means the starting setting, so old links keep working as defaults change.
   Layers are named by their short ids in city.json; renaming a layer's label doesn't break links.
   The fragment never reaches a server, and replaceState keeps the Back button clean. */
var linkReady = false, hashTimer = 0, lastHash = '';   // var: the panel's handlers can reach these before this line runs
const SHARE_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 10V2.5M5 5.2 8 2.2l3 3M4.5 7.5H3.5v6h9v-6h-1" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const enc = v => encodeURIComponent(v).replace(/%2C/g, ',').replace(/%2F/g, '/').replace(/%3A/g, ':').replace(/%2B/g, '+');
const SUBS = LAYERS.filter(it => it.sub).map(it => it.sub);
// Start keeping the address bar in step at the next touch, click, key or scroll, so a plain visit
// (or one just reset) stays a plain URL until someone actually changes something. Set after this
// event's own handlers, so the gesture that armed it doesn't count.
function armLink(){
  const ev = ['pointerdown', 'keydown', 'wheel'];
  const start = () => { ev.forEach(e => removeEventListener(e, start, true)); linkReady = true; };
  setTimeout(() => ev.forEach(e => addEventListener(e, start, true)), 1200);
}
function queueHash(){ if (linkReady){ clearTimeout(hashTimer); hashTimer = setTimeout(writeHash, 250); } }
function linkState(){
  const c = map.getCenter(), z = map.getZoom();
  const parts = [['map', (Math.round(z * 4) / 4) + '/' + c.lat.toFixed(5) + '/' + c.lng.toFixed(5)]];
  if (pin){ const p = pin.getLatLng(); parts.push(['pin', p.lat.toFixed(5) + ',' + p.lng.toFixed(5)]); if (pinName) parts.push(['name', pinName]); }
  if (scope === 'outer') parts.push(['view', 'region']);
  if (focusKey) parts.push(['focus', focusKey]);
  const on = LAYERS.filter(it => state[it.id]).map(it => it.id)
    .concat(SUBS.filter(s => document.getElementById(s.id).checked).map(s => s.id));
  const dflt = LAYERS.filter(it => it.on).map(it => it.id).concat(SUBS.filter(s => s.on).map(s => s.id));
  if (on.join() !== dflt.join()) parts.push(['layers', on.length ? on.join(',') : 'none']);
  if (lens !== FIRST_LENS || (LENSES[lens].pick && pick[lens] !== LENSES[lens].pick[0][0])) parts.push(['lens', lens + (LENSES[lens].pick ? ':' + pick[lens] : '')]);
  const fit = FILTERS.map(f => f.max ? (filt[f.lens] ? f.lens + ':' + filt[f.lens] : '') : (filt[f.lens].size ? f.lens + ':' + [...filt[f.lens]].join('+') : '')).filter(Boolean);
  if (fit.length) parts.push(['fit', fit.join(',')]);
  const brd = BOARDS.filter(it => state[it.id] && boardPick[it.id] !== it.boards[0][0]).map(it => it.id + ':' + boardPick[it.id]);
  if (brd.length) parts.push(['board', brd.join(',')]);
  return parts.map(([k, v]) => k + '=' + enc(v)).join('&');
}
function writeHash(){
  const h = '#' + linkState();
  if (h === location.hash) return;
  lastHash = h;
  try { history.replaceState(null, '', h); } catch (e) {}
}
function readHash(h){
  const out = {};
  h.replace(/^#/, '').split('&').forEach(kv => { const i = kv.indexOf('='); if (i > 0) { try { out[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); } catch (e) {} } });
  return out;
}
// Put the map into the state a link describes. Unknown ids and malformed parts are skipped.
function applyHash(h){
  const o = readHash(h);
  if (!['map', 'pin', 'view', 'layers', 'lens', 'fit', 'focus', 'board'].some(k => k in o)) return false;
  const num = s => s.split(/[,/]/).map(Number);
  setScope(o.view === 'region' || regionFeature(o.focus) ? 'outer' : 'inner', false);
  setFocus(regionFeature(o.focus) ? o.focus : null, false);
  if (o.layers){
    const want = new Set(o.layers === 'none' ? [] : o.layers.split(','));
    // Area fills first, then the lens: switching the lens on turns fills off, so it must come last to win.
    LAYERS.slice().sort((a, b) => (a.kind === 'lens') - (b.kind === 'lens')).forEach(it => {
      const cb = document.getElementById('lyr-' + it.id), w = want.has(it.id);
      if (cb.checked !== w){ cb.checked = w; setLayer(it.id, w); }
    });
    SUBS.forEach(s => { document.getElementById(s.id).checked = want.has(s.id); });
    syncStnNames();
  }
  (o.board || '').split(',').forEach(part => { const [id, b] = part.split(':'); if (b) setBoard(id, b); });
  const [lk, lp] = (o.lens || '').split(':');
  if (lk && LENSES[lk] && document.querySelector('[data-lens="' + lk + '"]')){ if (lp) setPick(lk, lp); setLens(lk); }
  if (o.fit){
    clearFilters();
    o.fit.split(',').forEach(part => {
      const [k, v] = part.split(':'), f = FILTERS.find(x => x.lens === k);
      if (!f || v == null || !document.querySelector('[data-f="' + k + '"]')) return;
      if (f.max){ if (f.options.some(([ov]) => +ov === +v)) filt[k] = +v; }
      else v.split('+').forEach(t => { if (f.options.some(([ov]) => String(ov) === t)) filt[k].add(t); });
    });
    applyFilter();
  }
  const m = o.map ? num(o.map) : null, ok = a => a && a.every(Number.isFinite);
  const p = o.pin ? num(o.pin) : null;
  if (ok(m) && m.length === 3) map.setView([m[1], m[2]], m[0], {animate: false});
  if (ok(p) && p.length === 2){
    const at = L.latLng(p[0], p[1]);
    if (ok(m)) inspect(at, o.name || undefined);
    else goTo(at, o.name || '', false);
  } else closeHere();
  if (!ok(m) && !(ok(p) && p.length === 2)) frame(scope === 'inner' ? CITY_BOUNDS : focusKey ? L.geoJSON(regionFeature(focusKey)).getBounds() : REGION_VIEW);
  return true;
}
// Share: the phone's share sheet where there is one, otherwise copy the link.
async function share(e){
  writeHash();
  const url = location.href;
  const title = document.title + (pin && pinName ? ' · ' + pinName : '');
  if (navigator.share && matchMedia('(pointer:coarse)').matches){
    try { await navigator.share({title, url}); return; } catch (err){ if (err && err.name === 'AbortError') return; }
  }
  let copied = false;
  try { await navigator.clipboard.writeText(url); copied = true; } catch (err) {}
  if (!copied){ window.prompt('Copy this link:', url); return; }
  flash('Link copied');
}
function flash(msg){
  let t = document.getElementById('toast');
  if (!t){ t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
  t.textContent = msg; t.classList.add('on');
  clearTimeout(flash._t); flash._t = setTimeout(() => t.classList.remove('on'), 1800);
}
document.getElementById('shareView').addEventListener('click', share);
map.on('moveend', queueHash);
// A link pasted into the same tab (only the #fragment changes) re-applies without a reload.
window.addEventListener('hashchange', () => { if (location.hash !== lastHash){ linkReady = false; applyHash(location.hash); linkReady = true; } });


/* ---------- Save the map as a 4K image (all in the browser) ----------
   The map is drawn from the site's own shapes, with no tiles from other sites, so html-to-image (loaded
   only when first used) can turn it into a picture. The map is briefly redrawn in a 16:9 frame that
   covers what's on screen, rendered at 3840 x 2160, and stamped with the data credits the licences
   ask for. The panels, the pin and the controls are left out; "Without labels" also drops every name. */
const IMG_LIB = 'https://cdn.jsdelivr.net/npm/html-to-image@1.11.13/dist/html-to-image.js';
let imgLib = null;
const loadImgLib = () => imgLib || (imgLib = new Promise((res, rej) => {
  const sc = document.createElement('script'); sc.src = IMG_LIB;
  sc.onload = () => window.htmlToImage ? res(window.htmlToImage) : rej(new Error('missing'));
  sc.onerror = () => { imgLib = null; rej(new Error('load')); };
  document.head.appendChild(sc);
}));
const imgBtn = document.getElementById('saveImg'), imgMenu = document.getElementById('imgMenu');
function imgMenuOpen(on){ imgMenu.hidden = !on; imgBtn.setAttribute('aria-expanded', String(on)); if (on) loadImgLib().catch(() => {}); }
imgBtn.addEventListener('click', e => { e.stopPropagation(); imgMenuOpen(imgMenu.hidden); });
imgMenu.querySelectorAll('[data-img]').forEach(b => b.addEventListener('click', () => saveImage(b.dataset.img === 'labels')));
document.addEventListener('click', e => { if (!imgMenu.hidden && !imgMenu.contains(e.target)) imgMenuOpen(false); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !imgMenu.hidden){ imgMenuOpen(false); imgBtn.focus(); } });
// html-to-image copies each SVG whole without the page's stylesheet, and the map's shapes take their
// colours from CSS classes. So, for the moment of capture, the computed look is written onto each shape.
const SVG_PROPS = ['fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
  'stroke-linecap', 'stroke-linejoin', 'opacity', 'display', 'visibility', 'paint-order'];
function inlineSvgStyles(root){
  const saved = [];
  root.querySelectorAll('svg *').forEach(n => {
    const cs = getComputedStyle(n);
    saved.push([n, n.getAttribute('style')]);
    n.setAttribute('style', SVG_PROPS.map(k => k + ':' + cs.getPropertyValue(k)).join(';'));
  });
  return () => saved.forEach(([n, v]) => { if (v == null) n.removeAttribute('style'); else n.setAttribute('style', v); });
}
const frames = n => new Promise(r => { const step = k => k ? requestAnimationFrame(() => step(k - 1)) : r(); step(n); });
let saving = false;
async function saveImage(labels){
  if (saving) return; saving = true;
  imgMenuOpen(false);
  const W = 3840, H = 2160, el = map.getContainer(), busy = document.getElementById('busy');
  const center = map.getCenter(), zoom = map.getZoom(), before = el.getAttribute('style') || '';
  // A 16:9 frame at least as big as the screen's map, so the picture shows what's on screen (and a bit more on the short side).
  const cw = Math.round(Math.max(el.clientWidth, el.clientHeight * 16 / 9)), ch = Math.round(cw * 9 / 16);
  busy.firstElementChild.textContent = 'Making your image…'; busy.hidden = false;
  let canvas = null, restoreSvg = null;
  try {
    const lib = await loadImgLib();
    el.style.right = 'auto'; el.style.bottom = 'auto'; el.style.width = cw + 'px'; el.style.height = ch + 'px';
    map.invalidateSize({pan: false}); map.setView(center, zoom, {animate: false, reset: true});   // reset: redraw every shape for the new frame
    await new Promise(r => setTimeout(r, 400)); declutter(); await frames(2);
    const has = (n, c) => n.classList && n.classList.contains(c);
    const skip = n => has(n, 'leaflet-control-container') || has(n, 'leaflet-pin-pane') || has(n, 'hover-tip') ||
      (!labels && (has(n, 'leaflet-tooltip-pane') || has(n, 'leaflet-stlbl-pane') || has(n, 'shield') ||
        (n.tagName === 'B' && n.parentElement && has(n.parentElement, 'lm'))));
    restoreSvg = inlineSvgStyles(el);
    canvas = await lib.toCanvas(el, {width: cw, height: ch, canvasWidth: W, canvasHeight: H, pixelRatio: 1,
      backgroundColor: getComputedStyle(el).backgroundColor, filter: n => !skip(n)});
    stampCredits(canvas);
  } catch (err){
    console.error(err);
  } finally {
    if (restoreSvg) restoreSvg();
    el.setAttribute('style', before);
    map.invalidateSize({pan: false}); map.setView(center, zoom, {animate: false, reset: true});   // reset: redraw every shape for the new frame
    busy.hidden = true; saving = false;
  }
  if (!canvas){ flash('The image couldn’t be made. Check your connection and try again.'); return; }
  canvas.toBlob(async blob => {
    if (!blob){ flash('The image couldn’t be made.'); return; }
    const name = slug(document.title) + (pin && pinName ? '-' + slug(pinName) : '') + (labels ? '' : '-no-labels') + '.png';
    const file = new File([blob], name, {type: 'image/png'});
    if (matchMedia('(pointer:coarse)').matches && navigator.canShare && navigator.canShare({files: [file]})){
      try { await navigator.share({files: [file], title: document.title}); return; } catch (e){ if (e && e.name === 'AbortError') return; }
    }
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    flash('Image saved');
  }, 'image/png');
}
// Bottom-right: the map's name and address, then the data credits (the licences ask for them wherever the map goes).
function stampCredits(canvas){
  const ctx = canvas.getContext('2d'), cs = getComputedStyle(document.documentElement);
  const ink = cs.getPropertyValue('--ink').trim() || '#23262B', bg = cs.getPropertyValue('--panel').trim() || '#fff';
  const font = cs.getPropertyValue('--font').trim() || 'sans-serif';
  const credit = (() => { const d = document.createElement('div'); d.innerHTML = CITY.attribution; return d.textContent.replace(/\s+/g, ' ').trim(); })();
  const title = document.title + ' · ' + location.host + location.pathname.replace(/\/$/, '');
  const pad = 22, x = canvas.width - 36, y = canvas.height - 36, maxW = canvas.width - 200;
  ctx.font = '400 24px ' + font; const w2 = Math.min(ctx.measureText(credit).width, maxW);
  ctx.font = '700 30px ' + font; const w1 = ctx.measureText(title).width;
  const bw = Math.max(w1, w2) + pad * 2, bh = 30 + 24 + 14 + pad * 2;
  ctx.globalAlpha = .88; ctx.fillStyle = bg;
  ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(x - bw, y - bh, bw, bh, 14); else ctx.rect(x - bw, y - bh, bw, bh); ctx.fill();
  ctx.globalAlpha = 1; ctx.fillStyle = ink; ctx.textAlign = 'right'; ctx.textBaseline = 'alphabetic';
  ctx.fillText(title, x - pad, y - bh + pad + 28);
  ctx.font = '400 24px ' + font; ctx.globalAlpha = .75;
  ctx.fillText(credit, x - pad, y - pad, maxW);
  ctx.globalAlpha = 1;
}

/* ---------- load ---------- */
renderEmpty('Loading map data…');
const files = ['base', 'regions'];
LAYERS.forEach(it => [].concat(it.file || it.files || []).forEach(f => { if (!files.includes(f)) files.push(f); }));
const loaded = {};
Promise.all(files.map(f => get(f).then(d => { loaded[f] = d; }))
  .concat([get(CITY.lens.file).then(d => { data.profiles = d; }), get(CITY.card.reps.file).then(d => { data.reps = d; }).catch(() => { data.reps = null; }),
    CITY.regionPlaces ? get(CITY.regionPlaces.file).then(d => { data.regionPlaces = d; }).catch(() => { data.regionPlaces = null; }) : null,
    CITY.drive ? get('drive_grid.json').then(d => { data.driveGrid = d; }).catch(() => { data.driveGrid = null; }) : null,
    CITY.focus ? get('region_areas').then(d => { data.regionAreas = d; }).catch(() => { data.regionAreas = null; }) : null]))
.then(() => {
  const base = loaded.base, src = it => it.file ? loaded[it.file] : it.files.map(f => loaded[f]);
  LAYERS.filter(it => AREA_KINDS.includes(it.kind) || it.kind === 'boards').forEach(it => { data.layers[it.id] = loaded[it.file]; });
  Object.assign(data, {footprint: data.layers[CITY.footprint], units: UNITS && loaded[UNITS.file],
    knownas: byKind('knownas') && loaded[byKind('knownas').file], landmarks: byKind('landmarks') && loaded[byKind('landmarks').file],
    outer: {type:'FeatureCollection', features: base.features.filter(f => f.properties.kind === 'neighbour')}});
  buildBase(base, loaded.regions);
  indexPlaces(base);
  buildFocusUI();
  // City-only mode: cover every other municipality and the land beyond the region (water stays visible).
  mask = L.geoJSON({type:'FeatureCollection', features: base.features.filter(f => f.properties.kind !== 'city')},
    {pane:'mask', interactive:false, style: () => ({className:'mask'})});
  // A lens with no figures in this build's data (e.g. transit times not fetched yet) is hidden, with its filter row.
  CITY.lens.lenses.filter(L_ => L_.optional).forEach(L_ => {
    if (!Object.values(data.profiles).some(d => d[L_.minutes || L_.field || L_.key] != null)) document.querySelectorAll('[data-lens="' + L_.id + '"], .frow:has([data-f="' + L_.id + '"])').forEach(e => e.remove());
  });
  ORDER.forEach(it => { layers[it.id] = KINDS[it.kind](it, it.kind === 'lens' ? [data.units, data.profiles] : it.kind === 'suburbs' ? base : src(it)); });
  drawDriveLegend();
  ORDER.forEach(it => { if (state[it.id]) layers[it.id].addTo(map); });
  syncStnNames();
  zoomClasses();
  if (!applyHash(location.hash)){
    setScope('inner', false);
    frame(CITY_BOUNDS);
    inspect(L.latLng(CITY.example.at), CITY.example.name);
  }
  lastHash = location.hash;
  if (location.hash) linkReady = true; else armLink();
  window.cityMapReady = true;
}).catch(err => { renderEmpty('The map data didn’t load (' + err.message + '). Reload the page to try again.'); });
})();

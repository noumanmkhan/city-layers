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
const AREA_KINDS = ['fill', 'units', 'outline', 'patches'];   // polygon layers the "What's here" card tests against

/* Neighbourhood lenses (tiers from the city's profile data). One shows at a time. */
const LENSES = {};
CITY.lens.lenses.forEach(L_ => { LENSES[L_.id] = L_; });
const FILTERS = CITY.lens.filters;
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
  return !filt[f.lens].size || filt[f.lens].has(d[L_.key]);
});
const lensClass = d => { const L_ = LENSES[lens]; return 'lens ' + (d && d[L_.key] ? L_.id + '-' + d[L_.key] : '') + (filtOn() && !matches(d) ? ' out' : ''); };
let lens = FIRST_LENS;
const TIER_LABEL = {};
Object.values(LENSES).forEach(L_ => L_.tiers.forEach(([k, label, v]) => { TIER_LABEL[L_.key + ':' + k] = [label, v]; }));
const tierOf = d => d && d[LENSES[lens].key] ? TIER_LABEL[LENSES[lens].key + ':' + d[LENSES[lens].key]][0] : '';

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

const panes = [['base',200],['fill',350],['lines',420],['streets',400],['civic',430],['hwy',450],['rail',460],['mask',465],['transit',470],['stlbl',475],['pts',480],['pin',620]];
panes.forEach(([n,z]) => { map.createPane(n); map.getPane(n).style.zIndex = z; });
map.getPane('base').style.pointerEvents = 'none';
map.getPane('stlbl').style.pointerEvents = 'none';
map.getPane('mask').style.pointerEvents = 'none';

const layers = {}; const data = {layers: {}};
const get = f => fetch(DATA + (f.includes('.') ? f : f + '.geojson')).then(r => { if (!r.ok) throw new Error(f); return r.json(); });

function zoomClasses(){
  const z = map.getZoom(), el = map.getContainer();
  [10,11,12,13,14].forEach(t => el.classList.toggle('z'+t, z >= t - .01));
}
map.on('zoomend', zoomClasses); zoomClasses();

/* Label declutter: after each move, place labels in priority order and hide any that would overlap
   a label already placed. Icons stay; hovering an icon still shows its name. */
const LABEL_PRIORITY = ['.lm.t1 b', '.lm.t2 b', '.lbl-stn.end', '.lbl-go.end', '.shield', '.lbl-stn', '.lbl-go', '.lbl-cult', '.lbl-area', '.lbl-nbhd', '.lbl-ward, .lbl-prov, .lbl-fed', '.lbl-bia'];
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
// Representation layers draw in one of three styles, by level of government.
const OUTLINE = {city:'ward', state:'prov', national:'fed'};

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
const RANK = it => ({fill: it.size === 'major' ? 0 : 1, lens: 2, patches: 3, units: 4, outline: {national: 5, state: 6, city: 7}[it.level], knownas: 8, streets: 9, highways: 10, rail: 11, metro: 12, landmarks: 13})[it.kind];
const ORDER = LAYERS.map(it => it).sort((a, b) => RANK(a) - RANK(b));

/* ---------- panel ---------- */
const state = {};
const host = document.getElementById('layers');
CITY.groups.forEach(([title, items]) => {
  const grp = document.createElement('div'); grp.className = 'grp';
  grp.innerHTML = '<h2>' + title + '</h2>';
  items.forEach(it => {
    const row = document.createElement('label'); row.className = 'row'; row.htmlFor = 'lyr-' + it.id;
    row.innerHTML = '<span class="sw ' + it.id + ' k-' + (it.kind === 'outline' ? it.level : it.kind) + '">' + (SWATCH[it.kind] || '') + '</span><span class="tx"><b>' + it.name + '</b><span>' + it.note + '</span></span>' +
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
        applyFilter();
      }));
      box.querySelector('#fclear').addEventListener('click', () => { clearFilters(); applyFilter(); });
    }
    if (it.sub){
      const s = document.createElement('label'); s.className = 'sub';
      s.innerHTML = '<input type="checkbox" id="' + it.sub.id + '"' + (it.sub.on ? ' checked' : '') + '> ' + it.sub.label;
      grp.appendChild(s);
      s.querySelector('input').addEventListener('change', () => syncStnNames());
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
function drawLegend(){
  const el = document.getElementById('legend'); if (!el) return;
  const L_ = LENSES[lens];
  el.innerHTML = L_.tiers.map(([k, label, v]) => '<div><i style="background:var(' + v + ')"></i>' + label + '</div>').join('') +
    '<small>' + L_.note + ' Source: ' + (L_.source || CITY.lens.source) + '</small>';
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
}
const kindOf = id => (LAYERS.find(it => it.id === id) || {}).kind;
function setLayer(id, on){
  state[id] = on;
  const lyr = layers[id]; if (!lyr) return;
  if (on) { lyr.addTo(map); } else { map.removeLayer(lyr); }
  if (METRO && id === METRO.id) syncStnNames();
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
  clearFilters(); applyFilter(); setLens(FIRST_LENS);
  setScope('inner', true);
});
document.getElementById('allOff').addEventListener('click', () => {
  Object.keys(state).forEach(id => { const cb = document.getElementById('lyr-' + id); if (cb.checked){ cb.checked = false; setLayer(id, false); } });
});
const panel = document.getElementById('panel');
document.getElementById('ph').addEventListener('click', () => { if (matchMedia('(max-width:760px)').matches) panel.classList.toggle('collapsed'); });
if (matchMedia('(max-width:760px)').matches) panel.classList.add('collapsed');

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
    '</dl><p>' + esc(fill(T.footer, {name: d.name})) + '</p></div>';
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
    }).join('') +
    '</dl><p>' + esc(fill(cfg.note, {date})) + '</p></div>';
}
function placePin(latlng){
  if (pin) pin.setLatLng(latlng); else pin = L.marker(latlng, {pane:'pin', interactive:false, keyboard:false, icon: L.divIcon({className:'', iconSize:[20, 20], iconAnchor:[10, 10], html:'<span class="pin"></span>'})}).addTo(map);
}
const colorOf = (id, f) => { const it = LAYERS.find(l => l.id === id); return 'var(' + ((it && it.colors && it.colors[f.properties.name]) || '--ink-3') + ')'; };
function inspect(latlng, title){
  const x = latlng.lng, y = latlng.lat;
  if (!hit(data.footprint, x, y)){
    const muni = hit(data.outer, x, y);
    if (!muni){ here.hidden = false; renderEmpty(CITY.outside.beyond); return; }
    placePin(latlng);
    const m = muni.properties;
    here.hidden = false;
    here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>' + esc(title || m.name) + '</strong></div><button type="button" aria-label="Close" id="hereX">×</button></div>' +
      '<div class="pills"><span class="pill"><i style="background:var(--land-out-line)"></i>' + esc(m.name) + '</span><span class="pill"><i style="background:var(--muni-label)"></i>' + esc(fill(CITY.outside.regionPill, m)) + '</span></div>' +
      '<p class="outside-note">' + esc(CITY.outside.note) + '</p>';
    document.getElementById('hereX').onclick = closeHere;
    return;
  }
  placePin(latlng);
  const hits = {};
  LAYERS.filter(it => AREA_KINDS.includes(it.kind)).forEach(it => { hits[it.id] = hit(data.layers[it.id], x, y); });
  const pillCfg = CITY.card.pills.find(p => p.knownas);
  const near = (data.knownas ? data.knownas.features : []).map(f => [f, metres([x, y], f.geometry.coordinates)]).filter(a => a[1] < 650).sort((a, b) => a[1] - b[1]).slice(0, pillCfg ? pillCfg.knownas : 2);
  const pills = [];
  CITY.card.pills.forEach(p => {
    if (p.knownas) { near.forEach(([f]) => pills.push(['var(--cult-enclave)', f.properties.name])); return; }
    const h = hits[p.layer];
    if (p.else) { if (h) pills.push([colorOf(p.layer, h), h.properties.name]); else if (hits[p.else]) pills.push([colorOf(p.else, hits[p.else]), hits[p.else].properties.name]); return; }
    if (h) pills.push(['var(' + p.color + ')', fill(p.text, h.properties)]);
  });
  const facts = CITY.card.facts.map(r => {
    if (r.knownas) return [r.label, near.length ? near.map(a => a[0].properties.name).join(', ') : '—'];
    const h = hits[r.layer];
    if (h) return [r.label, fill(r.text, h.properties)];
    if (r.emptyWithin && Object.entries(r.emptyWithin).some(([id, name]) => hits[id] && hits[id].properties.name === name)) return [r.label, '—'];
    return [r.label, r.empty || '—'];
  });
  const coords = Math.abs(y).toFixed(4) + '° ' + (y >= 0 ? 'N' : 'S') + ', ' + Math.abs(x).toFixed(4) + '° ' + (x < 0 ? 'W' : 'E');
  here.hidden = false;
  here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>' + esc(title || coords) + '</strong></div><button type="button" aria-label="Close" id="hereX">×</button></div>' +
    '<div class="pills">' + pills.map(p => '<span class="pill"><i style="background:' + p[0] + '"></i>' + esc(p[1]) + '</span>').join('') + '</div>' +
    section('bounds', 'Boundaries', '<dl class="facts">' + facts.map(f => '<dt>' + f[0] + '</dt><dd>' + esc(f[1]) + '</dd>').join('') + '</dl>') +
    section('live', 'Living here', livingHere(UNITS && hits[UNITS.id])) +
    section('reps', 'Representatives', representatives(hits));
  document.getElementById('hereX').onclick = closeHere;
  here.querySelectorAll('details.sec').forEach(d => d.addEventListener('toggle', () => { secOpen[d.dataset.sec] = d.open; try { localStorage.setItem('cardSections', JSON.stringify(secOpen)); } catch (e) {} }));
}
function renderEmpty(msg){
  here.innerHTML = '<div class="hh"><div><small>What’s here</small><strong>Tap the map</strong></div><button type="button" aria-label="Close" id="hereX">×</button></div><div class="hint">' + esc(msg) + '</div>';
  document.getElementById('hereX').onclick = closeHere;
}
function closeHere(){ here.hidden = true; if (pin){ map.removeLayer(pin); pin = null; } }

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
  return [name, a.neighbourhood || a.suburb || a.quarter, a.postcode].filter(Boolean).join(' · ');
}
function choose(r){ goTo(L.latLng(+r.lat, +r.lon), placeLabel(r), true); }
function goTo(latlng, name, fromSearch){
  showResults('');
  if (fromSearch) q.value = name;
  inspect(latlng, name);  // fill the card first, so a map-move problem can't hide the result
  const zoom = Math.max(map.getZoom(), 15);
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
  const exact = landmarkMatches(text).filter(x => x.s === 0);
  if (exact.length === 1){ goLandmark(exact[0].f); return; }
  busy = true;
  const wait = 1100 - (Date.now() - lastSearch);
  if (wait > 0) await new Promise(r => setTimeout(r, wait));
  lastSearch = Date.now();
  go.disabled = true; go.textContent = '…';
  const url = 'https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=6&countrycodes=' + CITY.search.country + '&bounded=1' +
    '&viewbox=' + CITY.search.viewbox + '&q=' + encodeURIComponent(text);
  try {
    let list;
    try { list = await geocode(url); }
    catch (err){ showResults('<li class="msg">Address search isn’t responding right now. Try again in a moment, or tap the map instead.</li>'); return; }
    // Keep matches inside the city, and merge repeats of the same address (one per entrance/postcode).
    const inCity = [];
    list.filter(r => hit(data.footprint, +r.lon, +r.lat)).forEach(r => {
      const dup = inCity.some(k => placeLabel(k) === placeLabel(r) && metres([+k.lon, +k.lat], [+r.lon, +r.lat]) < 150);
      if (!dup) inCity.push(r);
    });
    if (!inCity.length){
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
/* Landmark suggestions: instant, local, no network (Nominatim's policy rules out
   autocomplete-as-you-type, so live suggestions come only from our own curated list). */
const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/['’]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
function landmarkMatches(text){
  const qq = norm(text);
  if (qq.length < 2 || !data.landmarks) return [];
  const out = [];
  data.landmarks.features.forEach(f => {
    let best = null;
    [f.properties.name].concat(f.properties.aliases).forEach((n, i) => {
      const nn = norm(n);
      const s = nn === qq ? 0 : nn.startsWith(qq) ? 1 : (' ' + nn).includes(' ' + qq) ? 2 : null;
      if (s !== null && (!best || s < best.s)) best = {s, alias: i ? n : null};
    });
    if (best) out.push({f, ...best});
  });
  return out.sort((a, b) => a.s - b.s || a.f.properties.tier - b.f.properties.tier || a.f.properties.name.localeCompare(b.f.properties.name)).slice(0, 5);
}
function goLandmark(f){ goTo(L.latLng(f.geometry.coordinates[1], f.geometry.coordinates[0]), f.properties.name, true); }
q.addEventListener('input', () => {
  const m = landmarkMatches(q.value);
  if (!m.length){ showResults(''); return; }
  window.__lm = m;
  showResults(m.map((x, i) => '<li><button type="button" data-lm="' + i + '">' + esc(x.f.properties.name) +
    '<span>' + esc(x.f.properties.catLabel) + (x.alias ? ' · also called ' + esc(x.alias) : '') + '</span></button></li>').join('') +
    '<li class="msg">' + esc(CITY.search.more) + '</li>');
  results.querySelectorAll('[data-lm]').forEach(b => b.addEventListener('click', () => goLandmark(window.__lm[+b.dataset.lm].f)));
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
  if (move) frame(s === 'inner' ? CITY_BOUNDS : REGION_VIEW);
  queueDeclutter();
}
document.querySelectorAll('[data-scope]').forEach(b => b.addEventListener('click', () => { if (b.dataset.scope !== scope) setScope(b.dataset.scope, true); }));

/* ---------- load ---------- */
renderEmpty('Loading map data…');
const files = ['base', 'regions'];
LAYERS.forEach(it => [].concat(it.file || it.files || []).forEach(f => { if (!files.includes(f)) files.push(f); }));
const loaded = {};
Promise.all(files.map(f => get(f).then(d => { loaded[f] = d; }))
  .concat([get(CITY.lens.file).then(d => { data.profiles = d; }), get(CITY.card.reps.file).then(d => { data.reps = d; }).catch(() => { data.reps = null; })]))
.then(() => {
  const base = loaded.base, src = it => it.file ? loaded[it.file] : it.files.map(f => loaded[f]);
  LAYERS.filter(it => AREA_KINDS.includes(it.kind)).forEach(it => { data.layers[it.id] = loaded[it.file]; });
  Object.assign(data, {footprint: data.layers[CITY.footprint], units: UNITS && loaded[UNITS.file],
    knownas: byKind('knownas') && loaded[byKind('knownas').file], landmarks: byKind('landmarks') && loaded[byKind('landmarks').file],
    outer: {type:'FeatureCollection', features: base.features.filter(f => f.properties.kind === 'neighbour')}});
  buildBase(base, loaded.regions);
  // City-only mode: cover every other municipality and the land beyond the region (water stays visible).
  mask = L.geoJSON({type:'FeatureCollection', features: base.features.filter(f => f.properties.kind !== 'city')},
    {pane:'mask', interactive:false, style: () => ({className:'mask'})});
  // A lens with no figures in this build's data (e.g. transit times not fetched yet) is hidden, with its filter row.
  CITY.lens.lenses.filter(L_ => L_.optional).forEach(L_ => {
    if (!Object.values(data.profiles).some(d => d[L_.minutes || L_.key] != null)) document.querySelectorAll('[data-lens="' + L_.id + '"], .frow:has([data-f="' + L_.id + '"])').forEach(e => e.remove());
  });
  ORDER.forEach(it => { layers[it.id] = KINDS[it.kind](it, it.kind === 'lens' ? [data.units, data.profiles] : src(it)); });
  ORDER.forEach(it => { if (state[it.id]) layers[it.id].addTo(map); });
  syncStnNames();
  zoomClasses();
  setScope('inner', false);
  frame(CITY_BOUNDS);
  inspect(L.latLng(CITY.example.at), CITY.example.name);
}).catch(err => { renderEmpty('The map data didn’t load (' + err.message + '). Reload the page to try again.'); });
})();

/* In-context severity scale strip under each scored indicator. Fully additive:
   missing scoring.js or data/methodology.json -> lens pages render exactly as before.
   Same hook pattern as predict.js: the lens:rendered event + the .ind[data-indicator]
   card, plus the data-scale-now lens.js stamps. Renders only SEVERITY signals; info /
   momentum / neutral signals already carry their own "why not scored" note. */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  async function get(url) {
    try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; }
    catch (e) { return null; }
  }
  // Per-category slice (a few KB) with a fallback to the full file, so a missing or
  // unknown-category slice degrades to the prior behavior. `cat` is the canonical
  // category id from the lens:rendered event. Mirrors predict.js — keep in sync.
  async function sliceOrFull(prefix, cat, full) {
    if (cat) { var s = await get(prefix + cat + ".json"); if (s) return s; }
    return get(full);
  }
  // Page-scoped memo shared with predict.js (self.__baOpenP): the open predictions
  // are fetched once per lens page, not once per script.
  function getOpen(cat) {
    return (self.__baOpenP = self.__baOpenP
      || sliceOrFull("/data/predictions/open/", cat, "/data/predictions/open.json"));
  }
  // Mirrors lens.js fmtVal / predict.js fmtVal / build.py _fmt — keep in sync (house rule).
  function fmtVal(v, unit, vf) {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "", a = Math.abs(v);
    const num = vf === "thousands" ? Math.round(a).toLocaleString("en-US") : a.toFixed(2);
    if (!unit) return sign + num;
    if (unit[0] === "$") return `${sign}$${num}${unit.slice(1)}`;
    if (unit.length > 1 && /[a-z]/i.test(unit[0])) return `${sign}${num} ${unit}`;
    return `${sign}${num}${unit}`;
  }
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

  function strip(sig, scaleNow, pred, href) {
    const segs = sig.segments, edges = sig.edges;
    const unit = (sig.axis || {}).unit || "", vf = (sig.axis || {}).value_format || "decimal";
    const axisLabel = (sig.axis || {}).label || "";
    // Linear display range padded beyond the outer thresholds, widened so the
    // current value (and any forecast marker) is always visible.
    const lo0 = edges[0], hi0 = edges[edges.length - 1];
    const pad = ((hi0 - lo0) || Math.abs(hi0) || 1) * 0.18;
    // Ghost (forecast) marker only when the forecast lands on THIS axis — i.e. a
    // raw level or an already-YoY series. For yoy_computed (rule derives YoY from a
    // level) and delta_from_low (rise above a trailing low), the prediction's `point`
    // is in different units than the strip plots, so a marker there would mislead.
    const onAxis = ["level", "yoy"].indexOf((sig.axis || {}).kind) !== -1;
    const ghost = (pred && onAxis && pred.point != null) ? pred.point : null;
    let dMin = lo0 - pad, dMax = hi0 + pad;
    [scaleNow, ghost].forEach(v => {
      if (v != null) { dMin = Math.min(dMin, v - pad * 0.5); dMax = Math.max(dMax, v + pad * 0.5); }
    });
    const rng = (dMax - dMin) || 1;
    const pos = v => clamp((v - dMin) / rng * 100, 0, 100);

    let bars = "";
    segs.forEach((s, i) => {
      const left = i === 0 ? 0 : pos(edges[i - 1]);
      const right = i === segs.length - 1 ? 100 : pos(edges[i]);
      bars += `<span class="scale-seg ${esc(s.status)}" style="left:${left}%;width:${Math.max(right - left, 0)}%"></span>`;
    });
    const nowX = pos(scaleNow);
    let marks = `<span class="scale-mark" aria-hidden="true" style="left:${nowX}%"></span>`;
    if (ghost != null) {
      marks += `<span class="scale-ghost" aria-hidden="true" style="left:${pos(ghost)}%" title="forecast ~${esc(fmtVal(ghost, unit, vf))}"></span>`;
    }
    const labelX = clamp(nowX, 12, 88);
    const edgesTxt = edges.map(e => esc(fmtVal(e, unit, vf))).join(" · ");
    const ghostTxt = ghost != null ? ` · forecast ~${esc(fmtVal(ghost, unit, vf))}` : "";
    // When the strip's axis differs from the chart above it (yoy_computed /
    // delta_from_low plot a transformed value), name what's being scored so "now X"
    // reconciles with the chart.
    const scoredOn = (!onAxis && axisLabel) ? `scored on ${esc(axisLabel)} · ` : "";
    return `<div class="scale">
      <div class="scale-head"><span class="scale-lab">How we score this</span>
        <a class="scale-link" href="${esc(href)}">full methodology &rarr;</a></div>
      <div class="scale-track">
        <div class="scale-bar" aria-hidden="true">${bars}</div>${marks}
        <div class="scale-nowrap"><span class="scale-now" style="left:${labelX}%">now <b>${esc(fmtVal(scaleNow, unit, vf))}</b></span></div>
      </div>
      <div class="scale-edges">${scoredOn}bands: ${edgesTxt}${ghostTxt}</div>
    </div>`;
  }

  document.addEventListener("lens:rendered", async function (ev) {
    const lensId = ev.detail && ev.detail.id;
    if (!lensId) return;
    const cat = ev.detail && ev.detail.category;
    const [method, open] = await Promise.all([
      sliceOrFull("/data/methodology/", cat, "/data/methodology.json"), getOpen(cat)]);
    if (!method || !method.signals) return;
    const preds = {};
    if (open && open.predictions) {
      open.predictions.forEach(p => { if (p.lens === lensId) preds[p.indicator] = p; });
    }
    document.querySelectorAll("#lens-root .ind[data-indicator]").forEach(card => {
      const id = card.dataset.indicator;
      const sig = method.signals[lensId + "::" + id];
      if (!sig || sig.taxonomy !== "severity" || !sig.segments || !sig.edges || !sig.edges.length) return;
      const raw = card.dataset.scaleNow;
      if (raw == null || raw === "") return;
      const scaleNow = parseFloat(raw);
      if (isNaN(scaleNow)) return;
      const href = "/dashboards/methodology.html#" + lensId + "--" + id;
      const div = document.createElement("div");
      div.innerHTML = strip(sig, scaleNow, preds[id], href);
      const node = div.firstElementChild;
      const ctx = card.querySelector(".context");
      if (ctx) ctx.insertAdjacentElement("afterend", node);
      else card.appendChild(node);
    });
  });
})();

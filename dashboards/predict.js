/* "Next print" blocks under indicator charts + the last graded call.
   Fully additive: if this file or its JSON is missing, lens pages render
   exactly as before. Matches cards via data-indicator + the lens id from
   the lens:rendered event (lens ids are globally unique). */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  async function get(url) {
    try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; }
    catch (e) { return null; }
  }
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDue(iso) {
    if (!iso || iso.length < 10) return "";
    return `due ~${MONTHS[+iso.slice(5, 7) - 1]} ${+iso.slice(8, 10)}`;
  }
  // Mirrors lens.js fmtVal / build.py _fmt — keep in sync (house rule).
  function fmtVal(v, unit, vf) {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "", a = Math.abs(v);
    const num = vf === "thousands" ? Math.round(a).toLocaleString("en-US") : a.toFixed(2);
    if (!unit) return sign + num;
    if (unit[0] === "$") return `${sign}$${num}${unit.slice(1)}`;
    if (unit.length > 1 && /[a-z]/i.test(unit[0])) return `${sign}${num} ${unit}`;
    return `${sign}${num}${unit}`;
  }
  function statusPhrase(p) {
    // Descriptive (info-only) series carry no badge — forecast them without
    // implying one. "info" means the lens treats this number as descriptive.
    if (!p.implied_status || p.implied_status === "unknown" || p.implied_status === "info") return "";
    const badge = `<span class="badge ${esc(p.implied_status)}">${esc(p.implied_status)}</span>`;
    return p.implied_status !== p.current_status
      ? ` — would tip this signal to ${badge}`
      : ` — would keep this signal ${badge}`;
  }
  function lastCall(g) {
    if (!g || !g.grade) return "";
    const mark = g.grade.hit ? "✓" : "✗";
    const cls = g.grade.hit ? "hit" : "miss";
    const rev = g.grade.revised_to != null
      ? ` <span class="pred-rev">(later revised to ${esc(fmtVal(g.grade.revised_to, g.unit, g.value_format))} — we grade against the first print)</span>` : "";
    return `<div class="pred-last"><span class="pred-mark ${cls}">${mark}</span>
      Last call: we said ${esc(fmtVal(g.point, g.unit, g.value_format))},
      actual was <strong>${esc(fmtVal(g.grade.actual, g.unit, g.value_format))}</strong>${rev}
      · <a href="/dashboards/track-record.html">our record &rarr;</a></div>`;
  }
  function block(p, g) {
    const range = `${esc(fmtVal(p.lo, p.unit, p.value_format))}–${esc(fmtVal(p.hi, p.unit, p.value_format))}`;
    return `<div class="predict">
      <div class="pred-head">Next print <span class="pred-due">${esc(fmtDue(p.due))}</span></div>
      <div class="pred-line">We expect <strong>~${esc(fmtVal(p.point, p.unit, p.value_format))}</strong>
        <span class="pred-range">(likely ${range})</span>${statusPhrase(p)}</div>
      <div class="pred-why">${esc(p.why || "")}</div>${lastCall(g)}</div>`;
  }
  document.addEventListener("lens:rendered", async function (ev) {
    const lensId = ev.detail && ev.detail.id;
    if (!lensId) return;
    const [open, recent] = await Promise.all([
      get("/data/predictions/open.json"), get("/data/predictions/recent.json")]);
    if (!open || !open.predictions) return;
    const mine = {};
    open.predictions.forEach(p => { if (p.lens === lensId) mine[p.indicator] = p; });
    document.querySelectorAll("#lens-root .ind[data-indicator]").forEach(card => {
      const p = mine[card.dataset.indicator];
      if (!p) return;
      const g = recent && recent.last && recent.last[p.key];
      const div = document.createElement("div");
      div.innerHTML = block(p, g);
      card.appendChild(div.firstElementChild);
    });
  });
})();

/* Shared renderer for Today's Brief.
   loadBrief("brief-panel", { compact:false }) -> full hub panel
   loadBrief("brief-strip", { compact:true })  -> one-line home summary */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function countsLine(c) {
    const parts = [];
    if (c.alert) parts.push(`${c.alert} alert`);
    if (c.elevated) parts.push(`${c.elevated} elevated`);
    if (c.watch) parts.push(`${c.watch} on watch`);
    return parts.length ? parts.join(" · ") : "All clear across the dashboards";
  }

  function transitionRow(t) {
    return `<a class="brief-trans" href="${t.href}">
      <span class="brief-trans-title">${esc(t.lens_title)}</span>
      <span class="brief-arrow">
        <span class="badge ${esc(t.from_status)}">${esc(t.from_status)}</span>
        &rarr;
        <span class="badge ${esc(t.to_status)}">${esc(t.to_status)}</span>
      </span>
      <span class="brief-trans-read">${esc(t.headline)}</span>
    </a>`;
  }

  function moveRow(m) {
    const delta = m.delta ? `<i class="delta ${esc(m.dir || "")}">${esc(m.delta)}</i>` : "";
    return `<a class="brief-move" href="${m.href}">
      <span class="brief-move-title">${esc(m.lens_title)}</span>
      <span class="brief-move-stat">${esc(m.stat_label)} <b>${esc(m.stat_value)}</b> ${delta}</span>
    </a>`;
  }

  function fullPanel(data) {
    const trans = (data.transitions || []).map(transitionRow).join("");
    const moves = (data.top_moves || []).map(moveRow).join("");
    const quiet = !trans && !moves;
    return `
      <div class="brief-head">Today&rsquo;s Brief
        <span class="brief-counts">${esc(countsLine(data.status_counts || {}))}</span></div>
      ${trans ? `<div class="brief-sec-label">Status changes</div>${trans}` : ""}
      ${moves ? `<div class="brief-sec-label">Biggest moves</div><div class="brief-moves">${moves}</div>` : ""}
      ${quiet ? `<div class="brief-quiet">Markets are quiet today — no status changes.</div>` : ""}`;
  }

  function compactStrip(data) {
    const t0 = (data.transitions || [])[0];
    const lead = t0
      ? `<a class="brief-strip-lead" href="${t0.href}">${esc(t0.lens_title)}: ${esc(t0.from_status)} &rarr; ${esc(t0.to_status)}</a>`
      : "";
    return `<span class="brief-strip-counts">${esc(countsLine(data.status_counts || {}))}</span>${lead}`;
  }

  window.loadBrief = async function (elId, opts) {
    opts = opts || {};
    const el = document.getElementById(elId);
    if (!el) return;
    try {
      const res = await fetch("/data/brief/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      el.innerHTML = opts.compact ? compactStrip(data) : fullPanel(data);
      el.hidden = false;
    } catch (err) {
      el.hidden = true;  // brief is additive — never block the page
      console.error(err);
    }
  };
})();

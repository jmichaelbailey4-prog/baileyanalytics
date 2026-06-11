/* Shared renderer for hub pages (the dashboards index and each category hub).
   Usage: loadHubGrid("hub-grid", "/data/banking/index.json", id => href) */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function sparkline(values, accent) {
    if (!values || values.length < 2) return "";
    const min = Math.min(...values), max = Math.max(...values), range = (max - min) || 1;
    const pts = values.map((v, i) => {
      const x = (i / (values.length - 1)) * 100;
      const y = 30 - ((v - min) / range) * 28;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    return `<svg class="spark" aria-hidden="true" viewBox="0 0 100 34" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${esc(accent)}" stroke-width="2"/></svg>`;
  }

  function tile(lens, href) {
    const stats = (lens.key_stats || [])
      .map(s => {
        const delta = s.d ? ` <i class="delta ${esc(s.dir || "")}">${esc(s.d)}</i>` : "";
        return `<span>${esc(s.k)} <b>${esc(s.v)}</b>${delta}</span>`;
      }).join("");
    // Cross-category pages (the brief) set category_label so a lens named
    // outside its home category still says where it lives.
    const cat = lens.category_label ? `<span class="hub-cat">${esc(lens.category_label)}</span> · ` : "";
    return `
      <a class="hub-card" href="${href}">
        <div class="hub-eyebrow" style="color:${lens.accent}">${cat}${esc(lens.title)}
          <span class="badge ${esc(lens.status)}">${esc(lens.status)}</span></div>
        <div class="hub-read">${esc(lens.headline_read)}</div>
        ${sparkline(lens.sparkline, lens.accent)}
        <div class="hub-stats">${stats}</div>
        <div class="hub-cta">View lens &rarr;</div>
      </a>`;
  }

  // "3 hours ago" / "2 days ago". Slow-moving sources (banking) legitimately go
  // days between data changes, so this informs without crying wolf.
  function relTime(iso) {
    const h = (Date.now() - new Date(iso).getTime()) / 3.6e6;
    if (!isFinite(h) || h < 0) return "";
    if (h < 1) return "just now";
    if (h < 36) return `${Math.round(h)} hour${Math.round(h) === 1 ? "" : "s"} ago`;
    const d = Math.round(h / 24);
    return `${d} day${d === 1 ? "" : "s"} ago`;
  }

  // Shared card renderer: also used by /dashboards/brief.html.
  window.renderHubTiles = function (grid, lenses, hrefFor) {
    grid.innerHTML = (lenses || []).map(l => tile(l, hrefFor(l.id))).join("");
  };

  // badgeId (optional): element that receives the category's blended status
  // (index.json `status`) as a badge — used by hub h1s and the dashboards index.
  window.loadHubGrid = async function (gridId, url, hrefFor, badgeId) {
    const grid = document.getElementById(gridId);
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      renderHubTiles(grid, data.lenses, hrefFor);
      const badge = badgeId && data.status && document.getElementById(badgeId);
      if (badge) {
        badge.className = `badge ${esc(data.status)}`;
        badge.textContent = data.status;
        badge.title = "Overall category status — balanced across all lenses";
        badge.hidden = false;
      }
      const ago = data.last_updated && relTime(data.last_updated);
      if (ago) grid.insertAdjacentHTML("afterend", `<div class="hub-fresh">Data last changed ${esc(ago)}</div>`);
    } catch (err) {
      grid.innerHTML = `<div class="status-msg error">Dashboards are still being refreshed. Check back shortly.</div>`;
      console.error(err);
    }
  };
})();

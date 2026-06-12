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

  // Public page path for a lens id. Mirrors brief.py lens_href — keep in sync.
  // Rule: page slug = lens id minus its category prefix ("bank-" for banking,
  // "market-" for markets, "<category>-" otherwise), with one true override.
  window.lensHref = function (category, id) {
    if (category === "economic") return `/dashboards/${encodeURIComponent(id)}.html`;
    const overrides = { "consumer-credit": "credit-stress" };
    const prefixes = { banking: "bank-", markets: "market-" };
    const pre = prefixes[category] || category + "-";
    const slug = overrides[id] || (id.indexOf(pre) === 0 ? id.slice(pre.length) : id);
    return `/dashboards/${encodeURIComponent(category)}/${encodeURIComponent(slug)}.html`;
  };

  // Slim hub (Phase C): one card per category — title, blended badge,
  // description, and a status-dot chip per lens. Reads the same index.json
  // the full grids use; the card is one link to the category hub.
  window.loadCategoryCards = async function (elId, cats) {
    const el = document.getElementById(elId);
    if (!el) return;
    const results = await Promise.allSettled(cats.map(async c => {
      const res = await fetch(c.url, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const chips = (data.lenses || []).map(l =>
        `<span class="lens-chip"><span class="chip-dot ${esc(l.status || "unknown")}"></span>${esc(l.title)}</span>`).join("");
      const status = data.status || "unknown";
      return `<a class="cat-card" href="${esc(c.href)}">
        <div class="cat-title">${esc(c.title)} <span class="badge ${esc(status)}">${esc(status)}</span></div>
        <div class="cat-desc">${esc(c.desc)}</div>
        <div class="lens-chips">${chips}</div></a>`;
    }));
    const cards = results.filter(r => r.status === "fulfilled").map(r => r.value);
    results.forEach(r => { if (r.status === "rejected") console.error(r.reason); });
    if (cards.length) el.innerHTML = cards.join("");
  };

  // opts: a badge-element id string, or { badgeId, staleDays }. badgeId receives
  // the category's blended status (index.json `status`); staleDays (default 10)
  // is how long without a data change before the freshness stamp turns amber —
  // banking passes 120 because its quarterly source legitimately goes quiet.
  window.loadHubGrid = async function (gridId, url, hrefFor, opts) {
    if (typeof opts === "string") opts = { badgeId: opts };
    opts = opts || {};
    const grid = document.getElementById(gridId);
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      renderHubTiles(grid, data.lenses, hrefFor);
      const badge = opts.badgeId && data.status && document.getElementById(opts.badgeId);
      if (badge) {
        badge.className = `badge ${esc(data.status)}`;
        badge.textContent = data.status;
        badge.title = "Overall category status — balanced across all lenses";
        badge.hidden = false;
      }
      const ago = data.last_updated && relTime(data.last_updated);
      if (ago) {
        const ageH = (Date.now() - new Date(data.last_updated).getTime()) / 3.6e6;
        const stale = ageH > (opts.staleDays || 10) * 24;
        grid.insertAdjacentHTML("afterend",
          `<div class="hub-fresh${stale ? " stale" : ""}">Data last changed ${esc(ago)}${stale ? " — the refresh may be delayed" : ""}</div>`);
      }
    } catch (err) {
      grid.innerHTML = `<div class="status-msg error">Dashboards are still being refreshed. Check back shortly.</div>`;
      console.error(err);
    }
  };
})();

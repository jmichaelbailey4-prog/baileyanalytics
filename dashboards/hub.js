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
    return `
      <a class="hub-card" href="${href}">
        <div class="hub-eyebrow" style="color:${lens.accent}">${esc(lens.title)}
          <span class="badge ${esc(lens.status)}">${esc(lens.status)}</span></div>
        <div class="hub-read">${esc(lens.headline_read)}</div>
        ${sparkline(lens.sparkline, lens.accent)}
        <div class="hub-stats">${stats}</div>
        <div class="hub-cta">View lens &rarr;</div>
      </a>`;
  }

  window.loadHubGrid = async function (gridId, url, hrefFor) {
    const grid = document.getElementById(gridId);
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      grid.innerHTML = (data.lenses || []).map(l => tile(l, hrefFor(l.id))).join("");
    } catch (err) {
      grid.innerHTML = `<div class="status-msg error">Dashboards are still being refreshed. Check back shortly.</div>`;
      console.error(err);
    }
  };
})();

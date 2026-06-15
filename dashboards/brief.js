/* Shared renderer for Today's Brief (the merged daily surface).
   loadBrief("brief-strip", { compact:true }) -> one-line home summary
   loadBrief("state-line",  { mode:"line" })  -> home hero verdict (element IS the link) */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }

  // One fetch per page view even when two surfaces render (home: hero line +
  // counts strip) — both awaits share the same promise.
  let dataPromise = null;
  function getData() {
    dataPromise = dataPromise || fetch("/data/brief/today.json", { cache: "no-cache" })
      .then(res => { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); });
    return dataPromise;
  }

  function countsText(c) {
    const parts = [];
    if (c.alert) parts.push(`${c.alert} alert`);
    if (c.elevated) parts.push(`${c.elevated} elevated`);
    if (c.watch) parts.push(`${c.watch} on watch`);
    return parts.length ? parts.join(" · ") : "All clear across the dashboards";
  }

  function verdictHtml(v, badgeClass) {
    return `<span class="${badgeClass} ${esc(v.status)}">${esc(v.status)}</span>
      <span class="state-sentence">${esc(v.sentence)}</span>`;
  }

  function compactStrip(data) {
    const t0 = (data.transitions || [])[0];
    const lead = t0
      ? `<a class="brief-strip-lead" href="${t0.href}">${esc(t0.lens_title)}: ${esc(t0.from_status)} &rarr; ${esc(t0.to_status)}</a>`
      : "";
    return `<a class="brief-strip-counts" href="/dashboards/brief.html#pressure">${esc(countsText(data.status_counts || {}))}</a>${lead}`;
  }

  window.loadBrief = async function (elId, opts) {
    opts = opts || {};
    const el = document.getElementById(elId);
    if (!el) return;
    try {
      const data = await getData();
      if (opts.mode === "line") {
        // Home hero one-liner: the element IS the link; .pill classes match
        // the home page's badge styles.
        if (!data.verdict || !data.verdict.sentence) throw new Error("no verdict");
        el.innerHTML = verdictHtml(data.verdict, "pill");
      } else {
        el.innerHTML = compactStrip(data);
      }
      el.hidden = false;
    } catch (err) {
      // Brief is additive — never block the page. Keep any server-baked content
      // (the home hero verdict line ships baked-visible); only hide if empty.
      if (!el.innerHTML.trim()) el.hidden = true;
      console.error(err);
    }
  };
})();

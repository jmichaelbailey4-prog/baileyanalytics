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

  // Category-id -> display name. Lenses shown outside their home category
  // (transitions, brief cards) carry this so "Bank Profitability" vs
  // "Corporate Profits" never needs guessing. Keep in step with brief.py.
  const CAT_LABELS = {
    economic: "Economy", consumer: "Consumer", banking: "Banking",
    business: "Business", markets: "Markets", energy: "Energy",
    housing: "Housing", global: "Global",
  };
  window.briefCategoryLabel = id => CAT_LABELS[id] || "";

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

  function transitionRow(t) {
    const cat = CAT_LABELS[t.category];
    return `<a class="brief-trans" href="${t.href}">
      ${cat ? `<span class="brief-cat">${esc(cat)}</span>` : ""}
      <span class="brief-trans-title">${esc(t.lens_title)}</span>
      <span class="brief-arrow">
        <span class="badge ${esc(t.from_status)}">${esc(t.from_status)}</span>
        &rarr;
        <span class="badge ${esc(t.to_status)}">${esc(t.to_status)}</span>
      </span>
      <span class="brief-trans-read">${esc(t.headline)}</span>
    </a>`;
  }

  // Used by /dashboards/brief.html so transition markup lives in one place.
  window.renderBriefTransitions = transitions => (transitions || []).map(transitionRow).join("");

  function compactStrip(data) {
    const t0 = (data.transitions || [])[0];
    const lead = t0
      ? `<a class="brief-strip-lead" href="${t0.href}">${esc(t0.lens_title)}: ${esc(t0.from_status)} &rarr; ${esc(t0.to_status)}</a>`
      : "";
    return `<a class="brief-strip-counts" href="/dashboards/brief.html">${esc(countsText(data.status_counts || {}))}</a>${lead}`;
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
      el.hidden = true;  // brief is additive — never block the page
      console.error(err);
    }
  };
})();

/* Shared renderer for The State of Things.
   loadState("state-panel", { mode: "panel" }) -> hub strip (badge + sentence + link)
   loadState("state-line",  { mode: "line" })  -> home one-liner (the element IS the link;
                                                  uses the home page's .pill badge classes)
   loadState(null,          { mode: "page" })  -> fills the state.html sections */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function verdict(v, badgeClass, withLink) {
    return `<span class="${badgeClass} ${esc(v.status)}">${esc(v.status)}</span>
      <span class="state-sentence">${esc(v.sentence)}</span>` +
      (withLink ? ` <a class="state-link" href="/dashboards/state.html">The full picture &rarr;</a>` : "");
  }

  function pressureCard(p) {
    const lenses = (p.lenses || []).map(l => `
      <a class="state-lens" href="${l.href}">
        <span class="badge ${esc(l.status)}">${esc(l.status)}</span>
        <span class="state-lens-title">${esc(l.title)}</span>
        <span class="state-lens-read">${esc(l.headline)}</span></a>`).join("");
    return `<div class="state-card">
      <a class="state-cat" href="${p.href}">${esc(p.title)}
        <span class="badge ${esc(p.status)}">${esc(p.status)}</span></a>${lenses}</div>`;
  }

  function steadyChip(c) {
    return `<a class="state-steady" href="${c.href}">
      <span class="badge ${esc(c.status)}">${esc(c.status)}</span>${esc(c.title)}</a>`;
  }

  function renderPage(data) {
    document.getElementById("verdict").innerHTML =
      `<div class="state-verdict">${verdict(data.verdict, "badge", false)}</div>`;
    const stamp = data.generated_at && new Date(data.generated_at);
    if (stamp && !isNaN(stamp)) {
      document.getElementById("asof").textContent = "As of " +
        stamp.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    }
    const pp = data.pressure_points || [];
    if (pp.length) {
      document.getElementById("pressure-sec").hidden = false;
      document.getElementById("pressure").innerHTML = pp.map(pressureCard).join("");
    }
    const st = data.steady || [];
    if (st.length) {
      document.getElementById("steady-sec").hidden = false;
      document.getElementById("steady").innerHTML = st.map(steadyChip).join("");
    }
    if (data.changed) {
      const n = Number(data.changed.transitions);
      document.getElementById("changed-sec").hidden = false;
      document.getElementById("changed").innerHTML = n
        ? `<a class="state-link" href="${esc(data.changed.href)}">${n} lens${n === 1 ? "" : "es"} changed status today — see Today&rsquo;s Brief &rarr;</a>`
        : `Quiet day — no status changes. <a class="state-link" href="${esc(data.changed.href)}">Today&rsquo;s Brief &rarr;</a>`;
    }
  }

  window.loadState = async function (elId, opts) {
    opts = opts || {};
    const el = elId ? document.getElementById(elId) : null;
    if (elId && !el) return;
    try {
      const res = await fetch("/data/state/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (!data.verdict || !data.verdict.sentence) throw new Error("no verdict");
      if (opts.mode === "page") { renderPage(data); return; }
      el.innerHTML = opts.mode === "line"
        ? verdict(data.verdict, "pill", false)
        : `<div class="state-verdict">${verdict(data.verdict, "badge", true)}</div>`;
      el.hidden = false;
    } catch (err) {
      // The state is additive — never block the page it sits on.
      if (opts.mode === "page") {
        document.getElementById("verdict").innerHTML =
          `<div class="status-msg error">The State of Things is still being refreshed. Check back shortly.</div>`;
      } else if (el) {
        el.hidden = true;
      }
      console.error(err);
    }
  };
})();

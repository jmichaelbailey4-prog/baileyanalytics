/* Shared renderer for lens pages. Usage: renderLens('/data/lenses/recession-watch.json') */
(function () {
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const RANGES = { "1Y": 1, "5Y": 5, "Max": null };

  function fmtDate(s) {
    const [y, m, d] = s.split("-");
    return `${MONTHS[+m - 1]} ${d ? +d + ", " : ""}${y}`;
  }
  function fmtMonth(s) {
    const [y, m] = s.split("-");
    if (!m) return y; // annual series ("2026") label the year alone
    return `${MONTHS[+m - 1]} ${y}`;
  }
  // Monthly/quarterly series date every point on the 1st; showing "May 1, 2026"
  // would imply daily precision the data doesn't have.
  function isMonthly(observations) {
    return observations.length > 0 &&
      observations.every(o => o.date.length < 10 || o.date.slice(8) === "01");
  }
  function fmtUpdated(iso) {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  }
  function fmtVal(value, unit, fmt) {
    const f = parseFloat(value);
    if (isNaN(f)) return "—";
    const sign = f < 0 ? "-" : "";
    const a = Math.abs(f);
    const num = (fmt === "thousands") ? Math.round(a).toLocaleString("en-US") : a.toFixed(2);
    if (!unit) return sign + num;
    if (unit[0] === "$") return sign + "$" + num + unit.slice(1); // "$" / "$T" / "-$55.90B"
    // word units ("months", "Bcf") read better with a space; symbols ("%", "M", "k") stay tight
    return sign + ((unit.length > 1 && /^[a-z]/i.test(unit)) ? num + " " + unit : num + unit);
  }
  function esc(s) {
    const d = document.createElement("div"); d.textContent = s; return d.innerHTML;
  }
  function cutoff(observations, years) {
    if (!years || !observations.length) return observations;
    const last = new Date(observations[observations.length - 1].date);
    const limit = new Date(last); limit.setFullYear(limit.getFullYear() - years);
    return observations.filter(o => new Date(o.date) >= limit);
  }

  // Theme-aware chart chrome: read from the --chart-* CSS vars so charts match
  // the active theme at build time and can recolor live on a `ba:theme` event.
  function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  // Honor the OS "reduce motion" setting: Chart.js animates by default; CSS
  // transitions already respect this, so charts should too.
  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }
  function chartChrome() {
    return {
      grid: cssVar("--chart-grid") || "#1E293B", tick: cssVar("--chart-tick") || "#64748B",
      axis: cssVar("--chart-axis") || "#1E293B", ttBg: cssVar("--chart-tooltip-bg") || "#0A0E14",
      ttBorder: cssVar("--chart-tooltip-border") || "#1E293B",
      ttTitle: cssVar("--chart-tooltip-title") || "#F8FAFC", ttBody: cssVar("--chart-tooltip-body") || "#CBD5E1",
    };
  }

  // Custom plugin: shade recession periods using the x category scale.
  const recessionPlugin = {
    id: "recessionBands",
    beforeDraw(chart, args, opts) {
      const periods = opts.periods || [];
      if (!periods.length) return;
      const { ctx, chartArea, scales: { x } } = chart;
      const labels = chart.data.labels;
      ctx.save();
      ctx.fillStyle = cssVar("--chart-recession") || "rgba(248,113,113,0.09)";
      periods.forEach(p => {
        let i0 = labels.findIndex(l => l >= p.start);
        let i1 = -1;
        for (let i = labels.length - 1; i >= 0; i--) { if (labels[i] < p.end) { i1 = i; break; } }
        if (i0 === -1 || i1 === -1 || i1 < i0) return;
        const xa = x.getPixelForValue(i0), xb = x.getPixelForValue(i1);
        ctx.fillRect(xa, chartArea.top, Math.max(xb - xa, 2), chartArea.bottom - chartArea.top);
      });
      ctx.restore();
    },
  };

  function makeChart(canvas, indicator, recessions, years) {
    const obs = cutoff(indicator.observations, years).filter(o => o.value !== "." && o.value !== null);
    const labels = obs.map(o => o.date);
    const values = obs.map(o => parseFloat(o.value));
    const monthly = isMonthly(indicator.observations);
    const c = chartChrome();
    return new Chart(canvas.getContext("2d"), {
      type: "line",
      plugins: [recessionPlugin],
      data: { labels, datasets: [{ data: values, borderColor: indicator.color, borderWidth: 2,
        pointRadius: 0, tension: 0.25, fill: true, backgroundColor: indicator.color + "1A" }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: reducedMotion() ? false : undefined,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          recessionBands: { periods: recessions },
          tooltip: {
            backgroundColor: c.ttBg, borderColor: c.ttBorder, borderWidth: 1,
            titleColor: c.ttTitle, bodyColor: c.ttBody, padding: 10,
            callbacks: {
              title: items => monthly ? fmtMonth(items[0].label) : fmtDate(items[0].label),
              label: ctx => " " + fmtVal(ctx.parsed.y, indicator.unit, indicator.value_format),
            },
          },
        },
        scales: {
          x: { type: "category", ticks: { maxTicksLimit: 7, color: c.tick, font: { size: 11 },
                 callback(v) { const s = this.getLabelForValue(v); if (!s) return s;
                   // annual labels ("2026") have no month part — always show the year
                   return (years && years <= 1 && s.length >= 7) ? MONTHS[+s.slice(5, 7) - 1] : s.slice(0, 4); } },
               // Labels are month/year-granular while ticks are sampled from daily/weekly
               // points, so consecutive SHOWN ticks can repeat ("Jun Jun", "2024 2024").
               // The tick callback runs before Chart.js auto-skips down to ~7 ticks, so
               // dedupe must happen here, after auto-skip, on the displayed set only.
               afterUpdate(axis) {
                 const t = axis.ticks;
                 for (let i = t.length - 1; i > 0; i--) {
                   if (t[i].label && t[i].label === t[i - 1].label) t[i].label = "";
                 }
               },
               grid: { display: false }, border: { color: c.axis } },
          y: { ticks: { color: c.tick, font: { size: 11 }, maxTicksLimit: 7, callback: v => fmtVal(v, indicator.unit, indicator.value_format) },
               grid: { color: c.grid }, border: { display: false } },
        },
      },
    });
  }

  // The muted "why a signal carries no score / forecast" note. Mirrors
  // build.signal_note (Python) — keep the matrix + headings in sync.
  function signalNote(ind) {
    const sev = ind.no_severity_reason || "", pred = ind.no_prediction_reason || "";
    let heading, body;
    if (sev && pred) { heading = "Why it isn’t scored or forecast"; body = sev + " " + pred; }
    else if (sev) { heading = "Why it isn’t scored"; body = sev; }
    else if (pred) { heading = "Why it isn’t forecast"; body = pred; }
    else return "";
    return `<div class="signal-note"><strong>${esc(heading)}:</strong> ${esc(body)}</div>`;
  }

  function indicatorCard(indicator, recessions, defaultRange) {
    const el = document.createElement("div");
    el.className = "ind";
    el.id = "ind-" + indicator.id;        // shareable anchor (#ind-<id>)
    el.style.scrollMarginTop = "1rem";
    el.dataset.indicator = indicator.id;  // hook for predict.js + scoring.js blocks
    if (indicator.scale_now != null) el.dataset.scaleNow = indicator.scale_now;  // scoring.js marker
    const latest = indicator.latest ? fmtVal(indicator.latest.value, indicator.unit, indicator.value_format) : "—";
    const fmtAsOf = isMonthly(indicator.observations) ? fmtMonth : fmtDate;
    const asOf = indicator.latest ? `<div class="ind-asof">as of ${fmtAsOf(indicator.latest.date)}</div>` : "";
    el.innerHTML = `
      <div class="ind-top">
        <div class="ind-title">${esc(indicator.title)}</div>
        <div class="ind-num"><div class="ind-val" style="color:${indicator.color}">${latest}</div>${asOf}</div>
      </div>
      <div class="ranges" role="group" aria-label="Chart range"></div>
      <div class="chart-box"><canvas role="img" aria-label="${esc(indicator.title)} — line chart"></canvas></div>
      <div class="context">
        <div class="ctx-block"><div class="lbl">What it is</div><p>${esc(indicator.context)}</p></div>
        <div class="ctx-block read"><div class="lbl">The read right now</div><p>${esc(indicator.read)}</p></div>
      </div>
      ${signalNote(indicator)}`;
    const canvas = el.querySelector("canvas");
    const rangesBox = el.querySelector(".ranges");
    const pageDefault = (defaultRange in RANGES) ? defaultRange : "1Y";
    const startKey = (window.BAPrefs && window.BAPrefs.effectiveRange)
      ? window.BAPrefs.effectiveRange(pageDefault) : pageDefault;
    let chart = makeChart(canvas, indicator, recessions, RANGES[startKey]);
    Object.keys(RANGES).forEach(key => {
      const btn = document.createElement("button");
      btn.textContent = key;
      btn.setAttribute("aria-pressed", String(key === startKey));
      if (key === startKey) btn.classList.add("active");
      btn.addEventListener("click", () => {
        rangesBox.querySelectorAll("button").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-pressed", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-pressed", "true");
        chart.destroy();
        chart = makeChart(canvas, indicator, recessions, RANGES[key]);
        if (window.BAPrefs && window.BAPrefs.setRangeDefault) window.BAPrefs.setRangeDefault(key);
      });
      rangesBox.appendChild(btn);
    });
    return el;
  }

  // Per-category chrome. Economic is the default so existing pages — which call
  // renderLens(url) with no options — render exactly as before.
  const DEFAULT_OPTS = {
    back: "Economic Lenses",
    href: "/dashboards/economic/",
    foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, ' +
      'St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.',
  };

  function tiersHtml(tiers) {
    if (!tiers) return "";
    const head = `<th>Bank tier</th>` +
      tiers.columns.map(c => `<th class="num">${esc(c.label)}</th>`).join("");
    const body = tiers.rows.map(r =>
      `<tr><td>${esc(r.tier)}</td>` +
      r.values.map(v => `<td class="num ${esc(v.status || "")}">${esc(v.value)}</td>`).join("") +
      `</tr>`).join("");
    return `<section class="tbl-sec">
      <div class="tbl-lab">${esc(tiers.label)}</div>
      <div class="tbl-sub">${esc(tiers.subtitle || "")}</div>
      <table class="lens-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
    </section>`;
  }

  function rankingsHtml(rankings) {
    return (rankings || []).map(rk => {
      const body = rk.rows.map(row =>
        `<tr>
          <td><span class="bankname">${esc(row.name)}</span><br><span class="bankloc">${esc(row.location)}</span></td>
          <td class="num ${esc(row.status || "")}">${esc(row.value)}</td>
          <td class="num">${esc(row.asset)}</td>
          <td><span class="tpill ${esc(row.status || "")}">${esc(row.status || "")}</span></td>
        </tr>`).join("");
      return `<section class="tbl-sec">
        <div class="tbl-lab">Bank spotlight — ranked</div>
        <div class="tbl-sub">${esc(rk.subtitle || rk.title)}</div>
        <table class="lens-table"><thead><tr>
          <th>Bank</th><th class="num">${esc(rk.value_label)}</th><th class="num">Assets</th><th>Signal</th>
        </tr></thead><tbody>${body}</tbody></table>
      </section>`;
    }).join("");
  }

  // Journey-aware back: where the reader CAME FROM (same-origin referrer),
  // falling back to the category hub. Validated against the browser-default
  // strict-origin-when-cross-origin policy — never add a stricter
  // <meta name="referrer"> or this silently degrades to the fallback.
  function journeyBack(opts) {
    try {
      const r = document.referrer ? new URL(document.referrer) : null;
      if (r && r.origin === location.origin) {
        if (r.pathname === "/dashboards/brief.html") return { label: "Back to Today’s Brief", href: "/dashboards/brief.html" };
        if (r.pathname === "/" || r.pathname === "/index.html") return { label: "Back to home", href: "/" };
      }
    } catch (e) { /* malformed referrer: use the fallback */ }
    return { label: opts.back, href: opts.href };
  }

  function render(root, lens, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const scoreboard = lens.indicators.map(i => `
      <div class="signal">
        <div class="k">${esc(i.short)}</div>
        <div class="v">${i.latest ? fmtVal(i.latest.value, i.unit, i.value_format) : "—"}</div>
        <div class="s ${i.signal_status}">${esc(i.signal_status)}</div>
      </div>`).join("");
    const back = journeyBack(opts);
    const favCategory = (opts.href || "/dashboards/economic/").split("/").filter(Boolean).pop();
    root.innerHTML = `
      <div class="crumbs"><a href="/dashboards/">Dashboards</a><span class="sep">›</span><a href="${esc(opts.href)}">${esc(opts.back)}</a><span class="sep">›</span><span class="here">${esc(lens.title)}</span></div>
      <a class="back" href="${esc(back.href)}">← ${esc(back.label)}</a>
      <div class="eyebrow" style="color:${lens.accent}">${esc(lens.title)}</div>
      <h1 class="read-hero">${esc(lens.headline_read)}</h1>
      <div class="badgerow">
        <span class="badge ${lens.status}">${esc(lens.status)}</span>
        <span class="updated">Updated ${fmtUpdated(lens.last_updated)} · ${lens.indicators.length} signals</span>
        <button class="fav-star js-only" type="button" aria-pressed="false"
          data-fav-id="${esc(lens.id)}" data-fav-title="${esc(lens.title)}" data-fav-category="${esc(favCategory)}"
          aria-label="Save to Favorites" title="Save to Favorites">&#9734;</button>
      </div>
      <div class="scoreboard">${scoreboard}</div>
      <div class="indicators"></div>
      ${tiersHtml(lens.tiers)}
      ${rankingsHtml(lens.rankings)}
      <div class="foot">${opts.foot}</div>`;
    const holder = root.querySelector(".indicators");
    const defaultRange = opts.defaultRange || "1Y";
    lens.indicators.forEach(i => holder.appendChild(indicatorCard(i, lens.recessions || [], defaultRange)));
    // `category` (the page-declared category id) lets predict.js/scoring.js fetch
    // the right per-category prediction/methodology slice without re-deriving it.
    document.dispatchEvent(new CustomEvent("lens:rendered", { detail: { id: lens.id, category: favCategory } }));
    // Deep links to an indicator card (#ind-<id>) — the content doesn't exist
    // until this render, so the browser's own fragment scroll already gave up.
    if (location.hash) {
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) target.scrollIntoView();
    }
  }

  // Recolor existing charts when the theme flips (personalize.js dispatches
  // ba:theme). Chart.getChart(canvas) avoids stale refs after range-rebuilds.
  document.addEventListener("ba:theme", function () {
    if (typeof Chart === "undefined" || !Chart.getChart) return;
    var c = chartChrome();
    document.querySelectorAll(".chart-box canvas").forEach(function (cv) {
      var ch = Chart.getChart(cv);
      if (!ch) return;
      var o = ch.options;
      o.plugins.tooltip.backgroundColor = c.ttBg; o.plugins.tooltip.borderColor = c.ttBorder;
      o.plugins.tooltip.titleColor = c.ttTitle;   o.plugins.tooltip.bodyColor = c.ttBody;
      o.scales.x.ticks.color = c.tick; o.scales.x.border.color = c.axis;
      o.scales.y.ticks.color = c.tick; o.scales.y.grid.color = c.grid;
      ch.update("none");
    });
  });

  window.renderLens = async function (jsonUrl, opts) {
    const root = document.getElementById("lens-root");
    try {
      const res = await fetch(jsonUrl, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      render(root, await res.json(), opts);
    } catch (err) {
      root.innerHTML = `<div class="status-msg error">Data is still being refreshed. Check back shortly.</div>`;
      console.error(err);
    }
  };
})();

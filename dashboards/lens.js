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

  // Custom plugin: shade recession periods using the x category scale.
  const recessionPlugin = {
    id: "recessionBands",
    beforeDraw(chart, args, opts) {
      const periods = opts.periods || [];
      if (!periods.length) return;
      const { ctx, chartArea, scales: { x } } = chart;
      const labels = chart.data.labels;
      ctx.save();
      ctx.fillStyle = "rgba(248,113,113,0.09)";
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
    return new Chart(canvas.getContext("2d"), {
      type: "line",
      plugins: [recessionPlugin],
      data: { labels, datasets: [{ data: values, borderColor: indicator.color, borderWidth: 2,
        pointRadius: 0, tension: 0.25, fill: true, backgroundColor: indicator.color + "1A" }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: false },
          recessionBands: { periods: recessions },
          tooltip: {
            backgroundColor: "#0A0E14", borderColor: "#1E293B", borderWidth: 1,
            titleColor: "#F8FAFC", bodyColor: "#CBD5E1", padding: 10,
            callbacks: {
              title: items => monthly ? fmtMonth(items[0].label) : fmtDate(items[0].label),
              label: ctx => " " + fmtVal(ctx.parsed.y, indicator.unit, indicator.value_format),
            },
          },
        },
        scales: {
          x: { type: "category", ticks: { maxTicksLimit: 7, color: "#64748B", font: { size: 11 },
                 callback(v) { const s = this.getLabelForValue(v); if (!s) return s;
                   // annual labels ("2026") have no month part — always show the year
                   return (years && years <= 1 && s.length >= 7) ? MONTHS[+s.slice(5, 7) - 1] : s.slice(0, 4); } },
               grid: { display: false }, border: { color: "#1E293B" } },
          y: { ticks: { color: "#64748B", font: { size: 11 }, callback: v => fmtVal(v, indicator.unit, indicator.value_format) },
               grid: { color: "#1E293B" }, border: { display: false } },
        },
      },
    });
  }

  function indicatorCard(indicator, recessions, defaultRange) {
    const el = document.createElement("div");
    el.className = "ind";
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
      </div>`;
    const canvas = el.querySelector("canvas");
    const rangesBox = el.querySelector(".ranges");
    const startKey = (defaultRange in RANGES) ? defaultRange : "1Y";
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
      });
      rangesBox.appendChild(btn);
    });
    return el;
  }

  // Per-category chrome. Economic is the default so existing pages — which call
  // renderLens(url) with no options — render exactly as before.
  const DEFAULT_OPTS = {
    back: "Economic Lenses",
    href: "/dashboards/",
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

  function render(root, lens, opts) {
    opts = Object.assign({}, DEFAULT_OPTS, opts || {});
    const scoreboard = lens.indicators.map(i => `
      <div class="signal">
        <div class="k">${esc(i.short)}</div>
        <div class="v">${i.latest ? fmtVal(i.latest.value, i.unit, i.value_format) : "—"}</div>
        <div class="s ${i.signal_status}">${esc(i.signal_status)}</div>
      </div>`).join("");
    root.innerHTML = `
      <a class="back" href="${esc(opts.href)}">← ${esc(opts.back)}</a>
      <div class="eyebrow" style="color:${lens.accent}">${esc(lens.title)}</div>
      <div class="read-hero">${esc(lens.headline_read)}</div>
      <div class="badgerow">
        <span class="badge ${lens.status}">${esc(lens.status)}</span>
        <span class="updated">Updated ${fmtUpdated(lens.last_updated)} · ${lens.indicators.length} signals</span>
      </div>
      <div class="scoreboard">${scoreboard}</div>
      <div class="indicators"></div>
      ${tiersHtml(lens.tiers)}
      ${rankingsHtml(lens.rankings)}
      <div class="foot">${opts.foot}</div>`;
    const holder = root.querySelector(".indicators");
    const defaultRange = opts.defaultRange || "1Y";
    lens.indicators.forEach(i => holder.appendChild(indicatorCard(i, lens.recessions || [], defaultRange)));
  }

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

/* Shared renderer for lens pages. Usage: renderLens('/data/lenses/recession-watch.json') */
(function () {
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const RANGES = { "1Y": 1, "5Y": 5, "Max": null };

  function fmtDate(s) {
    const [y, m, d] = s.split("-");
    return `${MONTHS[+m - 1]} ${d ? +d + ", " : ""}${y}`;
  }
  function fmtUpdated(iso) {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  }
  function fmtVal(value, unit, fmt) {
    const f = parseFloat(value);
    if (isNaN(f)) return "—";
    if (fmt === "thousands") return Math.round(f).toLocaleString("en-US") + unit;
    return f.toFixed(2) + unit;
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
              title: items => fmtDate(items[0].label),
              label: ctx => " " + fmtVal(ctx.parsed.y, indicator.unit, indicator.value_format),
            },
          },
        },
        scales: {
          x: { type: "category", ticks: { maxTicksLimit: 7, color: "#64748B", font: { size: 11 },
                 callback(v) { const s = this.getLabelForValue(v); return s ? s.slice(0, 4) : s; } },
               grid: { display: false }, border: { color: "#1E293B" } },
          y: { ticks: { color: "#64748B", font: { size: 11 }, callback: v => indicator.value_format === "thousands" ? Math.round(v).toLocaleString("en-US") + indicator.unit : v + indicator.unit },
               grid: { color: "#1E293B" }, border: { display: false } },
        },
      },
    });
  }

  function indicatorCard(indicator, recessions) {
    const el = document.createElement("div");
    el.className = "ind";
    const latest = indicator.latest ? fmtVal(indicator.latest.value, indicator.unit, indicator.value_format) : "—";
    el.innerHTML = `
      <div class="ind-top">
        <div class="ind-title">${esc(indicator.title)}</div>
        <div class="ind-val" style="color:${indicator.color}">${latest}</div>
      </div>
      <div class="ranges"></div>
      <div class="chart-box"><canvas></canvas></div>
      <div class="context">
        <div class="ctx-block"><div class="lbl">What it is</div><p>${esc(indicator.context)}</p></div>
        <div class="ctx-block read"><div class="lbl">The read right now</div><p>${esc(indicator.read)}</p></div>
      </div>`;
    const canvas = el.querySelector("canvas");
    const rangesBox = el.querySelector(".ranges");
    let chart = makeChart(canvas, indicator, recessions, RANGES.Max);
    Object.keys(RANGES).forEach(key => {
      const btn = document.createElement("button");
      btn.textContent = key;
      if (key === "Max") btn.classList.add("active");
      btn.addEventListener("click", () => {
        rangesBox.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        chart.destroy();
        chart = makeChart(canvas, indicator, recessions, RANGES[key]);
      });
      rangesBox.appendChild(btn);
    });
    return el;
  }

  function render(root, lens) {
    const scoreboard = lens.indicators.map(i => `
      <div class="signal">
        <div class="k">${esc(i.short)}</div>
        <div class="v">${i.latest ? fmtVal(i.latest.value, i.unit, i.value_format) : "—"}</div>
        <div class="s ${i.signal_status}">${esc(i.signal_status)}</div>
      </div>`).join("");
    root.innerHTML = `
      <a class="back" href="/dashboards/">← Economic Lenses</a>
      <div class="eyebrow" style="color:${lens.accent}">${esc(lens.title)}</div>
      <div class="read-hero">${esc(lens.headline_read)}</div>
      <div class="badgerow">
        <span class="badge ${lens.status}">${esc(lens.status)}</span>
        <span class="updated">Updated ${fmtUpdated(lens.last_updated)} · ${lens.indicators.length} signals</span>
      </div>
      <div class="scoreboard">${scoreboard}</div>
      <div class="indicators"></div>
      <div class="foot">
        Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>,
        St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.
      </div>`;
    const holder = root.querySelector(".indicators");
    lens.indicators.forEach(i => holder.appendChild(indicatorCard(i, lens.recessions || [])));
  }

  window.renderLens = async function (jsonUrl) {
    const root = document.getElementById("lens-root");
    try {
      const res = await fetch(jsonUrl, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      render(root, await res.json());
    } catch (err) {
      root.innerHTML = `<div class="status-msg error">Data is still being refreshed. Check back shortly.</div>`;
      console.error(err);
    }
  };
})();

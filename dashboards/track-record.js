/* Track Record page renderer: aggregates from track-record.json, recent
   grades from recent.json. Fully additive — a missing file leaves the
   young-record copy in place. */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  async function get(url) {
    try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; }
    catch (e) { return null; }
  }
  const TITLES = { economic: "Economic Lenses", consumer: "The Consumer",
    markets: "Markets & Financial Conditions", energy: "Energy & Commodities",
    housing: "Housing & Real Estate", global: "Global Economy",
    business: "Corporate & Business Health", banking: "Banking System Health" };
  const pct = x => `${Math.round(x * 100)}%`;
  // Mirrors lens.js fmtVal / build.py _fmt — keep in sync (house rule).
  function fmtVal(v, unit, vf) {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "", a = Math.abs(v);
    const num = vf === "thousands" ? Math.round(a).toLocaleString("en-US")
      : a.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (!unit) return sign + num;
    if (unit[0] === "$") return `${sign}$${num}${unit.slice(1)}`;
    if (unit.length > 1 && /[a-z]/i.test(unit[0])) return `${sign}${num} ${unit}`;
    return `${sign}${num}${unit}`;
  }
  document.addEventListener("DOMContentLoaded", async function () {
    const [tr, recent] = await Promise.all([
      get("/data/predictions/track-record.json"), get("/data/predictions/recent.json")]);
    if (!tr || !tr.graded) {
      document.getElementById("since").textContent =
        "The first predictions are open now — grades land as the prints arrive. Check back this week.";
      return;
    }
    if (tr.since) {
      const d = new Date(tr.since);
      const when = isNaN(d) ? tr.since.slice(0, 10)
        : d.toLocaleDateString(undefined, { year: "numeric", month: "long" });
      document.getElementById("since").textContent =
        `${tr.graded} predictions graded since ${when} — this record grows weekly. ` +
        `Every one was published before the number existed.`;
    }
    document.getElementById("calibration").textContent = pct(tr.calibration);
    document.getElementById("skill").textContent = pct(Math.max(tr.skill, 0));
    const cats = Object.entries(tr.categories || {});
    if (cats.length) {
      document.getElementById("cats-sec").hidden = false;
      document.getElementById("cats").innerHTML = `<table class="lens-table">
        <thead><tr><th>Category</th><th class="num">Graded</th><th class="num">In range</th>
        <th class="num">Direction</th><th class="num">Skill vs naive</th></tr></thead><tbody>` +
        cats.map(([c, b]) => `<tr><td>${esc(TITLES[c] || c)}</td><td class="num">${b.graded}</td>
          <td class="num">${b.graded ? pct(b.calibration) : "—"}</td>
          <td class="num">${b.graded ? pct(b.direction) : "—"}</td>
          <td class="num">${b.graded ? pct(Math.max(b.skill, 0)) : "—"}</td></tr>`).join("") +
        `</tbody></table>`;
    }
    const feed = (recent && recent.feed) || [];
    if (feed.length) {
      document.getElementById("feed-sec").hidden = false;
      document.getElementById("feed").innerHTML = feed.map(e => {
        const g = e.grade, mark = g.hit ? "✓" : "✗", cls = g.hit ? "hit" : "miss";
        const rev = g.revised_to != null
          ? ` <span class="pred-rev">(revised to ${esc(fmtVal(g.revised_to, e.unit, e.value_format))})</span>` : "";
        return `<a class="track-row" href="${esc(e.href)}">
          <span class="pred-mark ${cls}">${mark}</span>
          <span class="track-ind">${esc(e.title)}</span>
          <span class="track-said">we said ${esc(fmtVal(e.point, e.unit, e.value_format))},
            actual ${esc(fmtVal(g.actual, e.unit, e.value_format))}${rev}</span></a>`;
      }).join("");
    }
  });
})();

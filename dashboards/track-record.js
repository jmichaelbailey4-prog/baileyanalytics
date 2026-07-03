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
  // Edge stats (skill/direction) can be null before any signal series is graded.
  const pctn = x => (x == null ? "&mdash;" : pct(Math.max(x, 0)));
  // MONTHS + fmtDue mirror predict.js — keep in sync (house rule). Note the
  // shape differs on purpose: predict.js returns "due ~Jun 5" (standalone);
  // here it returns "~Jun 5" and the call site adds the "· due " prefix.
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDue(iso) {
    if (!iso || iso.length < 10) return "";
    return `~${MONTHS[+iso.slice(5, 7) - 1]} ${+iso.slice(8, 10)}`;
  }
  // Mirrors lens.js fmtVal / build.py _fmt — keep in sync (house rule).
  function fmtVal(v, unit, vf) {
    if (v == null || isNaN(v)) return "—";
    const sign = v < 0 ? "-" : "", a = Math.abs(v);
    const num = vf === "thousands" ? Math.round(a).toLocaleString("en-US") : a.toFixed(2);
    if (!unit) return sign + num;
    if (unit[0] === "$") return `${sign}$${num}${unit.slice(1)}`;
    if (unit.length > 1 && /[a-z]/i.test(unit[0])) return `${sign}${num} ${unit}`;
    return `${sign}${num}${unit}`;
  }
  // The open predictions — shown whether or not anything has been graded yet, so
  // the page is never an empty flagship: it's the public list of calls on record.
  function renderOpen(open) {
    const preds = (open && open.predictions) || [];
    if (!preds.length) return;
    const isMove = p => !p.descriptive && p.implied_status && p.current_status
      && p.implied_status !== p.current_status;
    const moves = preds.filter(isMove).length;
    document.getElementById("open-sec").hidden = false;
    const moveCopy = moves
      ? ` ${moves === 1 ? "One of them implies" : moves + " of them imply"} a status change if it lands — ${moves === 1 ? "it is" : "those are"} flagged below.` : "";
    document.getElementById("open-intro").textContent =
      `${preds.length} predictions are open right now — each published before its number existed, ` +
      `each awaiting its print and a public grade.${moveCopy}`;
    // Far-overdue rows are lagging *sources* (GEPU publishes ~6 months late),
    // not stale promises — sort them last and say why, or the list opens with
    // "due ~Jan 15" in July.
    const cutoff = new Date(Date.now() - 45 * 864e5).toISOString().slice(0, 10);
    const isLate = p => p.due && p.due < cutoff;
    const rows = preds.slice().sort((a, b) =>
      (isLate(a) - isLate(b)) || (a.due || "").localeCompare(b.due || ""));
    document.getElementById("open").innerHTML = rows.map(p => {
      const range = `${esc(fmtVal(p.lo, p.unit, p.value_format))}–${esc(fmtVal(p.hi, p.unit, p.value_format))}`;
      const move = isMove(p)
        ? ` <span class="badge ${esc(p.implied_status)}">&rarr; ${esc(p.implied_status)}</span>` : "";
      const due = isLate(p) ? " · still awaiting a print, well past the usual date"
        : (p.due ? ` · due ${esc(fmtDue(p.due))}` : "");
      return `<a class="track-row" href="${esc(p.href)}">
        <span class="track-ind">${esc(p.title)}</span>
        <span class="track-said">we expect ~${esc(fmtVal(p.point, p.unit, p.value_format))}
          (likely ${range})${due}</span>${move}</a>`;
    }).join("");
  }
  document.addEventListener("DOMContentLoaded", async function () {
    const [tr, recent, open] = await Promise.all([
      get("/data/predictions/track-record.json"), get("/data/predictions/recent.json"),
      get("/data/predictions/open.json")]);
    renderOpen(open);
    if (!tr || !tr.graded) {
      document.getElementById("since").textContent =
        "The first predictions are open now — grades land as the prints arrive. Check back this week.";
      document.getElementById("calibration").textContent = "pending";
      document.getElementById("badge").textContent = "pending";
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
    // Badge accuracy on the badge-driving series — a stronger, equally honest
    // headline than the edge-over-naive skill (which is broken out by category
    // below). "pending" until at least one signal series is graded.
    document.getElementById("badge").textContent =
      tr.status == null ? "pending" : pct(tr.status);
    const cats = Object.entries(tr.categories || {});
    if (cats.length) {
      document.getElementById("cats-sec").hidden = false;
      document.getElementById("cats").innerHTML = `<table class="lens-table">
        <thead><tr><th>Category</th><th class="num">Graded</th><th class="num">In range</th>
        <th class="num">Direction</th><th class="num">Skill vs naive</th></tr></thead><tbody>` +
        cats.map(([c, b]) => `<tr><td>${esc(TITLES[c] || c)}</td><td class="num">${b.graded}</td>
          <td class="num">${b.graded ? pct(b.calibration) : "—"}</td>
          <td class="num">${b.graded ? pctn(b.direction) : "—"}</td>
          <td class="num">${b.graded ? pctn(b.skill) : "—"}</td></tr>`).join("") +
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

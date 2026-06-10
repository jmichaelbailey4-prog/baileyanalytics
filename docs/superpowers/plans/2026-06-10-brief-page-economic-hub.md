# Brief Detail Page + Economic Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Today's Brief detail page (`/dashboards/brief.html`) with anchored sections of hub cards, slim the landing brief panel to linked counts + transitions, and give the Economic category its missing hub page + "Overview →" link.

**Architecture:** `brief.py` exposes the already-computed flat lens list in `today.json` (`lenses`: id/title/category/href/status) so the new page can group and link without duplicating slug maps. `hub.js` exports its private card renderer as `renderHubTiles`; `brief.html` joins `today.json` against the six category `index.json` files client-side and renders sections with those exact cards. `brief.js` drops the inline move rows and renders linked counts + "Biggest movers → / Full brief →". The economic hub is a clone of the housing hub fed by `/data/lenses/index.json`.

**Tech Stack:** Python 3.12 stdlib + `unittest`; zero-build static HTML/CSS/JS.

**Spec:** `docs/superpowers/specs/2026-06-10-brief-page-and-economic-hub-design.md`
**Branch:** `feat/brief-page-economic-hub`

---

## Conventions

- Full suite: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
- One file: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
- Git: `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" ...`; commit per task, trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`; **do not push**.
- Frontend checks: background `python -m http.server 8123 --directory "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics"` + curl greps.

---

### Task 1: `lenses` list in `today.json` (TDD)

**Files:**
- Modify: `scripts/lenses/brief.py` (`build_brief`)
- Test: `scripts/tests/test_brief.py`, `scripts/tests/test_refresh_brief.py`

- [ ] **Step 1: Failing tests.** Append to `test_brief.py` (before `if __name__`):

```python
class TestBriefLensesList(unittest.TestCase):
    def test_today_includes_flat_lenses_list(self):
        idx = {"economic": {"lenses": [
            {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
             "status": "elevated", "headline_read": "h",
             "key_stats": [], "sparkline": []}]},
               "housing": {"lenses": [
            {"id": "housing-home-prices", "title": "Price Stability", "accent": "#b",
             "status": "ok", "headline_read": "h2",
             "key_stats": [], "sparkline": []}]}}
        today, _ = brief.build_brief(idx, {})
        self.assertEqual(len(today["lenses"]), 2)
        fiscal = next(l for l in today["lenses"] if l["lens_id"] == "fiscal-health")
        self.assertEqual(fiscal, {"lens_id": "fiscal-health", "lens_title": "Fiscal Health",
                                  "category": "economic", "href": "/dashboards/fiscal-health.html",
                                  "status": "elevated"})
        homes = next(l for l in today["lenses"] if l["lens_id"] == "housing-home-prices")
        self.assertEqual(homes["href"], "/dashboards/housing/home-prices.html")
```

In `test_refresh_brief.py`, add to `test_brief_flag_writes_today_and_state` after the existing asserts:

```python
            self.assertTrue(any(l["lens_id"] == "fiscal-health" and l["status"] == "elevated"
                                for l in today["lenses"]))
```

- [ ] **Step 2: Run, expect FAIL** (`KeyError: 'lenses'`).
- [ ] **Step 3: Implement.** In `build_brief`, add to the `today` dict after `"top_moves": moves,`:

```python
        "lenses": [{"lens_id": r["lens_id"], "lens_title": r["lens_title"],
                    "category": r["category"], "href": r["href"], "status": r["status"]}
                   for r in flat],
```

- [ ] **Step 4: Full suite → OK.**
- [ ] **Step 5: Regenerate + commit.** `python scripts/refresh_lenses.py --brief` (writes once — content changed), then commit `scripts/lenses/brief.py`, both test files, `data/brief/today.json`:
  `feat(brief): expose flat lens list in today.json`

### Task 2: export `renderHubTiles` from `hub.js`

**Files:** Modify `dashboards/hub.js`

- [ ] **Step 1:** Replace the body line of `loadHubGrid` that does `grid.innerHTML = (data.lenses || []).map(...)` with a shared function. After `function relTime(...)`, add:

```javascript
  // Shared card renderer: also used by /dashboards/brief.html.
  window.renderHubTiles = function (grid, lenses, hrefFor) {
    grid.innerHTML = (lenses || []).map(l => tile(l, hrefFor(l.id))).join("");
  };
```

and inside `loadHubGrid` use `renderHubTiles(grid, data.lenses, hrefFor);`.

- [ ] **Step 2: Commit.** `refactor(hub): export renderHubTiles for the brief page`

### Task 3: slim the landing panel (`brief.js` + CSS)

**Files:** Modify `dashboards/brief.js`, `dashboards/lens.css`, root `index.html` (strip CSS)

- [ ] **Step 1:** In `brief.js`: rename `countsLine` → `countsText` (same body); add `countsLinks`; replace `fullPanel` and `compactStrip`; delete `moveRow`:

```javascript
  function countsLinks(c) {
    const parts = [];
    for (const s of ["alert", "elevated", "watch"]) {
      if (c[s]) parts.push(`<a href="/dashboards/brief.html#${s}">${c[s]} ${s === "watch" ? "on watch" : s}</a>`);
    }
    return parts.length ? parts.join(" · ") : "All clear across the dashboards";
  }

  function fullPanel(data) {
    const trans = (data.transitions || []).map(transitionRow).join("");
    const movers = (data.top_moves || []).length
      ? `<a class="brief-link" href="/dashboards/brief.html#moves">Biggest movers &rarr;</a>` : "";
    return `
      <div class="brief-head">Today&rsquo;s Brief
        <span class="brief-counts">${countsLinks(data.status_counts || {})}</span></div>
      ${trans ? `<div class="brief-sec-label">Status changes</div>${trans}` : ""}
      <div class="brief-links">${movers}<a class="brief-link" href="/dashboards/brief.html">Full brief &rarr;</a></div>`;
  }

  function compactStrip(data) {
    const t0 = (data.transitions || [])[0];
    const lead = t0
      ? `<a class="brief-strip-lead" href="${t0.href}">${esc(t0.lens_title)}: ${esc(t0.from_status)} &rarr; ${esc(t0.to_status)}</a>`
      : "";
    return `<a class="brief-strip-counts" href="/dashboards/brief.html">${esc(countsText(data.status_counts || {}))}</a>${lead}`;
  }
```

Also expose the transition markup for the brief page (after `transitionRow`):

```javascript
  // Used by /dashboards/brief.html so transition markup lives in one place.
  window.renderBriefTransitions = transitions => (transitions || []).map(transitionRow).join("");
```

- [ ] **Step 2: lens.css.** Delete `.brief-moves`, `.brief-move`, `.brief-move:hover`, `.brief-move-title`, `.brief-move-stat`, `.brief-move-stat b`, `.brief-quiet`. Add:

```css
.brief-counts a{color:var(--muted);text-decoration:none;border-bottom:1px solid var(--border)}
.brief-counts a:hover{color:var(--text);border-bottom-color:var(--muted)}
.brief-links{display:flex;gap:1.4rem;margin-top:.85rem;flex-wrap:wrap}
.brief-link{font-size:.74rem;color:var(--blue);text-decoration:none;letter-spacing:.03em}
.brief-link:hover{text-decoration:underline}
```

- [ ] **Step 3: root `index.html` strip CSS.** `.brief-strip-counts` gains `text-decoration: none;`; add `.brief-strip-counts:hover { text-decoration: underline; }`.
- [ ] **Step 4: Commit.** `feat(brief): landing panel links into the brief page, drops move rows`

### Task 4: `dashboards/brief.html`

**Files:** Create `dashboards/brief.html`

- [ ] **Step 1:** Create the page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Today's Brief — Bailey Analytics</title>
  <meta name="description" content="What changed across the dashboards today — status changes, the biggest movers, and every lens currently on alert, elevated, or on watch.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Today's Brief — Bailey Analytics">
  <meta property="og:description" content="What changed across the dashboards today — status changes, the biggest movers, and every lens currently on alert, elevated, or on watch.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/brief.html">
  <meta name="twitter:card" content="summary">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  <style>
    .sec-head { font-size: 1.4rem; font-weight: 600; letter-spacing: -0.01em; margin: 2.25rem 0 0.3rem; scroll-margin-top: 1rem; }
    .sec-sub { color: var(--muted); font-size: .92rem; max-width: 42rem; margin-bottom: 1.15rem; }
  </style>
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>

  <main>
    <a class="back" href="/dashboards/">&larr; Dashboards</a>
    <h1>Today&rsquo;s Brief</h1>
    <p class="lede">What changed and what matters across all six dashboard categories — status changes first, then the day&rsquo;s biggest movers, then every lens that currently warrants attention. <strong>Open any card</strong> for the full charts and context.</p>
    <div class="hub-fresh" id="asof"></div>

    <section id="transitions-sec">
      <h2 class="sec-head">Status changes today</h2>
      <p class="sec-sub">Lenses whose overall status moved since the prior data — the headline events.</p>
      <div id="transitions"><div class="status-msg">Loading&hellip;</div></div>
    </section>

    <section id="moves-sec" hidden>
      <h2 class="sec-head" id="moves">Biggest movers</h2>
      <p class="sec-sub">The lenses whose lead indicator moved the most, judged against that indicator&rsquo;s own typical day-to-day swing.</p>
      <div class="hub-grid" id="moves-grid"></div>
    </section>

    <section id="alert-sec" hidden>
      <h2 class="sec-head" id="alert">On alert</h2>
      <p class="sec-sub">Readings at levels that have historically meant real stress.</p>
      <div class="hub-grid" id="alert-grid"></div>
    </section>

    <section id="elevated-sec" hidden>
      <h2 class="sec-head" id="elevated">Elevated</h2>
      <p class="sec-sub">Clearly outside comfortable ranges and worth following closely.</p>
      <div class="hub-grid" id="elevated-grid"></div>
    </section>

    <section id="watch-sec" hidden>
      <h2 class="sec-head" id="watch">On watch</h2>
      <p class="sec-sub">First warnings — not stressed yet, but moving the wrong way.</p>
      <div class="hub-grid" id="watch-grid"></div>
    </section>

    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (St. Louis Fed), the <a href="https://banks.data.fdic.gov/" target="_blank" rel="noopener">FDIC</a>, the <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a>, and <a href="https://www.coingecko.com/" target="_blank" rel="noopener">CoinGecko</a>. Public data, refreshed regularly.
    </div>
  </main>

  <script defer src="/dashboards/hub.js"></script>
  <script defer src="/dashboards/brief.js"></script>
  <script>document.addEventListener("DOMContentLoaded", async () => {
    const DIRS = ["lenses", "consumer", "banking", "markets", "energy", "housing"];
    let brief;
    try {
      const res = await fetch("/data/brief/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      brief = await res.json();
    } catch (err) {
      document.getElementById("transitions").innerHTML =
        `<div class="status-msg error">The brief is still being refreshed. Check back shortly.</div>`;
      console.error(err);
      return;
    }

    const stamp = brief.generated_at && new Date(brief.generated_at);
    if (stamp && !isNaN(stamp)) {
      document.getElementById("asof").textContent =
        "As of " + stamp.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    }

    document.getElementById("transitions").innerHTML =
      (brief.transitions || []).length
        ? renderBriefTransitions(brief.transitions)
        : `<div class="status-msg">No status changes today.</div>`;

    // Card data (sparkline, stats, headline) comes from the category indexes.
    const byId = {};
    await Promise.allSettled(DIRS.map(async dir => {
      const res = await fetch(`/data/${dir}/index.json`, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      (await res.json()).lenses.forEach(l => { byId[l.id] = l; });
    }));

    const meta = brief.lenses || [];
    const hrefById = {};
    meta.forEach(m => { hrefById[m.lens_id] = m.href; });
    const hrefFor = id => hrefById[id] || "/dashboards/";

    function fill(name, ids) {
      const lenses = ids.map(id => byId[id]).filter(Boolean);
      if (!lenses.length) return;
      document.getElementById(`${name}-sec`).hidden = false;
      renderHubTiles(document.getElementById(`${name}-grid`), lenses, hrefFor);
    }
    fill("moves", (brief.top_moves || []).map(m => m.lens_id));
    for (const s of ["alert", "elevated", "watch"])
      fill(s, meta.filter(m => m.status === s).map(m => m.lens_id));
  });</script>
</body>
</html>
```

- [ ] **Step 2: Commit.** `feat(brief): Today's Brief detail page with anchored sections`

### Task 5: economic hub + Overview link + home tile

**Files:** Create `dashboards/economic/index.html`; modify `dashboards/index.html`, root `index.html`

- [ ] **Step 1:** Create `dashboards/economic/index.html` (housing-hub clone):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Economic Lenses — Bailey Analytics</title>
  <meta name="description" content="The U.S. economy in plain English — recession risk, the cost of money, the job market, the cost of living, and the government's finances. Built from FRED data.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Economic Lenses — Bailey Analytics">
  <meta property="og:description" content="The U.S. economy in plain English — recession risk, the cost of money, the job market, the cost of living, and the government's finances. Built from FRED data.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/economic/">
  <meta name="twitter:card" content="summary">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>

  <main>
    <a class="back" href="/dashboards/">&larr; Dashboards</a>
    <h1>Economic Lenses</h1>
    <p class="lede">Where the U.S. economy actually stands — recession risk, what money costs, how the job market is holding up, what living costs are doing, and the government&rsquo;s finances. <strong>Open any lens</strong> for interactive charts and the context behind each number.</p>
    <div class="hub-grid" id="hub-grid"><div class="status-msg">Loading&hellip;</div></div>
    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a>, St. Louis Fed. Public data, refreshed daily.
    </div>
  </main>

  <script defer src="/dashboards/hub.js"></script>
  <script>document.addEventListener("DOMContentLoaded", () => {
    loadHubGrid("hub-grid", "/data/lenses/index.json",
      id => `/dashboards/${encodeURIComponent(id)}.html`);
  });</script>
</body>
</html>
```

- [ ] **Step 2:** `dashboards/index.html` — Economic cat-sub gains the Overview link (matching the other five):

```html
    <p class="cat-sub">The U.S. economy — recession risk, the cost of money, the job market, the cost of living, and the government's finances. Refreshed daily from FRED. <a href="/dashboards/economic/" style="color:var(--blue);text-decoration:none">Overview &rarr;</a></p>
```

- [ ] **Step 3:** root `index.html` — `CATEGORIES`: Economy `href: "/dashboards/economic/"`.
- [ ] **Step 4: Commit.** `feat(economic): category hub page + Overview link`

### Task 6: verification

- [ ] Full suite → OK.
- [ ] Serve + curl: `/dashboards/brief.html` contains `id="moves"`, `id="alert"`, `renderHubTiles`; `/dashboards/economic/` serves with `hub-grid`; `/dashboards/` contains `/dashboards/economic/`; `dashboards/brief.js` contains `brief.html#` and no `brief-move`; `dashboards/lens.css` has no `.brief-move`; `/data/brief/today.json` carries `lenses`.
- [ ] `git status --porcelain` clean; report (no push).

## Self-review

- **Spec coverage:** today.json `lenses` (T1), `renderHubTiles` export (T2), panel slim + strip link + dead CSS removal (T3), brief.html sections/anchors/joins/empty-states (T4), economic hub + Overview + home tile (T5), tests/curl checks (T1/T6). Covered.
- **Type consistency:** `renderHubTiles(grid, lenses, hrefFor)` and `renderBriefTransitions(transitions)` used identically in T2/T3/T4; `lenses` entry fields match T1's test (`lens_id/lens_title/category/href/status`).
- **No placeholders.**

# Revamp Phase C — Home & Hub Simplification Plan (READY — spec signed off 2026-06-12)

> **READY (spec signed off 2026-06-12: V2 tiles confirmed) — execute after Phases A and B merge.** Consumes `categories[].sentence` from the merged `data/brief/today.json` and the 4-item nav. Spec: `docs/superpowers/specs/2026-06-11-website-revamp-design.md` §3, §5, §12, Appendix A.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Single-badge V2 home tiles with category-altitude sentences; the Dashboards hub slims to 8 category cards; the hub's brief panel and `brief.js`'s now-unused `fullPanel` renderer are removed.

**Architecture:** Home keeps its per-category `index.json` fetches for sparkline/stat and adds the already-fetched `data/brief/today.json` for sentences. The hub swaps `loadHubGrid`-per-category for one new `hub.js` `loadCategoryCards` reading the same 8 `index.json`s. Category hub pages are untouched.

**Tech Stack:** Hand-written HTML/JS + lens.css. No pipeline changes (Phase A baked everything needed).

**Branch:** `revamp-phase-c` off `main` (after A and B merge).

---

### Task 1: V2 home tiles (`index.html`)

**Files:**
- Modify: `index.html` — `tile()` + `worstLens()` (~lines 379–446), tile CSS (~lines 218–241, 274–287)

- [ ] **Step 1:** In the inline script, fetch `today.json` once alongside the category indexes and build a sentence map. Replace the `(async function () { ... })()` body's fetch block:

```javascript
            // Sentences come from the merged brief JSON (authored per
            // category x status — Appendix A of the revamp spec); sparkline
            // and key stat still come from each category's index.json.
            let sentences = {};
            try {
                const t = await fetch("/data/brief/today.json", { cache: "no-cache" });
                if (t.ok) (await t.json()).categories.forEach(c => { sentences[c.category] = c.sentence; });
            } catch (e) { /* tiles degrade to stat-only */ }
```

(The `CATEGORIES` array gains a `cat` id field per entry: `{ title: "Economy", cat: "economic", url: ..., href: ... }` — add `cat` to all 8 lines.)

- [ ] **Step 2:** Replace `tile()` and drop the callout flag (single badge, category sentence, worst-lens stat retained):

```javascript
        function tile(cat, lens, status, sentence) {
            const stat = (lens.key_stats || [])[0] || { k: "", v: "—" };
            const delta = stat.d ? ` <i class="delta ${esc(stat.dir || "")}">${esc(stat.d)}</i>` : "";
            return `
                <a class="lens" href="${cat.href}">
                    <div class="eb" style="color:${lens.accent}">${esc(cat.title)}
                        <span class="pill ${esc(status)}" title="Overall category status — balanced across all lenses">${esc(status)}</span></div>
                    <div class="read">${esc(sentence || "")}</div>
                    ${sparkline(lens.sparkline, lens.accent)}
                    <div class="stat">${esc(stat.k)} <b>${esc(stat.v)}</b>${delta}</div>
                    <div class="chip-val" style="color:${lens.accent}">${esc(stat.v)}</div>
                    <div class="chip-k">${esc(stat.k)}</div>
                </a>`;
        }
```

Call site becomes `tile(cat, lens, status, sentences[cat.cat])`. `worstLens()` stays (it still picks the sparkline/stat source). Delete the `.lens .lead` CSS rule and the `flag` logic — nothing renders a second badge now.

- [ ] **Step 3:** Mobile tiles keep the story (audit C2) — in the `@media (max-width: 640px)` block, stop hiding the sentence and clamp it:

```css
            .lens .lead, .lens .spark, .lens .stat { display: none; }
            .lens .read { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
                overflow: hidden; font-size: 0.78rem; margin-top: 0.3rem; }
```

(keep the existing `.chip-val`/`.chip-k` rules; the chip stat now sits under a 2-line sentence).

- [ ] **Step 4:** Serve + screenshot home desktop/390px: every tile shows exactly one badge; sentence matches badge severity by construction; with `data/brief/today.json` absent (rename it temporarily), tiles degrade to badge + spark + stat, no errors.
- [ ] **Step 5: Commit** — `git add index.html && git commit -m "feat(home): V2 tiles — one badge + category-altitude sentence"`

---

### Task 2: `hub.js` `loadCategoryCards`

**Files:**
- Modify: `dashboards/hub.js` (new export beside `loadHubGrid`)
- Modify: `dashboards/lens.css` (category-card styles)

- [ ] **Step 1:** Append to `dashboards/lens.css`:

```css
/* --- Slim hub: category cards (Phase C) --- */
.cat-card{display:block;text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1.25rem;transition:border-color .2s ease,transform .2s ease}
.cat-card:hover,.cat-card:focus-visible{border-color:var(--blue);transform:translateY(-2px)}
.cat-card .cat-title{display:flex;align-items:center;gap:.6rem;font-weight:600;font-size:1.08rem;margin-bottom:.35rem}
.cat-card .cat-desc{color:var(--muted);font-size:.85rem;line-height:1.5;margin-bottom:.8rem}
.lens-chips{display:flex;flex-wrap:wrap;gap:.4rem}
.lens-chip{display:inline-flex;align-items:center;gap:.4rem;font-size:.72rem;color:var(--muted);background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:999px;padding:.22rem .65rem}
.lens-chip .chip-dot{width:.5rem;height:.5rem;border-radius:50%;flex:none}
.chip-dot.ok{background:var(--green)}.chip-dot.watch{background:var(--amber)}.chip-dot.elevated{background:#FB923C}.chip-dot.alert{background:var(--red)}.chip-dot.neutral{background:var(--blue)}.chip-dot.unknown{background:var(--dim)}
```

- [ ] **Step 2:** Add to `dashboards/hub.js` (reuses its existing `esc`; match its module pattern):

```javascript
  // Slim hub (Phase C): one card per category — title, blended badge,
  // description, and a status-dot chip per lens. Reads the same index.json
  // the full grids use; the card is one link to the category hub.
  window.loadCategoryCards = async function (elId, cats) {
    const el = document.getElementById(elId);
    if (!el) return;
    const results = await Promise.allSettled(cats.map(async c => {
      const res = await fetch(c.url, { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      const chips = (data.lenses || []).map(l =>
        `<span class="lens-chip"><span class="chip-dot ${esc(l.status || "unknown")}"></span>${esc(l.title)}</span>`).join("");
      const status = data.status || "unknown";
      return `<a class="cat-card" href="${esc(c.href)}">
        <div class="cat-title">${esc(c.title)} <span class="badge ${esc(status)}">${esc(status)}</span></div>
        <div class="cat-desc">${esc(c.desc)}</div>
        <div class="lens-chips">${chips}</div></a>`;
    }));
    const cards = results.filter(r => r.status === "fulfilled").map(r => r.value);
    results.forEach(r => { if (r.status === "rejected") console.error(r.reason); });
    if (cards.length) el.innerHTML = cards.join("");
  };
```

- [ ] **Step 3: Commit** — `git add dashboards/hub.js dashboards/lens.css && git commit -m "feat(hub): loadCategoryCards renderer for the slim hub"`

---

### Task 3: slim `dashboards/index.html`

**Files:**
- Modify: `dashboards/index.html` (replace the per-category `<h2>/<p>/<div class="hub-grid">` blocks, lines 33–80)

- [ ] **Step 1:** Replace everything between the `lede` and the `foot` with one grid plus the existing category descriptions moved into data (descriptions are the current `cat-sub` texts, trimmed of their "Overview →" links):

```html
    <div class="hub-grid" id="cat-cards" style="margin-top:1.5rem"><div class="status-msg"><span class="js-only">Loading&hellip;</span><noscript>The interactive dashboards require JavaScript.</noscript></div></div>
```

and the script block becomes:

```html
  <script defer src="/dashboards/hub.js"></script>
  <script>document.addEventListener("DOMContentLoaded", () => {
    loadCategoryCards("cat-cards", [
      { title: "Economic Lenses", url: "/data/lenses/index.json", href: "/dashboards/economic/",
        desc: "The U.S. economy — recession risk, the cost of money, the job market, the cost of living, and the government's finances." },
      { title: "The Consumer", url: "/data/consumer/index.json", href: "/dashboards/consumer/",
        desc: "Two-thirds of the economy — household spending, the credit behind it, income and savings, and how consumers feel." },
      { title: "Banking System Health", url: "/data/banking/index.json", href: "/dashboards/banking/",
        desc: "The health of the U.S. banking system, from FDIC Call Reports — asset quality, profitability, capital, and funding." },
      { title: "Corporate & Business Health", url: "/data/business/index.json", href: "/dashboards/business/",
        desc: "The business side of the economy — profits, new-business formation, investment, and business credit." },
      { title: "Markets & Financial Conditions", url: "/data/markets/index.json", href: "/dashboards/markets/",
        desc: "What markets are pricing — risk sentiment, the major asset classes, Fed liquidity, and crypto market structure." },
      { title: "Energy & Commodities", url: "/data/energy/index.json", href: "/dashboards/energy/",
        desc: "The physical economy — what fuel and power cost, how energy is produced, and the commodity prices that feed inflation." },
      { title: "Housing & Real Estate", url: "/data/housing/index.json", href: "/dashboards/housing/",
        desc: "The housing market — home prices and sales, affordability, construction and inventory, and rents." },
      { title: "Global Economy", url: "/data/global/index.json", href: "/dashboards/global/",
        desc: "The world beyond U.S. borders — the dollar and major currencies, global growth, trade and supply chains, and policy uncertainty." },
    ]);
  });</script>
```

Also delete the brief panel (`<section class="brief-panel" id="brief-panel">`), its `loadBrief("brief-panel", ...)` call, the `brief.js` script tag, and the now-unused `.cat-head`/`.cat-sub` inline styles — the daily read is one nav-click away; the hub's lede keeps a one-line pointer: append to the lede paragraph `For the daily read, see <a href="/dashboards/brief.html" style="color:var(--blue);text-decoration:none">Today&rsquo;s Brief</a>.`

- [ ] **Step 2:** Serve + verify: hub is ~1 screen on desktop; each card links to its category hub; chips show every lens with the right dot color; with one `index.json` renamed away the other 7 cards still render.
- [ ] **Step 3: Commit** — `git add dashboards/index.html && git commit -m "feat(hub): slim hub — 8 category cards replace the 33-card wall"`

---

### Task 4: remove the now-unused panel renderer + dead state.py fields

**Files:**
- Modify: `dashboards/brief.js` (delete `fullPanel` and `countsLinks` — the hub panel was their last consumer; home uses only `line` + `compact` strip)
- Modify: `scripts/lenses/state.py` (delete `BRIEF_HREF` + the `changed` block in `build_state`), `scripts/lenses/today.py` (nothing — it never read `changed`), `scripts/tests/test_state.py` (drop `changed` assertions)

- [ ] **Step 1:** In `brief.js`, delete `fullPanel` + `countsLinks` and the `opts.compact ? ... : fullPanel(...)` else-branch (strip becomes the non-line default); grep `loadBrief(` across `*.html` → only the home `line` and `compact` strip call sites remain.
- [ ] **Step 2:** In `state.py`, delete lines 178 (`BRIEF_HREF`) and 310–312 (the `out["changed"]` block); run `python -m unittest scripts.tests.test_state -v`, update the tests that asserted `changed`, re-run → PASS.
- [ ] **Step 3:** Full suite → PASS. **Commit** — `git add -A && git commit -m "chore(today): drop interim hub panel mode and state.py changed pointer"`

---

### Task 5: end-to-end verification

- [ ] **Step 1:** Full unittest suite → PASS.
- [ ] **Step 2:** Served walk desktop + 390px: home tiles single-badge with sentences (and 2-line clamp on mobile); hub one-screen with 8 cards; category hubs unchanged; `dashboards/economic/`→ lens → back journeys still correct from Phase B.
- [ ] **Step 3:** Update `CLAUDE.md` (home tile contract: badge + `categories[].sentence`; hub = category cards via `loadCategoryCards`; category hubs own the full lens grids) and the memory of record. **Commit.**
- [ ] **Step 4:** `/code-review`; fix findings; stop — merge/push only on Michael's go.

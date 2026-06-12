# Revamp Phase A — Brief/State Merge Implementation Plan (READY — spec signed off 2026-06-12)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge The State of Things into Today's Brief — one surface at `/dashboards/brief.html` backed by an extended `data/brief/today.json`; `state.html` becomes a redirect; the `--state` pass and `data/state/` die.

**Architecture:** Per spec §12 decision ② (Michael, 2026-06-12) the Brief is canonical, so `feed.xml`, the brief URL, and the home strip's `#alert/#elevated/#watch` anchors are all untouched. A new pure composer `lenses/today.py` calls the existing, untouched `brief.build_brief` + `state.build_state` and returns the brief JSON **extended flat** with `verdict`, `watching`, `pressure`, and `categories` (each with an Appendix A sentence). `brief.js` absorbs `state.js`'s verdict modes; `state.js` is deleted.

**Tech Stack:** stdlib Python + unittest (pipeline), hand-written HTML/JS + lens.css (site). No new dependencies.

**Branch:** `revamp-phase-a` off `main`. Run the full suite (`python -m unittest discover -s scripts/tests -p "test_*.py"` from `baileyanalytics/`) before each commit.

**Validated:** composer logic + Task 1 edits ran green in a sandbox against the full 559-test suite on 2026-06-11 (nested-shape variant; the flat shape below is the same logic minus one level of nesting). The quiet-day path, referrer behavior, and redirect mechanics were prototype-validated (spec §10).

---

### Task 1: `brief.py` carries `headline` on public lenses + movers

**Files:**
- Modify: `scripts/lenses/brief.py` (in `rank_moves` ~line 135 and `build_brief` ~line 178)
- Test: `scripts/tests/test_brief.py`

- [ ] **Step 1: Write the failing tests** — append to `scripts/tests/test_brief.py`:

```python
class HeadlineCarryThrough(unittest.TestCase):
    INDICES = {"economic": {"lenses": [{
        "id": "cost-of-living", "title": "The Cost of Living", "status": "elevated",
        "headline_read": "Inflation is still hot.",
        "key_stats": [{"k": "CPI", "v": "4.17%", "d": "0.39%", "dir": "up"}],
        "sparkline": [1.0, 1.0, 1.0, 1.0, 9.0],
    }]}}

    def test_lenses_list_carries_headline(self):
        today, _ = brief.build_brief(self.INDICES, {"statuses": {}})
        self.assertEqual(today["lenses"][0]["headline"], "Inflation is still hot.")

    def test_top_moves_carry_headline(self):
        today, _ = brief.build_brief(self.INDICES, {"statuses": {"cost-of-living": "elevated"}})
        self.assertTrue(today["top_moves"])
        self.assertEqual(today["top_moves"][0]["headline"], "Inflation is still hot.")
```

- [ ] **Step 2: Run to verify both fail** — `python -m unittest scripts.tests.test_brief -k Headline -v` → FAIL with `KeyError: 'headline'`.

- [ ] **Step 3: Implement** — two additions in `scripts/lenses/brief.py`:

In `rank_moves`, inside the `scored.append((score, {...}))` dict, after `"href": r["href"],` add:

```python
            "headline": r["headline"],
```

In `build_brief`, change the `"lenses"` comprehension to:

```python
        "lenses": [{"lens_id": r["lens_id"], "lens_title": r["lens_title"],
                    "category": r["category"], "href": r["href"], "status": r["status"],
                    "headline": r["headline"]}
                   for r in flat],
```

- [ ] **Step 4: Update the one existing test the new field breaks** (sandbox-verified as the only suite casualty): `test_brief.py` `TestBriefLensesList.test_today_includes_flat_lenses_list`, expected dict at ~line 310 — append `, "headline": "h"` before the closing brace:

```python
        self.assertEqual(fiscal, {"lens_id": "fiscal-health", "lens_title": "Fiscal Health",
                                  "category": "economic", "href": "/dashboards/fiscal-health.html",
                                  "status": "elevated", "headline": "h"})
```

- [ ] **Step 5: Run the full brief tests** — `python -m unittest scripts.tests.test_brief -v` → all PASS.

- [ ] **Step 6: Commit** — `git add scripts/lenses/brief.py scripts/tests/test_brief.py && git commit -m "feat(brief): lens records and movers carry headline_read"`

---

### Task 2: `lenses/today.py` composer + category sentence bank

**Files:**
- Create: `scripts/lenses/today.py`
- Test: `scripts/tests/test_today.py`

- [ ] **Step 1: Write the failing tests** — create `scripts/tests/test_today.py`:

```python
import unittest

from lenses import brief, today


def _lens(id_, status, headline="h", cat_title="T"):
    return {"id": id_, "title": cat_title, "status": status, "headline_read": headline,
            "key_stats": [{"k": "K", "v": "1"}], "sparkline": [1, 2, 1, 2, 1]}


INDICES = {
    "economic": {"status": "watch", "lenses": [_lens("cost-of-living", "elevated"), _lens("job-market", "ok")]},
    "consumer": {"status": "elevated", "lenses": [_lens("consumer-sentiment", "alert")]},
    "banking": {"status": "ok", "lenses": [_lens("bank-profitability", "ok")]},
    "business": {"status": "ok", "lenses": [_lens("business-credit", "watch")]},
    "markets": {"status": "watch", "lenses": [_lens("market-risk-sentiment", "watch")]},
    "energy": {"status": "elevated", "lenses": [_lens("energy-oil-fuels", "alert")]},
    "housing": {"status": "watch", "lenses": [_lens("housing-affordability", "elevated")]},
    "global": {"status": "watch", "lenses": [_lens("global-uncertainty", "elevated")]},
}


class BuildToday(unittest.TestCase):
    def setUp(self):
        self.out, self.new_state = today.build_today(INDICES, {"statuses": {}})

    def test_extends_brief_shape_flat(self):
        # the brief's existing keys survive at the top level (feed + strip
        # renderers read them unchanged) ...
        for key in ("generated_at", "transitions", "top_moves", "status_counts", "lenses"):
            self.assertIn(key, self.out)
        # ... and the absorbed state content sits beside them
        for key in ("verdict", "watching", "pressure", "categories"):
            self.assertIn(key, self.out)

    def test_pressure_rows_sorted_worst_first_with_headlines(self):
        rows = self.out["pressure"]
        self.assertTrue(rows)
        sev = {"alert": 3, "elevated": 2, "watch": 1}
        ranks = [sev[r["status"]] for r in rows]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        self.assertTrue(all(r.get("headline") for r in rows))
        self.assertTrue(all(r["status"] in sev for r in rows))

    def test_categories_carry_authored_sentences(self):
        cats = {c["category"]: c for c in self.out["categories"]}
        self.assertEqual(len(cats), 8)
        self.assertEqual(cats["banking"]["sentence"],
                         today.CATEGORY_SENTENCES["banking"]["ok"])
        self.assertEqual(cats["energy"]["sentence"],
                         today.CATEGORY_SENTENCES["energy"]["elevated"])

    def test_sentence_bank_is_complete(self):
        for cid in brief.CATEGORIES:
            for status in ("ok", "watch", "elevated", "alert"):
                self.assertIn(status, today.CATEGORY_SENTENCES[cid],
                              f"missing sentence for {cid}/{status}")

    def test_unknown_status_gets_generic_sentence(self):
        indices = dict(INDICES)
        indices["banking"] = {"status": "neutral", "lenses": [_lens("bank-profitability", "neutral")]}
        out, _ = today.build_today(indices, {"statuses": {}})
        cats = {c["category"]: c for c in out["categories"]}
        self.assertTrue(cats["banking"]["sentence"])  # generic fallback, never empty

    def test_new_state_passthrough(self):
        self.assertIn("statuses", self.new_state)
        self.assertEqual(self.new_state["statuses"]["cost-of-living"], "elevated")

    def test_watching_included_when_predictions_open(self):
        preds = [{"key": "k", "indicator": "CPI", "lens": "cost-of-living",
                  "category": "economic", "title": "CPI inflation",
                  "lens_title": "The Cost of Living", "due": "2026-06-12",
                  "point": 4.05, "unit": "%", "value_format": "decimal",
                  "implied_status": "elevated", "current_status": "elevated",
                  "href": "/dashboards/cost-of-living.html"}]
        out, _ = today.build_today(INDICES, {"statuses": {}}, open_predictions=preds)
        self.assertEqual(len(out["watching"]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python -m unittest scripts.tests.test_today -v` → FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement** — create `scripts/lenses/today.py`:

```python
"""Today's Brief, merged: the brief JSON extended with the absorbed State of
Things content (verdict + watching + flat pressure rows + category roll-up
with authored tile sentences). A thin composer over the existing pure
builders — brief.build_brief supplies change detection and the flat lens
list; state.build_state supplies the verdict, watching block, and category
records. Pure like both of them — no network, no disk I/O. Spec:
docs/superpowers/specs/2026-06-11-website-revamp-design.md (§2, §12, App. A)."""

from . import brief, state

SEVERITY = brief.SEVERITY  # ok/watch/elevated/alert ladder

# --- Tile copy bank (spec Appendix A, signed off 2026-06-12) ---
# One sentence per (category, blended status): the home tile's read, authored
# at category altitude so it can never contradict the badge it sits beside.
# elevated/alert rows reuse state.PRESSURE_CLAUSES vocabulary on purpose.
CATEGORY_SENTENCES = {
    "economic": {
        "ok": "The core economy is steady — no major warning lights.",
        "watch": "Mostly steady — a corner or two of the economy runs hot.",
        "elevated": "The core economy is under real strain.",
        "alert": "The core economy is flashing serious warnings.",
    },
    "consumer": {
        "ok": "Households are keeping pace — spending, credit, and savings look healthy.",
        "watch": "Households are keeping up, but cracks are starting to show.",
        "elevated": "Household finances are stretched thin.",
        "alert": "Households are in real distress.",
    },
    "banking": {
        "ok": "Banks are solid — capital, profits, and loan books look healthy.",
        "watch": "Banks are solid overall, but parts of the system bear watching.",
        "elevated": "Cracks are showing in the banking system.",
        "alert": "The banking system is under serious stress.",
    },
    "business": {
        "ok": "Business health is holding up — profits and investment look solid.",
        "watch": "Business health is holding up, but conditions are tightening at the margin.",
        "elevated": "Business health is deteriorating.",
        "alert": "Corporate America is in real trouble.",
    },
    "markets": {
        "ok": "Markets are calm — no stress in financial conditions.",
        "watch": "Markets are mostly calm, but a few cracks are showing.",
        "elevated": "Financial markets are under stress.",
        "alert": "Financial markets are in turmoil.",
    },
    "energy": {
        "ok": "Energy costs are behaving — no unusual pressure at the pump or on the power bill.",
        "watch": "Energy costs bear watching — some prices are drifting the wrong way.",
        "elevated": "Energy and commodity costs are squeezing budgets.",
        "alert": "Energy and commodity costs are surging.",
    },
    "housing": {
        "ok": "Housing is balanced — prices, supply, and rents read normal.",
        "watch": "Housing is mostly balanced, but parts of the market are drifting out of balance.",
        "elevated": "The housing market is out of balance.",
        "alert": "The housing market is in serious trouble.",
    },
    "global": {
        "ok": "The global backdrop is quiet — trade, growth, and currencies read calm.",
        "watch": "The global backdrop is mostly quiet, but risks are ticking up.",
        "elevated": "The global backdrop is turning hostile.",
        "alert": "The global economy is in serious stress.",
    },
}


def _sentence(cat):
    """Authored sentence for a category record; a new category or a non-severity
    status degrades to generic copy, never a crash or an empty tile."""
    authored = CATEGORY_SENTENCES.get(cat["category"], {}).get(cat["status"])
    return authored or f"{cat['title']} reads {cat['status']} right now."


def build_today(category_indices, prior_state, open_predictions=None):
    """Assemble (today_json, new_state). today_json is brief.build_brief's
    output with the absorbed state content added beside it — existing keys
    keep their shape so feed.build_item and the strip/panel renderers read
    the file unchanged. new_state is the brief's transition memory."""
    brief_today, new_state = brief.build_brief(category_indices, prior_state)
    state_today = state.build_state(category_indices, brief_today,
                                    open_predictions=open_predictions)

    pressure = [dict(r) for r in brief_today["lenses"]
                if SEVERITY.get(r["status"], 0) >= 1]
    pressure.sort(key=lambda r: (-SEVERITY[r["status"]],
                                 brief.CATEGORIES.index(r["category"])))

    today_json = dict(brief_today)
    today_json.update({
        "verdict": state_today["verdict"],
        "watching": state_today.get("watching", []),
        "pressure": pressure,
        "categories": [dict(c, sentence=_sentence(c))
                       for c in state_today["categories"]],
    })
    return today_json, new_state
```

- [ ] **Step 4: Run** — `python -m unittest scripts.tests.test_today -v` → all PASS.

- [ ] **Step 5: Commit** — `git add scripts/lenses/today.py scripts/tests/test_today.py && git commit -m "feat(brief): today.py composer — brief JSON absorbs verdict/watching/pressure/sentences"`

---

### Task 3: `refresh_lenses.py` — one `--brief` pass; `--state` retired

**Files:**
- Modify: `scripts/refresh_lenses.py` (imports line 18; `STATE_OUT_DIR` line 39; `refresh_brief` lines 641–672; `_load_brief_today` 675–682 and `refresh_state` 697–709 deleted; `main` flags/wiring 712–781)
- Create test: `scripts/tests/test_refresh_today.py`
- Modify tests: `scripts/tests/test_refresh_brief.py`, delete `scripts/tests/test_refresh_state.py` (port any uncovered case first)

- [ ] **Step 1: Write the failing test** — create `scripts/tests/test_refresh_today.py`:

```python
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import refresh_lenses  # noqa: E402


class RefreshBriefMerged(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._saved = (refresh_lenses.BRIEF_OUT_DIR, refresh_lenses.FEED_PATH)
        refresh_lenses.BRIEF_OUT_DIR = self.tmp / "brief"
        refresh_lenses.FEED_PATH = self.tmp / "feed.xml"
        refresh_lenses.BRIEF_OUT_DIR.mkdir(parents=True)

    def tearDown(self):
        refresh_lenses.BRIEF_OUT_DIR, refresh_lenses.FEED_PATH = self._saved

    def test_dry_run_writes_merged_today_json(self):
        refresh_lenses.refresh_brief(dry_run=True)
        today = json.loads((refresh_lenses.BRIEF_OUT_DIR / "today.json").read_text(encoding="utf-8"))
        for key in ("transitions", "top_moves", "status_counts", "lenses",
                    "verdict", "pressure", "categories"):
            self.assertIn(key, today)
        self.assertTrue((refresh_lenses.BRIEF_OUT_DIR / "_prior_state.json").exists())
        self.assertTrue(refresh_lenses.FEED_PATH.exists())

    def test_state_pass_is_gone(self):
        self.assertFalse(hasattr(refresh_lenses, "refresh_state"))
        self.assertFalse(hasattr(refresh_lenses, "STATE_OUT_DIR"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** — `python -m unittest scripts.tests.test_refresh_today -v` → FAIL (`verdict` missing; `refresh_state` still present).

- [ ] **Step 3: Implement** in `scripts/refresh_lenses.py`:
  - Line 18: add `today` to the `from lenses import ...` list (keep `state` — `today.py` imports it; `refresh_lenses` itself no longer calls it directly, so drop it from this import only if unused after the edits — check with a grep).
  - Delete line 39 (`STATE_OUT_DIR = ...`).
  - In `refresh_brief` (line 647), replace the build call:

```python
        today_json, new_state = today.build_today(
            indices, _load_prior_state(),
            open_predictions=_load_open_predictions())
```

  and rename the local `today` variable collisions accordingly: the subsequent writes become `build.write_lens_file(BRIEF_OUT_DIR / "today.json", today_json)` and `feed.build_item(today_json)`. (The variable was previously named `today`; it must be renamed `today_json` to not shadow the module.)
  - Delete `_load_brief_today` (lines 675–682) and `refresh_state` (lines 697–709). Keep `_load_open_predictions` — it moved callers from `refresh_state` to `refresh_brief`.
  - In `main()`: replace the `--state` definition (lines 726–727) with a deprecated alias:

```python
    parser.add_argument("--state", action="store_true", help=argparse.SUPPRESS)
```

  keep `--brief` as-is; in the wiring replace `do_brief`/`do_state` with:

```python
    if args.state:
        print("WARN: --state is deprecated; the brief pass now includes the verdict.",
              file=sys.stderr)
    do_brief = args.brief or args.state or not any_flag
```

  and delete the trailing `if do_state: refresh_state(args.dry_run)` block.

- [ ] **Step 4: Run** — `python -m unittest scripts.tests.test_refresh_today -v` → PASS. Update `test_refresh_brief.py` for the merged shape (its assertions on `today.json` keys gain the new ones only if it asserts exact key sets — check), port any unique case from `test_refresh_state.py`, then delete it. Full suite → PASS.

- [ ] **Step 5: Remove the dead baked file** — `git rm data/state/today.json` (the `data/state/` dir goes with it; keep all of `data/brief/`).

- [ ] **Step 6: Commit** — `git add -A scripts/refresh_lenses.py scripts/tests/ && git commit -m "feat(brief): --brief builds the merged surface; --state retired to alias"`

---

### Task 4: `brief.js` absorbs the verdict modes; `state.js` deleted

**Files:**
- Modify: `dashboards/brief.js`, `dashboards/lens.css`
- Delete (Task 6, after consumers re-point): `dashboards/state.js`

- [ ] **Step 1:** In `dashboards/brief.js`, add a verdict renderer and a `line` mode, and put the verdict atop the hub panel. After the `countsLinks` function add:

```javascript
  function verdictHtml(v, badgeClass) {
    return `<span class="${badgeClass} ${esc(v.status)}">${esc(v.status)}</span>
      <span class="state-sentence">${esc(v.sentence)}</span>`;
  }
```

Replace `fullPanel`'s return with (verdict line added, link text updated):

```javascript
    return `
      <div class="state-verdict">${verdictHtml(data.verdict, "badge")}
        <a class="state-link" href="/dashboards/brief.html">The full picture &rarr;</a></div>
      <div class="brief-head">Today&rsquo;s Brief
        <span class="brief-counts">${countsLinks(data.status_counts || {})}</span></div>
      ${trans ? `<div class="brief-sec-label">Status changes</div>${trans}` : ""}
      <div class="brief-links">${movers}<a class="brief-link" href="/dashboards/brief.html">Full brief &rarr;</a></div>`;
```

In `window.loadBrief`, support the home hero's one-liner — replace the `el.innerHTML = opts.compact ? ... : ...;` line with:

```javascript
      if (opts.mode === "line") {
        if (!data.verdict || !data.verdict.sentence) throw new Error("no verdict");
        el.innerHTML = verdictHtml(data.verdict, "pill");
      } else {
        el.innerHTML = opts.compact ? compactStrip(data) : fullPanel(data);
      }
```

(`fullPanel` may render before the verdict exists in a stale cached JSON — guard inside `fullPanel`: `const v = data.verdict; const verdictRow = v && v.sentence ? \`<div class="state-verdict">...\` : "";` and interpolate `${verdictRow}` instead of the unconditional div.)

- [ ] **Step 2:** Append the pressure-row styles to `dashboards/lens.css` after the `.state-steady` block:

```css
/* --- Brief: compact pressure rows (replaces the card walls) --- */
.att-row{display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;padding:.42rem .5rem;border-radius:9px;color:var(--text);text-decoration:none}
.att-row:hover{background:rgba(255,255,255,.03)}
.att-row .brief-cat{flex:none;width:4.6rem}
.att-row .att-title{font-weight:600;font-size:.88rem;flex:none}
.att-row .att-read{color:var(--muted);font-size:.82rem;flex:1 1 16rem;min-width:0}
.att-group{margin-bottom:.9rem}
@media(max-width:640px){.att-row .att-read{flex-basis:100%}}
```

- [ ] **Step 3: Commit** — `git add dashboards/brief.js dashboards/lens.css && git commit -m "feat(brief): brief.js gains verdict line/panel modes + pressure-row styles"`

---

### Task 5: merged `brief.html`; `state.html` becomes a redirect

**Files:**
- Modify: `dashboards/brief.html` (lede, sections, inline script)
- Overwrite: `dashboards/state.html` (redirect stub)

- [ ] **Step 1:** Rework `dashboards/brief.html` `<main>` to the verdict-led A1 structure (title and og tags unchanged — the page keeps its name and URL). Replace the lede and everything from `<section id="transitions-sec">` through the last section with:

```html
    <h1>Today&rsquo;s Brief</h1>
    <p class="lede">The daily read on the U.S. and global economy — where things stand, what changed, and what we&rsquo;re watching next. <strong>Open anything</strong> for the full charts and context.</p>
    <div class="hub-fresh" id="asof"></div>

    <section class="state-panel" id="verdict" style="margin-top:1.25rem"><div class="status-msg"><span class="js-only">Loading&hellip;</span><noscript>The interactive dashboards require JavaScript.</noscript></div></section>

    <section id="transitions-sec">
      <h2 class="sec-head">What changed today</h2>
      <p class="sec-sub">Status changes first — the headline events — then the biggest moves in the data, judged against each indicator&rsquo;s own typical day-to-day swing.</p>
      <div id="transitions"></div>
    </section>

    <section id="moves-sec" hidden>
      <div class="brief-sec-label" id="moves">Biggest movers</div>
      <div class="hub-grid" id="moves-grid" style="margin-top:.5rem"></div>
    </section>

    <section id="watching-sec" hidden>
      <h2 class="sec-head">What we&rsquo;re watching next</h2>
      <p class="sec-sub">Our published predictions for the most consequential upcoming prints — each graded in public when the number lands.</p>
      <div id="watching"></div>
    </section>

    <section id="pressure-sec" hidden>
      <h2 class="sec-head">Where the pressure is</h2>
      <p class="sec-sub">Everything currently warranting attention, worst first.</p>
      <div id="pressure"></div>
    </section>

    <section>
      <h2 class="sec-head">Across the dashboards</h2>
      <p class="sec-sub">Every category&rsquo;s overall read — jump into any of them.</p>
      <div id="cats"></div>
    </section>
```

(keep the existing back link, `.foot` with the RSS link, and the `<meta>` head as they are).

- [ ] **Step 2:** Replace the page's inline `<script>` (lines 71–131) — the old one re-fetched all 8 `index.json`s to decorate cards; the merged JSON now carries everything:

```html
  <script defer src="/dashboards/brief.js"></script>
  <script>document.addEventListener("DOMContentLoaded", async () => {
    const esc = s => { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; };
    let data;
    try {
      const res = await fetch("/data/brief/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      data = await res.json();
    } catch (err) {
      document.getElementById("verdict").innerHTML =
        `<div class="status-msg error">The brief is still being refreshed. Check back shortly.</div>`;
      console.error(err);
      return;
    }

    const stamp = data.generated_at && new Date(data.generated_at);
    if (stamp && !isNaN(stamp)) {
      document.getElementById("asof").textContent =
        "As of " + stamp.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
    }

    if (data.verdict && data.verdict.sentence) {
      document.getElementById("verdict").innerHTML = `<div class="state-verdict">
        <span class="badge ${esc(data.verdict.status)}">${esc(data.verdict.status)}</span>
        <span class="state-sentence" style="font-size:1.15rem">${esc(data.verdict.sentence)}</span></div>`;
    }

    document.getElementById("transitions").innerHTML =
      (data.transitions || []).length
        ? renderBriefTransitions(data.transitions)
        : `<div class="status-msg" style="text-align:left;padding:.4rem 0">No status changes today — a quiet day on the board.</div>`;

    const CAT = window.briefCategoryLabel;
    const moves = data.top_moves || [];
    if (moves.length) {
      document.getElementById("moves-sec").hidden = false;
      document.getElementById("moves-grid").innerHTML = moves.map(m => {
        const delta = m.delta ? ` <i class="delta ${esc(m.dir || "")}">${esc(m.delta)}</i>` : "";
        return `<a class="hub-card" href="${esc(m.href)}">
          <div class="hub-eyebrow"><span class="hub-cat">${esc(CAT(m.category))} ·</span> ${esc(m.lens_title)}</div>
          <div class="hub-read">${esc(m.headline || "")}</div>
          <div class="hub-stats">${esc(m.stat_label)} <b>${esc(m.stat_value)}</b>${delta}</div></a>`;
      }).join("");
    }

    if ((data.watching || []).length) {
      document.getElementById("watching-sec").hidden = false;
      document.getElementById("watching").innerHTML = data.watching.map(x => {
        const claim = x.change
          ? `we expect <strong>${esc(x.point_fmt)}</strong> — which would tip ${esc(x.lens_title)} to <span class="badge ${esc(x.implied_status)}">${esc(x.implied_status)}</span>`
          : `we expect <strong>${esc(x.point_fmt)}</strong>, no status change`;
        return `<a class="state-lens" href="${esc(x.href)}">
          <span class="state-lens-title">${esc(x.title)}</span>
          <span class="state-lens-read">${claim}</span></a>`;
      }).join("") + `<a class="state-link" href="/dashboards/track-record.html">Our track record &rarr;</a>`;
    }

    const GROUPS = [
      ["alert", "On alert — levels that have historically meant real stress"],
      ["elevated", "Elevated — clearly outside comfortable ranges"],
      ["watch", "On watch — first warnings"],
    ];
    const rows = data.pressure || [];
    if (rows.length) {
      document.getElementById("pressure-sec").hidden = false;
      document.getElementById("pressure").innerHTML = GROUPS.map(([s, label]) => {
        const group = rows.filter(p => p.status === s);
        if (!group.length) return "";
        return `<div class="att-group" id="${s}">
          <div class="brief-sec-label">${esc(label)}</div>` +
          group.map(p => `<a class="att-row" href="${esc(p.href)}">
            <span class="brief-cat">${esc(CAT(p.category))}</span>
            <span class="att-title">${esc(p.lens_title)}</span>
            <span class="badge ${esc(p.status)}">${esc(p.status)}</span>
            <span class="att-read">${esc(p.headline)}</span></a>`).join("") + `</div>`;
      }).join("");
    }

    document.getElementById("cats").innerHTML = (data.categories || []).map(c =>
      `<a class="state-steady" href="${esc(c.href)}">
        <span class="badge ${esc(c.status)}">${esc(c.status)}</span>${esc(c.title)}</a>`).join("");

    // Fragment deep links (#alert etc.) target sections that were hidden at
    // browser scroll time — re-run once visible.
    if (location.hash) {
      const target = document.getElementById(location.hash.slice(1));
      if (target && !target.closest("[hidden]")) target.scrollIntoView();
    }
  });</script>
```

(drop the `hub.js` script tag — `renderHubTiles` is no longer used here; `renderBriefTransitions` and `briefCategoryLabel` come from `brief.js` as before).

- [ ] **Step 3:** Overwrite `dashboards/state.html` with a redirect stub (exact `dashboards/economic.html` pattern):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The State of Things — Bailey Analytics</title>
  <link rel="canonical" href="https://baileyanalytics.com/dashboards/brief.html">
  <meta http-equiv="refresh" content="0; url=/dashboards/brief.html">
  <meta name="robots" content="noindex">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <style>
    body { background:#0A0E14; color:#94A3B8; margin:0; padding:1.5rem; min-height:100vh;
      display:flex; align-items:center; justify-content:center; text-align:center;
      font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif; }
    a { color:#38BDF8; }
  </style>
</head>
<body>
  <p>The State of Things is now part of <a href="/dashboards/brief.html">Today&rsquo;s Brief</a>. Redirecting&hellip;</p>
</body>
</html>
```

- [ ] **Step 4: Commit** — `git add dashboards/brief.html dashboards/state.html && git commit -m "feat(brief): merged verdict-led brief page; state.html redirects"`

---

### Task 6: re-point consumers; delete `state.js`

**Files:**
- Modify: `index.html` (lines 325, 346–347, 409–414), `dashboards/index.html` (lines 33–35, 75–79), `dashboards/track-record.html` (line 26)
- Delete: `dashboards/state.js`

- [ ] **Step 1: Home `index.html`:**
  - Line 325: `href="/dashboards/state.html"` → `href="/dashboards/brief.html"`.
  - Line 347: delete the `state.js` script tag (brief.js stays).
  - Lines 409–414: the hero one-liner now rides `loadBrief` — replace the `showState` block with:

```javascript
            // The hero verdict line is independent of the tiles — show it first
            // (brief.js loads deferred; this inline script can win the race).
            const showLine = () => { if (typeof loadBrief === "function") loadBrief("state-line", { mode: "line" }); };
            if (typeof loadBrief === "function") showLine();
            else window.addEventListener("DOMContentLoaded", showLine);
```

  (the existing brief-strip call at lines 441–445 is already `loadBrief("brief-strip", { compact: true })` — unchanged.)

- [ ] **Step 2: Hub `dashboards/index.html`:** delete the `state-panel` section (line 33) and the `state.js` script tag (line 75); delete the `loadState("state-panel", { mode: "panel" });` call (line 78) — the brief panel (which now opens with the verdict, Task 4) is the hub's single synthesis panel.

- [ ] **Step 3: `dashboards/track-record.html` line 26:** `<a class="back" href="/dashboards/state.html">&larr; The State of Things</a>` → `<a class="back" href="/dashboards/brief.html">&larr; Today&rsquo;s Brief</a>`.

- [ ] **Step 4:** `git rm dashboards/state.js`, then verify: `grep -rn "state\.js\|loadState\|state\.html" index.html dashboards/*.html dashboards/*.js` → only the `state.html` redirect stub itself.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat(brief): re-point home/hub/track-record; remove state.js"`

---

### Task 7: workflow + docs

**Files:**
- Modify: `.github/workflows/refresh-fred.yml` (lines 84–90), `CLAUDE.md`

- [ ] **Step 1:** In `refresh-fred.yml`, delete the "Rebuild The State of Things" step (lines 88–90) and rename the brief step:

```yaml
      - name: Rebuild Today's Brief (no network)
        if: ${{ success() || failure() }}
        run: python scripts/refresh_lenses.py --brief
```

- [ ] **Step 2:** Update `CLAUDE.md`: the `--brief`/`--state` description becomes "`--brief` (the merged Today's Brief: `today.py` composes `brief.py` + `state.py` → `data/brief/today.json` + `/feed.xml`; `--state` is a deprecated alias; `dashboards/state.html` is a redirect)"; update the State of Things sentence to say its verdict/pressure/watching content now renders on `brief.html` and the hub panel/home hero via `brief.js`.

- [ ] **Step 3: Commit** — `git add .github/workflows/refresh-fred.yml CLAUDE.md && git commit -m "chore(brief): drop --state workflow step; document the merge"`

---

### Task 8: end-to-end verification

- [ ] **Step 1: Full suite** — `python -m unittest discover -s scripts/tests -p "test_*.py"` → all PASS.
- [ ] **Step 2: Offline build** — `python scripts/refresh_lenses.py --dry-run --brief` → `data/brief/today.json` gains `verdict`/`pressure`/`categories`. **Restore afterward: `git checkout -- data/`** (a dry run overwrites `data/`).
- [ ] **Step 3: Build live** (`FRED_API_KEY` not needed — `--brief` is a no-network synthesis pass over checked-in indexes): `python scripts/refresh_lenses.py --brief`, then serve and walk: `/dashboards/brief.html` renders verdict-led with all sections; `/dashboards/state.html` bounces to it; home hero verdict shows and links to the brief; home counts strip deep-links land on the pressure groups; hub shows one panel opening with the verdict; `/feed.xml` unchanged in structure (`git diff feed.xml` shows at most a content refresh, no link changes); zero console errors (predictions 404s excepted until that data exists).
- [ ] **Step 4:** `/code-review` per the delivery workflow; fix findings; stop — **merge/push only on Michael's go**.

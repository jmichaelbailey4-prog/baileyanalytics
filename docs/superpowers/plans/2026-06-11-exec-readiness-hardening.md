# Exec-Readiness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every P2/recommendation item from the 2026-06-11 executive-readiness review: payload size, slug-map duplication, stale-data signaling, no-JS fallbacks, home "as of" stamp, an RSS push channel for Today's Brief, and a rate-expectations indicator on Cost of Money.

**Architecture:** All changes follow existing patterns — pure helpers in `scripts/lenses/util.py`, computed-series injection mirroring `_inject_business_shares`, shared client rendering in `dashboards/hub.js`. New baked artifacts (`feed.xml`, the spread indicator) are produced offline from existing data so the live site updates on deploy; the pipeline regenerates them identically on its next run.

**Tech Stack:** stdlib Python 3 + unittest (TDD), vanilla JS, static HTML. No new dependencies.

**Out of scope (blocked/deferred):** Geopolitical-risk source beyond EPU (GPR xlsx verified unusable 2026-06 — see data-source-verification memory); email delivery (RSS-to-email services can consume `feed.xml` later).

**Modeling note:** Thinning published JSON does not lose history for the future predictive-models phase — FRED/EIA/FDIC retain full history and can be re-fetched at training time; the only accumulating store, `data/markets/_crypto_history.json`, is explicitly never thinned.

---

## File Structure

- `scripts/lenses/util.py` — tiered `thin_observations` (monthly tier past 5y); new `spread_ffill`
- `scripts/lenses/feed.py` — **new**: RSS item building + XML rendering (pure, no I/O)
- `scripts/lenses/narrative.py` — `rule_rate_expectations` (info-status read)
- `scripts/lenses/config.py` — 4th Cost of Money indicator (computed spread)
- `scripts/lenses/brief.py` — `lens_href` collapsed to prefix rule + one override
- `scripts/refresh_lenses.py` — `_inject_rate_expectations` in `refresh_economic`; feed writing in `refresh_brief`
- `dashboards/hub.js` — `window.lensHref`; stale-data flag in `loadHubGrid`
- `dashboards/lens.css` — `.hub-fresh.stale`, `.asof` styles
- `dashboards/index.html` + 8 category hub pages — use `lensHref`, drop local SLUG maps
- `index.html` (home) — hero "as of" stamp; RSS `<link>`
- All HTML pages with `Loading…` placeholders — noscript fallback
- `scripts/tests/test_util.py`, `test_feed.py` (new), `test_narrative.py`, `test_brief.py`, `test_config_*` — coverage
- One-shot offline bake scripts (run then delete): re-thin `data/`, bake spread into `data/lenses/cost-of-money.json`, bake `feed.xml`

---

### Task 1: Tiered thinning in `util.thin_observations`

**Files:** Modify `scripts/lenses/util.py:8-33`, `scripts/tests/test_util.py`

- [ ] **Step 1: Update/add failing tests** in `TestThinObservations`:

```python
    def test_mid_window_daily_points_thinned_to_weekly(self):
        # daily points 2-5 years back thin to one per ISO week
        old = [{"date": f"2024-03-{d:02d}", "value": str(d)} for d in range(4, 18)]  # 14 days
        recent = [{"date": "2026-05-01", "value": "x"}]
        out = util.thin_observations(old + recent, keep_years=2)
        kept = [o["date"] for o in out if o["date"].startswith("2024")]
        # Mar 4 2024 is a Monday: 14 days cover ISO weeks 10 and 11 -> 2 survivors
        self.assertEqual(kept, ["2024-03-04", "2024-03-11"])

    def test_old_daily_points_thinned_to_monthly(self):
        # daily points >5 years back thin to one per calendar month
        old = [{"date": f"2020-03-{d:02d}", "value": str(d)} for d in range(2, 16)]
        recent = [{"date": "2026-05-01", "value": "x"}]
        out = util.thin_observations(old + recent, keep_years=2)
        kept = [o["date"] for o in out if o["date"].startswith("2020")]
        self.assertEqual(kept, ["2020-03-02"])
```

Also update the existing `test_old_daily_points_thinned_to_weekly` (2020 dates are now >5y back): rename it to match the monthly behavior or change its dates to 2024.

- [ ] **Step 2: Run** `python -m unittest scripts.tests.test_util` style discover — expect the new tests FAIL.

- [ ] **Step 3: Implement** tiered thinning:

```python
def thin_observations(raw_observations, keep_years=2, monthly_after_years=5):
    """Shrink a published series: full resolution in the trailing `keep_years`,
    one point per ISO week out to `monthly_after_years`, one point per calendar
    month beyond that. Monthly-or-slower cadences pass through unchanged.
    NOTE: this only thins the *published* JSON — sources retain full history,
    so nothing is lost for future modeling work."""
    if not raw_observations:
        return raw_observations
    last = raw_observations[-1]["date"]
    weekly_boundary = f"{int(last[:4]) - keep_years}{last[4:]}"
    monthly_boundary = f"{int(last[:4]) - monthly_after_years}{last[4:]}"
    out, seen_weeks, seen_months = [], set(), set()
    for obs in raw_observations:
        if obs["date"] >= weekly_boundary:
            out.append(obs)
            continue
        parts = obs["date"].split("-")
        if len(parts) < 3:  # EIA monthly periods are "YYYY-MM" — monthly never thins
            out.append(obs)
            continue
        if obs["date"] < monthly_boundary:
            month = (parts[0], parts[1])
            if month not in seen_months:
                seen_months.add(month)
                out.append(obs)
            continue
        week = date(int(parts[0]), int(parts[1]), int(parts[2])).isocalendar()[:2]
        if week not in seen_weeks:
            seen_weeks.add(week)
            out.append(obs)
    return out
```

- [ ] **Step 4: Run full suite** — expect PASS (427+ tests).
- [ ] **Step 5: Offline re-thin baked data** — one-shot script over every `data/<cat>/<lens>.json` (skip `index.json`, `_*.json`, `brief/`): load, apply `util.thin_observations` to each `indicators[].observations`, write back with `json.dumps(doc, indent=2) + "\n"`. Record before/after sizes. Delete script.
- [ ] **Step 6: Commit** `perf(data): tier old observations to monthly past 5y (halves big lens payloads)`

### Task 2: Slug-map consolidation

**Files:** Modify `dashboards/hub.js`, `scripts/lenses/brief.py:35-92`, `dashboards/index.html`, all 8 `dashboards/<cat>/index.html`

- [ ] **Step 1: Python first (tests exist).** Replace the six `_*_SLUGS` dicts + `lens_href` chain in `brief.py` with:

```python
# Page-slug rule: lens ids are "<prefix>-<slug>"; strip the category prefix.
# Two irregulars: banking ids use "bank-", markets ids use "market-" (and
# crypto-structure has no prefix — the strip is a no-op). One true override.
_SLUG_OVERRIDES = {"consumer-credit": "credit-stress"}
_ID_PREFIXES = {"banking": "bank-", "markets": "market-"}


def lens_href(category, lens_id):
    """Public page path for a lens. Mirrors dashboards/hub.js lensHref — keep in sync."""
    if category == "economic":
        return f"/dashboards/{lens_id}.html"
    if category not in CATEGORIES:
        return "/dashboards/"
    prefix = _ID_PREFIXES.get(category, category + "-")
    slug = _SLUG_OVERRIDES.get(lens_id) or (
        lens_id[len(prefix):] if lens_id.startswith(prefix) else lens_id)
    return f"/dashboards/{category}/{slug}.html"
```

(Move `CATEGORIES` above `lens_href`.)

- [ ] **Step 2: Run** `test_brief.py` — all existing href assertions must PASS unchanged.
- [ ] **Step 3: JS mirror** in `hub.js` (before `loadHubGrid`):

```js
  // Public page path for a lens id. Mirrors brief.py lens_href — keep in sync.
  window.lensHref = function (category, id) {
    if (category === "economic") return `/dashboards/${encodeURIComponent(id)}.html`;
    const overrides = { "consumer-credit": "credit-stress" };
    const prefixes = { banking: "bank-", markets: "market-" };
    const pre = prefixes[category] || category + "-";
    const slug = overrides[id] || (id.indexOf(pre) === 0 ? id.slice(pre.length) : id);
    return `/dashboards/${encodeURIComponent(category)}/${encodeURIComponent(slug)}.html`;
  };
```

- [ ] **Step 4: Replace callers.** `dashboards/index.html`: drop the four `*_SLUGS` consts; every call becomes e.g. `loadHubGrid("consumer-grid", "/data/consumer/index.json", id => lensHref("consumer", id), "consumer-badge")`. Each category hub page: drop its local `SLUGS`, call `id => lensHref("<category>", id)`.
- [ ] **Step 5: Verify** with `node --check` on hub.js + every inline block; confirm generated hrefs unchanged by spot-comparing against `data/brief/today.json` hrefs.
- [ ] **Step 6: Commit** `refactor: single lensHref slug rule (was 3 duplicated maps)`

### Task 3: Stale-data flag

**Files:** Modify `dashboards/hub.js`, `dashboards/lens.css`, `dashboards/index.html`, `dashboards/banking/index.html`

- [ ] **Step 1:** In `loadHubGrid`, accept an options object or legacy string as 4th param; flag staleness:

```js
  window.loadHubGrid = async function (gridId, url, hrefFor, opts) {
    if (typeof opts === "string") opts = { badgeId: opts };
    opts = opts || {};
    const staleDays = opts.staleDays || 10;
    // ... existing fetch/render/badge code (badgeId -> opts.badgeId) ...
    const ageH = data.last_updated && (Date.now() - new Date(data.last_updated).getTime()) / 3.6e6;
    const ago = data.last_updated && relTime(data.last_updated);
    if (ago) {
      const stale = ageH > staleDays * 24;
      grid.insertAdjacentHTML("afterend",
        `<div class="hub-fresh${stale ? " stale" : ""}">Data last changed ${esc(ago)}${stale ? " — the refresh may be delayed" : ""}</div>`);
    }
```

- [ ] **Step 2:** CSS: `.hub-fresh.stale{color:var(--amber)}`. Banking (legitimately slow, quarterly source): pass `{ badgeId: ..., staleDays: 120 }` on `dashboards/banking/index.html` and the bank-grid call in `dashboards/index.html`.
- [ ] **Step 3:** `node --check`, visual sanity via local server. Commit `feat: amber stale-data flag when a category stops refreshing`

### Task 4: No-JS fallbacks

**Files:** Every HTML page containing a `Loading…`/`Loading&hellip;` placeholder (lens pages, hub pages, brief).

- [ ] **Step 1:** Scripted replace of each placeholder div with:

```html
<div class="status-msg"><span class="js-only">Loading&hellip;</span><noscript>The interactive dashboards require JavaScript.</noscript></div>
```

(For lens pages the literal is `Loading…` — handle both spellings.) The `js-only` span needs one global rule — but it must only hide when JS is OFF, so it lives inside noscript: prepend `<noscript><style>.js-only{display:none}</style></noscript>` immediately after each page's `<body>` open tag (idempotent, page-local, no JS-on cost).

- [ ] **Step 2:** Verify by grepping that no page retains a bare `Loading` placeholder without noscript sibling. Commit `feat: noscript fallback on all data-driven pages`

### Task 5: Home hero "as of" stamp

**Files:** Modify `index.html` (home)

- [ ] **Step 1:** Add under the tagline: `<div class="asof" id="hero-asof" hidden></div>` with CSS `.asof{font-size:.75rem;color:var(--faint);margin-top:.9rem;letter-spacing:.04em}`.
- [ ] **Step 2:** In the loader, each settled result currently returns tile HTML; return `{ html, updated: data.last_updated }`, then:

```js
const newest = results.filter(r => r.status === "fulfilled").map(r => r.value.updated)
  .filter(Boolean).sort().pop();
if (newest) {
  const el = document.getElementById("hero-asof");
  el.textContent = "Live data — updated " + new Date(newest).toLocaleDateString(undefined,
    { year: "numeric", month: "long", day: "numeric" });
  el.hidden = false;
}
```

- [ ] **Step 3:** `node --check` inline block; commit `feat(home): live "as of" stamp on the hero`

### Task 6: RSS feed for Today's Brief

**Files:** Create `scripts/lenses/feed.py`, `scripts/tests/test_feed.py`; modify `scripts/refresh_lenses.py` (`refresh_brief`); add `<link rel="alternate">` to `index.html`, `dashboards/index.html`, `dashboards/brief.html`; bake `feed.xml` + `data/brief/_feed_items.json` offline.

- [ ] **Step 1: Failing tests** (`test_feed.py`):

```python
import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import feed

TODAY = {
    "generated_at": "2026-06-11T02:07:53Z",
    "transitions": [{"lens_title": "Consumer Credit Stress", "category": "consumer",
                     "from_status": "watch", "to_status": "elevated",
                     "href": "/dashboards/consumer/credit-stress.html",
                     "headline": "Delinquencies are climbing."}],
    "top_moves": [{"lens_title": "Oil & Fuels", "category": "energy",
                   "href": "/dashboards/energy/oil-fuels.html",
                   "stat_label": "Gasoline", "stat_value": "$4.15", "delta": "$0.16", "dir": "down"}],
    "status_counts": {"ok": 17, "watch": 3, "elevated": 8, "alert": 3, "neutral": 2},
}

class TestBuildItem(unittest.TestCase):
    def test_item_carries_date_title_and_counts(self):
        item = feed.build_item(TODAY)
        self.assertEqual(item["date"], "2026-06-11")
        self.assertIn("3 alert", item["title"])
        self.assertIn("Consumer Credit Stress", item["description"])
        self.assertIn("watch → elevated", item["description"])
        self.assertIn("Oil & Fuels", item["description"])

    def test_quiet_day_title(self):
        quiet = dict(TODAY, transitions=[], top_moves=[],
                     status_counts={"ok": 33, "watch": 0, "elevated": 0, "alert": 0})
        item = feed.build_item(quiet)
        self.assertIn("All clear", item["title"])

class TestRenderFeed(unittest.TestCase):
    def test_renders_valid_escaped_rss(self):
        xml = feed.render_feed([feed.build_item(TODAY)])
        self.assertTrue(xml.startswith("<?xml"))
        self.assertIn("<rss", xml)
        self.assertIn("https://baileyanalytics.com/dashboards/brief.html", xml)
        self.assertNotIn("&'", xml)  # escaping happened
        import xml.dom.minidom
        xml.dom.minidom.parseString(xml)  # well-formed

    def test_items_capped_and_newest_first(self):
        items = [{"date": f"2026-06-{d:02d}", "title": "t", "description": "d"} for d in range(1, 10)]
        merged = feed.merge_items(items[:-1], items[-1], cap=5)
        self.assertEqual(len(merged), 5)
        self.assertEqual(merged[0]["date"], "2026-06-09")

    def test_merge_replaces_same_day(self):
        old = [{"date": "2026-06-11", "title": "old", "description": "d"}]
        merged = feed.merge_items(old, {"date": "2026-06-11", "title": "new", "description": "d"})
        self.assertEqual([i["title"] for i in merged], ["new"])
```

- [ ] **Step 2: Run — FAIL** (no module `feed`).
- [ ] **Step 3: Implement `feed.py`** (pure; no I/O):

```python
"""RSS feed for Today's Brief. Pure: build_item/merge_items/render_feed take and
return data; refresh_lenses owns disk I/O. One item per day, newest first."""

from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape

SITE = "https://baileyanalytics.com"
BRIEF_URL = f"{SITE}/dashboards/brief.html"


def _counts_phrase(c):
    parts = []
    for s, label in (("alert", "alert"), ("elevated", "elevated"), ("watch", "on watch")):
        if c.get(s):
            parts.append(f"{c[s]} {label}")
    return " · ".join(parts) if parts else "All clear across the dashboards"


def build_item(today):
    """One feed item summarizing a day's brief."""
    day = (today.get("generated_at") or "")[:10]
    title = f"Today's Brief — {_counts_phrase(today.get('status_counts', {}))}"
    lines = []
    for t in today.get("transitions", []):
        lines.append(f"{t['lens_title']}: {t['from_status']} → {t['to_status']} — {t['headline']}")
    for m in today.get("top_moves", []):
        arrow = "▼" if m.get("dir") == "down" else "▲"
        lines.append(f"{m['lens_title']}: {m['stat_label']} {m['stat_value']} ({arrow}{m['delta']})")
    if not lines:
        lines.append("No status changes or outsized moves today.")
    return {"date": day, "title": title, "description": "\n".join(lines)}


def merge_items(existing, new_item, cap=30):
    """Prepend new_item, replacing any same-day item; keep the newest `cap`."""
    items = [i for i in (existing or []) if i.get("date") != new_item["date"]]
    items.insert(0, new_item)
    items.sort(key=lambda i: i["date"], reverse=True)
    return items[:cap]


def render_feed(items):
    """Render RSS 2.0 XML. Item pubDates are midnight UTC of the brief date."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0"><channel>',
           "<title>Bailey Analytics — Today's Brief</title>".replace("'", "&#39;"),
           f"<link>{BRIEF_URL}</link>",
           "<description>Daily plain-English status changes and movers across the "
           "Bailey Analytics economic dashboards.</description>"]
    for i in items:
        dt = datetime.strptime(i["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        out.append("<item>")
        out.append(f"<title>{escape(i['title'])}</title>")
        out.append(f"<link>{BRIEF_URL}</link>")
        out.append(f"<guid isPermaLink=\"false\">brief-{i['date']}</guid>")
        out.append(f"<pubDate>{format_datetime(dt)}</pubDate>")
        out.append(f"<description>{escape(i['description'])}</description>")
        out.append("</item>")
    out.append("</channel></rss>")
    return "\n".join(out)
```

- [ ] **Step 4: Run — PASS.**
- [ ] **Step 5: Wire into `refresh_brief`** (inside the existing try, after the today.json write):

```python
        # RSS: one item per day, rolling 30 days, written only when the brief changed.
        if wrote:
            items_path = BRIEF_OUT_DIR / "_feed_items.json"
            try:
                existing = json.loads(items_path.read_text(encoding="utf-8"))
            except (ValueError, OSError, FileNotFoundError):
                existing = []
            items = feed.merge_items(existing, feed.build_item(today))
            items_path.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
            feed_path = Path(__file__).resolve().parent.parent / "feed.xml"
            feed_path.write_text(feed.render_feed(items), encoding="utf-8")
            print(f"Wrote {feed_path}")
```

(Add `feed` to the `from lenses import ...` line.)

- [ ] **Step 6:** Head links on home/dashboards/brief pages: `<link rel="alternate" type="application/rss+xml" title="Bailey Analytics — Today&#39;s Brief" href="/feed.xml">`; visible `RSS` link in the brief page's `.brief-links`/foot. Bake current `feed.xml` + `_feed_items.json` offline from `data/brief/today.json` with a one-shot script (then delete it).
- [ ] **Step 7:** Full suite + `--dry-run`-free verification (don't dry-run; it overwrites data). Commit `feat: RSS feed for Today's Brief (feed.xml, rolling 30 days)`

### Task 7: Rate Expectations indicator on Cost of Money

**Files:** Modify `scripts/lenses/util.py` (`spread_ffill` + tests), `scripts/lenses/narrative.py` (`rule_rate_expectations` + tests in `test_narrative.py`), `scripts/lenses/config.py` (4th indicator), `scripts/refresh_lenses.py` (`_inject_rate_expectations`); offline bake into `data/lenses/cost-of-money.json`.

- [ ] **Step 1: Failing tests.** `test_util.py`:

```python
class TestSpreadFfill(unittest.TestCase):
    def test_subtracts_with_forward_fill(self):
        a = [{"date": "2026-01-02", "value": "4.20"}, {"date": "2026-02-03", "value": "4.00"}]
        b = [{"date": "2026-01-01", "value": "4.50"}, {"date": "2026-02-01", "value": "4.40"}]
        self.assertEqual(util.spread_ffill(a, b), [
            {"date": "2026-01-02", "value": "-0.30"},
            {"date": "2026-02-03", "value": "-0.40"},
        ])

    def test_skips_dates_before_subtrahend_starts(self):
        a = [{"date": "2025-12-31", "value": "4.20"}]
        b = [{"date": "2026-01-01", "value": "4.50"}]
        self.assertEqual(util.spread_ffill(a, b), [])

    def test_handles_none(self):
        self.assertEqual(util.spread_ffill(None, []), [])
```

`test_narrative.py`:

```python
class TestRateExpectations(unittest.TestCase):
    def test_deep_negative_reads_cuts(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", -1.1)])
        self.assertIn("cut", text.lower())
        self.assertEqual(status, "info")

    def test_near_zero_reads_hold(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", 0.05)])
        self.assertIn("hold", text.lower())
        self.assertEqual(status, "info")

    def test_positive_reads_hikes(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", 0.8)])
        self.assertIn("hike", text.lower())

    def test_empty(self):
        self.assertEqual(narrative.rule_rate_expectations([]), narrative._NO_DATA)
```

- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement.** `util.py`:

```python
def spread_ffill(minuend, subtrahend):
    """a - b on a's dates, forward-filling b (e.g. daily yield minus monthly policy
    rate). Skips a-dates before b begins. Returns [{'date','value'}], 2-dp strings."""
    if not minuend or not subtrahend:
        return []
    b = sorted((p["date"], to_float(p["value"])) for p in subtrahend)
    out, bi, last_b = [], 0, None
    for p in sorted(minuend, key=lambda r: r["date"]):
        a = to_float(p["value"])
        while bi < len(b) and b[bi][0] <= p["date"]:
            if b[bi][1] is not None:
                last_b = b[bi][1]
            bi += 1
        if a is None or last_b is None:
            continue
        out.append({"date": p["date"], "value": f"{a - last_b:.2f}"})
    return out
```

`narrative.py` (near `rule_rate_trend`):

```python
def rule_rate_expectations(obs):
    """DGS2 minus the fed funds rate: the bond market's pricing of the Fed's next
    moves. Descriptive (info) — it carries no good/bad verdict for the badge."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= -0.75:
        return (f"The 2-year yield sits {abs(v):.2f} points below the Fed's rate — "
                "markets are pricing meaningful rate cuts ahead.", "info")
    if v <= -0.25:
        return (f"The 2-year yield is {abs(v):.2f} points below the Fed's rate — "
                "markets lean toward rate cuts.", "info")
    if v < 0.25:
        return ("The 2-year yield is roughly in line with the Fed's rate — "
                "markets expect the Fed to hold near current levels.", "info")
    return (f"The 2-year yield is {v:.2f} points above the Fed's rate — "
            "markets are pricing rate hikes ahead.", "info")
```

`config.py` — append to `COST_OF_MONEY.indicators`:

```python
        Indicator(
            id="rate-expectations",
            title="Rate Expectations · 2-Year minus Fed Funds",
            short="2y vs Fed",
            unit="%",
            color="#FBBF24",
            series_id="DGS2_FEDFUNDS_SPREAD",
            limit=2600,
            source="computed",
            rule=narrative.rule_rate_expectations,
            context=(
                "The 2-year Treasury yield minus the Fed's current policy rate — the bond "
                "market's verdict on where the Fed goes next. Well below zero means markets "
                "are pricing rate cuts; above zero, hikes. It is computed from the two "
                "series charted above."
            ),
        ),
```

`refresh_lenses.py` — in `refresh_economic`, after `fetched`/`failed` are set, before `ready`:

```python
    # Computed: 2y-vs-Fed spread for the rate-expectations indicator (mirrors
    # the business-shares pattern; falls back to prior data if inputs failed).
    spread = util.spread_ffill(fetched.get("DGS2:lin"), fetched.get("FEDFUNDS:lin"))
    fetched["DGS2_FEDFUNDS_SPREAD:lin"] = spread or _prior_obs(OUT_DIR, "cost-of-money", "rate-expectations")
```

(`_prior_obs` is defined below `refresh_markets` — move it above `refresh_economic` or reference it lazily; plan: move the function definition above `refresh_economic`.)

- [ ] **Step 4: Run full suite — PASS.** Also add a config test (`test_config_markets.py`-style, in `test_narrative.py` or a new `test_config_economic.py`): `COST_OF_MONEY` has 4 indicators and the 4th has `source == "computed"`.
- [ ] **Step 5: Offline bake** — one-shot script: load `data/lenses/cost-of-money.json`, compute `util.spread_ffill(treasury-2y obs, fed-funds obs)`, thin, run the rule, append the indicator dict with the exact shape `build.build_lens` produces (`id/title/short/unit/color/series_id/observations/latest/context/read/signal_status/value_format`), write back. `data/lenses/index.json` is unaffected (key stats come from the first 2 indicators; status unchanged — "info" is ignored by `status_max`). Delete script.
- [ ] **Step 6: Update docs** — CLAUDE.md "Cost of Money is now 3 policy-rate charts" → "4 charts (3 policy rates + a computed 2y-vs-Fed rate-expectations spread)". Commit `feat(economic): Rate Expectations indicator — what markets price the Fed to do next`

### Task 8: Final verification

- [ ] Full unittest suite green.
- [ ] `node --check` on all JS + every inline HTML block.
- [ ] Re-parse every changed JSON.
- [ ] `python -m http.server` spot-fetch: `/feed.xml` (200, valid XML), one thinned lens JSON, dashboards index.
- [ ] Report payload-size deltas.

## Self-Review

- Spec coverage: payload size (T1), slug maps (T2), stale flag (T3), noscript (T4), as-of stamp (T5), RSS (T6), rate expectations (T7) — geopolitics/email explicitly out of scope with reasons. ✔
- Type consistency: `spread_ffill` returns 2-dp string values matching FRED observation shape; `feed.merge_items(existing, new_item, cap)` signature consistent between tests and impl; `loadHubGrid` 4th-param back-compat covers the badge strings added earlier today. ✔
- No placeholders. ✔

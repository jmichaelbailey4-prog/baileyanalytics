# Today's Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based, pipeline-generated "Today's Brief" — a cross-category digest of status transitions and the most significant moves across all six dashboard categories — surfaced atop `/dashboards/` and on the home page.

**Architecture:** A new stdlib-only module `scripts/lenses/brief.py` reads the six already-built `index.json` files plus a persisted `data/brief/_prior_state.json`, diffs lens statuses to find transitions, ranks remaining moves by % change of each lens's primary indicator (from the sparkline already in `index.json`), and writes `data/brief/today.json` + an updated `_prior_state.json`. A `--brief` step in `refresh_lenses.py` runs it last, decoupled from which categories were refreshed. A shared `dashboards/brief.js` renders the JSON into a hub panel and a compact home-page strip.

**Tech Stack:** Python 3.12 stdlib (`json`, `pathlib`, `datetime`), `unittest`; zero-build static HTML/CSS/JS (no framework, no bundler).

**Reference:** Spec at `docs/superpowers/specs/2026-06-10-todays-brief-design.md`.

---

## Conventions (read once before starting)

- **Run tests** (full suite):
  `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
- **Run one test:**
  `python -m unittest -v scripts.tests.test_brief` is NOT how this repo runs — instead:
  `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"` (each test file has a `unittest.main()` main guard and inserts `parents[1]` on `sys.path`).
- **Test file skeleton** (every new test file starts with this, matching `test_build_housing.py`):
  ```python
  import sys
  import pathlib
  import json
  import unittest

  sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
  from lenses import brief          # or: import refresh_lenses
  ```
- **Commits:** small, per-task. End every commit message with the Co-Authored-By trailer:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
  Do all git work inside the repo: `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" ...`. **Do NOT push** (Michael pushes manually).
- **Do not run a non-dry-run `refresh_lenses.py`** (needs keys + network). The brief has no network; its tests use fixtures and temp dirs.

---

## File Structure

- **Create `scripts/lenses/brief.py`** — pure synthesis: href map, `pct_change`, `detect_transitions`, `rank_moves`, `build_brief`. No network, no disk I/O (callers pass data in, get data out).
- **Modify `scripts/refresh_lenses.py`** — add `BRIEF_OUT_DIR`, `BRIEF_FIXTURE`, `refresh_brief(dry_run)`, the `--brief` flag, and wire `do_brief` into `main()` (runs last).
- **Create `scripts/tests/test_brief.py`** — unit tests for `brief.py`.
- **Create `scripts/tests/test_refresh_brief.py`** — integration test for `refresh_brief` via a temp `data/` tree.
- **Create `scripts/tests/fixtures/brief_indices_sample.json`** — sample per-category index data (input for dry-run + tests).
- **Create `dashboards/brief.js`** — shared renderer (`loadBrief`).
- **Modify `dashboards/index.html`** — add a brief panel above the category grids + a `<script>` call.
- **Modify `index.html`** (root home page) — add a compact brief strip + render call.
- **Modify `dashboards/lens.css`** — add `.brief-*` styles.
- **Modify `.github/workflows/refresh-fred.yml`** and **`.github/workflows/refresh-banking.yml`** — add a `--brief` step before the commit step.

---

## Task 1: `pct_change` helper

**Files:**
- Create: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/tests/test_brief.py`:

```python
import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief


class TestPctChange(unittest.TestCase):
    def test_normal_rise(self):
        self.assertAlmostEqual(brief.pct_change([100.0, 110.0]), 10.0)

    def test_normal_fall(self):
        self.assertAlmostEqual(brief.pct_change([200.0, 150.0]), -25.0)

    def test_uses_last_two_only(self):
        self.assertAlmostEqual(brief.pct_change([1.0, 2.0, 4.0, 5.0]), 25.0)

    def test_single_point_is_none(self):
        self.assertIsNone(brief.pct_change([5.0]))

    def test_empty_is_none(self):
        self.assertIsNone(brief.pct_change([]))

    def test_zero_prior_is_none(self):
        self.assertIsNone(brief.pct_change([0.0, 3.0]))

    def test_none_arg_is_none(self):
        self.assertIsNone(brief.pct_change(None))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `ModuleNotFoundError: No module named 'lenses.brief'` (or AttributeError once the file exists).

- [ ] **Step 3: Write minimal implementation**

Create `scripts/lenses/brief.py`:

```python
"""Cross-category 'Today's Brief': diff lens statuses for transitions and rank
the most significant moves. Pure synthesis over already-built index.json data —
no network, no disk I/O (callers pass data in and get data out)."""

# Severity ladder for transition direction. Mirrors the home page's SEVERITY
# (index.html) and util.STATUS_ORDER; neutral/info/unknown are intentionally
# absent — only these four can "transition".
SEVERITY = {"ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def pct_change(sparkline):
    """Signed percent change of the last point vs the one before it, or None when
    there are <2 points or the prior value is zero. The sparkline already carries
    the primary indicator's raw numeric series (build.build_index)."""
    if not sparkline or len(sparkline) < 2:
        return None
    prior, latest = sparkline[-2], sparkline[-1]
    if prior == 0:
        return None
    return (latest - prior) / prior * 100.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): add pct_change helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `lens_href` — public page path per lens

**Files:**
- Modify: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

This mirrors the slug logic in `dashboards/index.html:62-96` exactly — keep them in sync.

- [ ] **Step 1: Write the failing test** (append to `test_brief.py`, before `if __name__`)

```python
class TestLensHref(unittest.TestCase):
    def test_economic_is_flat_dashboards(self):
        self.assertEqual(brief.lens_href("economic", "fiscal-health"),
                         "/dashboards/fiscal-health.html")

    def test_banking_strips_bank_prefix(self):
        self.assertEqual(brief.lens_href("banking", "bank-asset-quality"),
                         "/dashboards/banking/asset-quality.html")

    def test_markets_uses_slug_map(self):
        self.assertEqual(brief.lens_href("markets", "market-risk-sentiment"),
                         "/dashboards/markets/risk-sentiment.html")
        self.assertEqual(brief.lens_href("markets", "crypto-structure"),
                         "/dashboards/markets/crypto-structure.html")

    def test_energy_uses_slug_map(self):
        self.assertEqual(brief.lens_href("energy", "energy-oil-fuels"),
                         "/dashboards/energy/oil-fuels.html")

    def test_consumer_uses_slug_map(self):
        self.assertEqual(brief.lens_href("consumer", "consumer-credit"),
                         "/dashboards/consumer/credit-stress.html")

    def test_housing_uses_slug_map(self):
        self.assertEqual(brief.lens_href("housing", "housing-home-prices"),
                         "/dashboards/housing/home-prices.html")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `AttributeError: module 'lenses.brief' has no attribute 'lens_href'`.

- [ ] **Step 3: Write minimal implementation** (append to `brief.py`)

```python
# Lens-id -> page-slug maps, mirroring dashboards/index.html (keep in sync).
_MARKET_SLUGS = {
    "market-risk-sentiment": "risk-sentiment",
    "market-scoreboard": "scoreboard",
    "market-liquidity": "liquidity",
    "crypto-structure": "crypto-structure",
}
_ENERGY_SLUGS = {
    "energy-oil-fuels": "oil-fuels",
    "energy-natural-gas": "natural-gas",
    "energy-electricity": "electricity",
    "energy-commodities": "commodities",
}
_CONSUMER_SLUGS = {
    "consumer-spending": "spending",
    "consumer-credit": "credit-stress",
    "consumer-income-savings": "income-savings",
    "consumer-sentiment": "sentiment",
}
_HOUSING_SLUGS = {
    "housing-home-prices": "home-prices",
    "housing-affordability": "affordability",
    "housing-supply-construction": "supply-construction",
    "housing-rent-shelter": "rent-shelter",
}


def lens_href(category, lens_id):
    """Public page path for a lens, mirroring dashboards/index.html slug logic."""
    if category == "economic":
        return f"/dashboards/{lens_id}.html"
    if category == "banking":
        return f"/dashboards/banking/{lens_id.replace('bank-', '', 1)}.html"
    if category == "markets":
        return f"/dashboards/markets/{_MARKET_SLUGS.get(lens_id, lens_id)}.html"
    if category == "energy":
        return f"/dashboards/energy/{_ENERGY_SLUGS.get(lens_id, lens_id)}.html"
    if category == "consumer":
        return f"/dashboards/consumer/{_CONSUMER_SLUGS.get(lens_id, lens_id)}.html"
    if category == "housing":
        return f"/dashboards/housing/{_HOUSING_SLUGS.get(lens_id, lens_id)}.html"
    return "/dashboards/"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (13 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): add lens_href slug map

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `_flatten_lenses` — category indices to a flat meta list

**Files:**
- Modify: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

`build_brief` (Task 6) needs one flat list of lens records carrying their category,
href, and the move fields. This task isolates that flattening.

- [ ] **Step 1: Write the failing test** (append to `test_brief.py`)

```python
def _indices():
    return {
        "economic": {"lenses": [
            {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
             "status": "elevated", "headline_read": "Debt is climbing.",
             "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "0.30%", "dir": "up"}],
             "sparkline": [120.0, 124.0]},
        ]},
        "markets": {"lenses": [
            {"id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#b",
             "status": "neutral", "headline_read": "Crypto is mixed.",
             "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "2.00%", "dir": "up"}],
             "sparkline": [50.0, 56.0]},
        ]},
    }


class TestFlatten(unittest.TestCase):
    def test_flattens_with_category_and_href(self):
        flat = brief._flatten_lenses(_indices())
        self.assertEqual(len(flat), 2)
        fiscal = next(r for r in flat if r["lens_id"] == "fiscal-health")
        self.assertEqual(fiscal["category"], "economic")
        self.assertEqual(fiscal["href"], "/dashboards/fiscal-health.html")
        self.assertEqual(fiscal["status"], "elevated")
        self.assertEqual(fiscal["headline"], "Debt is climbing.")
        self.assertEqual(fiscal["lens_title"], "Fiscal Health")

    def test_skips_missing_categories(self):
        flat = brief._flatten_lenses({"economic": None, "markets": {"lenses": []}})
        self.assertEqual(flat, [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `AttributeError: ... has no attribute '_flatten_lenses'`.

- [ ] **Step 3: Write minimal implementation** (append to `brief.py`)

```python
# Category order for the brief (drives tie-break ordering only).
CATEGORIES = ["economic", "consumer", "banking", "markets", "energy", "housing"]


def _flatten_lenses(category_indices):
    """Flatten {category: index_json} into a list of lens records carrying
    category, href, status, headline, key_stats, and sparkline."""
    flat = []
    for category in CATEGORIES:
        index = category_indices.get(category)
        if not index:
            continue
        for lens in index.get("lenses", []):
            flat.append({
                "lens_id": lens["id"],
                "lens_title": lens["title"],
                "category": category,
                "href": lens_href(category, lens["id"]),
                "status": lens.get("status", "unknown"),
                "headline": lens.get("headline_read", ""),
                "key_stats": lens.get("key_stats", []),
                "sparkline": lens.get("sparkline", []),
            })
    return flat
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): flatten category indices to lens meta list

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `detect_transitions`

**Files:**
- Modify: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

- [ ] **Step 1: Write the failing test** (append to `test_brief.py`)

```python
class TestDetectTransitions(unittest.TestCase):
    def _flat(self, *pairs):
        # pairs: (lens_id, status)
        return [{"lens_id": i, "lens_title": i.title(), "category": "economic",
                 "href": "/x", "status": s, "headline": f"{i} read.",
                 "key_stats": [], "sparkline": []} for i, s in pairs]

    def test_status_change_is_a_transition(self):
        prior = {"job-market": "watch"}
        flat = self._flat(("job-market", "elevated"))
        out = brief.detect_transitions(prior, flat)
        self.assertEqual(len(out), 1)
        t = out[0]
        self.assertEqual(t["from_status"], "watch")
        self.assertEqual(t["to_status"], "elevated")
        self.assertEqual(t["direction"], "worsening")
        self.assertEqual(t["lens_id"], "job-market")
        self.assertEqual(t["headline"], "job-market read.")

    def test_unchanged_status_is_not_a_transition(self):
        prior = {"job-market": "watch"}
        flat = self._flat(("job-market", "watch"))
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_first_run_no_prior_yields_no_transitions(self):
        flat = self._flat(("job-market", "elevated"))
        self.assertEqual(brief.detect_transitions({}, flat), [])

    def test_new_lens_not_in_prior_is_skipped(self):
        prior = {"job-market": "ok"}
        flat = self._flat(("brand-new", "alert"))
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_neutral_lens_excluded(self):
        prior = {"crypto-structure": "neutral"}
        flat = [{"lens_id": "crypto-structure", "lens_title": "Crypto", "category": "markets",
                 "href": "/x", "status": "ok", "headline": "h", "key_stats": [], "sparkline": []}]
        # 'neutral' is not in SEVERITY, so a neutral->ok change is not a transition
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_worsening_sorts_before_improving_and_by_jump(self):
        prior = {"a": "ok", "b": "watch", "c": "alert"}
        flat = self._flat(("a", "alert"), ("b", "ok"), ("c", "elevated"))
        out = brief.detect_transitions(prior, flat)
        # a: ok->alert (+3 worsening), c: alert->elevated (-1 improving),
        # b: watch->ok (-1 improving). Worsening first, then improving.
        self.assertEqual(out[0]["lens_id"], "a")
        self.assertEqual(out[0]["direction"], "worsening")
        self.assertTrue(all(t["direction"] == "improving" for t in out[1:]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `AttributeError: ... has no attribute 'detect_transitions'`.

- [ ] **Step 3: Write minimal implementation** (append to `brief.py`)

```python
def detect_transitions(prior_statuses, flat_lenses):
    """Lenses whose severity status changed vs. prior_statuses. Only ok/watch/
    elevated/alert transitions count (neutral/info/unknown are skipped). Sorted
    worsening-first by size of the severity jump, then improving."""
    out = []
    for r in flat_lenses:
        new = r["status"]
        old = prior_statuses.get(r["lens_id"])
        if old is None or old == new:
            continue
        if old not in SEVERITY or new not in SEVERITY:
            continue
        jump = SEVERITY[new] - SEVERITY[old]
        out.append({
            "lens_id": r["lens_id"],
            "lens_title": r["lens_title"],
            "category": r["category"],
            "href": r["href"],
            "from_status": old,
            "to_status": new,
            "direction": "worsening" if jump > 0 else "improving",
            "headline": r["headline"],
            "_jump": jump,
        })
    # Worsening (positive jump) first, largest jump first; then improving.
    out.sort(key=lambda t: -t["_jump"])
    for t in out:
        del t["_jump"]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (21 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): detect status transitions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: `rank_moves`

**Files:**
- Modify: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

- [ ] **Step 1: Write the failing test** (append to `test_brief.py`)

```python
class TestRankMoves(unittest.TestCase):
    def _lens(self, lens_id, spark, d="1.00%", dir_="up", k="Stat", v="1.00%"):
        return {"lens_id": lens_id, "lens_title": lens_id.title(), "category": "economic",
                "href": "/x", "status": "ok", "headline": "h",
                "key_stats": [{"k": k, "v": v, "d": d, "dir": dir_}], "sparkline": spark}

    def test_ranks_by_abs_pct_change_desc(self):
        flat = [self._lens("small", [100.0, 101.0]),   # +1%
                self._lens("big", [100.0, 110.0]),     # +10%
                self._lens("mid", [100.0, 95.0])]      # -5%
        moves = brief.rank_moves(flat, transition_ids=set(), limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["big", "mid", "small"])

    def test_excludes_transition_lenses(self):
        flat = [self._lens("big", [100.0, 110.0]), self._lens("mid", [100.0, 95.0])]
        moves = brief.rank_moves(flat, transition_ids={"big"}, limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["mid"])

    def test_threshold_filters_small_moves(self):
        flat = [self._lens("tiny", [100.0, 100.3])]   # +0.3% < 0.5%
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_limit_caps_results(self):
        flat = [self._lens(f"l{i}", [100.0, 100.0 + i + 1]) for i in range(6)]
        moves = brief.rank_moves(flat, set(), limit=3)
        self.assertEqual(len(moves), 3)

    def test_sparkline_too_short_is_skipped(self):
        flat = [self._lens("flat", [100.0])]
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_move_carries_display_fields(self):
        flat = [self._lens("big", [100.0, 110.0], d="10.00%", dir_="up",
                            k="Debt-to-GDP", v="124.50%")]
        m = brief.rank_moves(flat, set(), limit=5)[0]
        self.assertEqual(m["stat_label"], "Debt-to-GDP")
        self.assertEqual(m["stat_value"], "124.50%")
        self.assertEqual(m["delta"], "10.00%")
        self.assertEqual(m["dir"], "up")
        self.assertAlmostEqual(m["pct_change"], 10.0)
        self.assertEqual(m["href"], "/x")

    def test_neutral_lens_eligible_for_moves(self):
        crypto = self._lens("crypto-structure", [50.0, 56.0])
        crypto["status"] = "neutral"
        moves = brief.rank_moves([crypto], set(), limit=5)
        self.assertEqual(len(moves), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `AttributeError: ... has no attribute 'rank_moves'`.

- [ ] **Step 3: Write minimal implementation** (append to `brief.py`)

```python
MOVE_THRESHOLD_PCT = 0.5  # ignore moves smaller than this (noise floor)


def rank_moves(flat_lenses, transition_ids, limit=5):
    """Up to `limit` non-transition lenses ranked by |pct_change| of the primary
    indicator (descending), filtered to moves >= MOVE_THRESHOLD_PCT. Carries the
    first key_stat's display fields straight through."""
    candidates = []
    for r in flat_lenses:
        if r["lens_id"] in transition_ids:
            continue
        pc = pct_change(r["sparkline"])
        if pc is None or abs(pc) < MOVE_THRESHOLD_PCT:
            continue
        stat = (r["key_stats"] or [{}])[0]
        candidates.append({
            "lens_id": r["lens_id"],
            "lens_title": r["lens_title"],
            "category": r["category"],
            "href": r["href"],
            "stat_label": stat.get("k", ""),
            "stat_value": stat.get("v", "—"),
            "delta": stat.get("d", ""),
            "dir": stat.get("dir", ""),
            "pct_change": pc,
        })
    candidates.sort(key=lambda m: -abs(m["pct_change"]))
    return candidates[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (28 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): rank moves by percent change

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `build_brief` — assemble today.json + new state

**Files:**
- Modify: `scripts/lenses/brief.py`
- Test: `scripts/tests/test_brief.py`

`limit` for `rank_moves` is `5 - len(transitions)` so the combined headline count
stays at 5. `status_counts` tallies every lens's status (including `neutral`).

- [ ] **Step 1: Write the failing test** (append to `test_brief.py`)

```python
class TestBuildBrief(unittest.TestCase):
    def _indices(self):
        return {
            "economic": {"lenses": [
                {"id": "job-market", "title": "Job Market", "accent": "#a",
                 "status": "elevated", "headline_read": "Hiring is slowing.",
                 "key_stats": [{"k": "Unemployment", "v": "4.50%", "d": "0.20%", "dir": "up"}],
                 "sparkline": [4.0, 4.5]},
                {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
                 "status": "ok", "headline_read": "Finances steady.",
                 "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "0.30%", "dir": "up"}],
                 "sparkline": [100.0, 112.0]},  # +12% move
            ]},
            "markets": {"lenses": [
                {"id": "crypto-structure", "title": "Crypto", "accent": "#b",
                 "status": "neutral", "headline_read": "Crypto mixed.",
                 "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "2.00%", "dir": "up"}],
                 "sparkline": [50.0, 56.0]},  # +12% move
            ]},
        }

    def test_transition_detected_and_state_returned(self):
        prior = {"statuses": {"job-market": "watch", "fiscal-health": "ok",
                              "crypto-structure": "neutral"}}
        today, state = brief.build_brief(self._indices(), prior)
        self.assertEqual(len(today["transitions"]), 1)
        self.assertEqual(today["transitions"][0]["lens_id"], "job-market")
        self.assertEqual(today["transitions"][0]["to_status"], "elevated")
        # new state captures every current status
        self.assertEqual(state["statuses"]["job-market"], "elevated")
        self.assertEqual(state["statuses"]["crypto-structure"], "neutral")

    def test_moves_exclude_the_transition_lens(self):
        prior = {"statuses": {"job-market": "watch", "fiscal-health": "ok",
                              "crypto-structure": "neutral"}}
        today, _ = brief.build_brief(self._indices(), prior)
        ids = [m["lens_id"] for m in today["top_moves"]]
        self.assertNotIn("job-market", ids)
        self.assertIn("fiscal-health", ids)   # +12% move
        self.assertIn("crypto-structure", ids) # neutral but eligible

    def test_status_counts_tally(self):
        today, _ = brief.build_brief(self._indices(), {"statuses": {}})
        self.assertEqual(today["status_counts"],
                         {"ok": 1, "watch": 0, "elevated": 1, "alert": 0, "neutral": 1})

    def test_first_run_empty_prior(self):
        today, state = brief.build_brief(self._indices(), {})
        self.assertEqual(today["transitions"], [])
        self.assertTrue(today["top_moves"])  # moves still populate
        self.assertIn("generated_at", today)
        self.assertEqual(state["statuses"]["job-market"], "elevated")

    def test_combined_headline_count_capped_at_five(self):
        # 6 transitions -> 0 move slots
        prior_statuses = {f"l{i}": "ok" for i in range(6)}
        idx = {"economic": {"lenses": [
            {"id": f"l{i}", "title": f"L{i}", "accent": "#a", "status": "alert",
             "headline_read": "h", "key_stats": [{"k": "x", "v": "1", "d": "1", "dir": "up"}],
             "sparkline": [1.0, 2.0]} for i in range(6)]}}
        today, _ = brief.build_brief(idx, {"statuses": prior_statuses})
        self.assertEqual(len(today["transitions"]), 6)
        self.assertEqual(today["top_moves"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: FAIL — `AttributeError: ... has no attribute 'build_brief'`.

- [ ] **Step 3: Write minimal implementation** (append to `brief.py`)

Add the import at the top of `brief.py` (just below the module docstring):

```python
from datetime import datetime, timezone
```

Then append:

```python
def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _status_counts(flat_lenses):
    counts = {"ok": 0, "watch": 0, "elevated": 0, "alert": 0, "neutral": 0}
    for r in flat_lenses:
        s = r["status"]
        if s in counts:
            counts[s] += 1
    return counts


def build_brief(category_indices, prior_state):
    """Assemble (today_json, new_state) from per-category index data and the
    prior state. prior_state shape: {"statuses": {lens_id: status}}."""
    prior_statuses = (prior_state or {}).get("statuses", {})
    flat = _flatten_lenses(category_indices)

    transitions = detect_transitions(prior_statuses, flat)
    transition_ids = {t["lens_id"] for t in transitions}
    moves = rank_moves(flat, transition_ids, limit=max(0, 5 - len(transitions)))

    today = {
        "generated_at": _now(),
        "transitions": transitions,
        "top_moves": moves,
        "status_counts": _status_counts(flat),
    }
    new_state = {"captured_at": today["generated_at"],
                 "statuses": {r["lens_id"]: r["status"] for r in flat}}
    return today, new_state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_brief.py"`
Expected: PASS (33 tests).

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/brief.py scripts/tests/test_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): assemble today.json and prior state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Fixture for dry-run + integration

**Files:**
- Create: `scripts/tests/fixtures/brief_indices_sample.json`

This fixture is the canonical per-category index input for `--brief --dry-run`
(Task 8) and the integration test (Task 9). It carries at least one transition-worthy
and one move-worthy lens.

- [ ] **Step 1: Create the fixture**

Create `scripts/tests/fixtures/brief_indices_sample.json`:

```json
{
  "economic": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "recession-watch", "title": "Recession Watch", "accent": "#F87171",
       "status": "ok", "headline_read": "The economy looks steady.",
       "key_stats": [{"k": "Yield curve", "v": "0.40%", "d": "0.05%", "dir": "up"}],
       "sparkline": [0.30, 0.40]},
      {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#F87171",
       "status": "elevated", "headline_read": "Debt and interest costs are climbing.",
       "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "1.20%", "dir": "up"}],
       "sparkline": [110.0, 124.5]}
    ]
  },
  "markets": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#818CF8",
       "status": "neutral", "headline_read": "Bitcoin dominance is rising.",
       "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "3.00%", "dir": "up"}],
       "sparkline": [50.0, 56.0]}
    ]
  },
  "consumer": {
    "last_updated": "2026-06-10T13:00:00Z",
    "lenses": [
      {"id": "consumer-sentiment", "title": "Consumer Sentiment", "accent": "#E879F9",
       "status": "watch", "headline_read": "Confidence is softening.",
       "key_stats": [{"k": "Sentiment", "v": "62.00", "d": "1.00", "dir": "down"}],
       "sparkline": [63.0, 62.0]}
    ]
  }
}
```

- [ ] **Step 2: Verify it is valid JSON**

Run: `python -c "import json; json.load(open(r'C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/fixtures/brief_indices_sample.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/fixtures/brief_indices_sample.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(brief): add brief indices fixture

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: `refresh_brief` + `--brief` flag in `refresh_lenses.py`

**Files:**
- Modify: `scripts/refresh_lenses.py`
- Test: `scripts/tests/test_refresh_brief.py` (Task 9)

`refresh_brief` reads each category's `index.json` from its existing module-global
out-dir (live) or the fixture (dry-run), reads `_prior_state.json` from
`BRIEF_OUT_DIR`, calls `brief.build_brief`, and writes `today.json` +
`_prior_state.json`. A missing category index is skipped (additive/fault-tolerant).

- [ ] **Step 1: Add module globals and import**

In `scripts/refresh_lenses.py`, add `brief` to the `from lenses import ...` line
(line 18), so it reads:

```python
from lenses import brief, build, coingecko, config, eia, fdic, fred, util, yahoo
```

Then add these globals just after `CRYPTO_FIXTURE` (line 33):

```python
BRIEF_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"
BRIEF_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "brief_indices_sample.json"

# category -> the module-global out-dir whose index.json feeds the brief.
# 'economic' lives in data/lenses/ (not data/economic/).
def _brief_index_dirs():
    return {
        "economic": OUT_DIR,
        "banking": BANK_OUT_DIR,
        "markets": MARKETS_OUT_DIR,
        "energy": ENERGY_OUT_DIR,
        "housing": HOUSING_OUT_DIR,
        "consumer": CONSUMER_OUT_DIR,
    }
```

(`_brief_index_dirs()` is a function, not a constant, so it re-reads the module
globals each call — letting tests monkeypatch the out-dirs.)

- [ ] **Step 2: Add `refresh_brief`**

Add this function just before `def main(` (line 424):

```python
def _load_brief_indices(dry_run):
    """Return {category: index_json}. Dry-run reads one fixture file; live reads
    each category's index.json from its out-dir, skipping any not yet present."""
    if dry_run:
        return json.loads(BRIEF_FIXTURE.read_text(encoding="utf-8"))
    indices = {}
    for category, out_dir in _brief_index_dirs().items():
        path = out_dir / "index.json"
        if path.exists():
            try:
                indices[category] = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
    return indices


def _load_prior_state():
    path = BRIEF_OUT_DIR / "_prior_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {}


def refresh_brief(dry_run):
    """Build + write data/brief/today.json and _prior_state.json from the current
    per-category index.json files. Additive — never raises; a missing category is
    simply absent from the brief."""
    try:
        indices = _load_brief_indices(dry_run)
        today, new_state = brief.build_brief(indices, _load_prior_state())
        BRIEF_OUT_DIR.mkdir(parents=True, exist_ok=True)
        (BRIEF_OUT_DIR / "today.json").write_text(
            json.dumps(today, indent=2) + "\n", encoding="utf-8")
        (BRIEF_OUT_DIR / "_prior_state.json").write_text(
            json.dumps(new_state, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {BRIEF_OUT_DIR / 'today.json'}")
    except Exception as exc:  # noqa: BLE001 - never break the run on a brief failure
        print(f"WARN: brief build failed ({exc}); keeping previous brief", file=sys.stderr)
```

Note: unlike category refreshes, the brief always rewrites `today.json` (its
`generated_at`/`captured_at` always change). That is intentional — the brief is the
freshness signal — and the commit step only commits when `git status` shows a diff,
so an all-identical brief still produces a trivial timestamp-only change. (Acceptable;
matches `_crypto_history.json`, which also rewrites each run.)

- [ ] **Step 3: Add the `--brief` flag and wire into `main()`**

In `main()`, add the argument after the `--consumer` line (line 432):

```python
    parser.add_argument("--brief", action="store_true", help="rebuild only Today's Brief from existing indices")
```

Update the `any_flag` expression (lines 437-438) to include brief:

```python
    any_flag = (args.economic or args.banking or args.markets or args.energy
                or args.housing or args.consumer or args.brief)
```

Add `do_brief` after `do_consumer` (line 444):

```python
    do_brief = args.brief or not any_flag
```

Add the brief call as the **last** thing before `return code` (after the banking
block at lines 467-468):

```python
    if do_brief:
        refresh_brief(args.dry_run)
```

- [ ] **Step 4: Smoke-test the flag manually (writes to a temp dir, not real data/)**

Run:
```
python -c "import sys, pathlib, tempfile; sys.path.insert(0, r'C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts'); import refresh_lenses as r; d=pathlib.Path(tempfile.mkdtemp()); r.BRIEF_OUT_DIR=d; r.main(['--brief','--dry-run']); print((d/'today.json').read_text()[:200])"
```
Expected: prints the head of a valid `today.json` with `generated_at` and `transitions`.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): add --brief step to refresh_lenses

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Integration test for `refresh_brief`

**Files:**
- Create: `scripts/tests/test_refresh_brief.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/tests/test_refresh_brief.py`:

```python
import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBriefDryRun(unittest.TestCase):
    def test_brief_flag_writes_today_and_state(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.BRIEF_OUT_DIR
            refresh_lenses.BRIEF_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--brief", "--dry-run"])
            finally:
                refresh_lenses.BRIEF_OUT_DIR = orig
            self.assertEqual(rc, 0)
            today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
            state = json.loads((tmp / "_prior_state.json").read_text(encoding="utf-8"))
            self.assertIn("generated_at", today)
            self.assertIn("transitions", today)
            self.assertIn("top_moves", today)
            self.assertIn("status_counts", today)
            # fixture has fiscal-health elevated -> captured in state
            self.assertEqual(state["statuses"]["fiscal-health"], "elevated")

    def test_second_run_detects_transition_from_seeded_state(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            # seed a prior state where fiscal-health was 'ok' (fixture says 'elevated')
            (tmp / "_prior_state.json").write_text(
                json.dumps({"statuses": {"fiscal-health": "ok"}}) + "\n", encoding="utf-8")
            orig = refresh_lenses.BRIEF_OUT_DIR
            refresh_lenses.BRIEF_OUT_DIR = tmp
            try:
                refresh_lenses.main(["--brief", "--dry-run"])
            finally:
                refresh_lenses.BRIEF_OUT_DIR = orig
            today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
            ids = [t["lens_id"] for t in today["transitions"]]
            self.assertIn("fiscal-health", ids)
            t = next(t for t in today["transitions"] if t["lens_id"] == "fiscal-health")
            self.assertEqual(t["from_status"], "ok")
            self.assertEqual(t["to_status"], "elevated")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it passes** (implementation already exists from Task 8)

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_brief.py"`
Expected: PASS (2 tests). If FAIL, fix `refresh_brief` in Task 8, not the test.

- [ ] **Step 3: Run the FULL suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: OK, all ~270 + new tests pass. **If `data/` was touched by any earlier smoke test, run** `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" status` **and `git checkout -- data/` if needed** (no real data should have changed — the brief tests use temp dirs).

- [ ] **Step 4: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/test_refresh_brief.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(brief): integration test for --brief dry-run

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Generate a real `data/brief/today.json` from current indices

The frontend tasks need a real file to render against. The brief has **no network**,
so this is safe to run live (it only reads the existing committed `index.json` files).

**Files:**
- Create (generated): `data/brief/today.json`, `data/brief/_prior_state.json`

- [ ] **Step 1: Generate the real brief from committed indices**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --brief`
Expected: `Wrote .../data/brief/today.json`.

- [ ] **Step 2: Eyeball the output**

Run: `python -c "import json; d=json.load(open(r'C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/data/brief/today.json')); print('transitions', len(d['transitions'])); print('moves', [(m['lens_title'], round(m['pct_change'],1)) for m in d['top_moves']]); print('counts', d['status_counts'])"`
Expected: a sensible counts tally (totals to ~26 lenses) and 0–5 moves with plausible % changes. (First-ever run has 0 transitions — expected.)

- [ ] **Step 3: Commit the generated brief**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add data/brief/today.json data/brief/_prior_state.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "data(brief): initial Today's Brief snapshot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 11: `dashboards/brief.js` — shared renderer

**Files:**
- Create: `dashboards/brief.js`

Renders `today.json` into either the full hub panel or the compact home strip.
Uses the same `esc` pattern as `hub.js`. Badge classes (`badge ok/watch/...`) and
`delta up/down` already exist in `lens.css`.

- [ ] **Step 1: Create the renderer**

Create `dashboards/brief.js`:

```javascript
/* Shared renderer for Today's Brief.
   loadBrief("brief-panel", { compact:false }) -> full hub panel
   loadBrief("brief-strip", { compact:true })  -> one-line home summary */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function countsLine(c) {
    const parts = [];
    if (c.alert) parts.push(`${c.alert} alert`);
    if (c.elevated) parts.push(`${c.elevated} elevated`);
    if (c.watch) parts.push(`${c.watch} on watch`);
    return parts.length ? parts.join(" · ") : "All clear across the dashboards";
  }

  function transitionRow(t) {
    return `<a class="brief-trans" href="${t.href}">
      <span class="brief-trans-title">${esc(t.lens_title)}</span>
      <span class="brief-arrow">
        <span class="badge ${esc(t.from_status)}">${esc(t.from_status)}</span>
        &rarr;
        <span class="badge ${esc(t.to_status)}">${esc(t.to_status)}</span>
      </span>
      <span class="brief-trans-read">${esc(t.headline)}</span>
    </a>`;
  }

  function moveRow(m) {
    const delta = m.delta ? `<i class="delta ${esc(m.dir || "")}">${esc(m.delta)}</i>` : "";
    return `<a class="brief-move" href="${m.href}">
      <span class="brief-move-title">${esc(m.lens_title)}</span>
      <span class="brief-move-stat">${esc(m.stat_label)} <b>${esc(m.stat_value)}</b> ${delta}</span>
    </a>`;
  }

  function fullPanel(data) {
    const trans = (data.transitions || []).map(transitionRow).join("");
    const moves = (data.top_moves || []).map(moveRow).join("");
    const quiet = !trans && !moves;
    return `
      <div class="brief-head">Today&rsquo;s Brief
        <span class="brief-counts">${esc(countsLine(data.status_counts || {}))}</span></div>
      ${trans ? `<div class="brief-sec-label">Status changes</div>${trans}` : ""}
      ${moves ? `<div class="brief-sec-label">Biggest moves</div><div class="brief-moves">${moves}</div>` : ""}
      ${quiet ? `<div class="brief-quiet">Markets are quiet today — no status changes.</div>` : ""}`;
  }

  function compactStrip(data) {
    const t0 = (data.transitions || [])[0];
    const lead = t0
      ? `<a class="brief-strip-lead" href="${t0.href}">${esc(t0.lens_title)}: ${esc(t0.from_status)} &rarr; ${esc(t0.to_status)}</a>`
      : "";
    return `<span class="brief-strip-counts">${esc(countsLine(data.status_counts || {}))}</span>${lead}`;
  }

  window.loadBrief = async function (elId, opts) {
    opts = opts || {};
    const el = document.getElementById(elId);
    if (!el) return;
    try {
      const res = await fetch("/data/brief/today.json", { cache: "no-cache" });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      el.innerHTML = opts.compact ? compactStrip(data) : fullPanel(data);
      el.hidden = false;
    } catch (err) {
      el.hidden = true;  // brief is additive — never block the page
      console.error(err);
    }
  };
})();
```

- [ ] **Step 2: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/brief.js
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): shared brief.js renderer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 12: Brief styles in `lens.css`

**Files:**
- Modify: `dashboards/lens.css`

Append brief styles at the end of the file. Reuse existing CSS vars
(`--panel`, `--border`, `--text`, `--muted`, `--dim`, `--blue`). `.badge` and
`.delta` classes already exist.

- [ ] **Step 1: Append the styles**

Add to the end of `dashboards/lens.css`:

```css
/* ---- Today's Brief ---- */
.brief-panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;
  padding:1.1rem 1.2rem;margin-bottom:2rem}
.brief-head{font-size:1.05rem;font-weight:600;letter-spacing:-.01em;display:flex;
  align-items:baseline;gap:.7rem;flex-wrap:wrap;margin-bottom:.9rem}
.brief-counts{font-size:.78rem;font-weight:500;color:var(--muted)}
.brief-sec-label{font-size:.66rem;text-transform:uppercase;letter-spacing:.12em;
  color:var(--dim);margin:.8rem 0 .45rem}
.brief-trans{display:flex;align-items:center;gap:.7rem;flex-wrap:wrap;text-decoration:none;
  color:inherit;padding:.5rem .6rem;border-radius:9px;transition:background-color .15s ease}
.brief-trans:hover{background:rgba(255,255,255,.03)}
.brief-trans-title{font-weight:600;font-size:.86rem}
.brief-arrow{display:inline-flex;align-items:center;gap:.4rem;color:var(--dim);font-size:.8rem}
.brief-trans-read{color:var(--muted);font-size:.8rem;flex:1 1 14rem;min-width:0}
.brief-moves{display:flex;flex-direction:column;gap:.15rem}
.brief-move{display:flex;align-items:baseline;gap:.7rem;justify-content:space-between;
  text-decoration:none;color:inherit;padding:.4rem .6rem;border-radius:9px;
  transition:background-color .15s ease}
.brief-move:hover{background:rgba(255,255,255,.03)}
.brief-move-title{font-weight:600;font-size:.84rem}
.brief-move-stat{font-size:.78rem;color:var(--muted)}
.brief-move-stat b{color:var(--text);font-weight:600}
.brief-quiet{color:var(--muted);font-size:.84rem;padding:.3rem .2rem}
@media(max-width:640px){
  .brief-trans{gap:.4rem}
  .brief-trans-read{flex-basis:100%}
}
```

- [ ] **Step 2: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/lens.css
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "style(brief): brief panel + strip CSS

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 13: Wire the brief panel into `dashboards/index.html`

**Files:**
- Modify: `dashboards/index.html`

- [ ] **Step 1: Add the panel element** above the first category head.

In `dashboards/index.html`, immediately after the `<p class="lede">...</p>` block
(line 29) and before `<h2 class="cat-head">...Economic Lenses`, insert:

```html
    <section class="brief-panel" id="brief-panel" hidden></section>
```

- [ ] **Step 2: Add the script tag.**

Change the script includes near the bottom. After the existing
`<script defer src="/dashboards/hub.js"></script>` (line 60), add:

```html
  <script defer src="/dashboards/brief.js"></script>
```

- [ ] **Step 3: Call the renderer.**

Inside the existing `DOMContentLoaded` handler (the inline `<script>` starting at
line 61), add as the first statement inside the arrow function (right after
`() => {`):

```javascript
    loadBrief("brief-panel", { compact: false });
```

- [ ] **Step 4: Verify visually.**

Run (serves the site): `python -m http.server 8000` from the repo root
(`C:/Users/jmich/Documents/Business/Repositories/baileyanalytics`), open
`http://localhost:8000/dashboards/`. Expected: a "Today's Brief" panel renders above
the Economic Lenses heading, showing the counts line and (on first run) "Markets are
quiet today" or the biggest moves. Stop the server (Ctrl+C) when done.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): surface Today's Brief on dashboards hub

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 14: Compact brief strip on the home page

**Files:**
- Modify: `index.html` (root)

The home page already loads category tiles via an inline IIFE. Add a compact strip
inside the `.lenses-wrap` section, above the grid, plus the `brief.js` include and a
`loadBrief` call.

- [ ] **Step 1: Add the strip element** inside `.lenses-wrap`.

In root `index.html`, change the `seclabel`/grid block (lines 292-293). After the
`<div class="seclabel">...</div>` line, insert the strip:

```html
            <div class="brief-strip" id="brief-strip" hidden></div>
```

- [ ] **Step 2: Add minimal strip CSS.**

The root `index.html` is self-contained (its own `<style>`), so add these rules at
the end of its `<style>` block (just before `</style>` at line 277):

```css
        .brief-strip {
            display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem 1rem;
            font-size: 0.82rem; color: var(--muted);
            padding: 0.7rem 0.9rem; margin-bottom: 1rem;
            background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
        }
        .brief-strip-counts { color: var(--text); font-weight: 600; }
        .brief-strip-lead { color: var(--blue); text-decoration: none; }
        .brief-strip-lead:hover { text-decoration: underline; }
```

- [ ] **Step 3: Include `brief.js` and call it.**

The home page uses inline JS (not `hub.js`). Add the include just before the existing
inline `<script>` (line 304):

```html
    <script defer src="/dashboards/brief.js"></script>
```

Then, inside the existing IIFE, after `document.getElementById("lenses").hidden = false;`
(line 369), add:

```javascript
            loadBrief("brief-strip", { compact: true });
```

(Placing it here means the strip shows only once the live section is revealed,
keeping the hero clean when data is unavailable.)

- [ ] **Step 4: Verify visually.**

Serve and open `http://localhost:8000/` (root). Expected: once the live tiles load,
a one-line brief strip ("2 elevated · 5 on watch …") appears above the category
tiles. On first run with no transitions, it shows just the counts line.

- [ ] **Step 5: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(brief): compact brief strip on home page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 15: Add `--brief` step to both workflows

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`
- Modify: `.github/workflows/refresh-banking.yml`

Both commit steps already `git add data/`, so `data/brief/` is captured automatically
— only a build step is needed, placed **last** so it sees the freshest indices.

- [ ] **Step 1: refresh-fred.yml** — insert a step between the consumer step
(ends line 60) and the commit step (line 62):

```yaml
      - name: Rebuild Today's Brief (no network)
        if: ${{ success() || failure() }}
        run: python scripts/refresh_lenses.py --brief
```

- [ ] **Step 2: refresh-banking.yml** — insert a step between the FDIC fetch step
(ends line 29) and the commit step (line 31):

```yaml
      - name: Rebuild Today's Brief (no network)
        if: ${{ success() || failure() }}
        run: python scripts/refresh_lenses.py --brief
```

- [ ] **Step 3: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add .github/workflows/refresh-fred.yml .github/workflows/refresh-banking.yml
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "ci(brief): rebuild Today's Brief after each refresh

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 16: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite.**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: `OK` — all ~270 prior tests + ~37 new brief tests pass.

- [ ] **Step 2: Confirm no unintended `data/` churn.**

Run: `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" status --porcelain`
Expected: clean (everything committed). Only `data/brief/*` should have been added
in Task 10; no other `data/` files changed. If a stray `data/` change appears from a
test, `git checkout -- data/` (machine-vs-machine; we only authored `data/brief/`).

- [ ] **Step 3: Report to Michael.**

Summarize: tests green, brief renders on both surfaces, nothing pushed (awaiting his
go-ahead). Do NOT push — Michael pushes manually.

---

## Self-Review notes (addressed)

- **Spec coverage:** transitions (Task 4), %-change ranking via sparkline (Tasks 1,5),
  state persistence (Tasks 6,8), `--brief` decoupled step run last (Task 8),
  category→dir map with economic→lenses (Task 8), hub panel + home strip (Tasks 13,14),
  both workflows (Task 15), neutral lenses eligible-for-moves/excluded-from-transitions
  (Tasks 4,5), ≥0.5% threshold + quiet-day empty state (Tasks 5,11). All covered.
- **No placeholders:** every code/test step shows full content.
- **Type consistency:** `today.json` keys (`generated_at`, `transitions`, `top_moves`,
  `status_counts`) and record fields (`lens_id`, `lens_title`, `category`, `href`,
  `from_status`/`to_status`/`direction`/`headline` for transitions; `stat_label`/
  `stat_value`/`delta`/`dir`/`pct_change` for moves) are identical across `brief.py`,
  the tests, `brief.js`, and the fixture.
- **`_fmt`/`fmtVal` sync rule untouched:** the brief renders pre-formatted `key_stats`
  values; no new unit logic is introduced.
```

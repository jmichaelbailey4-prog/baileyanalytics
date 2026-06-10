# Housing & Real Estate Category Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 5th dashboard category — Housing & Real Estate — 4 lenses / 15 FRED indicators with a new two-sided "market health" status model, and move the 30-year mortgage rate out of Cost of Money into Housing.

**Architecture:** Pure-FRED category reusing the lens pipeline end-to-end (`config.py` lens defs → `refresh_lenses.py --housing` → `data/housing/*.json` → thin `renderLens` pages cloned from the energy pattern). The only new machinery is `narrative.market_health` (two-sided YoY severity) plus five small level-band rules. Spec: `docs/superpowers/specs/2026-06-10-housing-real-estate-design.md`.

**Tech Stack:** Python stdlib only, `unittest`, vanilla HTML/JS pages, GitHub Actions.

**Conventions for every task:**
- Repo root: `C:/Users/jmich/Documents/Business/Repositories/baileyanalytics`. Never `cd`; use `git -C "<repo>"` and absolute paths.
- Test command (all): `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
- Single file: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_narrative_housing.py"`
- Branch: `housing-real-estate` (already created). Commit after each task; **do not push**.
- Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Narrative grammar gotcha: labels are interpolated into sentences — use colon phrasing (`"{label}: up 7%…"`) or labels that read as singular subjects ("The homeownership rate is…"). Never `"{label} have/has…"`.

**File map:**
- Modify: `scripts/lenses/narrative.py` (new rules + HEADLINES), `scripts/lenses/config.py` (housing lenses, CATEGORIES, cost-of-money edit), `scripts/refresh_lenses.py` (`--housing`), `scripts/tests/test_narrative.py` (mortgage bands), `scripts/tests/test_build.py` (cost-of-money 4→3), `dashboards/index.html` (hub section), `dashboards/cost-of-money.html` (foot pointer), `.github/workflows/refresh-fred.yml` (housing step)
- Create: `scripts/tests/test_narrative_housing.py`, `scripts/tests/test_config_housing.py`, `scripts/tests/test_build_housing.py`, `scripts/tests/test_refresh_housing.py`, `scripts/tests/fixtures/housing_sample.json`, `dashboards/housing/{index,home-prices,affordability,supply-construction,rent-shelter}.html`

---

### Task 1: `narrative.market_health` — the two-sided severity factory

**Files:**
- Test: `scripts/tests/test_narrative_housing.py` (create)
- Modify: `scripts/lenses/narrative.py` (append after `generation_share`, before `HEADLINES`)

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_narrative_housing.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def _yoy(prior, latest):
    """Two observations exactly one year apart."""
    return [("2025-01-01", prior), ("2026-01-01", latest)]


class TestMarketHealth(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.market_health("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))

    def test_hot_alert(self):
        text, status = self.rule(_yoy(100.0, 116.0))  # +16%
        self.assertEqual(status, "alert")
        self.assertIn("overheating", text)

    def test_hot_elevated(self):
        _, status = self.rule(_yoy(100.0, 111.0))  # +11%
        self.assertEqual(status, "elevated")

    def test_hot_watch(self):
        _, status = self.rule(_yoy(100.0, 107.0))  # +7%
        self.assertEqual(status, "watch")

    def test_cold_alert(self):
        text, status = self.rule(_yoy(100.0, 89.0))  # -11%
        self.assertEqual(status, "alert")
        self.assertIn("freeze", text)

    def test_cold_elevated(self):
        _, status = self.rule(_yoy(100.0, 94.0))  # -6%
        self.assertEqual(status, "elevated")

    def test_cold_watch(self):
        _, status = self.rule(_yoy(100.0, 97.0))  # -3%
        self.assertEqual(status, "watch")

    def test_steady_is_ok(self):
        text, status = self.rule(_yoy(100.0, 101.0))  # +1%
        self.assertEqual(status, "ok")
        self.assertIn("little changed", text)

    def test_short_history_is_ok_not_crash(self):
        _, status = self.rule([("2026-01-01", 100.0)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([]), ("Data unavailable.", "unknown"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_narrative_housing.py"`
Expected: ERROR ×9 — `AttributeError: module 'lenses.narrative' has no attribute 'market_health'`

- [ ] **Step 3: Implement**

In `scripts/lenses/narrative.py`, after `generation_share` (before `HEADLINES`), add:

```python
# --- Housing & Real Estate rules ---

def market_health(label, hot, cold):
    """Factory: two-sided market-health severity from the trailing-12-month % change.
    `hot` and `cold` are (watch, elevated, alert) YoY-% thresholds — hot positive
    (overheating), cold negative (freezing). Both extremes raise severity."""
    hot_w, hot_e, hot_a = hot
    cold_w, cold_e, cold_a = cold

    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label}: latest reading {v:,.0f}.", "ok")
        pct = (v - prior) / abs(prior) * 100
        if pct >= hot_a:
            return (f"{label}: up {pct:.0f}% from a year ago — overheating.", "alert")
        if pct >= hot_e:
            return (f"{label}: up {pct:.0f}% from a year ago — running hot.", "elevated")
        if pct >= hot_w:
            return (f"{label}: up {pct:.0f}% from a year ago — heating up.", "watch")
        if pct <= cold_a:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — a deep freeze.", "alert")
        if pct <= cold_e:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — cooling sharply.", "elevated")
        if pct <= cold_w:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — cooling.", "watch")
        return (f"{label}: little changed from a year ago ({pct:+.0f}%).", "ok")

    return _rule
```

- [ ] **Step 4: Run to verify pass**

Same command. Expected: `OK` (9 tests).

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_housing.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(narrative): two-sided market_health severity factory

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Housing level-band rules (+ mortgage rule rewrite)

**Files:**
- Test: `scripts/tests/test_narrative_housing.py` (extend), `scripts/tests/test_narrative.py:144-155` (update `TestMortgage`)
- Modify: `scripts/lenses/narrative.py` (`rule_mortgage` rewrite + 4 new rules + 1 info factory)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/tests/test_narrative_housing.py` (before the `__main__` block):

```python
class TestAffordability(unittest.TestCase):
    def test_bands(self):
        cases = [(135.0, "ok"), (115.0, "watch"), (105.6, "elevated"), (90.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_affordability([("2026-05-01", v)])
            self.assertEqual(status, want, f"index {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_affordability([]), ("Data unavailable.", "unknown"))


class TestMortgageDelinquency(unittest.TestCase):
    def test_bands(self):
        cases = [(1.89, "ok"), (2.5, "watch"), (5.0, "elevated"), (9.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_mortgage_delinquency([("2026-01-01", v)])
            self.assertEqual(status, want, f"rate {v}")


class TestMonthsSupply(unittest.TestCase):
    def test_two_sided_bands(self):
        cases = [(2.5, "elevated"), (3.5, "watch"), (5.0, "ok"),
                 (7.0, "watch"), (9.4, "elevated"), (11.0, "alert")]
        for v, want in cases:
            text, status = narrative.rule_months_supply([("2026-04-01", v)])
            self.assertEqual(status, want, f"supply {v}: {text}")

    def test_glut_text_mentions_glut(self):
        text, _ = narrative.rule_months_supply([("2026-04-01", 9.4)])
        self.assertIn("glut", text)


class TestRentalVacancy(unittest.TestCase):
    def test_two_sided_bands(self):
        cases = [(4.5, "elevated"), (5.5, "watch"), (7.3, "ok"),
                 (9.0, "watch"), (11.0, "elevated")]
        for v, want in cases:
            _, status = narrative.rule_rental_vacancy([("2026-01-01", v)])
            self.assertEqual(status, want, f"vacancy {v}")


class TestLevelPoints(unittest.TestCase):
    def test_info_with_direction(self):
        rule = narrative.level_points("The homeownership rate")
        text, status = rule([("2025-01-01", 65.7), ("2026-01-01", 65.3)])
        self.assertEqual(status, "info")
        self.assertIn("65.3%", text)
        self.assertIn("down 0.4 points", text)

    def test_info_steady(self):
        rule = narrative.level_points("The homeownership rate")
        text, status = rule([("2025-01-01", 65.3), ("2026-01-01", 65.3)])
        self.assertEqual(status, "info")
        self.assertIn("little changed", text)
```

In `scripts/tests/test_narrative.py`, replace the `TestMortgage` class (lines 144–155) with the new 4-band expectations:

```python
class TestMortgage(unittest.TestCase):
    def test_punishing_is_alert(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 7.8)])
        self.assertEqual(status, "alert")

    def test_high_is_elevated(self):
        text, status = narrative.rule_mortgage([("2026-06-01", 6.84)])
        self.assertEqual(status, "elevated")
        self.assertIn("stretched", text)

    def test_above_comfort_is_watch(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 5.9)])
        self.assertEqual(status, "watch")

    def test_moderate_is_ok(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 4.2)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_mortgage([]), ("Data unavailable.", "unknown"))
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_narrative*.py"`
Expected: ERRORs (missing `rule_affordability` etc.) + FAILs in `TestMortgage` (6.84 currently "watch").

- [ ] **Step 3: Implement**

In `scripts/lenses/narrative.py`, **replace** the existing `rule_mortgage` (currently a 2-band rule returning "watch" at ≥6.5):

```python
def rule_mortgage(obs):
    """MORTGAGE30US level bands: <5.5 ok, 5.5-6.5 watch, 6.5-7.5 elevated, >=7.5 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 7.5:
        return (f"30-year mortgages are at {v:.2f}% — punishing rates that freeze out most buyers.", "alert")
    if v >= 6.5:
        return (f"30-year mortgages are at {v:.2f}% — high enough to keep affordability stretched.", "elevated")
    if v >= 5.5:
        return (f"30-year mortgages are at {v:.2f}% — above the comfort zone for most budgets.", "watch")
    return (f"30-year mortgages are at {v:.2f}% — moderate by recent standards.", "ok")
```

Then add after `market_health` in the Housing section:

```python
def rule_affordability(obs):
    """FIXHAI: NAR affordability index. 100 = the median family barely qualifies
    for the median home. >=130 ok, 110-130 watch, 95-110 elevated, <95 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 130:
        return (f"The affordability index is {v:.0f} — the median family comfortably affords the median home.", "ok")
    if v >= 110:
        return (f"The affordability index is {v:.0f} — affordable, but with less cushion than usual.", "watch")
    if v >= 95:
        return (f"The affordability index is {v:.0f} — the median family barely qualifies for the median home.", "elevated")
    return (f"The affordability index is {v:.0f} — the median home is out of reach for the median family.", "alert")


def rule_mortgage_delinquency(obs):
    """DRSFRMACBS: % of bank single-family mortgages past due.
    <2 ok, 2-4 watch, 4-7 elevated, >=7 alert (2009 peak ~11)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 2:
        return (f"Just {v:.1f}% of mortgages are delinquent — homeowners are keeping up.", "ok")
    if v < 4:
        return (f"Mortgage delinquencies are at {v:.1f}% — creeping up off their lows.", "watch")
    if v < 7:
        return (f"Mortgage delinquencies have climbed to {v:.1f}% — real homeowner stress.", "elevated")
    return (f"Mortgage delinquencies are at {v:.1f}% — crisis-level homeowner distress.", "alert")


def rule_months_supply(obs):
    """MSACSR: months' supply of new houses. 4-6 balanced; low = tight (hot),
    high = glut (cold). <3 elevated, 3-4 watch, 4-6 ok, 6-8 watch, 8-10 elevated, >10 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 3:
        return (f"Just {v:.1f} months of new-home supply — a tight market that props up prices.", "elevated")
    if v < 4:
        return (f"{v:.1f} months of new-home supply — on the tight side.", "watch")
    if v <= 6:
        return (f"{v:.1f} months of new-home supply — a balanced market.", "ok")
    if v <= 8:
        return (f"{v:.1f} months of new-home supply — inventory is building up.", "watch")
    if v <= 10:
        return (f"{v:.1f} months of new-home supply — a glut that pressures prices and builders.", "elevated")
    return (f"{v:.1f} months of new-home supply — a severe glut.", "alert")


def rule_rental_vacancy(obs):
    """RRVRUSQ156N: rental vacancy %. 6-8 healthy; low = rent pressure (hot),
    high = glut (cold). <5 elevated, 5-6 watch, 6-8 ok, 8-10 watch, >10 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 5:
        return (f"Rental vacancy is just {v:.1f}% — a tight market that pushes rents up.", "elevated")
    if v < 6:
        return (f"Rental vacancy is {v:.1f}% — on the tight side, supporting rent growth.", "watch")
    if v <= 8:
        return (f"Rental vacancy is {v:.1f}% — a healthy balance between renters and landlords.", "ok")
    if v <= 10:
        return (f"Rental vacancy is {v:.1f}% — loosening in renters' favor.", "watch")
    return (f"Rental vacancy is {v:.1f}% — a glut of empty rentals.", "elevated")


def level_points(label):
    """Descriptive `info` for a %-level series: latest value + ~12-month change in
    points. Label must read as a singular subject ("The homeownership rate")."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None:
            return (f"{label} is {v:.1f}%.", "info")
        delta = v - prior
        if delta >= 0.2:
            return (f"{label} is {v:.1f}%, up {delta:.1f} points from a year ago.", "info")
        if delta <= -0.2:
            return (f"{label} is {v:.1f}%, down {abs(delta):.1f} points from a year ago.", "info")
        return (f"{label} is {v:.1f}%, little changed from a year ago.", "info")
    return _rule
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_narrative*.py"`
Expected: `OK`.

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_housing.py scripts/tests/test_narrative.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(narrative): housing level-band rules; mortgage rule to 4 severity bands

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Housing HEADLINES

**Files:**
- Test: `scripts/tests/test_narrative_housing.py` (extend)
- Modify: `scripts/lenses/narrative.py` (`HEADLINES` dict)

- [ ] **Step 1: Write the failing test**

Append to `scripts/tests/test_narrative_housing.py`:

```python
class TestHousingHeadlines(unittest.TestCase):
    LENS_IDS = ["housing-home-prices", "housing-affordability",
                "housing-supply-construction", "housing-rent-shelter"]

    def test_every_lens_has_all_severity_headlines(self):
        for lid in self.LENS_IDS:
            for status in ("alert", "elevated", "watch", "ok", "unknown"):
                self.assertTrue(narrative.HEADLINES.get(lid, {}).get(status),
                                f"missing {lid}/{status}")

    def test_synthesize_aggregates_to_worst(self):
        headline, overall = narrative.synthesize(
            "housing-affordability", ["elevated", "ok", "info", "ok"])
        self.assertEqual(overall, "elevated")
        self.assertTrue(headline)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_narrative_housing.py"`
Expected: FAIL — missing headlines.

- [ ] **Step 3: Implement**

In `narrative.py`, inside `HEADLINES` after the `"energy-commodities"` entry, add:

```python
    "housing-home-prices": {
        "alert": "The housing market is flashing red — prices or sales are at an extreme.",
        "elevated": "The housing market is out of balance — prices and sales are under strain.",
        "watch": "The housing market is shifting — prices or sales are moving off balance.",
        "ok": "The housing market looks balanced — prices and sales are steady.",
        "unknown": "Some home-price data is temporarily unavailable.",
    },
    "housing-affordability": {
        "alert": "Buying a home is out of reach for the typical family.",
        "elevated": "Housing affordability is badly stretched.",
        "watch": "Housing affordability is tightening.",
        "ok": "Housing is broadly affordable for the typical family.",
        "unknown": "Some affordability data is temporarily unavailable.",
    },
    "housing-supply-construction": {
        "alert": "Housing supply is at an extreme — construction or inventory is flashing red.",
        "elevated": "Housing supply is out of balance — inventory or construction is strained.",
        "watch": "Housing supply is shifting — construction and inventory bear watching.",
        "ok": "Housing supply looks healthy — construction and inventory are in balance.",
        "unknown": "Some construction data is temporarily unavailable.",
    },
    "housing-rent-shelter": {
        "alert": "Rents are surging — acute pressure on renters.",
        "elevated": "Rents are rising fast and the rental market is strained.",
        "watch": "Rents are climbing — renters are feeling it.",
        "ok": "The rental market is balanced — rents are behaving.",
        "unknown": "Some rental data is temporarily unavailable.",
    },
```

- [ ] **Step 4: Run to verify pass** — same command, expect `OK`.

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_housing.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(narrative): housing lens headlines

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Housing lenses in `config.py` + the Cost of Money edit

**Files:**
- Test: `scripts/tests/test_config_housing.py` (create), `scripts/tests/test_build.py:78-86` (update)
- Modify: `scripts/lenses/config.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_config_housing.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestHousingConfig(unittest.TestCase):
    def test_four_housing_lenses_in_order(self):
        ids = [l.id for l in config.HOUSING_LENSES]
        self.assertEqual(ids, ["housing-home-prices", "housing-affordability",
                               "housing-supply-construction", "housing-rent-shelter"])

    def test_all_indicators_are_fred(self):
        for lens in config.HOUSING_LENSES:
            for ind in lens.indicators:
                self.assertEqual(ind.source, "fred", ind.id)

    def test_mortgage_rate_lives_only_in_housing(self):
        # the de-dup: MORTGAGE30US must appear exactly once across all categories
        hits = []
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                for ind in lens.indicators:
                    if getattr(ind, "series_id", "") == "MORTGAGE30US":
                        hits.append(lens.id)
        self.assertEqual(hits, ["housing-affordability"])

    def test_cost_of_money_has_three_indicators(self):
        self.assertEqual(len(config.COST_OF_MONEY.indicators), 3)
        ids = [i.id for i in config.COST_OF_MONEY.indicators]
        self.assertNotIn("mortgage-30y", ids)

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "housing")
        self.assertEqual(cat["out"], "housing")
        self.assertEqual(cat["disclaimer"], "")

    def test_each_lens_has_a_severity_driver(self):
        # first indicator of each lens carries the verdict (severity token, not info)
        for lens in config.HOUSING_LENSES:
            first = lens.indicators[0]
            _, status = first.rule([("2025-01-01", 100.0), ("2026-01-01", 100.0)])
            self.assertIn(status, {"ok", "watch", "elevated", "alert"}, lens.id)


if __name__ == "__main__":
    unittest.main()
```

In `scripts/tests/test_build.py`, replace `TestBuildCostOfMoney` (lines 78–86):

```python
class TestBuildCostOfMoney(unittest.TestCase):
    def test_builds_with_three_indicators(self):
        lj = build.build_lens(config.COST_OF_MONEY, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-money")
        self.assertEqual(len(lj["indicators"]), 3)
        self.assertEqual(lj["status"], "watch")  # fed funds 4.33 >= 4.0
        ids = [i["id"] for i in lj["indicators"]]
        self.assertNotIn("yield-curve", ids)
        self.assertNotIn("mortgage-30y", ids)
```

- [ ] **Step 2: Run to verify failure**

Run the full suite. Expected: ERRORs (`config.HOUSING_LENSES` missing) + FAIL (cost-of-money still has 4 indicators).

- [ ] **Step 3: Implement**

In `scripts/lenses/config.py`:

**(a)** Delete the entire `mortgage-30y` Indicator from `COST_OF_MONEY` (the block `Indicator(id="mortgage-30y", … )` at lines ~162–175).

**(b)** Append at the end of the file (after the energy `CATEGORIES.append`):

```python
# --- Housing & Real Estate (FRED) ---

HOUSING_HOME_PRICES = Lens(
    id="housing-home-prices", title="Home Prices", accent="#F472B6",
    indicators=[
        Indicator(
            id="case-shiller", title="Case-Shiller National Home Price Index",
            short="Case-Shiller", unit="", color="#F472B6",
            series_id="CSUSHPINSA", limit=240,
            rule=narrative.market_health("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10)),
            context=("The S&P Case-Shiller national index — the most-watched measure of U.S. "
                     "home prices. Reported with a ~2-month lag."),
        ),
        Indicator(
            id="existing-home-sales", title="Existing-Home Sales · annual rate",
            short="Home sales", unit="", color="#38BDF8",
            series_id="EXHOSLUSM495S", limit=240, value_format="thousands",
            rule=narrative.market_health("Home sales", hot=(10, 20, 30), cold=(-10, -20, -30)),
            context=("How many existing homes are selling, at an annual rate — the market's "
                     "pulse. A collapse in sales is how a housing freeze shows up first."),
        ),
        Indicator(
            id="median-price", title="Median Sales Price of Houses Sold",
            short="Median price", unit="$", color="#34D399",
            series_id="MSPUS", limit=80, value_format="thousands",
            rule=narrative.energy_level("The median sale price"),
            context=("The median price of homes actually sold (quarterly) — a dollars-and-cents "
                     "companion to the Case-Shiller index."),
        ),
    ],
)

HOUSING_AFFORDABILITY = Lens(
    id="housing-affordability", title="Affordability & Financing", accent="#FBBF24",
    indicators=[
        Indicator(
            id="mortgage-rate", title="30-Year Fixed Mortgage Rate",
            short="30-yr mortgage", unit="%", color="#FBBF24",
            series_id="MORTGAGE30US", limit=1040,
            rule=narrative.rule_mortgage,
            context=("The average rate on a 30-year fixed home loan — the single biggest driver "
                     "of what a buyer can afford each month."),
        ),
        Indicator(
            id="affordability-index", title="Housing Affordability Index (NAR)",
            short="Affordability", unit="", color="#F472B6",
            series_id="FIXHAI", limit=240,
            rule=narrative.rule_affordability,
            context=("The National Association of Realtors index: 100 means the median-income "
                     "family can just barely afford the median home. Higher is better — "
                     "the historical norm is 130-180."),
        ),
        Indicator(
            id="debt-service", title="Mortgage Debt Service · % of income",
            short="Debt service", unit="%", color="#38BDF8",
            series_id="MDSP", limit=80,
            rule=narrative.level_points("The mortgage-payment share of disposable income"),
            context=("Mortgage payments as a share of household disposable income (quarterly) — "
                     "how heavy the aggregate mortgage burden actually is."),
        ),
        Indicator(
            id="delinquency", title="Mortgage Delinquency Rate · banks",
            short="Delinquency", unit="%", color="#F87171",
            series_id="DRSFRMACBS", limit=80,
            rule=narrative.rule_mortgage_delinquency,
            context=("The share of single-family mortgages at commercial banks that are past "
                     "due (quarterly) — where affordability stress turns into credit stress."),
        ),
    ],
)

HOUSING_SUPPLY_CONSTRUCTION = Lens(
    id="housing-supply-construction", title="Supply & Construction", accent="#34D399",
    indicators=[
        Indicator(
            id="housing-starts", title="Housing Starts · annual rate",
            short="Starts", unit="", color="#34D399",
            series_id="HOUST", limit=240, value_format="thousands",
            rule=narrative.market_health("Homebuilding", hot=(20, 35, 50), cold=(-10, -20, -35)),
            context=("New homes started each month, in thousands at an annual rate — the "
                     "construction industry's output, and a classic leading indicator."),
        ),
        Indicator(
            id="building-permits", title="Building Permits · annual rate",
            short="Permits", unit="", color="#A78BFA",
            series_id="PERMIT", limit=240, value_format="thousands",
            rule=narrative.market_health("Permitting", hot=(20, 35, 50), cold=(-10, -20, -35)),
            context=("Permits pulled for new housing units — the step before starts, so it "
                     "leads the rest of the construction pipeline."),
        ),
        Indicator(
            id="months-supply", title="Months' Supply of New Houses",
            short="Months' supply", unit="mo", color="#FBBF24",
            series_id="MSACSR", limit=240,
            rule=narrative.rule_months_supply,
            context=("How long it would take to sell every new home on the market at the "
                     "current sales pace. Roughly 4-6 months is balanced; more is a glut, "
                     "less is a squeeze."),
        ),
        Indicator(
            id="active-listings", title="Active Listings (Realtor.com)",
            short="Listings", unit="", color="#38BDF8",
            series_id="ACTLISCOUUS", limit=240, value_format="thousands",
            rule=narrative.energy_level("Active listings"),
            context=("Homes listed for sale nationwide (Realtor.com count, since 2016) — "
                     "the inventory buyers actually get to choose from."),
        ),
    ],
)

HOUSING_RENT_SHELTER = Lens(
    id="housing-rent-shelter", title="Rent & Shelter", accent="#A78BFA",
    indicators=[
        Indicator(
            id="rent-cpi", title="CPI: Rent of Primary Residence",
            short="Rent CPI", unit="", color="#A78BFA",
            series_id="CUSR0000SEHA", limit=240,
            rule=narrative.consumer_cost("Rent", 4, 6, 9),
            context=("The rent component of the Consumer Price Index — what tenants actually "
                     "pay. It moves slowly but relentlessly, and it is a third of core CPI."),
        ),
        Indicator(
            id="owners-equivalent-rent", title="CPI: Owners' Equivalent Rent",
            short="OER", unit="", color="#38BDF8",
            series_id="CUSR0000SEHC", limit=240,
            rule=narrative.energy_level("Owners' equivalent rent"),
            context=("What homeowners would pay to rent their own homes — the largest single "
                     "component of the CPI, and the bridge between home prices and inflation."),
        ),
        Indicator(
            id="rental-vacancy", title="Rental Vacancy Rate",
            short="Vacancy", unit="%", color="#34D399",
            series_id="RRVRUSQ156N", limit=80,
            rule=narrative.rule_rental_vacancy,
            context=("The share of rental units sitting empty (quarterly). Low vacancy gives "
                     "landlords pricing power; high vacancy hands it back to renters."),
        ),
        Indicator(
            id="homeownership", title="Homeownership Rate",
            short="Ownership", unit="%", color="#F472B6",
            series_id="RHORUSQ156N", limit=80,
            rule=narrative.level_points("The homeownership rate"),
            context=("The share of households that own their home (quarterly) — the long arc "
                     "of whether owning is gaining or losing ground versus renting."),
        ),
    ],
)

HOUSING_LENSES = [HOUSING_HOME_PRICES, HOUSING_AFFORDABILITY,
                  HOUSING_SUPPLY_CONSTRUCTION, HOUSING_RENT_SHELTER]

CATEGORIES.append(
    {"id": "housing", "title": "Housing & Real Estate", "lenses": HOUSING_LENSES,
     "out": "housing", "back": "Housing & Real Estate",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed", "disclaimer": ""}
)
```

- [ ] **Step 4: Run the full suite to verify pass**

Run the full-suite command. Expected: `OK` (note: `test_build.py` cost-of-money fixture already lacks nothing — `MORTGAGE30US:lin` in `fetched_sample.json` simply goes unused).

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_housing.py scripts/tests/test_build.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(config): housing lenses + category; move mortgage rate out of cost-of-money

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Housing fixture + build tests

**Files:**
- Create: `scripts/tests/fixtures/housing_sample.json`, `scripts/tests/test_build_housing.py`

- [ ] **Step 1: Create the fixture**

All series use uniform `2025-01-01` → `2026-01-01` dates so `_value_year_ago` resolves (the Energy fixture lesson). Values are chosen to exercise specific bands (noted inline below — JSON has no comments, so don't copy the annotations):

Create `scripts/tests/fixtures/housing_sample.json`:

```json
{
  "CSUSHPINSA:lin": [
    {"date": "2025-01-01", "value": "300.0"},
    {"date": "2026-01-01", "value": "330.0"}
  ],
  "EXHOSLUSM495S:lin": [
    {"date": "2025-01-01", "value": "4000000"},
    {"date": "2026-01-01", "value": "4170000"}
  ],
  "MSPUS:lin": [
    {"date": "2025-01-01", "value": "400000"},
    {"date": "2026-01-01", "value": "403200"}
  ],
  "MORTGAGE30US:lin": [
    {"date": "2025-01-01", "value": "6.70"},
    {"date": "2026-01-01", "value": "6.84"}
  ],
  "FIXHAI:lin": [
    {"date": "2025-01-01", "value": "108.0"},
    {"date": "2026-01-01", "value": "105.6"}
  ],
  "MDSP:lin": [
    {"date": "2025-01-01", "value": "5.80"},
    {"date": "2026-01-01", "value": "5.92"}
  ],
  "DRSFRMACBS:lin": [
    {"date": "2025-01-01", "value": "1.80"},
    {"date": "2026-01-01", "value": "1.89"}
  ],
  "HOUST:lin": [
    {"date": "2025-01-01", "value": "1500"},
    {"date": "2026-01-01", "value": "1465"}
  ],
  "PERMIT:lin": [
    {"date": "2025-01-01", "value": "1500"},
    {"date": "2026-01-01", "value": "1423"}
  ],
  "MSACSR:lin": [
    {"date": "2025-01-01", "value": "8.7"},
    {"date": "2026-01-01", "value": "9.4"}
  ],
  "ACTLISCOUUS:lin": [
    {"date": "2025-01-01", "value": "950000"},
    {"date": "2026-01-01", "value": "1058693"}
  ],
  "CUSR0000SEHA:lin": [
    {"date": "2025-01-01", "value": "428.0"},
    {"date": "2026-01-01", "value": "446.7"}
  ],
  "CUSR0000SEHC:lin": [
    {"date": "2025-01-01", "value": "430.0"},
    {"date": "2026-01-01", "value": "440.7"}
  ],
  "RRVRUSQ156N:lin": [
    {"date": "2025-01-01", "value": "7.2"},
    {"date": "2026-01-01", "value": "7.3"}
  ],
  "RHORUSQ156N:lin": [
    {"date": "2025-01-01", "value": "65.7"},
    {"date": "2026-01-01", "value": "65.3"}
  ],
  "USREC:lin": [
    {"date": "2025-01-01", "value": "0"},
    {"date": "2026-01-01", "value": "0"}
  ]
}
```

Band targets: Case-Shiller +10% → elevated (hot); home sales +4.25% → ok; mortgage 6.84 → elevated; FIXHAI 105.6 → elevated; delinquency 1.89 → ok; starts −2.3% → ok; permits −5.1% → ok; months' supply 9.4 → elevated (glut); rent CPI +4.4% → watch; vacancy 7.3 → ok.

- [ ] **Step 2: Write the failing tests**

Create `scripts/tests/test_build_housing.py`:

```python
import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "housing_sample.json"


def _fetched():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestBuildHousing(unittest.TestCase):
    def test_all_four_lenses_build(self):
        jsons = [build.build_lens(l, _fetched()) for l in config.HOUSING_LENSES]
        self.assertEqual([j["id"] for j in jsons],
                         ["housing-home-prices", "housing-affordability",
                          "housing-supply-construction", "housing-rent-shelter"])

    def test_home_prices_badge_is_elevated_hot(self):
        lj = build.build_lens(config.HOUSING_HOME_PRICES, _fetched())
        cs = next(i for i in lj["indicators"] if i["id"] == "case-shiller")
        self.assertEqual(cs["signal_status"], "elevated")  # +10% YoY, hot band
        self.assertEqual(lj["status"], "elevated")

    def test_affordability_badge_from_drivers(self):
        lj = build.build_lens(config.HOUSING_AFFORDABILITY, _fetched())
        self.assertEqual(lj["status"], "elevated")  # mortgage 6.84 + FIXHAI 105.6
        ds = next(i for i in lj["indicators"] if i["id"] == "debt-service")
        self.assertEqual(ds["signal_status"], "info")  # info ignored by status_max

    def test_supply_glut_is_elevated(self):
        lj = build.build_lens(config.HOUSING_SUPPLY_CONSTRUCTION, _fetched())
        ms = next(i for i in lj["indicators"] if i["id"] == "months-supply")
        self.assertEqual(ms["signal_status"], "elevated")  # 9.4 months = glut

    def test_rent_shelter_watch_from_rent_cpi(self):
        lj = build.build_lens(config.HOUSING_RENT_SHELTER, _fetched())
        self.assertEqual(lj["status"], "watch")  # rent +4.4% YoY


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_build_housing.py"`
Expected: `OK` if Tasks 1–4 are correct (this task's tests pin the fixture↔band contract; if any fail, fix the fixture value or the band — the annotations above say which band each value targets).

- [ ] **Step 4: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/fixtures/housing_sample.json scripts/tests/test_build_housing.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(housing): fixture + lens build tests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: `refresh_lenses.py --housing`

**Files:**
- Test: `scripts/tests/test_refresh_housing.py` (create)
- Modify: `scripts/refresh_lenses.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/tests/test_refresh_housing.py`:

```python
import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestHousingDryRun(unittest.TestCase):
    def test_housing_flag_runs_dry_into_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.HOUSING_OUT_DIR
            refresh_lenses.HOUSING_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--housing", "--dry-run"])
            finally:
                refresh_lenses.HOUSING_OUT_DIR = orig
            self.assertEqual(rc, 0)
            for name in ("housing-home-prices.json", "housing-affordability.json",
                         "housing-supply-construction.json", "housing-rent-shelter.json",
                         "index.json"):
                self.assertTrue((tmp / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_refresh_housing.py"`
Expected: ERROR — `AttributeError: module 'refresh_lenses' has no attribute 'HOUSING_OUT_DIR'`

- [ ] **Step 3: Implement**

In `scripts/refresh_lenses.py`:

**(a)** After `ENERGY_OUT_DIR = …` add:

```python
HOUSING_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "housing"
```

**(b)** After `ENERGY_FIXTURE = …` add:

```python
HOUSING_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "housing_sample.json"
```

**(c)** After `refresh_energy` add (mirrors `refresh_economic` — pure FRED, no injection):

```python
def refresh_housing(dry_run):
    """Build + write the housing (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    if dry_run:
        fetched = json.loads(HOUSING_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.HOUSING_LENSES, api_key)

    ready = [lens for lens in config.HOUSING_LENSES if lens_ready(lens, failed)]
    for lens in config.HOUSING_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No housing lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  HOUSING_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all housing data up to date.")
    return 0
```

**(d)** In `main()`: add the flag after `--energy`:

```python
    parser.add_argument("--housing", action="store_true", help="refresh only the housing lenses")
```

change the `any_flag` line to:

```python
    any_flag = args.economic or args.banking or args.markets or args.energy or args.housing
```

add after `do_energy = …`:

```python
    do_housing = args.housing or not any_flag
```

and add after the `do_energy` block (before `do_banking`):

```python
    if do_housing:
        hc = refresh_housing(args.dry_run)
        if hc:
            code = hc
```

- [ ] **Step 4: Run the full suite to verify pass** — full-suite command, expect `OK`.

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_refresh_housing.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(refresh): --housing flag and housing lens refresh

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Pages — housing hub, 4 lens pages, dashboards index, cost-of-money pointer

**Files:**
- Create: `dashboards/housing/index.html`, `dashboards/housing/home-prices.html`, `dashboards/housing/affordability.html`, `dashboards/housing/supply-construction.html`, `dashboards/housing/rent-shelter.html`
- Modify: `dashboards/index.html`, `dashboards/cost-of-money.html`

No JS unit tests exist for pages; verification is a syntax check + the local-serve review in Task 9.

- [ ] **Step 1: Create the housing hub**

Create `dashboards/housing/index.html` as an exact copy of `dashboards/energy/index.html` with these substitutions:
- `<title>`: `Housing &amp; Real Estate — Bailey Analytics`
- `<meta name="description" content="The U.S. housing market in plain English — home prices and sales, affordability, construction and inventory, and rents. Built from FRED data.">`
- `<h1>`: `Housing &amp; Real Estate`
- `p.lede`: `Where housing actually stands — what homes cost and how fast they're selling, whether a typical family can afford to buy, how much is being built, and what's happening to rents. <strong>Open any lens</strong> for interactive charts and the context behind each number.`
- `.foot`: `Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a>, St. Louis Fed. Public data, refreshed daily.`
- `SLUGS`:

```js
    const SLUGS = {
      "housing-home-prices": "home-prices",
      "housing-affordability": "affordability",
      "housing-supply-construction": "supply-construction",
      "housing-rent-shelter": "rent-shelter"
    };
```

- fetch URL: `/data/housing/index.json`; card href prefix: `/dashboards/housing/`

- [ ] **Step 2: Create the 4 lens pages**

Each is the thin wrapper pattern (copy of `dashboards/energy/oil-fuels.html` shape). Common: stylesheet/scripts identical; `back: "Housing & Real Estate"`, `href: "/dashboards/housing/"`, foot crediting FRED:

```js
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
```

| File | `<title>` | meta description | renderLens URL |
|---|---|---|---|
| `home-prices.html` | `Home Prices — Bailey Analytics` | `Is the U.S. housing market overheating or freezing? Case-Shiller home prices, existing-home sales, and the median sale price, in plain English.` | `/data/housing/housing-home-prices.json` |
| `affordability.html` | `Affordability &amp; Financing — Bailey Analytics` | `Can a typical family afford to buy? Mortgage rates, the NAR affordability index, the mortgage burden on incomes, and delinquencies.` | `/data/housing/housing-affordability.json` |
| `supply-construction.html` | `Supply &amp; Construction — Bailey Analytics` | `How much housing America is building and how much is for sale — starts, permits, months' supply, and active listings.` | `/data/housing/housing-supply-construction.json` |
| `rent-shelter.html` | `Rent &amp; Shelter — Bailey Analytics` | `What's happening to the cost of a roof — rent inflation, owners' equivalent rent, rental vacancy, and homeownership.` | `/data/housing/housing-rent-shelter.json` |

Full example (`home-prices.html`; the other three differ only in the table fields above):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Home Prices — Bailey Analytics</title>
  <meta name="description" content="Is the U.S. housing market overheating or freezing? Case-Shiller home prices, existing-home sales, and the median sale price, in plain English.">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading&hellip;</div></main>
  <script src="/dashboards/lens.js"></script>
  <script>
    renderLens("/data/housing/housing-home-prices.json", {
      back: "Housing & Real Estate",
      href: "/dashboards/housing/",
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
    });
  </script>
</body>
</html>
```

(Housing data is mostly monthly, so the site-wide 1Y default applies — do **not** pass `defaultRange`.)

- [ ] **Step 3: Add the housing section to `dashboards/index.html`**

After the Energy `hub-grid` div (line ~53), add:

```html
    <h2 class="cat-head"><span class="dot" style="background:#F472B6"></span>Housing &amp; Real Estate</h2>
    <p class="cat-sub">The housing market — home prices and sales, affordability, construction and inventory, and rents. Refreshed daily from FRED. <a href="/dashboards/housing/" style="color:var(--blue);text-decoration:none">Overview &rarr;</a></p>
    <div class="hub-grid" id="housing-grid"><div class="status-msg">Loading&hellip;</div></div>
```

And after the `ENERGY_SLUGS` `loadGrid` call in the script, add:

```js
    const HOUSING_SLUGS = {
      "housing-home-prices": "home-prices",
      "housing-affordability": "affordability",
      "housing-supply-construction": "supply-construction",
      "housing-rent-shelter": "rent-shelter"
    };
    loadGrid("/data/housing/index.json", "housing-grid",
             id => `/dashboards/housing/${encodeURIComponent(HOUSING_SLUGS[id] || id)}.html`);
```

- [ ] **Step 4: Point Cost of Money readers at Housing**

In `dashboards/cost-of-money.html`:
- meta description → `What it costs to borrow in the U.S. — the Fed funds rate and Treasury yields, from FRED.`
- replace `<script>renderLens("/data/lenses/cost-of-money.json");</script>` with:

```html
  <script>
    renderLens("/data/lenses/cost-of-money.json", {
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set. Mortgage rates now live in <a href="/dashboards/housing/affordability.html">Housing &rarr; Affordability &amp; Financing</a>.'
    });
  </script>
```

- [ ] **Step 5: Syntax-check the inline JS**

Run (PowerShell): `node --check "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/dashboards/lens.js"`
(For the HTML pages, eyeball the `<script>` blocks — they are tiny. `node --check` only validates `.js` files.)
Expected: no output (pass).

- [ ] **Step 6: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/housing dashboards/index.html dashboards/cost-of-money.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(pages): housing hub + lens pages; cost-of-money pointer to housing

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Daily workflow step

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`

- [ ] **Step 1: Add the housing step**

After the energy step (line ~41), insert:

```yaml
      - name: Fetch latest housing data (FRED)
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python scripts/refresh_lenses.py --housing
```

- [ ] **Step 2: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add .github/workflows/refresh-fred.yml
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "ci: refresh housing lenses daily

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Live build, badge sanity-check, local review

- [ ] **Step 1: Full test suite**

Run the full-suite command. Expected: `OK`, ~205 tests (184 prior + ~21 new).

- [ ] **Step 2: Live data build** (FRED_API_KEY is in the session env)

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --economic --housing`
Expected: writes `data/housing/*.json` (5 files) and rewrites `data/lenses/cost-of-money.json` (mortgage indicator gone). **Do not use `--dry-run`** — it would overwrite real data with fixtures.

- [ ] **Step 3: Sanity-check badges against the spec's expectations**

Read each `data/housing/*.json` `status` + indicator `signal_status`/`signal_text`. Expected with current data: affordability index ~105.6 → elevated; months' supply ~9.4 → elevated (glut); delinquency ~1.9 → ok; vacancy ~7.3 → ok; mortgage rate per its level. If a badge contradicts the data's plain-English meaning, adjust the band in `narrative.py`, update the matching test, re-run the suite, and note the change.

- [ ] **Step 4: Serve locally for Michael's review**

Run in background: `python -m http.server 8000` (cwd `baileyanalytics/`), then check `http://localhost:8000/dashboards/housing/` and the four lens pages + `http://localhost:8000/dashboards/` (housing section) + cost-of-money (3 charts + footer pointer).

- [ ] **Step 5: Commit the data**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add data/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "data(housing): initial live build; cost-of-money without mortgage rate

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then stop — Michael reviews locally before any merge/push (deploying = pushing `main`).

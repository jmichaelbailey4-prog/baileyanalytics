# Energy & Commodities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth dashboard category — Energy & Commodities — driven by a new EIA API source (lenses 1–3) plus FRED (commodities), reusing the existing lens framework.

**Architecture:** A new `eia.py` fetcher mirrors `fred.py` and returns the same `[{date,value}]` shape, so `build.build_lens` is reused unchanged. EIA indicators carry routing fields and `source="eia"`; `refresh_energy` fetches FRED (commodities) + injects EIA series + computes generation shares, exactly paralleling `refresh_markets`. Consumer-cost severity rules drive lens badges; physical `info` indicators inform but don't.

**Tech Stack:** Standard-library Python 3, `unittest`. No third-party deps. Vanilla HTML/CSS/JS pages reusing `lens.js`/`lens.css`.

**Spec:** `docs/superpowers/specs/2026-06-09-energy-commodities-design.md`

**Conventions:**
- Run from the parent dir with absolute paths (repo is `baileyanalytics/`).
- Full suite:
  ```
  python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
  ```
- A single test file runs directly (each test does `sys.path.insert`):
  ```
  python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_eia.py"
  ```
- Commit on the `feature/energy-commodities` branch only. **Do not push or deploy.** End each commit message with:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
- **No live build** in this plan — there is no `EIA_API_KEY` in the environment. Everything is verified via fixtures + `--dry-run`. The live build, threshold calibration, and EIA route verification happen when the owner provides the key.
- **Never** run `refresh_lenses.py --dry-run` outside a patched temp dir — it overwrites tracked `data/`.

---

### Task 1: EIA fetcher + share helper

**Files:**
- Create: `scripts/lenses/eia.py`
- Modify: `scripts/lenses/util.py` (add `pct_share`)
- Test: `scripts/tests/test_eia.py`, `scripts/tests/test_util.py`

- [ ] **Step 1: Write the failing test for `pct_share`**

Add to `scripts/tests/test_util.py` inside a new test class:

```python
class TestPctShare(unittest.TestCase):
    def test_matched_dates_only_and_rounded(self):
        num = [{"date": "2026-01", "value": "30"}, {"date": "2026-02", "value": "40"}]
        den = [{"date": "2026-01", "value": "120"}, {"date": "2026-03", "value": "200"}]
        # only 2026-01 is in both: 30/120 = 25.0%
        self.assertEqual(util.pct_share(num, den), [{"date": "2026-01", "value": "25.0"}])

    def test_skips_zero_denominator(self):
        self.assertEqual(util.pct_share([{"date": "d", "value": "5"}],
                                        [{"date": "d", "value": "0"}]), [])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_util.py"`
Expected: FAIL — `AttributeError: module 'lenses.util' has no attribute 'pct_share'`.

- [ ] **Step 3: Implement `pct_share` in `util.py`**

Append to `scripts/lenses/util.py`:

```python
def pct_share(numerator, denominator):
    """Percent share (numerator / denominator * 100) on dates present in both.

    Inputs are [{'date','value'}] (values numeric or numeric strings). Returns
    [{'date','value'}] with the share rounded to 1 dp as a string, sorted by date.
    Skips dates where the denominator is missing or zero.
    """
    den = {p["date"]: to_float(p["value"]) for p in (denominator or [])}
    out = []
    for p in (numerator or []):
        d = den.get(p["date"])
        n = to_float(p["value"])
        if n is not None and d:
            out.append({"date": p["date"], "value": f"{n / d * 100:.1f}"})
    return sorted(out, key=lambda r: r["date"])
```

- [ ] **Step 4: Run it to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_util.py"`
Expected: PASS.

- [ ] **Step 5: Write the failing test for the EIA fetcher**

Create `scripts/tests/test_eia.py`:

```python
import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import eia


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# EIA returns newest-first; one row has a null value to be dropped.
PAYLOAD = {
    "response": {
        "data": [
            {"period": "2026-03-06", "value": 3.25},
            {"period": "2026-02-27", "value": None},
            {"period": "2026-02-20", "value": 3.10},
        ]
    }
}


class TestFetchSeries(unittest.TestCase):
    def test_parses_oldest_first_and_drops_nulls(self):
        fake = FakeResponse(json.dumps(PAYLOAD).encode())
        with mock.patch("lenses.eia.urllib.request.urlopen", return_value=fake) as m:
            rows = eia.fetch_series("petroleum/pri/gnd",
                                    [("series", "EMM_EPMR_PTE_NUS_DPG")],
                                    "weekly", "KEY", length=10)
        self.assertEqual(rows, [
            {"date": "2026-02-20", "value": "3.1"},
            {"date": "2026-03-06", "value": "3.25"},
        ])
        called_url = m.call_args.args[0]
        self.assertIn("petroleum/pri/gnd/data/", called_url)
        self.assertIn("api_key=KEY", called_url)
        self.assertIn("frequency=weekly", called_url)

    def test_custom_data_column(self):
        payload = {"response": {"data": [{"period": "2026-01", "price": 12.5}]}}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.eia.urllib.request.urlopen", return_value=fake):
            rows = eia.fetch_series("electricity/retail-sales", [("sectorid", "RES")],
                                    "monthly", "KEY", data_col="price")
        self.assertEqual(rows, [{"date": "2026-01", "value": "12.5"}])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 6: Run it to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_eia.py"`
Expected: FAIL — `ModuleNotFoundError: No module named 'lenses.eia'`.

- [ ] **Step 7: Implement `eia.py`**

Create `scripts/lenses/eia.py`:

```python
"""EIA API v2 access — energy data (the physical economy). Mirrors fred.py.

Returns the same oldest-first [{'date','value'}] shape FRED returns, so the
existing build pipeline consumes it unchanged. Only this module (plus fred /
fdic / coingecko / yahoo) touches the network. Values are stored as strings to
match FRED's convention; display precision is handled by each indicator's
value_format.
"""

import json
import urllib.parse
import urllib.request

BASE = "https://api.eia.gov/v2"

# Net-generation dataset (monthly, all-sector) used for the electricity mix.
# fueltypeid facets: ALL = total, REN = renewables, NG = natural gas.
_GEN_ROUTE = "electricity/electric-power-operational-data"
_GEN_FACETS = {"total": "ALL", "renewable": "REN", "natgas": "NG"}
_GEN_COL = "generation"


def fetch_series(route, facets, frequency, api_key, length=520, data_col="value", timeout=20):
    """Fetch one EIA v2 series as oldest-first [{'date','value'}].

    facets: iterable of (key, value) -> facets[key][]=value. Values are kept as
    strings (str()) to match FRED; null values are dropped.
    """
    params = [
        ("api_key", api_key),
        ("frequency", frequency),
        ("data[0]", data_col),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", length),
    ]
    for k, v in facets:
        params.append((f"facets[{k}][]", v))
    url = f"{BASE}/{route}/data/?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    rows = payload.get("response", {}).get("data", [])
    out = []
    for r in rows:
        val = r.get(data_col)
        if val is None:
            continue
        out.append({"date": r["period"], "value": str(val)})
    out.reverse()  # API returns newest-first
    return out


def generation_mix(api_key, timeout=20):
    """Fetch monthly net generation for total / renewable / natural-gas as a dict
    of oldest-first [{'date','value'}] series. The caller computes shares."""
    out = {}
    for name, fuel in _GEN_FACETS.items():
        out[name] = fetch_series(
            _GEN_ROUTE,
            [("fueltypeid", fuel), ("location", "US"), ("sectorid", "99")],
            "monthly", api_key, length=240, data_col=_GEN_COL, timeout=timeout)
    return out
```

- [ ] **Step 8: Run both test files to verify they pass**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_eia.py"
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_util.py"
```
Expected: PASS for both.

- [ ] **Step 9: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/eia.py scripts/lenses/util.py scripts/tests/test_eia.py scripts/tests/test_util.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(energy): EIA v2 fetcher + pct_share helper

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Indicator EIA fields + narrative rules

**Files:**
- Modify: `scripts/lenses/config.py` (Indicator dataclass, ~lines 13-31)
- Modify: `scripts/lenses/narrative.py` (new rules + HEADLINES)
- Test: `scripts/tests/test_narrative_energy.py`

- [ ] **Step 1: Add EIA routing fields to the `Indicator` dataclass**

In `scripts/lenses/config.py`, extend the dataclass (after the `source` field) and update the `source` comment:

```python
    source: str = "fred"  # "fred" | "yahoo" | "eia" (non-FRED sources are injected by refresh_*)
    eia_route: str = ""             # EIA v2 route, e.g. "petroleum/pri/gnd" (empty = computed/injected)
    eia_facets: tuple = ()          # ((key, value), ...) -> facets[key][]=value
    eia_freq: str = ""              # "daily" | "weekly" | "monthly"
    eia_col: str = "value"          # data column to request/read
```

This is additive — existing FRED/Yahoo indicators keep their defaults. Run the
full suite to confirm nothing breaks:
```
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```
Expected: OK (still 157).

- [ ] **Step 2: Write the failing narrative test**

Create `scripts/tests/test_narrative_energy.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def yr(a, b):
    """Two points a year apart so the YoY helper resolves a prior value."""
    return [("2025-01-01", a), ("2026-01-01", b)]


class TestConsumerCost(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.consumer_cost("Gasoline", 10, 25, 40)

    def test_falling_is_ok(self):
        self.assertEqual(self.rule(yr(4.00, 3.50))[1], "ok")

    def test_small_rise_is_ok(self):
        self.assertEqual(self.rule(yr(4.00, 4.20))[1], "ok")   # +5%

    def test_watch_band(self):
        self.assertEqual(self.rule(yr(4.00, 4.60))[1], "watch")  # +15%

    def test_elevated_band(self):
        self.assertEqual(self.rule(yr(4.00, 5.20))[1], "elevated")  # +30%

    def test_alert_band(self):
        self.assertEqual(self.rule(yr(4.00, 6.00))[1], "alert")   # +50%

    def test_no_baseline_is_ok(self):
        self.assertEqual(self.rule([("2026-01-01", 4.00)])[1], "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([])[1], "unknown")


class TestInfoRules(unittest.TestCase):
    def test_energy_level_is_info(self):
        text, status = narrative.energy_level("Crude inventories")(yr(400.0, 430.0))
        self.assertEqual(status, "info")
        self.assertIn("Crude inventories", text)

    def test_generation_share_is_info(self):
        text, status = narrative.generation_share("Renewables")(yr(20.0, 24.0))
        self.assertEqual(status, "info")
        self.assertIn("%", text)


class TestEnergySynthesis(unittest.TestCase):
    def test_info_ignored_price_severity_drives_badge(self):
        # one price severity (elevated) + physical info -> lens reads elevated
        headline, overall = narrative.synthesize("energy-oil-fuels",
                                                 ["elevated", "info", "info"])
        self.assertEqual(overall, "elevated")
        self.assertTrue(headline)

    def test_all_info_is_unknown(self):
        _, overall = narrative.synthesize("energy-electricity", ["info", "info"])
        self.assertEqual(overall, "unknown")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_energy.py"`
Expected: FAIL — `AttributeError: module 'lenses.narrative' has no attribute 'consumer_cost'`.

- [ ] **Step 4: Implement the rules in `narrative.py`**

Add to `scripts/lenses/narrative.py` (after the markets rules, before `HEADLINES`):

```python
# --- Energy & Commodities rules ---

def consumer_cost(label, watch, elevated, alert):
    """Factory: consumer-cost severity from trailing-12-month % change. Rising fast
    means household stress; falling/flat is ok. Thresholds are YoY-% bands."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.2f}.", "ok")
        pct = (v - prior) / abs(prior) * 100
        if pct >= alert:
            return (f"{label} costs have surged {pct:.0f}% over the past year — acute pressure on households.", "alert")
        if pct >= elevated:
            return (f"{label} costs are up {pct:.0f}% over the past year — a real squeeze.", "elevated")
        if pct >= watch:
            return (f"{label} costs are up {pct:.0f}% over the past year — climbing.", "watch")
        if pct <= -watch:
            return (f"{label} costs have fallen {abs(pct):.0f}% over the past year — relief for households.", "ok")
        return (f"{label} costs are roughly flat over the past year.", "ok")
    return _rule


def energy_level(label):
    """Descriptive `info`: latest level + trailing-12-month direction. No verdict."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.0f}.", "info")
        pct = (v - prior) / abs(prior) * 100
        if pct >= 3:
            return (f"{label} is up {pct:.0f}% from a year ago, now {v:,.0f}.", "info")
        if pct <= -3:
            return (f"{label} is down {abs(pct):.0f}% from a year ago, now {v:,.0f}.", "info")
        return (f"{label} is little changed from a year ago, now {v:,.0f}.", "info")
    return _rule


def generation_share(label):
    """Descriptive `info` for an electricity generation share (%) + its direction."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None:
            return (f"{label} make up {v:.1f}% of electricity generation.", "info")
        delta = v - prior
        if delta >= 0.5:
            return (f"{label} have risen to {v:.1f}% of electricity generation (up {delta:.1f} points in a year).", "info")
        if delta <= -0.5:
            return (f"{label} have slipped to {v:.1f}% of electricity generation (down {abs(delta):.1f} points in a year).", "info")
        return (f"{label} hold steady at {v:.1f}% of electricity generation.", "info")
    return _rule
```

- [ ] **Step 5: Add HEADLINES entries**

In `scripts/lenses/narrative.py`, add these four entries inside the `HEADLINES`
dict (alongside the existing market entries):

```python
    "energy-oil-fuels": {
        "alert": "Fuel costs are spiking — acute pressure at the pump.",
        "elevated": "Fuel costs are well above last year.",
        "watch": "Fuel costs are climbing.",
        "ok": "Fuel costs are stable or easing.",
        "unknown": "Some fuel data is temporarily unavailable.",
    },
    "energy-natural-gas": {
        "alert": "Natural gas costs are spiking.",
        "elevated": "Natural gas is well above last year.",
        "watch": "Natural gas costs are climbing.",
        "ok": "Natural gas costs are stable or easing.",
        "unknown": "Some natural-gas data is temporarily unavailable.",
    },
    "energy-electricity": {
        "alert": "Power bills are spiking.",
        "elevated": "Electricity prices are well above last year.",
        "watch": "Electricity prices are climbing.",
        "ok": "Power bills are steady.",
        "unknown": "Some electricity data is temporarily unavailable.",
    },
    "energy-commodities": {
        "alert": "Commodity costs are surging.",
        "elevated": "Commodity and food costs are well above last year.",
        "watch": "Commodity costs are climbing.",
        "ok": "Commodity costs are stable or easing.",
        "unknown": "Some commodity data is temporarily unavailable.",
    },
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_energy.py"`
Expected: PASS.

- [ ] **Step 7: Run the full suite**

Run the discover command. Expected: OK.

- [ ] **Step 8: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/lenses/narrative.py scripts/tests/test_narrative_energy.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(energy): consumer-cost + info narrative rules, Indicator EIA fields

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Energy lens config + category registration

**Files:**
- Modify: `scripts/lenses/config.py` (add lenses + CATEGORIES append, after the markets block)
- Test: `scripts/tests/test_config_energy.py`

- [ ] **Step 1: Write the failing config test**

Create `scripts/tests/test_config_energy.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestEnergyConfig(unittest.TestCase):
    def test_four_energy_lenses_in_order(self):
        ids = [l.id for l in config.ENERGY_LENSES]
        self.assertEqual(ids, ["energy-oil-fuels", "energy-natural-gas",
                               "energy-electricity", "energy-commodities"])

    def test_eia_lenses_have_routes_or_computed(self):
        for lid in ("energy-oil-fuels", "energy-natural-gas", "energy-electricity"):
            lens = next(l for l in config.ENERGY_LENSES if l.id == lid)
            for ind in lens.indicators:
                self.assertEqual(ind.source, "eia")
            # at least one directly-fetched (routed) EIA indicator per lens
            self.assertTrue(any(ind.eia_route for ind in lens.indicators))

    def test_commodities_lens_is_fred(self):
        lens = next(l for l in config.ENERGY_LENSES if l.id == "energy-commodities")
        self.assertTrue(all(ind.source == "fred" for ind in lens.indicators))
        self.assertIn("PFOODINDEXM", {i.series_id for i in lens.indicators})

    def test_each_lens_has_a_severity_price_indicator(self):
        # the first indicator of each lens is the consumer-cost (severity) driver
        for lens in config.ENERGY_LENSES:
            first = lens.indicators[0]
            _, status = first.rule([("2025-01-01", 100.0), ("2026-01-01", 100.0)])
            self.assertIn(status, {"ok", "watch", "elevated", "alert"})

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "energy")
        self.assertEqual(cat["out"], "energy")
        self.assertEqual(cat["disclaimer"], "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_energy.py"`
Expected: FAIL — `AttributeError: module 'lenses.config' has no attribute 'ENERGY_LENSES'`.

- [ ] **Step 3: Add the four lenses + category**

In `scripts/lenses/config.py`, after the markets `CATEGORIES.append(...)` block
(end of file), add:

```python
# --- Energy & Commodities (EIA + FRED) ---

ENERGY_OIL_FUELS = Lens(
    id="energy-oil-fuels", title="Oil & Fuels", accent="#FB923C",
    indicators=[
        Indicator(
            id="gasoline", title="Retail Gasoline · Regular", short="Gasoline", unit="",
            color="#FB923C", series_id="EMM_EPMR_PTE_NUS_DPG", limit=520,
            rule=narrative.consumer_cost("Gasoline", 10, 25, 40), value_format="decimal",
            source="eia", eia_route="petroleum/pri/gnd",
            eia_facets=(("series", "EMM_EPMR_PTE_NUS_DPG"),), eia_freq="weekly",
            context=("The U.S. average retail price for a gallon of regular gasoline — the "
                     "energy cost households feel most directly."),
        ),
        Indicator(
            id="diesel", title="Retail Diesel · On-Highway", short="Diesel", unit="",
            color="#FBBF24", series_id="EMD_EPD2D_PTE_NUS_DPG", limit=520,
            rule=narrative.consumer_cost("Diesel", 10, 25, 40), value_format="decimal",
            source="eia", eia_route="petroleum/pri/gnd",
            eia_facets=(("series", "EMD_EPD2D_PTE_NUS_DPG"),), eia_freq="weekly",
            context=("The U.S. average on-highway diesel price — the fuel that moves freight, "
                     "so it feeds into the price of nearly everything."),
        ),
        Indicator(
            id="crude-production", title="U.S. Crude Oil Production", short="Crude output", unit="",
            color="#34D399", series_id="WCRFPUS2", limit=520,
            rule=narrative.energy_level("U.S. crude production"), value_format="thousands",
            source="eia", eia_route="petroleum/sum/sndw",
            eia_facets=(("series", "WCRFPUS2"),), eia_freq="weekly",
            context=("U.S. field production of crude oil (thousand barrels per day) — the supply "
                     "side that, with demand, sets the price of oil."),
        ),
        Indicator(
            id="crude-stocks", title="Crude Inventories · excl. SPR", short="Crude stocks", unit="",
            color="#38BDF8", series_id="WCESTUS1", limit=520,
            rule=narrative.energy_level("Crude inventories"), value_format="thousands",
            source="eia", eia_route="petroleum/stoc/wstk",
            eia_facets=(("series", "WCESTUS1"),), eia_freq="weekly",
            context=("Commercial crude oil inventories (thousand barrels, excluding the Strategic "
                     "Petroleum Reserve) — low stocks point to upward price pressure."),
        ),
    ],
)

ENERGY_NATURAL_GAS = Lens(
    id="energy-natural-gas", title="Natural Gas", accent="#60A5FA",
    indicators=[
        Indicator(
            id="henry-hub", title="Henry Hub Spot Price", short="Henry Hub", unit="",
            color="#60A5FA", series_id="RNGWHHD", limit=900,
            rule=narrative.consumer_cost("Natural gas", 20, 50, 100), value_format="decimal",
            source="eia", eia_route="natural-gas/pri/fut",
            eia_facets=(("series", "RNGWHHD"),), eia_freq="daily",
            context=("The U.S. benchmark natural-gas price ($/MMBtu) — it drives home heating "
                     "bills and a large share of electricity generation cost."),
        ),
        Indicator(
            id="gas-storage", title="Working Gas in Storage · Lower 48", short="Gas storage", unit="",
            color="#38BDF8", series_id="NW2_EPG0_SWO_R48_BCF", limit=520,
            rule=narrative.energy_level("Gas in storage"), value_format="thousands",
            source="eia", eia_route="natural-gas/stor/wkly",
            eia_facets=(("series", "NW2_EPG0_SWO_R48_BCF"),), eia_freq="weekly",
            context=("Working natural gas held in underground storage (Bcf) — the cushion that "
                     "buffers winter demand; low storage means price risk."),
        ),
        Indicator(
            id="gas-production", title="U.S. Dry Gas Production", short="Gas output", unit="",
            color="#34D399", series_id="N9070US2", limit=240,
            rule=narrative.energy_level("Dry gas production"), value_format="thousands",
            source="eia", eia_route="natural-gas/prod/sum",
            eia_facets=(("series", "N9070US2"),), eia_freq="monthly",
            context=("U.S. dry natural-gas production — record output has reshaped both home "
                     "energy costs and the country's role as an exporter."),
        ),
        Indicator(
            id="lng-exports", title="U.S. LNG Exports", short="LNG exports", unit="",
            color="#A78BFA", series_id="N9133US2", limit=240,
            rule=narrative.energy_level("LNG exports"), value_format="thousands",
            source="eia", eia_route="natural-gas/move/expc",
            eia_facets=(("series", "N9133US2"),), eia_freq="monthly",
            context=("U.S. liquefied natural gas exports — a fast-growing link between domestic "
                     "gas prices and global demand."),
        ),
    ],
)

ENERGY_ELECTRICITY = Lens(
    id="energy-electricity", title="Electricity & the Grid", accent="#FBBF24",
    indicators=[
        Indicator(
            id="electricity-price", title="Retail Electricity · Residential", short="Power price", unit="",
            color="#FBBF24", series_id="ELEC_PRICE_RES_US", limit=240,
            rule=narrative.consumer_cost("Electricity", 5, 10, 20), value_format="decimal",
            source="eia", eia_route="electricity/retail-sales",
            eia_facets=(("sectorid", "RES"), ("stateid", "US")), eia_freq="monthly", eia_col="price",
            context=("The U.S. average residential electricity price (cents per kWh) — the power "
                     "bill households pay every month."),
        ),
        Indicator(
            id="renewables-share", title="Renewables · Share of Generation", short="Renewables", unit="%",
            color="#34D399", series_id="RENEW_SHARE", limit=240,
            rule=narrative.generation_share("Renewables"), value_format="decimal",
            source="eia",  # computed/injected (no eia_route)
            context=("The share of U.S. electricity generated from renewables (wind, solar, hydro, "
                     "and more) — the clearest single read on the energy transition."),
        ),
        Indicator(
            id="natgas-share", title="Natural Gas · Share of Generation", short="Gas share", unit="%",
            color="#60A5FA", series_id="NG_SHARE", limit=240,
            rule=narrative.generation_share("Natural gas"), value_format="decimal",
            source="eia",  # computed/injected
            context=("The share of U.S. electricity generated from natural gas — still the single "
                     "largest source, and the swing fuel that balances the grid."),
        ),
        Indicator(
            id="net-generation", title="Total Net Generation", short="Net generation", unit="",
            color="#38BDF8", series_id="NET_GEN_TOTAL", limit=240,
            rule=narrative.energy_level("Net generation"), value_format="thousands",
            source="eia",  # computed/injected (total from generation_mix)
            context=("Total U.S. net electricity generation (GWh) — a read on how much power the "
                     "economy is consuming."),
        ),
    ],
)

ENERGY_COMMODITIES = Lens(
    id="energy-commodities", title="Commodities & Materials", accent="#A3E635",
    indicators=[
        Indicator(
            id="food-index", title="Global Food Price Index", short="Food", unit="",
            color="#A3E635", series_id="PFOODINDEXM", limit=300,
            rule=narrative.consumer_cost("Food", 5, 12, 25), value_format="decimal",
            context=("The IMF's global food commodity price index — the upstream driver of grocery "
                     "inflation."),
        ),
        Indicator(
            id="copper", title="Copper · “Dr. Copper”", short="Copper", unit="",
            color="#FB923C", series_id="PCOPPUSDM", limit=300,
            rule=narrative.energy_level("Copper"), value_format="thousands",
            context=("The global price of copper ($/metric ton) — nicknamed “Dr. Copper” "
                     "for its knack of signalling the direction of the global economy."),
        ),
        Indicator(
            id="broad-commodities", title="Broad Commodity Index", short="Commodities", unit="",
            color="#38BDF8", series_id="PALLFNFINDEXM", limit=300,
            rule=narrative.energy_level("Commodities"), value_format="decimal",
            context=("The IMF's all-commodity price index — a single gauge of raw-input cost "
                     "pressure across the economy."),
        ),
    ],
)

ENERGY_EIA_LENSES = [ENERGY_OIL_FUELS, ENERGY_NATURAL_GAS, ENERGY_ELECTRICITY]
ENERGY_LENSES = ENERGY_EIA_LENSES + [ENERGY_COMMODITIES]

CATEGORIES.append(
    {"id": "energy", "title": "Energy & Commodities", "lenses": ENERGY_LENSES,
     "out": "energy", "back": "Energy & Commodities",
     "source_label": "U.S. Energy Information Administration (EIA) and FRED", "disclaimer": ""}
)
```

> Note: `electricity-price` uses `series_id="ELEC_PRICE_RES_US"` as a synthetic
> unique key (the EIA retail-sales endpoint is addressed by facets, not a series
> id), and the three generation indicators use synthetic ids (`RENEW_SHARE`,
> `NG_SHARE`, `NET_GEN_TOTAL`) because they are computed/injected in Task 5.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_energy.py"`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Expected: OK.

- [ ] **Step 6: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_energy.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(energy): four energy lenses + category registration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Fixtures + offline build verification

**Files:**
- Create: `scripts/tests/fixtures/energy_sample.json`
- Test: `scripts/tests/test_build_energy.py`

- [ ] **Step 1: Create the build fixture**

Create `scripts/tests/fixtures/energy_sample.json` — a fetched-style dict keyed by
`fetch_key` (`<series_id>:lin`), each a small oldest-first series spanning >1 year
so the YoY rules fire. Computed-indicator keys (`RENEW_SHARE:lin`, `NG_SHARE:lin`,
`NET_GEN_TOTAL:lin`) are pre-filled here (in live runs they are injected):

```json
{
  "EMM_EPMR_PTE_NUS_DPG:lin": [
    {"date": "2025-01-06", "value": "3.10"},
    {"date": "2026-01-05", "value": "3.80"}
  ],
  "EMD_EPD2D_PTE_NUS_DPG:lin": [
    {"date": "2025-01-06", "value": "3.90"},
    {"date": "2026-01-05", "value": "3.95"}
  ],
  "WCRFPUS2:lin": [
    {"date": "2025-01-03", "value": "13200"},
    {"date": "2026-01-02", "value": "13500"}
  ],
  "WCESTUS1:lin": [
    {"date": "2025-01-03", "value": "420000"},
    {"date": "2026-01-02", "value": "430000"}
  ],
  "RNGWHHD:lin": [
    {"date": "2025-01-06", "value": "3.00"},
    {"date": "2026-01-05", "value": "4.20"}
  ],
  "NW2_EPG0_SWO_R48_BCF:lin": [
    {"date": "2025-01-03", "value": "3100"},
    {"date": "2026-01-02", "value": "2900"}
  ],
  "N9070US2:lin": [
    {"date": "2025-01-01", "value": "3400"},
    {"date": "2026-01-01", "value": "3600"}
  ],
  "N9133US2:lin": [
    {"date": "2025-01-01", "value": "380"},
    {"date": "2026-01-01", "value": "460"}
  ],
  "ELEC_PRICE_RES_US:lin": [
    {"date": "2025-01-01", "value": "16.2"},
    {"date": "2026-01-01", "value": "17.0"}
  ],
  "RENEW_SHARE:lin": [
    {"date": "2025-01-01", "value": "21.0"},
    {"date": "2026-01-01", "value": "24.0"}
  ],
  "NG_SHARE:lin": [
    {"date": "2025-01-01", "value": "42.0"},
    {"date": "2026-01-01", "value": "41.0"}
  ],
  "NET_GEN_TOTAL:lin": [
    {"date": "2025-01-01", "value": "330000"},
    {"date": "2026-01-01", "value": "335000"}
  ],
  "PFOODINDEXM:lin": [
    {"date": "2025-01-01", "value": "120.0"},
    {"date": "2026-01-01", "value": "128.0"}
  ],
  "PCOPPUSDM:lin": [
    {"date": "2025-01-01", "value": "9000"},
    {"date": "2026-01-01", "value": "9500"}
  ],
  "PALLFNFINDEXM:lin": [
    {"date": "2025-01-01", "value": "150.0"},
    {"date": "2026-01-01", "value": "158.0"}
  ],
  "USREC:lin": [
    {"date": "2025-01-01", "value": "0"},
    {"date": "2026-01-01", "value": "0"}
  ]
}
```

- [ ] **Step 2: Write the build test**

Create `scripts/tests/test_build_energy.py`:

```python
import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "energy_sample.json"


def _fetched():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestBuildEnergy(unittest.TestCase):
    def test_all_four_lenses_build(self):
        fetched = _fetched()
        jsons = [build.build_lens(l, fetched) for l in config.ENERGY_LENSES]
        self.assertEqual([j["id"] for j in jsons],
                         ["energy-oil-fuels", "energy-natural-gas",
                          "energy-electricity", "energy-commodities"])

    def test_oil_lens_badge_is_severity_from_gasoline(self):
        fetched = _fetched()
        oil = build.build_lens(config.ENERGY_OIL_FUELS, fetched)
        # gasoline +22.6% -> watch (band 10/25/40); badge should be a severity token
        self.assertIn(oil["status"], {"ok", "watch", "elevated", "alert"})
        gas = next(i for i in oil["indicators"] if i["id"] == "gasoline")
        self.assertEqual(gas["signal_status"], "watch")

    def test_physical_indicators_are_info(self):
        fetched = _fetched()
        oil = build.build_lens(config.ENERGY_OIL_FUELS, fetched)
        prod = next(i for i in oil["indicators"] if i["id"] == "crude-production")
        self.assertEqual(prod["signal_status"], "info")

    def test_electricity_shares_present(self):
        fetched = _fetched()
        elec = build.build_lens(config.ENERGY_ELECTRICITY, fetched)
        renew = next(i for i in elec["indicators"] if i["id"] == "renewables-share")
        self.assertTrue(renew["observations"])
        self.assertEqual(renew["signal_status"], "info")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it to verify it passes** (no implementation needed — Tasks 2-3 already wired the rules/config)

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build_energy.py"`
Expected: PASS. If `test_oil_lens_badge` shows a different gasoline status than
`watch`, recompute: fixture gasoline goes 3.10 → 3.80 = +22.6%, which is in the
10–25 `watch` band — assertion is correct. (If a rule edit changed the band,
align the fixture or assertion to the real value, don't force it.)

- [ ] **Step 4: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/fixtures/energy_sample.json scripts/tests/test_build_energy.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(energy): build fixture + lens build verification

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Orchestration — refresh_energy + EIA injection + `--energy`

**Files:**
- Modify: `scripts/refresh_lenses.py`
- Test: `scripts/tests/test_refresh_energy.py`

- [ ] **Step 1: Write the failing orchestration test**

Create `scripts/tests/test_refresh_energy.py`:

```python
import sys
import pathlib
import json
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config


class TestEnergyDryRun(unittest.TestCase):
    def _build(self):
        fetched = json.loads(refresh_lenses.ENERGY_FIXTURE.read_text(encoding="utf-8"))
        return [build.build_lens(l, fetched) for l in config.ENERGY_LENSES]

    def test_builds_four_energy_lenses(self):
        ids = {j["id"] for j in self._build()}
        self.assertEqual(ids, {"energy-oil-fuels", "energy-natural-gas",
                               "energy-electricity", "energy-commodities"})

    def test_energy_flag_runs_dry_into_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.ENERGY_OUT_DIR
            refresh_lenses.ENERGY_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--energy", "--dry-run"])
            finally:
                refresh_lenses.ENERGY_OUT_DIR = orig
            self.assertEqual(rc, 0)
            self.assertTrue((tmp / "energy-oil-fuels.json").exists())
            self.assertTrue((tmp / "index.json").exists())


class TestGenerationShareInjection(unittest.TestCase):
    def test_pct_share_used_for_renewables(self):
        # total 100, renewable 24 -> 24.0
        from lenses import util
        share = util.pct_share([{"date": "2026-01", "value": "24"}],
                               [{"date": "2026-01", "value": "100"}])
        self.assertEqual(share, [{"date": "2026-01", "value": "24.0"}])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_energy.py"`
Expected: FAIL — `AttributeError: module 'refresh_lenses' has no attribute 'ENERGY_FIXTURE'`.

- [ ] **Step 3: Add energy orchestration to `refresh_lenses.py`**

In `scripts/refresh_lenses.py`, add `eia` to the import line:
```python
from lenses import build, coingecko, config, eia, fdic, fred, util, yahoo
```

Add path constants near the other OUT_DIR constants (after `MARKETS_OUT_DIR`):
```python
ENERGY_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "energy"
ENERGY_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "energy_sample.json"
```

Add these functions (place them after `refresh_markets`):
```python
def _prior_energy_obs(lens_id, ind_id):
    """Prior observations for one energy indicator from its existing lens JSON
    (fallback when an EIA fetch or the key is unavailable)."""
    path = ENERGY_OUT_DIR / f"{lens_id}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ind in data.get("indicators", []):
                if ind.get("id") == ind_id:
                    return ind.get("observations", [])
        except (ValueError, OSError):
            pass
    return []


def _inject_generation_shares(fetched, api_key):
    """Compute renewables/natural-gas share of generation + total net generation
    from EIA's generation-mix dataset, inject under their indicator fetch_keys."""
    mix = eia.generation_mix(api_key)
    fetched["NET_GEN_TOTAL:lin"] = mix["total"]
    fetched["RENEW_SHARE:lin"] = util.pct_share(mix["renewable"], mix["total"])
    fetched["NG_SHARE:lin"] = util.pct_share(mix["natgas"], mix["total"])


def _inject_eia(fetched, dry_run):
    """Populate every EIA indicator (lenses 1-3). Additive: on a missing key or a
    fetch failure, fall back to prior data so the FRED commodities lens and any
    unaffected lenses still publish. In dry-run the fixture already carries the keys."""
    if dry_run:
        return
    api_key = os.environ.get("EIA_API_KEY")
    computed = {"renewables-share", "natgas-share", "net-generation"}
    if not api_key:
        print("WARN: EIA_API_KEY not set; keeping previous energy data", file=sys.stderr)
        for lens in config.ENERGY_EIA_LENSES:
            for ind in lens.indicators:
                fetched[ind.fetch_key] = _prior_energy_obs(lens.id, ind.id)
        return
    # Directly-routed EIA indicators
    for lens in config.ENERGY_EIA_LENSES:
        for ind in lens.indicators:
            if ind.id in computed or not ind.eia_route:
                continue
            try:
                fetched[ind.fetch_key] = eia.fetch_series(
                    ind.eia_route, ind.eia_facets, ind.eia_freq, api_key, ind.limit, ind.eia_col)
            except Exception as exc:  # noqa: BLE001 - keep prior on failure
                print(f"WARN: EIA fetch failed for {ind.series_id}: {exc}", file=sys.stderr)
                fetched[ind.fetch_key] = _prior_energy_obs(lens.id, ind.id)
    # Computed generation shares (renewables/natgas/total)
    try:
        _inject_generation_shares(fetched, api_key)
    except Exception as exc:  # noqa: BLE001 - keep prior on failure
        print(f"WARN: EIA generation mix failed ({exc}); keeping previous data", file=sys.stderr)
        for ind_id, key in (("net-generation", "NET_GEN_TOTAL:lin"),
                            ("renewables-share", "RENEW_SHARE:lin"),
                            ("natgas-share", "NG_SHARE:lin")):
            fetched[key] = _prior_energy_obs("energy-electricity", ind_id)


def refresh_energy(dry_run):
    """Build + write the energy lenses (EIA lenses 1-3 + the FRED commodities lens).
    Additive — an EIA failure never aborts the run; the FRED lens still publishes."""
    if dry_run:
        fetched = json.loads(ENERGY_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.ENERGY_LENSES, api_key)

    _inject_eia(fetched, dry_run)

    ready = [lens for lens in config.ENERGY_LENSES if lens_ready(lens, failed)]
    for lens in config.ENERGY_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready], ENERGY_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all energy data up to date.")
    return 0
```

Note on `fetch_all` + EIA: `unique_specs` skips non-FRED indicators, so
`fetch_all(config.ENERGY_LENSES, ...)` only fetches the FRED commodities series
(plus USREC) and never tries to fetch EIA series. `lens_ready` checks
`fetch_key in failed`; EIA fetch_keys are never added to `failed`, so EIA lenses
are always "ready" (their data comes from `_inject_eia`). This mirrors how gold
and crypto are handled in `refresh_markets`.

- [ ] **Step 4: Wire the `--energy` flag into `main`**

In `scripts/refresh_lenses.py`, in `main`, add the argument and dispatch:
```python
    parser.add_argument("--energy", action="store_true", help="refresh only the energy lenses")
```
Update the flag logic:
```python
    any_flag = args.economic or args.banking or args.markets or args.energy
    do_economic = args.economic or not any_flag
    do_banking = args.banking or not any_flag
    do_markets = args.markets or not any_flag
    do_energy = args.energy or not any_flag
```
And add the dispatch (after the markets block, before banking):
```python
    if do_energy:
        ec = refresh_energy(args.dry_run)
        if ec:
            code = ec
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_energy.py"`
Expected: PASS (dry-run writes four lens files + index into the temp dir).

- [ ] **Step 6: Run the full suite**

Expected: OK.

- [ ] **Step 7: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_refresh_energy.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(energy): refresh_energy orchestration + EIA injection + --energy flag

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Pages (hub + four lenses + hub card)

No unit tests — pages are thin wrappers over the shared renderer (consistent with
the existing markets pages). Verified by the offline build in Task 8 + visual
review. The renderer (`lens.js`/`lens.css`) needs **no** changes — momentum/info
badges and severity badges already have styles.

**Files:**
- Create: `dashboards/energy/index.html`
- Create: `dashboards/energy/oil-fuels.html`, `natural-gas.html`, `electricity.html`, `commodities.html`
- Modify: `dashboards/index.html` (add the energy hub card + loader)

- [ ] **Step 1: Create the category hub `dashboards/energy/index.html`**

Clone `dashboards/markets/index.html` exactly, changing only: `<title>` →
"Energy & Commodities — Bailey Analytics"; the meta description; the `<h1>` →
"Energy &amp; Commodities"; the lede paragraph to describe the four lenses; the
`SLUGS` map to:
```javascript
    const SLUGS = {
      "energy-oil-fuels": "oil-fuels",
      "energy-natural-gas": "natural-gas",
      "energy-electricity": "electricity",
      "energy-commodities": "commodities"
    };
```
the fetch path to `/data/energy/index.json`; the hub-card href base to
`/dashboards/energy/`; and the footer to:
```html
      Data: <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a> and <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a>. Public data, refreshed daily.
```

- [ ] **Step 2: Create the four lens pages**

Each is a thin wrapper cloned from `dashboards/markets/risk-sentiment.html`,
changing only the `<title>`, meta description, the `renderLens(...)` JSON path +
`back`/`href`, and the `foot`. Exact values:

`dashboards/energy/oil-fuels.html`:
```html
    renderLens("/data/energy/energy-oil-fuels.json", {
      back: "Energy & Commodities",
      href: "/dashboards/energy/",
      foot: 'Data: <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a>. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
    });
```
`natural-gas.html` → JSON `/data/energy/energy-natural-gas.json` (same `back`/`href`/`foot`).
`electricity.html` → JSON `/data/energy/energy-electricity.json` (same `back`/`href`/`foot`).
`commodities.html` → JSON `/data/energy/energy-commodities.json`, with `foot` crediting FRED:
```html
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (IMF commodity indices). Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
```
Set each page's `<title>` to "<Lens name> — Bailey Analytics" and a one-line meta
description matching the lens.

- [ ] **Step 3: Add the energy hub card to `dashboards/index.html`**

After the markets section block (the `<div class="hub-grid" id="markets-grid">`
line), add:
```html
    <h2 class="cat-head"><span class="dot" style="background:#FB923C"></span>Energy &amp; Commodities</h2>
    <p class="cat-sub">The physical economy — what fuel and power cost, how energy is produced, and the commodity prices that feed inflation. Refreshed from the U.S. EIA and FRED. <a href="/dashboards/energy/" style="color:var(--blue);text-decoration:none">Overview &rarr;</a></p>
    <div class="hub-grid" id="energy-grid"><div class="status-msg">Loading&hellip;</div></div>
```
And after the existing `loadGrid("/data/markets/index.json", ...)` call, add:
```javascript
    const ENERGY_SLUGS = {
      "energy-oil-fuels": "oil-fuels",
      "energy-natural-gas": "natural-gas",
      "energy-electricity": "electricity",
      "energy-commodities": "commodities"
    };
    loadGrid("/data/energy/index.json", "energy-grid",
             id => `/dashboards/energy/${encodeURIComponent(ENERGY_SLUGS[id] || id)}.html`);
```

- [ ] **Step 4: Sanity-check the pages locally (optional, manual)**

If serving locally: `python -m http.server 8000` from `baileyanalytics/` and open
`http://localhost:8000/dashboards/energy/`. (Energy JSON won't exist until a build;
the page should show the graceful "still being refreshed" message — that's fine.)

- [ ] **Step 5: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/energy dashboards/index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(energy): category hub, four lens pages, dashboards hub card

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Daily workflow step

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`

- [ ] **Step 1: Read the workflow to match its existing step style**

Read `.github/workflows/refresh-fred.yml`. It already runs `--economic` then
`--markets` with `FRED_API_KEY` (+ optional `COINGECKO_API_KEY`).

- [ ] **Step 2: Add an energy step**

Add a step that runs `python scripts/refresh_lenses.py --energy` with both
`FRED_API_KEY` and `EIA_API_KEY` in `env:`, mirroring the existing markets step's
shape exactly (same `working-directory`/`env` pattern). Example:
```yaml
      - name: Refresh energy lenses
        working-directory: baileyanalytics
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: python scripts/refresh_lenses.py --energy
```
(Match the actual indentation/working-directory of the existing steps in the file.)

- [ ] **Step 3: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add .github/workflows/refresh-fred.yml
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "ci(energy): refresh energy lenses in the daily workflow

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Final offline verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite**

Run the discover command.
Expected: OK, with the new energy tests included (count rises from 157).

- [ ] **Step 2: Offline build into a temp dir (does not touch tracked data)**

```
python - <<'PY'
import tempfile, pathlib, refresh_lenses
sys = __import__("sys"); sys.path.insert(0, "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts")
with tempfile.TemporaryDirectory() as td:
    refresh_lenses.ENERGY_OUT_DIR = pathlib.Path(td)
    rc = refresh_lenses.main(["--energy", "--dry-run"])
    print("rc", rc, "files", sorted(p.name for p in pathlib.Path(td).glob("*.json")))
PY
```
Expected: `rc 0` and five files (`energy-oil-fuels.json`, `energy-natural-gas.json`,
`energy-electricity.json`, `energy-commodities.json`, `index.json`).

- [ ] **Step 3: Confirm no tracked `data/` changes**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" status --short data/
```
Expected: empty (no live data was built; `data/energy/` is created only by a live
or temp build, not committed in this plan).

- [ ] **Step 4: Stop — hand back to the owner**

Do **not** push or deploy. Summarize for the owner: the category is built and
fully unit-tested offline; the remaining steps need them: (1) create a free EIA
API key + add `EIA_API_KEY` as a GitHub secret and local env var; (2) run a live
build (`python scripts/refresh_lenses.py --energy`); (3) verify/adjust any EIA
route or facet that the live run reveals (the fetcher makes this a one-line fix);
(4) calibrate the consumer-cost thresholds against live data; (5) review, then
merge + deploy.

---

## Notes for the implementer

- Tasks are ordered by dependency (fetcher → rules → config → fixture → orchestration
  → pages → CI → verify). Each leaves the suite green.
- The fuzziest real-world risk is EIA route/facet/series-id accuracy (spec item D).
  It does not block this plan: all code is fixture-tested, and the live run will
  reveal any 400s, each fixable in one config line. `_inject_eia` keeps prior data
  on any failure, so a wrong route degrades gracefully rather than crashing.
- After all tasks: use **superpowers:finishing-a-development-branch**, but choose
  "keep as-is" (option 3) — the branch needs the owner's live build + approval
  before merge/deploy.
```

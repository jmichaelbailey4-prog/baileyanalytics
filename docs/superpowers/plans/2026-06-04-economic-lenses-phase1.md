# Economic Lenses — Phase 1 Implementation Plan (Framework + Recession Watch)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the config-driven data pipeline, the rule-based narrative engine, the shared frontend "lens" renderer, and ship the Recession Watch lens page end-to-end — proving the whole framework on the flagship lens.

**Architecture:** A Python package (`scripts/lenses/`) defines lenses as config (indicators + evergreen context + a pure narrative rule per indicator). An expanded refresh script fetches each unique FRED series once (using FRED `units` transforms), runs the narrative rules, and writes one JSON per lens plus a hub `index.json`. A shared static frontend (`dashboards/lens.css` + `dashboards/lens.js`) renders any lens JSON into the approved UI (hero "current read", scoreboard, indicator cards with charts, range toggle, recession shading). Stays static, no build step, FRED-only, Chart.js from CDN.

**Tech Stack:** Python 3.13 stdlib only (`urllib`, `json`, `dataclasses`, `unittest`), vanilla HTML/CSS/JS, Chart.js 4 via CDN, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-06-04-economic-lenses-design.md`

**Scope note:** This plan delivers Phase 1 only (per spec §11). Phases 2 (the other three lenses) and 3 (hub page + retire `economic.html`) will each get their own plan once this framework is validated. Phase 1 produces working, testable software on its own: a live Recession Watch page fed by the new pipeline.

---

## File structure (Phase 1)

**Create — Python pipeline (`scripts/lenses/` package):**
- `scripts/lenses/__init__.py` — marks the package.
- `scripts/lenses/util.py` — value parsing + status helpers. One responsibility: small pure utilities.
- `scripts/lenses/narrative.py` — the rule functions (one per indicator) + per-lens synthesis. Pure functions, no I/O.
- `scripts/lenses/recessions.py` — turn USREC observations into recession date ranges. Pure.
- `scripts/lenses/fred.py` — fetch observations from the FRED API (the only network module).
- `scripts/lenses/config.py` — dataclasses (`Indicator`, `Lens`) + the Recession Watch config + the `LENSES` list + helper-series constants.
- `scripts/lenses/build.py` — assemble a lens JSON and the hub `index.json` from config + fetched data; write files (skipping unchanged).
- `scripts/refresh_lenses.py` — CLI entry point: fetch (live) or load fixtures (`--dry-run`), build, write.

**Create — tests (`scripts/tests/`):**
- `scripts/tests/__init__.py`
- `scripts/tests/test_util.py`, `test_narrative.py`, `test_recessions.py`, `test_fred.py`, `test_build.py`
- `scripts/tests/fixtures/fetched_sample.json` — offline sample of fetched data for dry-run + build tests.

**Create — frontend:**
- `dashboards/lens.css` — shared stylesheet for lens (and later hub) pages.
- `dashboards/lens.js` — shared renderer (`renderLens(jsonUrl)`).
- `dashboards/recession-watch.html` — thin page stub.

**Generated (by running the pipeline):**
- `data/lenses/recession-watch.json`, `data/lenses/index.json`.

**Modify:**
- `.github/workflows/refresh-fred.yml` — also run `refresh_lenses.py` and commit `data/lenses/`.

**Untouched in Phase 1:** `scripts/refresh_fred.py`, `data/economic.json`, `dashboards/economic.html` (retired in Phase 3).

---

## Conventions used across tasks

- **Cleaned observations**: a list of `(date_str, float_value)` tuples in chronological order, nulls removed. Produced by `util.clean()`. Every narrative rule takes this exact type and returns `(text: str, status: str)`.
- **Status vocabulary**: `"ok"`, `"watch"`, `"elevated"`, `"alert"`, `"unknown"`.
- **Fetched dict**: keyed by `fetch_key = f"{series_id}:{units_transform or 'lin'}"`; value is the raw observation list `[{"date","value"}]` (chronological, values as strings, may include `"."`).
- **Run a single test file:** `python scripts/tests/test_<name>.py -v` from the repo root.
- **Run all tests:** `python -m unittest discover -s scripts/tests -p "test_*.py" -v`

---

### Task 1: Package + test scaffolding

**Files:**
- Create: `scripts/lenses/__init__.py`
- Create: `scripts/tests/__init__.py`
- Create: `scripts/tests/test_smoke.py`

- [ ] **Step 1: Create the package markers**

`scripts/lenses/__init__.py`:
```python
"""Economic Lenses data pipeline."""
```

`scripts/tests/__init__.py`:
```python
```
(empty file)

- [ ] **Step 2: Write a smoke test that proves the import path works**

`scripts/tests/test_smoke.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # add scripts/ to path


class TestSmoke(unittest.TestCase):
    def test_package_imports(self):
        import lenses  # noqa: F401
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run it to verify it passes**

Run: `python scripts/tests/test_smoke.py -v`
Expected: PASS (`test_package_imports ... ok`)

- [ ] **Step 4: Commit**

```bash
git add scripts/lenses/__init__.py scripts/tests/__init__.py scripts/tests/test_smoke.py
git commit -m "chore: scaffold lenses package and test runner"
```

---

### Task 2: Value & status utilities

**Files:**
- Create: `scripts/lenses/util.py`
- Test: `scripts/tests/test_util.py`

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_util.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import util


class TestUtil(unittest.TestCase):
    def test_to_float_parses_numbers(self):
        self.assertEqual(util.to_float("4.2"), 4.2)

    def test_to_float_returns_none_for_fred_null(self):
        self.assertIsNone(util.to_float("."))
        self.assertIsNone(util.to_float(None))

    def test_clean_drops_nulls_and_keeps_order(self):
        raw = [
            {"date": "2026-01-01", "value": "1.0"},
            {"date": "2026-02-01", "value": "."},
            {"date": "2026-03-01", "value": "2.5"},
        ]
        self.assertEqual(util.clean(raw), [("2026-01-01", 1.0), ("2026-03-01", 2.5)])

    def test_status_max_picks_most_severe(self):
        self.assertEqual(util.status_max(["ok", "watch", "elevated"]), "elevated")

    def test_status_max_ignores_unknown_when_others_present(self):
        self.assertEqual(util.status_max(["unknown", "ok"]), "ok")

    def test_status_max_all_unknown(self):
        self.assertEqual(util.status_max(["unknown", "unknown"]), "unknown")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_util.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lenses.util'`)

- [ ] **Step 3: Implement**

`scripts/lenses/util.py`:
```python
"""Small pure helpers shared across the pipeline."""

STATUS_ORDER = {"unknown": -1, "ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def to_float(value):
    """Parse a FRED value string to float, or None for missing values ('.', None)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean(raw_observations):
    """Convert raw [{'date','value'}] into chronological [(date, float)], dropping nulls."""
    out = []
    for obs in raw_observations:
        f = to_float(obs.get("value"))
        if f is not None:
            out.append((obs["date"], f))
    return out


def status_max(statuses):
    """Return the most severe status; 'unknown' only if nothing else is present."""
    known = [s for s in statuses if s in STATUS_ORDER and s != "unknown"]
    if not known:
        return "unknown"
    return max(known, key=lambda s: STATUS_ORDER[s])
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_util.py -v`
Expected: PASS (6 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/util.py scripts/tests/test_util.py
git commit -m "feat: add value parsing and status utilities"
```

---

### Task 3: Narrative rule — yield curve

**Files:**
- Create: `scripts/lenses/narrative.py`
- Test: `scripts/tests/test_narrative.py`

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_narrative.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


class TestYieldCurve(unittest.TestCase):
    def test_inverted_is_elevated(self):
        obs = [("2026-05-01", -0.5), ("2026-06-01", -0.3)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "elevated")
        self.assertIn("inverted", text)

    def test_recent_uninversion_is_watch(self):
        obs = [("2026-01-01", -0.2), ("2026-05-01", 0.1), ("2026-06-01", 0.30)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "watch")
        self.assertIn("un-inverted", text)

    def test_long_positive_is_ok(self):
        obs = [("2026-01-01", 0.8)] * 5 + [("2026-06-01", 0.9)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_yield_curve([]), ("Data unavailable.", "unknown"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_narrative.py -v`
Expected: FAIL (`AttributeError: module 'lenses.narrative' has no attribute 'rule_yield_curve'`)

- [ ] **Step 3: Implement**

`scripts/lenses/narrative.py`:
```python
"""Rule-based narrative engine. Pure functions of cleaned observations.

Each rule takes a chronological list of (date, float) tuples and returns
(text, status). Status is one of: ok, watch, elevated, alert, unknown.
"""

from . import util

_NO_DATA = ("Data unavailable.", "unknown")


def rule_yield_curve(obs):
    """T10Y2Y: inverted (<0) warns; a recent un-inversion warrants vigilance."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    recent = [val for _, val in obs[-126:]]  # ~6 months of daily data
    was_inverted = any(val < 0 for val in recent[:-1])
    if v < 0:
        return (
            f"The curve is inverted by {abs(v):.2f} points — a classic recession "
            "warning that has preceded every U.S. recession since the 1970s.",
            "elevated",
        )
    if was_inverted:
        return (
            f"The curve recently un-inverted to +{v:.2f} after an extended inversion. "
            "Recessions historically begin after the curve climbs back above zero — "
            "a reason for more vigilance, not less.",
            "watch",
        )
    return (
        f"The curve is positive (+{v:.2f}) with no recent inversion — "
        "no recession warning from the curve right now.",
        "ok",
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_narrative.py -v`
Expected: PASS (4 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/narrative.py scripts/tests/test_narrative.py
git commit -m "feat: add yield-curve narrative rule"
```

---

### Task 4: Narrative rule — Sahm rule

**Files:**
- Modify: `scripts/lenses/narrative.py`
- Modify: `scripts/tests/test_narrative.py`

- [ ] **Step 1: Add the failing test** (append this class to `scripts/tests/test_narrative.py`, before the `if __name__` block)

```python
class TestSahm(unittest.TestCase):
    def test_triggered_is_alert(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.55)])
        self.assertEqual(status, "alert")
        self.assertIn("triggered", text)

    def test_near_trigger_is_watch(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.43)])
        self.assertEqual(status, "watch")

    def test_low_is_ok(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.10)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_sahm([]), ("Data unavailable.", "unknown"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_narrative.py -v`
Expected: FAIL (`AttributeError: ... has no attribute 'rule_sahm'`)

- [ ] **Step 3: Implement** (append to `scripts/lenses/narrative.py`)

```python
def rule_sahm(obs):
    """SAHMREALTIME: trips at 0.50; 0.35-0.50 is a warning band."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 0.50:
        return (
            f"The Sahm rule has triggered at {v:.2f}, historically consistent with "
            "a recession already underway.",
            "alert",
        )
    if v >= 0.35:
        return (
            f"The Sahm rule is at {v:.2f}, climbing toward its 0.50 recession "
            "trigger but not there yet.",
            "watch",
        )
    return (f"The Sahm rule is at {v:.2f}, well below its 0.50 recession trigger.", "ok")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_narrative.py -v`
Expected: PASS (8 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/narrative.py scripts/tests/test_narrative.py
git commit -m "feat: add Sahm-rule narrative rule"
```

---

### Task 5: Narrative rule — initial jobless claims

**Files:**
- Modify: `scripts/lenses/narrative.py`
- Modify: `scripts/tests/test_narrative.py`

- [ ] **Step 1: Add the failing test** (append before the `if __name__` block)

```python
class TestClaims(unittest.TestCase):
    def test_low_is_ok(self):
        text, status = narrative.rule_claims([("2026-06-01", 219000.0)])
        self.assertEqual(status, "ok")
        self.assertIn("219k", text)

    def test_creeping_is_watch(self):
        _, status = narrative.rule_claims([("2026-06-01", 275000.0)])
        self.assertEqual(status, "watch")

    def test_high_is_elevated(self):
        _, status = narrative.rule_claims([("2026-06-01", 340000.0)])
        self.assertEqual(status, "elevated")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_claims([]), ("Data unavailable.", "unknown"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_narrative.py -v`
Expected: FAIL (`... has no attribute 'rule_claims'`)

- [ ] **Step 3: Implement** (append to `scripts/lenses/narrative.py`)

```python
def rule_claims(obs):
    """ICSA (weekly level): <250k low, 250-300k creeping, >=300k elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    k = v / 1000
    if v < 250000:
        return (
            f"Initial jobless claims are low at ~{k:.0f}k — employers aren't "
            "shedding workers.",
            "ok",
        )
    if v < 300000:
        return (f"Jobless claims at ~{k:.0f}k are creeping up from their lows.", "watch")
    return (
        f"Jobless claims have risen to ~{k:.0f}k, a sign of accelerating layoffs.",
        "elevated",
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_narrative.py -v`
Expected: PASS (12 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/narrative.py scripts/tests/test_narrative.py
git commit -m "feat: add jobless-claims narrative rule"
```

---

### Task 6: Narrative rule — unemployment trend

**Files:**
- Modify: `scripts/lenses/narrative.py`
- Modify: `scripts/tests/test_narrative.py`

- [ ] **Step 1: Add the failing test** (append before the `if __name__` block)

```python
class TestUnemploymentTrend(unittest.TestCase):
    def test_rising_from_low_is_watch(self):
        obs = [("m1", 3.6), ("m2", 3.7), ("m3", 3.9), ("m4", 4.1), ("m5", 4.2)]
        text, status = narrative.rule_unemployment_trend(obs)
        self.assertEqual(status, "watch")
        self.assertIn("0.6", text)  # 4.2 - 3.6

    def test_steady_is_ok(self):
        obs = [("m1", 4.1), ("m2", 4.0), ("m3", 4.1), ("m4", 4.2)]
        _, status = narrative.rule_unemployment_trend(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_unemployment_trend([]), ("Data unavailable.", "unknown"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_narrative.py -v`
Expected: FAIL (`... has no attribute 'rule_unemployment_trend'`)

- [ ] **Step 3: Implement** (append to `scripts/lenses/narrative.py`)

```python
def rule_unemployment_trend(obs):
    """UNRATE: a rise of >=0.5pts above the trailing 12-month low is a warning."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    window = [val for _, val in obs[-12:]]
    low = min(window)
    delta = v - low
    if delta >= 0.5:
        return (
            f"Unemployment at {v:.1f}% is up {delta:.1f} points from its recent low — "
            "the kind of rise that has preceded past downturns.",
            "watch",
        )
    return (f"Unemployment is steady at {v:.1f}%, near its recent lows.", "ok")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_narrative.py -v`
Expected: PASS (15 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/narrative.py scripts/tests/test_narrative.py
git commit -m "feat: add unemployment-trend narrative rule"
```

---

### Task 7: Per-lens synthesis (headline read)

**Files:**
- Modify: `scripts/lenses/narrative.py`
- Modify: `scripts/tests/test_narrative.py`

- [ ] **Step 1: Add the failing test** (append before the `if __name__` block)

```python
class TestSynthesize(unittest.TestCase):
    def test_watch_headline(self):
        headline, overall = narrative.synthesize("recession-watch", ["ok", "watch", "ok", "watch"])
        self.assertEqual(overall, "watch")
        self.assertIn("warning lights", headline)

    def test_alert_headline(self):
        headline, overall = narrative.synthesize("recession-watch", ["alert", "watch"])
        self.assertEqual(overall, "alert")
        self.assertIn("flashing", headline)

    def test_unknown_lens_returns_empty_headline(self):
        headline, overall = narrative.synthesize("does-not-exist", ["ok"])
        self.assertEqual(overall, "ok")
        self.assertEqual(headline, "")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_narrative.py -v`
Expected: FAIL (`... has no attribute 'synthesize'`)

- [ ] **Step 3: Implement** (append to `scripts/lenses/narrative.py`)

```python
HEADLINES = {
    "recession-watch": {
        "alert": "Recession signals are flashing — multiple indicators have tripped.",
        "elevated": "Recession risk is elevated — the yield curve is warning.",
        "watch": "No recession underway — but the warning lights are no longer all green.",
        "ok": "The economy looks steady — no major recession signals right now.",
        "unknown": "Some recession signals are temporarily unavailable.",
    },
}


def synthesize(lens_id, statuses):
    """Combine indicator statuses into (headline_read, overall_status)."""
    overall = util.status_max(statuses)
    headline = HEADLINES.get(lens_id, {}).get(overall, "")
    return headline, overall
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_narrative.py -v`
Expected: PASS (18 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/narrative.py scripts/tests/test_narrative.py
git commit -m "feat: add per-lens narrative synthesis"
```

---

### Task 8: Recession periods from USREC

**Files:**
- Create: `scripts/lenses/recessions.py`
- Test: `scripts/tests/test_recessions.py`

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_recessions.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import recessions


class TestRecessions(unittest.TestCase):
    def test_extracts_one_period(self):
        obs = [
            {"date": "2020-01-01", "value": "0"},
            {"date": "2020-02-01", "value": "1"},
            {"date": "2020-03-01", "value": "1"},
            {"date": "2020-04-01", "value": "0"},
        ]
        self.assertEqual(
            recessions.recession_periods(obs),
            [{"start": "2020-02-01", "end": "2020-04-01"}],
        )

    def test_open_ended_period_uses_last_date(self):
        obs = [
            {"date": "2026-01-01", "value": "0"},
            {"date": "2026-02-01", "value": "1"},
        ]
        self.assertEqual(
            recessions.recession_periods(obs),
            [{"start": "2026-02-01", "end": "2026-02-01"}],
        )

    def test_no_recession(self):
        obs = [{"date": "2026-01-01", "value": "0"}]
        self.assertEqual(recessions.recession_periods(obs), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_recessions.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lenses.recessions'`)

- [ ] **Step 3: Implement**

`scripts/lenses/recessions.py`:
```python
"""Convert the USREC indicator (1 = in recession) into date ranges for shading."""

from . import util


def recession_periods(usrec_obs):
    """Return [{'start','end'}] periods where USREC == 1 (chronological input)."""
    periods = []
    start = None
    for obs in usrec_obs:
        v = util.to_float(obs.get("value"))
        if v is None:
            continue
        if v >= 0.5 and start is None:
            start = obs["date"]
        elif v < 0.5 and start is not None:
            periods.append({"start": start, "end": obs["date"]})
            start = None
    if start is not None:
        periods.append({"start": start, "end": usrec_obs[-1]["date"]})
    return periods
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_recessions.py -v`
Expected: PASS (3 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/recessions.py scripts/tests/test_recessions.py
git commit -m "feat: derive recession periods from USREC"
```

---

### Task 9: FRED fetch module

**Files:**
- Create: `scripts/lenses/fred.py`
- Test: `scripts/tests/test_fred.py`

- [ ] **Step 1: Write the failing test** (uses `unittest.mock` to avoid the network)

`scripts/tests/test_fred.py`:
```python
import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import fred


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestFred(unittest.TestCase):
    def test_returns_chronological_observations(self):
        payload = {
            "observations": [
                {"date": "2026-06-02", "value": "0.30", "realtime_start": "x"},
                {"date": "2026-06-01", "value": "0.28", "realtime_start": "x"},
            ]
        }
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fred.urllib.request.urlopen", return_value=fake) as m:
            obs = fred.fetch_observations("T10Y2Y", api_key="KEY", limit=500)
        # chronological (oldest first), trimmed to date/value
        self.assertEqual(obs, [
            {"date": "2026-06-01", "value": "0.28"},
            {"date": "2026-06-02", "value": "0.30"},
        ])
        # the request used sort_order=desc and included the api key + series
        called_url = m.call_args[0][0]
        self.assertIn("series_id=T10Y2Y", called_url)
        self.assertIn("api_key=KEY", called_url)
        self.assertIn("sort_order=desc", called_url)

    def test_includes_units_transform_when_given(self):
        fake = FakeResponse(json.dumps({"observations": []}).encode())
        with mock.patch("lenses.fred.urllib.request.urlopen", return_value=fake) as m:
            fred.fetch_observations("CPIAUCSL", api_key="KEY", limit=240, units="pc1")
        self.assertIn("units=pc1", m.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_fred.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lenses.fred'`)

- [ ] **Step 3: Implement**

`scripts/lenses/fred.py`:
```python
"""FRED API access — the only module that touches the network."""

import json
import urllib.parse
import urllib.request

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch_observations(series_id, api_key, limit, units=None, timeout=15):
    """Fetch the most recent `limit` observations, returned oldest-first.

    Returns a list of {"date", "value"} dicts (values are raw strings, may be ".").
    """
    params = {
        "series_id": series_id,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
        "api_key": api_key,
    }
    if units:
        params["units"] = units
    url = f"{FRED_BASE}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read())
    observations = [
        {"date": o["date"], "value": o["value"]}
        for o in payload.get("observations", [])
    ]
    observations.reverse()
    return observations
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_fred.py -v`
Expected: PASS (2 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/fred.py scripts/tests/test_fred.py
git commit -m "feat: add FRED fetch module with units transform"
```

---

### Task 10: Config — dataclasses + Recession Watch lens

**Files:**
- Create: `scripts/lenses/config.py`
- Test: `scripts/tests/test_build.py` (config assertions; build added next task)

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_build.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestConfig(unittest.TestCase):
    def test_recession_watch_lens_present(self):
        ids = [lens.id for lens in config.LENSES]
        self.assertIn("recession-watch", ids)

    def test_indicator_fetch_key(self):
        lens = next(l for l in config.LENSES if l.id == "recession-watch")
        ind = lens.indicators[0]
        self.assertEqual(ind.fetch_key, f"{ind.series_id}:lin")

    def test_every_indicator_has_rule_and_context(self):
        for lens in config.LENSES:
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `python scripts/tests/test_build.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lenses.config'`)

- [ ] **Step 3: Implement**

`scripts/lenses/config.py`:
```python
"""Lens configuration — the single source of truth for what gets built."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import narrative

# Helper series fetched but not displayed directly.
USREC_KEY = "USREC:lin"
USREC_LIMIT = 240  # ~20 years of monthly data, enough to shade recent charts


@dataclass(frozen=True)
class Indicator:
    id: str
    title: str
    short: str            # compact label for hub key-stats
    unit: str
    color: str
    series_id: str
    limit: int
    rule: Callable        # (cleaned_obs) -> (text, status)
    context: str          # evergreen "what it is" copy
    units_transform: Optional[str] = None

    @property
    def fetch_key(self):
        return f"{self.series_id}:{self.units_transform or 'lin'}"


@dataclass(frozen=True)
class Lens:
    id: str
    title: str
    accent: str
    indicators: list = field(default_factory=list)


RECESSION_WATCH = Lens(
    id="recession-watch",
    title="Recession Watch",
    accent="#F87171",
    indicators=[
        Indicator(
            id="yield-curve",
            title="Yield Curve · 10-Year minus 2-Year",
            short="Yield curve",
            unit="%",
            color="#F87171",
            series_id="T10Y2Y",
            limit=2600,  # ~10y daily
            rule=narrative.rule_yield_curve,
            context=(
                "The gap between 10-year and 2-year Treasury yields. When it goes "
                "negative (“inverts”), investors expect rate cuts ahead — and "
                "every U.S. recession since the 1970s was preceded by an inversion."
            ),
        ),
        Indicator(
            id="sahm-rule",
            title="Sahm Rule Recession Indicator",
            short="Sahm rule",
            unit="",
            color="#FBBF24",
            series_id="SAHMREALTIME",
            limit=240,
            rule=narrative.rule_sahm,
            context=(
                "A real-time recession alarm built from unemployment: it trips when the "
                "3-month average jobless rate rises 0.5 points above its prior-year low. "
                "It has flagged every recession since 1970 with almost no false alarms."
            ),
        ),
        Indicator(
            id="jobless-claims",
            title="Initial Jobless Claims · weekly",
            short="Jobless claims",
            unit="",
            color="#34D399",
            series_id="ICSA",
            limit=520,  # ~10y weekly
            rule=narrative.rule_claims,
            context=(
                "How many people filed for unemployment benefits last week — the "
                "freshest read on layoffs. A sustained climb is one of the earliest "
                "signs of a weakening economy."
            ),
        ),
        Indicator(
            id="unemployment",
            title="Unemployment Rate",
            short="Unemployment",
            unit="%",
            color="#38BDF8",
            series_id="UNRATE",
            limit=240,
            rule=narrative.rule_unemployment_trend,
            context=(
                "The share of the labor force without a job and looking. A steady, "
                "sustained rise off its lows is a hallmark of an economy tipping into "
                "recession."
            ),
        ),
    ],
)

LENSES = [RECESSION_WATCH]
```

- [ ] **Step 4: Run to verify it passes**

Run: `python scripts/tests/test_build.py -v`
Expected: PASS (3 tests ok)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/config.py scripts/tests/test_build.py
git commit -m "feat: add lens config and Recession Watch definition"
```

---

### Task 11: Build — assemble lens JSON, hub index, write files

**Files:**
- Create: `scripts/lenses/build.py`
- Create: `scripts/tests/fixtures/fetched_sample.json`
- Modify: `scripts/tests/test_build.py`

- [ ] **Step 1: Create the fixture** (offline sample of fetched data)

`scripts/tests/fixtures/fetched_sample.json`:
```json
{
  "T10Y2Y:lin": [
    {"date": "2024-01-01", "value": "-0.40"},
    {"date": "2025-01-01", "value": "0.05"},
    {"date": "2026-06-02", "value": "0.30"}
  ],
  "SAHMREALTIME:lin": [
    {"date": "2026-04-01", "value": "0.37"},
    {"date": "2026-05-01", "value": "0.43"}
  ],
  "ICSA:lin": [
    {"date": "2026-05-24", "value": "215000"},
    {"date": "2026-05-31", "value": "219000"}
  ],
  "UNRATE:lin": [
    {"date": "2025-06-01", "value": "3.7"},
    {"date": "2026-01-01", "value": "4.0"},
    {"date": "2026-05-01", "value": "4.2"}
  ],
  "USREC:lin": [
    {"date": "2020-02-01", "value": "1"},
    {"date": "2020-05-01", "value": "0"},
    {"date": "2026-05-01", "value": "0"}
  ]
}
```

- [ ] **Step 2: Add the failing tests** (append before the `if __name__` block in `scripts/tests/test_build.py`)

```python
import json as _json
from lenses import build


def _load_fixture():
    p = pathlib.Path(__file__).resolve().parent / "fixtures" / "fetched_sample.json"
    return _json.loads(p.read_text(encoding="utf-8"))


class TestBuildLens(unittest.TestCase):
    def setUp(self):
        self.fetched = _load_fixture()
        self.lens_json = build.build_lens(config.RECESSION_WATCH, self.fetched)

    def test_top_level_shape(self):
        lj = self.lens_json
        self.assertEqual(lj["id"], "recession-watch")
        self.assertEqual(lj["status"], "watch")  # un-inverted curve + near-trigger Sahm
        self.assertIn("warning lights", lj["headline_read"])
        self.assertEqual(len(lj["indicators"]), 4)
        self.assertEqual(lj["recessions"], [{"start": "2020-02-01", "end": "2020-05-01"}])

    def test_indicator_shape(self):
        ind = self.lens_json["indicators"][0]
        self.assertEqual(ind["id"], "yield-curve")
        self.assertEqual(ind["latest"], {"date": "2026-06-02", "value": "0.30"})
        self.assertEqual(ind["signal_status"], "watch")
        self.assertTrue(ind["context"])
        self.assertIn("un-inverted", ind["read"])
        self.assertTrue(len(ind["observations"]) == 3)


class TestBuildIndex(unittest.TestCase):
    def test_index_entry(self):
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        idx = build.build_index([lj])
        entry = idx["lenses"][0]
        self.assertEqual(entry["id"], "recession-watch")
        self.assertEqual(entry["status"], "watch")
        self.assertEqual(entry["key_stats"][0]["k"], "Yield curve")
        self.assertTrue(entry["sparkline"])  # non-empty list of numbers


class TestWriteOutputs(unittest.TestCase):
    def test_skips_unchanged_file(self):
        import tempfile
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            first = build.write_lens_file(out / "recession-watch.json", lj)
            second = build.write_lens_file(out / "recession-watch.json", lj)
            self.assertTrue(first)    # wrote
            self.assertFalse(second)  # unchanged -> skipped
```

- [ ] **Step 3: Run to verify it fails**

Run: `python scripts/tests/test_build.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'lenses.build'`)

- [ ] **Step 4: Implement**

`scripts/lenses/build.py`:
```python
"""Assemble lens JSON + hub index from config and fetched data; write to disk."""

import json
from datetime import datetime, timezone

from . import config, narrative, recessions, util


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latest_raw(raw):
    """Last observation with a real (non-null) value."""
    for obs in reversed(raw):
        if obs["value"] not in (None, "."):
            return {"date": obs["date"], "value": obs["value"]}
    return None


def _fmt(value, unit):
    f = util.to_float(value)
    if f is None:
        return "—"
    return f"{f:.2f}{unit}"


def build_lens(lens, fetched):
    """Build the full JSON dict for one lens."""
    indicators = []
    statuses = []
    for ind in lens.indicators:
        raw = fetched.get(ind.fetch_key, [])
        cleaned = util.clean(raw)
        text, status = ind.rule(cleaned)
        statuses.append(status)
        indicators.append({
            "id": ind.id,
            "title": ind.title,
            "short": ind.short,
            "unit": ind.unit,
            "color": ind.color,
            "series_id": ind.series_id,
            "observations": raw,
            "latest": _latest_raw(raw),
            "context": ind.context,
            "read": text,
            "signal_status": status,
        })
    headline, overall = narrative.synthesize(lens.id, statuses)
    return {
        "id": lens.id,
        "title": lens.title,
        "accent": lens.accent,
        "last_updated": _now(),
        "status": overall,
        "headline_read": headline,
        "recessions": recessions.recession_periods(fetched.get(config.USREC_KEY, [])),
        "indicators": indicators,
    }


def build_index(lens_jsons):
    """Build the hub index from already-built lens JSONs."""
    lenses = []
    for lj in lens_jsons:
        primary = lj["indicators"][0]
        spark = [
            util.to_float(o["value"])
            for o in primary["observations"]
            if o["value"] not in (None, ".")
        ][-40:]
        key_stats = []
        for ind in lj["indicators"][:2]:
            if ind["latest"]:
                key_stats.append({"k": ind["short"], "v": _fmt(ind["latest"]["value"], ind["unit"])})
        lenses.append({
            "id": lj["id"],
            "title": lj["title"],
            "accent": lj["accent"],
            "status": lj["status"],
            "headline_read": lj["headline_read"],
            "key_stats": key_stats,
            "sparkline": spark,
        })
    return {"last_updated": _now(), "lenses": lenses}


def _strip_volatile(d):
    out = dict(d)
    out.pop("last_updated", None)
    return out


def write_lens_file(path, lens_json):
    """Write a lens/index JSON, skipping if data (ignoring last_updated) is unchanged.

    Returns True if written, False if skipped.
    """
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if _strip_volatile(existing) == _strip_volatile(lens_json):
                return False
        except (ValueError, OSError):
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lens_json, indent=2) + "\n", encoding="utf-8")
    return True


def write_outputs(lens_jsons, out_dir):
    """Write each lens file + index.json. Returns list of paths actually written."""
    written = []
    for lj in lens_jsons:
        path = out_dir / f"{lj['id']}.json"
        if write_lens_file(path, lj):
            written.append(path)
    index_path = out_dir / "index.json"
    if write_lens_file(index_path, build_index(lens_jsons)):
        written.append(index_path)
    return written
```

- [ ] **Step 5: Run to verify it passes**

Run: `python scripts/tests/test_build.py -v`
Expected: PASS (config tests + 4 build tests ok)

- [ ] **Step 6: Commit**

```bash
git add scripts/lenses/build.py scripts/tests/fixtures/fetched_sample.json scripts/tests/test_build.py
git commit -m "feat: assemble lens JSON and hub index, write with unchanged-skip"
```

---

### Task 12: Entry point `refresh_lenses.py` (live + `--dry-run`)

**Files:**
- Create: `scripts/refresh_lenses.py`

- [ ] **Step 1: Implement** (no new unit test — validated by the dry-run command in Step 2; it reuses already-tested modules)

`scripts/refresh_lenses.py`:
```python
#!/usr/bin/env python3
"""Fetch FRED data for all lenses and write data/lenses/*.json.

Usage:
  python scripts/refresh_lenses.py            # live (needs FRED_API_KEY)
  python scripts/refresh_lenses.py --dry-run  # offline, uses test fixture data
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `lenses` importable
from lenses import build, config, fred

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "lenses"
FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fetched_sample.json"


def unique_specs(lenses):
    """Map fetch_key -> (series_id, units_transform, max_limit) across all lenses."""
    specs = {}
    for lens in lenses:
        for ind in lens.indicators:
            cur = specs.get(ind.fetch_key)
            limit = ind.limit if cur is None else max(cur[2], ind.limit)
            specs[ind.fetch_key] = (ind.series_id, ind.units_transform, limit)
    return specs


def fetch_all(lenses, api_key):
    """Fetch every needed series once. Returns (fetched, failed_keys)."""
    fetched, failed = {}, set()
    for key, (series_id, units, limit) in unique_specs(lenses).items():
        try:
            fetched[key] = fred.fetch_observations(series_id, api_key, limit, units)
        except Exception as exc:  # noqa: BLE001 - keep going, skip dependent lenses
            print(f"WARN: fetch failed for {series_id}: {exc}", file=sys.stderr)
            failed.add(key)
    try:
        fetched[config.USREC_KEY] = fred.fetch_observations("USREC", api_key, config.USREC_LIMIT)
    except Exception as exc:  # noqa: BLE001 - shading is non-critical
        print(f"WARN: USREC fetch failed: {exc}", file=sys.stderr)
        fetched[config.USREC_KEY] = []
    return fetched, failed


def lens_ready(lens, failed):
    return not any(ind.fetch_key in failed for ind in lens.indicators)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    args = parser.parse_args(argv)

    if args.dry_run:
        fetched = json.loads(FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.LENSES, api_key)

    ready = [lens for lens in config.LENSES if lens_ready(lens, failed)]
    for lens in config.LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No lenses could be built", file=sys.stderr)
        return 2

    lens_jsons = [build.build_lens(lens, fetched) for lens in ready]
    written = build.write_outputs(lens_jsons, OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all lens data up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the dry-run to verify it builds files offline**

Run: `python scripts/refresh_lenses.py --dry-run`
Expected: prints `Wrote .../data/lenses/recession-watch.json` and `Wrote .../data/lenses/index.json` on first run.

- [ ] **Step 3: Verify the generated JSON looks right**

Run: `python -c "import json;d=json.load(open('data/lenses/recession-watch.json'));print(d['status'], '|', d['headline_read']); print([i['id'] for i in d['indicators']])"`
Expected: `watch | No recession underway — but the warning lights are no longer all green.` and the four indicator ids.

- [ ] **Step 4: Run the full test suite**

Run: `python -m unittest discover -s scripts/tests -p "test_*.py" -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit** (commit the script; the dry-run JSON will be overwritten by the first live run, but committing it gives the frontend something to load immediately)

```bash
git add scripts/refresh_lenses.py data/lenses/
git commit -m "feat: add refresh_lenses entry point with dry-run and fetch resilience"
```

---

### Task 13: Shared stylesheet `dashboards/lens.css`

**Files:**
- Create: `dashboards/lens.css`

(Ported from the approved mockup `.superpowers/brainstorm/.../lens-page.html`. No logic; verified visually in Task 16.)

- [ ] **Step 1: Create the stylesheet**

`dashboards/lens.css`:
```css
:root{
  --bg:#0A0E14;--panel:#0F172A;--border:#1E293B;--text:#F8FAFC;--muted:#94A3B8;
  --dim:#64748B;--faint:#475569;--blue:#38BDF8;--green:#34D399;--amber:#FBBF24;--red:#F87171;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}
body{background:var(--bg);color:var(--text);line-height:1.5;font-feature-settings:"ss01","cv11";
  font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif;padding:5rem 1.5rem 4rem}
nav.wordmark{position:fixed;top:1.5rem;left:1.5rem;z-index:10}
nav.top-nav{position:fixed;top:1.5rem;right:1.5rem;z-index:10;display:flex;gap:1.75rem}
nav a{color:var(--muted);text-decoration:none;font-size:.875rem;letter-spacing:.05em;text-transform:uppercase;
  font-weight:500;padding:.5rem .25rem;border-bottom:1px solid transparent;transition:color .2s,border-color .2s}
nav a:hover,nav a:focus-visible{color:var(--text);border-bottom-color:var(--blue)}
main{max-width:48rem;margin:0 auto}
.back{display:inline-block;color:var(--dim);font-size:.78rem;text-decoration:none;margin-bottom:1.25rem;letter-spacing:.03em}
.back:hover{color:var(--blue)}
.eyebrow{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.14em}
.read-hero{font-size:clamp(1.5rem,3.5vw,2rem);font-weight:600;letter-spacing:-.02em;line-height:1.2;margin:.5rem 0 .75rem;max-width:36rem}
.badgerow{display:flex;align-items:center;gap:.75rem;flex-wrap:wrap}
.badge{font-size:.66rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;padding:3px 10px;border-radius:999px}
.badge.ok{background:#16261f;color:var(--green)} .badge.watch{background:#2c2517;color:var(--amber)}
.badge.elevated{background:#3a2a17;color:#FB923C} .badge.alert{background:#3b1f24;color:var(--red)}
.badge.unknown{background:#1d2433;color:var(--dim)}
.updated{font-size:.72rem;color:var(--dim)}
.scoreboard{display:grid;grid-template-columns:repeat(4,1fr);gap:.625rem;margin:1.5rem 0 .5rem}
@media(max-width:620px){.scoreboard{grid-template-columns:1fr 1fr}}
.signal{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:.75rem}
.signal .k{font-size:.62rem;text-transform:uppercase;letter-spacing:.07em;color:var(--dim)}
.signal .v{font-size:1.15rem;font-weight:600;margin:.25rem 0 .125rem}
.signal .s{font-size:.66rem;font-weight:600}
.s.ok{color:var(--green)} .s.watch{color:var(--amber)} .s.elevated{color:#FB923C} .s.alert{color:var(--red)} .s.unknown{color:var(--dim)}
.ind{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:1.375rem;margin-top:1.125rem}
.ind-top{display:flex;justify-content:space-between;align-items:flex-start;gap:.75rem}
.ind-title{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:600}
.ind-val{font-size:1.5rem;font-weight:600;letter-spacing:-.01em}
.ranges{display:flex;gap:.375rem;margin:.625rem 0 .375rem;align-items:center}
.ranges button{font:inherit;font-size:.68rem;color:var(--dim);background:transparent;border:1px solid var(--border);
  border-radius:6px;padding:3px 9px;cursor:pointer;transition:.15s}
.ranges button:hover{color:var(--text)}
.ranges button.active{color:var(--bg);background:var(--muted);border-color:var(--muted);font-weight:600}
.chart-box{position:relative;height:200px;margin-top:.25rem}
.context{margin-top:1rem;display:grid;gap:.75rem}
.ctx-block .lbl{font-size:.64rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);margin-bottom:.1875rem}
.ctx-block.read .lbl{color:var(--amber)}
.ctx-block p{color:var(--muted);font-size:.9rem;line-height:1.6}
.foot{margin:1.875rem 0 .375rem;padding-top:1.125rem;border-top:1px solid var(--border);font-size:.74rem;color:var(--dim);line-height:1.6}
.foot a{color:var(--muted)}
.status-msg{text-align:center;color:var(--dim);font-size:.9rem;padding:4rem 0}
.status-msg.error{color:var(--red)}
@media(max-width:640px){body{padding:5rem 1rem 3rem}nav.top-nav{gap:1rem}}
```

- [ ] **Step 2: Commit**

```bash
git add dashboards/lens.css
git commit -m "feat: add shared lens stylesheet"
```

---

### Task 14: Shared renderer `dashboards/lens.js`

**Files:**
- Create: `dashboards/lens.js`

(Vanilla JS, depends on global `Chart` from the CDN. Builds all DOM from the lens JSON. Verified visually in Task 16.)

- [ ] **Step 1: Implement**

`dashboards/lens.js`:
```javascript
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
  function fmtVal(value, unit) {
    const f = parseFloat(value);
    return isNaN(f) ? "—" : f.toFixed(2) + unit;
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
        for (let i = labels.length - 1; i >= 0; i--) { if (labels[i] <= p.end) { i1 = i; break; } }
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
              label: ctx => ` ${ctx.parsed.y.toFixed(2)}${indicator.unit}`,
            },
          },
        },
        scales: {
          x: { type: "category", ticks: { maxTicksLimit: 7, color: "#64748B", font: { size: 11 },
                 callback(v) { const s = this.getLabelForValue(v); return s ? s.slice(0, 4) : s; } },
               grid: { display: false }, border: { color: "#1E293B" } },
          y: { ticks: { color: "#64748B", font: { size: 11 }, callback: v => v + indicator.unit },
               grid: { color: "#1E293B" }, border: { display: false } },
        },
      },
    });
  }

  function indicatorCard(indicator, recessions) {
    const el = document.createElement("div");
    el.className = "ind";
    const latest = indicator.latest ? fmtVal(indicator.latest.value, indicator.unit) : "—";
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
        <div class="v">${i.latest ? fmtVal(i.latest.value, i.unit) : "—"}</div>
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
```

- [ ] **Step 2: Commit**

```bash
git add dashboards/lens.js
git commit -m "feat: add shared lens renderer with range toggle and recession shading"
```

---

### Task 15: Recession Watch page stub

**Files:**
- Create: `dashboards/recession-watch.html`

- [ ] **Step 1: Implement**

`dashboards/recession-watch.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Recession Watch — Bailey Analytics</title>
  <meta name="description" content="A daily read on U.S. recession risk — yield curve, Sahm rule, jobless claims, and unemployment, from FRED.">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading…</div></main>
  <script src="/dashboards/lens.js"></script>
  <script>renderLens("/data/lenses/recession-watch.json");</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add dashboards/recession-watch.html
git commit -m "feat: add Recession Watch lens page"
```

---

### Task 16: Manual verification in the browser

**Files:** none (verification only)

- [ ] **Step 1: Ensure data exists**

Run: `python scripts/refresh_lenses.py --dry-run`
Expected: `data/lenses/recession-watch.json` and `index.json` exist.

- [ ] **Step 2: Serve the site locally**

Run: `python -m http.server 8000`
(Leave running; open a second terminal or stop with Ctrl+C when done.)

- [ ] **Step 3: Open the page and verify**

Open: `http://localhost:8000/dashboards/recession-watch.html`

Confirm against the approved mockup:
- Hero shows the headline read "No recession underway — but the warning lights are no longer all green." with an amber **watch** badge.
- Scoreboard shows four signals (Yield curve / Sahm rule / Jobless claims / Unemployment) with colored status words.
- Each indicator card shows: chart, "What it is", and "The read right now".
- The **1Y / 5Y / Max** buttons re-scale each chart (Max shows the 2020 recession band on time series that reach back that far).
- Hovering a chart shows a dark tooltip with the value.
- No console errors.

- [ ] **Step 4: Note** — if anything looks off, fix `lens.js`/`lens.css` and re-verify before continuing. Commit any fixes with `git commit -m "fix: <what>"`.

---

### Task 17: Wire the daily GitHub Action

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`

- [ ] **Step 1: Update the workflow** to also run the lenses pipeline and commit its output. Replace the "Fetch latest FRED data" and "Commit and push" steps with:

```yaml
      - name: Fetch latest FRED data (legacy dashboard)
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python scripts/refresh_fred.py

      - name: Fetch latest FRED data (lenses)
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python scripts/refresh_lenses.py

      - name: Commit and push if data changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          if [[ -n "$(git status --porcelain data/)" ]]; then
            git add data/
            git commit -m "chore: refresh FRED data ($(date -u +%Y-%m-%d))"
            git push
          else
            echo "No data changes — skipping commit."
          fi
```

- [ ] **Step 2: Validate the YAML locally**

Run: `python -c "import yaml,sys" 2>NUL || pip install pyyaml` then
Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/refresh-fred.yml')); print('YAML OK')"`
Expected: `YAML OK`
(If PyYAML isn't available and you don't want to install it, instead visually confirm indentation matches the surrounding steps.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/refresh-fred.yml
git commit -m "ci: refresh lenses data daily alongside legacy dashboard"
```

---

### Task 18: Final full-suite check

**Files:** none

- [ ] **Step 1: Run every test**

Run: `python -m unittest discover -s scripts/tests -p "test_*.py" -v`
Expected: all tests PASS, zero failures/errors.

- [ ] **Step 2: Confirm the working tree is clean and the branch is ready**

Run: `git status`
Expected: nothing to commit (all work committed across tasks).

---

## Self-review (completed during planning)

**Spec coverage check** (spec → task):
- §2 scope / non-goals (static, FRED-only, no AI) → respected throughout; no runtime model dependency anywhere.
- §4 indicator lineup (Recession Watch subset) → Task 10 config (T10Y2Y, SAHMREALTIME, ICSA, UNRATE) + USREC helper. *Other lenses' series are Phase 2.*
- §5 architecture / config-driven pipeline → Tasks 9–12.
- §6 data shapes (index.json + per-lens) → Task 11 `build_lens`/`build_index`, asserted in tests.
- §7 hybrid narrative (evergreen context + rule-based read + status) → Tasks 3–7 (rules), Task 10 (context), Task 11 (assembly).
- §8 UI (hero read, scoreboard, 3-part cards, range-toggle-every-chart, recession shading, hover) → Tasks 13–16.
- §9 resilience (fetch failure keeps prior data; unchanged-skip; frontend graceful failure) → Task 11 `write_lens_file` skip, Task 12 `lens_ready`/skip, Task 14 catch block.
- §10 testing (stdlib unittest; rules, assembly, dry-run) → Tasks 2–11 tests + Task 12 dry-run.
- §11 build order (Recession Watch first) → this whole plan is Phase 1.

**Placeholder scan:** none — every code/test step contains complete content.

**Type/name consistency:** verified — cleaned-obs `(date, float)` interface used identically by every rule and by `build_lens`; `fetch_key`/`USREC_KEY` keying consistent across `config`, `build`, `refresh_lenses`; `write_lens_file` name consistent across `build.py` and its test.

---

## Future plans (out of scope here — will be planned separately)

- **Phase 2:** add Cost of Money, Job Market, Cost of Living lenses — new `Indicator`/`Lens` config entries, evergreen copy, narrative rules (incl. `units=pc1` transforms and a `derive.py` for payroll MoM change), `HEADLINES` entries, and thin page stubs. Reuses everything built here; no new plumbing.
- **Phase 3:** build the hub page `dashboards/index.html` (consumes `index.json`), retire `dashboards/economic.html` (redirect), and remove `refresh_fred.py`/`data/economic.json` from the workflow once the lenses fully supersede them.

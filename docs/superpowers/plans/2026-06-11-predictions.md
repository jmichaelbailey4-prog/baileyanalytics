# Predictions & Track Record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** For every badge-driving indicator, publish a next-print prediction (point + empirical 80% band + plain-English why + implied badge) before the print exists, grade it against the first-observed actual when it lands, and display the running record on lens pages, a Track Record page, and the State of Things.

**Architecture:** A new `scripts/predictions/` package alongside (never inside) the stdlib lens pipeline. Two jobs: a weekly **tournament** (rolling-origin backtests over full live history pick a champion model + empirical bands per indicator → `data/predictions/models.json`) and a daily **grade-and-predict** (freeze first-print grades, footnote revisions, emit new open predictions → `data/predictions/{open,recent,track-record,ledger/YYYY}.json`). Browser surfaces are additive renderers over those baked files.

**Tech Stack:** Python 3.12, numpy/pandas/statsmodels (first third-party deps — new `requirements.txt`), unittest, vanilla JS, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-06-11-predictions-design.md`. Read it first.

**House rules that bind every task:** TDD (write the failing test first); never modify lens pipeline behavior (two additive lines in `lens.js` and one additive parameter in `state.py` are the only allowed touches, see Tasks 9–10); all writes under `data/predictions/` go through write-if-changed; per-indicator try/except in both jobs; absolute paths in commands (the session cwd is the parent of the repos). All test commands below abbreviate `REPO = C:/Users/jmich/Documents/Business/Repositories/baileyanalytics`.

**Run tests with:**
```powershell
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_predict_*.py" -v
```
(Substitute the specific `-p "test_predict_<module>.py"` per task.)

---

## File structure

Create:
- `requirements.txt` — numpy/pandas/statsmodels, pinned
- `scripts/predict.py` — CLI: `daily` / `tournament` subcommands, `--dry-run`
- `scripts/predictions/__init__.py` — empty
- `scripts/predictions/roster.py` — which indicators get predicted (derived from `lenses.config`)
- `scripts/predictions/cadence.py` — cadence inference, weekly resample of dailies, target/due dates
- `scripts/predictions/models.py` — the six models behind one interface + versions
- `scripts/predictions/backtest.py` — rolling-origin harness + tournament + empirical bands
- `scripts/predictions/explain.py` — plain-English "why" copy bank
- `scripts/predictions/ledger.py` — entry construction, file I/O, aggregates
- `scripts/predictions/grade.py` — actual matching, grading, revision footnotes
- `scripts/predictions/runner.py` — orchestration (fetch full history, tournament/daily loops)
- `scripts/tests/test_predict_roster.py`, `test_predict_cadence.py`, `test_predict_models.py`, `test_predict_backtest.py`, `test_predict_explain.py`, `test_predict_ledger.py`, `test_predict_grade.py`, `test_predict_runner.py`
- `scripts/tests/fixtures/predict_histories_sample.json`
- `dashboards/predict.js`, `dashboards/track-record.html`, `dashboards/track-record.js`
- `.github/workflows/tournament.yml`

Modify:
- `scripts/lenses/state.py` + `scripts/refresh_lenses.py` — watching block (additive param)
- `dashboards/lens.js` — two additive lines (indicator-id stamp + rendered event)
- `dashboards/state.js`, `dashboards/state.html` — watching section
- `dashboards/lens.css` — `.predict` block + track-record styles
- every lens page `*.html` — one `<script>` tag (harmless where no predictions exist)
- `.github/workflows/refresh-fred.yml` — pip install + daily step
- `CLAUDE.md`, the spec (one amendment), `about.html` (one sentence)

---

### Task 1: requirements.txt + roster

**Files:**
- Create: `requirements.txt`, `scripts/predictions/__init__.py`, `scripts/predictions/roster.py`
- Test: `scripts/tests/test_predict_roster.py`

The roster derives from `lenses.config.CATEGORIES` by rule, not by hand-list: skip the `banking` category, skip lenses in `narrative.NEUTRAL_LENSES`, keep only `source in ("fred","eia")` indicators with a non-computed route, and **probe each rule** to drop info-only indicators (an info rule returns `"info"` for any input; a severity rule never does). A commented `EXTRA_EXCLUDE` set covers anything the rules can't express. The test pins known members in/out — that's the auditable artifact.

- [ ] **Step 1: Write `requirements.txt`**

```
numpy==2.2.6
pandas==2.3.0
statsmodels==0.14.4
```

(If pip cannot resolve these exact pins on Python 3.12, take the nearest current stable of each and record the change in the commit message.)

Run: `pip install -r "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/requirements.txt"`
Expected: installs cleanly.

- [ ] **Step 2: Write the failing roster test**

`scripts/tests/test_predict_roster.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import roster  # noqa: E402


class TestRoster(unittest.TestCase):
    def setUp(self):
        self.entries = roster.build_roster()
        self.keys = {e.key for e in self.entries}

    def test_severity_fred_indicators_included(self):
        self.assertIn("economic/cost-of-living/cpi", self.keys)
        self.assertIn("economic/recession-watch/jobless-claims", self.keys)
        self.assertIn("markets/market-risk-sentiment/hy-spread", self.keys)
        self.assertIn("housing/housing-affordability/mortgage-rate", self.keys)

    def test_neutral_lenses_excluded(self):
        self.assertFalse(any(e.lens_id in ("market-scoreboard", "crypto-structure")
                             for e in self.entries))

    def test_info_indicators_excluded(self):
        self.assertNotIn("markets/market-liquidity/fed-balance-sheet", self.keys)
        self.assertNotIn("markets/market-liquidity/bank-reserves", self.keys)
        self.assertNotIn("economic/fiscal-health/receipts", self.keys)

    def test_banking_and_non_fred_eia_excluded(self):
        self.assertFalse(any(e.category == "banking" for e in self.entries))
        for e in self.entries:
            self.assertIn(e.indicator.source, ("fred", "eia"))

    def test_computed_eia_routes_excluded(self):
        # renewables-share etc. have no eia_route; they're injected/computed
        for e in self.entries:
            if e.indicator.source == "eia":
                self.assertTrue(e.indicator.eia_route)

    def test_duplicate_series_kept_per_lens_home(self):
        # unemployment appears in recession-watch AND job-market; both are
        # legitimate display homes — each gets its own (identical) prediction.
        self.assertIn("economic/recession-watch/unemployment", self.keys)
        self.assertIn("economic/job-market/unemployment", self.keys)

    def test_roster_is_reasonably_sized(self):
        self.assertGreater(len(self.entries), 40)
        self.assertLess(len(self.entries), 110)

    def test_keys_unique(self):
        self.assertEqual(len(self.keys), len(self.entries))


if __name__ == "__main__":
    unittest.main()
```

NOTE: `test_severity_fred_indicators_included` guesses two lens/indicator ids
(`housing-affordability/mortgage-rate`). Before running, open
`scripts/lenses/config.py`, find the real housing lens + mortgage indicator ids,
and correct the test to the actual ids. Same for any assertion that fails on a
naming mismatch — fix the *test's ids* against config.py, not the roster logic.

- [ ] **Step 3: Run to verify it fails**

Expected: `ModuleNotFoundError: No module named 'predictions'`.

- [ ] **Step 4: Implement `scripts/predictions/__init__.py`** (empty file) **and `scripts/predictions/roster.py`**

```python
"""Which indicators get predictions: derived from lenses.config by rule.

Rule (spec §2): we predict what can move a badge. Rostered iff the indicator's
source is fred/eia with a real fetchable route, its rule can emit severity
statuses (probed — info-only rules always return "info"), its lens is not
neutral, and its category is not banking (quarterly FDIC, deferred)."""

from dataclasses import dataclass

from lenses import config, narrative

# Hand exclusions for anything the rules can't express. Keep commented.
EXTRA_EXCLUDE = {
    # e.g. "economic/cost-of-money/fed-funds",
}

# Synthetic probe series: 40 years of monthly dates, gently trending + wavy so
# level/YoY/trend rules all see plausible numbers. Only the *status token* is
# inspected; info rules return "info" regardless of values.
def _probe_obs():
    out = []
    for i in range(480):
        year, month = 1986 + i // 12, 1 + i % 12
        out.append((f"{year:04d}-{month:02d}-01", 100.0 + i * 0.1 + (i % 7) * 0.3))
    return out


def _is_info_rule(rule):
    try:
        _, status = rule(_probe_obs())
    except Exception:  # noqa: BLE001 - a crashing probe never blocks the roster
        return False
    return status == "info"


@dataclass(frozen=True)
class RosterEntry:
    key: str          # "category/lens-id/indicator-id"
    category: str
    lens_id: str
    indicator: object  # the lenses.config Indicator


def build_roster():
    entries = []
    for cat in config.CATEGORIES:
        if cat["id"] == "banking":
            continue
        for lens in cat["lenses"]:
            if lens.id in narrative.NEUTRAL_LENSES:
                continue
            for ind in lens.indicators:
                if ind.source not in ("fred", "eia"):
                    continue
                if ind.source == "eia" and not ind.eia_route:
                    continue  # computed/injected (generation shares)
                key = f"{cat['id']}/{lens.id}/{ind.id}"
                if key in EXTRA_EXCLUDE:
                    continue
                if _is_info_rule(ind.rule):
                    continue
                entries.append(RosterEntry(key, cat["id"], lens.id, ind))
    return entries
```

- [ ] **Step 5: Run the test, fix id mismatches in the test per the NOTE, re-run until green**

- [ ] **Step 6: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add requirements.txt scripts/predictions/ scripts/tests/test_predict_roster.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(predictions): roster derived from lens config + first deps"
```

---

### Task 2: cadence, targets, due dates

**Files:**
- Create: `scripts/predictions/cadence.py`
- Test: `scripts/tests/test_predict_cadence.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import cadence  # noqa: E402


def _monthly(n, start_year=2020):
    return [(f"{start_year + i // 12:04d}-{1 + i % 12:02d}-01", float(i)) for i in range(n)]


class TestInfer(unittest.TestCase):
    def test_monthly(self):
        self.assertEqual(cadence.infer(_monthly(30)), "monthly")

    def test_weekly(self):
        obs = [(f"2026-{m:02d}-{d:02d}", 1.0) for m, d in
               [(1, 3), (1, 10), (1, 17), (1, 24), (1, 31), (2, 7), (2, 14), (2, 21), (2, 28), (3, 7)]]
        self.assertEqual(cadence.infer(obs), "weekly")

    def test_daily(self):
        obs = [(f"2026-03-{d:02d}", 1.0) for d in range(2, 28) if d % 7 not in (0, 1)]
        self.assertEqual(cadence.infer(obs), "daily")

    def test_quarterly(self):
        obs = [("2024-01-01", 1.0), ("2024-04-01", 1.0), ("2024-07-01", 1.0),
               ("2024-10-01", 1.0), ("2025-01-01", 1.0)]
        self.assertEqual(cadence.infer(obs), "quarterly")

    def test_eia_monthly_yyyy_mm(self):
        obs = [(f"2025-{m:02d}", 1.0) for m in range(1, 12)]
        self.assertEqual(cadence.infer(obs), "monthly")

    def test_annual(self):
        obs = [(f"{y}-01-01", 1.0) for y in range(2018, 2026)]
        self.assertEqual(cadence.infer(obs), "annual")


class TestWeeklyResample(unittest.TestCase):
    def test_last_obs_per_iso_week_dated_friday(self):
        obs = [("2026-06-01", 1.0), ("2026-06-02", 2.0), ("2026-06-03", 3.0),  # wk 23
               ("2026-06-08", 4.0), ("2026-06-09", 5.0)]                        # wk 24
        out = cadence.weekly_resample(obs)
        self.assertEqual(out, [("2026-06-05", 3.0), ("2026-06-12", 5.0)])


class TestNextPeriod(unittest.TestCase):
    def test_monthly(self):
        self.assertEqual(cadence.next_period("2026-05-01", "monthly"), "2026-06-01")
        self.assertEqual(cadence.next_period("2026-12-01", "monthly"), "2027-01-01")

    def test_eia_monthly(self):
        self.assertEqual(cadence.next_period("2026-05", "monthly"), "2026-06")

    def test_weekly(self):
        self.assertEqual(cadence.next_period("2026-06-06", "weekly"), "2026-06-13")

    def test_quarterly(self):
        self.assertEqual(cadence.next_period("2026-04-01", "quarterly"), "2026-07-01")
        self.assertEqual(cadence.next_period("2026-10-01", "quarterly"), "2027-01-01")


class TestDue(unittest.TestCase):
    def test_monthly_mid_following_month(self):
        self.assertEqual(cadence.due_estimate("2026-06-01", "monthly"), "2026-07-15")

    def test_weekly_five_days(self):
        self.assertEqual(cadence.due_estimate("2026-06-13", "weekly"), "2026-06-18")

    def test_quarterly_late_following_month(self):
        self.assertEqual(cadence.due_estimate("2026-04-01", "quarterly"), "2026-07-28")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails** (no module `cadence`)

- [ ] **Step 3: Implement `scripts/predictions/cadence.py`**

```python
"""Cadence inference + target/due dates. Dates are ISO strings throughout
(EIA monthly uses 'YYYY-MM'). Daily series are resampled to weekly (last
observation of each ISO week, dated that week's Friday) — predicting tomorrow
on a daily series is churn without insight (spec §2)."""

from datetime import date, timedelta

SEASON = {"weekly": 52, "monthly": 12, "quarterly": 4, "annual": 1, "daily": 52}
PERIOD_NOUN = {"weekly": "week", "monthly": "month", "quarterly": "quarter", "daily": "week"}


def _parse(d):
    parts = d.split("-")
    if len(parts) == 2:  # EIA "YYYY-MM"
        return date(int(parts[0]), int(parts[1]), 1)
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def infer(obs):
    """Cadence from the median gap of the last ~12 observations."""
    if len(obs) < 3:
        return "unknown"
    dates = [_parse(d) for d, _ in obs[-13:]]
    gaps = sorted((b - a).days for a, b in zip(dates, dates[1:]))
    med = gaps[len(gaps) // 2]
    if med <= 4:
        return "daily"
    if med <= 10:
        return "weekly"
    if med <= 45:
        return "monthly"
    if med <= 130:
        return "quarterly"
    return "annual"


def weekly_resample(obs):
    """[(date,val)] daily -> last obs per ISO week, dated that week's Friday."""
    out, cur_week, cur = [], None, None
    for d, v in obs:
        dt = _parse(d)
        wk = dt.isocalendar()[:2]
        if wk != cur_week:
            if cur is not None:
                out.append(cur)
            cur_week = wk
        friday = dt + timedelta(days=4 - dt.isocalendar()[2])
        cur = (friday.isoformat(), v)
    if cur is not None:
        out.append(cur)
    return out


def _is_yyyy_mm(d):
    return len(d) == 7


def next_period(last_date, cad):
    dt = _parse(last_date)
    if cad == "weekly" or cad == "daily":
        return (dt + timedelta(days=7)).isoformat()
    months = 3 if cad == "quarterly" else 1
    y, m = dt.year, dt.month + months
    if m > 12:
        y, m = y + 1, m - 12
    return f"{y:04d}-{m:02d}" if _is_yyyy_mm(last_date) else f"{y:04d}-{m:02d}-01"


def due_estimate(target_period, cad):
    """Approximate release date — rendered with '~' by the UI (no fake precision)."""
    dt = _parse(target_period)
    if cad in ("weekly", "daily"):
        return (dt + timedelta(days=5)).isoformat()
    if cad == "quarterly":
        y, m = (dt.year + 1, dt.month - 9) if dt.month + 3 > 12 else (dt.year, dt.month + 3)
        return f"{y:04d}-{m:02d}-28"
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return f"{y:04d}-{m:02d}-15"
```

- [ ] **Step 4: Run the test — all green** (`-p "test_predict_cadence.py"`)

- [ ] **Step 5: Commit** — `feat(predictions): cadence inference, weekly resample, target/due dates`

---

### Task 3: the model toolbox

**Files:**
- Create: `scripts/predictions/models.py`
- Test: `scripts/tests/test_predict_models.py`

One interface: `predict_one(name, values, season) -> float` (one step ahead). Models: `naive`, `seasonal-naive`, `drift`, `ets` (damped non-seasonal), `ets-seasonal`, `theta`, `sarima`. Versions live in `VERSIONS` and stamp every prediction.

- [ ] **Step 1: Write the failing test**

```python
import sys
import math
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import models  # noqa: E402

TREND = [100.0 + 2.0 * i for i in range(60)]                       # clean linear trend
SEASONAL = [100.0 + 2.0 * i + 10.0 * math.sin(2 * math.pi * i / 12) for i in range(72)]


class TestBaselines(unittest.TestCase):
    def test_naive(self):
        self.assertEqual(models.predict_one("naive", TREND, 12), TREND[-1])

    def test_seasonal_naive(self):
        self.assertEqual(models.predict_one("seasonal-naive", SEASONAL, 12), SEASONAL[-12])

    def test_seasonal_naive_short_history_falls_back_to_naive(self):
        self.assertEqual(models.predict_one("seasonal-naive", [1.0, 2.0], 12), 2.0)

    def test_drift_extends_trend(self):
        self.assertAlmostEqual(models.predict_one("drift", TREND, 12), TREND[-1] + 2.0, places=6)


class TestStatsmodels(unittest.TestCase):
    def test_ets_tracks_trend(self):
        p = models.predict_one("ets", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=1.0)

    def test_ets_seasonal_beats_naive_on_seasonal_series(self):
        p_seasonal = models.predict_one("ets-seasonal", SEASONAL, 12)
        truth = 100.0 + 2.0 * 72 + 10.0 * math.sin(2 * math.pi * 72 / 12)
        self.assertLess(abs(p_seasonal - truth), abs(SEASONAL[-1] - truth))

    def test_theta_runs(self):
        p = models.predict_one("theta", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=3.0)

    def test_sarima_runs(self):
        p = models.predict_one("sarima", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=3.0)

    def test_too_short_raises(self):
        with self.assertRaises(models.ModelError):
            models.predict_one("ets", [1.0, 2.0, 3.0], 1)

    def test_unknown_model_raises(self):
        with self.assertRaises(models.ModelError):
            models.predict_one("bogus", TREND, 1)

    def test_versions_cover_all_models(self):
        for name in models.MODEL_NAMES:
            self.assertIn(name, models.VERSIONS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Implement `scripts/predictions/models.py`**

```python
"""The model toolbox: six families behind one one-step-ahead interface.
All deterministic. Each family has a one-sentence explanation in explain.py —
a model that can't be explained in a sentence doesn't ship (brand rule)."""

import warnings

import numpy as np
import pandas as pd

VERSIONS = {"naive": 1, "seasonal-naive": 1, "drift": 1,
            "ets": 1, "ets-seasonal": 1, "theta": 1, "sarima": 1}
MODEL_NAMES = tuple(VERSIONS)
BASELINES = ("naive", "seasonal-naive", "drift")
MIN_POINTS = 24          # statsmodels families need real history
TRAIN_WINDOW = 480       # cap fits at the trailing window: faster, recent-weighted


class ModelError(Exception):
    pass


def _naive(v, s):
    return v[-1]


def _seasonal_naive(v, s):
    return v[-s] if s > 1 and len(v) >= s else v[-1]


def _drift(v, s):
    if len(v) < 2:
        return v[-1]
    return v[-1] + (v[-1] - v[0]) / (len(v) - 1)


def _ets(v, s, seasonal=False):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    arr = np.asarray(v, dtype=float)
    kwargs = {"trend": "add", "damped_trend": True}
    if seasonal:
        if s <= 1 or len(arr) < 2 * s + 4:
            raise ModelError("not enough history for a seasonal fit")
        kwargs.update(seasonal="add", seasonal_periods=s)
    fit = ExponentialSmoothing(arr, **kwargs).fit()
    return float(fit.forecast(1)[0])


def _theta(v, s):
    from statsmodels.tsa.forecasting.theta import ThetaModel
    series = pd.Series(np.asarray(v, dtype=float))
    deseasonalize = s > 1 and len(v) >= 2 * s
    fit = ThetaModel(series, period=max(s, 1), deseasonalize=deseasonalize).fit()
    return float(fit.forecast(1).iloc[0])


def _sarima(v, s):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    arr = np.asarray(v, dtype=float)
    seasonal_order = (0, 1, 1, s) if s > 1 and len(arr) >= 3 * s else (0, 0, 0, 0)
    fit = SARIMAX(arr, order=(1, 1, 1), seasonal_order=seasonal_order,
                  enforce_stationarity=False, enforce_invertibility=False
                  ).fit(disp=False, maxiter=50)
    return float(fit.forecast(1)[0])


_FAMILIES = {
    "naive": _naive,
    "seasonal-naive": _seasonal_naive,
    "drift": _drift,
    "ets": lambda v, s: _ets(v, s, seasonal=False),
    "ets-seasonal": lambda v, s: _ets(v, s, seasonal=True),
    "theta": _theta,
    "sarima": _sarima,
}


def predict_one(name, values, season):
    """One-step-ahead point forecast. Raises ModelError on anything unusable —
    callers treat that as 'this model sits this one out'."""
    fn = _FAMILIES.get(name)
    if fn is None:
        raise ModelError(f"unknown model {name!r}")
    v = [float(x) for x in values][-TRAIN_WINDOW:]
    if name not in BASELINES and len(v) < MIN_POINTS:
        raise ModelError(f"{name}: only {len(v)} points")
    if not v:
        raise ModelError("empty series")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = fn(v, int(season))
    except ModelError:
        raise
    except Exception as exc:  # noqa: BLE001 - statsmodels failure modes are many
        raise ModelError(f"{name}: {exc}") from exc
    if out is None or not np.isfinite(out):
        raise ModelError(f"{name}: non-finite forecast")
    return float(out)
```

- [ ] **Step 4: Run the test — green** (statsmodels convergence warnings are suppressed; the run may take ~20s)

- [ ] **Step 5: Commit** — `feat(predictions): model toolbox (naive/seasonal/drift/ets/theta/sarima)`

---

### Task 4: rolling-origin backtests + the tournament

**Files:**
- Create: `scripts/predictions/backtest.py`
- Test: `scripts/tests/test_predict_backtest.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import math
import pathlib
import random
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import backtest, models  # noqa: E402

random.seed(7)
SEASONAL = [100.0 + 0.5 * i + 8.0 * math.sin(2 * math.pi * i / 12)
            + random.gauss(0, 0.5) for i in range(240)]


class TestRollingOrigin(unittest.TestCase):
    def test_no_leakage_planted_break(self):
        # Flat at 100 then jumps to 1000 at index 150. A model standing at any
        # origin <= 150 must not benefit from post-break data: its prediction
        # must stay near 100, so the error AT the break is ~900 for every model.
        series = [100.0] * 150 + [1000.0] * 50
        for name in ("naive", "drift", "ets"):
            errors = backtest.rolling_errors(name, series, season=1,
                                             origins=backtest.pick_origins(len(series), 60))
            err_at_break = next(e for i, e in errors if i == 150)
            self.assertGreater(abs(err_at_break), 800.0,
                               f"{name} leaked future data across the break")

    def test_errors_are_signed_actual_minus_predicted(self):
        series = [1.0, 2.0, 3.0, 4.0, 5.0]
        errors = backtest.rolling_errors("naive", series, 1, [4])
        self.assertEqual(errors, [(4, 1.0)])  # actual 5.0 - naive 4.0


class TestTournament(unittest.TestCase):
    def test_seasonal_model_beats_naive_on_seasonal_series(self):
        result = backtest.tournament(SEASONAL, season=12, max_origins=60)
        self.assertNotIn(result["champion"], ("naive",))
        self.assertLess(result["mae"], result["snaive_mae"] + 1e-9)

    def test_random_walk_ships_baseline(self):
        rw = [0.0]
        for _ in range(299):
            rw.append(rw[-1] + random.gauss(0, 1))
        result = backtest.tournament(rw, season=1, max_origins=60)
        self.assertIn(result["champion"], models.BASELINES)

    def test_bands_cover_about_80pct(self):
        result = backtest.tournament(SEASONAL, season=12, max_origins=100)
        lo, hi = result["err_lo"], result["err_hi"]
        errors = [e for _, e in backtest.rolling_errors(
            result["champion"], SEASONAL, 12, backtest.pick_origins(len(SEASONAL), 100))]
        covered = sum(1 for e in errors if lo <= e <= hi) / len(errors)
        self.assertGreater(covered, 0.7)
        self.assertLess(covered, 0.95)

    def test_result_shape(self):
        r = backtest.tournament(SEASONAL, season=12, max_origins=40)
        for k in ("champion", "mae", "naive_mae", "snaive_mae",
                  "err_lo", "err_hi", "n_origins", "skill"):
            self.assertIn(k, r)
        self.assertLessEqual(r["err_lo"], 0.0)
        self.assertGreaterEqual(r["err_hi"], 0.0)

    def test_too_short_series_returns_none(self):
        self.assertIsNone(backtest.tournament([1.0] * 10, season=1, max_origins=40))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Implement `scripts/predictions/backtest.py`**

```python
"""Rolling-origin backtesting and the per-indicator tournament.

At each origin i, every model is fitted on values[:i] ONLY and predicts
values[i]. Champion = lowest MAE, but it ships only if it beats seasonal-naive
(spec §4) — otherwise the baseline itself ships, which is an honest prediction.
Bands are the empirical 10th–90th percentile of the champion's signed errors:
bands history earned, not parametric formulas. A model failing >10% of its
origins is disqualified for that series."""

from . import models

MIN_TRAIN = 36           # smallest training slice an origin may stand on
ERR_QUANTILES = (0.10, 0.90)
MAX_FAIL_SHARE = 0.10


def pick_origins(n, max_origins):
    """The last `max_origins` indices that leave >= MIN_TRAIN training points."""
    first = max(MIN_TRAIN, n - max_origins)
    return list(range(first, n))


def rolling_errors(name, values, season, origins):
    """[(origin_index, signed_error actual-minus-predicted)] — failures skipped."""
    out = []
    for i in origins:
        try:
            p = models.predict_one(name, values[:i], season)
        except models.ModelError:
            continue
        out.append((i, values[i] - p))
    return out


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    pos = q * (len(sorted_vals) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def tournament(values, season, max_origins):
    """Run every model through the same origins; return the champion record
    (spec §4 models.json fields) or None when the series is too short."""
    n = len(values)
    if n < MIN_TRAIN + 5:
        return None
    origins = pick_origins(n, max_origins)
    maes, errors_by_model = {}, {}
    for name in models.MODEL_NAMES:
        errs = rolling_errors(name, values, season, origins)
        if len(errs) < len(origins) * (1 - MAX_FAIL_SHARE):
            continue  # disqualified: too flaky for this series
        abs_errs = [abs(e) for _, e in errs]
        maes[name] = sum(abs_errs) / len(abs_errs)
        errors_by_model[name] = [e for _, e in errs]
    if "naive" not in maes:
        return None
    snaive_mae = maes.get("seasonal-naive", maes["naive"])
    champion = min(maes, key=maes.get)
    if maes[champion] >= snaive_mae and champion not in models.BASELINES:
        champion = "seasonal-naive" if "seasonal-naive" in maes else "naive"
    errs = sorted(errors_by_model[champion])
    err_lo = min(_quantile(errs, ERR_QUANTILES[0]), 0.0)
    err_hi = max(_quantile(errs, ERR_QUANTILES[1]), 0.0)
    return {
        "champion": champion,
        "mae": maes[champion],
        "naive_mae": maes["naive"],
        "snaive_mae": snaive_mae,
        "err_lo": err_lo,
        "err_hi": err_hi,
        "n_origins": len(errors_by_model[champion]),
        "skill": 1.0 - (maes[champion] / snaive_mae) if snaive_mae > 0 else 0.0,
    }
```

- [ ] **Step 4: Run the test — green** (this file is the slow one, ~1–3 min; that's the SARIMA refits)

- [ ] **Step 5: Commit** — `feat(predictions): rolling-origin backtests + champion tournament`

---

### Task 5: plain-English explanations

**Files:**
- Create: `scripts/predictions/explain.py`
- Test: `scripts/tests/test_predict_explain.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import explain, models  # noqa: E402


class TestStreak(unittest.TestCase):
    def test_rising_streak(self):
        self.assertEqual(explain.streak([1.0, 2.0, 3.0, 4.0]), ("risen", 3))

    def test_falling_streak(self):
        self.assertEqual(explain.streak([5.0, 4.0, 3.0]), ("fallen", 2))

    def test_no_streak(self):
        self.assertIsNone(explain.streak([1.0, 2.0, 1.5]))
        self.assertIsNone(explain.streak([1.0]))


class TestWhy(unittest.TestCase):
    def test_every_model_family_has_copy(self):
        for name in models.MODEL_NAMES:
            why = explain.why(name, "monthly", [1.0, 2.0, 1.5], "CPI")
            self.assertTrue(why and why[0].isupper() and why.endswith("."))

    def test_streak_lead_in(self):
        why = explain.why("ets-seasonal", "monthly", [1.0, 2.0, 3.0, 4.0], "CPI")
        self.assertIn("CPI has risen 3 straight months", why)

    def test_no_streak_no_lead_in(self):
        why = explain.why("naive", "weekly", [1.0, 2.0, 1.5], "Claims")
        self.assertNotIn("straight", why)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Implement `scripts/predictions/explain.py`**

```python
"""The plain-English 'why' behind every prediction (spec §4 copy bank).
One sentence, no black box: model-family skeleton + a simple momentum
diagnostic. Skeletons read as complete clauses after a semicolon."""

from .cadence import PERIOD_NOUN

SKELETONS = {
    "naive": "we expect roughly the last value — this series rarely rewards cleverness",
    "seasonal-naive": "we expect roughly what this series did a year ago this {period}",
    "drift": "this projects the series' long-run average step from today's level",
    "ets": "this projects the recent level and trend forward one {period}",
    "ets-seasonal": "this projects the recent trend with the usual seasonal pattern for the {period}",
    "theta": "this blends the series' long-run trend line with its recent level",
    "sarima": "this projects recent momentum, adjusted for the series' typical reversion",
}
MIN_STREAK = 2


def streak(values):
    """('risen'|'fallen', n) for the trailing run of strictly same-sign moves,
    or None when shorter than MIN_STREAK."""
    if len(values) < MIN_STREAK + 1:
        return None
    direction = None
    n = 0
    for prev, cur in zip(reversed(values[:-1]), reversed(values[1:])):
        # walk backwards pairwise: (last-1,last), (last-2,last-1), ...
        step = "risen" if cur > prev else "fallen" if cur < prev else None
        if step is None or (direction and step != direction):
            break
        direction = step
        n += 1
    return (direction, n) if direction and n >= MIN_STREAK else None


def why(model_name, cad, values, short_label):
    period = PERIOD_NOUN.get(cad, "period")
    body = SKELETONS.get(model_name, SKELETONS["naive"]).format(period=period)
    s = streak(values)
    if s:
        verb, n = s
        sentence = f"{short_label} has {verb} {n} straight {period}s; {body}."
    else:
        sentence = body[0].upper() + body[1:] + "."
    return sentence
```

- [ ] **Step 4: Run — green.** (If the zip-walk in `streak` confuses: it pairs `(values[i-1], values[i])` from the end backwards; first mismatch stops the run.)

- [ ] **Step 5: Commit** — `feat(predictions): plain-English why copy bank`

---

### Task 6: the ledger

**Files:**
- Create: `scripts/predictions/ledger.py`
- Test: `scripts/tests/test_predict_ledger.py`

All functions take an explicit `pred_dir` `Path` (testable with `tempfile`). Reuses `lenses.build.write_lens_file` for write-if-changed.

- [ ] **Step 1: Write the failing test**

```python
import json
import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import ledger  # noqa: E402


def _entry(key="economic/cost-of-living/cpi", target="2026-06-01", grade=None, made="2026-06-12T06:10:00Z"):
    return {"id": f"{key}@{target}", "key": key,
            "category": "economic", "lens": "cost-of-living", "indicator": "cpi",
            "series_id": "CPIAUCSL", "horizon": "next-print",
            "target_period": target, "due": "2026-07-15", "made_at": made,
            "model": "ets-seasonal@1", "point": 4.31, "lo": 4.02, "hi": 4.6,
            "unit": "%", "value_format": "decimal", "prev_value": 4.17,
            "why": "w", "implied_status": "elevated", "current_status": "elevated",
            "title": "Inflation · CPI (year-over-year)", "short": "CPI",
            "lens_title": "The Cost of Living", "href": "/dashboards/cost-of-living.html",
            "grade": grade}


def _grade(actual=4.17):
    return {"actual": actual, "graded_at": "2026-07-15T06:08:00Z", "hit": True,
            "abs_error": 0.14, "direction_hit": True, "status_hit": True,
            "naive_error": 0.31, "revised_to": None}


class TestLedgerIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_and_load_year_files(self):
        ledger.append_graded(self.dir, _entry(grade=_grade()))
        ledger.append_graded(self.dir, _entry(target="2026-07-01", grade=_grade()))
        rows = ledger.load_all_graded(self.dir)
        self.assertEqual(len(rows), 2)
        self.assertTrue((self.dir / "ledger" / "2026.json").exists())

    def test_append_is_idempotent_per_id(self):
        e = _entry(grade=_grade())
        ledger.append_graded(self.dir, e)
        ledger.append_graded(self.dir, e)
        self.assertEqual(len(ledger.load_all_graded(self.dir)), 1)

    def test_year_rollover(self):
        ledger.append_graded(self.dir, _entry(grade=_grade()))
        e2 = _entry(target="2027-01-01", grade=_grade())
        e2["made_at"] = "2027-01-05T06:00:00Z"
        ledger.append_graded(self.dir, e2)
        self.assertTrue((self.dir / "ledger" / "2027.json").exists())

    def test_open_write_skip_when_unchanged(self):
        wrote1 = ledger.write_open(self.dir, [_entry()])
        wrote2 = ledger.write_open(self.dir, [_entry()])
        self.assertTrue(wrote1)
        self.assertFalse(wrote2)
        data = json.loads((self.dir / "open.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["predictions"]), 1)


class TestAggregates(unittest.TestCase):
    def test_track_record_math(self):
        graded = [
            dict(_entry(grade=_grade()), grade=dict(_grade(), hit=True, abs_error=0.1, naive_error=0.2)),
            dict(_entry(target="2026-07-01"), grade=dict(_grade(), hit=False, abs_error=0.4,
                                                         naive_error=0.2, direction_hit=False, status_hit=False)),
        ]
        tr = ledger.track_record(graded)
        self.assertEqual(tr["graded"], 2)
        self.assertAlmostEqual(tr["calibration"], 0.5)
        self.assertAlmostEqual(tr["skill"], 1.0 - 0.5 / 0.4)  # 1 - sum(err)/sum(naive)
        self.assertAlmostEqual(tr["direction"], 0.5)
        self.assertAlmostEqual(tr["status"], 0.5)
        self.assertEqual(tr["categories"]["economic"]["graded"], 2)

    def test_recent_shape(self):
        graded = [dict(_entry(grade=_grade()), grade=dict(_grade()))]
        recent = ledger.recent(graded, feed_size=50)
        self.assertIn("economic/cost-of-living/cpi", recent["last"])
        self.assertEqual(len(recent["feed"]), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Implement `scripts/predictions/ledger.py`**

```python
"""Ledger I/O + aggregates. The ledger/YYYY.json files are the permanent
append-only record (append is idempotent per entry id; a graded entry is
frozen forever — spec §3). open/recent/track-record are derived views.
All writes reuse lenses.build.write_lens_file (write-if-changed)."""

import json
from datetime import datetime, timezone

from lenses import build


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _year_path(pred_dir, entry):
    return pred_dir / "ledger" / f"{entry['made_at'][:4]}.json"


def _load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return default


def append_graded(pred_dir, entry):
    """Append one graded entry to its year file. Idempotent per id; an id that
    already exists is left untouched (first-print grades never mutate)."""
    path = _year_path(pred_dir, entry)
    rows = _load(path, [])
    if any(r.get("id") == entry["id"] for r in rows):
        return False
    rows.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return True


def set_revision(pred_dir, entry_id, made_year, revised_to):
    """The one sanctioned mutation: fill grade.revised_to (footnote, spec §3)."""
    path = pred_dir / "ledger" / f"{made_year}.json"
    rows = _load(path, [])
    changed = False
    for r in rows:
        if r.get("id") == entry_id and r.get("grade") and r["grade"].get("revised_to") != revised_to:
            r["grade"]["revised_to"] = revised_to
            changed = True
    if changed:
        path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return changed


def load_all_graded(pred_dir):
    rows = []
    ledger_dir = pred_dir / "ledger"
    if ledger_dir.exists():
        for path in sorted(ledger_dir.glob("*.json")):
            rows.extend(_load(path, []))
    return rows


def write_open(pred_dir, entries):
    return build.write_lens_file(
        pred_dir / "open.json",
        {"generated_at": _now(), "predictions": entries})


def load_open(pred_dir):
    return _load(pred_dir / "open.json", {}).get("predictions", [])


def recent(graded, feed_size=50):
    """Last grade per key + a newest-first feed of recent grades."""
    by_made = sorted(graded, key=lambda e: e["grade"]["graded_at"])
    last = {}
    for e in by_made:
        last[e["key"]] = e
    return {"generated_at": _now(), "last": last, "feed": list(reversed(by_made))[:feed_size]}


def track_record(graded):
    """Aggregates recomputable by anyone from the ledger (spec §7)."""
    def _bucket(rows):
        n = len(rows)
        if not n:
            return {"graded": 0}
        s_err = sum(e["grade"]["abs_error"] for e in rows)
        s_naive = sum(e["grade"]["naive_error"] for e in rows)
        return {
            "graded": n,
            "calibration": sum(1 for e in rows if e["grade"]["hit"]) / n,
            "direction": sum(1 for e in rows if e["grade"]["direction_hit"]) / n,
            "status": sum(1 for e in rows if e["grade"]["status_hit"]) / n,
            "skill": (1.0 - s_err / s_naive) if s_naive > 0 else 0.0,
        }
    cats = {}
    for e in graded:
        cats.setdefault(e["category"], []).append(e)
    out = {"generated_at": _now(), "since": min((e["made_at"] for e in graded), default=None)}
    out.update(_bucket(graded))
    out["categories"] = {c: _bucket(rows) for c, rows in sorted(cats.items())}
    return out


def write_views(pred_dir, open_entries, graded):
    """Write open.json, recent.json, track-record.json (all write-if-changed)."""
    wrote = []
    if write_open(pred_dir, open_entries):
        wrote.append("open.json")
    if build.write_lens_file(pred_dir / "recent.json", recent(graded)):
        wrote.append("recent.json")
    if build.write_lens_file(pred_dir / "track-record.json", track_record(graded)):
        wrote.append("track-record.json")
    return wrote
```

- [ ] **Step 4: Run — green** (`build.write_lens_file` ignores `generated_at` via `_strip_volatile`, so the skip test passes)

- [ ] **Step 5: Commit** — `feat(predictions): append-only ledger + derived views`

---

### Task 7: grading

**Files:**
- Create: `scripts/predictions/grade.py`
- Test: `scripts/tests/test_predict_grade.py`

- [ ] **Step 1: Write the failing test**

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import grade  # noqa: E402


def _open_entry(point=4.31, lo=4.02, hi=4.6, prev=4.17, target="2026-06-01"):
    return {"id": f"economic/cost-of-living/cpi@{target}", "key": "economic/cost-of-living/cpi",
            "target_period": target, "point": point, "lo": lo, "hi": hi,
            "prev_value": prev, "implied_status": "elevated", "grade": None}


CLEANED = [("2026-04-01", 3.78), ("2026-05-01", 4.17), ("2026-06-01", 4.30)]


class TestMatchActual(unittest.TestCase):
    def test_first_obs_at_or_after_target(self):
        self.assertEqual(grade.match_actual(CLEANED, "2026-06-01"), ("2026-06-01", 4.30))

    def test_holiday_shifted_date_still_matches(self):
        obs = [("2026-06-06", 1.0), ("2026-06-14", 2.0)]  # target Sat slid to Sun
        self.assertEqual(grade.match_actual(obs, "2026-06-13"), ("2026-06-14", 2.0))

    def test_not_arrived_returns_none(self):
        self.assertIsNone(grade.match_actual(CLEANED, "2026-07-01"))

    def test_double_print_grades_only_target(self):
        # cron skipped a day; two new prints exist. First obs >= target IS the target print.
        obs = CLEANED + [("2026-07-01", 4.4)]
        self.assertEqual(grade.match_actual(obs, "2026-06-01"), ("2026-06-01", 4.30))


class TestGradeEntry(unittest.TestCase):
    def test_hit_inside_band(self):
        g = grade.grade_entry(_open_entry(), 4.30, "elevated")
        self.assertTrue(g["hit"])
        self.assertAlmostEqual(g["abs_error"], 0.01, places=6)
        self.assertTrue(g["direction_hit"])   # predicted up (4.31>4.17), actual up
        self.assertTrue(g["status_hit"])
        self.assertAlmostEqual(g["naive_error"], 0.13, places=6)  # |4.30-4.17|
        self.assertIsNone(g["revised_to"])

    def test_miss_outside_band(self):
        g = grade.grade_entry(_open_entry(), 4.9, "alert")
        self.assertFalse(g["hit"])
        self.assertFalse(g["status_hit"])

    def test_direction_flat_epsilon(self):
        e = _open_entry(point=4.17)            # predicted flat
        g = grade.grade_entry(e, 4.17, "elevated")
        self.assertTrue(g["direction_hit"])    # both flat -> hit
        g2 = grade.grade_entry(e, 4.5, "elevated")
        self.assertFalse(g2["direction_hit"])  # predicted flat, actual up


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Implement `scripts/predictions/grade.py`**

```python
"""Grading: match the first-observed actual, freeze the grade (spec §3).
The actual for a target is the FIRST observation dated >= target_period —
robust to holiday-shifted dates and to a skipped cron delivering two prints
(the first new print is still the one the prediction targeted)."""

from datetime import datetime, timezone

FLAT_EPS = 1e-9


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def match_actual(cleaned, target_period):
    """First (date, value) at/after target_period, or None if not yet printed.
    EIA 'YYYY-MM' and full ISO dates both compare correctly as strings only
    within a series, and series never mix formats."""
    for d, v in cleaned:
        if d >= target_period:
            return (d, v)
    return None


def _direction(delta):
    if abs(delta) < FLAT_EPS:
        return "flat"
    return "up" if delta > 0 else "down"


def grade_entry(entry, actual, actual_status):
    """The frozen grade block. naive_error = what guessing the last known value
    (prev_value at made_at) would have missed by — stored so the skill stat is
    recomputable from the ledger by anyone."""
    prev = entry["prev_value"]
    return {
        "actual": actual,
        "graded_at": _now(),
        "hit": entry["lo"] <= actual <= entry["hi"],
        "abs_error": abs(actual - entry["point"]),
        "direction_hit": _direction(entry["point"] - prev) == _direction(actual - prev),
        "status_hit": entry["implied_status"] == actual_status,
        "naive_error": abs(actual - prev),
        "revised_to": None,
    }
```

- [ ] **Step 4: Run — green**

- [ ] **Step 5: Commit** — `feat(predictions): first-print grading with frozen grades`

---

### Task 8: runner + CLI

**Files:**
- Create: `scripts/predictions/runner.py`, `scripts/predict.py`, `scripts/tests/fixtures/predict_histories_sample.json`
- Test: `scripts/tests/test_predict_runner.py`

The runner owns: full-history fetch (FRED `limit=100000`; EIA `max(ind.limit, 2000)`), derive + optional weekly resample, the tournament loop, and the daily grade→footnote→predict loop. Per-indicator try/except everywhere. Revision look-back: entries graded within the last 3 of their periods.

- [ ] **Step 1: Build the fixture**

`scripts/tests/fixtures/predict_histories_sample.json` — synthetic full histories keyed like the roster keys the dry run will serve. Generate it with a throwaway script (do not hand-type 200 points):

```python
# scratch: python - <<'EOF' style generation, run once, output committed
import json, math, random
random.seed(11)
def monthly(n, base, trend, amp):
    out, y, m = [], 2008, 1
    for i in range(n):
        out.append({"date": f"{y:04d}-{m:02d}-01",
                    "value": f"{base + trend*i + amp*math.sin(2*math.pi*i/12) + random.gauss(0,0.2):.2f}"})
        m += 1
        if m > 12: y, m = y+1, 1
    return out
def weekly(n, base):
    from datetime import date, timedelta
    out, d = [], date(2016, 1, 2)
    for i in range(n):
        out.append({"date": d.isoformat(), "value": f"{base + random.gauss(0,8000):.0f}"})
        d += timedelta(days=7)
    return out
fix = {"economic/cost-of-living/cpi": monthly(220, 230.0, 0.45, 1.5),
       "economic/recession-watch/jobless-claims": weekly(530, 225000.0)}
print(json.dumps(fix, indent=2))
```

Pipe the output into the fixture file. The cpi history here is a raw index whose
derive (`yoy_pct`) the runner applies — confirm the cpi indicator's actual
`derive` in config.py and shape the fixture so post-derive values are plausible
(if cpi's config derive is `derive.yoy_pct`, the above works as-is).

- [ ] **Step 2: Write the failing runner test**

```python
import json
import sys
import pathlib
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import ledger, roster, runner  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "predict_histories_sample.json"


def _fixture_entries():
    keys = set(json.loads(FIXTURE.read_text(encoding="utf-8")))
    return [e for e in roster.build_roster() if e.key in keys]


class TestTournamentRun(unittest.TestCase):
    def test_dry_run_tournament_writes_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            n = runner.run_tournament(pred_dir, dry_run=True, entries=_fixture_entries())
            self.assertEqual(n, 2)
            models_json = json.loads((pred_dir / "models.json").read_text(encoding="utf-8"))
            rec = models_json["indicators"]["economic/cost-of-living/cpi"]
            for k in ("champion", "cadence", "season", "mae", "snaive_mae",
                      "err_lo", "err_hi", "skill", "explain"):
                self.assertIn(k, rec)
            self.assertEqual(rec["cadence"], "monthly")


class TestDailyRun(unittest.TestCase):
    def _bootstrap(self, pred_dir):
        runner.run_tournament(pred_dir, dry_run=True, entries=_fixture_entries())

    def test_first_daily_emits_open_predictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            opens = ledger.load_open(pred_dir)
            self.assertEqual(len(opens), 2)
            e = next(o for o in opens if o["key"] == "economic/cost-of-living/cpi")
            for k in ("id", "point", "lo", "hi", "due", "made_at", "model", "why",
                      "implied_status", "current_status", "prev_value", "href",
                      "horizon", "target_period", "unit", "title", "lens_title"):
                self.assertIn(k, e)
            self.assertIsNone(e["grade"])
            self.assertTrue(e["model"].endswith("@1"))

    def test_second_daily_is_stable_no_new_print(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            first = ledger.load_open(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            second = ledger.load_open(pred_dir)
            self.assertEqual([e["id"] for e in first], [e["id"] for e in second])
            self.assertEqual([e["point"] for e in first], [e["point"] for e in second])

    def test_new_print_grades_and_rolls_forward(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            # Simulate the next month's print arriving: extend the fixture history.
            hist = json.loads(FIXTURE.read_text(encoding="utf-8"))
            cpi = hist["economic/cost-of-living/cpi"]
            last = cpi[-1]
            y, m = int(last["date"][:4]), int(last["date"][5:7]) + 1
            if m > 12: y, m = y + 1, 1
            cpi.append({"date": f"{y:04d}-{m:02d}-01",
                        "value": f"{float(last['value']) * 1.004:.2f}"})
            with mock.patch.object(runner, "_load_fixture_histories", return_value=hist):
                runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            graded = ledger.load_all_graded(pred_dir)
            self.assertEqual(len(graded), 1)
            g = graded[0]["grade"]
            self.assertIsNotNone(g["actual"])
            opens = ledger.load_open(pred_dir)
            cpi_open = next(o for o in opens if o["key"] == "economic/cost-of-living/cpi")
            self.assertGreater(cpi_open["target_period"], graded[0]["target_period"])

    def test_missing_models_json_grades_but_emits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            self.assertEqual(ledger.load_open(pred_dir), [])

    def test_one_indicator_failure_never_blanks_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            with mock.patch.object(runner.models, "predict_one",
                                   side_effect=[runner.models.ModelError("boom")] +
                                               [4.0] * 50):
                runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            self.assertGreaterEqual(len(ledger.load_open(pred_dir)), 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run to verify it fails**

- [ ] **Step 4: Implement `scripts/predictions/runner.py`**

```python
"""Orchestration for the two jobs (spec §4–§5). The only module here that
touches the network — via the lens pipeline's own fetchers, read-only.
Every per-indicator body is wrapped: one failure skips that indicator and
never blanks the rest (house pattern)."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from lenses import brief, build, config, eia, fred, util

from . import backtest, cadence, explain, grade, ledger, models

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "predict_histories_sample.json"
FRED_FULL_LIMIT = 100000
MAX_ORIGINS = {"weekly": 104, "monthly": 96, "quarterly": 32, "daily": 104}
REVISION_LOOKBACK = 3  # re-check grades for this many trailing periods


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_fixture_histories():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _fetch_history(entry, dry_run, fixture_cache):
    """Raw full history for one roster entry ([{'date','value'}])."""
    ind = entry.indicator
    if dry_run:
        return fixture_cache.get(entry.key, [])
    if ind.source == "eia":
        return eia.fetch_series(ind.eia_route, ind.eia_facets, ind.eia_freq,
                                os.environ["EIA_API_KEY"], max(ind.limit, 2000), ind.eia_col)
    return fred.fetch_observations(ind.series_id, os.environ["FRED_API_KEY"],
                                   FRED_FULL_LIMIT, ind.units_transform)


def _prepared_series(entry, raw):
    """(cleaned [(date,float)], cadence) — derive applied, dailies resampled weekly."""
    ind = entry.indicator
    if ind.derive:
        raw = ind.derive(raw)
    cleaned = util.clean(raw)
    cad = cadence.infer(cleaned)
    if cad == "daily":
        cleaned = cadence.weekly_resample(cleaned)
    return cleaned, cad


def run_tournament(pred_dir, dry_run, entries):
    """Backtest every model per indicator; write models.json. Returns the
    number of indicators that got a champion."""
    fixture_cache = _load_fixture_histories() if dry_run else {}
    registry = {}
    for entry in entries:
        try:
            cleaned, cad = _prepared_series(entry, _fetch_history(entry, dry_run, fixture_cache))
            if cad in ("annual", "unknown"):
                continue
            season = cadence.SEASON[cad]
            values = [v for _, v in cleaned]
            result = backtest.tournament(values, season, MAX_ORIGINS[cad])
            if result is None:
                continue
            registry[entry.key] = dict(
                result, cadence=cad, season=season,
                champion=f"{result['champion']}@{models.VERSIONS[result['champion']]}",
                explain=explain.SKELETONS[result["champion"]],
            )
            print(f"tournament: {entry.key} -> {registry[entry.key]['champion']} "
                  f"(skill {result['skill']:.2f})")
        except Exception as exc:  # noqa: BLE001 - one series never sinks the job
            print(f"WARN: tournament failed for {entry.key}: {exc}", file=sys.stderr)
    build.write_lens_file(pred_dir / "models.json",
                          {"generated_at": _now(), "indicators": registry})
    return len(registry)


def _make_open_entry(entry, cleaned, cad, champ_rec):
    ind = entry.indicator
    name = champ_rec["champion"].split("@")[0]
    values = [v for _, v in cleaned]
    point = models.predict_one(name, values, champ_rec["season"])
    target = cadence.next_period(cleaned[-1][0], cad)
    _, current_status = ind.rule(cleaned)
    _, implied_status = ind.rule(cleaned + [(target, point)])
    return {
        "id": f"{entry.key}@{target}", "key": entry.key,
        "category": entry.category, "lens": entry.lens_id, "indicator": ind.id,
        "series_id": ind.series_id, "horizon": "next-print",
        "target_period": target, "due": cadence.due_estimate(target, cad),
        "made_at": _now(), "model": champ_rec["champion"],
        "point": round(point, 4),
        "lo": round(point + champ_rec["err_lo"], 4),
        "hi": round(point + champ_rec["err_hi"], 4),
        "unit": ind.unit, "value_format": ind.value_format,
        "prev_value": values[-1],
        "why": explain.why(name, cad, values, ind.short),
        "implied_status": implied_status, "current_status": current_status,
        "title": ind.title, "short": ind.short,
        "lens_title": _lens_title(entry), "href": brief.lens_href(entry.category, entry.lens_id),
        "grade": None,
    }


def _lens_title(entry):
    for cat in config.CATEGORIES:
        if cat["id"] == entry.category:
            for lens in cat["lenses"]:
                if lens.id == entry.lens_id:
                    return lens.title
    return entry.lens_id


def _check_revisions(pred_dir, entry, cleaned):
    """Footnote pass: recently graded entries whose source value moved get
    grade.revised_to set. Never alters hit (spec §3)."""
    recent_dates = {d: v for d, v in cleaned[-(REVISION_LOOKBACK + 2):]}
    for row in ledger.load_all_graded(pred_dir):
        if row["key"] != entry.key or not row.get("grade"):
            continue
        actual_date = None
        m = grade.match_actual(cleaned, row["target_period"])
        if m:
            actual_date, current_value = m
        if actual_date in recent_dates and abs(current_value - row["grade"]["actual"]) > 1e-9:
            ledger.set_revision(pred_dir, row["id"], row["made_at"][:4], current_value)


def run_daily(pred_dir, dry_run, entries):
    """Grade -> footnote -> predict, per indicator (spec §5)."""
    fixture_cache = _load_fixture_histories() if dry_run else {}
    models_path = pred_dir / "models.json"
    registry = {}
    if models_path.exists():
        try:
            registry = json.loads(models_path.read_text(encoding="utf-8")).get("indicators", {})
        except (ValueError, OSError):
            pass
    open_by_key = {e["key"]: e for e in ledger.load_open(pred_dir)}
    next_open = []
    for entry in entries:
        try:
            cleaned, cad = _prepared_series(entry, _fetch_history(entry, dry_run, fixture_cache))
            if not cleaned or cad in ("annual", "unknown"):
                continue
            prior = open_by_key.get(entry.key)
            if prior:
                m = grade.match_actual(cleaned, prior["target_period"])
                if m:
                    actual_date, actual = m
                    upto = [(d, v) for d, v in cleaned if d <= actual_date]
                    _, actual_status = entry.indicator.rule(upto)
                    prior = dict(prior, grade=grade.grade_entry(prior, actual, actual_status))
                    ledger.append_graded(pred_dir, prior)
                    prior = None  # consumed; a fresh prediction follows
            _check_revisions(pred_dir, entry, cleaned)
            if prior is not None:
                next_open.append(prior)          # target not printed yet: stays open
            elif entry.key in registry:
                next_open.append(_make_open_entry(entry, cleaned, cad, registry[entry.key]))
            # no champion (pre-bootstrap): grade/footnote ran, nothing emitted
        except Exception as exc:  # noqa: BLE001 - one series never sinks the job
            print(f"WARN: daily prediction failed for {entry.key}: {exc}", file=sys.stderr)
            if entry.key in open_by_key:
                next_open.append(open_by_key[entry.key])  # keep prior open entry
    wrote = ledger.write_views(pred_dir, next_open, ledger.load_all_graded(pred_dir))
    print(f"predictions: {len(next_open)} open; wrote {', '.join(wrote) or 'nothing (unchanged)'}")
    return len(next_open)
```

- [ ] **Step 5: Implement `scripts/predict.py`**

```python
#!/usr/bin/env python3
"""Predictions CLI — runs alongside refresh_lenses.py, never inside it.

Usage:
  python scripts/predict.py tournament            # weekly: backtest + pick champions
  python scripts/predict.py daily                 # daily: grade -> footnote -> predict
  python scripts/predict.py daily --dry-run       # fixtures, no network
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from predictions import roster, runner  # noqa: E402

PRED_DIR = Path(__file__).resolve().parent.parent / "data" / "predictions"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prediction pipeline.")
    parser.add_argument("job", choices=["daily", "tournament"])
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    args = parser.parse_args(argv)
    entries = roster.build_roster()
    if args.dry_run:
        import json
        keys = set(json.loads(runner.FIXTURE.read_text(encoding="utf-8")))
        entries = [e for e in entries if e.key in keys]
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    if args.job == "tournament":
        n = runner.run_tournament(PRED_DIR, args.dry_run, entries)
        print(f"tournament complete: {n} champions")
        return 0 if n else 1
    runner.run_daily(PRED_DIR, args.dry_run, entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the runner tests — green.** Then the whole prediction suite:

```powershell
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_predict_*.py"
```

And the full existing suite (nothing may regress):

```powershell
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```

- [ ] **Step 7: End-to-end dry run** (NOTE: writes `data/predictions/` — fine, it's new):

```powershell
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/predict.py" tournament --dry-run
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/predict.py" daily --dry-run
```

Expected: models.json with 2 champions; open.json with 2 predictions. Inspect both files by eye: points plausible, bands non-degenerate, why-sentences read well.

- [ ] **Step 8: Commit** — `feat(predictions): runner + predict.py CLI with dry-run fixtures`

---

### Task 9: State of Things "What we're watching next"

**Files:**
- Modify: `scripts/lenses/state.py` (additive param), `scripts/refresh_lenses.py:685-696` (`refresh_state`)
- Test: extend `scripts/tests/test_predict_runner.py`? No — create the block tests in `scripts/tests/test_state.py` style, appended to `test_state.py` as a new TestCase class `TestWatching`.

- [ ] **Step 1: Write the failing test** (append to `scripts/tests/test_state.py`)

```python
class TestWatching(unittest.TestCase):
    def _open(self, key, implied, current, due, sev_dist=0):
        lens = key.split("/")[1]
        return {"key": key, "indicator": key.split("/")[2], "lens": lens,
                "category": key.split("/")[0], "title": "T", "lens_title": "L",
                "due": due, "point": 4.31, "unit": "%", "value_format": "decimal",
                "implied_status": implied, "current_status": current,
                "href": f"/dashboards/{lens}.html"}

    def test_badge_changes_rank_first_alertward_before_okward(self):
        opens = [
            self._open("economic/cost-of-living/cpi", "elevated", "elevated", "2026-07-15"),
            self._open("economic/recession-watch/jobless-claims", "watch", "ok", "2026-06-18"),
            self._open("housing/home-prices/case-shiller", "ok", "watch", "2026-06-30"),
        ]
        block = state.build_watching(opens)
        self.assertEqual(block[0]["key"], "economic/recession-watch/jobless-claims")
        self.assertTrue(block[0]["change"])
        self.assertEqual(block[1]["key"], "housing/home-prices/case-shiller")
        self.assertEqual(block[2]["key"], "economic/cost-of-living/cpi")
        self.assertFalse(block[2]["change"])

    def test_capped_at_three_and_no_change_sorted_by_due(self):
        opens = [self._open(f"economic/l{i}/i{i}", "ok", "ok", f"2026-07-{10 + i:02d}")
                 for i in range(5)]
        block = state.build_watching(opens)
        self.assertEqual(len(block), 3)
        self.assertEqual([b["due"] for b in block],
                         ["2026-07-10", "2026-07-11", "2026-07-12"])

    def test_build_state_carries_watching_when_given(self):
        indices = {"economic": {"status": "ok", "lenses": [
            {"id": "recession-watch", "title": "RW", "status": "ok", "headline_read": "x"}]}}
        out = state.build_state(indices, None, open_predictions=[
            self._open("economic/recession-watch/jobless-claims", "watch", "ok", "2026-06-18")])
        self.assertIn("watching", out)
        self.assertEqual(out["watching"][0]["point_fmt"], "4.31%")

    def test_build_state_omits_watching_by_default(self):
        indices = {"economic": {"status": "ok", "lenses": []}}
        out = state.build_state(indices, None)
        self.assertNotIn("watching", out)
```

- [ ] **Step 2: Run — fails** (`state` has no `build_watching`)

- [ ] **Step 3: Implement in `scripts/lenses/state.py`** (add near the bottom, before `build_state`; then wire into `build_state`)

```python
WATCHING_CAP = 3
_SEV = util.STATUS_ORDER


def build_watching(open_predictions):
    """'What we're watching next': up to 3 open predictions ranked by
    consequence — predicted badge changes first (alert-ward before ok-ward,
    bigger jumps first), then nearest-due. Spec §7."""
    from . import build as _build  # _fmt: keep hub/page formatting identical

    def _is_change(p):
        return (p.get("implied_status") != p.get("current_status")
                and p.get("implied_status") in _SEV and p.get("current_status") in _SEV)

    def _rank(p):
        if _is_change(p):
            dist = _SEV[p["implied_status"]] - _SEV[p["current_status"]]
            # alert-ward (positive dist) first, bigger jumps first, then due
            return (0, 0 if dist > 0 else 1, -abs(dist), p.get("due") or "9999")
        return (1, 0, 0, p.get("due") or "9999")

    ranked = sorted((p for p in open_predictions or []), key=_rank)[:WATCHING_CAP]
    return [{
        "key": p["key"], "indicator": p["indicator"], "lens": p["lens"],
        "category": p["category"], "title": p.get("title", ""),
        "lens_title": p.get("lens_title", ""), "due": p.get("due"),
        "point_fmt": _build._fmt(p.get("point"), p.get("unit", ""),
                                 p.get("value_format", "decimal")),
        "implied_status": p.get("implied_status"),
        "current_status": p.get("current_status"),
        "change": _is_change(p), "href": p.get("href", "/dashboards/"),
    } for p in ranked]
```

In `build_state(category_indices, brief_today)` change the signature to
`build_state(category_indices, brief_today, open_predictions=None)` and, right
before the final `return`, add:

```python
    if open_predictions:
        out["watching"] = build_watching(open_predictions)
```

(adjust to the actual local name of the result dict in `build_state` — read the
function tail first; it may build the dict inline in the return statement, in
which case bind it to `out` first).

- [ ] **Step 4: Wire `refresh_lenses.py`.** In `refresh_state` (line ~685), replace the `build_state` call:

```python
def _load_open_predictions():
    path = Path(__file__).resolve().parent.parent / "data" / "predictions" / "open.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("predictions", [])
        except (ValueError, OSError):
            pass
    return None
```

and inside `refresh_state`'s try block:

```python
        today = state.build_state(indices, _load_brief_today(),
                                  open_predictions=_load_open_predictions())
```

- [ ] **Step 5: Run `test_state.py` + the full suite — green** (existing state tests must pass unchanged: the param is optional)

- [ ] **Step 6: Commit** — `feat(predictions): State of Things watching block`

---

### Task 10: lens-page surface (predict.js)

**Files:**
- Modify: `dashboards/lens.js` (two additive lines), `dashboards/lens.css`
- Create: `dashboards/predict.js`
- Modify: every lens page (one script tag)

No unit tests (house convention: JS surfaces are eyeballed); the pipeline contract is already tested.

- [ ] **Step 1: Two additive lines in `lens.js`.** In `indicatorCard` (line ~107), after `el.className = "ind";` add:

```js
    el.dataset.indicator = indicator.id;
```

In `renderLens` (line ~215), find where the lens JSON (`data`) has finished rendering into `#lens-root` (end of the function, after indicators are appended) and add:

```js
    document.dispatchEvent(new CustomEvent("lens:rendered", { detail: { id: data.id } }));
```

(Use the actual local variable holding the lens JSON — read the function; it may be named `data` or `lens`.)

- [ ] **Step 2: Create `dashboards/predict.js`**

```js
/* "Next print" blocks under indicator charts + the last graded call.
   Fully additive: if this file or its JSON is missing, lens pages render
   exactly as before. Matches cards via data-indicator + the lens id from
   the lens:rendered event. */
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  async function get(url) {
    try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; }
    catch (e) { return null; }
  }
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDue(iso) {
    if (!iso || iso.length < 10) return "";
    return `due ~${MONTHS[+iso.slice(5, 7) - 1]} ${+iso.slice(8, 10)}`;
  }
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
  function statusPhrase(p) {
    if (!p.implied_status || p.implied_status === "info") return "";
    return p.change || p.implied_status !== p.current_status
      ? ` — would tip this to <span class="badge ${esc(p.implied_status)}">${esc(p.implied_status)}</span>`
      : ` — would keep this <span class="badge ${esc(p.implied_status)}">${esc(p.implied_status)}</span>`;
  }
  function lastCall(g) {
    if (!g || !g.grade) return "";
    const mark = g.grade.hit ? "✓" : "✗";
    const cls = g.grade.hit ? "hit" : "miss";
    const rev = g.grade.revised_to != null
      ? ` <span class="pred-rev">(later revised to ${esc(fmtVal(g.grade.revised_to, g.unit, g.value_format))} — we grade against the first print)</span>` : "";
    return `<div class="pred-last"><span class="pred-mark ${cls}">${mark}</span>
      Last call: we said ${esc(fmtVal(g.point, g.unit, g.value_format))},
      actual was <strong>${esc(fmtVal(g.grade.actual, g.unit, g.value_format))}</strong>${rev}
      · <a href="/dashboards/track-record.html">our record &rarr;</a></div>`;
  }
  function block(p, g) {
    const range = `${fmtVal(p.lo, p.unit, p.value_format)}–${fmtVal(p.hi, p.unit, p.value_format)}`;
    return `<div class="predict">
      <div class="pred-head">Next print <span class="pred-due">${esc(fmtDue(p.due))}</span></div>
      <div class="pred-line">We expect <strong>~${esc(fmtVal(p.point, p.unit, p.value_format))}</strong>
        <span class="pred-range">(likely ${range})</span>${statusPhrase(p)}</div>
      <div class="pred-why">${esc(p.why || "")}</div>${lastCall(g)}</div>`;
  }
  document.addEventListener("lens:rendered", async function (ev) {
    const lensId = ev.detail && ev.detail.id;
    if (!lensId) return;
    const [open, recent] = await Promise.all([
      get("/data/predictions/open.json"), get("/data/predictions/recent.json")]);
    if (!open || !open.predictions) return;
    const mine = {};
    open.predictions.forEach(p => { if (p.lens === lensId) mine[p.indicator] = p; });
    document.querySelectorAll("#lens-root .ind[data-indicator]").forEach(card => {
      const p = mine[card.dataset.indicator];
      if (!p) return;
      const g = recent && recent.last && recent.last[p.key];
      const div = document.createElement("div");
      div.innerHTML = block(p, g);
      card.appendChild(div.firstElementChild);
    });
  });
})();
```

- [ ] **Step 3: Styles in `dashboards/lens.css`** (append; match the file's existing dark-theme palette — read neighboring rules and reuse its color variables/values):

```css
/* Next-print prediction blocks (predict.js) */
.predict { margin-top: 14px; padding: 12px 14px; border: 1px solid #1E293B; border-radius: 10px; background: rgba(30, 41, 59, .35); }
.predict .pred-head { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: #64748B; margin-bottom: 6px; }
.predict .pred-due { text-transform: none; letter-spacing: 0; margin-left: 6px; }
.predict .pred-line { font-size: 14px; }
.predict .pred-range { color: #94A3B8; font-size: 13px; }
.predict .pred-why { color: #94A3B8; font-size: 13px; margin-top: 4px; }
.predict .pred-last { margin-top: 8px; font-size: 13px; color: #94A3B8; border-top: 1px dashed #1E293B; padding-top: 8px; }
.predict .pred-mark.hit { color: #34D399; }
.predict .pred-mark.miss { color: #F87171; }
.predict .pred-rev { font-size: 12px; }
```

- [ ] **Step 4: Add the script tag to every lens page.** For each `dashboards/**/*.html` that contains `renderLens(` (use Grep to enumerate), add after the `lens.js` script tag:

```html
  <script defer src="/dashboards/predict.js"></script>
```

Add it to ALL lens pages including banking and the neutral markets pages — predict.js no-ops where no predictions match, and uniformity beats a hand-maintained list.

- [ ] **Step 5: Eyeball.** `python -m http.server 8000` from `baileyanalytics/`, open `http://localhost:8000/dashboards/cost-of-living.html`. With dry-run data from Task 8 present, the CPI card shows a Next-print block; other cards unchanged; a banking page shows nothing and logs no errors.

- [ ] **Step 6: Commit** — `feat(predictions): next-print blocks on lens pages`

---

### Task 11: Track Record page

**Files:**
- Create: `dashboards/track-record.html`, `dashboards/track-record.js`
- Modify: `dashboards/lens.css` (page styles), `dashboards/state.html` + `dashboards/state.js` (watching section render)

- [ ] **Step 1: `dashboards/track-record.html`.** Copy the head/nav/footer skeleton from `dashboards/state.html` (same conventions: wordmark, top-nav, lens.css). Body sections:

```html
  <main class="track">
    <h1>Track Record</h1>
    <p class="track-sub" id="since">Every prediction on this site is published before the number
      exists, then graded in public against the first print. This page is the whole record.</p>
    <section id="headline-sec">
      <div class="track-stats">
        <div class="track-stat"><div class="track-num" id="calibration">—</div>
          <div class="track-lab">of actuals landed inside our stated range</div>
          <p class="track-note">We aim for ~80%, not 100% — a forecaster who's never wrong is
            using bands too wide to mean anything.</p></div>
        <div class="track-stat"><div class="track-num" id="skill">—</div>
          <div class="track-lab">closer than guessing the last value</div>
          <p class="track-note">The "skill" score: how much our predictions beat the naive
            guess. Recomputable by anyone from the public ledger.</p></div>
      </div>
    </section>
    <section id="cats-sec" hidden><h2>By category</h2><div id="cats"></div></section>
    <section id="feed-sec" hidden><h2>Recent grades</h2><div id="feed"></div></section>
    <section id="how-sec">
      <h2>How this works</h2>
      <p>Each week, every indicator's history is backtested: we stand at hundreds of past
        dates, predict the next print using only data available then, and measure the miss.
        Whichever simple model wins — and only if it beats the naive "same as last time"
        guess — becomes that indicator's forecaster. The ranges we publish are the ranges
        those backtests earned. Every model is explainable in one sentence; there is no
        black box.</p>
      <p>Predictions are graded against the number as first published, then frozen — later
        data revisions are footnoted, never regraded, and a graded entry never changes.
        Because the ledger lives in this site's public git history, the timestamps are
        independently verifiable: every prediction is committed before its print exists.</p>
      <p>Asset prices (the markets scoreboard, crypto) are deliberately not predicted —
        next week's market move is the one thing honest models can't call, and we'd rather
        show you nothing than theater.</p>
    </section>
  </main>
  <script defer src="/dashboards/track-record.js"></script>
```

- [ ] **Step 2: `dashboards/track-record.js`**

```js
(function () {
  function esc(s) { const d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  async function get(url) {
    try { const r = await fetch(url, { cache: "no-cache" }); return r.ok ? await r.json() : null; }
    catch (e) { return null; }
  }
  const TITLES = { economic: "Economic Lenses", consumer: "The Consumer", markets: "Markets",
    energy: "Energy & Commodities", housing: "Housing", global: "Global Economy",
    business: "Business Health", banking: "Banking" };
  const pct = x => `${Math.round(x * 100)}%`;
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
    if (tr.since) document.getElementById("since").textContent =
      `${tr.graded} predictions graded since ${tr.since.slice(0, 10)} — this record grows weekly. ` +
      `Every one was published before the number existed.`;
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
```

- [ ] **Step 3: Page styles** (append to `lens.css`):

```css
/* Track Record page */
.track { max-width: 880px; margin: 0 auto; padding: 24px 16px 64px; }
.track-sub { color: #94A3B8; }
.track-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }
.track-stat { border: 1px solid #1E293B; border-radius: 12px; padding: 18px; }
.track-num { font-size: 36px; font-weight: 700; }
.track-lab { color: #CBD5E1; margin-top: 4px; }
.track-note { color: #64748B; font-size: 13px; margin-top: 8px; }
.track-row { display: flex; gap: 10px; align-items: baseline; padding: 8px 4px; border-bottom: 1px solid #1E293B; text-decoration: none; color: inherit; }
.track-ind { font-weight: 600; }
.track-said { color: #94A3B8; font-size: 13px; }
@media (max-width: 640px) { .track-stats { grid-template-columns: 1fr; } }
```

(Adapt selectors/colors to lens.css's actual conventions while implementing — reuse its badge classes and palette.)

- [ ] **Step 4: State page watching section.** In `dashboards/state.html`, after the steady section add:

```html
    <section id="watching-sec" hidden><h2>What we're watching next</h2><div id="watching"></div></section>
```

In `dashboards/state.js` `renderPage`, after the steady block add:

```js
    const w = data.watching || [];
    if (w.length) {
      document.getElementById("watching-sec").hidden = false;
      document.getElementById("watching").innerHTML = w.map(x => {
        const claim = x.change
          ? `we expect <strong>${esc(x.point_fmt)}</strong> — which would tip ${esc(x.lens_title)} to <span class="badge ${esc(x.implied_status)}">${esc(x.implied_status)}</span>`
          : `we expect <strong>${esc(x.point_fmt)}</strong>, no status change`;
        return `<a class="state-lens" href="${esc(x.href)}">
          <span class="state-lens-title">${esc(x.title)}</span>
          <span class="state-lens-read">${claim}</span></a>`;
      }).join("") +
      `<a class="state-link" href="/dashboards/track-record.html">Our track record &rarr;</a>`;
    }
```

And the panel mode one-liner: in the non-page branch, when `data.watching` has an entry with `change === true`, append after the verdict:

```js
        const chg = (data.watching || []).find(x => x.change);
        if (opts.mode !== "line" && chg) {
          el.innerHTML += `<div class="state-watch-line">We expect ${esc(chg.title)} (${esc(chg.point_fmt)}) to tip ${esc(chg.lens_title)} to ${esc(chg.implied_status)} — <a class="state-link" href="/dashboards/state.html">details &rarr;</a></div>`;
        }
```

- [ ] **Step 5: Eyeball** all three: track-record page with dry-run data, state page watching section (hand-edit `data/state/today.json` to include a `watching` array if the dry-run state didn't), `/dashboards/` panel.

- [ ] **Step 6: Commit** — `feat(predictions): track-record page + state watching surfaces`

---

### Task 12: workflows

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`
- Create: `.github/workflows/tournament.yml`

- [ ] **Step 1: `refresh-fred.yml`.** After the "Set up Python" step add:

```yaml
      - name: Install pipeline dependencies
        run: pip install -r requirements.txt
```

After the "Fetch latest global data" step and before "Rebuild Today's Brief", add:

```yaml
      - name: Grade and predict (daily prediction loop)
        if: ${{ success() || failure() }}
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: python scripts/predict.py daily
```

(The commit step already adds all of `data/`, which covers `data/predictions/`.)

- [ ] **Step 2: Create `.github/workflows/tournament.yml`**

```yaml
name: Prediction tournament

on:
  schedule:
    # Weekly, Sunday 05:00 UTC, before Monday's daily runs pick up the new
    # champions. GitHub cron silently skips slots sometimes (observed
    # 2026-06-10), so a second slot self-heals; models.json writes are
    # content-aware, so the rerun is free when the first worked.
    - cron: "0 5 * * 0"
    - cron: "0 12 * * 0"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  tournament:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install pipeline dependencies
        run: pip install -r requirements.txt

      - name: Run the model tournament (full-history backtests)
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
        run: python scripts/predict.py tournament

      - name: Commit and push if models changed
        if: ${{ success() || failure() }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          if [[ -n "$(git status --porcelain data/predictions/)" ]]; then
            git add data/predictions/
            git commit -m "chore: weekly prediction tournament ($(date -u +%Y-%m-%d))"
            git push
          else
            echo "No model changes — skipping commit."
          fi
```

- [ ] **Step 3: Commit** — `ci(predictions): daily grade-and-predict step + weekly tournament workflow`

---

### Task 13: docs + spec amendment

**Files:**
- Modify: `docs/superpowers/specs/2026-06-11-predictions-design.md`, `CLAUDE.md`, `about.html`

- [ ] **Step 1: Spec amendment.** In §7, replace "No changes inside `lens.js`" with: "Two additive lines in `lens.js` (a `data-indicator` attribute on each card and a `lens:rendered` event) are the hook; everything else lives in `predict.js`."

- [ ] **Step 2: `CLAUDE.md`.** Add a "Predictions & Track Record" subsection under the baileyanalytics architecture section, covering: `scripts/predictions/` package + `scripts/predict.py` (daily/tournament, `--dry-run` overwrites `data/predictions/`), the roster rule ("predicts what drives badges" — neutral/info/banking/computed excluded), first-print frozen grading + revision footnotes, `data/predictions/` file inventory, the two workflows, `requirements.txt` now existing (pip install step in both touched workflows), and that `state.py` consumes `open.json` for the watching block. Mention test pattern `test_predict_*.py`.

- [ ] **Step 3: `about.html`.** In "Where this is going", after the existing leading-indicators sentence, add one sentence:

```html
That work has begun: the site now publishes its own next-print predictions for the numbers it tracks&mdash;each with a plain-English why&mdash;and grades every one in public on the <a href="/dashboards/track-record.html">Track Record</a> page.
```

- [ ] **Step 4: Commit** — `docs(predictions): spec amendment, CLAUDE.md, about page`

---

### Task 14: full verification

- [ ] **Step 1: Full test suite**

```powershell
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```

Expected: all pass (~270 existing + ~60 new).

- [ ] **Step 2: Full dry-run of both pipelines** (then restore data):

```powershell
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/predict.py" tournament --dry-run
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/predict.py" daily --dry-run
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --dry-run
```

Verify `data/state/today.json` contains a `watching` block (the dry-run daily ran first, so open.json exists). Then `git checkout -- data/` EXCEPT keep `data/predictions/` dry-run artifacts out of the branch too: `git -C <repo> checkout -- data/ ; git -C <repo> clean -fd data/predictions/` — the branch ships **no** baked prediction data; the first real tournament populates it post-merge.

- [ ] **Step 3: Browser eyeball of all surfaces** (temporarily re-run the two dry-run commands for local data, eyeball, then clean again as in Step 2): lens page block, track-record page, state page, `/dashboards/` panel — desktop and narrow viewport.

- [ ] **Step 4: Commit anything outstanding; report ready for /code-review.** Per Michael's workflow: he runs `/code-review` in a fresh session; findings get fixed on this branch; merge/push only on his go. The bootstrap sequence after merge: dispatch `tournament.yml` once manually, then the next daily run emits the first open predictions.

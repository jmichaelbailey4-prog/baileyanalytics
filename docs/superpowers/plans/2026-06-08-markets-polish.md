# Markets Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** De-duplicate the yield-curve chart, give each scoreboard asset a volatility-appropriate momentum band, and make the ICE BofA credit-spread charts honest about their ~3-year history.

**Architecture:** All three changes live in `scripts/lenses/config.py` (lens/indicator definitions) plus their unit tests. No new modules, no renderer or HTML changes — the `narrative.market_level` factory already accepts per-asset bands, and `lens.js` already renders `indicator.context`.

**Tech Stack:** Standard-library Python 3, `unittest`. No third-party deps. Tests run via `python -m unittest`.

**Spec:** `docs/superpowers/specs/2026-06-08-markets-polish-design.md`

**Conventions:**
- Run from the parent dir using absolute paths (this repo is `baileyanalytics/`).
- Test command (full suite):
  ```
  python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
  ```
- Single test file, e.g.:
  ```
  python -m unittest -v scripts.tests.test_build
  ```
  run with cwd = `baileyanalytics/` OR use discover with `-p`. The repo uses `sys.path.insert` in each test to find `lenses`, so running the file directly also works:
  ```
  python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build.py"
  ```
- Commit on a feature branch only (do **not** push — pushing `main` deploys; this work is not on `main`). End every commit message with:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```
- **Do not run `refresh_lenses.py --dry-run`** as a test — it overwrites tracked `data/` from fixtures.

---

### Task 1: De-duplicate the yield-curve chart

Remove the duplicate `yield-curve` indicator from `COST_OF_MONEY`. It stays in
`RECESSION_WATCH`. Cost of Money already charts the 10-year and 2-year yields
separately, so the spread is redundant there.

**Files:**
- Modify: `scripts/lenses/config.py` (the `COST_OF_MONEY` lens, indicator `id="yield-curve"`, ~lines 172-186)
- Test: `scripts/tests/test_build.py` (`TestBuildCostOfMoney`, ~lines 78-83)

- [ ] **Step 1: Update the failing test first (count 5 → 4)**

In `scripts/tests/test_build.py`, change `TestBuildCostOfMoney`:

```python
class TestBuildCostOfMoney(unittest.TestCase):
    def test_builds_with_four_indicators(self):
        lj = build.build_lens(config.COST_OF_MONEY, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-money")
        self.assertEqual(len(lj["indicators"]), 4)
        self.assertEqual(lj["status"], "watch")
        ids = [i["id"] for i in lj["indicators"]]
        self.assertNotIn("yield-curve", ids)
```

(The overall status stays `"watch"` because `fed-funds` 4.33 and `mortgage-30y`
6.84 are both `"watch"` in the fixture — verified.)

- [ ] **Step 2: Run the test to verify it fails**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build.py"
```
Expected: FAIL — `AssertionError: 5 != 4` (config still has the indicator).

- [ ] **Step 3: Remove the indicator from config**

In `scripts/lenses/config.py`, delete the entire `Indicator(...)` block for the
yield curve inside `COST_OF_MONEY` (the one with `id="yield-curve"`,
`series_id="T10Y2Y"`, ending with the `context=(...)` about "When it turns
negative, short-term borrowing costs more than long-term"). Leave the trailing
`],` and `)` that close the `indicators` list and the `Lens(...)` call. The
`RECESSION_WATCH` yield-curve indicator is **not** touched.

After removal, `COST_OF_MONEY.indicators` is exactly: `fed-funds`,
`treasury-10y`, `treasury-2y`, `mortgage-30y`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build.py"
```
Expected: PASS (all tests in the file).

- [ ] **Step 5: Run the full suite to confirm no regression**

Run:
```
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```
Expected: OK (no failures). `rule_yield_curve` and its tests still pass — it's
still used by Recession Watch.

- [ ] **Step 6: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_build.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "refactor: drop duplicate yield-curve chart from Cost of Money

The 10y-2y spread (T10Y2Y) appeared identically in both Recession Watch
and Cost of Money. Cost of Money already charts DGS10 and DGS2 separately,
so the spread was redundant there. Keep it in Recession Watch, where the
inversion-as-recession-signal is the lens's purpose.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Per-asset scoreboard momentum bands

Give each of the six scoreboard assets a momentum band sized to its normal
annual volatility, replacing the shared ±2% default that flags ordinary moves.

**Files:**
- Modify: `scripts/lenses/config.py` (the six `MARKET_SCOREBOARD` indicators, ~lines 622-660)
- Test: `scripts/tests/test_config_markets.py` (add one test to `TestMarketConfig`)

- [ ] **Step 1: Write the failing test**

In `scripts/tests/test_config_markets.py`, add this helper near the top (after
the imports) and this test method inside `class TestMarketConfig`:

```python
def _yr(a, b):
    """Two observations a year apart so market_level resolves a prior value."""
    return [("2020-01-01", a), ("2021-01-01", b)]
```

```python
    def test_scoreboard_momentum_bands_are_per_asset(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        rules = {i.id: i.rule for i in board.indicators}
        # S&P 500: +/-5% band
        self.assertEqual(rules["sp500"](_yr(100.0, 103.0))[1], "flat")  # +3%
        self.assertEqual(rules["sp500"](_yr(100.0, 106.0))[1], "up")    # +6%
        # Dollar index: +/-3% band
        self.assertEqual(rules["dollar"](_yr(100.0, 102.0))[1], "flat") # +2%
        self.assertEqual(rules["dollar"](_yr(100.0, 96.0))[1], "down")  # -4%
        # WTI oil: +/-15% band
        self.assertEqual(rules["oil"](_yr(100.0, 110.0))[1], "flat")    # +10%
        self.assertEqual(rules["oil"](_yr(100.0, 120.0))[1], "up")      # +20%
        # Bitcoin: +/-25% band
        self.assertEqual(rules["btc"](_yr(100.0, 120.0))[1], "flat")    # +20%
        self.assertEqual(rules["btc"](_yr(100.0, 130.0))[1], "up")      # +30%
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py"
```
Expected: FAIL — with the current ±2% default, `sp500(_yr(100,103))` returns
`"up"` (3% > 2%), not `"flat"`. AssertionError `'up' != 'flat'`.

- [ ] **Step 3: Pass the per-asset bands in config**

In `scripts/lenses/config.py`, update each `rule=narrative.market_level(...)`
call inside `MARKET_SCOREBOARD` to include `up`/`down` args:

```python
            series_id="SP500", limit=2600, rule=narrative.market_level("The S&P 500", up=5, down=-5),
```
```python
            series_id="DCOILWTICO", limit=2600, rule=narrative.market_level("WTI crude", up=15, down=-15),
```
```python
            series_id="XAUUSD", limit=2600, rule=narrative.market_level("Gold", up=10, down=-10),
```
```python
            series_id="DTWEXBGS", limit=2600, rule=narrative.market_level("The dollar index", up=3, down=-3),
```
```python
            series_id="CBBTCUSD", limit=2600, rule=narrative.market_level("Bitcoin", up=25, down=-25),
```
```python
            series_id="CBETHUSD", limit=2600, rule=narrative.market_level("Ethereum", up=25, down=-25),
```

Match each line to the correct indicator by its `series_id` (the surrounding
`Indicator(...)` lines with `value_format`, `context`, `source` stay unchanged).
Do **not** change the `market_level` factory's default signature in
`narrative.py`.

- [ ] **Step 4: Run the test to verify it passes**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py"
```
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run:
```
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```
Expected: OK. (`test_narrative_markets.py::TestMarketLevel` still passes — it
exercises the factory's ±2% default directly, which is unchanged.)

- [ ] **Step 6: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat: per-asset momentum bands on the asset-class scoreboard

The shared +/-2% trailing-12-month default flagged ordinary moves as
momentum (e.g. the dollar's -0.7% read as 'down'). Size each band to the
asset's normal annual volatility: S&P +/-5, dollar +/-3, gold +/-10,
oil +/-15, BTC/ETH +/-25. Validated against live YoY: S&P up, oil up,
gold up, dollar flat, BTC down, ETH down.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Honest ICE BofA credit-spread history

The HY (`BAMLH0A0HYM2`) and IG (`BAMLC0A0CM`) series only return a rolling
~3-year window from the FRED API (ICE redistribution license), despite being
configured `limit=2600` (~10y). Lower the limit to reflect reality and tell the
reader in the chart context.

**Files:**
- Modify: `scripts/lenses/config.py` (the `hy-spread` and `ig-spread` indicators in `MARKET_RISK_SENTIMENT`, ~lines 594-607)
- Test: `scripts/tests/test_config_markets.py` (add one test to `TestMarketConfig`)

- [ ] **Step 1: Write the failing test**

In `scripts/tests/test_config_markets.py`, add this test method inside
`class TestMarketConfig`:

```python
    def test_ice_spread_indicators_use_short_window(self):
        risk = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-risk-sentiment")
        by_id = {i.id: i for i in risk.indicators}
        for ind_id in ("hy-spread", "ig-spread"):
            ind = by_id[ind_id]
            self.assertEqual(ind.limit, 900)
            self.assertIn("rolling", ind.context.lower())
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py"
```
Expected: FAIL — `900 != 2600` (limit not yet lowered).

- [ ] **Step 3: Update the two indicators in config**

In `scripts/lenses/config.py`, edit the `hy-spread` indicator:

```python
        Indicator(
            id="hy-spread", title="High-Yield Credit Spread", short="HY spread", unit="%",
            color="#FB923C", series_id="BAMLH0A0HYM2",
            limit=900,  # ICE BofA: FRED API only serves a rolling ~3y window
            rule=narrative.credit_spread("high-yield", 4.0, 6.0),
            context=("The extra yield investors demand to hold risky 'junk' corporate bonds over "
                     "Treasuries. It widens when markets fear defaults — an early stress signal. "
                     "Note: FRED serves only a rolling ~3-year window of this ICE BofA series, so "
                     "its chart history is shorter than the other indicators here."),
        ),
```

and the `ig-spread` indicator:

```python
        Indicator(
            id="ig-spread", title="Investment-Grade Credit Spread", short="IG spread", unit="%",
            color="#FBBF24", series_id="BAMLC0A0CM",
            limit=900,  # ICE BofA: FRED API only serves a rolling ~3y window
            rule=narrative.credit_spread("investment-grade", 1.5, 2.5),
            context=("The same risk premium for higher-quality corporate bonds. Because these "
                     "borrowers are safer, widening here signals stress reaching the core of credit. "
                     "Note: FRED serves only a rolling ~3-year window of this ICE BofA series, so "
                     "its chart history is shorter than the other indicators here."),
        ),
```

(Only `limit` and `context` change; `rule` thresholds stay — the stress bands
are deliberately unchanged per the spec.)

- [ ] **Step 4: Run the test to verify it passes**

Run:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py"
```
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run:
```
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```
Expected: OK.

- [ ] **Step 6: Commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "fix: be honest about ICE BofA credit-spread history window

FRED's API only serves a rolling ~3-year window for the ICE BofA HY/IG
spread series (redistribution license), despite limit=2600 implying ~10y.
Lower the limit to 900 and add a note to each chart's context so readers
know the history is shorter than the other indicators. Stress thresholds
unchanged (they map to absolute, historically-grounded levels).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Final live verification

Confirm the changes hold against real data, not just fixtures.

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite one last time**

Run:
```
python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"
```
Expected: OK, ~155+ tests.

- [ ] **Step 2: Live build of the affected categories**

With `FRED_API_KEY` (and `COINGECKO_API_KEY`) in the environment, from
`baileyanalytics/`:
```
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --economic --markets
```
Expected: writes updated `data/lenses/cost-of-money.json` (4 indicators, no
yield-curve) and `data/markets/market-scoreboard.json` / `market-risk-sentiment.json`.
No tracebacks; a failed crypto/gold source must not abort the run.

- [ ] **Step 3: Eyeball the output**

Confirm:
- `data/lenses/cost-of-money.json` has 4 indicators and none with `"id": "yield-curve"`.
- `data/markets/market-scoreboard.json` indicators show a varied `signal_status`
  spread (not everything `up`/`down`) — e.g. the dollar reads `flat`.
- `data/markets/market-risk-sentiment.json` HY/IG `context` contains the
  rolling-window note.

- [ ] **Step 4: Stage the regenerated data and commit**

```
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add data/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "data: rebuild economic + markets after polish changes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(If the live build can't run in this environment, skip Steps 2-4 and note that
the data rebuild will happen on the next scheduled `refresh-fred.yml` run; the
code + unit tests are the gate.)

---

## Notes for the implementer

- These tasks are independent and can be done in any order, but the order above
  groups commits cleanly. Each task leaves the suite green.
- After all tasks: use **superpowers:finishing-a-development-branch** to decide
  merge/PR/keep. Do **not** push to `main` without explicit user approval —
  pushing `main` deploys the live site.

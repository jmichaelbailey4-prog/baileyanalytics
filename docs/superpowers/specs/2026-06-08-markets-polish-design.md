# Markets Polish — Design

**Date:** 2026-06-08
**Status:** Approved (brainstorming) → ready for plan

## Goal

Clear three pieces of accumulated debt around the Markets category and the
shared economic lenses, none of which require front-end framework changes:

1. **De-duplicate the yield-curve chart** that appears identically in both the
   Recession Watch and Cost of Money lenses.
2. **Fix the Asset-Class Scoreboard momentum bands**, which currently use a
   ±2% trailing-12-month default that is noise for these assets.
3. **Make the ICE BofA credit-spread charts honest** about their history: the
   FRED API only serves a rolling ~3-year window for those two series, even
   though they are configured as if they hold ~10 years.

Explicitly **out of scope:** the home-page (`index.html`) showcase redesign,
which is deferred until additional dashboard categories and data sources land.
The Risk Sentiment *stress* thresholds (VIX / HY / IG / NFCI) were reviewed and
are deliberately **kept unchanged** — see the rationale below.

## Background / current state

- `scripts/lenses/config.py` defines every lens and indicator. The yield-curve
  indicator (`id="yield-curve"`, `series_id="T10Y2Y"`) is declared **twice**:
  once in `RECESSION_WATCH` and once in `COST_OF_MONEY`. Cost of Money also
  already charts the 10-year (`DGS10`) and 2-year (`DGS2`) yields as separate
  lines, so the spread is redundant within that lens, and its chart + narrative
  are near-identical to Recession Watch's.
- `scripts/lenses/narrative.py` exposes `market_level(label, up=2.0, down=-2.0)`,
  a factory that reads a price/level series' trailing ~12-month % change and
  returns `up` / `down` / `flat`. Every scoreboard indicator in `config.py`
  currently calls it **without** override args, so all six assets share the
  ±2% band.
- The two ICE BofA series are configured `limit=2600` (commented "~10y daily").

### Live calibration findings (2026-06-08)

Trailing-12-month change, pulled live from FRED + Yahoo:

| Asset | Series | YoY |
|---|---|---|
| S&P 500 | SP500 | +24.3% |
| WTI oil | DCOILWTICO | +56.1% |
| Dollar index | DTWEXBGS | −0.7% |
| Gold | GC=F (Yahoo) | strongly positive |
| Bitcoin | CBBTCUSD | −40.2% |
| Ethereum | CBETHUSD | −32.8% |

Stress-indicator history (FRED):

- **VIX (`VIXCLS`)** — full history available (9,202 obs back to 1990; 2008 peak
  80.9, 2020 peak 82.7). Median ~17, p90 ~27.
- **HY spread (`BAMLH0A0HYM2`)** — API returned only **785 obs starting
  2023-06-09** even when requesting from 1990. Range in that window: 2.59–4.61,
  median 3.14. The pre-2023 crisis history (e.g. 2020 ≈ 10%) is **not served by
  the API** — ICE's redistribution license caps FRED downloads to a rolling
  window.
- **IG spread (`BAMLC0A0CM`)** — same ~3-year cap; window range 0.73–1.41,
  median 0.90.
- **NFCI (`NFCI`)** — full history; normalized so 0 = historical average.

## Change 1 — De-duplicate the yield curve

**File:** `scripts/lenses/config.py`

Remove the `Indicator(id="yield-curve", ... series_id="T10Y2Y", ...)` block from
`COST_OF_MONEY`. Leave `RECESSION_WATCH` untouched — that is where the
inversion-as-recession-signal narrative is the lens's entire purpose.

After the change `COST_OF_MONEY` has four indicators: `fed-funds`,
`treasury-10y`, `treasury-2y`, `mortgage-30y`. This matches the 4–5 indicator
count used by the other lenses.

**Test impact:** `scripts/tests/test_build.py::TestBuildCostOfMoney` asserts
five indicators and an overall `"watch"` status. Update the count to **4** and
re-derive the expected overall status from the four remaining indicators against
`fetched_sample.json` (whatever `synthesize` legitimately produces — adjust the
assertion to the real value rather than forcing `"watch"`). No other test or
page references the Cost of Money yield-curve indicator. `rule_yield_curve` and
its own tests stay as-is (still used by Recession Watch).

## Change 2 — Per-asset scoreboard momentum bands

**File:** `scripts/lenses/config.py` (the six `MARKET_SCOREBOARD` indicators)

`market_level()` already accepts `up` / `down`. Pass per-asset bands sized to
each asset's normal annual volatility, so a genuinely "flat" year reads flat:

| Indicator | `series_id` | New call |
|---|---|---|
| S&P 500 | SP500 | `market_level("The S&P 500", up=5, down=-5)` |
| WTI oil | DCOILWTICO | `market_level("WTI crude", up=15, down=-15)` |
| Gold | XAUUSD | `market_level("Gold", up=10, down=-10)` |
| Dollar index | DTWEXBGS | `market_level("The dollar index", up=3, down=-3)` |
| Bitcoin | CBBTCUSD | `market_level("Bitcoin", up=25, down=-25)` |
| Ethereum | CBETHUSD | `market_level("Ethereum", up=25, down=-25)` |

Validated against the live YoY table above, these produce a varied, meaningful
split — S&P up, oil up, gold up, dollar **flat**, BTC down, ETH down — whereas
the old ±2% band would have falsely flagged the dollar's −0.7% as "down".

The `market_level` factory default stays `up=2.0 / down=-2.0` (unchanged
signature); only the call sites override it. No other caller exists.

**Test impact:** `scripts/tests/test_narrative_markets.py` — add/adjust cases
asserting the new bands at representative points, e.g.:
- S&P +3% → `flat`, +6% → `up`, −6% → `down`
- Bitcoin +20% → `flat`, +30% → `up`
- Dollar −0.7% → `flat`, −4% → `down`

Use real ISO dates ~1 year apart in the fixture observations so
`_value_year_ago` resolves a prior value.

## Change 3 — Honest ICE BofA credit-spread history

**File:** `scripts/lenses/config.py` (the `hy-spread` and `ig-spread`
indicators in `MARKET_RISK_SENTIMENT`)

Two edits per indicator:

1. **Lower `limit`** from `2600` to `900` with a comment explaining why
   (`# ICE BofA: FRED API only serves a rolling ~3y window`). This is honest
   about intent; functionally the API caps the response at ~785 obs regardless,
   so no data is lost.
2. **Append a transparency clause** to each indicator's `context` string so the
   "What it is" block tells the reader the chart's history is shorter than the
   others. Proposed wording (tighten as needed during implementation):
   > " Note: FRED serves only a rolling ~3-year window of this ICE BofA series,
   > so its chart history is shorter than the other indicators here."

No renderer change is needed — `lens.js` already prints `indicator.context` in
the "What it is" block.

**Test impact:** if any test asserts the exact `context` text for these two
indicators, update it; otherwise none. (`test_config_markets.py` checks
structure/series IDs, not prose — verify during implementation.)

## Stress bands — reviewed, deliberately unchanged

The Risk Sentiment severity thresholds map to **absolute, historically-grounded
levels**, not relative ones, so they are correct as written and recalibrating
them would make them worse:

- **VIX 20 / 30** — textbook calm/nervous/fearful; full history supports it.
- **HY 4.0 / 6.0%** and **IG 1.5 / 2.5%** — a 6% HY / 2.5% IG spread genuinely
  *is* credit stress historically. Current spreads (2.76% / 0.74%) correctly
  read "ok." Lowering these to fit the recent calm 3-year window would
  manufacture false "watch/elevated" signals out of normal noise.
- **NFCI 0 / 0.5** — NFCI is constructed so 0 = historical average; the bands
  are already absolute.

This decision is recorded here so a future reader does not "fix" the apparently
never-triggering thresholds without understanding the trade-off.

## Testing

- Run the full suite: `python -m unittest discover -s ".../scripts/tests" -p "test_*.py"`.
- All three changes are config/narrative only; no new modules.
- After implementation, a **live** build (`refresh_lenses.py --economic` and
  `--markets`) is the final verification — do not rely on `--dry-run`, which
  overwrites tracked `data/` from fixtures.

## Risks / notes

- The Cost of Money status assertion must be re-derived, not assumed; the
  removed indicator was contributing a status to the aggregate.
- The ICE rolling window is a property of FRED's licensing, not our code; the
  fix is transparency, not a data recovery. Longer credit-spread history would
  require a different source — a candidate for the upcoming data-source work.

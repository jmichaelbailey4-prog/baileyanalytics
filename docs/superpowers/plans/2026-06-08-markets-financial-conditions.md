# Markets & Financial Conditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third dashboard category, *Markets & Financial Conditions*, with two FRED-sourced lenses (Risk Sentiment, Asset-Class Scoreboard) and one CoinGecko-sourced lens (Crypto Market Structure).

**Architecture:** The two FRED lenses reuse the existing economic pipeline (`Indicator`/`Lens` dataclasses → `build_lens` → `build_index` → `write_outputs`) untouched, writing to `data/markets/`. The crypto lens adds a new network module `coingecko.py` (parallel to `fdic.py`) plus a `build_crypto_lens` builder and a small daily-accumulation step (a `data/markets/_crypto_history.json` file grows past CoinGecko's free 365-day window). Status uses the site's red/amber/green for Risk Sentiment, new `up`/`down`/`flat` momentum tokens for the Scoreboard, and a `neutral` lens badge for the two non-severity lenses.

**Tech Stack:** Python 3.12 stdlib only (`urllib`, `unittest`), vanilla HTML/CSS/JS, Chart.js via CDN. No third-party deps, no build step.

**Source of truth for design:** `docs/superpowers/specs/2026-06-08-markets-financial-conditions-design.md`.

**Conventions for the executing engineer:**
- Tests are `unittest`, not pytest. Run one file with `python "<abs path>/scripts/tests/test_x.py" -v`. Run the whole suite with `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" -v`.
- Never prepend `cd <repo> &&`; use absolute paths.
- **Commit locally** at each task for checkpointing, but **do not `git push`** — GitHub Pages deploys on push, and the user commits/deploys only when they ask. Deploy is the final gated step (Task 19).
- The two repos are independent git repos; run git inside `baileyanalytics/` (`git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" ...`).

---

# PHASE 1 — FRED Markets (category goes live with 2 lenses)

### Task 1: Status CSS — momentum + neutral tokens

**Files:**
- Modify: `dashboards/lens.css` (the `.s.*` scoreboard-status block at line ~31 and the `.badge.*` block at line ~21)

No automated test (CSS); verified visually in Task 8.

- [ ] **Step 1: Add momentum scoreboard-status colors**

In `dashboards/lens.css`, find the line:
```css
.s.ok{color:var(--green)} .s.watch{color:var(--amber)} .s.elevated{color:#FB923C} .s.alert{color:var(--red)} .s.unknown{color:var(--dim)}
```
Add immediately after it:
```css
.s.up{color:var(--green)} .s.down{color:var(--red)} .s.flat{color:var(--amber)} .s.info{color:var(--blue)}
```

- [ ] **Step 2: Add the neutral lens badge**

Find:
```css
.badge.unknown{background:#1d2433;color:var(--dim)}
```
Add immediately after it:
```css
.badge.neutral{background:#13233a;color:var(--blue)}
```

- [ ] **Step 3: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/lens.css
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): add momentum + neutral status styles"
```

---

### Task 2: Narrative rules — Risk Sentiment

**Files:**
- Create: `scripts/tests/test_narrative_markets.py`
- Modify: `scripts/lenses/narrative.py` (append after `rule_level_trend`, before the `HEADLINES` dict)

- [ ] **Step 1: Write failing tests**

Create `scripts/tests/test_narrative_markets.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def obs(*vals):
    """Build (date, value) tuples a year apart so _value_year_ago has a baseline."""
    return [(f"{2020 + i}-01-01", v) for i, v in enumerate(vals)]


class TestRiskSentimentRules(unittest.TestCase):
    def test_vix_bands(self):
        self.assertEqual(narrative.rule_vix([("d", 14.0)])[1], "ok")
        self.assertEqual(narrative.rule_vix([("d", 24.0)])[1], "watch")
        self.assertEqual(narrative.rule_vix([("d", 38.0)])[1], "elevated")
        self.assertEqual(narrative.rule_vix([])[1], "unknown")

    def test_credit_spread_factory(self):
        hy = narrative.credit_spread("high-yield", 4.0, 6.0)
        self.assertEqual(hy([("d", 3.2)])[1], "ok")
        self.assertEqual(hy([("d", 5.0)])[1], "watch")
        self.assertEqual(hy([("d", 7.5)])[1], "elevated")
        ig = narrative.credit_spread("investment-grade", 1.5, 2.5)
        self.assertEqual(ig([("d", 1.2)])[1], "ok")
        self.assertEqual(ig([("d", 3.0)])[1], "elevated")

    def test_financial_conditions(self):
        self.assertEqual(narrative.rule_financial_conditions([("d", -0.4)])[1], "ok")
        self.assertEqual(narrative.rule_financial_conditions([("d", 0.2)])[1], "watch")
        self.assertEqual(narrative.rule_financial_conditions([("d", 0.8)])[1], "elevated")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: FAIL — `AttributeError: module 'lenses.narrative' has no attribute 'rule_vix'`.

- [ ] **Step 3: Implement the rules**

In `scripts/lenses/narrative.py`, after `rule_level_trend` (ends at line ~352) and before `HEADLINES = {`:
```python
# --- Markets & Financial Conditions rules ---

def rule_vix(obs):
    """CBOE VIX level. <20 calm, 20-30 nervous, >=30 fearful."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 20:
        return (f"The VIX is at {v:.1f} — markets are calm.", "ok")
    if v < 30:
        return (f"The VIX is at {v:.1f} — some nervousness, but not panic.", "watch")
    return (f"The VIX is at {v:.1f} — markets are fearful.", "elevated")


def credit_spread(label, calm, stressed):
    """Factory: a credit-spread rule with its own calm/stressed thresholds (%)."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v < calm:
            return (f"The {label} spread is {v:.2f}% — tight, signaling calm credit conditions.", "ok")
        if v < stressed:
            return (f"The {label} spread is {v:.2f}% — widening off its lows.", "watch")
        return (f"The {label} spread is {v:.2f}% — wide, a sign of credit stress.", "elevated")
    return _rule


def rule_financial_conditions(obs):
    """Chicago Fed NFCI. <=0 looser than average, 0-0.5 a touch tight, >=0.5 tight."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= 0:
        return (f"The NFCI is {v:.2f} — financial conditions are looser than average.", "ok")
    if v < 0.5:
        return (f"The NFCI is {v:.2f} — conditions a touch tighter than average.", "watch")
    return (f"The NFCI is {v:.2f} — financial conditions are tight.", "elevated")
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): risk-sentiment narrative rules"
```

---

### Task 3: Narrative — momentum factory for the Scoreboard

**Files:**
- Modify: `scripts/lenses/narrative.py` (append after `rule_financial_conditions`)
- Modify: `scripts/tests/test_narrative_markets.py`

- [ ] **Step 1: Add failing tests**

Append this class to `scripts/tests/test_narrative_markets.py` (before the `if __name__` block):
```python
class TestMarketLevel(unittest.TestCase):
    def test_up_down_flat(self):
        rule = narrative.market_level("The S&P 500")
        self.assertEqual(rule(obs(100.0, 130.0))[1], "up")     # +30%
        self.assertEqual(rule(obs(100.0, 70.0))[1], "down")    # -30%
        self.assertEqual(rule(obs(100.0, 101.0))[1], "flat")   # +1%

    def test_no_year_baseline_is_flat(self):
        rule = narrative.market_level("Gold")
        self.assertEqual(rule([("2026-01-01", 2000.0)])[1], "flat")

    def test_text_includes_label_and_value(self):
        text, _ = narrative.market_level("Bitcoin")(obs(50000.0, 65000.0))
        self.assertIn("Bitcoin", text)
        self.assertIn("65,000", text)
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: FAIL — `module 'lenses.narrative' has no attribute 'market_level'`.

- [ ] **Step 3: Implement the factory**

In `scripts/lenses/narrative.py`, after `rule_financial_conditions`:
```python
def market_level(label, up=2.0, down=-2.0):
    """Factory: a momentum rule for a price/level series. Reports the trailing
    ~12-month % change and returns status 'up' / 'down' / 'flat' (momentum, not
    severity — the lens-level badge for the scoreboard is neutral)."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.2f}.", "flat")
        pct = (v - prior) / abs(prior) * 100
        if pct >= up:
            return (f"{label} is up {pct:.0f}% over the past year, now {v:,.2f}.", "up")
        if pct <= down:
            return (f"{label} is down {abs(pct):.0f}% over the past year, now {v:,.2f}.", "down")
        return (f"{label} is little changed over the past year, now {v:,.2f}.", "flat")
    return _rule
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): scoreboard momentum rule factory"
```

---

### Task 4: Narrative — headlines + neutral synthesis

**Files:**
- Modify: `scripts/lenses/narrative.py` (the `HEADLINES` dict and the `synthesize` function)
- Modify: `scripts/tests/test_narrative_markets.py`

- [ ] **Step 1: Add failing tests**

Append to `scripts/tests/test_narrative_markets.py`:
```python
class TestMarketSynthesis(unittest.TestCase):
    def test_risk_sentiment_is_severity_based(self):
        headline, overall = narrative.synthesize("market-risk-sentiment", ["ok", "watch", "ok"])
        self.assertEqual(overall, "watch")
        self.assertTrue(headline)

    def test_scoreboard_is_neutral_regardless_of_statuses(self):
        headline, overall = narrative.synthesize("market-scoreboard", ["up", "down", "flat"])
        self.assertEqual(overall, "neutral")
        self.assertTrue(headline)

    def test_crypto_is_neutral(self):
        headline, overall = narrative.synthesize("crypto-structure", ["info", "info"])
        self.assertEqual(overall, "neutral")
        self.assertTrue(headline)
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: FAIL — `test_scoreboard_is_neutral...` gets `overall == "unknown"` (momentum tokens aren't severities), not `"neutral"`.

- [ ] **Step 3: Add headlines + neutral synthesis**

In `scripts/lenses/narrative.py`, add these three entries inside the `HEADLINES` dict (after the `bank-concentrations-funding` entry, before the closing `}`):
```python
    "market-risk-sentiment": {
        "alert": "Markets are pricing acute stress.",
        "elevated": "Risk is elevated — volatility and credit spreads are climbing.",
        "watch": "A few cracks are showing — sentiment is no longer all calm.",
        "ok": "Markets are calm — volatility and credit stress are low.",
        "unknown": "Some risk indicators are temporarily unavailable.",
    },
    "market-scoreboard": {
        "neutral": "How the major asset classes are moving right now.",
    },
    "crypto-structure": {
        "neutral": "How capital is rotating across the crypto market.",
    },
```

Then replace the `synthesize` function with:
```python
NEUTRAL_LENSES = {"market-scoreboard", "crypto-structure"}


def synthesize(lens_id, statuses):
    """Combine indicator statuses into (headline_read, overall_status).

    Severity lenses aggregate to their worst status. NEUTRAL_LENSES (the markets
    scoreboard and crypto structure) carry no good/bad verdict, so they always
    report a fixed neutral headline + 'neutral' badge regardless of indicators."""
    if lens_id in NEUTRAL_LENSES:
        return HEADLINES.get(lens_id, {}).get("neutral", ""), "neutral"
    overall = util.status_max(statuses)
    headline = HEADLINES.get(lens_id, {}).get(overall, "")
    return headline, overall
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: PASS (8 tests). Also run `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative.py" -v` — existing severity behavior unchanged, PASS.

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): headlines + neutral lens synthesis"
```

---

### Task 5: Config — the two FRED market lenses + category

**Files:**
- Modify: `scripts/lenses/config.py` (append after the `BANKING_LENSES`/`CATEGORIES` block)
- Create: `scripts/tests/test_config_markets.py`

- [ ] **Step 1: Write failing tests**

Create `scripts/tests/test_config_markets.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestMarketConfig(unittest.TestCase):
    def test_two_fred_market_lenses(self):
        ids = [l.id for l in config.MARKET_FRED_LENSES]
        self.assertEqual(ids, ["market-risk-sentiment", "market-scoreboard"])

    def test_risk_sentiment_series(self):
        risk = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-risk-sentiment")
        series = {i.series_id for i in risk.indicators}
        self.assertEqual(series, {"VIXCLS", "BAMLH0A0HYM2", "BAMLC0A0CM", "NFCI"})

    def test_scoreboard_has_six_assets_incl_crypto(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertEqual(series,
            {"SP500", "DCOILWTICO", "GOLDAMGBD228NLBM", "DTWEXBGS", "CBBTCUSD", "CBETHUSD"})

    def test_scoreboard_has_no_treasury_series(self):
        # Rates are owned by Cost of Money; the scoreboard must not duplicate them.
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertNotIn("DGS10", series)
        self.assertNotIn("DGS2", series)

    def test_markets_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "markets")
        self.assertEqual(cat["out"], "markets")
        self.assertEqual(cat["disclaimer"], "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py" -v`
Expected: FAIL — `module 'lenses.config' has no attribute 'MARKET_FRED_LENSES'`.

- [ ] **Step 3: Add the lenses + category**

In `scripts/lenses/config.py`, after the `CATEGORIES = [...]` list (currently ends at line ~572), append:
```python
# ---------------------------------------------------------------------------
# Markets & Financial Conditions (category #3). Two FRED-sourced lenses reuse the
# economic Indicator/Lens pipeline unchanged; a third CoinGecko-sourced lens
# (crypto-structure) is built separately by refresh_lenses + build.build_crypto_lens.
# Rates are deliberately absent from the scoreboard — Cost of Money owns them.
# ---------------------------------------------------------------------------

MARKET_RISK_SENTIMENT = Lens(
    id="market-risk-sentiment",
    title="Risk Sentiment",
    accent="#FB7185",
    indicators=[
        Indicator(
            id="vix", title="Volatility · VIX", short="VIX", unit="", color="#FB7185",
            series_id="VIXCLS", limit=2600, rule=narrative.rule_vix,
            context=("The market's 'fear gauge' — the expected volatility of the S&P 500 "
                     "over the coming month. It spikes when investors are scared and falls when calm."),
        ),
        Indicator(
            id="hy-spread", title="High-Yield Credit Spread", short="HY spread", unit="%",
            color="#FB923C", series_id="BAMLH0A0HYM2", limit=2600,
            rule=narrative.credit_spread("high-yield", 4.0, 6.0),
            context=("The extra yield investors demand to hold risky 'junk' corporate bonds over "
                     "Treasuries. It widens when markets fear defaults — an early stress signal."),
        ),
        Indicator(
            id="ig-spread", title="Investment-Grade Credit Spread", short="IG spread", unit="%",
            color="#FBBF24", series_id="BAMLC0A0CM", limit=2600,
            rule=narrative.credit_spread("investment-grade", 1.5, 2.5),
            context=("The same risk premium for higher-quality corporate bonds. Because these "
                     "borrowers are safer, widening here signals stress reaching the core of credit."),
        ),
        Indicator(
            id="nfci", title="Financial Conditions · NFCI", short="NFCI", unit="", color="#38BDF8",
            series_id="NFCI", limit=520, rule=narrative.rule_financial_conditions,
            context=("The Chicago Fed's broad gauge of financial conditions across money, debt, and "
                     "equity markets. Zero is average; positive means tighter (more stressed) than normal."),
        ),
    ],
)

MARKET_SCOREBOARD = Lens(
    id="market-scoreboard",
    title="Asset-Class Scoreboard",
    accent="#22D3EE",
    indicators=[
        Indicator(
            id="sp500", title="S&P 500", short="S&P 500", unit="", color="#34D399",
            series_id="SP500", limit=2600, rule=narrative.market_level("The S&P 500"),
            value_format="thousands",
            context="The benchmark index of 500 large U.S. companies — the headline gauge of U.S. stocks.",
        ),
        Indicator(
            id="oil", title="Crude Oil · WTI", short="WTI oil", unit="", color="#FB923C",
            series_id="DCOILWTICO", limit=2600, rule=narrative.market_level("WTI crude"),
            context=("West Texas Intermediate, the U.S. benchmark oil price (dollars per barrel) — "
                     "a read on energy costs and global demand."),
        ),
        Indicator(
            id="gold", title="Gold", short="Gold", unit="", color="#FBBF24",
            series_id="GOLDAMGBD228NLBM", limit=2600, rule=narrative.market_level("Gold"),
            value_format="thousands",
            context=("The London afternoon gold fixing (dollars per troy ounce) — the classic "
                     "safe-haven asset investors flee to in times of stress."),
        ),
        Indicator(
            id="dollar", title="U.S. Dollar · Broad Index", short="Dollar", unit="", color="#38BDF8",
            series_id="DTWEXBGS", limit=2600, rule=narrative.market_level("The dollar index"),
            context=("The trade-weighted value of the U.S. dollar against a broad basket of "
                     "currencies — a strong dollar makes imports cheaper and U.S. exports pricier."),
        ),
        Indicator(
            id="btc", title="Bitcoin", short="Bitcoin", unit="", color="#A78BFA",
            series_id="CBBTCUSD", limit=2600, rule=narrative.market_level("Bitcoin"),
            value_format="thousands",
            context=("The price of Bitcoin in U.S. dollars (Coinbase) — the largest cryptocurrency "
                     "and a barometer of risk appetite in digital assets."),
        ),
        Indicator(
            id="eth", title="Ethereum", short="Ethereum", unit="", color="#818CF8",
            series_id="CBETHUSD", limit=2600, rule=narrative.market_level("Ethereum"),
            value_format="thousands",
            context=("The price of Ether in U.S. dollars (Coinbase) — the second-largest "
                     "cryptocurrency and the backbone of most decentralized applications."),
        ),
    ],
)

MARKET_FRED_LENSES = [MARKET_RISK_SENTIMENT, MARKET_SCOREBOARD]

CATEGORIES.append(
    {"id": "markets", "title": "Markets & Financial Conditions", "lenses": MARKET_FRED_LENSES,
     "out": "markets", "back": "Markets & Financial Conditions",
     "source_label": "FRED (St. Louis Fed) and CoinGecko", "disclaimer": ""}
)
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_config_markets.py" -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): config for risk-sentiment + scoreboard lenses"
```

---

### Task 6: Markets fixture (offline build data)

**Files:**
- Create: `scripts/tests/fixtures/markets_sample.json`

This fixture is keyed by `fetch_key` (`"<SERIES>:lin"`), matching `fetched_sample.json`. Each series needs ≥2 points a year apart so `market_level`/`_value_year_ago` produce a real read. Include `CBBTCUSD`/`CBETHUSD` (also used by the crypto lens's BTC/ETH ratio in Phase 2).

- [ ] **Step 1: Create the fixture**

Create `scripts/tests/fixtures/markets_sample.json`:
```json
{
  "VIXCLS:lin": [
    {"date": "2025-06-02", "value": "16.20"},
    {"date": "2026-06-02", "value": "18.50"}
  ],
  "BAMLH0A0HYM2:lin": [
    {"date": "2025-06-02", "value": "3.10"},
    {"date": "2026-06-02", "value": "3.45"}
  ],
  "BAMLC0A0CM:lin": [
    {"date": "2025-06-02", "value": "1.10"},
    {"date": "2026-06-02", "value": "1.25"}
  ],
  "NFCI:lin": [
    {"date": "2025-05-30", "value": "-0.45"},
    {"date": "2026-05-29", "value": "-0.38"}
  ],
  "SP500:lin": [
    {"date": "2025-06-02", "value": "5400.00"},
    {"date": "2026-06-02", "value": "6100.00"}
  ],
  "DCOILWTICO:lin": [
    {"date": "2025-06-02", "value": "72.50"},
    {"date": "2026-06-02", "value": "68.30"}
  ],
  "GOLDAMGBD228NLBM:lin": [
    {"date": "2025-06-02", "value": "2350.00"},
    {"date": "2026-06-02", "value": "2710.00"}
  ],
  "DTWEXBGS:lin": [
    {"date": "2025-06-02", "value": "121.40"},
    {"date": "2026-06-02", "value": "119.10"}
  ],
  "CBBTCUSD:lin": [
    {"date": "2025-06-02", "value": "52000.00"},
    {"date": "2026-06-02", "value": "65000.00"}
  ],
  "CBETHUSD:lin": [
    {"date": "2025-06-02", "value": "2800.00"},
    {"date": "2026-06-02", "value": "3100.00"}
  ]
}
```

- [ ] **Step 2: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/fixtures/markets_sample.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(markets): offline FRED fixture"
```

---

### Task 7: Orchestration — `refresh_markets` (FRED only, Phase 1)

**Files:**
- Modify: `scripts/refresh_lenses.py` (paths near line 20; new `refresh_markets`; `main` flag wiring)
- Create: `scripts/tests/test_refresh_markets.py`

- [ ] **Step 1: Write failing tests**

Create `scripts/tests/test_refresh_markets.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config


class TestMarketsDryRun(unittest.TestCase):
    def _build(self):
        import json
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        return [build.build_lens(l, fetched) for l in config.MARKET_FRED_LENSES]

    def test_builds_two_fred_market_lenses(self):
        jsons = self._build()
        self.assertEqual({j["id"] for j in jsons},
                         {"market-risk-sentiment", "market-scoreboard"})

    def test_scoreboard_status_is_neutral_and_has_momentum_signals(self):
        board = next(j for j in self._build() if j["id"] == "market-scoreboard")
        self.assertEqual(board["status"], "neutral")
        statuses = {i["signal_status"] for i in board["indicators"]}
        self.assertTrue(statuses <= {"up", "down", "flat"})

    def test_markets_flag_is_recognized(self):
        args = refresh_lenses.main.__wrapped__ if hasattr(refresh_lenses.main, "__wrapped__") else None
        # Flag parsing smoke: argparse accepts --markets without error.
        parser_ok = True
        try:
            refresh_lenses.main(["--markets", "--dry-run"])
        except SystemExit:
            parser_ok = False
        self.assertTrue(parser_ok)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_markets.py" -v`
Expected: FAIL — `module 'refresh_lenses' has no attribute 'MARKET_FIXTURE'`.

- [ ] **Step 3: Add paths, `refresh_markets`, and flag wiring**

In `scripts/refresh_lenses.py`, after the existing path constants (line ~23), add:
```python
MARKETS_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "markets"
MARKET_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "markets_sample.json"
```

Add this function after `refresh_banking` (line ~151):
```python
def refresh_markets(dry_run):
    """Build + write the markets (FRED) lenses. Returns an exit code (0 ok, non-zero error).

    Phase 1: the two FRED-sourced lenses only. The CoinGecko crypto lens is added
    to this function in Phase 2.
    """
    if dry_run:
        fetched = json.loads(MARKET_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.MARKET_FRED_LENSES, api_key)

    ready = [lens for lens in config.MARKET_FRED_LENSES if lens_ready(lens, failed)]
    for lens in config.MARKET_FRED_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)

    market_jsons = [build.build_lens(lens, fetched) for lens in ready]
    written = build.write_outputs(market_jsons, MARKETS_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all markets data up to date.")
    return 0
```

Replace the flag logic in `main` (lines ~157-171). Change the argument block to add `--markets`:
```python
    parser.add_argument("--markets", action="store_true", help="refresh only the markets lenses")
```
(add it right after the existing `--banking` argument line.)

Then replace the dispatch block:
```python
    # No source flag = refresh everything; each flag scopes the run so a workflow
    # can give each source its own cadence.
    any_flag = args.economic or args.banking or args.markets
    do_economic = args.economic or not any_flag
    do_banking = args.banking or not any_flag
    do_markets = args.markets or not any_flag

    code = 0
    if do_economic:
        code = refresh_economic(args.dry_run)
        if code:
            return code
    if do_markets:
        mc = refresh_markets(args.dry_run)
        if mc:
            code = mc
    if do_banking:
        refresh_banking(args.dry_run)
    return code
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_markets.py" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_refresh_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): refresh_markets orchestration + --markets flag"
```

---

### Task 8: Pages — markets overview, two lens pages, hub card

**Files:**
- Create: `dashboards/markets/index.html`
- Create: `dashboards/markets/risk-sentiment.html`
- Create: `dashboards/markets/scoreboard.html`
- Modify: `dashboards/index.html` (add the third category section + a third `loadGrid` call)

- [ ] **Step 1: Create the two lens pages**

`dashboards/markets/risk-sentiment.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Risk Sentiment — Bailey Analytics</title>
  <meta name="description" content="How much stress markets are pricing — VIX, credit spreads, and the Chicago Fed financial-conditions index, from FRED.">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading&hellip;</div></main>
  <script src="/dashboards/lens.js"></script>
  <script>
    renderLens("/data/markets/market-risk-sentiment.json", {
      back: "Markets & Financial Conditions",
      href: "/dashboards/markets/",
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a>, St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
    });
  </script>
</body>
</html>
```

`dashboards/markets/scoreboard.html` — identical except `<title>Asset-Class Scoreboard — Bailey Analytics</title>`, the description `"How the major asset classes are moving — stocks, oil, gold, the dollar, and crypto, from FRED."`, and `renderLens("/data/markets/market-scoreboard.json", { ... same back/href/foot ... });`.

- [ ] **Step 2: Create the overview page**

`dashboards/markets/index.html` — copy `dashboards/banking/index.html` and change: `<title>` and meta to Markets; the `<h1>` to `Markets & Financial Conditions`; the lede to *"What are markets pricing right now? Each lens turns public market data into a plain-English read — the stress in volatility and credit, where the major asset classes are headed, and how capital is rotating across crypto."*; the fetch URL to `/data/markets/index.json`; the footer source line to *"Data: FRED (St. Louis Fed) and CoinGecko. Public data, refreshed daily."*; and **replace the `tile` slug logic** — markets ids have no `bank-` prefix and map to short page slugs. Use this `tile`:
```javascript
    const SLUGS = {
      "market-risk-sentiment": "risk-sentiment",
      "market-scoreboard": "scoreboard",
      "crypto-structure": "crypto-structure"
    };
    function tile(lens) {
      const slug = SLUGS[lens.id] || lens.id;
      const stats = (lens.key_stats || [])
        .map(s => `<span>${esc(s.k)} <b>${esc(s.v)}</b></span>`).join("");
      return `
        <a class="hub-card" href="/dashboards/markets/${encodeURIComponent(slug)}.html">
          <div class="hub-eyebrow" style="color:${lens.accent}">${esc(lens.title)}
            <span class="badge ${esc(lens.status)}">${esc(lens.status)}</span></div>
          <div class="hub-read">${esc(lens.headline_read)}</div>
          ${sparkline(lens.sparkline, lens.accent)}
          <div class="hub-stats">${stats}</div>
          <div class="hub-cta">View lens &rarr;</div>
        </a>`;
    }
```
(`crypto-structure` is listed now; its page arrives in Phase 2. Until then the markets index.json simply won't contain it, so no broken card appears.)

- [ ] **Step 3: Add the category to the main hub**

In `dashboards/index.html`, after the Banking System Health section (line ~45), add:
```html
    <h2 class="cat-head"><span class="dot" style="background:#22D3EE"></span>Markets &amp; Financial Conditions</h2>
    <p class="cat-sub">What markets are pricing — risk sentiment, the major asset classes, and crypto market structure. Refreshed daily from FRED and CoinGecko. <a href="/dashboards/markets/" style="color:var(--blue);text-decoration:none">Overview &rarr;</a></p>
    <div class="hub-grid" id="markets-grid"><div class="status-msg">Loading&hellip;</div></div>
```
Then, in the `<script>` block, after the existing `loadGrid("/data/banking/index.json", ...)` call (line ~94), add:
```javascript
    const MARKET_SLUGS = {
      "market-risk-sentiment": "risk-sentiment",
      "market-scoreboard": "scoreboard",
      "crypto-structure": "crypto-structure"
    };
    loadGrid("/data/markets/index.json", "markets-grid",
             id => `/dashboards/markets/${encodeURIComponent(MARKET_SLUGS[id] || id)}.html`);
```

- [ ] **Step 4: Build data + smoke-test locally**

Generate the markets data offline, then serve and eyeball:
```bash
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --markets --dry-run
```
Expected: `Wrote .../data/markets/market-risk-sentiment.json`, `market-scoreboard.json`, and `index.json`.
Then: `python -m http.server 8000` from the repo root and open `http://localhost:8000/dashboards/markets/` and each lens page. Confirm: scoreboard badge reads `neutral`, asset rows show `up`/`down`/`flat` in green/red/amber, risk-sentiment shows a severity badge, charts render. (This dry-run data is fixture-based and will be overwritten by the live build in Task 10 — that's fine.)

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/markets/ dashboards/index.html data/markets/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(markets): overview, lens pages, hub card"
```

---

### Task 9: Daily workflow — refresh markets

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`

- [ ] **Step 1: Add a markets refresh step**

In `.github/workflows/refresh-fred.yml`, after the "Fetch latest FRED data (economic lenses)" step (line ~27) and before the "Commit and push" step, insert:
```yaml
      - name: Fetch latest markets data (FRED + CoinGecko)
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python scripts/refresh_lenses.py --markets
```
(In Phase 1 this runs the two FRED lenses; once Phase 2 lands, the same command also fetches CoinGecko — no further workflow change needed. The existing `git add data/` step already picks up `data/markets/`.)

- [ ] **Step 2: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add .github/workflows/refresh-fred.yml
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "ci(markets): refresh markets data daily"
```

---

### Task 10: Phase 1 verification — full suite + live FRED build

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" -v`
Expected: all tests pass (the prior 119 + the new markets tests).

- [ ] **Step 2: Live FRED build (real data)**

With a FRED key available:
```bash
$env:FRED_API_KEY = "<key>"
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --markets
```
Expected: writes real `data/markets/market-risk-sentiment.json`, `market-scoreboard.json`, `index.json`. If a series id is wrong, FRED returns an error and the run prints `WARN: fetch failed for <SERIES>` — fix the id in config and rebuild. Spot-check the JSON: latest values are sane (VIX ~10-40, SP500 a few thousand, BTC tens of thousands).

- [ ] **Step 3: Commit the real data**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add data/markets/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "data(markets): initial live FRED build"
```
Do **not** push yet — Phase 2 follows, and deploy is gated to Task 19.

---

# PHASE 2 — CoinGecko Crypto Market Structure lens

### Task 11: CoinGecko fetcher — network functions

**Files:**
- Create: `scripts/lenses/coingecko.py`
- Create: `scripts/tests/test_coingecko.py`

- [ ] **Step 1: Write failing tests (mocked network)**

Create `scripts/tests/test_coingecko.py`:
```python
import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import coingecko


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestTopCoins(unittest.TestCase):
    def test_excludes_stablecoins(self):
        payload = [
            {"id": "bitcoin", "symbol": "btc", "current_price": 60000, "market_cap": 1.2e12},
            {"id": "tether", "symbol": "usdt", "current_price": 1.0, "market_cap": 9e10},
            {"id": "ethereum", "symbol": "eth", "current_price": 3000, "market_cap": 4e11},
            {"id": "some-usd", "symbol": "x", "current_price": 1.0, "market_cap": 1e10},
            {"id": "solana", "symbol": "sol", "current_price": 150, "market_cap": 7e10},
        ]
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            coins = coingecko.top_coins(3)
        self.assertEqual([c["id"] for c in coins], ["bitcoin", "ethereum", "solana"])

    def test_market_cap_history_parses_ms_to_date(self):
        payload = {"market_caps": [[1700000000000, 1.0e12], [1700086400000, 1.1e12]]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            hist = coingecko.market_cap_history("bitcoin", days=2)
        self.assertEqual(hist[0]["date"], "2023-11-14")
        self.assertEqual(hist[1]["value"], 1.1e12)

    def test_global_metrics_extracts_btc_dominance(self):
        payload = {"data": {"market_cap_percentage": {"btc": 54.3, "eth": 17.1}}}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            self.assertEqual(coingecko.global_metrics()["btc_dominance"], 54.3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_coingecko.py" -v`
Expected: FAIL — `No module named 'lenses.coingecko'`.

- [ ] **Step 3: Implement the fetcher**

Create `scripts/lenses/coingecko.py`:
```python
"""CoinGecko API access — crypto market-structure data. No key (free public tier).

The free tier has no historical total-market-cap or dominance *series*, so the
large-vs-small rotation is built from per-coin market-cap history
(`/coins/{id}/market_chart`, 365 days free). BTC dominance comes from `/global`
as a current point and is accumulated daily by the caller.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.coingecko.com/api/v3"

# Top stablecoins by id — excluded from the "small/mid-cap" basket (a price≈$1
# heuristic backstops anything not listed here).
STABLECOINS = {
    "tether", "usd-coin", "dai", "first-digital-usd", "usds", "ethena-usde",
    "binance-usd", "trueusd", "paxos-standard", "usdd", "frax", "gemini-dollar",
}


def _get(path, params, timeout):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            raise


def top_coins(n=10, timeout=15):
    """Top `n` non-stablecoin coins by market cap: [{'id','symbol','market_cap'}]."""
    rows = _get("/coins/markets",
                {"vs_currency": "usd", "order": "market_cap_desc",
                 "per_page": n + 10, "page": 1}, timeout)
    out = []
    for r in rows:
        if r.get("id") in STABLECOINS:
            continue
        price = r.get("current_price") or 0
        if 0.95 <= price <= 1.05:  # stablecoin heuristic backstop
            continue
        out.append({"id": r["id"], "symbol": r.get("symbol", ""),
                    "market_cap": r.get("market_cap") or 0})
        if len(out) >= n:
            break
    return out


def market_cap_history(coin_id, days=365, timeout=15):
    """Daily market-cap history for one coin: [{'date','value'}], oldest-first."""
    data = _get(f"/coins/{coin_id}/market_chart",
                {"vs_currency": "usd", "days": days, "interval": "daily"}, timeout)
    out = []
    for ms, cap in data.get("market_caps", []):
        d = time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))
        out.append({"date": d, "value": cap})
    return out


def global_metrics(timeout=15):
    """Current global crypto metrics. Returns {'btc_dominance': float|None}."""
    data = _get("/global", {}, timeout).get("data", {})
    pct = data.get("market_cap_percentage", {}).get("btc")
    return {"btc_dominance": pct}
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_coingecko.py" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/coingecko.py scripts/tests/test_coingecko.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): CoinGecko fetcher"
```

---

### Task 12: Crypto compute — basket sum + rotation index

**Files:**
- Modify: `scripts/lenses/coingecko.py` (append pure compute functions)
- Modify: `scripts/tests/test_coingecko.py`

- [ ] **Step 1: Add failing tests**

Append to `scripts/tests/test_coingecko.py` (before `if __name__`):
```python
class TestCompute(unittest.TestCase):
    def test_basket_history_sums_by_date(self):
        a = [{"date": "2026-01-01", "value": 10.0}, {"date": "2026-01-02", "value": 12.0}]
        b = [{"date": "2026-01-01", "value": 5.0}, {"date": "2026-01-02", "value": 6.0}]
        out = coingecko.basket_history([a, b])
        self.assertEqual(out, [{"date": "2026-01-01", "value": 15.0},
                               {"date": "2026-01-02", "value": 18.0}])

    def test_compute_rotation_indexes_and_ratios(self):
        # large doubles, small triples -> small outperforms -> ratio rises above 100.
        large = [{"date": "2026-01-01", "value": 100.0}, {"date": "2026-01-02", "value": 200.0}]
        small = [{"date": "2026-01-01", "value": 50.0}, {"date": "2026-01-02", "value": 150.0}]
        out = coingecko.compute_rotation(large, small)
        self.assertEqual(out[0]["value"], 100.0)          # base date indexed to 100/100
        self.assertEqual(out[1]["value"], 150.0)          # (300/100)/(200/100)*100 = 150

    def test_compute_rotation_handles_no_overlap(self):
        self.assertEqual(coingecko.compute_rotation([], []), [])
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_coingecko.py" -v`
Expected: FAIL — `module 'lenses.coingecko' has no attribute 'basket_history'`.

- [ ] **Step 3: Implement compute functions**

Append to `scripts/lenses/coingecko.py`:
```python
def basket_history(coin_histories):
    """Sum market caps by date across coins. Input: list of [{'date','value'}]."""
    totals = {}
    for hist in coin_histories:
        for pt in hist:
            totals[pt["date"]] = totals.get(pt["date"], 0.0) + (pt["value"] or 0.0)
    return [{"date": d, "value": totals[d]} for d in sorted(totals)]


def compute_rotation(large_basket, small_basket):
    """Small-vs-large relative performance, indexed to 100 at the first common date.

    Returns [{'date','value'}] where value = (small_idx / large_idx) * 100. Rising
    means the small/mid-cap basket is outperforming the large-cap basket.
    """
    large = {p["date"]: p["value"] for p in large_basket}
    small = {p["date"]: p["value"] for p in small_basket}
    dates = [d for d in sorted(set(large) & set(small)) if large[d] and small[d]]
    if not dates:
        return []
    l0, s0 = large[dates[0]], small[dates[0]]
    out = []
    for d in dates:
        l_idx = large[d] / l0 * 100
        s_idx = small[d] / s0 * 100
        out.append({"date": d, "value": round(s_idx / l_idx * 100, 2)})
    return out


def crypto_market_structure(timeout=15, throttle=1.5):
    """Fetch + compute today's rotation series and current BTC dominance.

    Returns {'rotation': [{date,value}], 'dominance_point': {date, value}}.
    The top two non-stablecoins (reliably BTC + ETH) form the large-cap basket;
    ranks 3-10 form the small/mid-cap basket.
    """
    import datetime
    coins = top_coins(10, timeout)
    histories = {}
    for c in coins:
        histories[c["id"]] = market_cap_history(c["id"], 365, timeout)
        time.sleep(throttle)
    large = basket_history([histories[c["id"]] for c in coins[:2]])
    small = basket_history([histories[c["id"]] for c in coins[2:10]])
    rotation = compute_rotation(large, small)
    dom = global_metrics(timeout)["btc_dominance"]
    today = datetime.date.today().isoformat()
    return {"rotation": rotation, "dominance_point": {"date": today, "value": dom}}
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_coingecko.py" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/coingecko.py scripts/tests/test_coingecko.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): basket + rotation compute"
```

---

### Task 13: `util.merge_series` — daily accumulation helper

**Files:**
- Modify: `scripts/lenses/util.py`
- Modify: `scripts/tests/test_util.py`

- [ ] **Step 1: Add failing test**

Append to `scripts/tests/test_util.py` (inside the file; if it has a single test class, add a new class before `if __name__`):
```python
class TestMergeSeries(unittest.TestCase):
    def test_new_wins_and_old_is_retained(self):
        from lenses import util
        old = [{"date": "2026-01-01", "value": 1.0}, {"date": "2026-01-02", "value": 2.0}]
        new = [{"date": "2026-01-02", "value": 9.0}, {"date": "2026-01-03", "value": 3.0}]
        self.assertEqual(util.merge_series(old, new), [
            {"date": "2026-01-01", "value": 1.0},
            {"date": "2026-01-02", "value": 9.0},
            {"date": "2026-01-03", "value": 3.0},
        ])

    def test_handles_none(self):
        from lenses import util
        self.assertEqual(util.merge_series(None, [{"date": "2026-01-01", "value": 1.0}]),
                         [{"date": "2026-01-01", "value": 1.0}])
```
(Confirm `test_util.py` imports `unittest` and `from lenses import util`; if not, mirror the import header used by `test_narrative_markets.py`.)

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_util.py" -v`
Expected: FAIL — `module 'lenses.util' has no attribute 'merge_series'`.

- [ ] **Step 3: Implement**

Append to `scripts/lenses/util.py`:
```python
def merge_series(old, new):
    """Merge two [{'date','value'}] lists by date; `new` wins on conflicts. Sorted.

    Used to accumulate crypto history across daily refreshes so it grows past
    CoinGecko's free 365-day window: today's recomputed points refresh the recent
    window, while older points beyond the window persist from prior runs.
    """
    merged = {p["date"]: p["value"] for p in (old or [])}
    for p in (new or []):
        merged[p["date"]] = p["value"]
    return [{"date": d, "value": merged[d]} for d in sorted(merged)]
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_util.py" -v`
Expected: PASS.

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/util.py scripts/tests/test_util.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): merge_series accumulation helper"
```

---

### Task 14: Crypto narrative rules

**Files:**
- Modify: `scripts/lenses/narrative.py` (append after `market_level`)
- Modify: `scripts/tests/test_narrative_markets.py`

- [ ] **Step 1: Add failing tests**

Append to `scripts/tests/test_narrative_markets.py`:
```python
class TestCryptoRules(unittest.TestCase):
    def test_rotation_risk_on_off_balanced(self):
        # 90-point window: last value vs ~90 ago.
        rising = [(f"2026-{i:02d}", 100.0 + i) for i in range(1, 13)]
        self.assertEqual(narrative.rule_crypto_rotation(rising)[1], "info")
        self.assertIn("alts", narrative.rule_crypto_rotation(rising)[0].lower())

    def test_dominance_text(self):
        text, status = narrative.rule_btc_dominance([("d", 54.0)])
        self.assertEqual(status, "info")
        self.assertIn("54", text)

    def test_btc_eth_relative(self):
        self.assertEqual(narrative.rule_btc_eth_relative([("d", 20.0)])[1], "info")
        self.assertEqual(narrative.rule_btc_eth_relative([])[1], "unknown")
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: FAIL — `module 'lenses.narrative' has no attribute 'rule_crypto_rotation'`.

- [ ] **Step 3: Implement the crypto rules**

In `scripts/lenses/narrative.py`, after `market_level`:
```python
def rule_crypto_rotation(obs):
    """Large-vs-small rotation index (base 100). Compares the latest value to ~90
    observations ago to read risk-on (alts outperforming) vs risk-off (flight to majors)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    base = obs[max(0, len(obs) - 90)][1] or v
    if v >= base * 1.03:
        return ("Small- and mid-cap coins are outperforming Bitcoin and Ether — a risk-on "
                "rotation into alts.", "info")
    if v <= base * 0.97:
        return ("Capital is rotating back toward Bitcoin and Ether — a risk-off tilt within "
                "crypto.", "info")
    return ("Large and small caps are moving roughly in step — no clear rotation.", "info")


def rule_btc_dominance(obs):
    """Bitcoin's share of total crypto market value (%)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    return (f"Bitcoin is {v:.0f}% of total crypto market value.", "info")


def rule_btc_eth_relative(obs):
    """BTC/ETH price ratio — which of the two majors is leading over the past year."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if prior is None or prior == 0:
        return (f"The Bitcoin/Ether ratio is {v:.2f}.", "info")
    if v >= prior * 1.05:
        return (f"Bitcoin has gained on Ether over the past year (ratio {v:.2f}).", "info")
    if v <= prior * 0.95:
        return (f"Ether has gained on Bitcoin over the past year (ratio {v:.2f}).", "info")
    return (f"Bitcoin and Ether have held their relative value (ratio {v:.2f}).", "info")
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_narrative_markets.py" -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): crypto-structure narrative rules"
```

---

### Task 15: `build.build_crypto_lens`

**Files:**
- Modify: `scripts/lenses/build.py` (add after `build_banking_lens`)
- Create: `scripts/tests/test_build_markets.py`

- [ ] **Step 1: Write failing tests**

Create `scripts/tests/test_build_markets.py`:
```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build


class TestBuildCryptoLens(unittest.TestCase):
    def setUp(self):
        self.rotation = [{"date": "2026-01-01", "value": 100.0},
                         {"date": "2026-04-01", "value": 108.0}]
        self.dominance = [{"date": "2026-04-01", "value": 54.0}]
        self.btc_eth = [{"date": "2026-04-01", "value": 20.5}]

    def test_shape_and_ids(self):
        lj = build.build_crypto_lens(self.rotation, self.dominance, self.btc_eth)
        self.assertEqual(lj["id"], "crypto-structure")
        self.assertEqual(lj["status"], "neutral")
        ids = [i["id"] for i in lj["indicators"]]
        self.assertEqual(ids, ["crypto-rotation", "btc-dominance", "btc-eth-ratio"])
        self.assertEqual(lj["indicators"][0]["observations"], self.rotation)
        self.assertEqual(lj["indicators"][0]["latest"]["value"], 108.0)

    def test_renders_in_index(self):
        lj = build.build_crypto_lens(self.rotation, self.dominance, self.btc_eth)
        idx = build.build_index([lj])
        self.assertEqual(idx["lenses"][0]["id"], "crypto-structure")
        self.assertTrue(idx["lenses"][0]["sparkline"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build_markets.py" -v`
Expected: FAIL — `module 'lenses.build' has no attribute 'build_crypto_lens'`.

- [ ] **Step 3: Implement the builder**

In `scripts/lenses/build.py`, after `build_banking_lens` (line ~131):
```python
def build_crypto_lens(rotation_obs, dominance_obs, btc_eth_obs):
    """Assemble the CoinGecko/FRED crypto-structure lens JSON from three prepared
    series. Produces the standard lens shape (no tiers/rankings), so lens.js renders
    it with the existing single-line chart component."""
    specs = [
        ("crypto-rotation", "Large-vs-Small Rotation", "Alt rotation", "", "#818CF8",
         rotation_obs, narrative.rule_crypto_rotation,
         ("Small- and mid-cap coins' market value relative to Bitcoin and Ether, indexed to "
          "100 at the start of the window. Rising means alts are outperforming (risk-on); "
          "falling means a flight to the majors."), "decimal"),
        ("btc-dominance", "Bitcoin Dominance", "BTC dominance", "%", "#FBBF24",
         dominance_obs, narrative.rule_btc_dominance,
         ("Bitcoin's share of total cryptocurrency market value. A rising share signals "
          "caution; a falling share signals risk appetite. History accumulates daily."), "decimal"),
        ("btc-eth-ratio", "Bitcoin / Ether Ratio", "BTC/ETH", "", "#A78BFA",
         btc_eth_obs, narrative.rule_btc_eth_relative,
         ("The price of Bitcoin divided by the price of Ether — which of the two largest coins "
          "is leading. Sourced from FRED's decade-long price history."), "decimal"),
    ]
    indicators, statuses = [], []
    for id_, title, short, unit, color, obs, rule, context, vfmt in specs:
        text, status = rule(util.clean(obs))
        statuses.append(status)
        indicators.append({
            "id": id_, "title": title, "short": short, "unit": unit, "color": color,
            "observations": obs, "latest": _latest_raw(obs), "context": context,
            "read": text, "signal_status": status, "value_format": vfmt,
        })
    headline, overall = narrative.synthesize("crypto-structure", statuses)
    return {
        "id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#818CF8",
        "last_updated": _now(), "status": overall, "headline_read": headline,
        "recessions": [], "indicators": indicators,
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_build_markets.py" -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/build.py scripts/tests/test_build_markets.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): build_crypto_lens"
```

---

### Task 16: Crypto fixture + wire crypto into `refresh_markets`

**Files:**
- Create: `scripts/tests/fixtures/coingecko_sample.json`
- Modify: `scripts/refresh_lenses.py` (paths; `_btc_eth_ratio`, `_load_crypto_history`, `_build_crypto`; call from `refresh_markets`)
- Modify: `scripts/tests/test_refresh_markets.py`

- [ ] **Step 1: Create the CoinGecko fixture**

Create `scripts/tests/fixtures/coingecko_sample.json` (the shape `crypto_market_structure` returns):
```json
{
  "rotation": [
    {"date": "2025-06-02", "value": 100.0},
    {"date": "2026-06-02", "value": 112.5}
  ],
  "dominance_point": {"date": "2026-06-02", "value": 54.2}
}
```

- [ ] **Step 2: Add failing tests**

Append to `scripts/tests/test_refresh_markets.py`:
```python
class TestCryptoBuild(unittest.TestCase):
    def test_build_crypto_offline(self):
        import json
        fresh = json.loads(refresh_lenses.CRYPTO_FIXTURE.read_text(encoding="utf-8"))
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        btc_eth = refresh_lenses._btc_eth_ratio(fetched)
        lj = build.build_crypto_lens(fresh["rotation"], [fresh["dominance_point"]], btc_eth)
        self.assertEqual(lj["id"], "crypto-structure")
        self.assertTrue(lj["indicators"][2]["observations"])  # BTC/ETH ratio present

    def test_btc_eth_ratio_from_fred(self):
        import json
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        ratio = refresh_lenses._btc_eth_ratio(fetched)
        # 65000 / 3100 ≈ 20.97 on the latest shared date
        self.assertAlmostEqual(ratio[-1]["value"], 65000.0 / 3100.0, places=2)
```

- [ ] **Step 3: Run to verify failure**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_markets.py" -v`
Expected: FAIL — `module 'refresh_lenses' has no attribute 'CRYPTO_FIXTURE'`.

- [ ] **Step 4: Wire crypto into the orchestration**

In `scripts/refresh_lenses.py`, update the import line (line ~18) to include `coingecko`:
```python
from lenses import build, config, fdic, fred, coingecko
```
Add path constants next to `MARKET_FIXTURE`:
```python
CRYPTO_HISTORY = MARKETS_OUT_DIR / "_crypto_history.json"
CRYPTO_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "coingecko_sample.json"
```
Add these helpers above `refresh_markets`:
```python
def _btc_eth_ratio(fetched):
    """BTC/ETH price ratio from already-fetched FRED series (no extra network call)."""
    from lenses import util
    btc = {o["date"]: util.to_float(o["value"]) for o in fetched.get("CBBTCUSD:lin", [])}
    eth = {o["date"]: util.to_float(o["value"]) for o in fetched.get("CBETHUSD:lin", [])}
    out = []
    for d in sorted(set(btc) & set(eth)):
        if btc[d] is not None and eth[d] not in (None, 0):
            out.append({"date": d, "value": round(btc[d] / eth[d], 4)})
    return out


def _load_crypto_history():
    if CRYPTO_HISTORY.exists():
        try:
            return json.loads(CRYPTO_HISTORY.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"rotation": [], "dominance": []}


def _build_crypto(dry_run, fetched):
    """Build the crypto-structure lens JSON, accumulating history. Additive — on any
    failure, keep the prior crypto data (re-read it so the markets index stays complete)."""
    from lenses import util
    try:
        if dry_run:
            fresh = json.loads(CRYPTO_FIXTURE.read_text(encoding="utf-8"))
        else:
            fresh = coingecko.crypto_market_structure()
        hist = _load_crypto_history()
        rotation = util.merge_series(hist.get("rotation"), fresh["rotation"])
        dominance = util.merge_series(hist.get("dominance"), [fresh["dominance_point"]])
        CRYPTO_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        CRYPTO_HISTORY.write_text(
            json.dumps({"rotation": rotation, "dominance": dominance}, indent=2) + "\n",
            encoding="utf-8")
        return build.build_crypto_lens(rotation, dominance, _btc_eth_ratio(fetched))
    except Exception as exc:  # noqa: BLE001 - never break the run on a crypto failure
        print(f"WARN: crypto refresh failed ({exc}); keeping previous crypto data", file=sys.stderr)
        prior = MARKETS_OUT_DIR / "crypto-structure.json"
        if prior.exists():
            try:
                return json.loads(prior.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None
        return None
```
Then, inside `refresh_markets`, insert the crypto build between `market_jsons = [...]` and `written = build.write_outputs(...)`:
```python
    crypto_json = _build_crypto(dry_run, fetched)
    if crypto_json:
        market_jsons.append(crypto_json)
```

- [ ] **Step 5: Run to verify pass**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_refresh_markets.py" -v`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_refresh_markets.py scripts/tests/fixtures/coingecko_sample.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): accumulate + build crypto lens in refresh_markets"
```

---

### Task 17: Crypto lens page

**Files:**
- Create: `dashboards/markets/crypto-structure.html`

- [ ] **Step 1: Create the page**

`dashboards/markets/crypto-structure.html` — same template as the other lens pages:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Crypto Market Structure — Bailey Analytics</title>
  <meta name="description" content="How capital rotates across crypto — large-vs-small-cap performance, Bitcoin dominance, and the BTC/ETH ratio, from CoinGecko and FRED.">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading&hellip;</div></main>
  <script src="/dashboards/lens.js"></script>
  <script>
    renderLens("/data/markets/crypto-structure.json", {
      back: "Markets & Financial Conditions",
      href: "/dashboards/markets/",
      foot: 'Data: <a href="https://www.coingecko.com/" target="_blank" rel="noopener">CoinGecko</a> (market structure) and <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (BTC/ETH prices). Rotation history accumulates daily. The "read" is generated from the latest values by a fixed rule set.'
    });
  </script>
</body>
</html>
```

- [ ] **Step 2: Build crypto data offline + smoke-test**

```bash
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --markets --dry-run
```
Expected: now also writes `data/markets/crypto-structure.json` and `data/markets/_crypto_history.json`; the markets `index.json` now has 3 lenses. Serve (`python -m http.server 8000`) and open `http://localhost:8000/dashboards/markets/crypto-structure.html` — three charts render, badge reads `neutral`, the overview page now shows a third card.

- [ ] **Step 3: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/markets/crypto-structure.html data/markets/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(crypto): crypto-structure lens page"
```

---

### Task 18: Phase 2 verification — full suite + live build

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" -v`
Expected: all pass.

- [ ] **Step 2: Live build (FRED + CoinGecko)**

```bash
$env:FRED_API_KEY = "<key>"
python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --markets
```
Expected: writes all three market lens JSONs + `_crypto_history.json`. The rotation series should have ~365 points; dominance starts with one point (grows daily). If CoinGecko rate-limits (HTTP 429), the built-in backoff retries; if it still fails, the run prints `WARN: crypto refresh failed` and keeps prior data — re-run after a minute. Spot-check `crypto-structure.json`: rotation ~100±, dominance 40-60%, BTC/ETH ratio ~15-25.

- [ ] **Step 3: Commit the real data**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add data/markets/
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "data(crypto): initial live crypto build"
```

---

### Task 19: Deploy gate (user-approved)

**Files:** none

- [ ] **Step 1: Confirm with the user before pushing**

GitHub Pages deploys on push to `main`. Per the user's standing rule, **ask for explicit approval**, then:
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" push
```

- [ ] **Step 2: Post-deploy check**

After the Pages build, open `https://baileyanalytics.com/dashboards/` and confirm the Markets category appears with all three lenses, and the daily `Refresh FRED data` workflow's next run picks up `--markets` without error.

---

## Self-Review

**Spec coverage:** Risk Sentiment (Tasks 2,5,8) ✓; Asset-Class Scoreboard incl. BTC/ETH from FRED, rates omitted (Tasks 3,5 + `test_scoreboard_has_no_treasury_series`) ✓; Crypto Market Structure rotation/dominance/BTC-ETH (Tasks 11-17) ✓; CoinGecko free-tier 365-day approach + daily accumulation (Tasks 11-13,16) ✓; momentum + neutral status (Tasks 1,4) ✓; new category + hub + pages (Task 8,17) ✓; daily workflow (Task 9) ✓; multi-source build reuse (Tasks 5,7,15,16) ✓; testing throughout ✓; empty disclaimer / no advice framing (Task 5, pages) ✓; two-phase build (Phase 1 ships at Task 10) ✓.

**Placeholder scan:** No "TBD"/"handle edge cases"/bare "write tests" — every code step shows complete code and every test step shows real assertions. `<key>` in live-build steps is an intentional secret the engineer supplies.

**Type consistency:** `build_crypto_lens(rotation_obs, dominance_obs, btc_eth_obs)` — call sites in Task 15 test, Task 16 `_build_crypto`, and Task 16 test all pass `(rotation, dominance, btc_eth)` positionally ✓. `crypto_market_structure()` returns `{"rotation", "dominance_point"}` — consumed identically in `_build_crypto` and the fixture ✓. `merge_series(old, new)` signature consistent (Tasks 13, 16) ✓. Status tokens (`up`/`down`/`flat`/`info`/`neutral`) defined in CSS (Task 1), produced by rules (Tasks 3,4,14), asserted in tests ✓. `MARKET_FRED_LENSES` used in config/refresh/tests consistently ✓.

# Corporate & Business Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the 8th dashboard category — Corporate & Business Health — four pure-FRED lenses (profitability, formation, investment, credit) with pages, hub, home tile, brief wiring, workflow step, tests, and a live data build.

**Architecture:** Reuses the existing Lens/Indicator pipeline unchanged: new lenses in `config.py`, new narrative rules in `narrative.py`, a `refresh_business()` in `refresh_lenses.py` that injects two cross-series shares (profits÷GDP, high-propensity÷total applications) via `util.pct_share` after the FRED pass — mirroring `_inject_generation_shares` / `_btc_eth_ratio`. GDP is fetched solely as a share denominator and gets no chart. Static pages copy the consumer category's structure.

**Tech Stack:** Standard-library Python only; hand-written HTML; existing `unittest` suite; FRED keyed API.

---

## Band calibration (live-verified 2026-06-10 against full-history percentiles)

All spec first-pass bands were checked against full series history; 2008-09 and 2020 land in elevated/alert and today lands sensibly. Final bands:

| Series | Bands (status thresholds) | 2008-09 | 2020 | Today |
|---|---|---|---|---|
| CP yoy (lead) | ≥0 ok / <0 watch / ≤−5 elevated / ≤−15 alert | min −46 → alert | min −9.8 → elevated | +17.4 → ok |
| BABATOTALSAUS yoy (lead) | ≥0 ok / <0 watch / ≤−5 elevated / ≤−15 alert | min −23.8 → alert | min −19.6 → alert | +17.0 → ok |
| NEWORDER yoy (lead) | ≥0 ok / <0 watch / ≤−3 elevated / ≤−10 alert | min −32.1 → alert | min −16.8 → alert | +10.5 → ok |
| CMRMTSPL yoy | ≥0 ok / <0 watch / ≤−2 elevated / ≤−6 alert (chosen: p5=−5.0, 2008 min −13.4, 2020 min −15.6) | alert | alert | +1.6 → ok |
| ISRATIO level | <1.40 ok / 1.40–1.50 watch / ≥1.50 elevated (2008 peak 1.48 → watch; 2020 peak 1.74 → elevated) | watch | elevated | 1.32 → ok |
| BAA10YM level (lead) | <2.0 ok / 2.0–2.5 watch / 2.5–3.5 elevated / ≥3.5 alert | max 6.01 → alert | max 3.47 → elevated | 1.62 → ok |
| DRTSCILM level | ≤0 ok / 0–20 watch / 20–50 elevated / >50 alert | max 83.6 → alert | max 71.2 → alert | 8.1 → watch |
| DRBLACBS level | <1.5 ok / 1.5–2.5 watch / 2.5–4.0 elevated / ≥4.0 alert | max 4.39 → alert | 1.30 → ok | 1.34 → ok |
| BUSLOANS yoy | two-sided hot=(10, 20, 30) cold=(−0.5, −5, −12) (chosen: 2008-09 min −18.1 → alert; 2020 max +30.1 → alert-hot; p5=−7.3 → elevated) | alert | alert (boom) | +7.7 → ok |

Reference latest values for fixtures/tests: CP 3,917.2 ($B SAAR), GDP 31,819.5, CP/GDP share 12.3%, NFCPATAX yoy +17.4, PROPINC yoy +1.7, BABA 523,971/mo, BAHBA 146,555/mo, HP share 28.0%, NEWORDER yoy +10.5, CMRMTSPL yoy +1.6, ISRATIO 1.32, BAA10YM 1.62, DRTSCILM 8.1, DRBLACBS 1.34, BUSLOANS yoy +7.7.

**Deviation from spec:** the "~$3.9T / ~524K level surfaces in the read" wish can't be met with a `derive.yoy_pct` chart (the rule only sees the derived YoY series, and baking a level into rule text would go stale). The scale lives in the evergreen `context` copy instead.

---

### Task 1: Narrative rules + headlines (TDD)

**Files:**
- Modify: `scripts/lenses/narrative.py` (new factory + 4 rules + 4 HEADLINES entries, appended before `HEADLINES`)
- Create: `scripts/tests/test_narrative_business.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/tests/test_narrative_business.py`:

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def _obs(v):
    return [("2026-01-01", v)]


class TestYoyContractionBand(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.yoy_contraction_band("Corporate profits", 0, -5, -15)

    def test_growing_is_ok(self):
        text, status = self.rule(_obs(17.4))
        self.assertEqual(status, "ok")
        self.assertIn("growing 17.4%", text)

    def test_sub_one_percent_is_flat_ok(self):
        text, status = self.rule(_obs(0.4))
        self.assertEqual(status, "ok")
        self.assertIn("roughly flat", text)

    def test_small_decline_is_watch(self):
        text, status = self.rule(_obs(-2.0))
        self.assertEqual(status, "watch")
        self.assertIn("shrinking", text)

    def test_sharp_decline_is_elevated(self):
        text, status = self.rule(_obs(-9.8))
        self.assertEqual(status, "elevated")
        self.assertIn("contracting sharply", text)

    def test_collapse_is_alert(self):
        text, status = self.rule(_obs(-46.0))
        self.assertEqual(status, "alert")
        self.assertIn("severe contraction", text)

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([]), ("Data unavailable.", "unknown"))


class TestBaaSpread(unittest.TestCase):
    def test_bands(self):
        cases = [(1.62, "ok"), (2.2, "watch"), (2.8, "elevated"), (6.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_baa_spread(_obs(v))
            self.assertEqual(status, want, f"spread {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_baa_spread([]), ("Data unavailable.", "unknown"))


class TestLendingStandards(unittest.TestCase):
    def test_bands(self):
        cases = [(-10.0, "ok"), (0.0, "ok"), (8.1, "watch"), (35.0, "elevated"), (83.6, "alert")]
        for v, want in cases:
            _, status = narrative.rule_lending_standards(_obs(v))
            self.assertEqual(status, want, f"net tightening {v}")

    def test_easing_text(self):
        text, _ = narrative.rule_lending_standards(_obs(-10.0))
        self.assertIn("easing", text)

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_lending_standards([]), ("Data unavailable.", "unknown"))


class TestBusinessDelinquency(unittest.TestCase):
    def test_bands(self):
        cases = [(1.34, "ok"), (1.8, "watch"), (3.0, "elevated"), (4.4, "alert")]
        for v, want in cases:
            _, status = narrative.rule_business_delinquency(_obs(v))
            self.assertEqual(status, want, f"rate {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_business_delinquency([]), ("Data unavailable.", "unknown"))


class TestInventoriesSales(unittest.TestCase):
    def test_bands(self):
        cases = [(1.32, "ok"), (1.44, "watch"), (1.55, "elevated")]
        for v, want in cases:
            _, status = narrative.rule_inventories_sales(_obs(v))
            self.assertEqual(status, want, f"ratio {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_inventories_sales([]), ("Data unavailable.", "unknown"))


class TestBusinessHeadlines(unittest.TestCase):
    def test_all_business_lenses_have_full_headline_sets(self):
        for lens_id in ("business-profitability", "business-formation",
                        "business-investment", "business-credit"):
            self.assertIn(lens_id, narrative.HEADLINES)
            for status in ("ok", "watch", "elevated", "alert", "unknown"):
                self.assertTrue(narrative.HEADLINES[lens_id].get(status), f"{lens_id}/{status}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest scripts.tests.test_narrative_business` from the worktree — expect `AttributeError: ... 'yoy_contraction_band'`.

- [ ] **Step 3: Implement in `narrative.py`**

Append after the Housing rules (before `HEADLINES`):

```python
# --- Corporate & Business Health rules ---

def yoy_contraction_band(label, watch, elevated, alert, verb="are"):
    """Factory: one-sided severity for an already-YoY % series where FALLING is
    the stress signal (profits, business applications, capex orders). Thresholds
    are YoY-% values, descending (e.g. 0, -5, -15). Label reads as a plural
    subject ("Corporate profits"); pass verb="is" for singular ones."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v <= alert:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — a severe contraction.", "alert")
        if v <= elevated:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — contracting sharply.", "elevated")
        if v < watch:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — shrinking.", "watch")
        if v >= 1:
            return (f"{label} {verb} growing {v:.1f}% a year.", "ok")
        return (f"{label} {verb} roughly flat versus a year ago ({v:+.1f}%).", "ok")
    return _rule


def rule_baa_spread(obs):
    """BAA10YM: Moody's Baa yield minus the 10-year Treasury, in points.
    <2.0 ok, 2.0-2.5 watch, 2.5-3.5 elevated, >=3.5 alert (2008 ~6, COVID ~3.5)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 3.5:
        return (f"The Baa spread is {v:.2f} points — crisis-grade pricing of corporate credit risk.", "alert")
    if v >= 2.5:
        return (f"The Baa spread is {v:.2f} points — wide, a sign of building credit stress.", "elevated")
    if v >= 2.0:
        return (f"The Baa spread is {v:.2f} points — drifting wider off its lows.", "watch")
    return (f"The Baa spread is {v:.2f} points — corporate credit is priced calm.", "ok")


def rule_lending_standards(obs):
    """DRTSCILM: net % of banks tightening C&I standards (SLOOS).
    <=0 ok, 0-20 watch, 20-50 elevated, >50 alert (2008 ~84, COVID ~71)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v > 50:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — a credit crunch.", "alert")
    if v >= 20:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — broad tightening, a classic late-cycle signal.", "elevated")
    if v > 0:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — mild tightening.", "watch")
    if v < 0:
        return (f"A net {abs(v):.0f}% of banks are easing business-loan standards — credit is getting easier.", "ok")
    return ("Banks are neither tightening nor easing business-loan standards on balance.", "ok")


def rule_business_delinquency(obs):
    """DRBLACBS: % of bank business loans past due.
    <1.5 ok, 1.5-2.5 watch, 2.5-4.0 elevated, >=4.0 alert (2009 peak ~4.4)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 4.0:
        return (f"Business-loan delinquencies are at {v:.2f}% — crisis-level borrower distress.", "alert")
    if v >= 2.5:
        return (f"Business-loan delinquencies have climbed to {v:.2f}% — real borrower stress.", "elevated")
    if v >= 1.5:
        return (f"Business-loan delinquencies are at {v:.2f}%, creeping up off their lows.", "watch")
    return (f"Just {v:.2f}% of business loans are delinquent — borrowers are keeping up.", "ok")


def rule_inventories_sales(obs):
    """ISRATIO: total-business inventories-to-sales ratio (months of sales).
    <1.40 ok, 1.40-1.50 watch, >=1.50 elevated (2008 peaked ~1.48, COVID ~1.74)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 1.50:
        return (f"Inventories equal {v:.2f} months of sales — an overhang that typically forces production cuts.", "elevated")
    if v >= 1.40:
        return (f"Inventories equal {v:.2f} months of sales — stocks are building up.", "watch")
    return (f"Inventories equal {v:.2f} months of sales — lean and healthy.", "ok")
```

And inside `HEADLINES` (after the housing entries):

```python
    "business-profitability": {
        "alert": "Corporate profits are collapsing.",
        "elevated": "Corporate profits are contracting — earnings are under real pressure.",
        "watch": "Corporate profit growth is stalling.",
        "ok": "Corporate America is profitable — earnings are growing.",
        "unknown": "Some profit data is temporarily unavailable.",
    },
    "business-formation": {
        "alert": "Business formation has collapsed.",
        "elevated": "Business formation is contracting — fewer new firms are being started.",
        "watch": "Business formation is losing steam.",
        "ok": "New businesses are forming at a healthy clip.",
        "unknown": "Some formation data is temporarily unavailable.",
    },
    "business-investment": {
        "alert": "Business investment is collapsing — capex and sales are contracting hard.",
        "elevated": "Business investment is contracting.",
        "watch": "Business investment is wobbling — orders or sales are slipping.",
        "ok": "Businesses are investing — orders and sales are growing.",
        "unknown": "Some investment data is temporarily unavailable.",
    },
    "business-credit": {
        "alert": "Business credit is in crisis — lending is seizing up.",
        "elevated": "Business credit is tightening — stress is building.",
        "watch": "Business credit bears watching — conditions are tightening at the margin.",
        "ok": "Business credit is flowing — spreads and delinquencies are low.",
        "unknown": "Some business-credit data is temporarily unavailable.",
    },
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m unittest scripts.tests.test_narrative_business` — expect OK.

- [ ] **Step 5: Commit**

```bash
git -C <worktree> add scripts/lenses/narrative.py scripts/tests/test_narrative_business.py
git -C <worktree> commit -m "feat(business): narrative rules + headlines for Corporate & Business Health"
```

### Task 2: Lens config + category registration (TDD)

**Files:**
- Modify: `scripts/lenses/config.py` (append after the Housing block; also note `"computed"` in `Indicator.source` comment)
- Create: `scripts/tests/test_config_business.py`

- [ ] **Step 1: Write the failing tests**

```python
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative


class TestBusinessConfig(unittest.TestCase):
    def test_four_lenses(self):
        ids = [l.id for l in config.BUSINESS_LENSES]
        self.assertEqual(ids, ["business-profitability", "business-formation",
                               "business-investment", "business-credit"])

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "business")
        self.assertEqual(cat["out"], "business")
        self.assertEqual(cat["title"], "Corporate & Business Health")
        self.assertEqual(len(cat["lenses"]), 4)

    def test_every_indicator_has_rule_context_and_headline(self):
        for lens in config.BUSINESS_LENSES:
            self.assertIn(lens.id, narrative.HEADLINES)
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)

    def test_lead_indicators_first(self):
        leads = {l.id: l.indicators[0].id for l in config.BUSINESS_LENSES}
        self.assertEqual(leads, {
            "business-profitability": "profit-growth",
            "business-formation": "applications",
            "business-investment": "core-capex",
            "business-credit": "baa-spread",
        })

    def test_computed_shares_are_not_fred_fetched(self):
        import refresh_lenses
        specs = refresh_lenses.unique_specs(config.BUSINESS_LENSES)
        self.assertNotIn("CP_GDP_SHARE:lin", specs)
        self.assertNotIn("BFS_HP_SHARE:lin", specs)
        self.assertIn("CP:lin", specs)
        self.assertNotIn("GDP:lin", specs)  # GDP is share input only, no chart


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure** (`AttributeError: BUSINESS_LENSES`)

- [ ] **Step 3: Implement in `config.py`** — append after the housing `CATEGORIES.append`:

```python
# --- Corporate & Business Health (FRED) ---
# The "strategic" leg: are profits growing, are new firms forming, is capex
# expanding, is credit tightening? Pure FRED. Two cross-series shares
# (profits/GDP, high-propensity/total applications) are computed at refresh
# time via util.pct_share and injected under source="computed" fetch keys;
# GDP is fetched solely as a share denominator and gets no chart of its own.

BUSINESS_PROFITABILITY = Lens(
    id="business-profitability", title="Profitability", accent="#34D399",
    indicators=[
        Indicator(
            id="profit-growth", title="Corporate Profits · year-over-year",
            short="Profit growth", unit="%", color="#34D399",
            series_id="CP", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Corporate profits", 0, -5, -15),
            context=("How fast after-tax corporate profits are growing versus a year ago "
                     "(quarterly, all U.S. corporations — about $3.9 trillion a year). "
                     "Falling profits are how downturns reach hiring and investment."),
        ),
        Indicator(
            id="nonfinancial-profits", title="Nonfinancial Corporate Profits · year-over-year",
            short="Nonfin. profits", unit="%", color="#38BDF8",
            series_id="NFCPATAX", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_info("Nonfinancial corporate profit"),
            context=("The same after-tax profit growth for nonfinancial corporations only — "
                     "the 'Main Street corporates' read, with banks stripped out."),
        ),
        Indicator(
            id="profit-share", title="Corporate Profits · share of GDP",
            short="Profit share", unit="%", color="#A78BFA",
            series_id="CP_GDP_SHARE", limit=104, source="computed",
            rule=narrative.level_points("The corporate-profit share of GDP"),
            context=("After-tax corporate profits as a share of GDP — the closest public "
                     "proxy for economy-wide profit margins. The post-war norm is 5-7%; "
                     "the 2020s have run near record highs above 11%."),
        ),
        Indicator(
            id="proprietors-income", title="Proprietors' Income · year-over-year",
            short="Proprietors", unit="%", color="#FBBF24",
            series_id="PROPINC", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_info("Proprietors' income"),
            context=("Income of unincorporated businesses — sole proprietors and "
                     "partnerships. The closest thing to a small-business earnings line."),
        ),
    ],
)

BUSINESS_FORMATION = Lens(
    id="business-formation", title="Business Formation", accent="#38BDF8",
    indicators=[
        Indicator(
            id="applications", title="Business Applications · year-over-year",
            short="Applications", unit="%", color="#38BDF8",
            series_id="BABATOTALSAUS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Business applications", 0, -5, -15),
            context=("How fast new business applications are growing versus a year ago "
                     "(Census Business Formation Statistics — roughly half a million "
                     "applications a month). Falling applications mean fading dynamism."),
        ),
        Indicator(
            id="high-propensity", title="High-Propensity Applications · year-over-year",
            short="High-propensity", unit="%", color="#A78BFA",
            series_id="BAHBATOTALSAUS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_info("High-propensity application volume"),
            context=("Growth in applications with characteristics that make them likely to "
                     "become employer businesses — the quality signal inside the headline count."),
        ),
        Indicator(
            id="hp-share", title="High-Propensity Share of Applications",
            short="HP share", unit="%", color="#FBBF24",
            series_id="BFS_HP_SHARE", limit=300, source="computed",
            rule=narrative.level_points("The high-propensity share of applications"),
            context=("What fraction of all business applications look likely to become "
                     "employers — formation quality over time. It ran near half before "
                     "the pandemic-era boom in solo ventures pushed it below a third."),
        ),
    ],
)

BUSINESS_INVESTMENT = Lens(
    id="business-investment", title="Investment & Activity", accent="#FBBF24",
    indicators=[
        Indicator(
            id="core-capex", title="Core Capital-Goods Orders · year-over-year",
            short="Core capex", unit="%", color="#FBBF24",
            series_id="NEWORDER", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Core capital-goods orders", 0, -3, -10),
            context=("Orders for nondefense capital goods excluding aircraft — the cleanest "
                     "monthly read on whether businesses are investing in equipment. "
                     "(Headline durable goods is skipped here: aircraft orders make it noise.)"),
        ),
        Indicator(
            id="real-sales", title="Real Business Sales · year-over-year",
            short="Real sales", unit="%", color="#34D399",
            series_id="CMRMTSPL", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Real business sales", 0, -2, -6),
            context=("Real manufacturing and trade sales — total business volume adjusted "
                     "for inflation, one of the inputs NBER uses to date recessions."),
        ),
        Indicator(
            id="inventories-sales", title="Inventories-to-Sales Ratio",
            short="Inv./sales", unit="", color="#38BDF8",
            series_id="ISRATIO", limit=240,
            rule=narrative.rule_inventories_sales,
            context=("Total business inventories measured against a month of sales. Rising "
                     "means goods are piling up unsold — the overhang that precedes "
                     "production cuts. The COVID spike hit 1.74; 2008 peaked near 1.48."),
        ),
    ],
)

BUSINESS_CREDIT = Lens(
    id="business-credit", title="Credit & Stress", accent="#F87171",
    indicators=[
        Indicator(
            id="baa-spread", title="Baa Corporate Spread · over 10-Year Treasury",
            short="Baa spread", unit="%", color="#F87171",
            series_id="BAA10YM", limit=240,
            rule=narrative.rule_baa_spread,
            context=("The extra yield investors demand to hold Moody's Baa-rated corporate "
                     "bonds over 10-year Treasuries — the price of ordinary corporate credit "
                     "risk, with history back to 1953. 2008 peaked near 6 points. (A different "
                     "index family from the ICE BofA spreads on the Markets risk lens.)"),
        ),
        Indicator(
            id="lending-standards", title="Lending Standards · net % of banks tightening",
            short="Standards", unit="%", color="#FBBF24",
            series_id="DRTSCILM", limit=80,
            rule=narrative.rule_lending_standards,
            context=("From the Fed's quarterly loan-officer survey: the share of banks "
                     "tightening standards on commercial & industrial loans minus the share "
                     "easing. Sustained tightening above ~20% has preceded every modern recession."),
        ),
        Indicator(
            id="delinquency", title="Business-Loan Delinquency Rate",
            short="Delinquency", unit="%", color="#FB923C",
            series_id="DRBLACBS", limit=80,
            rule=narrative.rule_business_delinquency,
            context=("The share of commercial & industrial loans at banks that are past due "
                     "(quarterly) — where business credit stress stops being a forecast and "
                     "shows up as missed payments. The 2009 peak was about 4.4%."),
        ),
        Indicator(
            id="ci-loan-growth", title="C&I Loan Growth · year-over-year",
            short="C&I loans", unit="%", color="#A78BFA",
            series_id="BUSLOANS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_band_two_sided("C&I lending", hot=(10, 20, 30),
                                              cold=(-0.5, -5, -12), verb="is"),
            context=("How fast bank lending to businesses is growing. Outright contraction "
                     "is a credit squeeze; double-digit booms (2020 hit +30%) have their own "
                     "way of ending badly."),
        ),
    ],
)

BUSINESS_LENSES = [BUSINESS_PROFITABILITY, BUSINESS_FORMATION,
                   BUSINESS_INVESTMENT, BUSINESS_CREDIT]

CATEGORIES.append(
    {"id": "business", "title": "Corporate & Business Health", "lenses": BUSINESS_LENSES,
     "out": "business", "back": "Corporate & Business Health",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed", "disclaimer": ""}
)
```

Also update the `Indicator.source` field comment to `"fred" | "yahoo" | "eia" | "computed"`.

- [ ] **Step 4: Run to verify pass** — `python -m unittest scripts.tests.test_config_business`

- [ ] **Step 5: Commit** — `feat(business): four Corporate & Business Health lenses in config`

### Task 3: Fixture + refresh_business with share injection (TDD)

**Files:**
- Create: `scripts/tests/fixtures/business_sample.json`
- Modify: `scripts/refresh_lenses.py`
- Create: `scripts/tests/test_refresh_business.py`

- [ ] **Step 1: Create the fixture** — values mirror live 2026-06-10 readings; three yearly-spaced points per derived series so `yoy_pct` yields two points (hub delta arrows). Includes `GDP:lin` (the dry-run share denominator).

```json
{
  "CP:lin": [
    {"date": "2024-01-01", "value": "3100.0"},
    {"date": "2025-01-01", "value": "3335.7"},
    {"date": "2026-01-01", "value": "3917.2"}
  ],
  "NFCPATAX:lin": [
    {"date": "2024-01-01", "value": "2000.0"},
    {"date": "2025-01-01", "value": "2151.4"},
    {"date": "2026-01-01", "value": "2526.6"}
  ],
  "GDP:lin": [
    {"date": "2024-01-01", "value": "28600.0"},
    {"date": "2025-01-01", "value": "30100.0"},
    {"date": "2026-01-01", "value": "31819.5"}
  ],
  "PROPINC:lin": [
    {"date": "2024-01-01", "value": "2050.0"},
    {"date": "2025-01-01", "value": "2103.2"},
    {"date": "2026-01-01", "value": "2138.2"}
  ],
  "BABATOTALSAUS:lin": [
    {"date": "2024-05-01", "value": "430000"},
    {"date": "2025-05-01", "value": "447700"},
    {"date": "2026-05-01", "value": "523971"}
  ],
  "BAHBATOTALSAUS:lin": [
    {"date": "2024-05-01", "value": "139000"},
    {"date": "2025-05-01", "value": "141325"},
    {"date": "2026-05-01", "value": "146555"}
  ],
  "NEWORDER:lin": [
    {"date": "2024-04-01", "value": "73000"},
    {"date": "2025-04-01", "value": "74628"},
    {"date": "2026-04-01", "value": "82487"}
  ],
  "CMRMTSPL:lin": [
    {"date": "2024-03-01", "value": "1540000"},
    {"date": "2025-03-01", "value": "1563500"},
    {"date": "2026-03-01", "value": "1587949"}
  ],
  "ISRATIO:lin": [
    {"date": "2026-02-01", "value": "1.33"},
    {"date": "2026-03-01", "value": "1.32"}
  ],
  "BAA10YM:lin": [
    {"date": "2026-04-01", "value": "1.65"},
    {"date": "2026-05-01", "value": "1.62"}
  ],
  "DRTSCILM:lin": [
    {"date": "2026-01-01", "value": "6.2"},
    {"date": "2026-04-01", "value": "8.1"}
  ],
  "DRBLACBS:lin": [
    {"date": "2025-10-01", "value": "1.31"},
    {"date": "2026-01-01", "value": "1.34"}
  ],
  "BUSLOANS:lin": [
    {"date": "2024-04-01", "value": "2520.0"},
    {"date": "2025-04-01", "value": "2669.0"},
    {"date": "2026-04-01", "value": "2874.0"}
  ]
}
```

- [ ] **Step 2: Write the failing tests** — `scripts/tests/test_refresh_business.py`:

```python
import json
import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBusinessDryRun(unittest.TestCase):
    def _run(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.BUSINESS_OUT_DIR
            refresh_lenses.BUSINESS_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--business", "--dry-run"])
                files = {p.name: json.loads(p.read_text(encoding="utf-8"))
                         for p in tmp.glob("*.json")}
            finally:
                refresh_lenses.BUSINESS_OUT_DIR = orig
            return rc, files

    def test_business_flag_runs_dry_into_tempdir(self):
        rc, files = self._run()
        self.assertEqual(rc, 0)
        for name in ("business-profitability.json", "business-formation.json",
                     "business-investment.json", "business-credit.json", "index.json"):
            self.assertIn(name, files)

    def test_profit_share_injected_from_cp_and_gdp(self):
        _, files = self._run()
        prof = files["business-profitability.json"]
        share = next(i for i in prof["indicators"] if i["id"] == "profit-share")
        self.assertEqual(share["latest"]["value"], "12.3")  # 3917.2/31819.5*100
        self.assertEqual(share["signal_status"], "info")

    def test_hp_share_injected_from_bahba_and_baba(self):
        _, files = self._run()
        form = files["business-formation.json"]
        share = next(i for i in form["indicators"] if i["id"] == "hp-share")
        self.assertEqual(share["latest"]["value"], "28.0")  # 146555/523971*100

    def test_statuses_match_calibration(self):
        _, files = self._run()
        self.assertEqual(files["business-profitability.json"]["status"], "ok")
        self.assertEqual(files["business-credit.json"]["status"], "watch")  # SLOOS 8.1


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Implement in `refresh_lenses.py`**

Module constants (next to the others):

```python
BUSINESS_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "business"
BUSINESS_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "business_sample.json"
```

Add `"business": BUSINESS_OUT_DIR` to `_brief_index_dirs()`.

Helpers + refresh function (after `refresh_consumer`):

```python
def _prior_business_obs(lens_id, ind_id):
    """Prior observations for one business indicator from its existing lens JSON
    (fallback when a share input is unavailable)."""
    path = BUSINESS_OUT_DIR / f"{lens_id}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ind in data.get("indicators", []):
                if ind.get("id") == ind_id:
                    return ind.get("observations", [])
        except (ValueError, OSError):
            pass
    return []


def _inject_business_shares(fetched, api_key):
    """Compute the two cross-series shares and inject them under their computed
    fetch keys (mirrors the electricity generation-share pattern). The high-
    propensity share needs no extra network call; the profit share needs GDP,
    fetched here solely as the denominator (dry-run fixtures carry GDP:lin).
    Additive: a missing input falls back to prior published data."""
    hp = util.pct_share(fetched.get("BAHBATOTALSAUS:lin"), fetched.get("BABATOTALSAUS:lin"))
    fetched["BFS_HP_SHARE:lin"] = hp or _prior_business_obs("business-formation", "hp-share")
    gdp = fetched.get("GDP:lin")
    if gdp is None and api_key:
        try:
            gdp = fred.fetch_observations("GDP", api_key, 104)
        except Exception as exc:  # noqa: BLE001 - keep prior on failure
            print(f"WARN: GDP fetch failed ({exc}); keeping previous profit share", file=sys.stderr)
    share = util.pct_share(fetched.get("CP:lin"), gdp) if gdp else []
    fetched["CP_GDP_SHARE:lin"] = share or _prior_business_obs("business-profitability", "profit-share")


def refresh_business(dry_run):
    """Build + write the business (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    api_key = None
    if dry_run:
        fetched = json.loads(BUSINESS_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.BUSINESS_LENSES, api_key)

    _inject_business_shares(fetched, api_key)

    ready = [lens for lens in config.BUSINESS_LENSES if lens_ready(lens, failed)]
    for lens in config.BUSINESS_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No business lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  BUSINESS_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all business data up to date.")
    return 0
```

`fred` is already imported. Wire the flag in `main()`: add `parser.add_argument("--business", ...)`, include it in `any_flag`, `do_business = args.business or not any_flag`, and run it after `do_consumer` (before banking/brief) accumulating the exit code like housing/consumer.

- [ ] **Step 4: Run to verify pass** — `python -m unittest scripts.tests.test_refresh_business` and `python scripts/refresh_lenses.py --dry-run --business` (then `git checkout -- data/` if it wrote into data/business — the test uses a tempdir, the manual run writes for real).

- [ ] **Step 5: Commit** — `feat(business): refresh pipeline with cross-series share injection + dry-run fixture`

### Task 4: Today's Brief wiring (TDD)

**Files:**
- Modify: `scripts/lenses/brief.py` (slug map, `lens_href` branch, `CATEGORIES`)
- Modify: `scripts/tests/test_brief.py` (add a business href test)

- [ ] **Step 1: Failing test** — append to `test_brief.py`:

```python
class TestBusinessHref(unittest.TestCase):
    def test_business_lens_hrefs(self):
        self.assertEqual(brief.lens_href("business", "business-profitability"),
                         "/dashboards/business/profitability.html")
        self.assertEqual(brief.lens_href("business", "business-credit"),
                         "/dashboards/business/credit.html")
        self.assertIn("business", brief.CATEGORIES)
```

- [ ] **Step 2: Implement** — in `brief.py` add:

```python
_BUSINESS_SLUGS = {
    "business-profitability": "profitability",
    "business-formation": "formation",
    "business-investment": "investment",
    "business-credit": "credit",
}
```

a branch in `lens_href`:

```python
    if category == "business":
        return f"/dashboards/business/{_BUSINESS_SLUGS.get(lens_id, lens_id)}.html"
```

and `CATEGORIES = ["economic", "consumer", "banking", "business", "markets", "energy", "housing"]`.

- [ ] **Step 3: Run** — `python -m unittest scripts.tests.test_brief` → OK.

- [ ] **Step 4: Commit** — `feat(business): Today's Brief category wiring`

### Task 5: Pages — 4 lens pages, category hub, dashboards index, home tile

**Files:**
- Create: `dashboards/business/profitability.html`, `formation.html`, `investment.html`, `credit.html`, `index.html`
- Modify: `dashboards/index.html` (new category section + slug map; mention business in meta description)
- Modify: `index.html` (one `CATEGORIES` line)

- [ ] **Step 1: Lens pages.** Copy the consumer page skeleton. Per page substitute title/description/og/url/json/defaultRange. `profitability.html` (quarterly lead → `defaultRange: "5Y"`, the banking precedent):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Profitability — Bailey Analytics</title>
  <meta name="description" content="Is corporate America making money? Corporate profit growth, nonfinancial profits, the profit share of GDP, and proprietors' income, from FRED.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Profitability — Bailey Analytics">
  <meta property="og:description" content="Is corporate America making money? Corporate profit growth, nonfinancial profits, the profit share of GDP, and proprietors' income, from FRED.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/business/profitability.html">
  <meta name="twitter:card" content="summary">
  <script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading…</div></main>
  <script defer src="/dashboards/lens.js"></script>
  <script>document.addEventListener("DOMContentLoaded", () => {
    renderLens("/data/business/business-profitability.json", {
      back: "Corporate & Business Health",
      href: "/dashboards/business/",
      defaultRange: "5Y",
      foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.'
    });
  });</script>
</body>
</html>
```

The other three drop `defaultRange` and substitute:
- `formation.html`: title "Business Formation", json `business-formation.json`, description "Are new businesses being started? Business applications, high-propensity applications, and the high-propensity share, from Census data on FRED."
- `investment.html`: title "Investment & Activity", json `business-investment.json`, description "Are businesses investing? Core capital-goods orders, real business sales, and the inventories-to-sales ratio, from FRED."
- `credit.html`: title "Business Credit & Stress", json `business-credit.json`, description "Is business credit tightening? The Baa corporate spread, bank lending standards, business-loan delinquencies, and C&I loan growth, from FRED." Its `foot` adds a cross-pointer: `... by a fixed rule set. Market-priced credit spreads (ICE BofA high-yield and investment-grade) live on the <a href="/dashboards/markets/risk-sentiment.html">Risk Sentiment</a> lens.`

- [ ] **Step 2: Category hub** `dashboards/business/index.html` (consumer hub pattern):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Corporate &amp; Business Health — Bailey Analytics</title>
  <meta name="description" content="Corporate America in plain English — profitability, business formation, investment, and business credit. Built from FRED data.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Corporate &amp; Business Health — Bailey Analytics">
  <meta property="og:description" content="Corporate America in plain English — profitability, business formation, investment, and business credit. Built from FRED data.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/business/">
  <meta name="twitter:card" content="summary">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>

  <main>
    <a class="back" href="/dashboards/">&larr; Dashboards</a>
    <h1>Corporate &amp; Business Health</h1>
    <p class="lede">The business side of the economy — whether corporate America is making money, whether new businesses are being started, whether firms are investing, and whether the credit behind all of it is flowing or tightening. <strong>Open any lens</strong> for interactive charts and the context behind each number.</p>
    <div class="hub-grid" id="hub-grid"><div class="status-msg">Loading&hellip;</div></div>
    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a>, St. Louis Fed. Public data, refreshed daily.
    </div>
  </main>

  <script defer src="/dashboards/hub.js"></script>
  <script>document.addEventListener("DOMContentLoaded", () => {
    loadHubGrid("hub-grid", "/data/business/index.json",
      id => {
        const SLUGS = { "business-profitability": "profitability", "business-formation": "formation",
                        "business-investment": "investment", "business-credit": "credit" };
        return `/dashboards/business/${encodeURIComponent(SLUGS[id] || id)}.html`;
      });
  });</script>
</body>
</html>
```

- [ ] **Step 3: `dashboards/index.html`** — add after the Banking section (and mention business in the two meta descriptions):

```html
    <h2 class="cat-head"><span class="dot" style="background:#34D399"></span>Corporate &amp; Business Health</h2>
    <p class="cat-sub">The business side of the economy — profits, new-business formation, investment, and business credit. Refreshed daily from FRED. <a href="/dashboards/business/" style="color:var(--blue);text-decoration:none">Overview &rarr;</a></p>
    <div class="hub-grid" id="business-grid"><div class="status-msg">Loading&hellip;</div></div>
```

and in the script block:

```js
    const BUSINESS_SLUGS = {
      "business-profitability": "profitability",
      "business-formation": "formation",
      "business-investment": "investment",
      "business-credit": "credit"
    };
    loadHubGrid("business-grid", "/data/business/index.json",
                id => `/dashboards/business/${encodeURIComponent(BUSINESS_SLUGS[id] || id)}.html`);
```

- [ ] **Step 4: Home `index.html`** — one line in `CATEGORIES` after Banking:

```js
            { title: "Business", url: "/data/business/index.json", href: "/dashboards/business/" },
```

- [ ] **Step 5: Smoke-check** — serve locally (`python -m http.server 8000` from the worktree) and load `/dashboards/business/` + one lens page against the dry-run/live JSON; verify charts, badges, and hub tiles render.

- [ ] **Step 6: Commit** — `feat(business): lens pages, category hub, dashboards section, home tile`

### Task 6: Workflow step

**Files:**
- Modify: `.github/workflows/refresh-fred.yml`

- [ ] **Step 1:** Insert after the consumer step, before the brief step:

```yaml
      - name: Fetch latest business data (FRED)
        if: ${{ success() || failure() }}
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
        run: python scripts/refresh_lenses.py --business
```

- [ ] **Step 2: Commit** — `feat(business): daily workflow step`

### Task 7: Full suite + live build + final commit

- [ ] **Step 1:** `python -m unittest discover -s "<worktree>/scripts/tests" -p "test_*.py"` — all green.
- [ ] **Step 2:** Live scoped build: `python scripts/refresh_lenses.py --business` with `FRED_API_KEY` from the environment. Verify `data/business/*.json` (5 files), spot-check latest values and statuses against the calibration table. `git checkout --` anything outside `data/business/` if touched (it shouldn't be — the flag scopes the run).
- [ ] **Step 3:** Commit `data/business/` — `feat(business): first live data build`.

## Self-review notes

- Spec coverage: 4 lenses ✓, shares via pct_share injection ✓ (GDP no chart ✓), `--business` flag ✓, workflow ✓, brief map ✓, home tile ✓, hub + 4 pages ✓ (profitability 5Y ✓), bands calibrated ✓, tests + fixture ✓, footer cross-pointer to Markets credit spreads ✓ (one-way, on the business page).
- No new units: everything is `%` or a bare ratio — `_fmt`/`fmtVal` untouched.
- Deviations: level-in-read (see calibration section); CMRMTSPL + BUSLOANS bands chosen here (spec left them open); DRBLACBS gets a dedicated rule rather than reusing `consumer_delinquency` (its alert text says "consumer distress").

# Banking System Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Banking System Health dashboard category (four themed lenses) sourced from the FDIC BankFind API, reusing the existing lens framework and adding tier-table + ranked-spotlight components.

**Architecture:** Separate ingestion (pluggable per-source fetchers) from presentation (lens format + new table components). FDIC system-wide metrics become ordinary time-series indicators; size-tier and per-bank views are two new presentation blocks. The FRED path is untouched.

**Tech Stack:** Python 3.12 stdlib only (`urllib`, `unittest`); vanilla HTML/CSS/JS; Chart.js via CDN. No build step, no third-party deps.

**Source of truth for design:** `docs/superpowers/specs/2026-06-07-banking-system-health-dashboard-design.md`

**Test command (all):** `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -t "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts"`

---

## File Structure

**Ingestion**
- Create `scripts/lenses/fdic.py` — only banking module that touches the network. National time-series, tier aggregates, rankings.
- Modify `scripts/refresh_lenses.py` — source dispatch + build/write banking outputs.

**Config / build / narrative**
- Modify `scripts/lenses/config.py` — `Metric` spec, banking `Indicator` source field, `BANKING_LENSES`, tier/ranking specs.
- Modify `scripts/lenses/build.py` — build banking lens JSON (indicators + `tiers` + `rankings`), category-aware index.
- Modify `scripts/lenses/narrative.py` — banking status rules + headlines.

**Presentation**
- Modify `dashboards/lens.js` — category-agnostic renderer; render `tiers`/`rankings` when present.
- Modify `dashboards/lens.css` — table component styles.
- Create `dashboards/banking/index.html`, `asset-quality.html`, `profitability.html`, `capital-solvency.html`, `concentrations-funding.html`.
- Modify `dashboards/index.html` — show two categories.

**Data output** (generated, not hand-written): `data/banking/*.json`.

**Tests / fixtures**
- Create `scripts/tests/test_fdic.py`, `scripts/tests/test_narrative_banking.py`, `scripts/tests/fixtures/fdic_*.json`.

---

## Data shapes (locked — used across tasks)

National series fetcher returns FRED-style observations so `build`/`util` are reused unchanged:
```python
# [{"date": "2024-12-31", "value": "0.91"}, ...]   value is a numeric string
```

A banking metric is declared by the dollar fields to sum (ratios are sum-then-divide, never averaged):
```python
# config.Metric
Metric(numerator=["NALNLS"], denominator=["LNLSNET"], scale=100.0)   # -> percent
Metric(numerator=["ELNATR"], denominator=[], scale=1.0)              # -> level ($000s)
```

Lens JSON adds two optional arrays (economic lenses omit them; renderer guards on presence):
```jsonc
"tiers": {
  "label": "Across the system — by bank size",
  "subtitle": "...",
  "columns": [{"key":"noncurrent","label":"Noncurrent"}, ...],
  "rows": [{"tier":"Community (<$10B)","values":[{"value":"1.10%","status":"watch"}, ...]}, ...]
},
"rankings": [
  {"title":"Highest CRE delinquency","subtitle":"banks over $1B · Q4 2024",
   "value_label":"CRE delinq.",
   "rows":[{"name":"...","location":"Denver, CO","asset":"$3.2B","value":"6.40%","status":"alert"}, ...]}
]
```

---

## Task 1: FDIC national time-series fetcher

**Files:**
- Create: `scripts/lenses/fdic.py`
- Test: `scripts/tests/test_fdic.py`

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/test_fdic.py
import sys, pathlib, io, json, unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import fdic


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def _summary_payload(rows):
    return json.dumps({"data": [{"data": r} for r in rows]}).encode()


class TestNationalSeries(unittest.TestCase):
    def test_sums_states_then_divides_for_ratio(self):
        # Two states in one quarter; national noncurrent rate = sum(NALNLS)/sum(LNLSNET)*100
        rows = [
            {"REPDTE": "2024-12-31T00:00:00", "NALNLS": 100, "LNLSNET": 10000},
            {"REPDTE": "2024-12-31T00:00:00", "NALNLS": 50,  "LNLSNET": 5000},
        ]
        fake = FakeResponse(_summary_payload(rows))
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake) as m:
            obs = fdic.national_series(["NALNLS"], ["LNLSNET"], scale=100.0,
                                       start="20240101", end="20241231")
        # (100+50)/(10000+5000)*100 = 1.0
        self.assertEqual(obs, [{"date": "2024-12-31", "value": "1.0000"}])
        url = m.call_args[0][0]
        self.assertIn("api.fdic.gov/banks/summary", url)

    def test_level_metric_has_empty_denominator(self):
        rows = [{"REPDTE": "2024-12-31T00:00:00", "ELNATR": 300},
                {"REPDTE": "2024-12-31T00:00:00", "ELNATR": 200}]
        fake = FakeResponse(_summary_payload(rows))
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            obs = fdic.national_series(["ELNATR"], [], scale=1.0, start="20240101", end="20241231")
        self.assertEqual(obs, [{"date": "2024-12-31", "value": "500.0000"}])

    def test_orders_quarters_chronologically(self):
        rows = [
            {"REPDTE": "2024-12-31T00:00:00", "NALNLS": 10, "LNLSNET": 1000},
            {"REPDTE": "2024-03-31T00:00:00", "NALNLS": 10, "LNLSNET": 1000},
        ]
        fake = FakeResponse(_summary_payload(rows))
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            obs = fdic.national_series(["NALNLS"], ["LNLSNET"], scale=100.0,
                                       start="20240101", end="20241231")
        self.assertEqual([o["date"] for o in obs], ["2024-03-31", "2024-12-31"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest scripts.tests.test_fdic -v` (from `scripts/` parent on sys.path) — or the discover command above.
Expected: FAIL — `ModuleNotFoundError: No module named 'lenses.fdic'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/lenses/fdic.py
"""FDIC BankFind API access — the only banking module that touches the network.

National series are computed sum-then-divide across the per-state summary rows
(never by averaging per-entity ratios). Returns FRED-style [{date, value}] so the
rest of the pipeline is reused unchanged.
"""

import json
import urllib.parse
import urllib.request

SUMMARY_BASE = "https://api.fdic.gov/banks/summary"
FINANCIALS_BASE = "https://api.fdic.gov/banks/financials"


def _get(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def _rows(payload):
    return [r.get("data", r) for r in payload.get("data", [])]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def national_series(numerator, denominator, scale, start, end, timeout=25):
    """National quarterly series from the summary endpoint.

    numerator/denominator are lists of dollar field codes summed across states.
    For a ratio, value = scale * sum(numerator) / sum(denominator).
    For a level (denominator == []), value = scale * sum(numerator).
    """
    fields = ",".join(["REPDTE"] + numerator + denominator)
    params = {
        "filters": f"REPDTE:[{start} TO {end}]",
        "fields": fields,
        "limit": 20000,
        "format": "json",
    }
    url = f"{SUMMARY_BASE}?{urllib.parse.urlencode(params)}"
    payload = _get(url, timeout)
    by_quarter = {}
    for row in _rows(payload):
        rep = str(row.get("REPDTE", ""))[:10]
        if not rep:
            continue
        num, den = by_quarter.setdefault(rep, [0.0, 0.0])
        num += sum(_num(row.get(f)) for f in numerator)
        den += sum(_num(row.get(f)) for f in denominator)
        by_quarter[rep] = [num, den]
    obs = []
    for rep in sorted(by_quarter):
        num, den = by_quarter[rep]
        if denominator:
            value = scale * num / den if den else None
        else:
            value = scale * num
        if value is not None:
            obs.append({"date": rep, "value": f"{value:.4f}"})
    return obs
```

- [ ] **Step 4: Run test to verify it passes**

Run: discover command above.
Expected: PASS (3 tests in `test_fdic`).

- [ ] **Step 5: Commit** *(do not run until the user authorizes commits; see "Commit policy" note at end)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/fdic.py scripts/tests/test_fdic.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): FDIC national time-series fetcher"
```

---

## Task 2: FDIC ranking fetcher (bank spotlight)

**Files:**
- Modify: `scripts/lenses/fdic.py`
- Test: `scripts/tests/test_fdic.py`

- [ ] **Step 1: Write the failing test**

```python
class TestRanking(unittest.TestCase):
    def test_ranks_and_applies_hygiene_floor(self):
        # API is asked to sort DESC by the ratio field; hygiene floor excludes tiny books.
        payload = {"data": [
            {"data": {"NAME": "BIG CRE BANK", "CITY": "Denver", "STALP": "CO",
                      "ASSET": 3200000, "NCRER": 6.4, "LNRENRES": 900000}},
            {"data": {"NAME": "OK BANK", "CITY": "Tampa", "STALP": "FL",
                      "ASSET": 1800000, "NCRER": 5.1, "LNRENRES": 400000}},
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake) as m:
            rows = fdic.ranking(metric_field="NCRER", repdte="20241231",
                                asset_min=1000000, limit=10)
        self.assertEqual(rows[0]["name"], "BIG CRE BANK")
        self.assertEqual(rows[0]["location"], "Denver, CO")
        self.assertEqual(rows[0]["asset"], "$3.2B")
        self.assertEqual(rows[0]["value"], 6.4)
        url = m.call_args[0][0]
        self.assertIn("sort_by=NCRER", url)
        self.assertIn("sort_order=DESC", url)
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — `AttributeError: module 'lenses.fdic' has no attribute 'ranking'`.

- [ ] **Step 3: Write minimal implementation** (append to `fdic.py`)

```python
def _fmt_assets(thousands):
    """FDIC ASSET is in $000s. Render as $X.YB / $XXXm."""
    dollars = _num(thousands) * 1000
    if dollars >= 1e9:
        return f"${dollars / 1e9:.1f}B"
    return f"${dollars / 1e6:.0f}m"


def ranking(metric_field, repdte, asset_min, limit, timeout=25):
    """Top-`limit` banks by `metric_field` (descending) for one quarter.

    `asset_min` (in $000s) is the hygiene floor that keeps tiny-book artifacts
    (e.g. a bank showing 100% on a negligible loan book) out of the ranking.
    """
    flt = f"REPDTE:{repdte} AND ASSET:[{asset_min} TO *]"
    params = {
        "filters": flt,
        "fields": f"NAME,CITY,STALP,ASSET,{metric_field}",
        "sort_by": metric_field,
        "sort_order": "DESC",
        "limit": limit,
        "format": "json",
    }
    url = f"{FINANCIALS_BASE}?{urllib.parse.urlencode(params)}"
    payload = _get(url, timeout)
    out = []
    for row in _rows(payload):
        out.append({
            "name": row.get("NAME", ""),
            "location": f"{row.get('CITY','')}, {row.get('STALP','')}".strip(", "),
            "asset": _fmt_assets(row.get("ASSET")),
            "value": row.get(metric_field),
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/fdic.py scripts/tests/test_fdic.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): FDIC bank-ranking fetcher with hygiene floor"
```

---

## Task 3: FDIC tier-aggregate fetcher

**Files:**
- Modify: `scripts/lenses/fdic.py`
- Test: `scripts/tests/test_fdic.py`

- [ ] **Step 1: Write the failing test**

```python
class TestTiers(unittest.TestCase):
    def test_buckets_by_asset_band_and_sums(self):
        # Two banks: one community (<$10B = 10,000,000 $000s), one large.
        payload = {"data": [
            {"data": {"ASSET": 5000000, "NALNLS": 60, "LNLSNET": 6000}},     # community
            {"data": {"ASSET": 400000000, "NALNLS": 60, "LNLSNET": 12000}},  # large
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        tiers = [("Community (<$10B)", 0, 10_000_000),
                 ("Large (>$250B)", 250_000_000, None)]
        metric = {"key": "noncurrent", "numerator": ["NALNLS"], "denominator": ["LNLSNET"], "scale": 100.0}
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            rows = fdic.tier_aggregates([metric], repdte="20241231", tiers=tiers)
        # community: 60/6000*100 = 1.0 ; large: 60/12000*100 = 0.5
        self.assertEqual(rows[0]["tier"], "Community (<$10B)")
        self.assertEqual(rows[0]["values"][0]["value"], 1.0)
        self.assertEqual(rows[1]["values"][0]["value"], 0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — no attribute `tier_aggregates`.

- [ ] **Step 3: Write minimal implementation** (append to `fdic.py`)

```python
def tier_aggregates(metrics, repdte, tiers, timeout=25):
    """Per-size-tier ratios for one quarter.

    Pulls all banks' dollar fields once, buckets by asset band, sums per band,
    then computes each metric's ratio per tier. `tiers` is a list of
    (label, asset_min_000s, asset_max_000s_or_None).
    """
    fields = {"ASSET"}
    for m in metrics:
        fields.update(m["numerator"]); fields.update(m["denominator"])
    banks = _fetch_all_financials(sorted(fields), repdte, timeout)
    rows = []
    for label, lo, hi in tiers:
        members = [b for b in banks
                   if _num(b.get("ASSET")) >= lo and (hi is None or _num(b.get("ASSET")) < hi)]
        values = []
        for m in metrics:
            num = sum(_num(b.get(f)) for b in members for f in m["numerator"])
            den = sum(_num(b.get(f)) for b in members for f in m["denominator"])
            values.append({"value": round(m["scale"] * num / den, 4) if den else None})
        rows.append({"tier": label, "values": values})
    return rows


def _fetch_all_financials(fields, repdte, timeout, page=10000):
    """Page through every bank's financials for one quarter."""
    out, offset = [], 0
    while True:
        params = {"filters": f"REPDTE:{repdte}", "fields": ",".join(fields),
                  "limit": page, "offset": offset, "format": "json"}
        url = f"{FINANCIALS_BASE}?{urllib.parse.urlencode(params)}"
        rows = _rows(_get(url, timeout))
        out.extend(rows)
        if len(rows) < page:
            return out
        offset += page
```

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/fdic.py scripts/tests/test_fdic.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): FDIC size-tier aggregator"
```

---

## Task 4: Banking narrative rules + headlines

**Files:**
- Modify: `scripts/lenses/narrative.py`
- Test: `scripts/tests/test_narrative_banking.py`

Rules follow the existing `(obs) -> (text, status)` contract; thresholds below are the v1 starting points (documented in the spec, tunable).

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/test_narrative_banking.py
import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


class TestNoncurrent(unittest.TestCase):
    def test_low_is_ok(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 0.7)]); self.assertEqual(s, "ok")
    def test_creeping_is_watch(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 1.2)]); self.assertEqual(s, "watch")
    def test_high_is_elevated(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 2.1)]); self.assertEqual(s, "elevated")
    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_noncurrent([]), ("Data unavailable.", "unknown"))


class TestUninsuredShare(unittest.TestCase):
    def test_high_is_watch(self):
        t, s = narrative.rule_uninsured_share([("2024-12-31", 45.0)])
        self.assertEqual(s, "watch"); self.assertIn("45.0%", t)
    def test_low_is_ok(self):
        _, s = narrative.rule_uninsured_share([("2024-12-31", 25.0)]); self.assertEqual(s, "ok")


class TestBankingHeadline(unittest.TestCase):
    def test_asset_quality_watch(self):
        h, o = narrative.synthesize("bank-asset-quality", ["ok", "watch", "ok"])
        self.assertEqual(o, "watch"); self.assertTrue(h)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — `rule_noncurrent` not defined.

- [ ] **Step 3: Write minimal implementation** (append rules to `narrative.py`, add headline blocks to `HEADLINES`)

```python
def rule_noncurrent(obs):
    """Noncurrent loan rate (% of loans 90+ days late). <1 ok, 1-2 watch, >=2 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 1.0:
        return (f"Just {v:.2f}% of loans are 90+ days past due — low by historical standards.", "ok")
    if v < 2.0:
        return (f"Noncurrent loans are at {v:.2f}%, creeping up off recent lows.", "watch")
    return (f"Noncurrent loans have climbed to {v:.2f}% — elevated and worth watching.", "elevated")


def rule_charge_offs(obs):
    """Net charge-off rate (% of loans). <0.6 ok, 0.6-1.2 watch, >=1.2 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0.6:
        return (f"Banks are writing off {v:.2f}% of loans as losses — a benign level.", "ok")
    if v < 1.2:
        return (f"Loan losses are running at {v:.2f}%, above the calm-period norm.", "watch")
    return (f"Loan losses have reached {v:.2f}% — a meaningful drag on earnings.", "elevated")


def rule_coverage(obs):
    """Allowance coverage (allowance as % of noncurrent loans). Higher = safer."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 150:
        return (f"Reserves cover {v:.0f}% of problem loans — a comfortable cushion.", "ok")
    if v >= 100:
        return (f"Reserves cover {v:.0f}% of problem loans — adequate but not generous.", "watch")
    return (f"Reserves cover only {v:.0f}% of problem loans — a thin cushion.", "elevated")


def rule_cre_concentration(obs):
    """CRE loans as % of equity capital. >300 is the interagency 'concentration' flag."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 300:
        return (f"Commercial real estate equals {v:.0f}% of capital — above the supervisory concentration flag.", "elevated")
    if v >= 200:
        return (f"Commercial real estate is {v:.0f}% of capital — a notable concentration.", "watch")
    return (f"Commercial real estate is {v:.0f}% of capital — a manageable share.", "ok")


def rule_uninsured_share(obs):
    """Uninsured deposits as % of total deposits. Higher = more flight-prone."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 40:
        return (f"{v:.1f}% of deposits sit above the FDIC insurance cap — flight-prone if confidence cracks.", "watch")
    return (f"{v:.1f}% of deposits are uninsured — a moderate, manageable share.", "ok")


def rule_capital_ratio(obs):
    """Equity-to-assets (%). <8 thin, 8-10 watch, >=10 ok."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 8:
        return (f"Equity is {v:.1f}% of assets — a thin capital cushion.", "elevated")
    if v < 10:
        return (f"Equity is {v:.1f}% of assets — adequate capital.", "watch")
    return (f"Equity is {v:.1f}% of assets — a healthy capital cushion.", "ok")


def rule_net_margin(obs):
    """Net interest income as % of assets (NIM proxy). Higher = healthier earnings."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 2.5:
        return (f"Net interest margin is {v:.2f}% — compressed, squeezing bank earnings.", "watch")
    return (f"Net interest margin is {v:.2f}% — a healthy spread on lending.", "ok")


def rule_level_trend(obs):
    """Generic level metric ($000s) read as a year-over-year direction. Always 'ok' status."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if prior is None or prior == 0:
        return (f"Latest reading: {v:,.0f}.", "ok")
    pct = (v - prior) / abs(prior) * 100
    if pct >= 5:
        return (f"Up {pct:.0f}% from a year ago.", "ok")
    if pct <= -5:
        return (f"Down {abs(pct):.0f}% from a year ago.", "ok")
    return ("Little changed from a year ago.", "ok")
```

Add to `HEADLINES`:
```python
    "bank-asset-quality": {
        "alert": "Loan losses are mounting — credit quality is deteriorating fast.",
        "elevated": "Problem loans are elevated — commercial real estate is the pressure point.",
        "watch": "Loan books are healthy overall, but problem loans are creeping up.",
        "ok": "Bank loan quality is strong — few loans are going bad.",
        "unknown": "Some asset-quality data is temporarily unavailable.",
    },
    "bank-profitability": {
        "alert": "Bank earnings are collapsing.",
        "elevated": "Bank profitability is under real pressure.",
        "watch": "Bank earnings are holding, but margins are tightening.",
        "ok": "Banks are solidly profitable.",
        "unknown": "Some profitability data is temporarily unavailable.",
    },
    "bank-capital-solvency": {
        "alert": "Bank capital is dangerously thin.",
        "elevated": "Capital cushions are thinner than supervisors prefer.",
        "watch": "Capital is adequate but worth watching.",
        "ok": "Banks are well-capitalized.",
        "unknown": "Some capital data is temporarily unavailable.",
    },
    "bank-concentrations-funding": {
        "alert": "Funding and concentration risks are acute.",
        "elevated": "Concentration or funding risk is elevated.",
        "watch": "Some concentration and funding risks are building.",
        "ok": "Funding is stable and concentrations are contained.",
        "unknown": "Some concentration/funding data is temporarily unavailable.",
    },
```

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/narrative.py scripts/tests/test_narrative_banking.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): narrative rules and headlines"
```

---

## Task 5: Config — banking category, lenses, tier & ranking specs

**Files:**
- Modify: `scripts/lenses/config.py`
- Test: `scripts/tests/test_config_banking.py`

Add a `BankingIndicator` (source="fdic", carries a `Metric`), the four `BANKING_LENSES`, plus per-lens `tier_spec` and `ranking_specs`. Keep `LENSES` (economic) untouched; add `CATEGORIES`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/test_config_banking.py
import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestBankingConfig(unittest.TestCase):
    def test_four_banking_lenses(self):
        self.assertEqual(len(config.BANKING_LENSES), 4)
        self.assertEqual(config.BANKING_LENSES[0].id, "bank-asset-quality")

    def test_indicators_are_fdic_with_metrics(self):
        ind = config.BANKING_LENSES[0].indicators[0]
        self.assertEqual(ind.source, "fdic")
        self.assertTrue(ind.metric.numerator)

    def test_categories_registry(self):
        ids = [c["id"] for c in config.CATEGORIES]
        self.assertIn("economic", ids)
        self.assertIn("banking", ids)
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — `BANKING_LENSES` not defined.

- [ ] **Step 3: Write minimal implementation** (add to `config.py`)

```python
TIERS = [
    ("Community (<$10B)", 0, 10_000_000),
    ("Regional ($10B–$250B)", 10_000_000, 250_000_000),
    ("Large (>$250B)", 250_000_000, None),
]


@dataclass(frozen=True)
class Metric:
    numerator: list
    denominator: list
    scale: float = 100.0


@dataclass(frozen=True)
class BankingIndicator:
    id: str
    title: str
    short: str
    unit: str
    color: str
    metric: Metric
    rule: Callable
    context: str
    value_format: str = "decimal"
    limit: int = 80              # ~20y of quarters
    source: str = "fdic"


@dataclass(frozen=True)
class BankingLens:
    id: str
    title: str
    accent: str
    indicators: list = field(default_factory=list)
    tier_metrics: list = field(default_factory=list)   # [{key,label,numerator,denominator,scale}]
    rankings: list = field(default_factory=list)        # [{title,subtitle,metric_field,asset_min,limit,value_label,rule}]


BANK_ASSET_QUALITY = BankingLens(
    id="bank-asset-quality",
    title="Asset Quality",
    accent="#FBBF24",
    indicators=[
        BankingIndicator(id="noncurrent", title="Noncurrent Loan Rate · loans 90+ days past due",
            short="Noncurrent", unit="%", color="#FBBF24",
            metric=Metric(["NALNLS"], ["LNLSNET"]), rule=narrative.rule_noncurrent,
            context="The share of all bank loans that are 90+ days late or no longer accruing interest — the broadest gauge of credit going bad."),
        BankingIndicator(id="charge-offs", title="Net Charge-Off Rate", short="Charge-offs",
            unit="%", color="#FB923C", metric=Metric(["NTLNLS"], ["LNLSNET"]),
            rule=narrative.rule_charge_offs,
            context="Loans banks have given up on and written off as losses, as a share of total loans."),
        BankingIndicator(id="coverage", title="Allowance Coverage Ratio", short="Coverage",
            unit="%", color="#34D399", metric=Metric(["LNATRES"], ["NALNLS"]),
            rule=narrative.rule_coverage,
            context="Money banks have set aside for losses, measured against the loans already going bad. Higher means a thicker safety buffer."),
        BankingIndicator(id="provisions", title="Provisions for Credit Losses · quarterly",
            short="Provisions", unit="", color="#38BDF8", metric=Metric(["ELNATR"], []),
            rule=narrative.rule_level_trend, value_format="thousands",
            context="New money banks are setting aside this quarter to cover expected future loan losses — a forward-looking read on how worried they are."),
    ],
    tier_metrics=[
        {"key": "noncurrent", "label": "Noncurrent", "numerator": ["NALNLS"], "denominator": ["LNLSNET"], "scale": 100.0},
        {"key": "coverage", "label": "Coverage", "numerator": ["LNATRES"], "denominator": ["NALNLS"], "scale": 100.0},
    ],
    rankings=[
        {"title": "Highest commercial-real-estate delinquency", "subtitle": "banks over $1B in assets",
         "metric_field": "NCRER", "asset_min": 1_000_000, "limit": 10,
         "value_label": "CRE delinq.", "unit": "%"},
    ],
)

# Profitability
BANK_PROFITABILITY = BankingLens(
    id="bank-profitability", title="Profitability", accent="#34D399",
    indicators=[
        BankingIndicator(id="net-margin", title="Net Interest Margin", short="Margin",
            unit="%", color="#34D399", metric=Metric(["INTINC", "EINTEXP"], ["ASSET"], scale=100.0),
            rule=narrative.rule_net_margin,
            context="The spread banks earn between what they make on loans and pay on deposits, relative to their assets — the core of bank earnings.",
            ),  # NOTE: numerator handled as INTINC - EINTEXP in build (see Task 6 signed-numerator note)
        BankingIndicator(id="net-income", title="Net Income · quarterly", short="Net income",
            unit="", color="#38BDF8", metric=Metric(["NETINC"], []), rule=narrative.rule_level_trend,
            value_format="thousands",
            context="Total industry profit for the quarter, in thousands of dollars."),
        BankingIndicator(id="noninterest-income", title="Noninterest Income · quarterly",
            short="Fee income", unit="", color="#A78BFA", metric=Metric(["NONII"], []),
            rule=narrative.rule_level_trend, value_format="thousands",
            context="Income banks earn from fees and services rather than lending — diversification away from interest income."),
    ],
    tier_metrics=[
        {"key": "margin", "label": "Net margin", "numerator": ["INTINC", "EINTEXP"], "denominator": ["ASSET"], "scale": 100.0},
    ],
    rankings=[],
)

# Capital & Solvency
BANK_CAPITAL = BankingLens(
    id="bank-capital-solvency", title="Capital & Solvency", accent="#38BDF8",
    indicators=[
        BankingIndicator(id="equity-assets", title="Equity-to-Assets", short="Capital",
            unit="%", color="#38BDF8", metric=Metric(["EQ"], ["ASSET"]), rule=narrative.rule_capital_ratio,
            context="Shareholder equity as a share of total assets — the simplest measure of the cushion standing between losses and insolvency."),
    ],
    tier_metrics=[
        {"key": "capital", "label": "Equity/assets", "numerator": ["EQ"], "denominator": ["ASSET"], "scale": 100.0},
    ],
    rankings=[
        {"title": "Thinnest capital cushion", "subtitle": "banks over $1B in assets",
         "metric_field": "EQV", "asset_min": 1_000_000, "limit": 10,
         "value_label": "Equity/assets", "unit": "%", "sort_order": "ASC"},
    ],
)

# Concentrations & Funding
BANK_CONCENTRATIONS = BankingLens(
    id="bank-concentrations-funding", title="Concentrations & Funding", accent="#A78BFA",
    indicators=[
        BankingIndicator(id="uninsured", title="Uninsured-Deposit Share", short="Uninsured dep.",
            unit="%", color="#FBBF24", metric=Metric(["DEPNI"], ["DEP"]), rule=narrative.rule_uninsured_share,
            context="The share of deposits above the $250k FDIC insurance cap — the money most likely to flee in a panic, as it did at Silicon Valley Bank."),
        BankingIndicator(id="cre-concentration", title="CRE Concentration · % of capital",
            short="CRE/capital", unit="%", color="#FB923C",
            metric=Metric(["LNRENRES", "LNREMULT"], ["EQ"]), rule=narrative.rule_cre_concentration,
            context="Commercial real-estate loans measured against capital. Above ~300% is the level bank supervisors flag as a concentration risk."),
        BankingIndicator(id="loans-deposits", title="Loans-to-Deposits", short="Loans/dep.",
            unit="%", color="#34D399", metric=Metric(["LNLSNET"], ["DEP"]), rule=narrative.rule_level_trend,
            context="How much of deposits banks have lent out — a gauge of how stretched the system's funding is."),
    ],
    tier_metrics=[
        {"key": "uninsured", "label": "Uninsured dep.", "numerator": ["DEPNI"], "denominator": ["DEP"], "scale": 100.0},
        {"key": "cre", "label": "CRE/capital", "numerator": ["LNRENRES", "LNREMULT"], "denominator": ["EQ"], "scale": 100.0},
    ],
    rankings=[
        {"title": "Most reliant on uninsured deposits", "subtitle": "banks over $1B in assets",
         "metric_field": "DEPUNINS", "asset_min": 1_000_000, "limit": 10,
         "value_label": "Uninsured dep.", "unit": "%"},
    ],
)

BANKING_LENSES = [BANK_ASSET_QUALITY, BANK_PROFITABILITY, BANK_CAPITAL, BANK_CONCENTRATIONS]

CATEGORIES = [
    {"id": "economic", "title": "Economic Lenses", "lenses": LENSES, "out": "lenses",
     "back": "Economic Lenses", "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed",
     "disclaimer": ""},
    {"id": "banking", "title": "Banking System Health", "lenses": BANKING_LENSES, "out": "banking",
     "back": "Banking System Health",
     "source_label": "FDIC, quarterly bank Call Reports",
     "disclaimer": "Public regulatory data. Not investment advice and not a judgment of any institution's solvency."},
]
```

> **Build note for Task 6 (signed numerator):** the net-margin metric needs `INTINC - EINTEXP`, not `INTINC + EINTEXP`. Implement this by having `build` treat the metric numerator/denominator field lists through `fdic.national_series`, and add net interest income as a *derived* summary by passing `EINTEXP` as a field to subtract. Concretely: extend `national_series` numerator handling to accept a parallel `signs` list, OR (simpler, chosen) add a dedicated summary field pair and compute NIM proxy as `(sum(INTINC) - sum(EINTEXP)) / sum(ASSET)`. Task 6 Step 3 implements the subtraction explicitly.

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/config.py scripts/tests/test_config_banking.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): config — categories, banking lenses, tier & ranking specs"
```

---

## Task 6: Build banking lens JSON (indicators + tiers + rankings)

**Files:**
- Modify: `scripts/lenses/build.py`
- Test: `scripts/tests/test_build_banking.py`

Add `build_banking_lens(lens, fetched_series, tier_rows, ranking_rows)` that reuses the existing indicator-card assembly and appends `tiers` + `rankings`. The net-margin subtraction is handled where the metric has two numerator fields with the second being interest expense — represented explicitly by a `subtract_from_first` convention documented in the test.

- [ ] **Step 1: Write the failing test**

```python
# scripts/tests/test_build_banking.py
import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config, narrative


class TestBuildBanking(unittest.TestCase):
    def test_assembles_indicators_tiers_rankings(self):
        lens = config.BANK_ASSET_QUALITY
        series = {  # fetch_key -> observations
            "noncurrent": [{"date": "2024-12-31", "value": "0.91"}],
            "charge-offs": [{"date": "2024-12-31", "value": "0.52"}],
            "coverage": [{"date": "2024-12-31", "value": "187"}],
            "provisions": [{"date": "2024-12-31", "value": "5000"}],
        }
        tier_rows = [{"tier": "Community (<$10B)", "values": [{"value": 1.1}, {"value": 142}]}]
        ranking_rows = {"Highest commercial-real-estate delinquency":
                        [{"name": "X BANK", "location": "Denver, CO", "asset": "$3.2B", "value": 6.4}]}
        out = build.build_banking_lens(lens, series, tier_rows, ranking_rows)
        self.assertEqual(out["id"], "bank-asset-quality")
        self.assertEqual(len(out["indicators"]), 4)
        self.assertIn("tiers", out)
        self.assertEqual(out["tiers"]["rows"][0]["tier"], "Community (<$10B)")
        self.assertEqual(out["rankings"][0]["rows"][0]["name"], "X BANK")
        self.assertEqual(out["rankings"][0]["rows"][0]["value"], "6.40%")
        self.assertTrue(out["headline_read"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — no `build_banking_lens`.

- [ ] **Step 3: Write minimal implementation** (add to `build.py`)

```python
def _status_color(value, rule):
    cleaned = [("x", value)] if value is not None else []
    _, status = rule(cleaned)
    return status


def build_banking_lens(lens, series_by_key, tier_rows, ranking_rows):
    """Assemble one banking lens JSON: indicators (time series) + tiers + rankings."""
    indicators, statuses = [], []
    for ind in lens.indicators:
        raw = series_by_key.get(ind.id, [])
        cleaned = util.clean(raw)
        text, status = ind.rule(cleaned)
        statuses.append(status)
        indicators.append({
            "id": ind.id, "title": ind.title, "short": ind.short, "unit": ind.unit,
            "color": ind.color, "observations": raw, "latest": _latest_raw(raw),
            "context": ind.context, "read": text, "signal_status": status,
            "value_format": ind.value_format,
        })
    headline, overall = narrative.synthesize(lens.id, statuses)

    tiers = None
    if lens.tier_metrics and tier_rows:
        columns = [{"key": m["key"], "label": m["label"]} for m in lens.tier_metrics]
        rows = []
        for tr in tier_rows:
            vals = []
            for m, cell in zip(lens.tier_metrics, tr["values"]):
                v = cell.get("value")
                vals.append({
                    "value": "—" if v is None else f"{v:.2f}%" if m["scale"] == 100.0 else f"{v:,.0f}",
                    "status": _status_color(v, _tier_rule(lens, m["key"])),
                })
            rows.append({"tier": tr["tier"], "values": vals})
        tiers = {"label": "Across the system — by bank size",
                 "subtitle": "Where is the stress concentrated?",
                 "columns": columns, "rows": rows}

    rankings = []
    for spec in lens.rankings:
        rows = []
        for r in ranking_rows.get(spec["title"], []):
            v = r.get("value")
            unit = spec.get("unit", "")
            rows.append({"name": r["name"], "location": r["location"], "asset": r["asset"],
                         "value": "—" if v is None else f"{float(v):.2f}{unit}",
                         "status": _status_color(float(v) if v is not None else None,
                                                  _ranking_rule(spec))})
        rankings.append({"title": spec["title"], "subtitle": spec["subtitle"],
                         "value_label": spec["value_label"], "rows": rows})

    return {
        "id": lens.id, "title": lens.title, "accent": lens.accent, "last_updated": _now(),
        "status": overall, "headline_read": headline,
        "indicators": indicators, "tiers": tiers, "rankings": rankings,
    }


def _tier_rule(lens, key):
    """Map a tier column to the matching indicator rule for status coloring."""
    for ind in lens.indicators:
        if ind.id == key or ind.short.lower().startswith(key):
            return ind.rule
    return lambda obs: ("", "unknown")


def _ranking_rule(spec):
    return spec.get("rule", lambda obs: ("", "elevated"))
```

> Net-margin subtraction note: `series_by_key["net-margin"]` is produced in Task 7 by computing `(ΣINTINC − ΣEINTEXP)/ΣASSET`. Build treats it as a normal series, so no special-casing here.

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/build.py scripts/tests/test_build_banking.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): assemble banking lens JSON with tiers and rankings"
```

---

## Task 7: Refresh orchestration — fetch + build + write banking

**Files:**
- Modify: `scripts/refresh_lenses.py`
- Test: `scripts/tests/test_smoke.py` (extend with a banking dry-run)
- Create: `scripts/tests/fixtures/fdic_sample.json`

Add a banking branch: for each banking lens, fetch each indicator's national series (`fdic.national_series`), the tier aggregates (`fdic.tier_aggregates`), and each ranking (`fdic.ranking`); build via `build.build_banking_lens`; write to `data/banking/`. Net-margin handled by subtracting EINTEXP via a small wrapper. `--dry-run` reads `fdic_sample.json`.

- [ ] **Step 1: Write the failing test** (extend smoke)

```python
class TestBankingDryRun(unittest.TestCase):
    def test_builds_four_banking_lenses_offline(self):
        import refresh_lenses
        jsons = refresh_lenses.build_banking_from_fixture()  # added in Step 3
        self.assertEqual(len(jsons), 4)
        ids = {j["id"] for j in jsons}
        self.assertEqual(ids, {"bank-asset-quality", "bank-profitability",
                               "bank-capital-solvency", "bank-concentrations-funding"})
        aq = next(j for j in jsons if j["id"] == "bank-asset-quality")
        self.assertTrue(aq["indicators"][0]["observations"])
        self.assertIsNotNone(aq["tiers"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: discover command. Expected: FAIL — no `build_banking_from_fixture`.

- [ ] **Step 3: Write minimal implementation** (add to `refresh_lenses.py`)

```python
from lenses import fdic  # add to imports

BANK_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "banking"
FDIC_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fdic_sample.json"


def _net_margin_series(start, end):
    ii = {o["date"]: float(o["value"]) for o in fdic.national_series(["INTINC"], [], 1.0, start, end)}
    ie = {o["date"]: float(o["value"]) for o in fdic.national_series(["EINTEXP"], [], 1.0, start, end)}
    aa = {o["date"]: float(o["value"]) for o in fdic.national_series(["ASSET"], [], 1.0, start, end)}
    out = []
    for d in sorted(set(ii) & set(ie) & set(aa)):
        if aa[d]:
            out.append({"date": d, "value": f"{(ii[d] - ie[d]) / aa[d] * 100:.4f}"})
    return out


def _series_for_indicator(ind, start, end):
    if ind.id == "net-margin":
        return _net_margin_series(start, end)
    return fdic.national_series(ind.metric.numerator, ind.metric.denominator,
                                ind.metric.scale, start, end)


def fetch_banking(start, end):
    """Fetch all series/tiers/rankings for the banking lenses (live)."""
    latest = end  # latest quarter; refine to the most recent REPDTE present if needed
    result = {}
    for lens in config.BANKING_LENSES:
        series = {ind.id: _series_for_indicator(ind, start, end) for ind in lens.indicators}
        tiers = fdic.tier_aggregates(lens.tier_metrics, latest, config.TIERS) if lens.tier_metrics else []
        rankings = {}
        for spec in lens.rankings:
            rankings[spec["title"]] = fdic.ranking(spec["metric_field"], latest,
                                                   spec["asset_min"], spec["limit"])
        result[lens.id] = (series, tiers, rankings)
    return result


def build_banking_from_fixture():
    data = json.loads(FDIC_FIXTURE.read_text(encoding="utf-8"))
    out = []
    for lens in config.BANKING_LENSES:
        s, t, r = data[lens.id]
        # JSON keys for rankings come back as title strings already
        out.append(build.build_banking_lens(lens, s, t, r))
    return out
```

Wire into `main()`: after the economic block, add a banking block that uses `fetch_banking` (live) or `build_banking_from_fixture` (`--dry-run`), then `build.write_outputs(bank_jsons, BANK_OUT_DIR)`. Economic lenses path stays exactly as-is.

Also create `scripts/tests/fixtures/fdic_sample.json` — a small object keyed by the four lens ids, each `[series_by_key, tier_rows, ranking_rows]`, mirroring the shapes in Task 6's test. (Concrete fixture content written during execution from the live probe outputs; it is real captured data, not a placeholder.)

- [ ] **Step 4: Run test to verify it passes**

Run: discover command. Expected: PASS.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/refresh_lenses.py scripts/tests/test_smoke.py scripts/tests/fixtures/fdic_sample.json
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): refresh orchestration + dry-run fixture"
```

---

## Task 8: Renderer — category-agnostic lens.js + table component

**Files:**
- Modify: `dashboards/lens.js`, `dashboards/lens.css`
- Test: manual (static site; verified by loading a page)

- [ ] **Step 1: Parameterize back link + footer.** In `render(root, lens)`, replace the hard-coded `← Economic Lenses` and FRED footer with values from `lens.category` (added to JSON) — fall back to the current strings when absent so economic pages are unchanged. Add `lens.category = {back, href, source_label, disclaimer}` in build for both categories (small addition to `build_lens`/`build_banking_lens`).

- [ ] **Step 2: Render tiers + rankings when present.** After appending indicator cards:

```javascript
function tableSection(label, subtitle, headCells, bodyRows) {
  const thead = headCells.map(h => `<th${h.num ? ' class="num"' : ''}>${esc(h.label)}</th>`).join("");
  const trs = bodyRows.map(r => "<tr>" + r.map(c =>
    c.pill ? `<td><span class="tpill ${esc(c.status)}">${esc(c.status)}</span></td>`
           : `<td class="${c.num ? "num " : ""}${c.status ? esc(c.status) : ""}">${esc(c.text)}</td>`
  ).join("") + "</tr>").join("");
  return `<section class="tbl-sec"><div class="tbl-lab">${esc(label)}</div>
    <div class="tbl-sub">${esc(subtitle || "")}</div>
    <table class="lens-table"><thead><tr>${thead}</tr></thead><tbody>${trs}</tbody></table></section>`;
}

if (lens.tiers) { /* build head from columns, rows from tiers.rows -> tableSection */ }
(lens.rankings || []).forEach(rk => { /* head: Bank, value_label(num), Assets(num), Signal; rows from rk.rows */ });
```

- [ ] **Step 3: Add table styles to `lens.css`** (dark theme, reuse pill colors):

```css
.tbl-sec { margin-top: 1.75rem; }
.tbl-lab { font-size: .7rem; text-transform: uppercase; letter-spacing: .12em; color: var(--blue); font-weight: 600; }
.tbl-sub { font-size: .8rem; color: var(--muted); margin: .25rem 0 .6rem; }
.lens-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.lens-table th { text-align: left; color: var(--faint); font-size: .65rem; text-transform: uppercase; letter-spacing: .07em; padding: .5rem .55rem; border-bottom: 1px solid var(--border); }
.lens-table td { padding: .55rem; border-bottom: 1px solid #131c2e; color: #E2E8F0; }
.lens-table td.num, .lens-table th.num { text-align: right; font-variant-numeric: tabular-nums; }
.lens-table td.ok{color:#34D399;} .lens-table td.watch{color:#FBBF24;}
.lens-table td.elevated{color:#FB923C;} .lens-table td.alert{color:#F87171;}
.tpill { font-size: .6rem; padding: .1rem .5rem; border-radius: 999px; border: 1px solid currentColor; text-transform: uppercase; }
.tpill.ok{color:#34D399;} .tpill.watch{color:#FBBF24;} .tpill.elevated{color:#FB923C;} .tpill.alert{color:#F87171;}
```

- [ ] **Step 4: Verify** by serving locally (Task 10) and loading a banking page; confirm econ pages are visually unchanged.

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/lens.js dashboards/lens.css
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): category-agnostic renderer + table component"
```

---

## Task 9: Pages — banking theme pages, banking overview, hub restructure

**Files:**
- Create: `dashboards/banking/{index,asset-quality,profitability,capital-solvency,concentrations-funding}.html`
- Modify: `dashboards/index.html`

- [ ] **Step 1:** Create each theme page from the lens-page boilerplate (mirror `recession-watch.html`), pointing at its JSON. Example `dashboards/banking/asset-quality.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Asset Quality — Bailey Analytics</title>
  <meta name="description" content="Plain-English read on U.S. bank loan quality — noncurrent loans, charge-offs, provisions, and CRE delinquency, from FDIC Call Reports.">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>
  <main id="lens-root"><div class="status-msg">Loading…</div></main>
  <script src="/dashboards/lens.js"></script>
  <script>renderLens("/data/banking/asset-quality.json");</script>
</body>
</html>
```

Repeat for the other three (titles/JSON paths per lens id).

- [ ] **Step 2:** Create `dashboards/banking/index.html` — a banking overview that fetches `/data/banking/index.json` and lists the four themes as cards (reuse the economic hub's card markup/CSS; back link to `/dashboards/`).

- [ ] **Step 3:** Modify `dashboards/index.html` to show two category sections: "Economic Lenses" (existing four) and "Banking System Health" (links into `/dashboards/banking/`). Follow the existing card grid markup.

- [ ] **Step 4: Verify** locally (Task 10).

- [ ] **Step 5: Commit** *(per commit policy)*

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/banking dashboards/index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(banking): theme pages, banking overview, two-category hub"
```

---

## Task 10: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1:** Run the full test suite — all pass:
  `python -m unittest discover -s ".../scripts/tests" -t ".../scripts"`
- [ ] **Step 2:** Backward-compat — regenerate economic lenses with `--dry-run` and confirm `data/lenses/*.json` are byte-identical to the committed versions (the source-dispatch refactor must not change economic output).
- [ ] **Step 3:** Live banking refresh once with network: `python scripts/refresh_lenses.py` → confirm `data/banking/*.json` written with sane values; capture real fixture data into `fdic_sample.json`.
- [ ] **Step 4:** Serve locally and click through: hub → Banking → each theme page; confirm charts, tier tables, spotlights render and economic pages are unchanged.
  `python -m http.server 8000 --directory "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics"`
- [ ] **Step 5:** Resolve open items from spec §9 as far as data allows (unrealized-securities-losses field; final thresholds); leave documented notes for any deferred.

---

## Commit policy (project-specific)

The user's standing rule: **commit/push only when the user asks.** The `git commit` steps above are the intended commit points, but during autonomous work do **not** run them — stage nothing and leave the working tree dirty for the user to review and commit. GitHub Pages deploys from `main`, so committing = deploying; never push without explicit instruction.

## Self-review notes
- Spec §3 lenses → Tasks 4–9 (all four). Spec §4 data methods → Tasks 1–3 + 7. Spec §5 architecture → Tasks 5–9. Spec §6 guardrails → narrative neutrality (Task 4), ranking hygiene (Task 2), disclaimer in category config (Task 5) + footer (Task 8). Spec §7 testing → Tasks 1–7,10. Spec §9 open items → Task 10 Step 5.
- Names kept consistent: `national_series`, `ranking`, `tier_aggregates`, `build_banking_lens`, `BankingLens.tier_metrics`/`.rankings`, `CATEGORIES`.
- Known proxies (documented, not placeholders): NIM ≈ net interest income / assets; capital ≈ equity/assets; CRE concentration uses nonresidential + multifamily RE. Risk-based capital and national CRE *delinquency* deferred (need fields absent from the summary endpoint).
- **CORRECTION (live test 2026-06-07):** Task 5's `uninsured` indicator using `Metric(["DEPNI"], ["DEP"])` is WRONG — summary `DEPNI` is *non-interest-bearing* deposits, not *uninsured*. There is no uninsured split in `/summary`. Before implementing Task 5/7, resolve spec §9 item 5: recommended fix is to make uninsured share a latest-quarter **tier + spotlight** metric only (financials `DEPUNINS`, already used in the spotlight) and replace the Concentrations time-series indicator with loans-to-deposits (`Metric(["LNLSNET"], ["DEP"])`, summary-supported). Awaiting user decision.
- **Validated against live API 2026-06-07:** `national_series` (noncurrent rate, loans-to-deposits-style ratios) and `ranking` (CRE stress, hygiene floor) return sane real values. Fetcher Tasks 1–3 + narrative Task 4 are implemented and passing (99 tests). Remaining: Tasks 5–10 (config, build, refresh, renderer, pages, e2e).

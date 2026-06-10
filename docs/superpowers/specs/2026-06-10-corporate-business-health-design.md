# Corporate & Business Health — 8th Dashboard Category — Design

**Date:** 2026-06-10
**Status:** Approved in brainstorm (Michael's calls: build in parallel with Global Economy; title "Corporate & Business Health"). Pending written-spec review.

## Goal

The "strategic" leg of the site's goal — executives benchmark against the
business landscape: are corporate profits growing, are new businesses forming,
is capex expanding, is credit tightening? This is the last planned breadth
category (see [[exec-dashboard-roadmap]]); with it and Global Economy shipped,
the macro/financial/physical/household/global/business domains are covered.

**Pure FRED** — zero new fetchers, zero new keys. All 16 series below were
live-verified 2026-06-10 (existence, frequency, history, latest obs). Notably:
the Moody's Baa spread (`BAA10YM`) carries history to 1953 with **no**
ICE-BofA-style rolling-window truncation.

## Category registration

```python
{"id": "business", "title": "Corporate & Business Health", "lenses": BUSINESS_LENSES,
 "out": "business", "back": "Corporate & Business Health",
 "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed",
 "disclaimer": ""}
```

- Data → `data/business/`, pages → `dashboards/business/<lens>.html` + hub.
- One line in the home `CATEGORIES` array; Today's Brief category map entry
  (`brief.py`) if needed — verify at plan time.
- CLI flag `--business`; new daily step in `refresh-fred.yml` under the
  `if: success() || failure()` pattern.

## The four lenses

### 1. Profitability (`business-profitability`) — quarterly → page passes `defaultRange: "5Y"`

| Indicator | Series | Role |
|---|---|---|
| Corporate profits after tax | `CP` → `yoy_pct` | **Lead.** One-sided YoY bands (falling profits = stress): ≥0% ok / 0 to −5 watch / −5 to −15 elevated / <−15 alert. ~$3.9T level surfaces in the read. |
| Nonfinancial corporate profits | `NFCPATAX` → `yoy_pct` | Info — the "Main Street corporates" read, strips out banks. |
| Profits share of GDP | `CP` ÷ `GDP` × 100 (cross-series, computed in build like the electricity generation shares via `util.pct_share`) | Info — the margin proxy (FRED has no margin series; verified). |
| Proprietors' income | `PROPINC` → `yoy_pct` | Info — the closest thing to small-business earnings. |

### 2. Business Formation (`business-formation`) — monthly, fresh (May 2026 already posted)

| Indicator | Series | Role |
|---|---|---|
| Business applications | `BABATOTALSAUS` → `yoy_pct` | **Lead.** YoY bands (applications falling = dynamism stress): ≥0 ok / 0 to −5 watch / −5 to −15 elevated / <−15 alert. ~524K/month level in the read. |
| High-propensity applications | `BAHBATOTALSAUS` → `yoy_pct` | Info — applications likely to become employers (the quality signal). **Note: the id is BAHBA…, not HBABA… — the latter does not exist.** |
| High-propensity share | `BAHBATOTALSAUS` ÷ `BABATOTALSAUS` × 100 | Info — formation quality over time. |

### 3. Investment & Activity (`business-investment`) — monthly

| Indicator | Series | Role |
|---|---|---|
| Core capex orders | `NEWORDER` → `yoy_pct` | **Lead.** YoY bands (nondefense capital goods ex-aircraft — the cleanest "are businesses investing?" signal): ≥0 ok / 0 to −3 watch / −3 to −10 elevated / <−10 alert. |
| Real business sales | `CMRMTSPL` → `yoy_pct` | YoY band — real manufacturing & trade sales, an NBER recession-dating input, 1967→. |
| Inventories-to-sales ratio | `ISRATIO` | Level bands (rising = overhang): <1.40 ok / 1.40–1.50 watch / ≥1.50 elevated (2008 peaked ~1.48, COVID spike ~1.55). |

(Headline durable goods `DGORDER` deliberately omitted — aircraft-order noise;
`NEWORDER` is the same survey minus the noise.)

### 4. Credit & Stress (`business-credit`) — monthly lead → default 1Y is fine

| Indicator | Series | Role |
|---|---|---|
| Baa spread over 10Y Treasury | `BAA10YM` | **Lead.** Level bands: <2.0 ok / 2.0–2.5 watch / 2.5–3.5 elevated / ≥3.5 alert (2008 ~6, COVID ~4). Monthly, 1953→. |
| Lending standards, C&I | `DRTSCILM` | Level bands on net % of banks tightening: ≤0 ok / 0–20 watch / 20–50 elevated / >50 alert. Quarterly SLOOS, already has Q2-2026. |
| Business-loan delinquency | `DRBLACBS` | Level bands: <1.5 ok / 1.5–2.5 watch / 2.5–4.0 elevated / ≥4.0 alert. Quarterly. |
| C&I loan growth | `BUSLOANS` → `yoy_pct` | Two-sided YoY band: contraction (<0) = stress; >10% credit boom = watch. |

Distinct series from Markets' ICE-BofA credit spreads (different index family),
so the one-home rule is satisfied; consider a footer cross-pointer between the
two credit lenses.

All band values above are first-pass calibrations — **verify each against full
series history percentiles at plan time** (the bands must put today's values in
sensible buckets and 2008/2020 in elevated/alert).

## Cross-cutting

- **Severity model:** standard severity throughout; everything is expressible
  with the existing `narrative` factories (`yoy_band`, `yoy_band_two_sided`,
  level bands) and `derive.yoy_pct` — extend factories only if a needed
  shape is genuinely missing.
- **Cross-series shares** (profit share of GDP, high-propensity share): computed
  at build/inject time from two fetched series via `util.pct_share`, following
  the electricity generation-share pattern. `GDP` (quarterly, $B SAAR) is
  fetched solely as an input to the share — it gets no chart of its own.
- **Units:** %, ratio, counts (~524K → readable scale per the unit conventions),
  $T in prose. Standard `_fmt`/`fmtVal` logic; keep in sync.
- **Tests:** TDD per repo norm — narrative band tests, derive/share tests,
  config-integrity tests, dry-run fixtures (`business` sample JSON) so
  `--dry-run` builds the category offline.

## Out of scope (deliberate, all researched)

- **Business bankruptcies** — no living FRED series (verified: only NBER series
  ending in the 1960s). US Courts publishes quarterly XLSX behind a
  varying-path scrape with intermittent 503s — feasible (stdlib xlsx parse was
  proven) but fragile, and `DRBLACBS`+`CORBLACBS` already cover realized
  distress at the same cadence. Deferred with research notes preserved here.
- **Census BFS detail** — the keyless bulk file
  (`census.gov/econ_getzippedfile/?programCode=BFS`, verified fresh daily) adds
  state × NAICS formation detail FRED lacks. Right upgrade path for a future
  map/sector feature; not needed for v1 (FRED carries both national headlines).
- **NFIB small-business optimism** — proprietary, not on FRED, no feed.
  Small-business angle is covered via `PROPINC`, `DRTSCIS` (SLOOS small firms,
  verified) and `CILSCBM027SBOG` (C&I loans at small banks, verified) — the
  latter two are available as info additions if a lens feels thin.

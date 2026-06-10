# Housing & Real Estate Category — Design

**Date:** 2026-06-10
**Status:** Approved by Michael (lens layout, two-sided status model, mortgage-rate move all confirmed)

## Goal

Add **Housing & Real Estate** as the 5th dashboard category (after Economic, Banking,
Markets, Energy & Commodities). Housing is the biggest remaining gap for an
executive/board audience and a classic leading indicator. All data is FRED-native —
no new fetcher, no new API key — making this the simplest category build yet.

Every candidate series was **live-verified against the FRED API on 2026-06-10**
(all 14 returned current data, including `FIXHAI` and `EXHOSLUSM495S`).

## Lenses & indicators (4 lenses, 15 indicators)

### 1. Home Prices (`housing-home-prices`) — "is the market overheating or freezing?"

| Indicator | Series | Freq | Role / rule |
|---|---|---|---|
| Case-Shiller National Home Price Index | `CSUSHPINSA` | monthly (~2-mo lag) | **driver** — `market_health`, YoY hot (6, 10, 15) / cold (−2, −5, −10) |
| Existing-Home Sales | `EXHOSLUSM495S` | monthly (SAAR) | **driver** — `market_health`, YoY hot (10, 20, 30) / cold (−10, −20, −30) |
| Median Sales Price of Houses Sold | `MSPUS` | quarterly | info |

### 2. Affordability & Financing (`housing-affordability`) — "can a regular family buy?"

| Indicator | Series | Freq | Role / rule |
|---|---|---|---|
| 30-Year Fixed Mortgage Rate | `MORTGAGE30US` | weekly | **driver** — level bands: ok <5.5, watch 5.5–6.5, elevated 6.5–7.5, alert ≥7.5. **Moved here from Economic → Cost of Money.** |
| NAR Housing Affordability Index | `FIXHAI` | monthly | **driver** — level bands (lower = worse; 100 = median family barely qualifies): ok ≥130, watch 110–130, elevated 95–110, alert <95 |
| Mortgage Debt Service (% of disposable income) | `MDSP` | quarterly | info |
| Mortgage Delinquency Rate (single-family, banks) | `DRSFRMACBS` | quarterly | **driver** — level bands: ok <2, watch 2–4, elevated 4–7, alert ≥7 (2009 peak ≈ 11) |

### 3. Supply & Construction (`housing-supply-construction`) — "are we building, and is inventory piling up?"

| Indicator | Series | Freq | Role / rule |
|---|---|---|---|
| Housing Starts | `HOUST` | monthly (thous., SAAR) | **driver** — `market_health`, YoY hot (20, 35, 50) / cold (−10, −20, −35) |
| Building Permits | `PERMIT` | monthly (thous., SAAR) | **driver** — `market_health`, same bands as starts (the leading indicator) |
| Months' Supply of New Houses | `MSACSR` | monthly | **driver** — two-sided level: ok 4–6 (balanced); tight: watch 3–4, elevated <3; glut: watch 6–8, elevated 8–10, alert >10 |
| Active Listings (Realtor.com) | `ACTLISCOUUS` | monthly (from 2016) | info |

### 4. Rent & Shelter (`housing-rent-shelter`) — "what's happening to the cost of a roof?"

| Indicator | Series | Freq | Role / rule |
|---|---|---|---|
| CPI: Rent of Primary Residence | `CUSR0000SEHA` | monthly | **driver** — `consumer_cost`, YoY watch 4 / elevated 6 / alert 9 |
| CPI: Owners' Equivalent Rent | `CUSR0000SEHC` | monthly | info |
| Rental Vacancy Rate | `RRVRUSQ156N` | quarterly | **driver** — two-sided level: ok 6–8; tight: watch 5–6, elevated <5; glut: watch 8–10, elevated >10 |
| Homeownership Rate | `RHORUSQ156N` | quarterly | info |

Indicator `context` strings explain each series in plain English (existing convention).
Large SAAR numbers (existing-home sales ≈ 4,170,000) display raw with explanatory
units, matching the Energy precedent; unit-suffix polish remains a site-wide open item.

## Status model: two-sided "market health" (the new piece)

Housing differs from Energy's one-sided consumer-cost model: **both overheating and
freezing are bad**. One new reusable narrative rule:

```python
narrative.market_health(label, hot=(w, e, a), cold=(w, e, a))
```

- YoY-%-change based, like `consumer_cost`, but with thresholds on both sides.
- Hot side text: "overheating — {label} up X% from a year ago."
- Cold side text: "cooling sharply — {label} down X% from a year ago."
- In-between: ok with a steady/balanced read.
- Returns the same severity ladder (`ok`/`watch`/`elevated`/`alert`/`unknown`), so
  `util.status_max`, badge colors, and `lens.css`/`lens.js` work unchanged.

Level-band drivers (mortgage rate, affordability index, delinquency, months' supply,
vacancy) get small dedicated rules with explicit bands, in the style of `rule_vix` /
`rule_noncurrent`. The two-sided level rules (months' supply, vacancy) phrase the
direction ("tight supply is propping up prices" vs "inventory glut").

Info indicators use a housing-flavored descriptive rule returning `info` (mirroring
`energy_level`), which `util.status_max` already ignores — the lens badge reflects
the worst **driver** severity. Housing lenses are NOT in `NEUTRAL_LENSES`.

**Threshold calibration:** the bands above are first-pass. Before deploy, run a live
build and sanity-check every badge against the actual data (the Energy playbook).
Expected with current data: affordability index 105.6 → elevated; months' supply
9.4 → elevated (glut side); delinquency 1.89 → ok; vacancy 7.3 → ok.

## The Cost of Money edit

- Remove `MORTGAGE30US` from `COST_OF_MONEY` (leaves fed funds, 10Y, 2Y — a clean
  policy-rates lens). Same playbook as the T10Y2Y yield-curve dedup.
- Cost of Money's lens-level read mentions mortgage rates in passing and points
  readers to the Housing category (text only, no chart).
- Update affected tests (`test_build.py` indicator counts) and regenerate
  `data/lenses/cost-of-money.json`.

Rationale (Michael's call): duplicated metrics cheapen the feel; every number gets
one home, and the mortgage rate is the star of the affordability story.

## Pipeline & pages (existing patterns only)

- **`config.py`:** `HOUSING_HOME_PRICES`, `HOUSING_AFFORDABILITY`,
  `HOUSING_SUPPLY_CONSTRUCTION`, `HOUSING_RENT_SHELTER`, `HOUSING_LENSES`, and a
  `CATEGORIES` entry (`id="housing"`, accent color distinct from the other four —
  use `#F472B6` pink).
- **`narrative.py`:** `market_health(...)`, the level-band rules, a housing info
  rule, and 4 `HEADLINES` entries.
- **`refresh_lenses.py`:** `--housing` flag + `refresh_housing(dry_run)` — pure
  FRED, no injection step (simpler than markets/energy). Output `data/housing/`
  (4 lens JSONs + `index.json`). Fixture `housing_sample.json` backs `--dry-run`.
- **Pages:** `dashboards/housing/{index,home-prices,affordability,supply-construction,rent-shelter}.html`
  cloned from the energy hub/lens pages (thin `renderLens` wrappers, FRED credit in
  footer). Hub card added to `dashboards/index.html`. Charts default to 1Y
  (mostly monthly data); quarterly series are sparse at 1Y but 5Y is one click away.
- **Workflow:** add a `--housing` step to the daily `refresh-fred.yml`
  (uses `FRED_API_KEY` only).
- **Root `index.html` showcase:** unchanged (deferred until Phase-1 categories are
  complete, per roadmap).

## Testing

TDD throughout, mirroring the Energy suite (~20 new tests):

- `test_narrative_housing.py` — `market_health` hot/cold/ok paths + every level-band
  rule at band edges + info rule.
- `test_config_housing.py` — 4 lenses, ids, sources all `fred`, no duplicate series
  site-wide (asserts `MORTGAGE30US` appears exactly once).
- `test_build_housing.py` — fixture-built lenses produce expected ids, statuses,
  scoreboard entries.
- `test_refresh_housing.py` — `--housing --dry-run` writes 4 lens files +
  `index.json` into a temp dir.
- Updated: `test_build.py` (cost-of-money 4 → 3 indicators).

Fixture dates run uniform 2025-01-01 → 2026-01-01 so YoY rules resolve (lesson from
the Energy fixture bug).

## Out of scope

- Regional/metro breakdowns (national only).
- Zillow/Redfin sources (not on FRED; revisit if granularity is wanted later).
- Commercial real estate (could be a future lens; office vacancy data is sparse on FRED).
- Root home-page showcase changes.

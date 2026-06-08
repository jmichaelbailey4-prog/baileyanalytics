# Banking System Health Dashboards — Design Spec

**Date:** 2026-06-07
**Status:** Draft for review
**Author:** Michael Bailey (with Claude)

## 1. Goal

Add a **Banking System Health** dashboard category to baileyanalytics.com that turns public FDIC bank Call Report data into plain-English reads — the same "lens" treatment the site already applies to FRED economic data. The value is making *important but illegible* regulatory data readable: is the U.S. banking system healthy, and where is stress building?

This is also the first step in a broader move: generalizing the site from "FRED economic lenses" into a multi-source, multi-category analytics resource (Census, SEC filings, market data are likely future categories).

## 2. Guiding principle: two layers, not one

The current codebase welds **data source** to **presentation format** — a "lens" is "some FRED series rendered a specific way." This redesign separates them:

1. **Ingestion layer** — where data comes from and how it is fetched/normalized. Pluggable per source (`fred.py`, new `fdic.py`, future `census.py`…). Every presentation format draws from it.
2. **Presentation layer** — how data is shown. The "lens" (a themed question answered by several time-series indicators) is **one format among several**. Banking reuses it heavily but adds new components.

Banking is the ideal first case to establish this split: its system-wide metrics are ordinary time series (fit the lens format unchanged), while its size-tier and per-bank views force exactly one new presentation component. We generalize **only** what banking forces — we design the seams so Census/SEC/markets can slot in later, but we do **not** pre-build a generic source registry or viz engine (YAGNI).

## 3. Scope

### In scope (v1)
- A **Banking System Health** category with **four themed banking lenses**:
  - **Asset Quality** — noncurrent loans, nonaccrual, net charge-offs, provisions, allowance coverage, CRE delinquency
  - **Profitability** — net interest margin, ROA/ROE, net income, interest income & expense, noninterest income, efficiency ratio
  - **Capital & Solvency** — risk-based capital, Tier 1, leverage ratio (+ unrealized securities losses if sourceable)
  - **Concentrations & Funding** — CRE concentration, loan mix, deposit mix, uninsured-deposit reliance, loans-to-deposits
- Each theme page = reused lens anatomy (read + badge + scoreboard + detailed metric cards) **plus** two appended sections: a **by-size-tier table** and a **ranked bank spotlight**.
- A **banking overview/landing page** listing the four themes (mirrors the economic-lenses hub).
- The main `/dashboards/` hub restructured to show **two categories**.
- The ingestion-layer generalization (source dispatch + `fdic.py`).
- The new shared presentation components (tier table + ranking table) in the shared renderer.

### Out of scope (deferred)
- **Rate Sensitivity** lens (5th theme) — requires duration/repricing data not cleanly available from the FDIC financials endpoint. Revisit once data is confirmed.
- Per-bank historical drill-downs / individual bank pages.
- Interactive screeners or user-selectable banks.
- A formal pluggable `DataSource` registry or generic visualization-block engine.

## 4. Data source: FDIC BankFind Suite API

Base: `https://api.fdic.gov/banks/` (no API key required; public regulatory data). Verified live 2026-06-07.

### 4.1 National quarterly history (metric charts)
Use the **`/summary`** endpoint. It returns **pre-summed dollar fields** grouped by **state × quarter (`REPDTE`) × institution class (`CB_SI`)**, going back decades. Method:
- Query a quarter range, all states, both `CB_SI` classes.
- Sum the dollar fields across state rows per `REPDTE` to get national totals.
- Compute each ratio from summed numerator/denominator (e.g. national noncurrent rate = ΣNALNLS ÷ ΣLNLSNET). **Never average per-entity ratios.**
- Result per metric: a `[{date, value}]` time series — identical shape to FRED output, so it reuses all existing chart/sparkline machinery.

Relevant summary dollar fields confirmed present: `ASSET, DEP, DEPI, DEPNI, NALNLS, NTLNLS, NCLNLS, LNLSNET, LNATRES, ELNATR, LNRENRES, LNREMULT, LNRE, NETINC, NIM, NONII, INTINC, EINTEXP, EQ, BANKS`.

### 4.2 Size-tier breakdown (latest quarter only — not a time series)
Use the **`/financials`** endpoint with asset-band filters (e.g. `ASSET:[1 TO 10000000]` etc., values in $000s). For the latest `REPDTE`, pull all banks' relevant dollar fields, bucket by asset band (Community <$10B / Regional $10B–$250B / Large >$250B), sum numerators/denominators per band, compute tier ratios. ~4,500 banks total → a handful of paginated calls, at refresh time only.

### 4.3 Bank spotlight rankings (latest quarter only)
Use **`/financials`** with `filters` (REPDTE + asset floor), `sort_by=<metric>`, `sort_order=DESC`, `limit=N`. Returns per-bank `NAME, CITY, STALP, ASSET, <metric>`. **Ranking hygiene (required):** apply a minimum-denominator filter (e.g. minimum CRE loan balance / total loans) to exclude tiny-book artifacts — a live probe surfaced a bank at "100% CRE-noncurrent" from a negligible book. Each ranking config declares its asset floor and hygiene threshold.

### 4.4 Cadence & volume
- Call Reports publish **quarterly**, ~30–40 days after quarter-end. The existing daily GitHub Actions cron can run the banking refresh too; it writes only when data changed (existing `write_lens_file` behavior), so most days are no-ops. No new schedule strictly required for v1.
- **Never bake raw panel data.** Only small derived JSON (national time series, tier aggregates, top-N rankings) is written to the repo.

### 4.5 Known open item: unrealized securities losses
The marquee "SVB metric" (AOCI / market-vs-amortized-cost gap on securities) is **not** a clean field in the financials endpoint. Candidates to investigate: `SCMV` (securities market value) vs `SC` (book), or the FDIC Quarterly Banking Profile aggregate, or a FRED series. Treated as a **Capital & Solvency enhancement**, not a v1 blocker. Document the resolution before adding the card.

## 5. Architecture & file changes

### 5.1 Ingestion: source dispatch
- Add `source` (default `"fred"`) and a `source_params` mechanism to the indicator config so each indicator declares where its data comes from.
- `refresh_lenses.py`'s fetch step groups indicators by source and dispatches to the right fetcher. FRED path is unchanged.
- New module `scripts/lenses/fdic.py` — the only banking module that touches the network. Exposes:
  - `fetch_summary_series(numerator_fields, denominator_fields, start, end)` → national `[{date, value}]` (percent or level).
  - `fetch_tier_aggregates(metric_spec, repdte, tiers)` → per-tier ratios for the latest quarter.
  - `fetch_ranking(metric_spec, repdte, asset_min, hygiene, limit)` → ranked list of `{name, city, state, asset, value, status}`.
  - Mirrors `fred.py` conventions (stdlib `urllib` only, returns plain dicts/lists).

### 5.2 Config: categories
- Extend `config.py` to express **categories**: `ECONOMIC_LENSES` (existing four) and `BANKING_LENSES` (new four). Each banking lens additionally declares its **tier spec** and **ranking spec(s)** for the appended sections.
- Indicators for banking lenses are FDIC-sourced; each declares numerator/denominator field codes (for ratio metrics) or a direct field.

### 5.3 New data shapes in lens JSON
Banking lens JSON reuses the existing structure (`indicators[]` time series) and adds two optional arrays consumed by the renderer:
- `tiers`: `{ label, columns:[{key,label}], rows:[{tier, values:[{value, status}]}] }`
- `rankings`: `[{ title, subtitle, columns, rows:[{name, location, asset, value, status}] }]`
Economic lenses simply omit these (renderer renders them only when present) — fully backward compatible.

### 5.4 Presentation: shared renderer
- Generalize `lens.js` (`renderLens`) so it is **category-agnostic**:
  - Parameterize the back link (text + href) and footer attribution (source + disclaimer) — currently hard-coded to "Economic Lenses" / FRED.
  - After rendering indicator cards, render `tiers` and `rankings` sections **if present**.
- Add a small **table renderer** for tier + ranking tables (the one genuinely new component), styled in `lens.css` to match the dark theme (status colors reuse existing pill classes).

### 5.5 Pages & data layout
```
data/
  lenses/            (existing economic lens JSON + index.json)
  banking/           (NEW: asset-quality.json, profitability.json,
                      capital-solvency.json, concentrations-funding.json, index.json)
dashboards/
  index.html         (RESTRUCTURED: lists both categories)
  banking/
    index.html       (NEW: banking overview, lists the 4 themes)
    asset-quality.html
    profitability.html
    capital-solvency.html
    concentrations-funding.html
  lens.js, lens.css  (generalized; shared by both categories)
scripts/
  refresh_lenses.py  (source dispatch added)
  lenses/
    fdic.py          (NEW)
    config.py        (categories + banking lenses)
    build.py, narrative.py, derive.py, util.py, recessions.py (extended as needed)
    tests/           (add FDIC fixtures + tests)
```

### 5.6 Narrative & status rules
- Add banking status rules to `narrative.py` (e.g. `rule_noncurrent`, `rule_cre_stress`, `rule_capital`, `rule_margin`), each mapping a latest value (and optionally trend) to `ok | watch | elevated | alert`, plus a one-line read.
- Per-lens headline synthesis reuses the existing `synthesize()` pattern, with banking-specific copy.
- Thresholds grounded in supervisory norms (e.g. noncurrent <1% ok; CRE concentration >300% of capital elevated per interagency guidance) — exact thresholds tuned during implementation with a documented rationale.

## 6. Guardrails (legal/editorial)

Publishing factual public data is safe; characterizations are where risk lives. The design bakes in:
- **Attribute everything** to FDIC Call Reports.
- **Per-metric status, never per-institution verdicts.** A bank row may show an "alert" pill on a *metric*; we never label a bank "failing"/"insolvent."
- **Disclaimer** on every banking page: "Public regulatory data. Not investment advice. Not a judgment of any institution's solvency."
- **Never claim to identify "problem banks"** — the FDIC Problem Bank List is confidential (count only). We show public ratios and let them speak.
- **Ranking hygiene** (§4.3) so we don't surface meaningless outliers.

## 7. Testing
- Reuse the existing offline `--dry-run` + fixtures pattern. Add captured FDIC API fixtures (summary, financials-tier, financials-ranking responses) under `scripts/tests/fixtures/`.
- Unit-test: national aggregation (sum-then-ratio), tier bucketing, ranking hygiene filter, and each new status rule.
- Verify backward compatibility: economic lenses build byte-identical output after the source-dispatch refactor.

## 8. Seams for future sources (validation, not v1 work)
- **Census / freight / more macro:** new fetcher → time-series indicators → reuse lens format directly (likely just more lenses in existing or new categories).
- **SEC filings:** new fetcher + a new presentation format (entity explorer) as a future category — the category structure and shared kit already accommodate it.
- **Market data:** either lens-shaped (market pulse) or a new explorer format; same pattern.
The two-layer split means each future source touches the ingestion layer + (optionally) one new presentation component, never the whole stack.

## 8a. As-built notes (implemented 2026-06-07, uncommitted)

**Supersedes §4's `/summary` plan: all banking data comes from the FDIC `/financials`
endpoint, aggregated quarterly.** Decisions as implemented:
- **Quarterly history (~81 quarters, 2006→present).** National series are aggregated
  across all banks per quarter from `/financials` — one bank fetch per quarter, shared
  across every indicator (~3 min full build). Charts, tiers, and rankings all draw from the
  same endpoint, so figures are consistent and match the FDIC Quarterly Banking Profile.
  (`/summary` was dropped — it's year-end only *and* its `NALNLS/LNLSNET` gave a wrong
  noncurrent rate, 0.68% vs the correct 0.98%.)
- **Prefer FDIC per-bank ratio fields** (`NCLNLSR`, `NTLNLSR`, `ROA`, `NIMY`, `LNLSDEPR`,
  `RBCRWAJ`), which are already annualized where relevant — loan/asset-weighted, no YTD
  de-cumulation needed. Sum-then-ratio only for reliable dollar fields (`EQ/ASSET`,
  `DEPUNINS/DEP`, CRE/`EQ`). `NALTOT` is null in `/financials` — never used. `NIM` is a
  dollar field (not the ratio) — use `NIMY`.
- **Indicators (all ratios):** Asset Quality = noncurrent, charge-offs; Profitability =
  net interest margin (`NIMY`), ROA; Capital = risk-based capital (`RBCRWAJ`) + equity/assets;
  Concentrations = uninsured-deposit share (now a proper chart), loans-to-deposits, CRE/capital.
- **Resolved earlier open items:** uninsured share is now a national chart (not just a tier);
  risk-based capital added; the tier-ROA-vs-chart cadence mismatch is gone (both annualized).
- **Refresh cadence (per-source):** `refresh_lenses.py` takes `--economic` / `--banking`
  (no flag = both). Daily `refresh-fred.yml` runs `--economic`; new weekly `refresh-banking.yml`
  runs `--banking`. **No cache** — full re-fetch each run so restated Call Reports self-heal.
- **Front-end:** `renderLens(url, opts)` is category-aware; economic pages call it with no
  opts and render byte-identically. Banking pages at `dashboards/banking/` pass banking chrome
  + the legal disclaimer; new tier/ranking table component in `lens.js`/`lens.css`.

## 9. Open items to resolve during implementation
1. Unrealized securities losses field mapping (§4.5).
2. Exact asset-band thresholds for tiers and the hygiene minimums for each ranking.
3. Final status-rule thresholds + rationale per metric.
4. Whether to add a dedicated quarterly cron or rely on the existing daily no-op refresh.
5. **Uninsured-deposit share has no cheap national time series.** Live testing (2026-06-07)
   confirmed the `/summary` endpoint's `DEPI`/`DEPNI` are *interest-bearing* /
   *non-interest-bearing* deposits, NOT insured/uninsured. The insured/uninsured split
   (`DEPINS`/`DEPUNINS`) exists only in the per-bank `/financials` endpoint. Options for the
   Concentrations & Funding lens: (a) use uninsured share only as a latest-quarter tier +
   spotlight metric (financials supports this), and chart a different funding time series
   (e.g. loans-to-deposits = `LNLSNET`/`DEP`, which summary supports); or (b) aggregate
   `DEPUNINS`/`DEP` across all banks per quarter for a true national trend (expensive — paginate
   ~4,500 banks per quarter; likely cache rather than recompute deep history). **Recommendation:
   option (a).** Decision pending.

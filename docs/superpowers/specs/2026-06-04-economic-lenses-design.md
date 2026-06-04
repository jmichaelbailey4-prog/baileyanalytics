# Economic Lenses — Design Spec

**Date:** 2026-06-04
**Status:** Approved design, pre-implementation
**Repo:** `baileyanalytics`

## 1. Overview

Revamp the single economic dashboard (`dashboards/economic.html`, currently UNRATE + DGS10)
into **Economic Lenses**: a small set of focused, interpretation-rich views of the U.S.
economy, built on a reusable framework.

**Primary goal:** a genuinely useful, bookmarkable tool that helps a reader actually
*understand* the economy — polished enough to double as a credibility piece for Bailey
Analytics, but "useful" wins ties.

**Core idea — a "lens":** a small group of indicators that move together and tell one
story, presented with the context to make sense of them. Each lens answers a question
("Is a recession coming?", "What does it cost to borrow?").

## 2. Scope (v1)

Four lenses:

| Lens | Question it answers | Status |
|---|---|---|
| **Recession Watch** | Is a downturn coming? | Flagship — build first |
| **The Cost of Money** | What does it cost to borrow? | v1 |
| **The Job Market** | Hot or cooling? | v1 |
| **The Cost of Living** | Is inflation beaten? | v1 |

- A **hub** page shows all four lenses **live** on launch (chosen structure: "full hub").
- Each lens has its **own page**.
- Narrative is **hybrid**: hand-written evergreen context + rule-based daily "current read."
- The existing `economic.html` is **retired** (redirect); its series are absorbed into the
  Job Market (unemployment) and Cost of Money (10-year Treasury) lenses.

### Non-goals (explicit YAGNI)

- **No AI/LLM at runtime.** The narrative is deterministic rules + static text. (AI may
  assist *authoring* during development, but is never a runtime dependency.)
- **No backend / server / database.** Stays a static site on GitHub Pages.
- **No build step or framework.** Hand-written HTML/CSS/JS + Chart.js from CDN, like today.
- **No data sources beyond FRED.** No accounts, no intraday/real-time data.

## 3. Information architecture

```
/dashboards/                       → the hub (four live lens tiles)   [was: sample-dashboards listing]
/dashboards/recession-watch.html   → lens page
/dashboards/cost-of-money.html     → lens page
/dashboards/job-market.html        → lens page
/dashboards/cost-of-living.html    → lens page
/dashboards/economic.html          → redirect to /dashboards/         [retired]
```

- Top nav unchanged ("Dashboards" → `/dashboards/`, "About" → `/about.html`).
- The retired `economic.html` becomes a minimal redirect page (`<meta http-equiv="refresh">`
  + canonical link) so any existing inbound links still land sensibly.

## 4. Indicator lineup & FRED series

All free FRED series. The FRED API's `units` transform does most "derived" math for us
(e.g. `units=pc1` = percent change from a year ago); two composite indicators exist as
their own FRED series, so almost nothing is computed by hand.

| Lens | Indicator | FRED series | Transform / note |
|---|---|---|---|
| Recession Watch | Yield curve (10Y–2Y) | `T10Y2Y` | direct composite series |
| | Sahm rule | `SAHMREALTIME` | direct composite series |
| | Initial jobless claims | `ICSA` | weekly level |
| | Unemployment (trend) | `UNRATE` | monthly |
| Cost of Money | Fed funds rate | `FEDFUNDS` | monthly effective |
| | 10-year Treasury | `DGS10` | daily |
| | 2-year Treasury | `DGS2` | daily |
| | 30-yr mortgage | `MORTGAGE30US` | weekly |
| | Yield curve | `T10Y2Y` | shared with Recession Watch |
| Job Market | Unemployment | `UNRATE` | monthly |
| | Nonfarm payrolls | `PAYEMS` | level; MoM change computed (diff) |
| | Job openings (JOLTS) | `JTSJOL` | monthly level |
| | Wage growth | `CES0500000003` | `units=pc1` → YoY % |
| | Labor-force participation | `CIVPART` | monthly % |
| Cost of Living | CPI | `CPIAUCSL` | `units=pc1` → YoY % |
| | Core CPI | `CPILFESL` | `units=pc1` |
| | PCE | `PCEPI` | `units=pc1` |
| | Real wages | derived: wage-growth YoY − CPI YoY (or a FRED real-earnings series) — finalize in impl |

Shared series (e.g. `T10Y2Y`, `UNRATE`, `DGS10`) are fetched **once** and reused.

## 5. Architecture & data flow

Config-driven: one Python config is the single source of truth; the pipeline and the
generated JSON flow from it.

```
lens config (Python)  ── per lens: id, title, accent, indicators[]
                          per indicator: FRED id (+transform), evergreen text, narrative rule(s)
        │
        ▼
scripts/refresh_fred.py (expanded)
  1. collect every unique FRED series across all lenses (dedupe), plus helper
     series not shown directly (e.g. USREC for recession shading)
  2. fetch each once (apply per-series units transform)
  3. compute the few derived values (e.g. payroll MoM change, real wages)
  4. run narrative rules → per-indicator "read" + per-lens synthesis + status
  5. write output files
        │
        ▼
data/lenses/index.json            ← hub: per lens { headline read, status, sparkline, key stats }
data/lenses/recession-watch.json  ← full lens data
data/lenses/cost-of-money.json
data/lenses/job-market.json
data/lenses/cost-of-living.json
```

**Frontend ("framework built once"):**

- `dashboards/lens.js` + `dashboards/lens.css` — shared renderer: charts, scoreboard,
  indicator cards, narrative blocks, range toggle, recession shading. Written once.
- Each lens page is **thin**: a small HTML stub that names its JSON file and calls the
  shared renderer. Adding a lens later = one config entry + one stub.
- `dashboards/index.html` (hub) loads `index.json`, renders the four tiles.

**GitHub Actions:** unchanged cron (daily 06:00 UTC) and structure; it just runs the
expanded script and commits whichever `data/lenses/*.json` files changed.

### Why per-lens JSON + a small hub index (not one big file)
Faster page loads (each page fetches only its own data), and cleaner daily commit diffs.

## 6. Data shapes

**`data/lenses/index.json`** (hub):
```json
{
  "last_updated": "2026-06-03T06:00:00Z",
  "lenses": [
    {
      "id": "recession-watch",
      "title": "Recession Watch",
      "accent": "#F87171",
      "status": "watch",                       // ok | watch | elevated | alert
      "headline_read": "No recession underway — but the warning lights aren't all green.",
      "key_stats": [{"k": "Yield curve", "v": "+0.30"}, {"k": "Sahm", "v": "0.43"}],
      "sparkline": [/* small array of recent values for the tile chart */]
    }
  ]
}
```

**`data/lenses/<lens>.json`** (full lens):
```json
{
  "id": "recession-watch",
  "title": "Recession Watch",
  "accent": "#F87171",
  "last_updated": "2026-06-03T06:00:00Z",
  "status": "watch",
  "headline_read": "No recession underway — but the warning lights aren't all green.",
  "indicators": [
    {
      "id": "yield-curve",
      "title": "Yield Curve · 10-Year minus 2-Year",
      "unit": "%",
      "color": "#F87171",
      "series_id": "T10Y2Y",
      "latest": {"date": "2026-06-02", "value": "0.30"},
      "observations": [{"date": "...", "value": "..."}],
      "context": "The gap between 10-year and 2-year Treasury yields…",   // evergreen, static
      "read": "The curve just un-inverted after the longest inversion on record…", // rule-generated
      "signal_status": "warn"
    }
  ]
}
```

## 7. Narrative engine (hybrid)

Two independent layers per indicator:

1. **Evergreen context** (`context`): authored once, lives in the Python config as a
   string ("what it is / why it matters"). Changes only by deliberate edit.
2. **Rule-based read** (`read`) + **`signal_status`**: pure functions of the latest
   value(s). Inputs → text + status. Examples of rule dimensions:
   - **Threshold crossings:** Sahm rule vs 0.50 trigger; yield curve vs 0.
   - **Regime/state:** inverted vs un-inverted; "just crossed" detection (recent sign change).
   - **Direction of travel:** rising/falling over last N periods.
   - **Level bands:** claims "low / normal / elevated."
   Each rule returns `{ text, status }`. A per-lens **synthesis rule** combines the
   indicator statuses into the lens `headline_read` + overall `status`.

Status vocabulary: `ok` (green) · `watch` (amber) · `elevated` (orange) · `alert` (red).

Rules must degrade gracefully on missing/`"."` FRED values → neutral phrasing, never crash.

## 8. UI / page design

Matches the existing site design language (dark theme tokens: bg `#0A0E14`, panel `#0F172A`,
border `#1E293B`, text `#F8FAFC`, muted `#94A3B8`); each lens carries an accent color.

**Hub (`/dashboards/`):** four tiles. Each: accent eyebrow + status pill, headline read,
sparkline, two key stats, "View lens →".

**Lens page:**
- **Hero:** accent eyebrow, big **synthesized "current read"** sentence, status badge,
  "Updated <date> · N signals."
- **Scoreboard:** compact row of the lens's key signals, each with a color-coded status word.
- **Indicator cards**, each in three parts: **(a)** chart, **(b)** "What it is" (evergreen
  context), **(c)** "The read right now" (rule-based).
- **Footer:** FRED attribution, exact series list, and a "see methodology" note explaining
  the read is generated by a fixed rule set (transparency = credibility).

**Interactivity (v1):**
- **Range toggle (1Y / 5Y / Max) on every chart.**  ← confirmed
- Hover tooltips (native Chart.js).
- **Recession shading** on time-series charts using NBER recession dates (`USREC`,
  fetched as a non-displayed helper series).

**Accessibility / polish:** carry over existing patterns — `prefers-reduced-motion`,
visible focus states, sufficient contrast, responsive down to mobile.

## 9. Error handling & resilience

- **Per-indicator fetch failure must not fail the whole run or destroy good data.** If a
  series fails to fetch, log it and **keep the previous JSON** for that lens (the workflow
  only commits changed files, so a failed fetch never overwrites good data with empty).
- **Stale-data guard:** every page shows "as of <date>"; if data is older than a threshold,
  surface a subtle note rather than presenting it as fresh.
- **Frontend fetch failure:** graceful status message (reuse existing pattern in
  `economic.html`).
- **FRED nulls (`"."`):** filtered in the pipeline (as today); narrative rules handle
  absence with neutral fallback text.

## 10. Testing

The repo currently has no tests; add a minimal **stdlib `unittest`** suite (no new
dependencies, fits the no-build philosophy). Focus on the logic that's easy to get wrong:

- **Narrative rule functions:** given representative values → assert expected `text` +
  `signal_status` (including edge cases: missing values, exactly-at-threshold, sign flips).
- **Derived calcs:** payroll MoM change, real-wage derivation.
- **JSON assembly:** shape/keys of `index.json` and a lens file from fixture inputs.
- **Pipeline dry-run mode:** run against local fixture data with **no network**, to validate
  output end-to-end in CI and locally.

## 11. Build order

Launch state is "all four live" (full hub), but build incrementally to de-risk:

1. **Phase 1 — Framework + Recession Watch end-to-end.** Refactor `refresh_fred.py` to the
   config-driven pipeline; build `lens.js`/`lens.css`; ship Recession Watch page + its JSON.
   Validates the whole architecture on the flagship.
2. **Phase 2 — Add the other three lenses.** Mostly config + evergreen copy + rule sets +
   thin stubs. No new plumbing.
3. **Phase 3 — Hub + cutover.** Build `/dashboards/` hub; retire `economic.html` (redirect);
   nav/polish; verify the daily Action commits all lens files.

## 12. Future (post-v1)

- Optional AI-assisted narrative *polish* with guardrails (kept off the critical path).
- More lenses (e.g. Housing, Markets).
- Indicator lineup tweaks (e.g. add S&P 500 to Cost of Money).
- These are explicitly out of v1 scope.

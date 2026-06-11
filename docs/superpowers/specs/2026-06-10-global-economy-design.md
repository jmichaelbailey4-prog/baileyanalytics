# Global Economy — 7th Dashboard Category — Design

**Date:** 2026-06-10
**Status:** Approved in brainstorm (Michael's calls: 4 lenses incl. trade; move DTWEXBGS from Markets scoreboard, no replacement; US EPU leads Uncertainty with GEPU as banded sanity check). Pending written-spec review.

## Goal

Fill the largest remaining gap against the site's goal — *"executives and board
members should bookmark this site and check it daily to stay informed on
strategic, economic, and geopolitical context."* Every existing category is
US-domestic; this one covers the world: the dollar, global growth, trade &
supply chains, and policy uncertainty. It also closes most of the breadth phase
(see [[exec-dashboard-roadmap]]) — after this and Corporate & Business Health,
the center of gravity shifts to synthesis.

All sources below were **live-verified 2026-06-10** (endpoints, formats, history
depth, stdlib parseability). Three new keyless fetchers; no new keys.

## Category registration

```python
{"id": "global", "title": "Global Economy", "lenses": GLOBAL_LENSES,
 "out": "global", "back": "Global Economy",
 "source_label": "FRED, IMF World Economic Outlook, NY Fed, and policyuncertainty.com",
 "disclaimer": ""}
```

- Data → `data/global/`, pages → `dashboards/global/<lens>.html` + hub `index.html`.
- One line in the home page's `CATEGORIES` array; one entry in Today's Brief's
  category→dir map (`brief.py`) if it has one — verify at plan time.
- CLI flag `--global` (argparse needs `dest="global_econ"` — `global` is a
  Python keyword). New step in `.github/workflows/refresh-fred.yml` (daily),
  under the same `if: success() || failure()` pattern.

## The four lenses

### 1. The Dollar & Currencies (`global-dollar-currencies`) — pure FRED, daily

| Indicator | Series | Role |
|---|---|---|
| Broad Dollar Index | DTWEXBGS | **Lead.** `derive.yoy_pct` → two-sided YoY bands: \|YoY\| <4% ok / 4–8 watch / 8–12 elevated / >12 alert (2022's stress run peaked ~+12% YoY). Both a surging and a sliding dollar raise severity, direction-aware text. |
| Euro | DEXUSEU | Info, YoY read. Quoted USD-per-EUR — phrasing must respect quote direction. |
| Japanese Yen | DEXJPUS | Info, YoY read. Quoted JPY-per-USD (rising = weaker yen). |
| Chinese Yuan | DEXCHUS | Info, YoY read. Quoted CNY-per-USD (rising = weaker yuan). |

**DTWEXBGS moves here from Markets · Asset-Class Scoreboard** (one home per
number — the MORTGAGE30US precedent). The scoreboard keeps five tiles and gains
a footer pointer to this lens. Exact band values verified against full history
percentiles at plan time (applies to all bands in this spec).

### 2. Global Growth (`global-growth`) — IMF WEO (new fetcher) + FRED

| Indicator | Source / key | Role |
|---|---|---|
| World real GDP growth | IMF `G001.NGDP_RPCH.A` | **Lead.** Level bands: ≥3.2 ok / 2.5–3.2 watch / 2.0–2.5 elevated / <2.0 alert (sub-2% ≈ global recession). |
| China real GDP growth | IMF `CHN.NGDP_RPCH.A` | Info. |
| Euro Area real GDP growth | IMF `G163.NGDP_RPCH.A` | Info. (US growth deliberately omitted — covered domestically.) |
| World inflation | IMF `G001.PCPIPCH.A` | Info. |
| Euro Area GDP, quarterly | FRED `CLVMEURSCAB1GQEA19` → `yoy_pct` | Info — the only quarterly pulse available. |

- **Forecast handling:** WEO publishes through 2030. Charts and key stats use
  **actuals only (≤ current year)** so hub deltas never compare against a
  projection; the lens read mentions the next-year IMF forecast in prose
  ("the IMF projects N% for 2027").
- Annual data → the page passes **`defaultRange: "Max"`** (1Y would show one point).
- WEO updates ~April/October — low churn; change-detection already handles it.

### 3. Trade & Supply Chain (`global-trade-supply`) — NY Fed (new fetcher) + FRED

| Indicator | Source / key | Role |
|---|---|---|
| Global Supply Chain Pressure Index | NY Fed GSCPI | **Lead.** Units are σ from historical mean → level bands: <0.5 ok / 0.5–1.5 watch / 1.5–2.5 elevated / ≥2.5 alert (negative = looser than normal, ok). Monthly, 1997→. |
| Trade balance, goods & services | FRED `BOPGSTB` | Info. $M → scaled to $B; phrasing handles the persistent deficit (more/less negative). |
| Import prices | FRED `IR` → `yoy_pct` | YoY band, consumer-cost style (rising import costs = stress; tariff read). |
| China exports | FRED `XTEXVA01CNM667S` → `yoy_pct` | Info — global trade pulse. |

### 4. Uncertainty & Risk (`global-uncertainty`) — policyuncertainty.com (new fetcher) + FRED

The original Geopolitical Risk (GPR) index ships only as binary `.xls` —
unusable with stdlib. Verified substitute: the Baker/Bloom/Davis **Economic
Policy Uncertainty** indices (true xlsx, stdlib-parsed end-to-end in research).

| Indicator | Source | Role |
|---|---|---|
| US Economic Policy Uncertainty | US EPU xlsx (monthly, 1900→, current to May 2026) | **Lead.** Level bands (long-run mean ≈ 100): <120 ok / 120–200 watch / 200–300 elevated / ≥300 alert. |
| Global Economic Policy Uncertainty | GEPU xlsx (monthly, 1997→) | **Banded with the same bands — the sanity check.** Lens badge = worst of the two (`status_max` default). Context notes the ~6-month publication lag honestly. |

- Page footer: **attribution to Baker, Bloom & Davis (policyuncertainty.com)** —
  required by the data's terms — plus a pointer to VIX in Markets · Risk
  Sentiment (VIX stays there; one home per number).

## New fetchers (`scripts/lenses/`)

All keyless, all following the existing fetcher contract (return observations,
raise on failure so the injector keeps prior data — same fault-tolerance as
yahoo/coingecko):

1. **`imf.py`** — IMF SDMX 2.1 API:
   `https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/{KEY}.{INDICATOR}.A?startPeriod=1980&endPeriod=<now+1>`.
   Returns StructureSpecific **XML only** (ignores JSON Accept headers) — parse
   with `xml.etree`: `Series` elements carry `COUNTRY`/`INDICATOR` attributes,
   child `Obs` carry `TIME_PERIOD`/`OBS_VALUE`. One request can batch countries
   (`USA+CHN+G163`). Old `dataservices.imf.org` is dead; DataMapper is
   Akamai-blocked — this is the only working path.
2. **`nyfed.py`** — GSCPI CSV:
   `https://www.newyorkfed.org/medialibrary/research/interactives/data/gscpi/gscpi_interactive_data.csv`
   (the file the official interactive loads). It's a **vintage matrix**: header
   row of Excel serial numbers (one column per vintage), rows are
   `30-Sep-1997`-style dates; **current series = last non-`#N/A` column per
   row**. Send a browser-ish User-Agent. Do NOT use the `.xlsx` download — it's
   secretly binary `.xls`.
3. **`epu.py`** — stdlib xlsx reader (`zipfile` + `xml.etree` + sharedStrings) for:
   - `https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx`
     — **rows newest-first**, final row is a citation string (skip both quirks).
   - `https://www.policyuncertainty.com/media/Global_Policy_Uncertainty_Data.xlsx`
     — ascending, `GEPU_current` column, citation trailer row.

Injection: `_inject_global` in `refresh_lenses.py` after the FRED pass, mirroring
`_inject_crypto`/`_inject_gold`/`_inject_eia`. Indicators carry
`source` ∈ {`imf`, `nyfed`, `epu`} so the FRED pass skips them.

## Cross-cutting

- **Severity model:** standard severity (ok/watch/elevated/alert) — bands above;
  `narrative` gains any missing band-factory variants only if the existing
  `yoy_band`/`yoy_band_two_sided`/level-band helpers can't express them.
- **Markets edit:** remove the `dollar` Indicator from `MARKET_SCOREBOARD`;
  add footer pointer on the scoreboard page. Markets fixtures/tests updated.
- **Thinning/units:** standard `thin_observations`; units are index points, %,
  $B, σ — all expressible with existing `_fmt`/`fmtVal` logic (keep in sync).
- **Monthly/annual labeling:** monthly series label "May 2026"-style (existing
  convention); annual IMF series label the year only.
- **Tests:** TDD per repo norm — fixtures (`imf_sample.xml`, `gscpi_sample.csv`,
  `epu_sample.xlsx` bytes or pre-parsed), fetcher parse tests, narrative band
  tests, build/dry-run integration. `--dry-run` must build the category offline.

## Out of scope (deliberate)

- OECD Composite Leading Indicators — hard-blocked by Cloudflare JS challenge;
  FRED's CLI mirrors are discontinued. Dropped, not deferred.
- GPR index — binary-only formats; EPU is the substitute.
- World Bank API — verified usable but annual with ~18-month lag; strictly
  dominated by IMF WEO for this purpose. Keep in the back pocket for
  country-detail features.
- FX charts beyond the four pairs; emerging-market coverage; commodity FX.

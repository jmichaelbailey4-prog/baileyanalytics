# Energy & Commodities — Design

**Date:** 2026-06-09
**Status:** Brainstorming approved (key forks decided interactively); spec pending user review on return. Implementation may proceed against fixtures on a feature branch per the user's "keep the ball moving" instruction. **No live build or deploy until the user provides an EIA key and approves.**

## Goal

Add a fourth dashboard category, **Energy & Commodities**, that shows the
*physical/operational* economy — what households pay for fuel and power, and how
energy is produced and supplied — using a new data source, the **U.S. Energy
Information Administration (EIA) API**. This is deliberately the most different
category from the existing three (Economy/FRED, Banking/FDIC, Markets): it
surfaces production, inventories, storage, and generation mix, not just
financial-market prices.

This is Phase 1 (breadth) of the larger program. Holistic cross-category
synthesis and predictive models are later phases and are **out of scope** here.

## Vision context (why this, why now)

The owner's north star is a standalone resource covering "all the major things
an executive or board member needs to know." Energy is a core gap: fuel and
power costs hit every household and business, and the energy transition is a
top-of-mind board theme. EIA is the authoritative free source for the physical
data FRED does not carry (production, inventories, generation by fuel).

## Decisions made interactively (approved)

1. **Four lenses**, split granularly: Oil & Fuels · Natural Gas · Electricity &
   the Grid · Commodities & Materials.
2. **Consumer-cost severity** status model: lenses take the household's side —
   rising fuel/power/food costs read as stress.
3. **Sourcing:** lenses 1–3 are EIA-native; lens 4 (Commodities) is FRED (copper,
   food, broad index — EIA does not carry these).

### Autonomous calls (flagged for owner review on return)

- **A.** Natural Gas uses **Henry Hub spot** as the price-severity driver (the
  recognizable benchmark that flows into bills) rather than the residential gas
  price. Alternative: swap to EIA residential natural-gas price (monthly).
- **B.** The Commodities lens uses the **food price index** as its consumer-cost
  severity driver; copper and the broad commodity index are `info` bellwethers.
  Alternative: make the whole Commodities lens neutral/`info`.
- **C.** Consumer-cost YoY severity thresholds are set to **defensible defaults**
  below, to be **calibrated against live data** when the EIA key is available
  (mirrors how the Markets momentum bands were calibrated live).
- **D.** Exact EIA route/facet codes below are my best-known values; they get
  **verified at the live build** (the fixtures make all code fully testable
  offline regardless). The EIA fetcher is structured so a route/facet fix is a
  one-line config change.

## Architecture

The category reuses the existing lens framework end-to-end. New pieces parallel
the Markets multi-source pattern:

- **`scripts/lenses/eia.py`** (new) — the only new network module. Mirrors
  `fred.py`. Fetches an EIA v2 dataset and returns `[{date, value}]` oldest-first
  (same shape FRED returns), so `build.build_lens` consumes it unchanged.
- **`Indicator` gains EIA routing fields** — `eia_route: str = ""`,
  `eia_facets: tuple = ()` (tuple of `(key, value)` pairs, frozen-friendly),
  `eia_freq: str = ""`, `eia_col: str = "value"`. FRED indicators leave these
  empty. `source="eia"` marks EIA indicators; `unique_specs` already skips
  non-FRED indicators, so the FRED pass ignores them.
- **`refresh_energy(dry_run)`** (new, in `refresh_lenses.py`) — mirrors
  `refresh_markets`: fetch the FRED commodities lens via `fetch_all`, inject EIA
  series via `_inject_eia`, compute generation shares, build all four lenses,
  write to `data/energy/`. Additive & fault-tolerant: an EIA failure keeps prior
  data and never blanks the FRED lens or other lenses.
- **`--energy` flag** added to `main`, parallel to `--economic/--banking/--markets`.
- **Pages** under `dashboards/energy/` reuse `lens.js`/`lens.css` (the renderer
  needs no changes). A hub card is added to `dashboards/index.html` and the
  category to `config.CATEGORIES`.
- **Data** written to `data/energy/<lens>.json` + `data/energy/index.json`.

### EIA API shape (v2)

`GET https://api.eia.gov/v2/<route>/data/?api_key=KEY&frequency=<freq>&data[0]=<col>&facets[<f>][]=<val>...&sort[0][column]=period&sort[0][direction]=desc&length=<n>`

Response: `{"response": {"data": [{"period": "2026-06-05", "<col>": 3.21, ...}, ...]}}`.
The fetcher maps each row's `period` → `date` and `<col>` → `value`, drops null
values, and reverses to oldest-first. Errors raise (the caller catches and keeps
prior data).

### Computed generation shares

There is no single EIA "renewables share" series; it is derived. `refresh_energy`
fetches **renewable net generation** and **total net generation** as separate EIA
series, computes `share = renewable / total * 100` per month, and injects the
result under the `renewables-share` indicator's `fetch_key`. Same for the
natural-gas share. This follows the existing `_btc_eth_ratio` precedent in
`refresh_lenses.py` (a derived series injected under an indicator key). A small
pure helper `_pct_share(numerator_obs, denominator_obs)` does the math and is
unit-tested.

## The four lenses

Order of indicators matters: the hub index uses indicator[0] for the sparkline
and the first two for key stats, so each lens leads with its headline
consumer-cost indicator.

### Lens 1 — Oil & Fuels (`energy-oil-fuels`, EIA)

| id | title | EIA route / series | freq | rule | status |
|---|---|---|---|---|---|
| `gasoline` | Retail Gasoline (Regular) | `petroleum/pri/gnd`, series `EMM_EPMR_PTE_NUS_DPG` | weekly | `consumer_cost("Gasoline", 10, 25, 40)` | severity |
| `diesel` | Retail Diesel (On-Highway) | `petroleum/pri/gnd`, series `EMD_EPD2D_PTE_NUS_DPG` | weekly | `consumer_cost("Diesel", 10, 25, 40)` | severity |
| `crude-production` | U.S. Crude Oil Production | `petroleum/sum/sndw`, series `WCRFPUS2` (Mbbl/d) | weekly | `energy_level("U.S. crude production")` | info |
| `crude-stocks` | Crude Oil Inventories (excl. SPR) | `petroleum/stoc/wstk`, series `WCESTUS1` (Mbbl) | weekly | `energy_level("Crude inventories")` | info |

### Lens 2 — Natural Gas (`energy-natural-gas`, EIA)

| id | title | EIA route / series | freq | rule | status |
|---|---|---|---|---|---|
| `henry-hub` | Henry Hub Spot Price | `natural-gas/pri/fut`, series `RNGWHHD` ($/MMBtu) | daily | `consumer_cost("Natural gas", 20, 50, 100)` | severity |
| `gas-storage` | Working Gas in Storage (Lower 48) | `natural-gas/stor/wkly`, series `NW2_EPG0_SWO_R48_BCF` (Bcf) | weekly | `energy_level("Gas in storage")` | info |
| `gas-production` | U.S. Dry Natural Gas Production | `natural-gas/prod/sum`, monthly dry-production series | monthly | `energy_level("Dry gas production")` | info |
| `lng-exports` | U.S. LNG Exports | `natural-gas/move/expc`, monthly LNG-export series | monthly | `energy_level("LNG exports")` | info |

### Lens 3 — Electricity & the Grid (`energy-electricity`, EIA)

| id | title | EIA route / series | freq | rule | status |
|---|---|---|---|---|---|
| `electricity-price` | Retail Electricity Price (Residential) | `electricity/retail-sales`, facets sectorid=RES, stateid=US, col `price` (¢/kWh) | monthly | `consumer_cost("Electricity", 5, 10, 20)` | severity |
| `renewables-share` | Renewables Share of Generation | computed: renewable ÷ total net generation (`electricity/electric-power-operational-data`) | monthly | `generation_share("Renewables")` | info |
| `natgas-share` | Natural-Gas Share of Generation | computed: natural-gas ÷ total net generation | monthly | `generation_share("Natural gas")` | info |
| `net-generation` | Total Net Electricity Generation | `electricity/electric-power-operational-data`, fueltype ALL (GWh) | monthly | `energy_level("Net generation")` | info |

### Lens 4 — Commodities & Materials (`energy-commodities`, FRED)

| id | title | FRED series | rule | status |
|---|---|---|---|---|
| `food-index` | Global Food Price Index | `PFOODINDEXM` | `consumer_cost("Food", 5, 12, 25)` | severity |
| `copper` | Copper ("Dr. Copper") | `PCOPPUSDM` | `energy_level("Copper")` | info |
| `broad-commodities` | Broad Commodity Index | `PALLFNFINDEXM` | `energy_level("Commodities")` | info |

(Gold is deliberately **not** here — it lives in the Markets scoreboard. WTI/Brent
crude prices likewise stay in Markets; Oil & Fuels tells the *supply/consumer*
story instead, avoiding duplicate price charts.)

## Status model

**Consumer-cost severity.** Price indicators carry a verdict; physical indicators
inform but do not.

- **`consumer_cost(label, watch, elevated, alert)`** — a severity rule keyed off
  the trailing-12-month % change (rising = household stress):
  - YoY change `< watch` (incl. falling) → **ok** ("eased"/"stable")
  - `≥ watch` → **watch**, `≥ elevated` → **elevated**, `≥ alert` → **alert**
  - No year-ago baseline → **ok** with a level-only read.
  - Per-indicator thresholds (see tables) because volatility differs (gas swings
    far more than electricity). **Defaults above are first-pass; calibrate live.**
- **`energy_level(label)`** — descriptive `info`: reports the latest level and its
  trailing-12-month direction (rose/fell/little changed). No verdict.
- **`generation_share(label)`** — descriptive `info`: reports the latest share (%)
  and whether it is rising or falling vs. a year ago.

**Aggregation:** `narrative.synthesize` aggregates as usual; `util.status_max`
already ignores any status outside the severity ladder, so `info` indicators do
not affect the lens badge. Each energy lens badge therefore reflects the worst
consumer-cost severity among its price indicators. Energy lenses are **not** in
`NEUTRAL_LENSES`.

**HEADLINES:** add ok/watch/elevated/alert/unknown entries for each of the four
lens ids. Examples (final wording in implementation):
- `energy-oil-fuels`: ok "Fuel costs are stable or easing." … alert "Fuel costs
  are spiking — real pressure on households."
- `energy-electricity`: ok "Power bills are steady." … elevated "Electricity
  prices are climbing well above last year."

## Key handling & fault tolerance

- **`EIA_API_KEY`** — required for the EIA (lenses 1–3) data. Read from the
  environment, mirroring `FRED_API_KEY`. Add as a GitHub Actions secret. The owner
  creates a free key at the EIA site (as they did for CoinGecko).
- **Additive:** if the EIA key is missing or a fetch fails, `_inject_eia` logs a
  warning and falls back to prior data (re-read from the existing
  `data/energy/*.json`), so the FRED commodities lens and any unaffected lenses
  still publish. An EIA failure never aborts the run or blanks data — identical
  philosophy to gold/crypto in Markets.
- No key is ever printed or committed. `.env` stays gitignored.

## Pages

- `dashboards/energy/index.html` — category hub (clone the Markets hub),
  loads `/data/energy/index.json`.
- `dashboards/energy/{oil-fuels,natural-gas,electricity,commodities}.html` —
  one per lens, each a thin `renderLens("/data/energy/<lens>.json", {...})` page
  cloned from a Markets lens page. Footer credits the EIA (lenses 1–3) or FRED
  (lens 4).
- `dashboards/index.html` — add an **Energy & Commodities** hub card + grid that
  loads `/data/energy/index.json`, mirroring the existing markets card. A
  `ENERGY_SLUGS` map translates lens ids → page slugs (e.g.
  `energy-oil-fuels → oil-fuels`).
- The root `index.html` showcase is **out of scope** (deferred until all Phase-1
  categories exist, per prior decision).

## Workflow

Add an `--energy` step to `.github/workflows/refresh-fred.yml` (energy data is
daily/weekly/monthly, fits the daily run), passing `EIA_API_KEY` and
`FRED_API_KEY`. The step runs `python scripts/refresh_lenses.py --energy`.

## Testing

TDD throughout, matching the existing suite. New test files:
- `test_eia.py` — mock `urllib` (like `test_yahoo`/`test_coingecko`); assert the
  fetcher parses `response.data` period/col into oldest-first `[{date,value}]`,
  drops nulls, and builds the correct URL with facets.
- `test_config_energy.py` — four lenses registered, correct ids/sources, EIA
  indicators carry routes, FRED commodities indicators are `source="fred"`,
  category registered in `CATEGORIES`.
- `test_narrative_energy.py` — `consumer_cost` band behavior (ok/watch/elevated/
  alert at representative YoY moves, falling → ok, no-baseline → ok);
  `energy_level` and `generation_share` return `info`; `synthesize` for an energy
  lens ignores `info` and reflects the price severity.
- `test_build_energy.py` — build each lens from a fixture; severity lenses
  aggregate to the price indicators' worst; `_pct_share` computes shares.
- `test_refresh_energy.py` — `--energy --dry-run` builds from fixtures into a temp
  dir (patch `ENERGY_OUT_DIR` so the dry-run never clobbers tracked data, the
  lesson from the Markets dry-run footgun); EIA injection falls back to prior data
  on failure.

Fixtures:
- `energy_sample.json` — a fetched-style dict keyed by `fetch_key` (like
  `markets_sample.json`) so `--dry-run` builds all four lenses offline.
- `eia_sample.json` — a canned raw EIA v2 response for `test_eia.py`.

**Do not run `refresh_lenses.py --dry-run` as a test** outside the patched temp
dir — it overwrites tracked `data/`.

## Out of scope

- Live data build and deploy (needs the EIA key + owner approval).
- Live threshold calibration (done when the key exists).
- Home-page showcase changes; cross-category synthesis; predictive models.
- EV-adoption data (EIA coverage is thin; the generation mix tells the transition
  story without it).

## Risks / notes

- **EIA route/facet accuracy:** the exact v2 routes/series above are best-known
  and verified at live build; the fetcher's config-driven design makes fixes
  trivial and the fixtures keep everything testable offline meanwhile.
- **Mixed frequencies:** EIA series are daily/weekly/monthly; the YoY helper
  (`_value_year_ago`) is already frequency-agnostic (ISO-date comparison), so it
  works across all of them.
- **Generation-share derivation** depends on two EIA series sharing month
  periods; `_pct_share` only emits a point where both exist (same guard as
  `_btc_eth_ratio`).

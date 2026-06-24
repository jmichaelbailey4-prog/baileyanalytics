# Score, explain, and order every lens signal — design

**Date:** 2026-06-24
**Status:** DRAFT — awaiting Michael's sign-off on the audit decisions + the reader copy
**Branch (when approved):** `score-explain-order`

## Problem

Today many indicators render as a gray **info** chip with no good/bad score, and a viewer
can't tell *why* a signal is info when it looks scorable. Three gaps:

1. Some info signals have an honest good/bad reading we're leaving on the table.
2. Where a signal genuinely can't be scored or forecast, we say nothing about why.
3. Lenses can open with an info-only / no-prediction signal at the top, burying the lead.

## Goal (decided with Michael — not re-litigated here)

1. Score everything that can be scored **honestly**.
2. Where a signal can't be scored, show a short note explaining why.
3. Predict everything we reasonably can; where we can't, show a short note explaining why.
   One combined note when both score *and* prediction are absent.
4. Within each lens, order signals so the highest-confidence, most-insightful come first —
   never lead with an info-only / no-prediction signal.

**Honesty bar (the whole point — protects site credibility):** a score must reflect a real
good-or-bad interpretation, not a forced threshold. When in doubt, keep it info with a clear
reason.

---

## Data model — three new `Indicator` fields

`scripts/lenses/config.py`, the frozen `Indicator` dataclass (and `BankingIndicator`, via
defaults — no banking indicator needs either note or non-aggregation):

```python
aggregate: bool = True          # severity counted toward the lens badge? (False = chip only)
no_severity_reason: str = ""    # reader copy: why this carries no good/bad score
no_prediction_reason: str = ""  # reader copy: why this isn't forecast
```

- `aggregate=False` → the indicator still computes and **shows its own severity chip**, but
  its status is excluded from `util.status_max` so it can't double-count a lead that already
  carries the theme's verdict. It still counts as "has severity" for ordering (tier 0/1).
- The two reason strings are **only emitted into the JSON when they apply** (see the matrix),
  so a normal scored+predicted indicator carries neither.

### Two intrinsic classifications (stable, value-independent)

Ordering and note-presence depend on what an indicator *can* do, not today's reading:

- **severity-capable** — its rule can emit `ok/watch/elevated/alert`. Determined by probing the
  rule with a synthetic series (reuse the pattern already in `predictions/roster.py`
  `_is_info_rule`; promote it to a shared `narrative.rule_kind(rule) -> "severity"|"info"|
  "momentum"|"unknown"`). info, momentum (`up/down/flat`), and neutral-lens indicators are
  **not** severity-capable.
- **predictable** — encodes the roster's inclusion rule in **config** so build/ordering can use
  it without importing the predictions package: `config.is_predictable(ind)` = `source in
  {fred,eia,yahoo,fdic,computed,nyfed,epu}` AND not (`eia` with empty `eia_route`) AND not in
  `EXTRA_EXCLUDE`. `roster.build_roster` is refactored to call this same helper (single source
  of truth; IMF and CoinGecko stay out exactly as today).

> A handful of predictable-by-rule indicators may have no *champion* yet (pre-bootstrap, or an
> annual cadence the runner skips). Those show neither a prediction block nor a note — existing
> "degrade silently" behavior. The notes are for the **structural** hold-outs only (below).

---

## The "why absent" matrix (Workstream 2)

| severity-capable | predictable | what renders |
|---|---|---|
| yes | yes | nothing (chip + prediction block) |
| **no** | yes | **"why it isn't scored"** note only |
| yes | **no** | **"why it isn't forecast"** note only |
| **no** | **no** | **one combined** note ("why it isn't scored or forecast") |

Rendered as a single muted `.signal-note` block inside the indicator card, below "The read
right now" (new CSS modeled on `.pred-note`/`.hub-why`). Mirrored into the baked `#baked-read`
fragment (`staticread.py`) for no-JS/crawlers, and into `predict.js`'s slot so the "why no
forecast" note appears exactly where a prediction block would. `build.py` emits the fields;
`lens.js`/`predict.js`/`staticread.py` render them; a tiny shared `note_html(no_sev, no_pred)`
helper (build + JS, kept in sync like `_fmt`/`fmtVal`) builds the combined text.

### Reason templates (reader-facing — REVIEW THESE)

A small reusable set keyed by situation; per-indicator override only where a template misfits.

**Why it isn't scored (`no_severity_reason`):**

| key | copy |
|---|---|
| `NEUTRAL_SCOREBOARD` | "Part of a neutral scoreboard — it shows which way the price is moving, not whether that's good or bad." |
| `NEUTRAL_CRYPTO` | "A structural read on how money is rotating within crypto — not a good-or-bad verdict." |
| `MARKET_PRICE` | "A market price has no inherent good-or-bad level — higher or lower isn't itself better or worse." |
| `PHYSICAL` | "A physical supply-and-demand reading, not a household cost — this lens's verdict comes from the price indicators." |
| `FED_PLUMBING` | "A descriptive level of the monetary plumbing — this lens's verdict is carried by M2 money-supply growth." |
| `RATE_LEVEL` | "A market interest rate has no inherent good-or-bad level — the Cost-of-Money verdict comes from the Fed's policy rate and the rate-expectations spread." *(only if Treasuries kept info — see D1)* |
| `RATE_EXPECTATIONS` | "Whether markets expect cuts or hikes isn't itself good or bad — it's the bond market's forecast, shown for context." |
| `TRADE_DEFICIT` | "The U.S. has run a trade deficit every year since 1976 — the level isn't good or bad on its own; what matters is the trend shown here." |
| `WEALTH_BACKDROP` | "Net worth mostly tracks stock and home prices — a wealth backdrop, not a good-or-bad read on household finances; the saving rate and real income carry that verdict." *(only if net-worth kept info — D4)* |
| `DEMOGRAPHIC_LEVEL` | "This level drifts with demographics — the job-market verdict is carried by unemployment, payrolls, and job openings." *(participation)* |
| `LEVEL_CONTEXT` | "A descriptive level shown for context — neither a high nor a low reading is simply good or bad." *(homeownership, profit-share, HP-share)* |
| `CONTEXT_LEAD` | "Shown for context alongside this lens's lead reading." *(china/euro growth, world-inflation, China exports, proprietors, EA-quarterly, active-listings — bespoke pointer where useful)* |

**Why it isn't forecast (`no_prediction_reason`):**

| key | copy |
|---|---|
| `ANNUAL` | "This series updates only once or twice a year — too few data points to build an honest forecast range. (For world growth, the IMF's own projection is shown in the read above.)" |
| `COMPUTED_SHARE` | "This is computed from other series at refresh time, so there's no single line to forecast directly." |
| `CRYPTO_HISTORY` | "We've only been recording this since the site launched — not yet enough history to forecast honestly." |

---

## Per-indicator audit (Workstream 1 + 3)

Outcome: **a** = promote to scored & aggregating · **b** = score, non-aggregating chip ·
**c** = keep info + note · **keep** = already scored+predicted, unchanged. "pred?" = predictable.
Indicators not listed under a category are **keep** (already scored & predicted).

### Economic
| lens · id | now | pred? | → | note / new rule |
|---|---|---|---|---|
| cost-of-money · treasury-10y | always-`ok` (rule_rate_trend) | yes | **b** *(D1)* | new one-sided `restrictive_rate` band (high = costly); non-aggregating so it doesn't triple-count with Fed funds |
| cost-of-money · treasury-2y | always-`ok` | yes | **b** *(D1)* | same |
| cost-of-money · rate-expectations | info | yes | **c** | `RATE_EXPECTATIONS` |
| job-market · wage-growth | always-`ok` (rule_wage_growth) | yes | **a** *(D2)* | add a low-wage warning band (slowing nominal pay = labor softening) |
| job-market · participation | always-`ok` | yes | **c** *(D2)* | `DEMOGRAPHIC_LEVEL` |
| fiscal-health · interest-cost | info (energy_level) | yes | **c** *(D3)* | "The dollar interest bill rises with the economy; debt-to-GDP and the deficit carry this lens's verdict." (alt: a new computed interest-÷-GDP scored series) |
| fiscal-health · receipts | info (yoy_info) | yes | **a** | `yoy_contraction_band("The federal tax take", 0,-3,-8, verb="is")` — falling receipts = weakening |

### Markets
| lens · id | now | pred? | → | note |
|---|---|---|---|---|
| scoreboard · sp500/oil/gold/btc/eth | momentum (neutral) | yes | **c** | `NEUTRAL_SCOREBOARD` (already carry the market-price disclaimer in predict.js) |
| liquidity · fed-balance-sheet/bank-reserves/reverse-repo | info | yes | **c** | `FED_PLUMBING` |
| crypto-structure · btc-dominance/crypto-rotation/btc-eth-ratio | info (neutral) | **no** | **c** | combined: `NEUTRAL_CRYPTO` + `CRYPTO_HISTORY` |

### Consumer
| lens · id | now | pred? | → | note / new rule |
|---|---|---|---|---|
| spending · auto-sales | info (energy_level) | yes | **a** | new `rule_auto_sales` level band (low SAAR = big-ticket pullback) |
| income-savings · net-worth | info (yoy_info) | yes | **c** *(D4)* | `WEALTH_BACKDROP` |

### Energy
| lens · id | now | pred? | → | note |
|---|---|---|---|---|
| oil-fuels · crude-production, crude-stocks | info | yes | **c** | `PHYSICAL` |
| natural-gas · gas-storage, gas-production, lng-exports | info | yes | **c** | `PHYSICAL` |
| electricity · renewables-share, natgas-share, net-generation | info | **no** | **c** | combined: `PHYSICAL` + `COMPUTED_SHARE` |
| commodities · copper, broad-commodities | info (market_price) | yes | **c** | `MARKET_PRICE` |

### Housing
| lens · id | now | pred? | → | note / new rule |
|---|---|---|---|---|
| home-prices · median-price | info (energy_level) | yes | **b** *(D5)* | derive `yoy_pct` + `yoy_band_two_sided` mirroring Case-Shiller; non-aggregating |
| affordability · debt-service (MDSP) | info (level_points) | yes | **a** | new `rule_mortgage_debt_service` (fixes the inconsistency with Consumer TDSP, which *is* scored) |
| supply-construction · active-listings | info (energy_level) | yes | **c** *(D5)* | `CONTEXT_LEAD` ("months' supply, which adjusts for the sales pace, carries the supply verdict; this is the raw count") |
| rent-shelter · owners-equivalent-rent | info (yoy_info) | yes | **b** *(D5)* | `yoy_band` mirroring rent-CPI; non-aggregating |
| rent-shelter · homeownership | info (level_points) | yes | **c** | `LEVEL_CONTEXT` |

### Global
| lens · id | now | pred? | → | note |
|---|---|---|---|---|
| dollar-currencies · euro/yen/yuan | info (fx_yoy, market_price) | yes | **c** | `MARKET_PRICE` |
| growth · world-growth | severity | **no** | **keep sev** + no-pred note | `ANNUAL` (severity stays; only "why no forecast") |
| growth · china-growth, euro-growth, world-inflation | info | **no** | **c** | combined: `CONTEXT_LEAD` + `ANNUAL` |
| growth · ea-gdp-quarterly | info | yes | **c** *(D5)* | `CONTEXT_LEAD` (offer **b** scored) |
| trade-supply · trade-balance | info | yes | **c** | `TRADE_DEFICIT` |
| trade-supply · china-exports | info | yes | **c** | `CONTEXT_LEAD` (global-demand pulse) |

### Business
| lens · id | now | pred? | → | note / new rule |
|---|---|---|---|---|
| profitability · nonfinancial-profits | info (yoy_info) | yes | **b** *(D5)* | `yoy_contraction_band` mirroring profit-growth; non-aggregating |
| profitability · profit-share | info (level_points) | yes | **c** | `LEVEL_CONTEXT` |
| profitability · proprietors-income | info (yoy_info) | yes | **c** | `CONTEXT_LEAD` (offer **b**) |
| formation · high-propensity | info (yoy_info) | yes | **b** *(D5)* | `yoy_contraction_band` mirroring applications; non-aggregating |
| formation · hp-share | info (level_points) | yes | **c** | `LEVEL_CONTEXT` |

### Banking — no changes (every indicator already severity + aggregating + predicted via baked).

**Workstream 3 conclusion:** the roster already covers ~107 indicators including info ones.
No new predictions are *honestly* addable: the 10 structural hold-outs (IMF annual ×4, EIA
computed shares ×3, crypto-structure ×3) can't earn an empirical 80% band or have no direct
series to fetch — each gets a `no_prediction_reason`. Surfacing verified: `predict.js` is on all
34 lens pages and matches by indicator id, so any rostered+championed indicator surfaces with
no silent gap.

**Counts:** (a) 4 — receipts, wage-growth, auto-sales, MDSP. (b) 6 — treasury-10y/2y,
median-price, OER, nonfinancial-profits, high-propensity. (c) ~31 + notes. New
`no_prediction_reason` on 10. New narrative rules: `restrictive_rate`, `rule_auto_sales`,
`rule_mortgage_debt_service`, a low-wage band on `rule_wage_growth`, plus reuse of existing
factories for the (a)/(b) YoY ones.

---

## Ordering by insight (Workstream 4)

Stable sort of each lens's indicators by tier (preserve authored order within a tier), applied
**once in `build.py`** so every consumer (lens charts, scoreboard, baked-read, and the hub's
`index.json` which reads `indicators[0]`/`[:2]`) stays consistent:

```
tier 0: severity-capable AND predictable
tier 1: severity-capable only
tier 2: predictable only
tier 3: neither            ← never first
```

### Coherence check — VERIFIED SAFE
Every lens's **authored lead is already a top-tier indicator**, so the sort **changes no lens's
lead chart and no hub key-stat** (`indicators[0]`). It only demotes a few *secondary*
info/non-predicted indicators below their scored/predicted siblings:

- **Global › Growth:** lead `world-growth` unchanged; 2nd hub key-stat `china-growth →
  ea-gdp-quarterly` (a quarterly, predicted series — an improvement).
- **Global › Trade & Supply:** lead `gscpi` unchanged; 2nd key-stat `trade-balance →
  import-prices` (scored — an improvement).
- **Housing › Supply & Construction:** lead `months-supply` unchanged; 2nd key-stat
  `active-listings → housing-starts` (scored — an improvement).
- **Fiscal:** body reorder only (`receipts` before `interest-cost`); hub key-stats unchanged.
- **crypto-structure** (all tier 3) and **scoreboard** (all tier 2): stable → leads unchanged
  (BTC-dominance and S&P 500 stay first, honoring the existing hub-readability note).

A test pins each lens's resulting `indicators[0]` id and full order so this stays true as
indicators are added. If Michael prefers `active-listings`/`ea-gdp-quarterly` scored (**b**),
they become tier 0 and stay in place — even fewer changes.

---

## Files touched
- `config.py` — 3 new fields; `is_predictable()`; set `aggregate=False` + reason strings per the audit; a couple of new rule wirings/derives.
- `narrative.py` — `rule_kind()`; new rules (`restrictive_rate`, `rule_auto_sales`,
  `rule_mortgage_debt_service`, low-wage band); reuse factories for (a)/(b).
- `util.py` — no change to `status_max`; build does the aggregate filtering.
- `build.py` — filter non-aggregating statuses before `synthesize`; emit reason fields; sort
  indicators by tier; `note_html` helper; keep `_fmt` in sync.
- `predictions/roster.py` — call `config.is_predictable` (no behavior change).
- `dashboards/lens.js` + `predict.js` + `staticread.py` — render the notes; mirror `note_html`.
- `dashboards/lens.css` — `.signal-note`.
- Tests — `test_build.py` (aggregate filter, ordering pins, note emission), `test_narrative_*`
  (new rules), `test_config_*` (fields), a JS `node:test` for `note_html` parity, `test_predict_*`
  (roster unchanged via `is_predictable`).

## Test & verification plan
- TDD: rule bands, `aggregate` filtering, the ordering pins, the matrix→note logic, `is_predictable`
  parity with the old roster.
- Full suite (`unittest discover`, redirected to a file — never piped) + `node --test`.
- `--dry-run` build, then `git checkout -- .` (dry-run overwrites `data/` + publication surfaces);
  spot-check a lens page renders the note and the order.
- `/code-review`, fix findings, then present for Michael's GO. No push/deploy without it.

---

## Decisions for Michael (batched)

- **D1 — "always-green" Treasuries (10y/2y).** Recommend **b**: a one-sided "restrictive when
  high" chip, non-aggregating (Fed funds still carries the lens). Alt: keep **info** with the
  `RATE_LEVEL` note. (Either way the lens badge is unchanged.)
- **D2 — wage-growth & participation.** Recommend wage-growth **a** (add a low-wage warning so
  "ok" means something) and participation **c** info (demographic level; the lens already has
  three scored leads). Alt: both info, or a falling-participation warn too.
- **D3 — fiscal interest-cost.** Recommend **c** info (the $ bill always rises; debt/GDP + the
  deficit carry the verdict). Alt: build a new computed **interest ÷ GDP** (or ÷ receipts)
  scored series — more honest signal, modestly more work.
- **D4 — household net-worth.** Recommend **c** info (`WEALTH_BACKDROP`). Alt: a one-sided
  "falling = stress" score.
- **D5 — confirm the (b) non-aggregating set** (median-price, owners-equivalent-rent,
  nonfinancial-profits, high-propensity) and the two **info-vs-(b)** borderlines
  (active-listings, ea-gdp-quarterly). Recommend the set as listed; both borderlines **c** info.
- **Reader copy:** all template + new-rule reads above are reader-facing — please review the
  wording (this doc is the place to redline).

## Manual steps (none up front)
No GitHub/secret/workflow changes. Pure code + copy. After merge, the next `refresh-fred` cron
bakes the notes/order into `data/` and the lens pages; predictions are unaffected.

---

## Decisions — RESOLVED 2026-06-24 (Michael)

These override the draft rows above where they differ. Standing guidance Michael gave:
"**score as much as possible without making blatantly bad data**" and "work autonomously —
continue making your best call." (Reader copy still gets his review on the rendered pages
before any merge/deploy.)

- **D1 — Treasuries (10y/2y):** "Score and aggregate if accurate, else info." → **SCORE &
  AGGREGATE** (outcome **a**). Honest within the Cost-of-Money frame (higher rate = costlier
  money; Fed funds already warns at ≥4%). New one-sided ascending `restrictive_rate` factory,
  **ok/watch/elevated (no alert)** so the lens never over-dramatizes a mere rate level.
  Conservative bands: 10y ok<4.5 / watch 4.5–5.5 / elevated ≥5.5; 2y ok<4.0 / watch 4.0–5.0 /
  elevated ≥5.0. Aggregating only ever *raises* the badge (status_max), and the curve being
  expensive is exactly what this lens measures — verified non-embarrassing at today's ~4% levels.
- **D2:** **wage-growth → a** (low-wage warning band); **participation → c** info
  (`DEMOGRAPHIC_LEVEL`). As recommended.
- **D3 — interest-cost:** "Best of option 2 or 3; fall back to 1 only if bad data." → **option 2,
  via interest ÷ federal receipts** (not ÷GDP). Reuses two series already fetched in the economic
  pass (interest-cost + receipts), so it mirrors the existing rate-expectations injection with
  **no new network call**. New computed indicator **`interest-burden`** ("Interest Cost · share
  of federal revenue", scored & aggregating); keep `interest-cost` ($B) as an info companion with
  a note pointing to the burden ratio. Bands: <10% ok / 10–15 watch / 15–20 elevated / ≥20 alert.
  (Option 3's YoY-growth band rejected — it reads "ok" once rates plateau while the bill stays at
  record highs: the honesty trap.)
- **D4/D5 — echoes + borderlines:** "Leaning option 2 (score borderlines too); max scoring
  without blatantly bad data." → score the clean ones, hold the noisy ones:
  - **(b) non-aggregating scored:** median-price, owners-equivalent-rent, nonfinancial-profits,
    high-propensity **+ net-worth** (one-sided "falling = stress") **+ ea-gdp-quarterly**
    (one-sided "falling = weakening"; non-aggregating so one region can't drive the Global Growth
    badge).
  - **(c) keep info (bad-data guardrail):** **active-listings** (raw count distorted by
    Realtor.com coverage growth + seasonality — months-supply is the honest scored measure);
    **proprietors-income** (farm income makes YoY too volatile to score cleanly); **china-exports**
    (Lunar-New-Year/base-effect swings). Each keeps a clear `CONTEXT_LEAD` note.

**Net new scored signals:** treasury-10y, treasury-2y, wage-growth, receipts, auto-sales, MDSP,
interest-burden (computed), median-price, OER, nonfinancial-profits, high-propensity, net-worth,
ea-gdp-quarterly. Everything else genuinely directionless stays info **with a reason note** — the
gray chip now always explains itself.

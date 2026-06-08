# Markets & Financial Conditions — Dashboard Category Design

**Date:** 2026-06-08
**Status:** Approved design, pending implementation plan
**Builds on:** the Economic Lenses framework and the Banking System Health category (which proved the pluggable-source + new-category pattern).

## Overview

A third top-level dashboard category, **Markets & Financial Conditions**, parallel to *Economic Lenses* and *Banking System Health*. It tells two stories: how much stress markets are pricing right now, and how each major asset class — including crypto — is moving. It is the site's first **multi-source-within-one-category** build: two lenses are sourced from FRED (reusing the existing pipeline untouched) and one from a brand-new CoinGecko connector.

Written to `data/markets/`, with pages under `dashboards/markets/`, and added as a third category in the `dashboards/index.html` hub.

### Goals

- Demonstrate genuine multi-source integration (FRED + a new CoinGecko fetcher) in one coherent product.
- Reuse the existing component kit and build pipeline as much as possible; add the **minimum** new surface area.
- Ship incrementally: the category is live and useful after Phase 1, before the new-source lens lands in Phase 2.

### Non-goals

- No per-asset buy/sell recommendations, price targets, or forecasts (see Legal & framing).
- No paid data tiers. FRED needs no key; CoinGecko uses its free, no-key public tier.
- Surfacing Markets on the **home page** showcase is a separate, later decision — out of scope here.

## The three lenses

| Lens (id) | Source | Accent | Content |
|---|---|---|---|
| Risk Sentiment (`market-risk-sentiment`) | FRED | `#FB7185` | VIX, high-yield spread, investment-grade spread, NFCI |
| Asset-Class Scoreboard (`market-scoreboard`) | FRED | `#22D3EE` | S&P 500, WTI oil, gold, trade-weighted dollar, Bitcoin, Ethereum |
| Crypto Market Structure (`crypto-structure`) | CoinGecko + FRED | `#818CF8` | Large-vs-small rotation, BTC dominance, BTC/ETH relative strength |

Accents are tunable one-line in config; the values above are starting points and may collide with other categories' accents (harmless — accent is per-lens).

### Lens A — Risk Sentiment (FRED)

Framing: *"Is the market calm or stressed right now?"* Uses the site's standard red/amber/green status, mapped to stress. Shares no series with any existing lens.

| Indicator | FRED series | Unit | Stress thresholds (calm / watch / stressed) | Context |
|---|---|---|---|---|
| Volatility · VIX | `VIXCLS` | — | `<20` / `20–30` / `>30` | The "fear gauge" — rises when markets are scared |
| High-yield credit spread | `BAMLH0A0HYM2` | % | `<4` / `4–6` / `>6` | Extra yield demanded on junk bonds; widening = stress |
| Investment-grade spread | `BAMLC0A0CM` | % | `<1.5` / `1.5–2.5` / `>2.5` | Same signal for safer corporate debt |
| Financial Conditions Index | `NFCI` | — | `<0` / `0–0.5` / `>0.5` | Chicago Fed's broad gauge; positive = tighter than normal |

Thresholds are first-pass and tunable in `narrative.py`. NFCI is weekly; the rest are daily.

### Lens B — Asset-Class Scoreboard (FRED)

Framing: *"How is each major market doing?"* One indicator per asset class. Uses red/amber/green with a **momentum** convention: up-trend green, down-trend red, flat amber — purely a description of recent direction, never a recommendation. Each row's read states the trailing move factually (e.g. "S&P 500 is up 14% over the past year; near a record high").

| Indicator | FRED series | Asset class | Value format |
|---|---|---|---|
| S&P 500 | `SP500` | Equities | thousands (whole, comma) |
| WTI crude oil | `DCOILWTICO` | Energy | decimal |
| Gold | `XAUUSD` via **Stooq** (FRED dropped its LBMA gold series — returns HTTP 400) | Safe-haven commodity | thousands |
| Trade-weighted dollar | `DTWEXBGS` | Currency | decimal |
| Bitcoin | `CBBTCUSD` | Crypto (large cap) | thousands |
| Ethereum | `CBETHUSD` | Crypto (large cap) | thousands |

**Rates are deliberately omitted** — *Cost of Money* already owns the rate complex (four charts incl. the 10y). This avoids the duplicate-chart problem (the `T10Y2Y` yield-curve chart is currently replicated verbatim across Recession Watch and Cost of Money; we do not want a third such duplication). BTC/ETH are FRED-sourced here specifically to get the long history (`CBBTCUSD` ~2014, `CBETHUSD` ~2016) for free.

### Lens C — Crypto Market Structure (CoinGecko + FRED)

Framing: *"Are the big coins moving differently from the small ones?"* Three single-line charts — all reuse the existing chart component (no new dual-line UI). Status reads are descriptive, not good/bad.

1. **Large-vs-small rotation** (CoinGecko). A single relative-performance line: the small/mid-cap basket indexed to 100 ÷ the large-cap basket indexed to 100, plotted over time. Rising = alts outperforming (risk-on); falling = flight to Bitcoin (risk-off). ~365 days of history at launch, then accumulates daily (see Data accumulation). Status: *Risk-on / Risk-off / Balanced* from the recent trend.
   - **Large-cap basket** = BTC + ETH.
   - **Small/mid-cap basket** = ranks 3–10 of the current top coins by market cap, **excluding stablecoins** (a fixed id set plus a ~$1-price sanity check — stablecoins are top-by-cap but not a "small-cap" signal).
   - Basket value = Σ market caps; each basket indexed to 100 at the window start; recomputed from that day's actual top coins each refresh (always reflects current leaders).
2. **BTC dominance** (CoinGecko `/global`). Current dominance % shown as a key-stat (exact current figure is free); its time series accumulates daily going forward (history starts sparse and fills in). Status: descriptive.
3. **BTC/ETH relative strength** (FRED-derived). `CBBTCUSD ÷ CBETHUSD`, a long-history (~decade) ratio line giving this lens multi-year depth alongside the 1-year rotation chart. Rising = BTC leading; falling = ETH leading. Status: descriptive.

## Sourcing reality (honest constraints)

- **FRED long history applies only to prices.** BTC/ETH *prices* (`CBBTCUSD`, `CBETHUSD`) carry ~a decade of free daily history — used for the Scoreboard rows and the BTC/ETH relative line.
- **FRED cannot source breadth.** It carries only four coins (BTC, ETH, and the unrepresentative Litecoin/BCH) and only their *prices*, no market caps — so the large-vs-small signal is structurally impossible from FRED and must come from CoinGecko.
- **CoinGecko free-tier limits.** Historical total-market-cap and exact-dominance *series* are Pro-only. The free `/coins/{id}/market_chart?days=365` gives a 365-day daily market-cap history per coin, which is sufficient to build the rotation basket from the ground up. Current dominance via `/global` is free.
- **Mitigation for the 365-day cap:** daily refresh appends each day's computed rotation and dominance points to the stored JSON (dedup by date), so both histories grow past one year over time.

## CoinGecko connector (`scripts/lenses/coingecko.py`)

A new fetcher module that parallels `fdic.py` (the only module besides `fred.py`/`fdic.py` that touches the network). Endpoints (all free, no key):

- `GET /coins/markets?vs_currency=usd&order=market_cap_desc&per_page=15&page=1` — current top coins with `id`, `symbol`, `market_cap`. Fetch 15 to leave headroom after dropping stablecoins, then keep the top 10 non-stablecoins.
- `GET /coins/{id}/market_chart?vs_currency=usd&days=365&interval=daily` — per-coin daily market-cap history; called once per basket coin (~10 calls).
- `GET /global` — `data.market_cap_percentage.btc` (dominance) and total market cap.

Operational notes:

- ~12 calls per daily build. Light throttle (a short sleep between calls) and a brief backoff on HTTP 429.
- Stablecoin exclusion: a maintained id set (`tether`, `usd-coin`, `dai`, `first-digital-usd`, `usds`, …) plus a price≈$1 / symbol heuristic as a backstop.
- The module returns plain data structures (date/value lists and the current dominance figure); all interpretation/formatting happens in the build layer, mirroring how `fdic.py` returns rows for `build.py` to shape.

## Build & wiring

### Reused untouched

- `Indicator` / `Lens` dataclasses, `fred.py`, `fetch_all` / `unique_specs` (cross-lens series dedup is free), `build_lens`, `build_index`, `write_outputs`, `write_lens_file` (the unchanged-skip + accumulate-on-change behavior), `lens.js` / `lens.css` single-line chart + scoreboard rendering, `recessions.py`.

### New code

- **`config.py`:** `MARKET_LENSES = [RISK_SENTIMENT, SCOREBOARD]` (FRED `Lens`es) and a `crypto` lens spec for the CoinGecko/FRED lens (its own small shape, since it isn't the standard single-series FRED indicator). A third `CATEGORIES` entry: `{"id": "markets", "title": "Markets & Financial Conditions", "out": "markets", "back": "Markets", "source_label": "FRED (St. Louis Fed) and CoinGecko", "disclaimer": ""}` — empty disclaimer like the economic category (attribution is carried by `source_label`; no advice disclaimer, per the framing note below).
- **`narrative.py`:** `rule_vix`, `rule_credit_spread` (parametrized for HY vs IG thresholds), `rule_financial_conditions` (stress statuses); `rule_market_level` (one parametrized momentum rule reused across all six Scoreboard rows — trailing % change → green/amber/red); `rule_crypto_rotation`, `rule_btc_dominance`, `rule_btc_eth_relative` (descriptive). Add the three new lens ids to `narrative.synthesize`. Status tokens reuse existing CSS classes where they exist; a neutral/descriptive class is added to `lens.css` only if none already fits.
- **`build.py`:** `build_crypto_lens(...)` — parallels `build_banking_lens`; assembles the three crypto chart series (rotation, dominance, BTC/ETH relative) + reads/statuses into the standard lens JSON shape so `lens.js` renders it with the existing component.
- **`refresh_lenses.py`:** generalize the FRED path so it builds **all FRED-sourced category lenses** (economic + markets) in one pass, each written to its own `out` dir; add the CoinGecko-sourced crypto lens build (read-existing → append today → write, for accumulation); add a `--markets` flag parallel to `--economic` / `--banking` (no flag = all).
- **Pages:** `dashboards/markets/index.html` (category overview, mirrors `dashboards/banking/index.html`) + `dashboards/markets/<lens-id>.html` ×3; add the third category card to `dashboards/index.html`.
- **Workflow:** the daily refresh covers markets (FRED lenses + the CoinGecko crypto append) on the daily cadence (market data is daily; NFCI weekly resolves naturally).

## Two-phase implementation

The single spec is implemented as two sequenced phases so the category ships before the new-source work:

- **Phase 1 — FRED Markets (category goes live):** Risk Sentiment + Scoreboard lenses, the FRED-path generalization, category shell + hub card + two pages, narrative rules + tests. After Phase 1, Markets is deployed with two working lenses.
- **Phase 2 — CoinGecko crypto lens (differentiated):** `coingecko.py`, `build_crypto_lens`, the crypto config + accumulation, the third page, refresh wiring, and tests.

## Testing

Follows the existing TDD pattern in `scripts/tests/`, no network (fixtures only):

- Each new narrative rule: threshold → correct status (VIX/spreads/NFCI stress bands; `rule_market_level` momentum green/amber/red and trailing-% computation; crypto rules' descriptive reads).
- CoinGecko rotation computation: stablecoin exclusion, large/small basket split, index-to-100, ratio line — from a fixed fixture payload.
- Accumulation/append logic: appending a new day dedups by date and grows history; an unchanged day is a no-op.
- A build test: the markets category (all three lenses) builds end-to-end from a FRED fixture + a new CoinGecko fixture.

## Legal & framing

General market commentary on a public site falls under the publisher's exclusion, not regulated investment advice — there is no meaningful exposure here, and the site has no standing "not investment advice" requirement. The only guardrails, kept for durability rather than legal necessity: describe **trend/momentum**, issue **no** explicit buy/sell calls or price predictions. (The Banking category's disclaimer addresses a different risk — confidential problem-bank data and solvency claims — and does not apply here.) The category's `disclaimer` field is therefore left empty, matching the economic category; source attribution for FRED and CoinGecko is carried by the standard `source_label` footer.

# Predictions for (nearly) every metric — design

**Status:** design / partial implementation on branch `autonomous-polish-predictions`.
**Author:** Claude (autonomous session, 2026-06-15), for Michael's review.
**Supersedes the V1 rule** in `2026-06-11-predictions-design.md` §2 ("we predict what
can move a badge"). Memory: [[predictions-revisit-neutral-lenses]], [[predictions-project]].

> This is the on-paper brainstorm Michael asked for: intent up front, then every open
> question with options, tradeoffs, and a recommended choice. The **uncontested slice is
> already implemented** on the branch (see §7); the **contested forks are stubbed/flagged**
> and listed in `DECISIONS-PENDING.md`. Nothing here is deployed.

---

## 1. Intent

Today the pipeline predicts **59 of 114** published indicators. The rule that picks them —
*"we predict what can move a badge"* — was a V1 integrity guard. Michael has escalated the
goal: **publish a forward-looking, honestly-graded forecast for nearly every metric on the
site**, not just the badge-drivers. The constraint that must survive intact is the site's
defining promise: **no theater, no overclaiming** — credibility is the product. The design
problem is to reconcile near-universal coverage with that bar.

## 2. The reconciling insight: coverage ≠ scoring

The V1 exclusions conflate two independent questions:

1. **Should we *forecast* this series?** (publish a next-print value + empirical band, then grade it)
2. **Should this series carry a severity *badge*?** (ok/watch/elevated/alert)

These are orthogonal. A series can be **descriptive** (no badge — "info") yet still perfectly
honest to forecast: the Fed balance sheet, crude-oil inventories, household net worth, and the
trade balance are all smooth, well-behaved macro/physical series. We can publish "next month we
expect ≈ X (likely X–Y)" and grade it against the first print **without** claiming it's a risk
signal.

So the resolution to the "info-only indicators" tension is: **predict them, but keep them
descriptive.** This unlocks the bulk of the coverage gap with zero integrity cost and *no* need
for the much larger narrative change of giving every metric a risk read. (That larger change —
"every number gets a scored assessment" — is evaluated and **not recommended** in §6.)

The honesty of doing this rests on machinery that already exists:

- The weekly **tournament** already selects naive/seasonal-naive/drift for low-signal series and
  only crowns a "real" model when it beats the naive guess by a **5% skill margin**
  (`backtest.MIN_SKILL`). A smooth series simply ships the baseline — no false sophistication.
- Bands are **empirical** (10th–90th percentile of that series' own backtest errors), so a
  predictable series gets a tight honest band and a noisy one gets a wide honest band. The band
  *is* the honesty.
- Each graded entry already publishes its **skill vs. the naive guess** per indicator and per
  category. A series we can't beat naive on shows ~0 skill — visibly, not hidden.

The thing we must never do is publish a forecast *dressed as skill we don't have*. The existing
surfaces don't — but they need two small honesty tweaks for descriptive series (§7).

## 3. Current exclusion breakdown (measured, 2026-06-15)

A one-off classification of `config.py` against the roster rules (run during this session)
breaks the 114 down as:

| Reason excluded | Count | Disposition |
|---|---:|---|
| **(rostered today)** | 59 | keep |
| info-only rule — **genuine macro/physical** | 23 | **Tier A: predict now (done)** |
| info-only rule — **market prices** (FX €/¥/¥uan, copper, broad-commodities) | 5 | Tier C: asset-price decision |
| banking (quarterly FDIC) | 9 | Tier B: needs FDIC fetch + viability |
| neutral-lens asset prices (S&P, oil, gold, BTC, ETH) | 5 | Tier C: asset-price decision |
| source = IMF (annual WEO) | 4 | Tier D: infeasible (annual; see §5) |
| source = computed (rate-exp spread, profit-share, hp-share) | 3 | Tier B: predict from injected series |
| EIA computed / no route (generation shares) | 3 | Tier D: derived; low value |
| source = EPU | 2 | Tier D: needs fetch plumbing |
| source = NYFed (GSCPI) | 1 | Tier D: needs fetch plumbing |

**Tier A alone takes coverage from 59 → 82 (72%).** Tier A+B (banking + computed) → ~94 (82%).
Tier C (all market/asset prices) → ~104 (91%). Tier D is the long tail (IMF annual is the one
genuinely infeasible bucket).

### An inconsistency worth naming
The site's current copy says *"Asset prices … are deliberately not predicted — next week's market
move is the one thing honest models can't call."* But the pipeline **already predicts energy fuel
prices** — WTI crude, gasoline, diesel, Henry Hub — under severity rules in the Energy category.
Those are commodity market prices subject to the exact same "can't call next week's move" logic.
So the asset-price line is **already not a clean principle**; it's really "we don't predict the
*markets scoreboard and crypto* specifically." Any decision in Tier C should be made with that
honesty, and the public copy should be reconciled to whatever we choose.

## 4. The crux — should we predict asset/market prices? (Tier C, CONTESTED)

This is the one real fork. It covers the scoreboard (S&P 500, oil, gold, BTC, ETH), crypto
structure, FX (EUR/JPY/CNY), and commodity-price indices (copper, broad commodities).

**Option C1 — Keep them excluded (recommended for now).**
Predict everything that is a macro/physical *quantity*; deliberately do not predict tradeable
*prices* (beyond the energy fuels already shipped, which we either keep or reconsider explicitly).
- *Pros:* preserves the credibility narrative verbatim; keeps the headline accuracy/skill stat
  "clean" (it measures macro forecasting, which we're genuinely good at, not coin-flips); avoids
  the dated-price-target-reads-as-investment-advice risk entirely. Tier A+B already delivers
  ~82% coverage, which honestly satisfies "nearly all" without touching the third rail.
- *Cons:* not *every* number gets a forecast; the FX/commodity lenses stay forecast-less.

**Option C2 — Predict them, segregated as "typical range" envelopes (the honest middle path).**
Publish asset-price forecasts but (a) framed as *volatility envelopes* ("history says next week is
usually within ±X% — we don't call direction"), not point targets; (b) **walled off from the
headline macro accuracy/skill stat** so coin-flips never dilute the macro record; (c) under an
asset-specific disclaimer. The tournament would honestly ship naive/drift and show ~0 skill — which
is itself an *educational* demonstration of market efficiency.
- *Pros:* full coverage; the "0 skill on prices, by design — here's the proof" framing is
  genuinely differentiated and on-brand; consistent with already predicting fuel prices.
- *Cons:* most engineering (segregated grading buckets, distinct UI, distinct copy); a dated public
  ledger of S&P/BTC numbers is screenshot-risk regardless of framing; reverses public copy.

**Option C3 — Predict them exactly like everything else.**
Rejected: mixes coin-flip grades into the headline stat (dilutes the strong macro record) and is
the highest investment-advice-perception risk for the least framing care.

**Recommendation: C1 now, C2 as a fast-follow if Michael wants literal 100% coverage.** C1 keeps
the promise intact and already gets us to "nearly all." If he wants the scoreboard covered, C2 is
the only version that doesn't cost credibility — but it's a real mini-project (segregated stats +
UI + legal copy), not a config flip. **Decision #1 in `DECISIONS-PENDING.md`.**

Mechanically, C is already flag-gated: scoreboard/crypto via `narrative.NEUTRAL_LENSES`; FX +
commodity prices via the new `roster.ASSET_PRICE_LIKE` set. Flipping C on later = empty those two
gates + build the C2 framing.

## 5. Other open questions

**Q2 — Banking (Tier B).** Forecastable, but (a) `predict.py` only fetches FRED/EIA today; banking
uses `fdic.py`, so it needs fetch plumbing; (b) quarterly cadence (season=4) needs `MIN_TRAIN=36`
quarters ≈ 9 years of history — FDIC call-report series have it, but each indicator must be checked.
*Recommendation:* do it as the next increment after sign-off — wire `predict.py` to `fdic.fetch_*`,
gate each series on a history-length check, let the tournament return `None` where too short
(it already degrades silently). Not in the uncontested slice because it touches the fetch layer.

**Q3 — Computed series (Tier B).** rate-expectations spread, profit-share, hp-share are injected by
`refresh_lenses` from other series. Predicting a computed spread is honest; the "why" copy is just
harder. *Recommendation:* include them once `predict.py` can reconstruct the injected series (small
plumbing). Low priority; modest coverage gain.

**Q4 — Non-fetcher sources (Tier D).** IMF WEO is **annual** — the runner already skips annual
(too few backtest origins to earn a band), so IMF is **genuinely infeasible** and should stay
excluded honestly (better than a 1-point-per-year "forecast"). GSCPI (NYFed) and EPU are monthly
and forecastable but need new fetch paths in `predict.py` for marginal coverage. *Recommendation:*
defer; revisit only if a synthesis feature needs them.

**Q5 — Legal / disclaimer framing.** Today: a global "not investment advice" line + the Track
Record's asset-price paragraph.
- For **Tier A descriptive macro forecasts:** the existing global disclaimer is sufficient — these
  are public-data projections, not advice. No new copy required.
- For **Tier C asset prices (if adopted):** add an asset-specific disclaimer co-located with those
  forecasts ("not a price target; not investment advice; past volatility ≠ future") and update the
  Track Record "deliberately not predicted" paragraph to describe the new segregated treatment.
  *Recommendation:* gate any asset-price copy change behind Decision #1; don't pre-write it.

**Q6 — Mechanics / surface load.** `predict.js` already loads `open.json` (53 KB) on every lens
page; +23 entries grows it modestly (one object each). Acceptable. Grading cadence is unchanged
(per-series due dates). The watching/track-record consequence-ranking puts descriptive (info)
predictions last automatically because they imply no badge change.

**Q7 — Headline-stat composition (the one Tier A side effect to decide).** Descriptive series are
smooth, so each scores ~0 *skill* (naive is hard to beat) while still calibrating ~80%. Once graded,
they blend into the Track Record **headline skill** number and drag it toward 0 — understating the
genuine edge on the signal series. *Recommendation:* compute the headline skill/calibration over
**signal (non-descriptive) series only**, and present descriptive forecasts as their own labeled
group + count. This needs `descriptive` plumbed `open.json` → graded ledger → `track-record.json`
aggregation (small, but a presentation choice for Michael). Not implemented here; **Decision #1b**.
On this branch the headline currently includes them (honest but conservative).

## 6. Rejected: "give every metric a scored badge"

The alternative resolution to the info-only tension — convert descriptive series into
severity-scored ones so almost nothing is "info" — is **not recommended**. It would force a risk
verdict onto series that have no natural good/bad direction (Fed balance sheet level, € exchange
rate, generation mix), inventing thresholds to justify a badge. That is exactly the "vibe-coded,
arbitrary" feel the site avoids, and it's a large narrative change for negative integrity value.
The §2 orthogonality split gets the coverage win without it: **predict descriptively, badge only
what genuinely has a safe/stressed reading.**

## 7. What's implemented on this branch

> **Decision (Michael, 2026-06-15): predict everything reachable, even neutral / info-only, and
> split the edge stat (#1b).** So the branch now goes past the Tier A slice below to the honest
> full-coverage form: market prices are predicted too, flagged so they carry a disclaimer and stay
> out of the headline edge number. Final state:
>
> - **Roster 59 → 92.** Lifted the neutral-lens skip and the asset-price exclusion, and allowed
>   `source="yahoo"`. Now predicted: all info macro (23), the **scoreboard** (S&P, oil, gold, BTC,
>   ETH), **FX** (€/¥/¥uan), **commodities** (copper, broad). Each entry carries two flags:
>   `descriptive` (no badge: info rule OR neutral lens) and `market_price` (a tradeable price —
>   scoreboard via its neutral lens, FX/commodity via a `market_price` field on the config
>   Indicator so the flag travels with the series, per the post-review fix).
> - **`predict.py`/`runner.py`** fetch Yahoo gold and stamp `descriptive`+`market_price` onto each
>   open/graded entry.
> - **Edge-stat split (#1b)** in `ledger.py`: skill / direction / status computed over **signal**
>   (non-descriptive) rows; calibration + graded span all; new `coverage` count. `track-record.js`
>   shows skill "pending" until a signal series grades and renders null edge cells as "—".
> - **Surfaces:** `predict.js` suppresses the badge clause for descriptive forecasts and adds a
>   *market-price* disclaimer note; `track-record.js` open-list never shows a move badge for a
>   descriptive forecast; the Track Record "deliberately not predicted" paragraph + skill note are
>   rewritten to describe the new treatment honestly.
> - **Still out (fetch plumbing / infeasible, not integrity):** banking (FDIC), computed spreads,
>   crypto-structure (CoinGecko + accumulated history — not in `config.CATEGORIES`), IMF (annual),
>   GSCPI/EPU. Mostly shipped 2026-06-16 — see the increment note below (only IMF +
>   crypto-structure remain out).
>
> The original Tier-A-only writeup below is kept for the reasoning; the integrity argument in §2
> (coverage ≠ scoring; empirical bands; honest 0-skill on prices) is exactly what makes predicting
> the scoreboard non-theater.

### Baked-history increment — DEPLOYED 2026-06-16 (roster 92 → 107)

The deferred Tier-B (banking 9 + computed 3) and Tier-D-fetchable (GSCPI + 2 EPU) items
shipped — **not** via the assumed new FDIC/EIA fetch path (§5 Q2/Q3), but by reading each
indicator's **already-baked** lens-JSON observation history. The pipeline already bakes full
depth into `data/<out>/<lens>.json` `indicators[].observations` (banking = 81 quarters back to
2006), so no fetcher was re-implemented:

- `roster.py`: `BAKED_SOURCES = (fdic, computed, nyfed, epu)` joins `DIRECT_SOURCES`; the
  banking-category skip is removed; each baked entry carries a `baked` flag. Banking is
  badge-driving **signal** (`descriptive=False`).
- `runner._baked_history` reads the lens JSON (degrades to `[]` on a missing/locked file, like
  `refresh_lenses._prior_obs` — kept local so the lightweight predictions package needn't import
  the heavy `refresh_lenses` module). `_prepared_series` **skips `ind.derive` for baked entries**
  (the baked obs are already post-derive/post-thin — the double-derive trap), and banking's
  `BankingIndicator` (which has no `series_id`/`derive`/`market_price`) is read via `getattr`.
- Quarterly grading verified end-to-end: `next_period` floors a Q1 (2026-03-31) print to a
  `2026-06-01` target, and `grade.match_actual` (first obs ≥ target) matches the real Q2 print
  (2026-06-30) and never the prior one.
- **Still out (correctly, not integrity):** IMF (annual — too few backtest origins to earn an
  empirical 80% band) and crypto-structure (short baked history + outside `config.CATEGORIES`).
- FF-merged `534eb9b` to main, Pages-deployed, 640 tests green; extensive /code-review found no
  bugs. No data re-baked — coverage activates on the next CI tournament/daily run.

### (original) uncontested slice — Tier A

1. **`scripts/predictions/roster.py`** — the blanket info-only exclusion is removed; info-only
   FRED/EIA series in non-banking, non-neutral lenses are now rostered. A new documented
   `ASSET_PRICE_LIKE` set keeps the 5 market-price info series (FX + copper + broad-commodities)
   excluded **pending Decision #1** (one-line flip to enable). `RosterEntry` gains a
   `descriptive` flag (`= _is_info_rule(rule)`) so downstream can label info forecasts.
   Result: roster 59 → **82**.
2. **`dashboards/predict.js`** — `statusPhrase()` now suppresses the "would tip/keep this signal"
   badge clause for **descriptive (info)** predictions, so a Fed-balance-sheet forecast reads
   "Next print: we expect ≈ X (likely X–Y)" with no fake badge implication.
3. **Tests** — `test_predict_roster.py` updated to the new contract: info-only macro series are
   included; FX/commodity-price (`ASSET_PRICE_LIKE`) and neutral lenses and banking stay excluded;
   roster size assertion widened; added a positive case (an info macro series is rostered) and a
   negative case (an asset-price-like series is not).

**Not implemented (awaiting sign-off):** Tier C (asset prices — flag-gated), Tier B (banking +
computed — needs fetch plumbing), Tier D, any legal-copy change, and the "scored-everything"
narrative change (rejected). No prediction data is re-baked here; the expanded roster takes effect
on the next scheduled tournament/daily run after merge.

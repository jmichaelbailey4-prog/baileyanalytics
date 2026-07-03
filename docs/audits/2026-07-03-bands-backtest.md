# Severity-band backtest & data-science prototypes (Pass 9, 2026-07-03)

Method: the **exact production rules** (imported from `lenses.config`) evaluated by prefix at each
month-end over full FRED history (fetch limit 100k, cached), scored against NBER recession dating
(USREC). Diffusion/percentile/lead-lag/logit prototypes run on the same data. Script: session
scratchpad `backtest_bands.py` (reproducible; ~20 FRED calls; re-run before any band change —
this run is the governance baseline the Pass 8 recommendation refers to).

## 1. How the current bands would have behaved historically

"Warned" = status ≥ elevated in the 12 months **before** an NBER start (rules capped at watch can never warn by this bar — marked †).
"FA months" = elevated+ months outside recessions with no recession within 18m (for **lagging** indicators this mostly counts post-crisis persistence, not error — marked ‡).

| Signal (rule) | Since | Warned | Elev+ share | FA months | Reading |
|---|---|---|---|---|---|
| Yield curve | 1977 | 5/6 | 16% | 31 | The flagship earns its lead spot (2020 miss is month-end sampling of the brief Aug-2019 inversion) |
| Payrolls | 1960 | 6/9 | 18% | 50 | Solid coincident-to-leading |
| Months of new-home supply | 1964 | 5/8 | 16% | 31 | Genuinely leading — the two-sided housing model is empirically earned |
| NFCI | 1972 | 4/7 | 17% | 14 | Excellent modern discrimination; pre-1984 regime ran structurally tight |
| CPI YoY | 1960 | 6/9 | 32% | 112 | Inflation precedes recessions but also runs hot in expansions — bands are a cost gauge, not a recession call (correct framing on site) |
| Sahm rule | 1960 | 3/9 | 22% | 94‡ | Confirms rather than predicts — by design (real-time recession dating); site copy already frames it as "recession already underway" ✓ |
| VIX | 1990 | 1/4 | 8% | 19 | Spikes at, not before — a nowcast; fine for a *conditions* lens |
| Jobless claims | 1990 | 3/4 | **68%** | 228 | **Regime-anchored bands**: 300k was normal for the 1990s–2000s; the 250/300k lines are calibrated to the post-2015 low-claims regime. Fine for today's display; historically they'd have read healthy decades as "elevated". Evidence for percentile context (§3) |
| Mortgage rate | 1972 | 6/7 | **62%** | 254 | Same class: >6.5% was normal 1973–2002. BAND_WHY already says "by recent standards" — honest, keep |
| Card delinquency | 1991 | 2/3 | 45% | 44‡ | 4–5% was the 1990s norm; post-2010 deleveraging moved it. Lagging ‡ |
| Mortgage delinquency | 1991 | 0/3 | 25% | 30‡ | Purely lagging (peaks 2010); site never claims otherwise |
| Business delinquency | 1988 | 2/4 | 31% | 32‡ | Mildly lagging |
| Lending standards | 1990 | 2/4 | 23% | 16 | Good modern signal (fired 1990, 2001, 2008, 2020, 2023) |
| Baa spread | 1960 | 2/9 | 25% | 137 | Credit spreads honestly false-alarm (2011–16 energy/euro scares) — bands fine, expectations set correctly |
| Sentiment | 1960 | 2/9 | 18% | 47 | Mood ≠ timing; fine as a consumer lens |
| M2 YoY | 1961 | 2/8 | 14% | 91 | The 1970s ran >10% chronically; two-sided bands are 2020s-framed — acceptable, documented |
| Saving rate | 1960 | 1/9 | 5% | 17 | Structural-cushion gauge, not a timer — correct framing |
| Debt service | 1980 | 1/2 | 38% | 20 | Level gauge; 80s structurally high |
| Unemployment trend† | 1960 | († watch-cap) | — | — | Fires at/after starts as designed (Sahm-style) |
| Fed funds† | 1960 | († watch-cap) | — | — | Policy-stance flag, not a signal |
| Debt/GDP | 1967 | 0/8 | 10% | 17 | Solvency gauge, not cyclical — correct framing |
| Inflation expectations | 1979 | 3/6 | 20% | 35 | Decent |

**Overall verdict:** the framework is honest about what it is — a *conditions* board, not a recession
timer — and the leading pieces (curve, supply, payrolls, NFCI, standards) genuinely led. Two rules
(claims, mortgage rate) carry regime-anchored levels; both already hedge with "recent standards"
language, and the durable fix is percentile context (§3), not band surgery.

## 2. Alert-tier evidence (P2-02: lenses that today cap at "elevated")

| Proposed edge | Fired (months/quarters) | Years | Verdict |
|---|---|---|---|
| VIX ≥ 40 | 11 months / 36y | 1998, 2008–09, 2011, 2020 | **Clean crisis discrimination — adopt** |
| VIX ≥ 35 | 16 months | + 1997, 2002 | Looser; prefer 40 |
| NFCI ≥ 1.0 | 87 months (mostly pre-1984) | modern era: 2008–09 only | **Adopt** (modern-era clean; the 1970s were structurally tight, disclosed in why-copy) |
| Noncurrent ≥ 3.0 | 18 quarters | 2009Q1–2013Q2 only | **Adopt** |
| Charge-offs ≥ 2.0 | 7 quarters | 2009Q2–2010Q4 only | **Adopt** |
| ROA ≤ 0 | (2009 industry losses) | definitionally crisis | **Adopt** |
| Claims ≥ 400k | 106 months incl. 1990–96, 2003–05 | too common | **Reject** — levels drift; keep watch/elevated only |
| Baa ≥ 3.5 (existing) | 18 months: 1982, 2002, 2008–09, 2016 | validates the existing alert | Keep |
| HY ≥ 8 / IG ≥ 3.5 | not API-backtestable (rolling 3y window) | 2008/2020 peaks are public record | **Adopt with prose-only justification** (no numeric claims beyond public peaks) |

## 3. Percentile context (prototype output, today vs full history)

Sentiment **0.0th** percentile (all-time record low) · months' supply **97.2th** · debt/GDP **97.9th** ·
saving rate **4.6th** · jobless claims **7.8th** · CPI YoY 71.8th · inflation expectations 86.7th ·
lending standards 64.8th · VIX 43.3rd · mortgage rate 36.9th. — One line per indicator, computed
from already-fetched history at build time; instantly "smarter-feeling", zero black box. **Caveat
found while prototyping:** percentile depth = fetch `limit`, and several limits are 20y; honest
"since YYYY" labels or raised limits required. **Build-next candidate.**

## 4. Cross-signal diffusion index (share of 22 signals at elevated+, monthly, 1990→)

Peaks: 2008-07/2009-01 **64%**; 2001-03 33%; 2008-01 41%; 2020-03 23% (COVID outran monthly badges);
quiet 2019-12 **0%**. Today (2026-06): watch+ 50%, elevated+ **23%** — breadth comparable to mid-2007
(55%/27%). Explainable in one sentence ("how much of the board is off-green"), fully recomputable,
and it would have said something true and useful at every cycle turn. **Strong candidate as the
site's first composite ("Stress Breadth").**

## 5. Yield-curve recession probability (logit prototype; statsmodels Probit blocked by a local scipy conflict — numpy IRLS used)

n=589 monthly obs (1977→), P(NBER recession within 12m | spread): AUC 0.72 in-sample.
Today (+0.35): **26%**. Curve at 0: 33%; at −1.0: 57%. Honest but modest discrimination on 10y−2y;
the literature's stronger variant uses 10y−3m (T10Y3M). **Next-phase candidate** — needs careful
"model-implied, in-sample" copy; do not ship as a headline number without out-of-sample framing.

## 6. Lead–lag on relationship-map edges (quarterly, Pearson r at lags)

- Lending standards → business-loan delinquency: **r=0.61 at +5 quarters** (standards lead by ~5Q; r decays either side). Empirically supports the map's credit edge — quotable, honestly correlational.
- Yield curve ↔ unemployment (levels): peak r at −1..0 quarters — levels-on-levels is confounded by the Fed's reaction; a change-transform is needed before this becomes a public number. Not shippable as-is.
- Affordability → home-price YoY: **not computable — FRED serves only ~14 months of FIXHAI** (see finding P9-01).

## 7. Found while prototyping — P9-01 (Credibility/High): FIXHAI is a rolling ~1-year window

FRED serves 14 observations of FIXHAI (12 non-null), and has since the housing category launched
(verified across all 9 commits touching the baked file — it never had depth). Consequences on the
live site: the affordability lead chart's "5Y/Max" ranges show ~1 year (undisclosed — the ICE
spreads got a disclosure note for exactly this class of limitation); the lead indicator silently
has **no prediction** (12 points < MIN_TRAIN=36); percentile/backtest impossible from FRED.
Fixes: disclosure note in the indicator context (mirrors ICE wording) + **windowed-series
accumulation** (merge prior baked observations on refresh so published history can only grow —
also applied to the ICE HY/IG spreads, which have the same forward-loss exposure; the crypto
`_crypto_history.json` already proved this pattern). A computed affordability proxy
(payment-on-median-home vs income) is the deeper next-phase alternative.

## 8. Tournament & ledger spot-checks

`models.json`: champions across 107 series — baselines dominate (naive/seasonal-naive/drift),
statsmodels families win only where structure exists; consistent with the 5% skill gate doing its
job (no overfit champions). Ledger: 110 graded, realized band coverage 81% vs stated ~80% ✓;
revision footnotes present — but see P3-01: for daily-resampled series some "revisions" were
partial-week grading artifacts, fixed this audit.

## Verdicts (build now / next phase / reject)

- **Build now:** alert tiers per §2 (this branch); windowed-series accumulation (this branch).
- **Next phase (designed, evidence-backed):** percentile context lines (§3); Stress Breadth diffusion index (§4); backtest-as-content ("how this framework read past cycles" methodology section — §1's table is publishable almost verbatim).
- **Later / conditional:** yield-curve probability (switch to 10y−3m, add out-of-sample validation first); lead-lag numbers on more map edges (publish only edges with clean transforms).
- **Reject:** claims/mortgage-rate band surgery (percentile context is the durable fix); PCA/factor extraction (tried nothing — the diffusion index answers the same reader question explainably; PCA loadings are a black box by this site's standards).

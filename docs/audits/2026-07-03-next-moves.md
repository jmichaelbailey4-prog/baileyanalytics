# What to build next — strategic memo (2026-07-03 audit, Pass 12)

Grounding: the full-site audit (`2026-07-03-full-audit.md`), the band backtest
(`2026-07-03-bands-backtest.md`), the 26-seat panel's return/subscribe verdicts, and the roadmap
memories (weekly synthesis, per-lens og cards, calibration view, slicer, deeper sources, accounts).

**Where the site stands.** The product is in genuinely strong shape: every sampled number traced
to its primary source exactly (16/16 across four APIs), deployed reality is byte-identical to the
repo, the honesty architecture (tier-gated relationships, self-grounded whys, graded predictions,
generated methodology) survives adversarial reading, and the panel's reader seats mostly came back
"would return". The audit's fixes closed the credibility edges a rival would have dunked on
(record-low copy, unreachable alerts, partial-week grading, the FIXHAI window). What the site
still lacks is not polish — it's **historical depth behind the badges** and **reach**.

---

## Quick wins (≤ a day each)

1. **Percentile context lines** — "Today's reading is the 97th percentile since 1963" under each
   scored indicator. Prototyped in the backtest (sentiment 0.0th, months-supply 97.2nd, debt/GDP
   97.9th — instantly quotable). Honest, zero black box, and it neutralizes the two
   regime-anchored rules (claims, mortgage rate) that level-bands can't fix. *Dependencies:*
   raise fetch limits on ~10 series; an honest "since YYYY" label per series; one new baked field
   + a one-line render in lens.js/staticread. *Evidence:* backtest §3. **Do this first.**
2. **Auto-loan rate (TERMCBAUTO48NS) + US food-at-home CPI** — the two indicators real-people
   seats reached for and missed (factory worker's car loan; single parent's groceries). One
   config entry each. *Evidence:* Pass 6/7.
3. **Core PCE alongside PCE** — the Fed's actual target measure; one config line. *Evidence:* Pass 6.
4. **Per-lens og:image cards** — the advisor/growth-PM convergence: people share one chart, and
   lens links currently unfurl with the generic site card. `ogcard.py` already renders cards;
   add a per-lens variant in the `--brief` pass. *Evidence:* Pass 7 (two seats + roadmap memory).

## Big bets (a phase each, in recommended order)

1. **"How this framework read past cycles" — backtest-as-content.** Bake the Pass 9 backtest into
   a public methodology section: per signal, how often each badge state fired since ~1960/1990 and
   what it did around recessions — the table in backtest §1 is publishable almost verbatim, and
   the rerun script becomes the band-governance tool (Pass 8 recommendation). This is the answer
   to the rival's last remaining dunk ("no history behind the badges") and converts the site's
   biggest hidden asset — disciplined rules — into its loudest credibility proof. Medium effort:
   a generator + one page + links from methodology/track record.
2. **Stress Breadth index (first composite).** "Share of the board off-green" — explainable in one
   sentence, fully recomputable, and it would have peaked at 64% in 2008-09, read 0% in Dec 2019,
   and reads ~23% elevated+ today (≈ mid-2007 breadth — a genuinely arresting fact). Ships as one
   number + a history chart on the brief/home. The honest gateway composite before any model.
   *Evidence:* backtest §4. Medium effort; pairs naturally with big bet #1.
3. **Weekly written synthesis** (roadmap's standing differentiator): a Sunday piece assembled from
   the week's transitions/movers/whys, human-reviewed before send. The digest already proves the
   channel; this deepens it. Effort: editorial pipeline + Michael's weekly 20 minutes.
4. **Recession-probability model** — only after #1/#2: switch to 10y−3m (T10Y3M), add
   out-of-sample validation, ship with "model-implied" framing. The 10y−2y logit's in-sample AUC
   of 0.72 is honest but not yet shippable as a headline number. *Evidence:* backtest §5.

## Explicitly deferred / rejected

- **PCA/factor composites** — rejected: unexplainable loadings; the diffusion index answers the
  same reader question transparently (backtest verdicts).
- **Claims/mortgage-rate band surgery** — rejected in favor of percentile context (backtest §1).
- **Accounts/sync/push/native** — still cost-deferred until traction (unchanged from roadmap).
- **Computed affordability proxy** (payment-on-median-home ÷ income) — designed candidate if the
  FIXHAI window ever becomes untenable; accumulation buys time (fixed@70f9c07).

## Audience & retention notes (from the panel)

The retention loop is now complete end-to-end (SEO entry → lens page → digest pointer → daily
email → archive permalinks → PWA). The two remaining reach levers, in order of leverage: per-lens
og cards (quick win #4) and the weekly synthesis (big bet #3). Monetization remains premature —
credibility assets (track record + backtest-as-content) are the compounding investment; revisit
sponsorship/consulting funnels once the digest list has real numbers to show.

## Top recommendation

**Ship percentile context now, then build "How this framework read past cycles" + the Stress
Breadth index as one "History" phase.** The argument: the audit proved the site's numbers and
honesty are already trustworthy; the panel's only unanswered attack and the readers' only
unanswered question are the same question — *"compared to what?"* Historical context answers it
on every chart (percentiles), for the whole board (breadth index), and for the framework itself
(the public backtest) — all three are validated by running code from this audit, all three are
explainable in one sentence, and together they turn the site's discipline into its marketing.

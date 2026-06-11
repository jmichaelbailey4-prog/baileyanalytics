# Predictions & Track Record — design spec (2026-06-11)

The prediction phase: for every badge-driving indicator, publish what we expect
the next print to be — before it exists — then grade ourselves in public when
it lands. The **track record is the product**; the models are plumbing. Every
prediction carries a plain-English "why" (no black box, per `about.html`), and
the ledger is committed to a public git repo, so `made_at < graded_at` is
independently verifiable from commit history — git is the notary.

All decisions below were settled with Michael 2026-06-11.

## 1. The prediction primitive

**Value + interval, one step ahead.** Per indicator: a point estimate for the
next print, an empirical 80% band, and a due date — on the *displayed* series
(post-`derive`, display units: CPI means YoY %, not the raw index). Reasons:

- It is the only primitive that grades honestly on every print.
- The exec-facing layers derive from it for free: direction is the sign of
  (point − last actual); the badge claim ("would keep Cost of Living
  elevated") is the existing `narrative` rule run on history + the predicted
  point — no second model to defend, and mechanically consistent with how
  badges are set today.
- `horizon` is a first-class field. V1 ships only `"next-print"`; a ~3-month
  horizon is the planned expansion and must slot in without schema migration.

## 2. Roster — what gets predicted

**Rule: we predict what can move a badge.** An indicator is rostered iff:

1. `source` is `fred` or `eia` (real fetchable history; the injected/computed
   series — crypto dominance, generation shares, rate-expectations spread,
   GSCPI, EPU, IMF — are deferred);
2. its rule can emit severity statuses (info-only indicators such as the Fed
   balance sheet trio are excluded — they don't drive badges);
3. its lens is not neutral (`narrative.NEUTRAL_LENSES`): the Asset-Class
   Scoreboard and crypto lenses are **excluded by principle** — asset prices
   are near-random-walks (the tournament would publish contentless "≈ today"
   forecasts forever, diluting the headline accuracy stat) and a dated public
   ledger of stock/crypto price targets reads as investment advice, against
   the footer disclosure. Same logic as why those lenses carry no badge.
   (Flagged for a later revisit as an "honest educational exhibit.")
4. its category is not Banking (FDIC quarterly — deferred so the young record
   isn't waiting months for grades).

Estimated ~70 indicators across the eight categories. The roster lives in
`scripts/predictions/roster.py`, **derived from `lenses.config` by the rules
above plus an explicit, commented exclusion list** — auditable, and a new lens
indicator joins the roster automatically unless excluded.

**Cadence and target:**

- Weekly/monthly/quarterly series → the next observation period.
- **Daily series → next Friday's value**, graded weekly ("next print" daily
  would mean predicting tomorrow ≈ today every day: churn, no insight).
- Cadence is inferred from observation spacing at tournament time and stored
  in `models.json`; the roster may override explicitly.
- Due dates are **approximate by design** ("due ~Jul 15", "due this week"),
  computed from per-cadence release-lag heuristics (per-indicator override in
  the roster). We know FRED observation dates, not BLS press calendars —
  exact dates would be fake day-precision, against house convention.

Grading tempo: ~8–10 weekly grades, ~40 monthly, a handful quarterly — first
grades within days of launch, roughly 75–90 per month after.

## 3. Grading — first print, frozen forever

- **First-observed grading.** A prediction targets "the next print," so it is
  graded against the value as our daily refresh *first sees it* for that
  `target_period`. The grade is then **frozen — never recomputed**. A track
  record that silently improves as revisions land is the opposite of the
  brand.
- **Revision footnote.** On subsequent runs, recently graded entries (a
  bounded look-back of a few observations) are re-checked; if the source value
  moved, `revised_to` is recorded. The footnote never alters `hit`. (Training
  already uses revised history for free — full-history fetches return revised
  data; the footnote is purely the honesty layer.)
- **Methodology honesty (display copy on the track-record page):** models
  train on revised history but predict first prints (irreducible, matters for
  revision-heavy series like payrolls); "first observed" means "first seen by
  our daily cron," which can trail the true first print by hours.
- **Grade fields:** `hit` (actual inside the 80% band), `abs_error`,
  `direction_hit` (sign of predicted move matches sign of actual move,
  relative to the last actual known at `made_at`), `status_hit`
  (`implied_status` equals the status the rule assigns once the actual
  lands), `naive_error` (what the naive guess would have missed by — stored
  per grade so the skill stat is recomputable from the ledger by anyone).
- **Edge cases, resolved by the frozen-forever principle:** cron skip
  delivering two prints → grade only the stated `target_period`, then predict
  the genuinely-next print (never write a prediction for a print that already
  exists); stale series → the open prediction stays open, never auto-failed;
  a second grading attempt is a no-op.

## 4. Model toolbox and tournament

Pinned in `baileyanalytics/requirements.txt`: `numpy`, `pandas`,
`statsmodels` (scikit-learn joins in tier 3). The existing stdlib lens
pipeline is not refactored; predictions are built alongside.

**Toolbox (tiers 1–2), each explainable in one sentence:**

| Model | One-sentence explanation skeleton |
|---|---|
| naive | "we expect roughly the last value — this series rarely rewards cleverness" |
| seasonal-naive | "we expect roughly what this series did a year ago this {period}" |
| drift | "we project the series' long-run average step from today's level" |
| ETS (Holt-Winters, damped) | "projects the recent level and trend, with the usual seasonal pattern for {period}" |
| SARIMA (small fixed order grid) | "projects the recent trend and momentum, adjusted for this series' typical reversion" |
| Theta | "blends the series' long-run trend line with its recent level" |

The published `why` is the model-family skeleton plus simple series
diagnostics (e.g. "has risen three straight months") from a small copy bank in
`scripts/predictions/explain.py`.

**Tournament (weekly):** per indicator, fetch **full history live** from
FRED/EIA (published thinning costs nothing — training never reads baked
JSON), apply the indicator's `derive`, then **rolling-origin backtesting**:
stand at many past dates, fit each model only on data strictly before the
origin, predict one step, compare to the actual. Champion = lowest backtest
MAE, **but a non-baseline champion must beat seasonal-naive by a 5% skill
margin (`MIN_SKILL`); otherwise the baseline itself ships** — a ~2% backtest
edge on a random walk is sampling luck (measured during implementation), and
every rostered indicator always has a publishable prediction. SARIMA's
seasonal component is capped at s ≤ 12 (a 52-week seasonal state space makes
fits take tens of seconds; weekly FRED series are seasonally adjusted anyway). The 80% band is the empirical 10th–90th percentile of the
champion's backtest errors, centered on the point — bands history earned, not
parametric formulas.

- **No leakage** is a tested invariant, not a convention (see §9).
- **Runtime budget:** the whole tournament must clear a free Actions runner
  comfortably (<< 6 h). Cheap models refit every origin; SARIMA may use
  statsmodels `extend`/`apply` between sparse refits and a small fixed order
  grid. Origin counts per cadence are bounded (e.g. ~100 monthly, ~104
  weekly origins).
- **Output `data/predictions/models.json`:** per indicator — champion
  `model@version`, cadence, backtest MAE, seasonal-naive MAE (the skill
  stat), band half-widths, last-tournament date, and the explanation
  skeleton. Version bumps when a model family's code changes.
- **Tier 3 (next phase, designed-for, not built):** cross-series features
  (claims → unemployment, permits → starts) via scikit-learn regularized
  regression / gradient boosting. The ledger and tournament don't care which
  family a champion comes from; `model@version` stamping means tier-3 wins
  show up as a visible, attributable accuracy improvement in the public
  record. Deep learning is excluded on data-size grounds (~300 monthly
  points), not budget.

## 5. Daily grade-and-predict

Appended to the daily FRED workflow after the category fetches, before
`--brief`/`--state`. Per rostered indicator, with per-indicator try/except:

1. **Grade:** if an observation for an open prediction's `target_period` has
   arrived, freeze the grade (first print) and move the entry open → graded.
2. **Footnote:** re-check the bounded revision window; set `revised_to`.
3. **Predict:** if no open prediction exists for the next print, fit the
   champion from `models.json` on the latest full history and write a new
   open entry (point, band, due, `why`, `implied_status` via the indicator's
   real `narrative` rule on history + point).

Missing `models.json` (pre-bootstrap) → grade/footnote still run, no new
predictions. One open prediction per indicator at a time (invariant). Runtime
~minutes for ~70 indicators.

## 6. Data layout — `data/predictions/`

All baked; the browser fetches only the small files. All writes are
write-if-changed ignoring `generated_at` (quiet-day no-commit preserved).

- **`open.json`** — current open predictions (~70), keyed for lookup by
  category/lens/indicator. Read by lens pages and `state.py`.
- **`recent.json`** — last grade per indicator + a global feed of the most
  recent ~50 grades. Read by lens pages and the track-record page.
- **`track-record.json`** — aggregates recomputed from the ledger each run:
  calibration % (hits / graded), skill vs naive
  (1 − Σ|err| / Σ|naive err|), direction %, status %, per-category table,
  counts, since-date.
- **`models.json`** — champion registry (tournament output; also feeds
  "how this works" copy).
- **`ledger/YYYY.json`** — append-only permanent archive, one file per year
  (~600 KB/yr; linked for transparency, never loaded by pages).

**Ledger entry** (the atom; `grade: null` while open):

```json
{
  "id": "cpi-2026-06",
  "category": "economic", "lens": "cost-of-living", "indicator": "cpi",
  "series_id": "CPIAUCSL", "horizon": "next-print",
  "target_period": "2026-06", "due": "~2026-07-15",
  "made_at": "2026-06-12T06:10:00Z",
  "model": "ets-seasonal@1",
  "point": 4.31, "lo": 4.02, "hi": 4.60, "unit": "%",
  "why": "Inflation has risen three straight months; this projects the recent trend with the usual June seasonal pattern.",
  "implied_status": "elevated",
  "grade": {
    "actual": 4.17, "graded_at": "2026-07-15T06:08:00Z",
    "hit": true, "abs_error": 0.14, "direction_hit": true,
    "status_hit": true, "naive_error": 0.31, "revised_to": null
  }
}
```

Model upgrades never touch history: graded entries keep the `model@version`
that made them, so the record can show accuracy by era honestly.

## 7. Surfaces

- **Per-lens pages — new `dashboards/predict.js`.** Lens pages add one script
  tag; after `lens.js` renders, `predict.js` fetches `open.json` +
  `recent.json` and appends a compact **"Next print"** block under each
  rostered indicator: expected value + band + due, the implied badge in plain
  English ("would keep this Elevated"), the `why` sentence, and **"Last call
  ✓/✗ — we said X, actual was Y"** (the most recent grade rides with the new
  open prediction for one full cycle — that is the aging visual), linking to
  the track record. Two additive lines in `lens.js` (a `data-indicator`
  attribute on each card and a `lens:rendered` event) are the hook;
  everything else lives in `predict.js`. Missing script or JSON → pages
  render exactly as today.
- **Track Record page — `dashboards/track-record.html` + `track-record.js`**
  (reads `track-record.json` + `recent.json`): (1) headline calibration stat
  with explainer — "we aim for ~80%, not 100% — a forecaster who's never
  wrong is using bands too wide to mean anything"; (2) skill vs naive ("our
  predictions have been N% closer than guessing the last value"); together
  un-fakeable — calibration proves the bands are honest, skill proves they're
  not lazily wide; (3) per-category accuracy table (badge-style); (4)
  recent-grades feed ("we said X · actual Y · ✓/✗", revision footnotes);
  (5) **"How this works"** — the toolbox, the tournament, first-print
  grading, the git-as-notary point. This section is the V1 methodology page.
  While young, the header says so proudly: "31 predictions graded since June
  2026 — this record grows weekly."
- **State of Things — "What we're watching next"** (the section reserved in
  the 2026-06-11 state spec). `state.py` reads `open.json` and appends a
  `watching` block to `data/state/today.json`: up to 3 entries ranked by
  **consequence** — predicted badge changes first (`implied_status` ≠ current
  lens-indicator status; alert-ward before ok-ward, by severity distance),
  then nearest-due notable prints. `state.js` renders it on `state.html`; the
  `/dashboards/` panel gets a one-liner only when a badge change is
  predicted. Missing `open.json` → block omitted (same mechanism as the
  brief's `changed` block).
- **Not in V1:** hub-tile/home-page prediction lines; nav restructuring
  (track record links from prediction blocks and the state page); longer
  horizons. One sentence in `about.html` "Where this is going" updates at
  ship time.

## 8. Pipeline & ops

- **New package `scripts/predictions/`** (roster, models, tournament,
  grading, explain, io), importing `lenses.config` read-only; writes only
  under `data/predictions/`. Entry point **`scripts/predict.py`** with
  subcommands `tournament` and `daily`, plus `--dry-run` from fixture
  histories. If every prediction module crashed, lenses build exactly as
  today.
- **`refresh-fred.yml`** gains `pip install -r requirements.txt` and
  `python scripts/predict.py daily` after the category fetches and before
  `--brief`/`--state`, under the same `success() || failure()` guard, same
  data commit. Banking workflow untouched in V1.
- **New `tournament.yml`** — weekly (Sun 05:00 UTC) **+ backup cron slot**
  (cron slots skip silently) + `workflow_dispatch`; `FRED_API_KEY` +
  `EIA_API_KEY`; commits `models.json`.
- **Bootstrap:** merge → dispatch tournament once → next daily run emits the
  first ~70 open predictions → first grades that week.
- **Fault tolerance:** per-indicator try/except in both jobs (a failing model
  skips that indicator, prior file state kept); all surfaces degrade silently
  per house pattern; the live record contains **only true out-of-sample,
  timestamped predictions** — backtest stats appear only in "How this works,"
  clearly labeled, never mixed into the record.

## 9. Testing (TDD, unittest)

`scripts/tests/test_predict_*.py`, fixtures backing `--dry-run`:

- **No-leakage proof:** feed the backtest harness a series with a planted
  structural break; models standing before the break must not benefit from
  data after it.
- **Calibration on synthetic truth:** known trend/seasonal/noise generators →
  tournament picks a sensible champion, beats naive, empirical 80% bands
  cover ~80% out-of-sample.
- **Tournament:** champion-must-beat-seasonal-naive else baseline ships;
  deterministic reruns; runtime-bounding parameters honored.
- **Grading invariants:** first-print freeze (second attempt is a no-op);
  revision footnote never alters `hit`; double-print cron-skip grades only
  the stated `target_period`; stale series stay open; one open prediction per
  indicator.
- **Ledger mechanics:** append-only, year rollover, write-skip when content
  unchanged.
- **`implied_status` / `status_hit`** via the real `narrative` rules.
- **Roster:** derived from `lenses.config` correctly — neutral lenses, info
  indicators, banking, injected sources excluded; a new config indicator
  appears automatically.
- **`state.py` watching block:** consequence ranking, badge-change-first,
  degradation when `open.json` is missing.
- **Degradation:** missing `models.json`, a model raising, missing prediction
  files at render time — nothing blanks.
- JS surfaces: manual `python -m http.server 8000` eyeball, per house
  convention.

## 10. Phases after V1 (recorded, not built)

1. **Tier 3 — cross-series features** (the "leading indicators" promise):
   scikit-learn enters requirements; champions compete in the same
   tournament; spurious-correlation defenses = regularization, economic
   plausibility, the same backtest gauntlet.
2. **~3-month horizon** predictions (the `horizon` field is already there).
3. Banking (FDIC quarterly) and injected/computed series join the roster.
4. Revisit the neutral-lens exclusion (educational-exhibit framing) — per
   Michael, flagged in memory.

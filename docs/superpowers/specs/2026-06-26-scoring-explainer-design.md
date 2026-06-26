# Scoring Explainer + "Now → next print" — Design Spec

**Date:** 2026-06-26
**Branch:** `scoring-explainer`
**Status:** built autonomously per Michael's brief; prose + screenshots batched for his review before any deploy.

Two independent, additive reader-experience upgrades flagged in a live-site review.
Everything degrades safe: with missing/old JSON every page renders exactly as it does
today. The three `fmtVal` twins (`build._fmt`, `lens.js fmtVal`, `predict.js fmtVal`)
stay in sync; a fourth renderer (`scoring.js`) reuses the same logic.

---

## Feature 1 — "Now → next print" (small)

**Problem.** Each indicator's *Next print* block (`dashboards/predict.js`, `block()`)
shows only the forecast ("We expect ~Y (likely lo–hi)"). The prediction has no anchor —
a reader can't see where the number *is* now.

**The data already exists.** `scripts/predictions/runner.py:_make_open_entry` emits
`prev_value` (= `values[-1]`) into `open.json`; `predict.js` just never renders it.

**Build.**
- `_make_open_entry`: add `prev_period` (= `cleaned[-1][0]`), the date of `prev_value`.
- `predict.js block()`: when `prev_value` is present, lead the line with the current
  value and an "as of" stamp:
  `Now <prev_value> (as of <period>) → next print ~<point> (likely lo–hi) … <status phrase>`.
  - `prev_value` formatted with the existing `fmtVal(unit, value_format)`.
  - `<period>` follows the site's monthly/quarterly convention ("May 2026", no fake
    day precision) — day == `01` ⇒ "May 2026"; otherwise "Jul 3, 2026" (weekly/daily).
- **Degrade-safe:** `prev_value`/`prev_period` missing ⇒ today's render verbatim.

**Tests.** Extend `test_predict_runner.py` (assert `prev_period` present and correct).
The JS render follows the repo's manual-verification norm for renderers.

---

## Feature 2 — Severity scoring explainer (bigger)

**Problem.** The badges (`ok / watch / elevated / alert`) aren't self-explanatory.
Surface, per signal, how a reading maps to a badge — for **every badge-carrying
indicator** (the severity roster, independent of the predictions roster).

**Out of scope.** How forecasts / their 80% bands are computed (models / tournament /
backtest). This is the *severity ring only*. The forecasting methodology, if ever
wanted, is a separate future page (natural home: Track Record).

### Decisions (made; locked)

**1. Single source of truth — generate, don't hand-maintain numbers.**
A `BandSpec` is a structured descriptor of a rule's decision axis: `kind` (how to read
the decision value), `unit`, ascending `edges`, per-segment `segments` (statuses),
optional `cap`, and a `probe` flag. `bands.py` (dependency-free) defines `BandSpec` and
the pure axis helpers. **Severity factories self-describe**: each factory
(`restrictive_rate`, `consumer_cost`, `yoy_band`, `yoy_band_two_sided`, `market_health`,
`consumer_delinquency`, `credit_spread`, `yoy_contraction_band`, `epu_band`,
`world_growth`) attaches `.band_spec` built **from its own threshold args** — so the
page can never show a number the code doesn't use. **Bespoke `rule_*` functions get an
explicit `.band_spec`** attached right after their def (numbers duplicated from the body,
guarded structurally by #2). Both the methodology page and the in-context scale render
from these specs.

**2. Drift lock (the whole point).** `test_bands.py` probes **every live scored rule**:
for each declared edge it feeds synthetic observations straddling the edge
(`bands.synth_obs(kind, edge±ε)`) and asserts the rule's returned status equals the
descriptor's segment on each side (cap applied). Editing a threshold without updating its
descriptor turns the build red. A coverage test asserts every `rule_kind == "severity"`
indicator has a spec, and every spec is well-formed. History/derived rules that can't be
probed on a single static axis (`rule_yield_curve`'s un-inversion) are marked
`probe=False` and covered in prose only — explicitly, not silently.

**3. Prose stays curated.** The "why these bands" calibration text lives in **one
reviewable place** (`reasons.BAND_WHY`, keyed by a per-rule tag, mirroring the existing
`reasons.py` "review prose here" pattern). It is **NOT approved** by being written — it
ships only after Michael's fact-check (batched). Numbers are guarded by #2; only the
words need his eyes.

### Taxonomy (mirrors the status model in CLAUDE.md)

- **severity** (`ok/watch/elevated/alert`) → a scale strip + bands on the methodology page.
- **info / descriptive** → "tracked, not scored — here's why" (reuses the already-shipped
  `no_severity_reason` from `reasons.py`).
- **momentum** (`up/down/flat`, the scoreboard) and **neutral** lenses (scoreboard,
  crypto-structure) → explained as such. `narrative.rule_kind()` buckets each signal.
- All four buckets are covered on the methodology page.

### Decision axes (`BandSpec.kind`)

- `level` — decision value = latest observation (mortgage %, VIX, debt/GDP, banking…).
- `yoy` — latest value *is* a YoY % (an already-`yoy_pct`-derived series, or a yoy_* factory).
- `yoy_computed` — the rule computes YoY internally from a level series
  (`consumer_cost`, `market_health`): decision value = the computed % (mirrors
  `narrative._value_year_ago`).
- `delta_from_low` — `rule_unemployment_trend` (points above the trailing-12-month low) —
  the exact "points above the 12-m low" axis the brief sketch named.
- `custom` — `probe=False`, prose-only, no strip (`rule_yield_curve`).

### Surface

**In-context scale strip** (`dashboards/scoring.js`, new; same hook pattern as
`predict.js` — `lens:rendered` + `.ind[data-indicator]`). Under each **scored** signal:
a compact color-coded strip drawn on the rule's real axis, with the real thresholds, a
marker at the current reading, and a "How we score this → full methodology" link to the
page's per-signal anchor.
- The current value on the decision axis is **baked** per scored indicator as `scale_now`
  in the lens JSON (`build.py`, computed in Python so `yoy_computed` needs no JS YoY
  re-derive); `lens.js` stamps it as `data-scale-now` on the `.ind` card (additive, the
  same way the `data-indicator` predict hook was added).
- **Ghost marker (decided: yes, conservative).** When a forecast exists *and* its
  `point` lies on the same axis as the bands (`kind != "yoy_computed"`), a faint
  secondary marker shows the forecast's implied position — purely positional, with no
  model explanation. Skipped for `yoy_computed` (there `point` is a level, not the YoY
  the axis shows — a marker there would mislead).
- Non-severity signals get no strip in-context (they already carry their
  `no_severity_reason` note from the shipped score-explain-order feature); they are fully
  covered on the methodology page.

**Methodology page** (`dashboards/methodology.html`, baked by `methodology.py` like
`briefpage.py`/`sitemap.py`; data also baked to `data/methodology.json` so the strip and
the page share one source). One page: a taxonomy explainer, then category → lens →
signal, each with an anchor (`#<lens-id>--<indicator-id>`). Severity signals show their
bands + curated why; info/momentum/neutral show their short "tracked, not scored" note.
Added to `sitemap.xml`. Linked from each signal's strip and from About. The 4-item nav
(Today's Brief / Dashboards / Track Record / About) is unchanged.

**No-JS / crawlers.** The methodology page is fully static (crawlable). `staticread.py`'s
baked `#baked-read` fragment gains, per scored indicator, a one-line static band summary
+ a deep link to the methodology anchor — so no-JS readers get the bands inline too.

### Wiring / ops

- `scoring.js` is stamped onto the 33 lens pages (after `predict.js`) by an idempotent
  one-shot tool (`scripts/tools/scoring_tag.py`, mirrors `cf_beacon.py`).
- `methodology.html` + `data/methodology.json` are baked in the `--brief` pass (runs
  last, no network; content-aware writes, so daily churn is zero — band specs change only
  when code changes). `methodology.html` is excluded from `pwa_head.py` (it emits its own
  head, like `brief.html`).
- Workflow commit globs already include `dashboards/`, `data/`, `sitemap.xml`.

### Constraints

- Additive + degrade-safe everywhere (missing/old JSON ⇒ today's render).
- Keep the four `fmtVal`/`_fmt` renderers in sync.
- Python tests required (`scripts/tests/`); JS renderers manually verified.
- `--dry-run` overwrites `data/` AND baked surfaces — `git checkout -- .` after offline
  test builds. Don't pipe the ~728-test run (masks exit code) — redirect to a file.

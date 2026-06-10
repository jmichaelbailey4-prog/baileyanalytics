# Today's Brief — Cross-Category Synthesis — Design

**Date:** 2026-06-10
**Status:** Approved in brainstorm (Option B state-snapshot + 3 corrections: `--brief` step decoupled from refresh scope, %-change ranking via sparkline, explicit category→dir map). Pending written-spec review.

## Goal

Ship the first **cross-category synthesis** feature. Today every category is an
island — six hubs, each aggregating its own lenses. A returning visitor has no
single place that answers *"what changed and what matters today?"* in under 30
seconds. **Today's Brief** is that place: a rule-based, pipeline-generated digest
that surfaces (1) **status transitions** since the prior data (the headline event —
e.g. "Consumer Sentiment: watch → elevated") and (2) the **3–5 most significant
moves** across all six categories, in plain English.

This is a step toward the roadmap's "synthesis" phase (see
[[exec-dashboard-roadmap]]): breadth is largely built; now we connect the dots.

Like everything on the site: rule-based (no LLM), baked into static JSON by the
Python pipeline, zero live calls from the browser.

## What the brief contains

A single static file `data/brief/today.json`:

```json
{
  "generated_at": "2026-06-10T13:05:00Z",
  "transitions": [
    {
      "lens_id": "consumer-sentiment",
      "lens_title": "Consumer Sentiment",
      "category": "consumer",
      "href": "/dashboards/consumer/sentiment.html",
      "from_status": "watch",
      "to_status": "elevated",
      "direction": "worsening",
      "headline": "Consumer confidence has slipped to a level that..."
    }
  ],
  "top_moves": [
    {
      "lens_id": "fiscal-health",
      "lens_title": "Fiscal Health",
      "category": "economic",
      "href": "/dashboards/fiscal-health.html",
      "stat_label": "Debt-to-GDP",
      "stat_value": "124.50%",
      "delta": "0.30%",
      "dir": "up"
    }
  ],
  "status_counts": { "alert": 0, "elevated": 2, "watch": 5, "ok": 14, "neutral": 2 }
}
```

- **`transitions`** — every lens whose `status` changed vs. the prior snapshot.
  Worsening transitions (toward `alert`) sort first, then improving. `headline` is
  the lens's *current* `headline_read` (already plain-English). `direction` is
  `worsening`/`improving`, derived from `STATUS_ORDER` movement.
- **`top_moves`** — up to 5 total items (transitions count toward the 5). Remaining
  slots filled by non-transitioning lenses ranked by the **significance of the
  primary indicator's latest move** — a dimensionless **z-score**: `|latest step| ÷
  pstdev(prior steps)`, computed from the `sparkline` array already in each
  `index.json`. (Implemented as `move_score`; **supersedes the original
  relative-%-change idea**, which over-weighted rate-valued series with small
  values — e.g. a 0.1-point move in a 0.8% series scored as +12%. The z-score judges
  each move against that series' own typical step, so level series like gasoline
  price and rate series like Food YoY are comparable.) The displayed `delta`/`dir`
  come straight from the lens's first `key_stat`; the score itself is internal to
  ranking and never written to the JSON.
- **`status_counts`** — tally across all lenses for the at-a-glance home-page line
  ("2 elevated · 5 on watch").

## Significance ranking (the rules)

1. **Transitions are the headline.** Any `status` change is significant by
   definition. Sorted worsening-first by magnitude of `STATUS_ORDER` jump
   (e.g. `ok → alert` outranks `watch → elevated`), then improving.
2. **Moves fill the rest.** Up to `5 − len(transitions)` non-transitioning lenses,
   ranked by `move_score` (the latest-step z-score) descending, keeping only moves
   of at least `MOVE_THRESHOLD_SIGMA` (1.0 — roughly one typical step).
3. **Why a z-score, not raw delta or % change:** raw deltas aren't comparable across
   units (a 0.25-point yield-curve move vs. a $2.4T debt move); % change breaks on
   rate-valued series with small denominators (a 0.1-point move in a 0.8% series
   looks like +12%). Normalizing the latest step by the series' own prior-step
   volatility is dimensionless and comparable across every unit, and the sparkline
   already carries the raw numeric primary series — no re-parsing of formatted
   strings.
4. **Neutral/info lenses** (markets scoreboard, crypto — `narrative.NEUTRAL_LENSES`)
   are **eligible for `top_moves`** (a big BTC-dominance swing is newsworthy) but
   **excluded from transition detection** (they have no severity to transition).
   They appear in `status_counts` under `neutral`.
5. **Thresholds:** a move needs `abs(pct_change) ≥ 0.5%` to qualify (filters noise);
   if fewer than 5 qualify, the brief simply shows fewer. A day with no transitions
   and no ≥0.5% moves yields empty arrays — the UI shows "Markets are quiet today."

## State persistence (the new piece)

Mirrors the `_crypto_history.json` accumulation pattern
(`refresh_lenses.py:_load_crypto_history`/`util.merge_series`).

- **`data/brief/_prior_state.json`** — written by the *previous* brief run, read by
  the current one. Shape: `{ "captured_at": "...", "statuses": { "<lens_id>": "<status>" } }`.
  Never served to the browser.
- **Flow each brief run:**
  1. Read `_prior_state.json` (→ `{}` if absent).
  2. Read every category's current `index.json` from disk.
  3. Diff statuses → `transitions`; compute `top_moves` and `status_counts`.
  4. Write `today.json`.
  5. Overwrite `_prior_state.json` with the just-observed statuses.
- **First run / missing prior:** `transitions = []` (nothing to diff against);
  `top_moves` and counts still populate. No special-case UI text needed beyond the
  normal "quiet day" empty state.

### Why a dedicated `--brief` step (corrects the brainstorm)

The brief is a synthesis over the **current published state on disk**, independent
of which categories a given invocation refreshed. Production never runs flagless —
the daily workflow invokes `--economic`, `--markets`, `--energy`, `--housing`,
`--consumer` as **separate flagged runs** (`refresh_lenses.py:437-468`), and banking
is a separate weekly workflow. A "run brief only when flagless" rule would mean the
brief **never generates in production**. Instead, `--brief` is its own step that
reads whatever `index.json` files exist and runs **last** in the workflow.

## Pipeline (`scripts/lenses/` + `refresh_lenses.py`)

- **New module `scripts/lenses/brief.py`** — pure functions, no network:
  - `CATEGORY_DIRS` — explicit map (corrects the brainstorm's uniform assumption):
    `{"economic": "lenses", "banking": "banking", "markets": "markets",
    "energy": "energy", "housing": "housing", "consumer": "consumer"}`.
    Note **economic → `data/lenses/`**, not `data/economic/` (`refresh_lenses.py:20`).
  - `LENS_HREFS` — map of `lens_id → public page path` for click-through (the
    home/dashboards pages already know these mappings; centralize here for the brief).
  - `detect_transitions(prior_statuses, current_lenses)` → sorted transition list.
  - `rank_moves(current_lenses, transitions, limit=5)` → `top_moves`.
  - `build_brief(category_indices, prior_state)` → `(today_json, new_state)`.
  - `pct_change(sparkline)` helper.
- **`refresh_lenses.py`:** add `--brief` flag + `refresh_brief(dry_run)`:
  reads the six `index.json` files (skipping any not yet on disk), reads
  `_prior_state.json`, calls `brief.build_brief`, writes `data/brief/today.json` and
  `data/brief/_prior_state.json`. Additive/fault-tolerant — a missing category index
  is skipped, never fatal. In `main()`, `do_brief = args.brief or not any_flag`, and
  it runs **after** all category refreshes.
- **No new keys, no new network sources.** Pure file synthesis.

## Pages (zero-build static frontend)

- **`dashboards/index.html` (hub):** a "Today's Brief" panel **at the top**, above
  the six category grids. Shows `generated_at`, transition pills (color-coded by
  `to_status` via existing badge classes in `lens.css`), and a plain-English
  top-moves list (each links to its lens via `href`). Empty state: "Markets are
  quiet today — no status changes." Fetched from `/data/brief/today.json`
  (`cache: "no-cache"`, matching `hub.js`).
- **Root `index.html` (home):** a compact brief strip near the top — one summary
  line from `status_counts` ("2 lenses elevated · 5 on watch") plus the top
  transition headline if any, linking to `/dashboards/`. Reuses the same JSON.
- **New shared `dashboards/brief.js`** renders both surfaces (one `renderBrief(el,
  data, {compact})` function; `compact` drives the home-page one-liner vs. the full
  hub panel). Styles live in `lens.css` alongside the hub-card CSS.
- **Unit rendering:** the brief displays values/deltas **already formatted** by
  `build.py _fmt` (they arrive pre-formatted in `key_stats`), so no new unit logic —
  the `_fmt`/`fmtVal` sync rule is not touched.

## Workflows

- **`refresh-fred.yml`:** add a final `--brief` step after the consumer step, under
  the same `if: ${{ success() || failure() }}` guard, and include `data/brief/` in
  the commit. Runs once per workflow invocation, last — so it observes the freshest
  category indices.
- **`refresh-banking.yml`:** also append a `--brief` step (so a banking status change
  on the weekly run produces a transition too). Cheap — pure file read.

## Testing (TDD, ~20 new tests)

- **`test_brief.py`:**
  - `detect_transitions`: changed / unchanged / first-run (empty prior) / lens
    appeared / lens disappeared / neutral lens excluded.
  - `rank_moves`: transitions fill first, %-change sort, 0.5% threshold, fewer-than-5,
    sparkline with <2 points (skipped safely), neutral lens eligible.
  - `pct_change`: normal, zero-prior guard, single-point guard.
  - `build_brief`: full assembly from fixture indices + prior state; `status_counts`
    correct; round-trips `_prior_state.json` shape.
  - Edge: all lenses neutral; empty/missing category index; empty `key_stats`.
- **`test_refresh_brief.py`:** `--brief --dry-run` reads fixture indices from a temp
  `data/` tree, writes `today.json` + `_prior_state.json`; second run detects a
  transition seeded by a doctored prior state.
- Fixtures: small `brief_indices_sample.json` (a few lenses per category) +
  `brief_prior_state_sample.json`. `--dry-run` must **not** clobber real
  `data/brief/` — `refresh_brief(dry_run=True)` writes to fixtures/temp, mirroring how
  other `--dry-run` paths use fixture inputs. (Guard against the standing
  "--dry-run overwrites data/" gotcha.)
- Full suite (~270 + new) must pass before any commit.

## Out of scope

- Per-lens (sub-status) transition history or a multi-day changelog (Option C) —
  v1 is "today" only. The `_prior_state.json` makes a future rolling log easy.
- LLM-written prose. All text is the existing rule-engine `headline_read`.
- New data sources, series, or keys.
- Email/RSS/push distribution of the brief.
- Indicator-level moves (we rank at the lens level via its primary indicator).

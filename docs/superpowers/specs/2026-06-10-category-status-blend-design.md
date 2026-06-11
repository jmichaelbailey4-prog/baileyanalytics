# Category Status Blend (home tiles) — Design

**Date:** 2026-06-10
**Status:** Direction approved by Michael (balanced category score, bad weighted heavier, worst-lens callout — "use your best judgement"); details delegated.

## Goal

The home page's category tiles currently wear the **worst lens's** badge and content,
so a category with one stressed lens and four healthy ones reads as if the whole
category is stressed. Michael's concern: that looks alarmist and gets the site
written off when an expert reads the category as broadly healthy. Replace the badge
with a **balanced category score** where bad readings weigh more than good ones
offset, and keep the worst lens visible as an attributed **callout** instead of the
whole story.

## The rule: `util.status_blend(statuses)`

- Map severities ok=0, watch=1, elevated=2, alert=3 (`util.STATUS_ORDER`);
  `neutral`/`info`/`unknown` are excluded (no severity lenses at all → `"neutral"`).
- Score = **quadratic mean (RMS)**: `sqrt(mean(s²))`. Squaring is the "bad counts
  more" weighting. (A geometric mean was considered and rejected: ok=0 collapses a
  geometric mean to 0, so any healthy lens would force the category to "ok".)
- Bands: `< 0.6` → ok · `< 1.5` → watch · `< 2.5` → elevated · `≥ 2.5` → alert.
  Calibration intent: one watch among ≥4 ok lenses stays **ok** (0.5); a category
  reads **alert** only when stress is broad (e.g. alert+alert+elevated+elevated →
  2.55), since a single alert lens is the callout's job, not the badge's.

With 2026-06-10 data: Economy **watch** (was elevated), Consumer **elevated** (was
alert), Banking **ok** (was watch), Markets **ok**, Energy **elevated** (was alert),
Housing **watch** (was elevated).

## Where it lives

- **Pipeline, not page JS:** `build.build_index` adds a top-level
  `"status": util.status_blend([lens statuses])` to every category `index.json` —
  unit-testable, single source of truth, and any surface can reuse it later.
- **Home page (`index.html`):** badge uses `data.status` (falls back to the worst
  lens's status if absent, e.g. stale cache). Tile content still comes from
  `worstLens()` (most newsworthy), but gains an attribution line above the
  headline: the lens title, plus that lens's own mini status pill **only when it is
  worse than the category badge** — that's the callout ("Sentiment & Expectations
  `alert`"). Mobile chip view hides the attribution line like it hides the
  headline/sparkline.
- Lens pages, hubs, and the brief stay lens-level; `status_max` (worst-of) remains
  the rule *within* a lens, where indicators tell one story. The blend is only for
  rolling up heterogeneous lenses into a category.
- **Regeneration:** the six `index.json` files are rebuilt offline from the lens
  JSONs already on disk (order preserved from each existing index), so the new
  field ships without a network fetch; the daily cron keeps it fresh thereafter.

## Testing

TDD: new `test_status_blend.py` — band edges (0.5→ok, 0.707→watch), the six
real-category profiles above, neutral/info/unknown exclusion, all-neutral →
neutral, single-lens alert → alert, empty → neutral; plus `build_index` emits the
key. Frontend verified via local server + curl. Full suite green before commit.

## Out of scope

- Category badges on `/dashboards/` section headings or hub pages.
- Changing the brief's lens-level `status_counts`.
- Any change to lens-level badge rules (`status_max`).

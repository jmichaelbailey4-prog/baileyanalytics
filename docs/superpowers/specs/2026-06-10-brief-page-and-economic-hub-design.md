# Brief Detail Page + Economic Hub — Design

**Date:** 2026-06-10
**Status:** Approved by Michael (one brief page with anchored sections; landing panel keeps counts + transitions, drops inline move rows).

## Goal

Two presentation fixes to make `/dashboards/` read cleanly on landing:

1. **Economic Lenses has no "Overview →" link** — it's the only category without a
   hub page (its lens pages live flat at `/dashboards/<lens>.html`, a legacy of
   being the first category). Give it one.
2. **The Today's Brief panel's "Biggest moves" rows look messy.** Replace them with
   links into a new **Today's Brief detail page** that shows the relevant lenses as
   the same visual cards the category hubs use. Status counts become deep links
   ("3 alert" → the three alert cards).

## Part 1 — Economic category hub

- **New page `dashboards/economic/index.html`**, cloned from the housing hub
  (`dashboards/housing/index.html`): wordmark, top-nav, `← Dashboards` back link,
  h1 "Economic Lenses", lede, `hub-grid` via `loadHubGrid("hub-grid",
  "/data/lenses/index.json", id => "/dashboards/<id>.html")`, FRED footer credit.
  Lens pages stay flat — no moves, no redirects.
- **`dashboards/index.html`:** add `<a href="/dashboards/economic/">Overview →</a>`
  to the Economic cat-sub, matching the other five categories.
- **Root `index.html`:** the Economy tile's `href` changes from `/dashboards/` to
  `/dashboards/economic/` (each home tile links to its category overview).

## Part 2 — Today's Brief detail page

### The page (`dashboards/brief.html`)

Standard page chrome (wordmark/top-nav/back link/lede + "as of" stamp from
`generated_at`). Sections, in order, each a `hub-grid` of the **existing hub
cards** (badge, plain-English read, sparkline, key stats):

| Section | Anchor | Content | When hidden |
|---|---|---|---|
| Status changes today | — | transition rows (lens title + `from → to` badges + headline), each linking to its lens | no transitions → shows "No status changes today." |
| Biggest movers | `#moves` | hub cards for `top_moves` lens ids, in rank order | no movers → section hidden |
| On alert | `#alert` | hub cards for every `status: alert` lens | count 0 → hidden |
| Elevated | `#elevated` | same for `elevated` | count 0 → hidden |
| On watch | `#watch` | same for `watch` | count 0 → hidden |

`ok`/`neutral` lenses are deliberately omitted — `/dashboards/` already shows
everything; this page is the triage view. Cards are sparkline-level visuals, not
full Chart.js charts (full charts would load ~10 × ~100KB lens JSONs on one page;
the full chart is one click away on the lens page).

**Data flow:** fetch `/data/brief/today.json` plus the six category `index.json`
files (`Promise.allSettled`, same pattern as the home page). Build an id → lens
map from the indexes (sparkline/key_stats/headline/accent/status live there); use
today.json's new `lenses` list for grouping and hrefs. A failed index fetch just
means those cards are absent — never an error page.

### `today.json` schema addition (pipeline)

`build_brief` already flattens every lens with category, href, and status —
expose it: add a top-level `"lenses"` array of
`{lens_id, lens_title, category, href, status}` (~25 entries, ~2 KB). This keeps
the slug/href logic in one place (`brief.py lens_href`) instead of duplicating the
slug maps a third time in JS. `transitions`/`top_moves`/`status_counts` unchanged.
The content-aware write (F1) means this lands as a one-time regeneration.

### `hub.js` refactor (reuse, no new card markup)

The card renderer (`tile` + `sparkline`) is private inside the IIFE. Expose one
shared entry point: `window.renderHubTiles(gridEl, lenses, hrefFor)` — used
internally by `loadHubGrid` and by `brief.html` (which passes
`hrefFor = id => hrefById[id]` built from today.json's `lenses`). Rendering is
byte-identical to today's hub cards.

### Landing panel slim-down (`brief.js`)

Full panel becomes:

```
TODAY'S BRIEF
3 alert · 6 elevated · 2 on watch        ← each nonzero count links to brief.html#<status>
[transition pills, when any — unchanged rendering]
Biggest movers →   Full brief →          ← brief.html#moves / brief.html
```

- Inline move rows (`moveRow`, `.brief-move*` CSS) are removed — that content now
  lives on the brief page. Dead CSS is deleted, not orphaned.
- "Biggest movers →" renders only when `top_moves` is non-empty.
- Quiet day: "All clear across the dashboards · Full brief →".
- Home-page compact strip: unchanged layout, but the counts text becomes a link to
  `/dashboards/brief.html` (the lead-transition link stays as is).

### brief.html rendering code

Page-specific logic (fetch/join/group/section rendering) lives in an inline
`<script>` on `brief.html` — it is used by exactly one page, matching how
`dashboards/index.html` and the home page keep their one-page logic inline.
`brief.js` stays the shared panel/strip renderer.

## Testing

- **Python (TDD):** `test_brief.py` — `build_brief` output includes `lenses` with
  the five fields, hrefs from `lens_href`, one entry per input lens;
  `test_refresh_brief.py` — generated `today.json` carries `lenses`. Full suite
  green before commit. Regenerate `data/brief/` once.
- **Frontend:** local `http.server` + curl checks — brief.html serves with section
  anchors; `renderHubTiles` exported in hub.js; panel HTML contains linked counts
  and no `brief-move` markup; economic hub serves and `dashboards/index.html`
  contains the Overview link.

## Out of scope

- Full Chart.js charts on the brief page.
- Multi-day brief history.
- Moving economic lens pages under `/dashboards/economic/` (flat URLs keep working).
- Home-page changes beyond the Economy tile href + strip link.

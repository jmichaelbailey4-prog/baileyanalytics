# The State of Things — design spec (2026-06-11)

The consolidated current-state summary: where do things **stand** overall (Today's
Brief answers what **changed**). One overall verdict — a status token plus one
assembled plain-English sentence — backed by Pressure Points, a Holding Steady
roll-up, and a link into Today's Brief. Programmatic narrative over already-baked
ingredients; no LLM at runtime, no numeric score shown anywhere.

Surfaces: a panel atop `/dashboards/`, its own page `dashboards/state.html`, and
the one-line verdict on the home hero.

## 1. Editorial rules (settled with Michael 2026-06-11)

### Overall token — blend of blends

`util.status_blend` applied to the 8 **category** blended statuses (the same RMS
math and bands documented in `util.py`, extended one level up). The verdict is
therefore always consistent with the category badges rendered beneath it.
Neutral and missing categories drop out of the blend, exactly as neutral lenses
drop out of category blends.

Today's real data: Consumer + Energy elevated, Economic + Housing + Global
watch, Banking + Markets + Business ok → √((4+4+1+1+1)/8) ≈ 1.17 → **watch**.

A deliberate property: even Consumer going full alert tomorrow leaves the
overall at √(17/8) ≈ 1.46 — still watch. The blend resists one-category panic;
Pressure Points carries the alarm. The overall escalates only when stress
spreads.

### Tiering and ranking

- **Pressure points** = categories at elevated or alert, ranked by **raw RMS
  score** (the un-banded `status_blend` value, recomputed from the lens statuses
  in each category's `index.json`) descending; ties fall to the canonical
  `CATEGORIES` order. Capped at 3. Each entry wears its worst lenses' verbatim
  `headline_read`s (up to 2 lenses per category, worst first; ties between
  lenses fall to their `config.py` order).
- **Holding steady** = every other category (ok *and* watch), badges visible —
  watch-tier categories are seen but don't make the headline.
- Today's ranking: Energy (2.35, two alert lenses) ahead of Consumer (1.87).

### Sentence shape

The skeleton is selected by the **shape** of the distribution. Shapes partition
cleanly on the overall token (one watch sub-split):

| Shape | Condition |
|---|---|
| `all-clear` | overall ok |
| `mixed-watch` | overall watch, no elevated/alert categories |
| `contained-pressure` | overall watch, ≥1 elevated/alert category (today) |
| `spreading-stress` | overall elevated |
| `broad-stress` | overall alert |

(Overall ok mathematically excludes any elevated+ category — one elevated among
eight already blends to watch — so `all-clear` never hides a pressure point.)

### Slots and assembly

- **Pressure clauses:** top pressure categories' fragments (see copy bank),
  joined with " and " (2) or commas + "and" (3). Cap: 2 clauses for
  `contained-pressure`, 3 for `spreading-stress` / `broad-stress`.
- **Anchor clause:** the top 1–2 *ok* categories by fixed anchor priority
  (banking, markets, economic, business, consumer, housing, energy, global),
  their steady clauses joined with " and ". If no category is ok, the skeleton's
  written fallback is used (e.g. "and little of the board reads steady").
- **Watch mentions** (`all-clear` / `mixed-watch` only): category **noun
  phrases**, not clauses ("the only thing worth watching is business health").
  With zero watch categories, the variant's no-watch ending is used; with two,
  singular phrasings pluralize ("the only things worth watching are X and Y").
- Fragments are lowercase, no terminal punctuation, authored to splice; the
  skeleton provides capitalization and final punctuation. The status token is
  carried separately in `verdict.status` and rendered as a badge — it is not
  part of the sentence string.

### Rotation

Each shape has 3 skeleton variants. Variant index =
`zlib.crc32(iso_date.encode()) % 3`, where `iso_date` is the UTC date of
generation (`YYYY-MM-DD`). Deterministic and reproducible for any given day,
varies across days, stable within a day (no intraday commit churn).

## 2. Copy bank (the editorial product — review this section closely)

### Category noun phrases (watch mentions, lists)

| Category | Noun phrase |
|---|---|
| economic | the core economy |
| consumer | household finances |
| banking | the banks |
| business | business health |
| markets | markets |
| energy | energy costs |
| housing | housing |
| global | the global backdrop |

### Pressure clauses (elevated / alert)

| Category | elevated | alert |
|---|---|---|
| economic | the core economy is under real strain | the core economy is flashing serious warnings |
| consumer | household finances are stretched thin | households are in real distress |
| banking | cracks are showing in the banking system | the banking system is under serious stress |
| business | business health is deteriorating | corporate America is in real trouble |
| markets | financial markets are under stress | financial markets are in turmoil |
| energy | energy and commodity costs are squeezing budgets | energy and commodity costs are surging |
| housing | the housing market is out of balance | the housing market is in serious trouble |
| global | the global backdrop is turning hostile | the global economy is in serious stress |

### Steady clauses (anchors)

| Category | Steady clause |
|---|---|
| banking | banks are solid |
| markets | markets are calm |
| economic | the core economy is steady |
| business | business health is holding up |
| consumer | households are keeping pace |
| housing | housing is balanced |
| energy | energy costs are behaving |
| global | the global backdrop is quiet |

### Skeletons (3 per shape; `{p}` pressure clauses, `{a}` anchor clause, `{w}` watch nouns)

**all-clear**
1. "The economy reads broadly healthy: {a}, with {w} the only thing worth watching." / no-watch ending: "…healthy: {a} — nothing on the board is flashing."
2. "A calm read across the board — {a}; the only thing worth watching is {w}." / no-watch: "A calm read across the board — {a}; nothing is flashing."
3. "Most everything reads steady right now: {a}; {w} is the lone watch item." / no-watch: "Most everything reads steady right now: {a}, with no watch items on the board."

(Implementation note, found while building: `mixed-watch` and
`contained-pressure` can also occur with **zero ok categories** — e.g.
elevated+watch+watch+watch → RMS ≈ 1.32 → watch — so they carry no-ok
fallbacks too, same mechanism as spreading-stress.)

**mixed-watch**
1. "Nothing is flashing red, but several corners bear watching — {w} — while {a}." / no-ok fallback: "Nothing is flashing red, but several corners bear watching: {w}."
2. "A wait-and-see picture: {a}, but {w} all bear watching." / no-ok: "A wait-and-see picture: {w} all bear watching."
3. "Steady on the surface with caution underneath — {a}, while {w} warrant attention." / no-ok: "Caution across the board — {w} all warrant attention."

**contained-pressure**
1. "The economy is holding up, but not without strain: {p}, while {a}." / no-ok fallback: "The economy is holding up, but not without strain — {p}, and the rest bears watching."
2. "Pressure is real but contained: {p}; meanwhile {a}." / no-ok: "Pressure is real but contained: {p}; the rest of the board bears watching."
3. "Most of the economy is on solid footing — {a} — but {p}." / no-ok: "Little of the board is fully in the clear — {p}, and the rest bears watching."

**spreading-stress**
1. "Stress is spreading: {p}; {a}." / no-ok fallback: "Stress is spreading: {p}, and little of the board reads steady."
2. "The strain is no longer contained — {p} — and the steady list is getting shorter; for now {a}." / no-ok: "The strain is no longer contained — {p} — and the steady list has run out."
3. "More of the economy is under strain than not: {p}; the relative bright spots: {a}." / no-ok: "More of the economy is under strain than not: {p}, with no real bright spots."

**broad-stress**
1. "Serious stress across the economy: {p}."
2. "The board is mostly red — {p} — and safe harbors are scarce."
3. "A genuinely bad stretch: {p}, and almost nothing on the board reads steady."

### Worked examples

1. **Today (real data, contained-pressure, watch), variant 1:**
   > The economy is holding up, but not without strain: energy and commodity
   > costs are squeezing budgets and household finances are stretched thin,
   > while banks are solid and markets are calm.
2. **Hypothetical escalation** (Consumer→alert, Banking→elevated; overall
   √(20/8) ≈ 1.58 → elevated, spreading-stress), variant 1:
   > Stress is spreading: households are in real distress, energy and commodity
   > costs are squeezing budgets, and cracks are showing in the banking system;
   > markets are calm and business health is holding up.
3. **Hypothetical calm day** (all ok except Business watch; √(1/8) ≈ 0.35 → ok,
   all-clear), variant 2:
   > A calm read across the board — banks are solid and markets are calm; the
   > only thing worth watching is business health.

## 3. Pipeline

New module **`scripts/lenses/state.py`** — pure synthesis mirroring `brief.py`'s
contract: `build_state(category_indices, brief_today) → state_json`. No network,
no disk I/O. It owns the copy bank, shape classification, raw-RMS ranking, and
sentence assembly. The RMS scoring inside `util.status_blend` is exposed (small
refactor: a `status_score(statuses)` helper that `status_blend` bands) so state
and category blends share one implementation.

`refresh_lenses.py` wiring, mirroring `refresh_brief`:

- Runs **after** `refresh_brief` (consumes the freshly written brief for the
  transition count), by default on every run; a `--state` flag rebuilds it alone.
- Reads the same category `index.json` set (`_brief_index_dirs`) plus
  `data/brief/today.json`.
- Writes `data/state/today.json` **only when content (ignoring `generated_at`)
  changed** — preserves the quiet-day no-commit path.
- Wrapped in try/except: any failure warns and keeps the previous file; a state
  failure never breaks the run or other outputs.
- `--dry-run` builds from the existing brief fixture indices, like the brief.

### Fault tolerance / degradation

- A missing category index is excluded from the blend, the blocks, and
  `categories[]` — the page renders whatever is present.
- Fewer than 4 categories present → `verdict.status = "unknown"`,
  `verdict.shape = "insufficient"`, sentence: "Not enough data to read the
  overall picture right now."
- Brief missing or unreadable → the `changed` block is omitted; the page hides
  that section.

## 4. Baked JSON — `data/state/today.json`

```json
{
  "generated_at": "2026-06-11T12:00:00Z",
  "verdict": {
    "status": "watch",
    "shape": "contained-pressure",
    "sentence": "The economy is holding up, but not without strain: …"
  },
  "pressure_points": [
    {
      "category": "energy",
      "title": "Energy & Commodities",
      "status": "elevated",
      "href": "/dashboards/energy/",
      "lenses": [
        { "id": "energy-oil-fuels", "title": "Oil & Fuels", "status": "alert",
          "headline": "Fuel costs are spiking — acute pressure at the pump.",
          "href": "/dashboards/energy/oil-fuels.html" },
        { "id": "energy-commodities", "title": "Commodities & Materials", "status": "alert",
          "headline": "Commodity costs are surging.",
          "href": "/dashboards/energy/commodities.html" }
      ]
    },
    { "category": "consumer", "...": "…" }
  ],
  "steady": [
    { "category": "economic", "title": "Economic Lenses", "status": "watch", "href": "/dashboards/" },
    { "category": "banking", "title": "Banking System Health", "status": "ok", "href": "/dashboards/banking/" }
  ],
  "changed": { "transitions": 2, "href": "/dashboards/brief.html" },
  "categories": [
    { "category": "economic", "title": "Economic Lenses", "status": "watch", "href": "/dashboards/" }
  ]
}
```

Notes:

- `steady` is ordered: watch categories first (most interesting), then ok, each
  group in canonical order. `categories` is all present categories in canonical
  order — the V2 substrate.
- Lens and category hrefs reuse the brief's `lens_href` slug logic (move/share
  it rather than duplicating). Category hub hrefs: `/dashboards/` for economic,
  `/dashboards/<category>/` otherwise.
- `changed.transitions` is the count of the brief's `transitions` array.

### V2 headroom (perspective slicer — not built now)

Blocks are data, not prose. A role view (Executive/Board, Investor, Household)
reorders `pressure_points` / `steady` / `categories` client-side and appends one
role-specific "what this means for you" line; it never rewrites the verdict
sentence or headlines. Nothing in V1's shape needs to change for that — role
definitions will ship as a static JS/JSON map in V2.

## 5. Surfaces

- **`dashboards/state.html`** — full page, same head/nav/footer conventions as
  `brief.html`: verdict (badge + sentence) → Pressure Points (category cards
  with badges + lens headlines, deep links) → Holding Steady (compact badge
  list) → What Changed Today ("N lenses moved overnight → Today's Brief";
  "Quiet day — no status changes" when zero).
- **Panel atop `dashboards/index.html`** — compact strip above the category
  sections: badge + sentence + "The full picture →" link to `state.html`.
- **Home hero (`index.html`)** — the verdict sentence + link, fetched from
  `data/state/today.json` alongside the existing tile fetches; absent/failed
  fetch leaves the hero exactly as it is today.
- Shared renderer **`dashboards/state.js`** exposing `renderStatePanel(el)` and
  `renderStatePage(el)`, reusing `lens.css` badge classes (pattern: `hub.js`).
  All three surfaces degrade silently if the JSON is missing.
- Out of scope for V1: RSS/feed integration, the perspective slicer, "What
  we're watching next" (prediction phase).

## 6. Testing (TDD)

`scripts/tests/test_state.py`, built against `brief_indices_sample.json` plus
small synthetic indices:

- `status_score` refactor: `status_blend` behavior unchanged (existing
  `test_status_blend.py` keeps passing).
- Overall token: blend-of-blends on today's shape; band edges (e.g. the
  1.46-still-watch case).
- Shape classification for all five shapes + `insufficient`.
- Raw-RMS pressure ranking, including today's Energy-over-Consumer case and a
  canonical-order tie-break.
- Sentence assembly: each shape × each variant; clause joining (2 vs 3); anchor
  fallbacks; watch mentions incl. zero-watch endings; lowercase splice
  invariants (no double punctuation, sentence starts capitalized).
- Rotation: deterministic per date, varies across dates.
- Degradation: missing category, missing brief, <4 categories, empty input.
- JSON shape: keys, ordering rules, href correctness via the shared slug logic.
- `refresh_lenses` wiring: write-skip when unchanged (ignoring `generated_at`),
  prior file kept on failure (mirror `test_refresh_brief.py`).

Presentation verification is manual: `python -m http.server 8000` and eyeball
the three surfaces, per house convention.

# Synthesis & the "Why" Layer — Design

**Date:** 2026-06-16
**Branch:** `synthesis-why-layer`
**Roadmap home:** site audit Part 2 #4 (`specs/2026-06-12-site-audit-and-next-steps.md`),
named again as the next bet in `DECISIONS-PENDING.md` #5.
**Status:** design complete; the *uncontested, honest* subset is built on this branch
(per-mover "why" + structural co-occurrence + the relationship-map scaffolding). The
**authored relationship-map content** and the **map-driven causal narrative** are
deliberately deferred to a follow-up session (they need Michael's editorial/economist
review). Contested forks are logged in `DECISIONS-PENDING.md` (2026-06-16 section).

---

## 1. Intent

Today the brief states facts in isolation. The verdict blends them; the movers and
pressure list enumerate them; but nothing **connects** them and nothing says **why** a
number moved. The audit's words: *"the site states 33 isolated facts; the connections are
left to the reader."* Every daily product people actually read (Axios Macro, Chartr, the
Daily Shot) leads with one human sentence of context. This layer adds two things:

- **(a) A one-line "why" per mover** — grounded in that mover's *own* data (its trend,
  streak, level vs. its own recent range), in the spirit of `predictions/explain.py`.
- **(b) Cross-category synthesis** — connecting the day's signals into one read
  ("most of today's pressure is the same cost-of-living squeeze showing up in three
  places"), instead of eight isolated category reads.

The gating constraint is **honesty**. This layer is the site's credibility centerpiece;
a single overclaimed causal sentence does more damage than the whole feature adds. So the
design makes honesty a **mechanical, unit-tested invariant**, not a matter of reviewer
vigilance.

---

## 2. The honesty rule (the crux)

> **State shared drivers, co-movement, and definitional links. Hedge empirical
> relationships ("tends to," "historically"). NEVER assert a specific causal mechanism as
> fact unless it is definitional. When in doubt, connect by co-occurrence, not causation.**

### Worked good/bad examples

| Verdict | Example | Why |
|---|---|---|
| ✅ **Co-occurrence (fact)** | "Four of today's pressure points are rising-price stories — fuel, food, electricity, and overall inflation." | A count over a shared *subject*. No mechanism claimed. |
| ✅ **Definitional (may state as fact)** | "Real income is income after inflation — so when prices climb faster than pay, it falls by definition." | An identity, not an empirical claim. Safe to state plainly. |
| ✅ **Empirical (must hedge)** | "Mortgage rates near 7% have *historically* cooled buyer demand; affordability is already stretched." | Hedged ("historically") + co-occurrence, not "rates ARE freezing the market." |
| ✅ **Per-mover (self-grounded)** | "Food: up 7 readings in a row, and its sharpest jump in this view." | Describes only its own series. No other series, no cause. |
| ❌ **Causation as fact** | "Energy prices are driving the drop in consumer sentiment." | Asserts a specific mechanism as fact. Banned. |
| ❌ **Per-mover naming another series** | "Food costs surged as fuel prices climbed." | A cross-series causal/temporal claim in a per-mover line. Banned. |

### The four invariants (each enforced by a test)

- **INV-1 — Per-mover whys are self-grounded.** A per-mover "why" contains **no causal
  token** and **names no other category or lens**. It is built only from its own series'
  sparkline + stat label.
- **INV-2 — Co-occurrence is a count, not a cause.** The co-occurrence sentence contains
  **no causal token**. It states *how many* pressure points share a subject and names
  them; it never says one causes another.
- **INV-3 — Relationship language matches edge strength.** A relationship sentence's
  wording is gated by its backing edge's `strength`:
  - `definitional` → *may* contain a causal token (it is an identity);
  - `empirical` → *must* contain a hedge token ("tend", "histor", "often", "typically",
    "usually") and may not state bare causation without it;
  - `co-occurrence` → *must contain neither* a causal token nor a hedge — pure conjunction
    ("alongside", "at the same time as").
  A relationship sentence with **no backing edge cannot be produced** — the composer only
  emits from the curated map.
- **INV-4 — Determinism.** Same inputs → identical output. No clock, no RNG; any phrasing
  rotation is seeded by the ISO date (mirrors `state.py._variant`).

The banned **causal tokens** and required **hedge tokens** live as explicit lists in
`synthesis.py` and are the backbone of the test suite (`find_causal_tokens`,
`find_hedge_tokens`). Adding a new template that violates an invariant fails CI.

---

## 3. Architecture — two layers, three signals, one wall

```
                         today.build_today(...)   ← the pure composer (already exists)
                                   │
        ┌──────────────────────────┼───────────────────────────────┐
        ▼                          ▼                                ▼
  per-mover "why"          co-occurrence                  relationship narrative
  (DESCRIPTIVE)            (STRUCTURAL)                   (RELATIONAL)
  self-grounded;           theme-tag counts;              curated directed map;
  one series only          no authored causal edges       tier-gated honesty
  ── BUILT ──              ── BUILT (minimal themes) ──    ── SCAFFOLDED, content deferred ──
        │                          │                                │
        └─ cannot overclaim ───────┴─ cannot overclaim ─────────────┴─ honesty gated by INV-3
```

**The wall:** layers (a) and (b) are **100% data-derived** — they author *no* causal
content, so they *cannot* overclaim. Layer (c), the only one that can make a relational
claim, draws *only* from a curated, version-controlled map whose every edge carries an
explicit strength tier; the composer's grammar is chosen by that tier. There is no path by
which a causal sentence appears without a human-authored, tier-tagged edge behind it.

### Signal 1 — the per-mover "why" (`synthesis.mover_why`)

A mover row in `today.json` carries `sparkline` (the primary indicator's numeric series,
~40 points), `stat_label`, `stat_value`, `delta`, `dir`. It carries **no dates and no
cadence** (config stores neither; cadence is inferred elsewhere from observation dates we
don't have here). So the why is **period-neutral** and built from three self-grounded
signals over the sparkline:

1. **Streak** — ≥ `MIN_STREAK` (3) consecutive same-direction steps → "up 4 readings in a
   row" / "down 3 readings running." (Mirrors `explain.streak`; "readings" avoids fake
   "months.")
2. **Fresh extreme** — the latest value is the max (or min) of the shown series and the
   series actually moved there → "a fresh high for the period shown" / "the lowest in this
   view."
3. **Outsized step** — `|latest step| ≥ OUTSIZE_SIGMA` (2.0) × stdev of the prior steps →
   "its sharpest move in this view." (The same z-logic that made it a mover, surfaced as
   prose.)

`mover_why` combines **at most two** clauses (priority: streak, then extreme, then
outsized), colon-prefixed with the stat label (`"Food: …"` — the house plural-agnostic
convention from `explain.py`). It returns **`""`** when nothing clears its bar — honest
silence; the card simply shows no why line (today's Dollar mover is exactly this case).

### Signal 2 — structural co-occurrence (`synthesis.cooccurrence`)

A minimal **theme map** (`synthesis.THEMES`: `lens_id → theme`) groups lenses by *subject*
(what they measure), not by cause. `cooccurrence` takes the day's `pressure` rows, finds
the **largest stressed theme cluster** with ≥ `MIN_THEME` (2) members, and emits a count:

> "Most of today's pressure is one story: **prices** — fuel, food, electricity, and the
> cost of living are all stressed."

A theme tag is a *categorization* (reviewable, reversible), **not a causal edge**. The
sentence is a pure count over a shared subject → satisfies INV-2 by construction. When no
theme reaches 2 stressed members, `cooccurrence` returns `""` (silent).

### Signal 3 — relationship narrative (`synthesis.compose_relationships` + `relationships.py`)

A **curated directed map** of macro relationships. Each edge:

```python
{
  "source": "<lens_id or indicator key>",   # the antecedent
  "target": "<lens_id or indicator key>",   # the consequent
  "strength": "definitional" | "empirical" | "co-occurrence",
  "link": "<plain-English connector phrase>",  # tier-appropriate grammar baked in
  "note": "<why this edge exists — the review surface>",
}
```

The composer activates an edge **only when both endpoints are "in play" today** (stressed,
moving, or otherwise flagged in `today.json`), then renders it with **tier-gated grammar**
(INV-3). The map content is **near-empty in this branch** (one illustrative placeholder
edge per tier, clearly marked `PLACEHOLDER`), but the engine + honesty gating + tests are
**complete** — authoring later is "append reviewed lines; the grammar and tests already
enforce honesty." See §6 for the deferred-content plan and §8 for mockups.

---

## 4. The six design questions, resolved

**(1) How are connections sourced — curated, data-derived, or hybrid? Defend vs. "no black box."**
**Hybrid, with a hard wall (§3).** Per-mover why and co-occurrence are *data-derived* (no
authored causal content → cannot overclaim). The relationship narrative is *curated*,
because empirical macro relationships are **not** reliably derivable from this site's
series, and auto-mined correlations would be the exact black box the site rejects. A
curated, version-controlled, plain-English map with per-edge strength tiers and a `note`
justifying each edge is the **opposite** of a black box — it is the most transparent
possible form, reviewed the same way Michael already reviews the `state.py`/`today.py` copy
banks (in the spec / edit-there-first).

**(2) What grounds each per-mover "why"?**
Only the mover's own primary-indicator `sparkline` (already in `today.json`) via
streak / fresh-extreme / outsized-step, plus its stat label. No external series, ever
(INV-1).

**(3) Surface, and how it stays non-templated.**
- Per-mover why → a muted sub-line inside each mover card on the baked brief
  (`briefpage._movers`) and the second clause of each mover row in the email
  (`digest._changed_rows`).
- Co-occurrence → one line directly under the verdict panel ("the read beneath the read").
- Relationship narrative (deferred content) → a lead sentence in "What changed today" when
  an edge is active.
Non-templated because: (i) the why combines three independent grounded signals
*situationally*, so different movers get structurally different lines; (ii) it returns
`""` rather than forcing a line, so cards vary between having / not having a why; (iii) any
fixed phrasing rotates on a date seed (INV-4-safe). Lens-page placement of the why is
**deferred** (the baked `#baked-read` block is a separate surface; not in this scope).

**(4) How is it unit-tested for honesty?**
The four invariants of §2, each a test: the causal-token linter over every generated
string; the "names no other lens/category" structural check for per-mover whys; the
tier↔grammar match for relationship sentences (synthetic edges of each tier prove the
grammar); plus determinism (same input → same output) and grounding (a known up-streak
fixture yields "in a row"; a flat fixture yields `""`; a 4-member theme cluster yields the
count). Honesty is therefore a property the build *enforces*, not a hope.

**(5) Quiet-day behavior.**
Most days are quiet; the layer **never manufactures drama**:
- Per-mover why: attaches only to movers that exist (z-scored) and only when a signal
  clears its bar; otherwise omitted. On a calm board the movers' whys are neutral
  descriptions ("up 3 in a row"), never alarming.
- Co-occurrence: silent unless ≥2 pressure points share a theme.
- Relationship narrative: silent unless an authored edge has both endpoints active (and the
  map is near-empty now, so silent in practice this session).
An all-clear day therefore produces **no synthesis line at all** — the verdict already says
"calm," and we add nothing.

**(6) Where the map lives + how Michael reviews it.**
`scripts/lenses/relationships.py` — a plain Python list of edge dicts, one per line with a
`note`. Version-controlled; the **diff is the review surface** (same model as the copy
banks). A test (`test_synthesis.py::TestRelationshipMapIntegrity`) validates every edge:
known endpoints, valid tier, non-empty `link`/`note`, and **tier↔phrasing consistency** (an
`empirical` edge whose `link` lacks a hedge token fails CI). Authoring later = appending
reviewed lines; a dishonest edge cannot pass.

---

## 5. Modules & wiring

**New — `scripts/lenses/synthesis.py`** (pure; no network, no disk I/O):
- signal helpers: `_streak`, `_fresh_extreme`, `_outsized` (all over a numeric list);
- `mover_why(mover) -> str` (INV-1);
- `THEMES`, `THEME_LABELS`, `cooccurrence(pressure_rows) -> str` (INV-2);
- honesty primitives: `CAUSAL_TOKENS`, `HEDGE_TOKENS`, `find_causal_tokens(text)`,
  `find_hedge_tokens(text)`, `names_other_subject(text, exclude)`;
- relationship engine: `active_relationships(edges, active_keys)`,
  `relationship_sentence(edge)`, `compose_relationships(edges, active_keys, cap) -> list`.

**New — `scripts/lenses/relationships.py`** (data only): `RELATIONSHIPS` (near-empty +
placeholders) and `active_keys(today_json)` (which lens ids / indicator keys are "in play"
today). Kept separate from the engine so the *content* Michael reviews is isolated from the
*logic* that's already proven.

**Changed — `scripts/lenses/today.py`** (`build_today`): after assembling `top_moves`,
attach `m["why"] = synthesis.mover_why(m)` to each; add
`today_json["synthesis"] = {"cooccurrence": …, "relationships": …}`. Additive and guarded
(wrapped like the existing `state` try/except so a synthesis hiccup never loses the brief).

**Changed — `scripts/lenses/briefpage.py`** (`_movers`): render `m["why"]` as
`<div class="hub-why">…</div>` when present; render the co-occurrence line under the
verdict panel.

**Changed — `scripts/lenses/digest.py`** (`_changed_rows`): append the why to the mover
row body.

**Changed — `dashboards/lens.css`**: add `.hub-why` (small, muted, italic; sits between the
read and the sparkline).

**Tests:** new `test_synthesis.py` (the bulk — engine + four invariants); extend
`test_today.py` (why attached, synthesis block present, additive guard), `test_briefpage.py`
(why + co-occurrence render), `test_digest.py` (why in email); update the
`today_sample.json` fixture with a `why` + `synthesis` block.

**Not run this session:** `refresh_lenses.py` / `--dry-run` (it overwrites `data/` and the
baked publication surfaces). The live brief HTML rebakes automatically on the first CI run
after merge. Worked examples (§7) are produced by calling the pure functions on the
*committed* `data/brief/today.json`, writing a throwaway preview to `%TEMP%` — never to the
repo.

---

## 6. Deferred to the next session (Michael's call)

- **Author the relationship map.** ~15–30 edges across the obvious macro spine
  (inflation → real income [definitional]; mortgage rates → housing demand [empirical];
  credit spreads ↔ risk sentiment [co-occurrence]; etc.), each with a `note`. This is
  economist-curated editorial; the engine + honesty tests already exist, so this is content
  entry, not engineering.
- **The map-driven lead sentence** in "What changed today" (the placement is wired but stays
  silent until edges exist). Mockups in §8 show the intended voice.
- **Lens-page placement** of the per-mover why (the `#baked-read` block is a separate
  surface).

---

## 7. Worked examples (verified on real data — 2026-06-16)

Produced by running the built code (`today.build_today` → `briefpage.render_brief`) over
the **committed** category `index.json` files — i.e. exactly what CI will bake after merge.
Nothing was written to the repo; a styled preview was emitted to
`%TEMP%/ba-synthesis-preview/brief-preview.html`.

**Verdict (unchanged) + the new co-occurrence line beneath it:**
> *The economy is holding up, but not without strain: energy and commodity costs are
> squeezing budgets and household finances are stretched thin, while banks are solid and
> markets are calm.*
> **Four of today's pressure points are about the cost of living — fuel, food and
> commodities, overall inflation, and electricity.**

That second line is the synthesis: 14 things warrant attention today, and the layer states
the honest fact that **four of them are the same cost-of-living story** — a count over a
shared subject, no causal claim. (Causal-token linter on the sentence: none.)

**Per-mover "why" (the new italic line under each mover's read):**

| Mover (card already shows) | New "why" line |
|---|---|
| Commodities · **Food 30.20%** ▲18.60% | *Food: up 7 readings in a row, to a fresh high.* |
| Electricity · **Power price 18.83¢/kWh** ▲ | *Power price: up 3 readings in a row, to a fresh high.* |
| Scoreboard · **S&P 500 7,554** ▲123 | *S&P 500: up 3 readings in a row — its sharpest move in this view.* |
| Dollar · **Dollar YoY −0.68%** ▼ | *(no line — nothing cleared the bar; honest silence)* |
| Household · **Saving rate 2.60%** ▼ | *Saving rate: down 3 readings in a row, to its lowest in this view.* |

Every why is grounded in that mover's **own** sparkline (the streak count, the fresh
extreme, the outsized step are all computed from the series in the card), names no other
series, and carries no causal token. The Dollar mover demonstrates the quiet-day instinct:
when nothing is defensibly notable, the layer says nothing rather than inventing a story.
The S&P line shows a market-price mover described as pure momentum (no good/bad, no cause).

## 8. Mockups — the deferred relationship narrative (to vet voice for next session)

These are **illustrative**, hand-written to the tier grammar the engine enforces — what the
map-driven sentence *would* read like once edges are authored:

- **definitional:** "Real income is pay after inflation — so with the cost of living still
  hot, household purchasing power keeps slipping unless wages catch up."
- **empirical (hedged):** "Mortgages near 7% have historically cooled buyer demand, and
  affordability is already stretched — a combination that has preceded past slowdowns in
  sales."
- **co-occurrence:** "The same week food and fuel costs jumped, households' saving rate fell
  to a new low — a cost squeeze and a thinner cushion showing up together."

Each is honest under §2: the definitional one states an identity; the empirical one hedges
and adds a co-occurrence rather than a bare cause; the co-occurrence one conjoins without
claiming either drives the other.

---

## 9. Out of scope / non-goals

- No LLM (see DECISIONS-PENDING D4). Rules + curated content only — the "no black box"
  promise is load-bearing.
- No auto-mined correlations presented as relationships.
- No new data sources; this layer re-reads what `today.json` already carries.
- No forward/predictive claims in the why (those are the predictions phase; a mover why
  describes a move that already printed).

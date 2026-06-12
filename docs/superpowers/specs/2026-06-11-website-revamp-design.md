# Website Revamp — Philosophy, IA & Navigation (SIGNED OFF 2026-06-12)

**Date:** 2026-06-11 · **Status:** SIGNED OFF — Michael resolved the §12 decision register on 2026-06-12: ① verdict-led merge, ② **the merged surface keeps the "Today's Brief" name at `/dashboards/brief.html`** (this supersedes every `/today.html` reference below — see §12 for the consequences, which *simplify* migration), ③ V2 category-sentence tiles, ④ clean cut of `data/state/today.json`, ⑤ Appendix A copy approved with a final polish pass delegated to the implementer. Decisions below were drafted autonomously from his stated principles; the **[DECISION]** flags record what was chosen and why.

**Inputs:** audit findings (`2026-06-11-website-revamp-audit-findings.md`) and five comparison mockups with desktop+mobile screenshots in `docs/superpowers/mockups/2026-06-11-revamp/` (open them at `http://localhost:8000/docs/superpowers/mockups/2026-06-11-revamp/<name>.html` while serving the repo, or view the baked `.png`s).

---

## 1. Philosophy: four surfaces, one job each

The audit found ~5 distinct content blocks spread across 12 navigable surfaces, with the same sentences rendering in up to four places. The revamp collapses the site to **four destinations plus the lens layer**, each with one job, and makes every page reachable from a single persistent top nav:

| Surface | One job | Primary persona |
|---|---|---|
| **Home** (`/`) | Front door: identity + the one-glance board (verdict line + 8 category tiles). Routes you to Today or into a category. | First-time visitor |
| **Today** (`/today.html`, new) | The daily read: verdict, what changed, what we're watching, where the pressure is. *The* page a returning reader opens every morning. Absorbs Today's Brief + The State of Things. | Returning daily reader |
| **Dashboards** (`/dashboards/` + 8 category hubs) | The reference catalogue: find any lens. The hub indexes categories; category hubs hold the lens cards. | Explorer / deep-diver |
| **Track Record** (`/dashboards/track-record.html`) | Accountability: how our published predictions have scored. Unchanged in content; finally reachable. | Skeptic / evaluator |

Lens pages stay exactly as they are (the audit's strongest layer) except for their navigation header (§4).

**Persistent top nav, every page:** wordmark (→ home) + `Today · Dashboards · Track Record · About`, with the active destination highlighted. This single change fixes the audit's B4 (Track Record orphaned), B5 (no nav entries), and B6 (home never names its destinations).

**What gets deleted:** `state.html` and `brief.html` as surfaces (redirect stubs remain), the hub's verdict + Brief panels, the hub's 33-card wall, the home tiles' second badge. Nothing else moves; the visual language (lens.css dark theme, badges, cards) is untouched — this is an IA revamp, not a restyle.

**Growth headroom:** a 9th/10th category = one tile on home, one card on the hub, one chip-row — no page gets longer than a screen-and-a-half. Role-based views (V2 of State's slicer idea) would become *filters on Today*, not new surfaces. Deeper predictions land in Today's "watching" block and Track Record. Nothing in this IA needs to be re-broken later.

## 2. Today — the merged daily surface

**Mockups:** `today-v1.html` (verdict-led, **recommended**) vs `today-v2.html` (change-led).

**[DECISION] Verdict-led (A1).** Order: the returning reader's questions, in order: *How are things? → What changed since yesterday? → What's coming? → Where exactly is the pressure? → Status of all the categories.* A2 (change-led, verdict demoted to a standfirst) optimizes for the reader who already knows the standing picture, but on quiet days (the majority — today's real data has exactly 1 transition) it leads with near-nothing. A1 leads with the site's best sentence every day. Runner-up: A2.

Page structure (all content already exists in the two source pages — nothing new is authored except section titles):

1. **Verdict** — State's badge + assembled sentence, in the existing `.state-panel` style. The page's only H1-adjacent element.
2. **What changed today** — Brief's transitions (worsening first), then Brief's biggest movers as `hub-card`s. Quiet-day copy: "No status changes today." Movers that *are* transitions aren't duplicated (already guaranteed by `rank_moves`).
3. **What we're watching next** — State's predictions block verbatim (consequence-ranked, links to Track Record). Renders only when `open.json` has entries — same degrade rule as today.
4. **Where the pressure is** — replaces *both* State's pressure-point cards *and* the Brief's three card-wall sections. One section, compact **rows** (category label · lens title · badge · headline), grouped On alert → Elevated → On watch, with the existing `#alert/#elevated/#watch` anchors preserved (home's counts strip deep-links to them). This is the audit's A3/A4 fix: standing state appears once, in scannable form, and a lens can no longer appear twice.
5. **Across the dashboards** — all 8 category chips with blended badges (replaces State's "Holding steady", whose title contradicted its watch chips — audit C3). Canonical category order.
6. Footer: data sources + RSS link.

**What is cut outright:** the Brief's full-card treatment of standing lenses (cards survive only for movers, where the sparkline shows the move); State's "What changed today" pointer section (self-resolving); both pages' cross-references to each other.

**Naming. [DECISION] Page title "Today", URL `/today.html`** (root — it's the site's daily product, not one dashboard among many; short and shareable). The RSS feed keeps the "Today's Brief" channel branding (§6). Runner-up: keep `brief.html` as the URL and "Today's Brief" as the title — less migration, but cements the asymmetric absorb (State readers land on a "Brief") and misses the chance to put the daily page at the root.

### Pipeline & data (`scripts/`)

- **New `lenses/today.py`** — a thin composer: calls `brief.build_brief(...)` and `state.build_state(...)` (both stay pure and untouched, with their tests) and emits one `data/today/today.json`: `{generated_at, verdict, changed: {transitions, top_moves}, watching, pressure: [...], categories: [...], status_counts, lenses}`. The pressure list is the flat severity-grouped row data (lens id/title/category/href/status/headline), derived from the same flatten the brief already does.
- **`refresh_lenses.py`**: new `--today` flag replacing `--brief --state`; it runs the same two builders through `today.py`, writes `data/today/today.json`, and keeps writing `data/brief/_prior_state.json` (transition memory) and `_feed_items.json` exactly as now. `--brief`/`--state` become deprecated aliases for `--today` (warn + run it) for one release, then are removed. Workflows (`refresh-fred.yml`) swap `--brief`/`--state` steps for one `--today` step.
- **[DECISION] Stop writing `data/brief/today.json` and `data/state/today.json`** in the same commit that re-points all fetchers (home, today page) to `data/today/today.json`. The site is the only consumer; a transition period would just be dead weight. Runner-up: dual-write for a week.
- **JS:** `state.js` + `brief.js` merge into one `today.js` with the same render modes — `page` (fills today.html), `line` (home hero verdict), `strip` (home counts line). The hub panel mode is deleted (§5). `predict.js`, `hub.js`, `lens.js` untouched by this phase.

### Migration & continuity

- `dashboards/state.html` and `dashboards/brief.html` become meta-refresh redirect stubs to `/today.html` — the exact pattern of `dashboards/economic.html`. All internal links re-point in the same commit (home hero, home strip, any `BRIEF_HREF` constants — `state.py`'s `BRIEF_HREF` becomes `TODAY_HREF = "/today.html"`).
- **`/feed.xml` continuity:** path unchanged; channel title stays "Bailey Analytics — Today's Brief" (subscribers' readers key on the URL, and the title is still truthful — the feed *is* the daily brief). New items' `<link>` points at `/today.html`; old items' brief.html links keep working via the redirect. `feed.py` needs only the link constant changed.
- Old anchors `brief.html#alert` etc. survive as `/today.html#alert` (redirect stubs can't carry fragments reliably, but the only fragment-links are on-site and get re-pointed).

## 3. Home

**Mockup:** `home-tiles.html` (three treatments side by side: current / V1 attributed callout / V2 category sentence).

- **Hero:** unchanged except the verdict line's link target (`/today.html`) and a labeled affordance: the verdict line gets a trailing "Today's full read →" so the destination finally has a name on the home page (audit B6). The counts strip ("3 alert · 8 elevated · 4 on watch") stays and deep-links to `/today.html#alert` etc.
- **[DECISION] Tiles: V2 — one badge, one category-level sentence.** The tile speaks at category altitude: blended badge + an authored sentence keyed to (category × status), so badge and words *cannot* contradict (the audit-C1 killer). Worst-lens detail isn't lost — it's one click away on Today (pressure rows) and the category hub. The stat line keeps the worst lens's key stat with its label (the tile's "number to glance at"), and the sparkline stays. Runner-up: V1 (single category badge + the worst-lens headline attributed via a named status-dot line that links to the lens) — keeps a real sentence about real data on the tile and fixes attribution, but on an OK-category tile the scary lens sentence still dominates, and the two-link tile is fussier on mobile. If Michael prefers keeping lens headlines on tiles, V1 is the spec'd fallback; the mockup shows both.
- **Tile copy bank:** extends `state.py`'s authored-copy approach: 32 fully-authored sentences (8 categories × 4 severities, **Appendix A**) in `today.py`, baked per category into `data/today/today.json` (`categories[].sentence`) — pipeline change rides with Phase A. A pure lookup; no per-day authoring, no generation rules.
- **Tile click → category hub** (unchanged). With V2 there's no longer a bait-and-switch (audit B7) because the sentence describes the category, not a lens.
- **Mobile tiles:** keep the compact chip (badge + stat) but add the V2 sentence clamped to two lines — mobile currently loses the story entirely (audit C2). If it doesn't fit the 2-col grid, drop to 1-col on ≤480px.
- **Header fix:** home adopts the standard fixed wordmark+nav header (wordmark hidden on home — the H1 serves), nav becomes the 4-item set, and the H1/nav overlap at 390px (audit D1) is fixed by giving the hero `padding-top` clearance like every other page.

## 4. Lens-page navigation (journey-aware)

**Mockup:** `lens-nav.html` (both arrival states).

- **Breadcrumb** (new, always present): `Dashboards › <Category> › <Lens>` — hierarchy made visible and fully clickable. The category crumb points at the *real* category hub — which retires the mislabeled "← Economic Lenses → main hub" default (audit B2): economic lens pages pass their category hub `/dashboards/economic/` like every other category. Implemented in `lens.js render()`; per-page opts already carry the category name/href.
- **Journey-aware back chip** (replaces the hardcoded back link): on render, `lens.js` inspects `document.referrer`; same-origin referrers map to a label: `/today.html` → "← Back to Today", `/` → "← Back to home", a category hub → "← <Category>", anything else/empty → "← <Category>" (the hierarchy default). No sessionStorage, no router — one referrer check, progressive enhancement, zero behavior change for crawlers/noscript (static fallback markup keeps the category link).
- **Back-link convention site-wide:** category hubs → "← Dashboards"; Track Record → "← Today" (it's reached from Today's watching block; also in top nav anyway); Today/Dashboards are top-nav destinations and carry **no** back link (audit B3's three conventions become one rule: *back links climb exactly one level; top-nav destinations don't have them*).

## 5. Dashboards hub & category hubs

**Mockup:** `hub-slim.html`.

- **Hub slims to the category index:** lede + 8 **category cards** (title, blended badge, the existing category description, and one chip per lens with a severity dot — chips are visual summaries, the card is one link to the category hub). No verdict panel, no Brief panel (both jobs now live on Today, one nav-click away), no 33 lens cards. Desktop height goes from ~6,100px to ~1,400px; the audit-A5 duplication (hub sections ≡ category hubs) is resolved by making the two layers different: hub = categories, category hub = lenses.
- **Category hubs unchanged** in content (they keep the full `hub-card` lens grids and "Data last changed" stamps) — they gain the new top nav and keep "← Dashboards". They're now the *only* place with the full-card lens grid, which is their job.
- `hub.js` gains a `loadCategoryCards` renderer for the slim hub (reads the existing per-category `index.json`s — status, lens titles, statuses; no pipeline change). `loadHubGrid` stays for category hubs and Today's movers.

## 6. Track Record & predictions

- Top-nav slot (the orphan fix). Content unchanged.
- Empty state (audit D4): the two stat cards show "first grades pending" copy instead of bare em-dashes until `track-record.json` has grades.
- Today's watching block keeps the "Our track record →" link; `predict.js` next-print blocks on lens pages untouched.

## 7. Bug fixes riding along (from the audit, all in scope)

- D1 mobile home header overlap (fixed by §3 header).
- D3 duplicate x-axis tick labels: a headless sweep of all 33 lens pages × 3 ranges (2026-06-11, `sweep-report.json`) found 163 affected chart-range combos — every 5Y view (113), most Max views (32), and 18 default views, including a month-label variant ("Jun, Jun, Jun…" on crypto-structure's young daily series). All are one bug: the `lens.js` tick callback truncates labels to year (or month) without deduping. Fix: the callback returns `""` when the rendered label equals the previous tick's rendered label. The same sweep found **no other bug classes** (no scoreboard dashes, no console errors beyond the expected predictions 404s).
- D5 pressure-row wrap inconsistency: superseded — the merged page's pressure rows use one fixed row layout.

## 8. Phasing (each independently shippable, in order)

- **Phase A — Today merge** (pipeline + page): `today.py`, `--today` flag, `data/today/today.json` (+ `categories[].sentence` copy bank), `today.js`, `/today.html`, redirect stubs, feed link constant, workflow step swap, re-point home fetchers. Tests: `test_today.py` (composer output shape, pressure grouping, sentence bank coverage for all 8×4 keys), existing brief/state tests stay green untouched.
- **Phase B — Navigation**: 4-item top nav on every page (33 lens pages + hubs + home + track-record + about), breadcrumbs + journey-aware back in `lens.js`, back-link convention sweep, home header fix, D3 tick dedupe. No pipeline changes.
- **Phase C — Home & hub simplification**: V2 tiles (consumes Phase A's sentences), mobile tile sentence, slim hub via `loadCategoryCards`, hub panel deletions.
- Each phase: branch → tests → `/code-review` → fix findings → merge/push **only on Michael's go** (standing rule).

Phase A first because B's nav needs a Today destination to point at, and C's tiles consume A's baked sentences.

## 9. Out of scope

Visual theme, lens-page content/charts, the predictions engine, role-based views (future filters on Today), any data-source work. The `EconomicDashboard/` prototype is untouched.

## 10. Prototype validation (2026-06-11 evening, autonomous session)

Run before implementation to de-risk the spec; scratch code only (temp dir + mockups dir), no site code.

- **Composer (Phase A):** a scratch `compose_today.py` built the §2 `today.json` shape from the repo's real `index.json`s by calling `brief.build_brief` + `state.build_state` unmodified — verdict, 5 movers, 15 pressure rows, 8 category chips, and the quiet-day path (0 transitions) all came out right. Rendered in `mockups/2026-06-11-revamp/today-v1-live.html` (+ PNGs) with zero console errors. Two data-contract findings for the implementation plan: (1) `build_brief` strips `headline_read` from its public `lenses` list — the composer must carry it through for the pressure rows; (2) `top_moves` records also need a `headline` field baked in, so the Today page stops re-fetching all 8 `index.json`s client-side just to decorate mover cards (the current brief.html behavior).
- **Journey-aware back (Phase B):** prototyped the `document.referrer` mapping and drove it headless through five arrival paths — from Today → "← Back to Today"; from a category hub and direct/bookmark → static category fallback; after a meta-refresh redirect hop the referrer still resolves. Mechanism confirmed. Caveat for the plan: it relies on the browser-default `strict-origin-when-cross-origin` referrer policy (full path is sent same-origin) — don't ever add a stricter `<meta name="referrer">`.
- **Redirect stubs:** meta-refresh lands correctly; URL **fragments do not survive** the hop (`redirect.html#alert` → `today.html`), confirming §2's requirement that all on-site fragment links be re-pointed in the same commit.

## 11. Appendix A — V2 tile copy bank (draft for Michael's editorial pass)

8 categories × 4 severities. Voice matches `state.py`'s clause banks; elevated/alert rows reuse its `PRESSURE_CLAUSES` verbatim (capitalized) so the site speaks one language; ok rows extend its `STEADY_CLAUSES`. Lives in `today.py` beside the verdict copy bank; baked as `categories[].sentence`.

| Category | ok | watch | elevated | alert |
|---|---|---|---|---|
| Economy | The core economy is steady — no major warning lights. | Mostly steady — a corner or two of the economy runs hot. | The core economy is under real strain. | The core economy is flashing serious warnings. |
| Consumer | Households are keeping pace — spending, credit, and savings look healthy. | Households are keeping up, but cracks are starting to show. | Household finances are stretched thin. | Households are in real distress. |
| Banking | Banks are solid — capital, profits, and loan books look healthy. | Banks are solid overall, but parts of the system bear watching. | Cracks are showing in the banking system. | The banking system is under serious stress. |
| Business | Business health is holding up — profits and investment look solid. | Business health is holding up, but conditions are tightening at the margin. | Business health is deteriorating. | Corporate America is in real trouble. |
| Markets | Markets are calm — no stress in financial conditions. | Markets are mostly calm, but a few cracks are showing. | Financial markets are under stress. | Financial markets are in turmoil. |
| Energy | Energy costs are behaving — no unusual pressure at the pump or on the power bill. | Energy costs bear watching — some prices are drifting the wrong way. | Energy and commodity costs are squeezing budgets. | Energy and commodity costs are surging. |
| Housing | Housing is balanced — prices, supply, and rents read normal. | Housing is mostly balanced, but parts of the market are drifting out of balance. | The housing market is out of balance. | The housing market is in serious trouble. |
| Global | The global backdrop is quiet — trade, growth, and currencies read calm. | The global backdrop is mostly quiet, but risks are ticking up. | The global backdrop is turning hostile. | The global economy is in serious stress. |

This replaces §3's "authored-ok-clause + suffix rule" sketch with fully authored sentences — simpler (a pure 32-entry lookup, no suffix generation) and every word reviewable. A new 9th category needs 4 sentences or it degrades to the generic `state.py` fallback clause.

*Polish pass (2026-06-12, per decision ⑤):* banking-watch no longer presumes exactly one stressed lens ("parts of the system bear watching"); markets-watch reuses the site's established "a few cracks are showing" voice instead of the off-register "jumpier"; energy-ok says "on the power bill" instead of "the plug"; housing-watch says "drifting *out of balance*" so the watch row sets up the elevated row's "out of balance."

## 12. Decision register — RESOLVED by Michael, 2026-06-12

1. **Today page shape: verdict-led A1.** ("I like the v1 verdict led.")
2. **Naming/URL: the runner-up won — "Today's Brief" stays at `/dashboards/brief.html`** and absorbs The State of Things. Consequences (all simplifications vs. the drafted `/today.html` route):
   - `feed.xml` is untouched — channel, item links, guids all already point at `brief.html`.
   - Only `dashboards/state.html` becomes a redirect stub (→ `/dashboards/brief.html`); no new root page.
   - The home counts strip's `#alert/#elevated/#watch` deep links keep working unchanged.
   - `data/brief/today.json` remains the surface's JSON, **extended flat** (adds `verdict`, `watching`, `pressure`, `categories[].sentence` beside the existing `transitions`/`top_moves`/`status_counts`/`lenses` keys) — so `feed.build_item` and the existing strip/panel renderers read it unchanged.
   - The pipeline keeps `--brief` as the flag (no `--today`); `--state` becomes a deprecated alias; `refresh_state`/`STATE_OUT_DIR` are removed; the composer module is still `lenses/today.py` (it builds *today's* brief).
   - Top-nav label (§1): **Today's Brief**. Journey-back label (§4): "← Back to Today's Brief", referrer match `/dashboards/brief.html`.
3. **Home tiles: V2 category-sentence.** ("Encourages clicking through and is cleaner.")
4. **Clean cut** of the superseded `data/state/today.json` in the same commit that re-points its consumers.
5. **Appendix A approved**; final wording polish delegated ("I trust your judgment") — the polish is already applied to Appendix A below (banking-watch, markets-watch, energy-ok, housing-watch rows reworded; rationale noted inline).

# Bailey Analytics — Full-Site Audit Ledger (2026-07-03)

Session: autonomous full-site audit per `Repositories/bailey-analytics-audit-prompt.md`.
Branch: `audit-2026-07-03` (from main @ c618de9, the 2026-07-03 06:00 UTC cron refresh). Local only — never pushed, never merged.

**Status legend:** `open` / `fixed@<hash>` / `proposed` / `accepted-risk` / `unverified`.
**Severity:** Credibility / Critical / High / Medium / Low / Polish.
**ID scheme:** `P<pass>-<nn>`.

## Progress

- [x] Setup: branch created, ledger committed
- [x] Pass 0 — Recon
- [ ] Pass 1 — Correctness & code quality
- [ ] Pass 2 — Logic & statistical honesty
- [ ] Pass 3 — UX & site flow
- [ ] Pass 4 — Content & legibility
- [ ] Pass 5 — Aesthetics
- [ ] Pass 6 — Metrics & presentation choices
- [ ] Pass 7 — Review panel
- [ ] Pass 8 — The rulebook itself
- [ ] Pass 9 — Data science & sophistication
- [ ] Pass 10 — Implementation
- [ ] Pass 11 — Verification
- [ ] Pass 12 — Final report & next-moves memo

## Pass 0 — Recon record

**Product summary.** baileyanalytics.com is a zero-build static site (GitHub Pages behind Cloudflare) that presents a daily plain-English read of the US/global economy: 8 dashboard categories × ~4 lenses each (33 lens pages), each lens = badge + headline read + scored indicator charts, driven by a Python pipeline that bakes JSON + static HTML surfaces on GitHub Actions crons (daily FRED/markets/energy/housing/consumer/global/business, weekly banking, weekly prediction tournament). Synthesis layers: Today's Brief (verdict + transitions + movers + watching + pressure), per-mover/indicator "why", a 22-edge relationship map, ~107-series published predictions graded against first prints (Track Record), methodology page + in-context scale strips, email digest (Buttondown), RSS, PWA + favorites + light/dark theme, Cloudflare analytics beacon, freshness dead-man's-switch.

**Surface inventory.** Root: home, about, 404, offline, robots/sitemap/feed/manifest/sw + favicon/apple icon. dashboards/: slim hub, brief + 18 dated archive pages + archive index, 33 lens pages (5 economic flat + 7 categories × 4), 8 category hubs (incl. economic/), favorites, methodology, track-record, 2 redirect stubs (state.html, economic.html). JS: lens/hub/brief/predict/scoring/personalize(+core)/favorites/track-record + sw.js; CSS: lens.css (+ inline blocks in home/about/404/offline). Data: 8 category dirs + brief/ + predictions/ (open/recent/track-record/models/ledger + per-cat slices) + methodology/ slices. Both themes; JS and no-JS (baked reads) states; mobile/desktop breakpoints.

**Live-vs-repo drift check (21 surfaces fetched 2026-07-03 ~17:00 UTC):** all byte-identical to checkout except `index.html`, where the ONLY delta is Cloudflare Scrape Shield rewriting the `mailto:` into `/cdn-cgi/l/email-protection` + injecting its decode script. Deployed reality == repo @ c618de9. 404 page serves correctly (HTTP 404 with 404.html body); og image + headers healthy (CF + Fastly caching, max-age=600).

**Notable recon observations (feed into later passes):**
- The CF email-protection wrap means **no-JS visitors see "[email protected]" instead of the real address** on home (and presumably about) — the site's no-JS story is otherwise deliberate (baked reads, noscript fallbacks). → P3 finding candidate.
- `dashboards/state.html` + `dashboards/economic.html` redirect stubs still shipped; retired-surface hygiene is a P1 hygiene item.
- Test suite ~932 tests; JS tests exist only for personalize-core + sw routeStrategy; DOM renderers untested by convention.

## Findings

### Pass 1 / Pass 2 candidates from the pipeline read (verification status per item)

- **P2-01 · Credibility · narrative headlines** — Several static per-status lens headlines name a *specific driver* the data may not support, because `synthesize` picks copy by worst-status alone:
  - `recession-watch.elevated`: "— the yield curve is warning." But `rule_claims` also emits elevated (≥300k), with the curve possibly fine. VERIFIED in code (`narrative.py` HEADLINES + rule_claims).
  - `recession-watch.alert`: "multiple indicators have tripped" — fires when ONE indicator (e.g. Sahm) alerts.
  - `bank-asset-quality.elevated`: "commercial real estate is the pressure point" — lens severity comes only from noncurrent/charge-offs (all-loan aggregates), not CRE.
  - `consumer-credit.alert`: "delinquencies at crisis levels" — TDSP (debt service) ≥13 alone can alert the lens.
  - `housing-home-prices.elevated`: "prices and sales are under strain" (could be only one); `business-investment.alert`: "capex and sales" (could be one).
  - Recommendation: make driver-naming honest — either driver-agnostic copy, or pick copy from the actual worst indicator. Status: open (fix in Pass 10; reader-facing copy → itemize).
- **P2-02 · High · unreachable alert states** — Whole categories can never reach `alert` no matter how bad reality gets: all four banking lenses (max elevated on every rule), market-risk-sentiment (VIX/spreads/NFCI all cap at elevated). Their `alert` HEADLINES copy is dead. In a 2008-scale crisis the site would read "elevated" for banks/markets while housing/consumer hit alert — cross-category incoherence + a hostile-reviewer target ("banking dashboard maxes out at 'elevated' in a banking crisis"). Candidate fix: add historically-grounded alert tiers (e.g. noncurrent ≥3.5% ~2009-scale, VIX ≥40, HY ≥8). Needs Pass 9 backtest evidence before changing bands. Status: open.
- **P2-03 · Medium · rule_unemployment_trend wording** — when delta<0.5 the read claims "steady … near its recent lows", but delta can be up to +0.49pt in a 12-mo slow grind (and the 12-mo window low itself drifts up in a >12-mo deterioration), so "steady near lows" can be false while the badge stays ok. Wording fix: state the delta ("up X pts from its 12-month low") instead of asserting "steady". Status: open.
- **P1-01 · Low · fmtVal twin rounding drift** — `build._fmt` uses Python `round()` (banker's: 2578.5→2578) for `thousands`; JS twins use `Math.round` (half-up: →2579). A hub key-stat baked in Python can differ by 1 from the page value rendered by JS at exact-.5 values. Fix: `math.floor(a+0.5)` in `_fmt`. Status: open.
- **P1-02 · Low · _status_of latent trap** — `build._status_of` feeds rules obs=[("x", value)]; any future ranking/tier rule that calls `_value_year_ago` would crash on `int("x")`. Today all wired rules are level-based (safe). Guard or document. Status: open.
- **P1-03 · Polish · _patch_lens_pages mtime gate** — the gate exists only to skip ~33 JSON parses but created a documented footgun (stale patches after merges; the "touch-data-jsons" workaround). `_patch_region_file` is already content-aware. Removing the gate is behavior-identical and deletes a trap. Status: open.
- **P1-04 · Polish · dead code** — `narrative.rule_rate_trend` self-documented as dead; `dashboards/state.html` + `dashboards/economic.html` redirect stubs (state.html retired 2026-06-12; economic.html redirect since 2026-06-10). Stubs still receive inbound links? Check before removing (sitemap excludes them). Status: open.
- **P2-04 · Low · brief transition memory loses a day on index outage** — if a category index fails to load, its lenses drop from `new_state["statuses"]`; when they reappear changed, old=None → no transition recorded. Self-healing, rare; note only. Status: accepted-risk candidate.

## Notes on solid ground (verified, no finding)
- Live == repo byte-identical on 21 surfaces (only CF email-protection rewrite on home).
- refresh_lenses failure paths: every source guarded, prior-data fallbacks throughout; write paths content-aware; `--dry-run` hazards documented and real.
- synthesis honesty stack (tier-gated map, high-precision linter, self-grounded whys) is as documented; `relationship_sentence` raises on tier violations; `today._safe_relationships` guards separately. 
- `state.classify_shape` "ok excludes pressure" claim holds mathematically up to 11 categories (RMS 2/√N ≥ 0.6 ⟺ N ≤ 11).

## Decision Log

- **D-001** Branched `audit-2026-07-03` from freshly-pulled main (c618de9) rather than the stale `sitewide-polish-2026-06` checkout. Runner-up: audit the checkout as-found. Why: the prompt's safety floor says pull main; the polish branch is already merged/deployed, so main is the live product.

## Deviations

(none yet)

## Blocked

(none yet)

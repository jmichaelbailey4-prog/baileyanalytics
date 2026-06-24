# PWA + Personalization (v1) — Design

**Date:** 2026-06-24
**Branch:** `pwa-personalization`
**Status:** Spec for review (Michael's sign-off)
**Predecessor context:** memory `pwa-personalization-project` (direction agreed 2026-06-24), `site-vision-standalone-resource`, `design-mobile-parity`, `analytics-and-monitoring-project` (baked-beacon / head-stamping precedent).

---

## 1. Goal

Reward returning readers and make the site feel like *their* tool, at **$0 and within the existing zero-build static model**. Two threads:

1. **Personalization** — client-side, `localStorage`-only: **Favorites** (star any lens, see them collected on a Favorites page) and a **remembered default chart range**.
2. **Installable PWA** — a `manifest.webmanifest` + service worker so the site installs to a phone/desktop home screen (standalone window, app icon) and works **offline** with last-seen data.

This is an **engagement/retention** play, not new-reader acquisition (noted honestly in the project memory). It is the cost-smart first rung: if it gets traction, that traction justifies paying later for accounts (cross-device sync) + native apps.

## 2. Scope

**In (v1):**
- Favorites: a ★ toggle on every lens page; a **Favorites page** (`/dashboards/favorites.html`) that collects starred lenses as tiles, with a strong empty state.
- Remembered **default chart range** (1Y / 5Y / Max) across pages and visits, with a sensible floor so low-frequency (quarterly) pages never render too sparse.
- A **"local-only" disclosure** (Michael's explicit ask): preferences live only in this browser, are not an account, reset if the visitor clears site data, and don't sync across devices — *yet*.
- **PWA**: manifest, app icons, service worker (installable + offline), an unobtrusive offline indicator.

**Out (deferred, by prior decision):**
- **Light theme + toggle** → **v1.1 fast-follow.** Highest effort/regression risk (the dark palette is hardcoded across four systems: `lens.css`, `index.html`'s own `:root`, `about.html`'s literal hex with *no* variables, and `lens.js` chart colors). Deferring it de-risks v1 and is a clean standalone follow-up.
- **Accounts / cross-device sync** — needs a backend + security responsibility + a bill that scales with success. `localStorage` delivers ~90% of the value for $0.
- **Push notifications** — needs a backend (subscription storage + send); the email digest already covers re-engagement.
- **Native iOS/Android apps** — recurring cost + a second codebase; the PWA delivers the "download the app" experience for $0.

## 3. Architecture constraints (hard)

- **Zero-build static only.** Hand-written HTML + baked JSON + shared `dashboards/lens.css` & `lens.js`; Chart.js from CDN. No bundler, framework, or backend. The *Python pipeline* may use libraries (Pillow is already a dep).
- **All personalization is client-side `localStorage`.** No server, no cookies sent anywhere, no third-party storage.
- **The three-CSS-places trap** (`index.html` + `about.html` carry standalone inline CSS; `lens.css` is the third). v1 adds almost no shared CSS (favorites/PWA chrome is small and mostly scoped to the Favorites page + tiny shared bits), and the theme work that would *really* exercise this trap is deferred — but any shared chrome added in v1 (e.g., offline banner, nav entry styling) is applied consistently.
- **No shared `<head>`/nav template.** `top-nav` markup is duplicated across **78 files**. Cross-page additions use the established **idempotent Python stamping** pattern (`scripts/tools/seo_heads.py`, `cf_beacon.py`) — never hand-edit 78 files — and the page **generators** (`briefpage.py`) are updated so baked pages match.

## 4. Decisions log (resolved autonomously — for Michael's review)

Each is reversible; flagged ones are one-liners to flip.

| # | Decision | Alternatives considered | Why |
|---|----------|------------------------|-----|
| D1 | Name the collection **"Favorites"** (page + nav + ★ action). | "My Dashboard" (original). | Michael's instruction. |
| D2 | **Favorites nav entry is injected by `personalize.js`** (JS), not hand-added to 78 navs. A **static** "Favorites" link is also added to the Dashboards hub (one file) + `sitemap.xml` for no-JS/crawler discovery. | Static 5th nav item stamped across all pages + generators. | Feature is inherently JS/localStorage; injecting avoids a 78-file blast radius and keeps nav consistent. No-JS users can't have favorites anyway; the static hub link + sitemap keep the page discoverable. |
| D3 | **Installed-app `start_url` = `/dashboards/favorites.html`** (lean into "your dashboard"). **FLAG:** trivially flippable to `/` (home) — one line in the manifest. | `start_url = /` (home), or `/dashboards/brief.html`. | The premise is a *personalized* app; Favorites has a strong empty state (shows the current overall verdict + an invite), so first-launch-before-favoriting is still useful. |
| D4 | **★ on lens pages only** in v1 (the canonical place you decide a lens matters); the Favorites page collects them. | Also add quick-add ★ on hub/home tiles. | YAGNI; tile quick-add is a clean v1.1 add. |
| D5 | **Default range = a remembered preference with a floor.** Explicitly clicking a range button sets the global pref; each lens opens at `max(userPref, pageMinimum)` on the 1Y<5Y<Max scale, so quarterly pages (which pass `defaultRange:"5Y"`) never drop to a too-sparse 1Y. Initial page default does **not** set the pref. | Per-page memory (remember range per lens id); or naive global override (no floor). | Global pref matches "default chart range"; the floor prevents a 1Y pref from breaking banking/credit-stress. Only explicit clicks set it, so a one-off look doesn't silently change global state. |
| D6 | **Service worker is network-first for HTML and `/data/*.json`, stale-while-revalidate for static assets, cache busted per deploy.** | Cache-first everything (classic PWA). | A daily-data site must never serve a frozen page/data when online. See §8. |
| D7 | **JS unit tests via Node's built-in `node:test`** (zero-dep), run locally + documented. Python suite stays the CI gate. | Add Jest/Node toolchain to CI. | Node 24 is available; `node:test` needs no install; keeps the site zero-build and avoids workflow churn. Pure logic (range floor, favorites set ops, SW route choice, storage (de)serialize) is extracted and tested. |
| D8 | **Icons generated once via Pillow** (`pwa_icons.py`, mirrors `ogcard.py`) reproducing the favicon (rounded #0F172A panel + #38BDF8 chart line); committed as static assets. | Hand-make PNGs; or regenerate in the pipeline daily. | Brand-consistent + reproducible + unit-testable; icons are static so no daily rebuild needed. |
| D9 | **No theme-init head script in v1** (only needed for the deferred light theme). v1 head additions are just: manifest link, icon/theme-color meta, `personalize.js` include, SW registration. | Add theme-init now to "future-proof." | YAGNI; add it with the theme in v1.1. |

## 5. Components

### 5.1 Storage layer — `dashboards/personalize-core.js` (pure, dual-exported)
Pure functions, no DOM, with the zero-build dual-export tail (`if (typeof module!=='undefined') module.exports = {...}`) so `node:test` can import them and the browser uses them as globals.

- **Keys** (namespaced): `ba:favorites` → JSON array of `{id, title, category}`; `ba:prefs` → JSON `{rangeDefault}`; `ba:schema` → integer (migration hook).
- **Favorites ops:** `addFavorite(list, fav)` (dedupe by `id`, newest-first or stable order), `removeFavorite(list, id)`, `hasFavorite(list, id)`, `parseFavorites(raw)` / `serializeFavorites(list)` (tolerant of corrupt JSON → `[]`).
- **Range resolver:** `effectiveRange(userPref, pageDefault)` = longer of the two on `{1Y:1,5Y:2,Max:3}`, defaulting unknowns to `1Y`/`pageDefault`. Pure, unit-tested (D5).
- A thin **`store`** wrapper (in `personalize.js`, not core) does the actual `localStorage` get/set with try/catch (private mode / disabled storage → no-throw degrade) and emits a `ba:changed` CustomEvent + honors the cross-tab `storage` event.

### 5.2 Favorite ★ control on lens pages — hook in `lens.js` (mirrors `predict.js`)
This reuses the **exact pattern `predict.js` already uses**: `lens.js` leaves a hook and fires `lens:rendered`; the personalization script binds behavior. `render()` already builds the **badgerow** (`status` badge + "Updated … · N signals") and has `lens.id` + `lens.title` in scope.
- `lens.js` emits a ★ toggle button in the badgerow carrying `data-fav-id`, `data-fav-title`, `data-fav-category` (category derived from the render context — the data URL / `opts.href`). It writes no `localStorage` itself (stays a pure renderer).
- `personalize.js` listens for `lens:rendered`, sets the ★'s initial `aria-pressed` from the store, and binds the toggle (add/remove favorite). Storing `category` with the favorite lets the Favorites page build `lensHref(category, id)` and fetch the right index.
- Accessibility: `aria-pressed` reflects state; label "Save to Favorites" / "Saved to Favorites"; keyboard-operable; `prefers-reduced-motion`-safe.
- Because `render()` wipes `#lens-root` (the baked-read fragment), the ★ is part of the rendered DOM — JS users get it, crawlers/no-JS see the static baked read (unchanged).

### 5.3 Favorites page — `dashboards/favorites.html` + `dashboards/favorites.js`
Reuses existing machinery (no new baked data needed):
- Reads `ba:favorites`, groups by category, fetches **only the needed** category `index.json` files (the same files the home/hubs use), looks up each starred `id`'s lens object, and renders tiles with the **existing `window.renderHubTiles(grid, lenses, hrefFor)`** + `window.lensHref(category, id)` from `hub.js`. Favorites tiles therefore match the hub-card look for free.
- **Empty state:** an inviting panel — "You haven't saved any lenses yet" + a one-line what/why + a button to **Dashboards** + (nice touch) the current overall verdict line from `today.json` so even an empty Favorites is oriented. Makes `start_url=favorites` safe on first launch.
- **Per-tile remove** (★-filled → click to unsave) so the page is self-managing.
- **Preferences section:** shows the current default chart range with a way to change/reset it (transparency for D5), kept minimal.
- **Local-only disclosure** (D-ask): *"Your favorites and preferences live only in this browser, on this device — there's no account. Clearing your browser's site data will reset them, and they won't sync to your other devices. Account sync is on the roadmap."*
- Resilient: a favorited `id` missing from its index (renamed/removed lens) is skipped gracefully (or shown as "unavailable"); a failed index fetch degrades that group, not the page.

### 5.4 Default chart range preference — `lens.js`
- On load, `render()`/`indicatorCard()` compute the start range via `effectiveRange(store.rangeDefault, opts.defaultRange || "1Y")` instead of the raw `opts.defaultRange`.
- A range **button click** writes `ba:prefs.rangeDefault` (explicit intent only).
- No regression: with no pref, banking/credit-stress still open at their declared 5Y; standard pages still open at 1Y.

### 5.5 PWA — manifest, icons, service worker
- **`/manifest.webmanifest`** (static): `name` "Bailey Analytics", `short_name` "Bailey", `description`, `start_url` `/dashboards/favorites.html` (D3), `scope` `/`, `display` `standalone`, `background_color`/`theme_color` `#0A0E14`, `icons` (192/512 + maskable), `orientation` "any".
- **Icons** in `/icons/` generated by **`scripts/lenses/pwa_icons.py`** (Pillow): `icon-192.png`, `icon-512.png`, `icon-192-maskable.png` & `icon-512-maskable.png` (mark inside the ~80% maskable safe zone, bg bled to edges), `/apple-touch-icon.png` (180×180, opaque bg). Reproduces the favicon design for brand continuity.
- **`/sw.js`** (root, scope `/`): see §8 for the caching strategy. Registered from `personalize.js` with `updateViaCache:'none'` so the SW script itself is always revalidated (deploys take effect promptly).
- **`/offline.html`** (root): a tiny branded fallback for navigations that miss the cache while offline.
- **Offline indicator:** `personalize.js` toggles a small fixed banner ("Offline — showing last saved data") on `offline`/`online` events. Unobtrusive; auto-hides when back online; `prefers-reduced-motion`-safe.

### 5.6 Cross-page wiring — `scripts/tools/pwa_head.py` (idempotent stamper) + generator updates
- Mirrors `seo_heads.py`/`cf_beacon.py`: a rerunnable pass that inserts into each hand-written page's `<head>`, marker-guarded, **scoped to root `*.html` + `dashboards/**`, excluding `.git`, `docs/`, `.superpowers/`, and the baked `dashboards/brief/` archive** (the `.superpowers/` exclusion is the lesson from the beacon work):
  - `<link rel="manifest" href="/manifest.webmanifest">`
  - `<meta name="theme-color" content="#0A0E14">`
  - `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`
  - `<script defer src="/dashboards/personalize-core.js"></script>` then `<script defer src="/dashboards/personalize.js"></script>` (order matters — §5.7 load-order note)
- **`briefpage.py`** (and any other generator that emits `<head>`/nav) is updated to emit the same tags so the baked brief + archive pages match; a one-time catch-up stamps existing baked pages (mirrors the beacon back-catalog fix).
- `sitemap.py` adds `/dashboards/favorites.html`.

### 5.7 `personalize.js` (the shared client glue, included on every page)
Small, dependency-free, `defer`. Responsibilities:
1. Registers the service worker.
2. Injects the **Favorites** nav entry into `nav.top-nav` (consistent position; authored to minimize layout shift).
3. Binds the lens-page **★** on the `lens:rendered` event (per §5.2): sets initial pressed state from the store and binds the toggle.
4. Writes the **range preference** on an explicit range-button click; `lens.js` reads the effective range via a `personalize-core` hook when present (else falls back to `opts.defaultRange`).
5. Renders the **offline indicator**.
6. No-ops safely where `localStorage`/`serviceWorker` are unavailable.

> **Load order:** `personalize-core.js` (pure) is stamped before `personalize.js` and before `lens.js`, so `lens.js` can call the range hook during its initial render. All three are `defer`, preserving document order.

## 6. Data flow

```
Lens page:  lens.js render() ──fires──> lens:rendered ──> personalize.js binds ★
   ★ click ──> store.toggleFavorite({id,title,category}) ──> localStorage(ba:favorites)
   range click ──> store.rangeDefault = key ──> localStorage(ba:prefs)

Favorites page: favorites.js
   read ba:favorites ──> group by category ──> fetch needed /data/<cat>/index.json
   ──> map starred ids to lens objects ──> renderHubTiles(grid, lenses, id=>lensHref(cat,id))

PWA: every page <head> ──> manifest + personalize.js ──> SW register
   SW intercepts fetch ──> network-first(HTML, /data/*.json) | SWR(assets) | cache fallback(offline)
```

## 7. Error handling / graceful degradation

- **No JS:** no ★, no Favorites nav entry, no SW. The static baked read still shows on lens pages; the Favorites page shows its no-JS notice; everything else is unchanged. The site is fully functional.
- **`localStorage` blocked/full** (private mode, quota): the `store` wrapper try/catches; favorites silently no-op rather than throwing. The ★ reflects in-memory state for the session.
- **Cleared site data:** favorites/prefs reset — this is exactly what the §5.3 disclosure warns about.
- **SW unsupported / registration fails:** the site works online normally; only offline support is absent.
- **Missing/renamed lens id, failed index fetch:** skipped per-tile / per-group; never blanks the page.
- **Corrupt stored JSON:** parsers fall back to empty.

## 8. The stale-service-worker risk (the #1 PWA hazard) + mitigation

A SW on a **daily-updated** site can serve a frozen site after a deploy if cached carelessly. Mitigations, baked into `sw.js`:
- **Versioned cache** name embedded in `sw.js` (e.g., `ba-cache-<version>`). On `activate`, delete every cache that isn't the current version (and `clients.claim()`).
- **HTML navigations → network-first**, cache fallback (fresh pages online; last-seen offline; `offline.html` if neither).
- **`/data/*.json` → network-first**, cache fallback (fresh data online; last-seen offline). *Never* cache-first data.
- **Static assets (CSS/JS/icons/fonts) → stale-while-revalidate** (instant load + background refresh; one load may be a version behind, then self-heals). These share stable URLs (`lens.css`, `lens.js`), so SWR is the right call.
- **Chart.js CDN → stale-while-revalidate** (URL is version-pinned).
- **`updateViaCache:'none'`** on registration so the browser always revalidates `sw.js`; a new deploy's SW takes over on the next load and purges old caches.
- **Install precache** is a *minimal shell* (core CSS/JS, manifest, icons, `offline.html`) so first offline works; everything else is runtime-cached as visited.

Net: online users always see fresh content; offline users see the last thing they loaded; a deploy never freezes the site.

## 9. Testing

**Python (`unittest`, the CI gate):**
- `pwa_icons.py`: output files exist at the right sizes/modes; apple-touch icon is opaque (no alpha); maskable mark within safe zone (sample corner pixels are background).
- `pwa_head.py`: inserts each tag once; **idempotent** on rerun; correct scope (stamps a sample lens/hub page, **skips** `docs/`, `.superpowers/`, baked `brief/` archive); warns on a page with no `</head>`.
- `briefpage.py`: baked brief/archive `<head>` now includes the manifest link + `personalize.js` + theme-color (extend existing brief tests).
- `sitemap.py`: includes `/dashboards/favorites.html`.

**JS (`node:test`, zero-dep, run locally + documented):**
- `effectiveRange` floor logic (D5) across the pref×pageDefault matrix.
- favorites set ops: add/dedupe/remove/has; tolerant parse of corrupt input.
- SW `routeStrategy(url)` returns the right strategy per request class (HTML / `/data/*.json` / asset / CDN) — pure function extracted from `sw.js`.
- storage (de)serialize round-trips.

**Manual PWA verification (documented in the batched review for Michael):**
- Lighthouse PWA/installability check; install on desktop Chrome + iOS Safari (16.4+) → standalone window + icon.
- Offline: load a few pages, go offline, confirm last-seen data + offline banner + `offline.html` on an unvisited route.
- Deploy-freshness: after a (future) deploy, confirm a hard reload shows new content (network-first working).

## 10. Manual steps for Michael (none external)

Unlike the analytics/distribution work, **v1 needs no Cloudflare/Buttondown/Search-Console actions** — everything is in-repo static files. His steps are just: (1) review this spec, (2) at the batched checkpoint, review the branch + try the install/offline behavior, (3) give the go to merge (= deploy). Post-deploy, watch the first refresh-fred cron to confirm the SW doesn't interfere with the daily data update (it won't — data is network-first — but worth a one-time look).

## 11. Rollout

Branch `pwa-personalization` → spec (this doc) → implementation plan → TDD build → `/code-review` → **batched checkpoint for Michael** (what's done + how to review, decisions w/ recs incl. D3 start_url, manual verification results, ready-to-deploy) → merge to `main` (= deploy) **only on his explicit go**. The light theme follows as a separate v1.1 branch.

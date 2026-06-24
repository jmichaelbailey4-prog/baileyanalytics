# PWA + Personalization (v1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add client-side Favorites + a Favorites page, a remembered default chart range, and an installable/offline PWA to the zero-build static site — all `localStorage` + static files, no backend.

**Architecture:** Pure logic in `dashboards/personalize-core.js` (dual-exported for `node:test`); DOM/browser glue in `dashboards/personalize.js`; the Favorites page reuses `hub.js` (`renderHubTiles` + `lensHref`) + the existing category `index.json`. PWA = `manifest.webmanifest` + Pillow-generated icons + a carefully-versioned `sw.js` (network-first HTML/data, SWR assets). Cross-page head tags come from one source (`lenses/pwa.py`), stamped by `tools/pwa_head.py` and emitted by `briefpage.py`.

**Tech Stack:** Vanilla JS (no modules/bundler), Chart.js (CDN, unchanged), Python 3 + Pillow (already pinned), `unittest` (CI gate) + Node 24 `node:test` (local, zero-dep).

## Global Constraints

- **Zero-build static site.** No bundler/framework/backend. Browser JS is plain `<script>` (no ES modules). Pipeline may use libraries.
- **All personalization is client-side `localStorage`.** Namespaced keys `ba:favorites`, `ba:prefs`. Degrade silently when storage/serviceWorker unavailable.
- **No shared `<head>`/nav template** — `top-nav` is duplicated across 78 files. Cross-page head additions go through `tools/pwa_head.py` (idempotent, marker `<!-- pwa:head -->`, scoped to root `*.html` + `dashboards/**`, **excluding** `.git`, `docs/`, `.superpowers/`, and the baked `dashboards/brief.html` + `dashboards/brief/` archive). The Favorites nav entry is **JS-injected** by `personalize.js`, not hand-added.
- **Single source for the head fragment** (`lenses/pwa.py head_tags()`), imported by both the stamper and `briefpage.py`, so baked + hand-written pages are byte-identical (avoids the re-bake flip-flop the beacon work hit).
- **SW must never freeze a daily site:** network-first for HTML + `/data/*.json`; SWR for static assets; cache busted by `CACHE_VERSION`; `updateViaCache:'none'`.
- **Light theme is OUT of v1** (deferred to v1.1). No theme-init script in v1.
- **Copy rule:** the local-only disclosure must state preferences are device-only, not an account, reset on clearing site data, and don't sync — *yet*.
- **Commit trailer:** end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Run commands** with absolute paths (never `cd <repo> &&`). Test run base: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`; JS: `node --test "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/js/"`.

## File Structure

**New (client):** `dashboards/personalize-core.js` (pure), `dashboards/personalize.js` (glue), `dashboards/favorites.html`, `dashboards/favorites.js`.
**New (PWA static):** `manifest.webmanifest`, `sw.js`, `offline.html`, `icons/icon-{192,512}.png`, `icons/icon-{192,512}-maskable.png`, `apple-touch-icon.png`.
**New (pipeline):** `scripts/lenses/pwa.py` (head_tags + manifest single source), `scripts/lenses/pwa_icons.py` (Pillow), `scripts/tools/pwa_head.py` (stamper).
**New (tests):** `scripts/tests/test_pwa.py`, `scripts/tests/test_pwa_icons.py`, `scripts/tests/test_pwa_head.py`, `scripts/tests/js/load.js`, `scripts/tests/js/personalize-core.test.js`, `scripts/tests/js/sw.test.js`.
**Modify:** `dashboards/lens.js` (★ + range hook), `dashboards/lens.css` (`.fav-star`), `scripts/lenses/briefpage.py` (+head_tags), `scripts/lenses/sitemap.py` (+favorites), `dashboards/index.html` (static Favorites link), `CLAUDE.md` (docs), plus existing brief/sitemap tests.

---

### Task 1: `personalize-core.js` — pure logic + `node:test` harness

**Files:**
- Create: `dashboards/personalize-core.js`
- Create: `scripts/tests/js/load.js`, `scripts/tests/js/personalize-core.test.js`

**Interfaces — Produces:** global `self.BACore` (browser) / `module.exports` (node) with:
`effectiveRange(userPref, pageDefault) -> "1Y"|"5Y"|"Max"`, `hasFavorite(list,id)->bool`, `addFavorite(list,{id,title,category})->list` (dedupe by id, newest-first), `removeFavorite(list,id)->list`, `parseFavorites(raw)->[{id,title,category}]` (tolerant), `serializeFavorites(list)->string`, `groupByCategory(list)->{cat:[fav]}`, `RANGE_RANK`.

- [ ] **Step 1: Write the harness** `scripts/tests/js/load.js`

```js
// Loads a browser <script> file in a CJS sandbox and returns its module.exports.
// Works regardless of any package.json "type" up the tree (no Node module
// resolution involved). Browser dual-export tail: `if (typeof module...) module.exports = ...`.
const fs = require("fs");
const path = require("path");
function loadScript(relFromRepoRoot) {
  const abs = path.join(__dirname, "..", "..", "..", relFromRepoRoot);
  const code = fs.readFileSync(abs, "utf8");
  const module = { exports: {} };
  new Function("module", "exports", code)(module, module.exports);
  return module.exports;
}
module.exports = { loadScript };
```

- [ ] **Step 2: Write the failing test** `scripts/tests/js/personalize-core.test.js`

```js
const test = require("node:test");
const assert = require("node:assert");
const { loadScript } = require("./load");
const core = loadScript("dashboards/personalize-core.js");

test("effectiveRange: no pref -> page default", () => {
  assert.equal(core.effectiveRange(null, "1Y"), "1Y");
  assert.equal(core.effectiveRange(undefined, "5Y"), "5Y");
});
test("effectiveRange: longer pref wins", () => {
  assert.equal(core.effectiveRange("Max", "1Y"), "Max");
  assert.equal(core.effectiveRange("5Y", "1Y"), "5Y");
});
test("effectiveRange: page default floors a shorter pref (banking stays 5Y)", () => {
  assert.equal(core.effectiveRange("1Y", "5Y"), "5Y");
});
test("effectiveRange: junk -> 1Y / pageDefault", () => {
  assert.equal(core.effectiveRange("bogus", "bogus"), "1Y");
  assert.equal(core.effectiveRange("bogus", "5Y"), "5Y");
});
test("favorites add/dedupe/remove/has", () => {
  let l = core.addFavorite([], { id: "a", title: "A", category: "economic" });
  l = core.addFavorite(l, { id: "b", title: "B", category: "markets" });
  l = core.addFavorite(l, { id: "a", title: "A2", category: "economic" });
  assert.equal(l.length, 2);
  assert.equal(l[0].id, "a");
  assert.equal(l[0].title, "A2");
  assert.ok(core.hasFavorite(l, "b"));
  l = core.removeFavorite(l, "a");
  assert.equal(core.hasFavorite(l, "a"), false);
});
test("parseFavorites tolerates junk", () => {
  assert.deepEqual(core.parseFavorites("not json"), []);
  assert.deepEqual(core.parseFavorites("{}"), []);
  assert.deepEqual(core.parseFavorites('[{"id":"x","title":"X","category":"c"},{"bad":1}]'),
    [{ id: "x", title: "X", category: "c" }]);
});
test("serialize round-trips", () => {
  const l = [{ id: "x", title: "X", category: "c" }];
  assert.deepEqual(core.parseFavorites(core.serializeFavorites(l)), l);
});
test("groupByCategory buckets in first-seen order", () => {
  const g = core.groupByCategory([{id:"a",category:"economic"},{id:"b",category:"markets"},{id:"c",category:"economic"}]);
  assert.deepEqual(Object.keys(g), ["economic", "markets"]);
  assert.equal(g.economic.length, 2);
});
```

- [ ] **Step 3: Run — verify FAIL**

Run: `node --test "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/js/"`
Expected: FAIL (`personalize-core.js` missing → `ENOENT`/throw).

- [ ] **Step 4: Implement** `dashboards/personalize-core.js`

```js
/* Pure, DOM-free personalization helpers. A global (self.BACore) in the browser,
   a CommonJS module under node:test. No localStorage/DOM here. */
(function (root) {
  "use strict";
  var RANGE_RANK = { "1Y": 1, "5Y": 2, "Max": 3 };

  function effectiveRange(userPref, pageDefault) {
    var pd = RANGE_RANK[pageDefault] ? pageDefault : "1Y";
    if (!RANGE_RANK[userPref]) return pd;
    return RANGE_RANK[userPref] >= RANGE_RANK[pd] ? userPref : pd;
  }
  function hasFavorite(list, id) {
    return Array.isArray(list) && list.some(function (f) { return f && f.id === id; });
  }
  function addFavorite(list, fav) {
    var out = (Array.isArray(list) ? list : []).filter(function (f) { return f && f.id !== fav.id; });
    out.unshift({ id: fav.id, title: fav.title, category: fav.category });
    return out;
  }
  function removeFavorite(list, id) {
    return (Array.isArray(list) ? list : []).filter(function (f) { return f && f.id !== id; });
  }
  function parseFavorites(raw) {
    try {
      var v = JSON.parse(raw);
      if (!Array.isArray(v)) return [];
      return v.filter(function (f) { return f && typeof f.id === "string"; })
              .map(function (f) { return { id: f.id, title: String(f.title || f.id), category: String(f.category || "") }; });
    } catch (e) { return []; }
  }
  function serializeFavorites(list) { return JSON.stringify(Array.isArray(list) ? list : []); }
  function groupByCategory(list) {
    var g = {};
    (Array.isArray(list) ? list : []).forEach(function (f) {
      if (!f || !f.category) return;
      (g[f.category] = g[f.category] || []).push(f);
    });
    return g;
  }
  var api = { effectiveRange: effectiveRange, hasFavorite: hasFavorite, addFavorite: addFavorite,
    removeFavorite: removeFavorite, parseFavorites: parseFavorites, serializeFavorites: serializeFavorites,
    groupByCategory: groupByCategory, RANGE_RANK: RANGE_RANK };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BACore = api;
})(typeof self !== "undefined" ? self : this);
```

- [ ] **Step 5: Run — verify PASS**

Run: `node --test "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/js/"`
Expected: PASS (all subtests).

- [ ] **Step 6: Commit**

```bash
git add dashboards/personalize-core.js scripts/tests/js/
git commit -m "feat(pwa): pure personalization core (favorites, range floor) + node:test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: PWA icons — `pwa_icons.py` + `unittest`, then generate

**Files:**
- Create: `scripts/lenses/pwa_icons.py`, `scripts/tests/test_pwa_icons.py`
- Generate (commit): `icons/icon-192.png`, `icons/icon-512.png`, `icons/icon-192-maskable.png`, `icons/icon-512-maskable.png`, `apple-touch-icon.png`

**Interfaces — Produces:** `pwa_icons.generate(root=None) -> list[str]` writes the icon set, returns relative paths.

- [ ] **Step 1: Confirm an existing Python test's import pattern** (so the new test mirrors it)

Run: `node -e "0" ; sed -n '1,12p' "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/test_ogcard.py"` (read how it puts `scripts/` on `sys.path` / imports `lenses`). Mirror that exact pattern in the new test header.

- [ ] **Step 2: Write the failing test** `scripts/tests/test_pwa_icons.py`

```python
import unittest
import tempfile
from pathlib import Path

# mirror test_ogcard.py's sys.path bootstrap (verified in Step 1)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lenses import pwa_icons  # noqa: E402
from PIL import Image  # noqa: E402


class TestPwaIcons(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        pwa_icons.generate(root=self.tmp)

    def test_sizes(self):
        self.assertEqual(Image.open(self.tmp / "icons/icon-192.png").size, (192, 192))
        self.assertEqual(Image.open(self.tmp / "icons/icon-512.png").size, (512, 512))
        self.assertEqual(Image.open(self.tmp / "icons/icon-512-maskable.png").size, (512, 512))
        self.assertEqual(Image.open(self.tmp / "apple-touch-icon.png").size, (180, 180))

    def test_apple_touch_is_opaque(self):
        # iOS rejects transparency on apple-touch-icon
        self.assertEqual(Image.open(self.tmp / "apple-touch-icon.png").mode, "RGB")

    def test_maskable_bleeds_to_corner(self):
        # maskable: panel bg fills the corner (safe-zone art is inset)
        px = Image.open(self.tmp / "icons/icon-512-maskable.png").convert("RGBA").getpixel((4, 4))
        self.assertEqual(px[:3], (15, 23, 42))      # #0F172A panel
        self.assertEqual(px[3], 255)

    def test_standard_corner_is_transparent(self):
        # non-maskable: rounded corner is transparent
        px = Image.open(self.tmp / "icons/icon-512.png").convert("RGBA").getpixel((1, 1))
        self.assertEqual(px[3], 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run — verify FAIL**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa_icons.py" -v`
Expected: FAIL (`ImportError: cannot import name 'pwa_icons'`).

- [ ] **Step 4: Implement** `scripts/lenses/pwa_icons.py`

```python
"""Generate PWA app icons from the favicon design (rounded #0F172A panel +
#38BDF8 chart line). Mirrors ogcard.py's Pillow usage. Static assets — run once,
commit; not part of the daily refresh."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = (15, 23, 42, 255)    # #0F172A
BLUE = (56, 189, 248, 255)   # #38BDF8
PTS64 = [(10, 44), (22, 34), (32, 38), (44, 20), (54, 26)]  # favicon polyline, 64-space


def _draw(size, maskable=False):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    inset = size * 0.10 if maskable else 0          # maskable safe zone (~80% art)
    s = (size - 2 * inset) / 64.0

    def P(p):
        return (inset + p[0] * s, inset + p[1] * s)

    if maskable:
        d.rectangle([0, 0, size, size], fill=PANEL)  # full-bleed for the mask
    else:
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=14 * (size / 64.0), fill=PANEL)
    w = max(2, int(round(5.5 * s)))
    line = [P(p) for p in PTS64]
    d.line(line, fill=BLUE, width=w, joint="curve")
    r = w / 2.0
    for x, y in line:                                # round caps/joins
        d.ellipse([x - r, y - r, x + r, y + r], fill=BLUE)
    return img


def generate(root=None):
    root = root or ROOT
    (root / "icons").mkdir(parents=True, exist_ok=True)
    out = []
    for rel, size, mask in [
        ("icons/icon-192.png", 192, False), ("icons/icon-512.png", 512, False),
        ("icons/icon-192-maskable.png", 192, True), ("icons/icon-512-maskable.png", 512, True),
    ]:
        _draw(size, maskable=mask).save(root / rel)
        out.append(rel)
    _draw(180, maskable=False).convert("RGB").save(root / "apple-touch-icon.png")  # opaque
    out.append("apple-touch-icon.png")
    return out


if __name__ == "__main__":
    print(generate())
```

- [ ] **Step 5: Run — verify PASS**, then generate the real icons

Run tests: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa_icons.py" -v` → PASS.
Generate: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/lenses/pwa_icons.py"` → prints the 5 paths.

- [ ] **Step 6: Commit**

```bash
git add scripts/lenses/pwa_icons.py scripts/tests/test_pwa_icons.py icons/ apple-touch-icon.png
git commit -m "feat(pwa): app icons generated from the favicon mark (Pillow)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `lenses/pwa.py` (head/manifest single source) + `manifest.webmanifest` + `offline.html`

**Files:**
- Create: `scripts/lenses/pwa.py`, `scripts/tests/test_pwa.py`, `manifest.webmanifest`, `offline.html`

**Interfaces — Produces:** `pwa.head_tags() -> str` (the exact head block, no leading indent on first line beyond what callers add), `pwa.manifest_dict() -> dict`, `pwa.manifest_json() -> str`, `pwa.THEME_COLOR`.

- [ ] **Step 1: Write the failing test** `scripts/tests/test_pwa.py`

```python
import json
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lenses import pwa  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


class TestPwa(unittest.TestCase):
    def test_head_tags_contents(self):
        h = pwa.head_tags()
        self.assertIn('rel="manifest" href="/manifest.webmanifest"', h)
        self.assertIn('name="theme-color"', h)
        self.assertIn('rel="apple-touch-icon" href="/apple-touch-icon.png"', h)
        self.assertIn('src="/dashboards/personalize-core.js"', h)
        self.assertIn('src="/dashboards/personalize.js"', h)
        # core must precede personalize (load order)
        self.assertLess(h.index("personalize-core.js"), h.index('personalize.js"'))

    def test_manifest_dict(self):
        m = pwa.manifest_dict()
        self.assertEqual(m["start_url"], "/dashboards/favorites.html")
        self.assertEqual(m["display"], "standalone")
        self.assertEqual(m["scope"], "/")
        purposes = {i["purpose"] for i in m["icons"]}
        self.assertEqual(purposes, {"any", "maskable"})

    def test_manifest_file_matches_source(self):
        disk = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertEqual(json.loads(disk), pwa.manifest_dict())

    def test_offline_page_exists(self):
        self.assertTrue((ROOT / "offline.html").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — verify FAIL** (`ImportError` / files missing).

- [ ] **Step 3: Implement** `scripts/lenses/pwa.py`

```python
"""Single source for the PWA head fragment + web manifest. Imported by the head
stamper (tools/pwa_head.py) and briefpage.py so baked + hand-written pages emit
byte-identical tags (no re-bake flip-flop)."""
import json

THEME_COLOR = "#0A0E14"


def head_tags():
    return (
        '  <link rel="manifest" href="/manifest.webmanifest">\n'
        f'  <meta name="theme-color" content="{THEME_COLOR}">\n'
        '  <link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
        '  <script defer src="/dashboards/personalize-core.js"></script>\n'
        '  <script defer src="/dashboards/personalize.js"></script>'
    )


def manifest_dict():
    return {
        "name": "Bailey Analytics",
        "short_name": "Bailey",
        "description": "Daily, plain-English dashboards on the U.S. and global economy.",
        "start_url": "/dashboards/favorites.html",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": THEME_COLOR,
        "theme_color": THEME_COLOR,
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icons/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def manifest_json():
    return json.dumps(manifest_dict(), indent=2) + "\n"
```

- [ ] **Step 4: Write the static files**

Generate the manifest from source (keeps them in lockstep):
`python -c "import sys; sys.path.insert(0,'C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts'); from lenses import pwa; open('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/manifest.webmanifest','w',encoding='utf-8').write(pwa.manifest_json())"`

Create `offline.html` (standalone inline CSS — does NOT load lens.css, mirrors about.html's pattern):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Offline — Bailey Analytics</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <style>
    body{min-height:100vh;min-height:100dvh;display:flex;flex-direction:column;align-items:center;
      justify-content:center;text-align:center;gap:1rem;margin:0;padding:2rem;
      background:#0A0E14;color:#F8FAFC;line-height:1.5;
      font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif}
    h1{font-size:1.5rem;font-weight:600;margin:0}
    p{color:#94A3B8;max-width:24rem;margin:0}
    a{color:#38BDF8;text-decoration:none}
  </style>
</head>
<body>
  <h1>You're offline</h1>
  <p>Bailey Analytics needs a connection to load new pages. Pages and data you've already viewed are still available — <a href="/dashboards/favorites.html">open your Favorites</a> or <a href="/">go home</a>.</p>
</body>
</html>
```

- [ ] **Step 5: Run — verify PASS**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa.py" -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/lenses/pwa.py scripts/tests/test_pwa.py manifest.webmanifest offline.html
git commit -m "feat(pwa): manifest + offline page + single-source head fragment

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `sw.js` — service worker + `routeStrategy` `node:test`

**Files:**
- Create: `sw.js`, `scripts/tests/js/sw.test.js`

**Interfaces — Produces:** `routeStrategy(reqUrl, {sameOrigin, mode}) -> "html"|"data"|"asset"|"network"`; constants `CACHE_VERSION`, `CACHE`, `PRECACHE`.

- [ ] **Step 1: Write the failing test** `scripts/tests/js/sw.test.js`

```js
const test = require("node:test");
const assert = require("node:assert");
const { loadScript } = require("./load");
const sw = loadScript("sw.js");

test("navigations -> html (network-first + offline fallback)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/x", { mode: "navigate", sameOrigin: true }), "html");
});
test("same-origin data json -> data (network-first)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/data/lenses/index.json", { sameOrigin: true }), "data");
});
test("static assets -> asset (stale-while-revalidate)", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/dashboards/lens.css", { sameOrigin: true }), "asset");
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/icons/icon-192.png", { sameOrigin: true }), "asset");
});
test("cross-origin (Chart.js CDN) -> asset", () => {
  assert.equal(sw.routeStrategy("https://cdn.jsdelivr.net/npm/chart.js@4/x.js", { sameOrigin: false }), "asset");
});
test("other same-origin -> network passthrough", () => {
  assert.equal(sw.routeStrategy("https://baileyanalytics.com/something", { sameOrigin: true }), "network");
});
test("constants present", () => {
  assert.ok(sw.CACHE.startsWith("ba-cache-"));
  assert.ok(Array.isArray(sw.PRECACHE) && sw.PRECACHE.includes("/offline.html"));
});
```

- [ ] **Step 2: Run — verify FAIL** (`sw.js` missing).

- [ ] **Step 3: Implement** `sw.js`

```js
/* Bailey Analytics service worker. A daily-data site must never serve frozen
   content while online: HTML + /data/*.json are network-first; static assets are
   stale-while-revalidate; cache is busted by CACHE_VERSION each deploy. The pure
   router (routeStrategy) is exported for node:test; SW wiring is guarded so the
   file loads cleanly under test (no self/caches). */
var CACHE_VERSION = "v1";                 // bump on deploy to purge old caches
var CACHE = "ba-cache-" + CACHE_VERSION;
var PRECACHE = ["/offline.html", "/manifest.webmanifest",
  "/dashboards/lens.css", "/dashboards/lens.js", "/dashboards/hub.js",
  "/dashboards/personalize-core.js", "/dashboards/personalize.js",
  "/icons/icon-192.png", "/icons/icon-512.png", "/favicon.svg"];

function routeStrategy(reqUrl, opts) {
  opts = opts || {};
  var u;
  try { u = new URL(reqUrl); } catch (e) { return "network"; }
  if (opts.mode === "navigate") return "html";
  if (opts.sameOrigin && u.pathname.indexOf("/data/") === 0 && u.pathname.indexOf(".json") === u.pathname.length - 5) return "data";
  if (/\.(css|js|png|svg|webmanifest|woff2?)$/.test(u.pathname)) return "asset";
  if (!opts.sameOrigin) return "asset";
  return "network";
}

if (typeof self !== "undefined" && self.addEventListener && typeof caches !== "undefined") {
  self.addEventListener("install", function (e) {
    e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); }));
  });
  self.addEventListener("activate", function (e) {
    e.waitUntil(caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); }));
  });
  self.addEventListener("fetch", function (e) {
    var req = e.request;
    if (req.method !== "GET") return;
    var sameOrigin = new URL(req.url).origin === self.location.origin;
    var strat = routeStrategy(req.url, { sameOrigin: sameOrigin, mode: req.mode });
    if (strat === "html") e.respondWith(networkFirst(req, "/offline.html"));
    else if (strat === "data") e.respondWith(networkFirst(req, null));
    else if (strat === "asset") e.respondWith(staleWhileRevalidate(req));
    // "network": no respondWith -> default browser fetch
  });
}

function networkFirst(req, fallbackUrl) {
  return fetch(req).then(function (res) {
    if (res && res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(req, copy); }); }
    return res;
  }).catch(function () {
    return caches.match(req).then(function (hit) {
      if (hit) return hit;
      if (fallbackUrl) return caches.match(fallbackUrl);
      return Response.error();
    });
  });
}
function staleWhileRevalidate(req) {
  return caches.open(CACHE).then(function (c) {
    return c.match(req).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res && (res.ok || res.type === "opaque")) c.put(req, res.clone());
        return res;
      }).catch(function () { return hit; });
      return hit || net;
    });
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { routeStrategy: routeStrategy, CACHE_VERSION: CACHE_VERSION, CACHE: CACHE, PRECACHE: PRECACHE };
}
```

- [ ] **Step 4: Run — verify PASS**

Run: `node --test "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/js/"` → all PASS (core + sw).

- [ ] **Step 5: Commit**

```bash
git add sw.js scripts/tests/js/sw.test.js
git commit -m "feat(pwa): service worker (network-first HTML/data, SWR assets) + tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `lens.js` — favorite ★ in badgerow + range-preference hook; `.fav-star` CSS

**Files:**
- Modify: `dashboards/lens.js` (the `render()` badgerow; `indicatorCard()` start range + range-button click)
- Modify: `dashboards/lens.css` (append `.fav-star`)

**Interfaces — Consumes:** optional `window.BAPrefs.effectiveRange(pageDefault)` / `window.BAPrefs.setRangeDefault(key)` (Task 6). **Produces:** a `.fav-star[data-fav-id][data-fav-title][data-fav-category]` button in the badgerow for `personalize.js` (Task 6) to bind on the existing `lens:rendered` event.

*No unit test:* `lens.js` is browser-DOM render code — the repo's existing renderers (`hub.js`, `predict.js`, `brief.js`) carry no JS unit tests; the testable logic (range floor) is already covered in Task 1. Verified manually in Task 9.

- [ ] **Step 1: Add the range hook in `indicatorCard()`**

In `dashboards/lens.js`, replace the `startKey` line:
```js
    const startKey = (defaultRange in RANGES) ? defaultRange : "1Y";
```
with:
```js
    const pageDefault = (defaultRange in RANGES) ? defaultRange : "1Y";
    const startKey = (window.BAPrefs && window.BAPrefs.effectiveRange)
      ? window.BAPrefs.effectiveRange(pageDefault) : pageDefault;
```

- [ ] **Step 2: Persist range on explicit click**

In the range-button `click` handler in `indicatorCard()`, after `chart = makeChart(canvas, indicator, recessions, RANGES[key]);`, add:
```js
        if (window.BAPrefs && window.BAPrefs.setRangeDefault) window.BAPrefs.setRangeDefault(key);
```

- [ ] **Step 3: Add the ★ to the badgerow in `render()`**

Compute the category and inject the button. Immediately before `const back = journeyBack(opts);` add:
```js
    const favCategory = (opts.href || "/dashboards/economic/").split("/").filter(Boolean).pop();
```
Then in the `root.innerHTML` template, change the `.badgerow` block from:
```js
      <div class="badgerow">
        <span class="badge ${lens.status}">${esc(lens.status)}</span>
        <span class="updated">Updated ${fmtUpdated(lens.last_updated)} · ${lens.indicators.length} signals</span>
      </div>
```
to:
```js
      <div class="badgerow">
        <span class="badge ${lens.status}">${esc(lens.status)}</span>
        <span class="updated">Updated ${fmtUpdated(lens.last_updated)} · ${lens.indicators.length} signals</span>
        <button class="fav-star js-only" type="button" aria-pressed="false"
          data-fav-id="${esc(lens.id)}" data-fav-title="${esc(lens.title)}" data-fav-category="${esc(favCategory)}"
          aria-label="Save to Favorites" title="Save to Favorites">&#9734;</button>
      </div>
```

- [ ] **Step 4: Append `.fav-star` to `dashboards/lens.css`**

```css
/* ---- Favorites star (lens-page badgerow; personalize.js binds behavior) ---- */
.fav-star{margin-left:auto;background:transparent;border:0;cursor:pointer;color:var(--dim);
  font-size:1.25rem;line-height:1;padding:.15rem .35rem;border-radius:6px;transition:color .15s,transform .15s}
.fav-star:hover{color:var(--amber)}
.fav-star[aria-pressed="true"]{color:var(--amber)}
.fav-star:focus-visible{outline:2px solid var(--blue);outline-offset:3px}
@media(prefers-reduced-motion:reduce){.fav-star{transition:none}}
```

- [ ] **Step 5: Smoke-check (no syntax error)**

Run: `node -e "require('fs').readFileSync('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/dashboards/lens.js','utf8'); new Function(require('fs').readFileSync('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/dashboards/lens.js','utf8')); console.log('parse-ok')"`
Expected: `parse-ok` (parses as a function body; references to `window`/`Chart` are fine since it isn't executed).

- [ ] **Step 6: Commit**

```bash
git add dashboards/lens.js dashboards/lens.css
git commit -m "feat(pwa): lens-page favorite star + remembered chart range hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `personalize.js` — store, ★ binding, range pref, SW register, nav inject, offline banner

**Files:**
- Create: `dashboards/personalize.js`

**Interfaces — Consumes:** `self.BACore` (Task 1), `.fav-star` + `lens:rendered` (Task 5), `/sw.js` (Task 4). **Produces:** `self.BAStore` (`favorites()`, `setFavorites(l)`, `toggle(fav)`, `getPref(n)`, `setPref(n,v)`), `self.BAPrefs` (`effectiveRange(pageDefault)`, `setRangeDefault(key)`); injects the Favorites nav link; fires `ba:changed` on mutation.

*No unit test:* DOM/browser glue (matches the repo's untested renderers). Pure logic it relies on is tested in Task 1. Verified manually in Task 9.

- [ ] **Step 1: Implement** `dashboards/personalize.js`

```js
/* Client glue for personalization + PWA. Pure logic lives in personalize-core.js
   (self.BACore). DOM/browser wiring only. Degrades silently without
   localStorage / serviceWorker. */
(function () {
  "use strict";
  var core = self.BACore || {};
  var FAV_KEY = "ba:favorites", PREF_KEY = "ba:prefs";

  var store = {
    _get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    _set: function (k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } },
    favorites: function () { return core.parseFavorites(this._get(FAV_KEY)); },
    setFavorites: function (l) { this._set(FAV_KEY, core.serializeFavorites(l)); this._emit(); },
    toggle: function (fav) {
      var l = this.favorites();
      l = core.hasFavorite(l, fav.id) ? core.removeFavorite(l, fav.id) : core.addFavorite(l, fav);
      this.setFavorites(l);
      return core.hasFavorite(l, fav.id);
    },
    getPref: function (name) { try { return (JSON.parse(this._get(PREF_KEY)) || {})[name] || null; } catch (e) { return null; } },
    setPref: function (name, val) {
      var p = {};
      try { p = JSON.parse(this._get(PREF_KEY)) || {}; } catch (e) {}
      p[name] = val; this._set(PREF_KEY, JSON.stringify(p));
    },
    _emit: function () { try { document.dispatchEvent(new CustomEvent("ba:changed")); } catch (e) {} }
  };
  self.BAStore = store;
  self.BAPrefs = {
    effectiveRange: function (pageDefault) { return core.effectiveRange(store.getPref("rangeDefault"), pageDefault); },
    setRangeDefault: function (key) { store.setPref("rangeDefault", key); }
  };

  // --- Service worker ---
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch(function () {});
    });
  }

  // --- Favorites nav entry (injected; avoids editing 78 navs) ---
  function injectNav() {
    var nav = document.querySelector("nav.top-nav");
    if (!nav || nav.querySelector("[data-fav-nav]")) return;
    var a = document.createElement("a");
    a.href = "/dashboards/favorites.html";
    a.textContent = "Favorites";
    a.setAttribute("data-fav-nav", "");
    if (location.pathname === "/dashboards/favorites.html") a.setAttribute("aria-current", "page");
    var after = null;
    nav.querySelectorAll("a").forEach(function (l) {
      if (/\/dashboards\/?$/.test(l.getAttribute("href") || "")) after = l;
    });
    if (after && after.nextSibling) nav.insertBefore(a, after.nextSibling);
    else if (after) nav.appendChild(a);
    else nav.appendChild(a);
  }

  // --- Lens-page star (bound on lens:rendered, per lens.js) ---
  function syncStar(btn) {
    var on = core.hasFavorite(store.favorites(), btn.getAttribute("data-fav-id"));
    btn.setAttribute("aria-pressed", String(on));
    btn.innerHTML = on ? "&#9733;" : "&#9734;";   // ★ / ☆
    var lbl = on ? "Saved to Favorites" : "Save to Favorites";
    btn.setAttribute("aria-label", lbl); btn.title = lbl;
  }
  document.addEventListener("lens:rendered", function () {
    var btn = document.querySelector(".fav-star[data-fav-id]");
    if (!btn || btn._bound) return;
    btn._bound = true;
    syncStar(btn);
    btn.addEventListener("click", function () {
      store.toggle({
        id: btn.getAttribute("data-fav-id"),
        title: btn.getAttribute("data-fav-title"),
        category: btn.getAttribute("data-fav-category")
      });
      syncStar(btn);
    });
  });

  // --- Offline indicator (styled inline so it works on pages without lens.css) ---
  function offlineBanner() {
    if (document.getElementById("ba-offline")) return;
    var b = document.createElement("div");
    b.id = "ba-offline";
    b.textContent = "Offline — showing last saved data";
    b.setAttribute("role", "status");
    b.style.cssText = "position:fixed;left:50%;bottom:1rem;transform:translateX(-50%);z-index:50;" +
      "background:#0F172A;color:#F8FAFC;border:1px solid #1E293B;border-radius:999px;" +
      "padding:.5rem 1rem;font:500 .8rem -apple-system,BlinkMacSystemFont,'Inter',sans-serif;" +
      "box-shadow:0 4px 16px rgba(0,0,0,.4);display:none";
    document.body.appendChild(b);
    function upd() { b.style.display = navigator.onLine ? "none" : "block"; }
    window.addEventListener("online", upd);
    window.addEventListener("offline", upd);
    upd();
  }

  function init() { injectNav(); offlineBanner(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
```

- [ ] **Step 2: Smoke-check parse**

Run: `node -e "new Function(require('fs').readFileSync('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/dashboards/personalize.js','utf8')); console.log('parse-ok')"`
Expected: `parse-ok`.

- [ ] **Step 3: Commit**

```bash
git add dashboards/personalize.js
git commit -m "feat(pwa): personalize.js glue (store, star, SW register, nav, offline)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `favorites.html` + `favorites.js` — the Favorites page

**Files:**
- Create: `dashboards/favorites.html`, `dashboards/favorites.js`

**Interfaces — Consumes:** `self.BACore`, `self.BAStore`, `self.BAPrefs`, `window.renderHubTiles`, `window.lensHref`, the category `index.json` files. Renders into `#fav-root`.

*No unit test:* DOM glue. The grouping/range logic it uses is tested in Task 1.

- [ ] **Step 1: Create** `dashboards/favorites.html` (mirror `dashboards/index.html` head/nav; load `hub.js` + `favorites.js`; `pwa_head.py` in Task 8 will stamp the PWA tags)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Favorites — Bailey Analytics</title>
  <meta name="description" content="Your saved Bailey Analytics lenses, in one place. Stored only in this browser.">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Favorites — Bailey Analytics">
  <meta property="og:description" content="Your saved Bailey Analytics lenses, in one place.">
  <meta property="og:url" content="https://baileyanalytics.com/dashboards/favorites.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta property="og:image" content="https://baileyanalytics.com/og/site.png">
  <link rel="canonical" href="https://baileyanalytics.com/dashboards/favorites.html">
  <meta name="robots" content="noindex">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  <noscript><style>.js-only{display:none}</style></noscript>
</head>
<body>
  <nav class="wordmark" aria-label="Bailey Analytics home"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav" aria-label="Primary"><a href="/dashboards/brief.html">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    <h1>Favorites</h1>
    <p class="lede">Your saved lenses, in one place. Tap the &#9734; on any lens to add it here.</p>
    <div id="fav-root"><div class="status-msg"><span class="js-only">Loading&hellip;</span><noscript>Favorites require JavaScript.</noscript></div></div>
  </main>
  <script defer src="/dashboards/hub.js"></script>
  <script defer src="/dashboards/favorites.js"></script>
</body>
</html>
```

> Note `<meta name="robots" content="noindex">` — a per-visitor page has no shared SEO value. (It still goes in the sitemap for the PWA's start_url, Task 9; that's fine.)

- [ ] **Step 2: Create** `dashboards/favorites.js`

```js
/* Renders the Favorites page: saved lenses as hub tiles (reusing hub.js), an
   empty state, a default-range preference, the local-only disclosure, and
   per-tile remove. All client-side; degrades to the empty state without data. */
(function () {
  "use strict";
  var core = self.BACore, store = self.BAStore;
  var INDEX = {
    economic: "/data/lenses/index.json", consumer: "/data/consumer/index.json",
    banking: "/data/banking/index.json", business: "/data/business/index.json",
    markets: "/data/markets/index.json", energy: "/data/energy/index.json",
    housing: "/data/housing/index.json", global: "/data/global/index.json"
  };

  function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function loadCategory(cat) {
    return fetch(INDEX[cat], { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw 0; return r.json();
    }).then(function (d) {
      var m = {}; (d.lenses || []).forEach(function (l) { m[l.id] = l; }); return m;
    }).catch(function () { return {}; });
  }

  function disclosure() {
    return '<p class="fav-note">Your favorites and preferences live only in this browser, on this device — ' +
      "there's no account. Clearing your browser's site data will reset them, and they won't sync to your " +
      'other devices. Account sync is on the roadmap.</p>';
  }

  function prefsBlock() {
    var cur = (store && store.getPref("rangeDefault")) || "";
    function opt(v, label) { return '<option value="' + v + '"' + (cur === v ? " selected" : "") + ">" + label + "</option>"; }
    return '<section class="fav-prefs"><h2 class="fav-h2">Preferences</h2>' +
      '<label class="fav-pref-row">Default chart range ' +
      '<select id="fav-range"><option value="">Auto (1Y, longer where needed)</option>' +
      opt("1Y", "1 year") + opt("5Y", "5 years") + opt("Max", "Max") + "</select></label>" +
      '<button type="button" id="fav-clear" class="fav-clear">Clear all favorites</button>' +
      "</section>";
  }

  function emptyState() {
    return '<div class="fav-empty"><p class="fav-empty-lead">You haven\'t saved any lenses yet.</p>' +
      '<p class="fav-empty-sub">Browse the dashboards and tap the &#9734; on any lens to pin it here for quick access.</p>' +
      '<a class="cta" href="/dashboards/">Browse dashboards &rarr;</a></div>' +
      prefsBlock() + disclosure();
  }

  function wirePrefs() {
    var sel = document.getElementById("fav-range");
    if (sel) sel.addEventListener("change", function () {
      if (sel.value) store.setPref("rangeDefault", sel.value);
      else store.setPref("rangeDefault", null);
    });
    var clr = document.getElementById("fav-clear");
    if (clr) clr.addEventListener("click", function () {
      if (confirm("Remove all saved favorites? This can't be undone.")) store.setFavorites([]);
    });
  }

  // Inject a small remove (✕) control into each rendered hub-card, correlated
  // to `lenses` by render order (renderHubTiles preserves order).
  function wireRemove(root, lenses) {
    root.querySelectorAll(".hub-card").forEach(function (card, i) {
      var lens = lenses[i]; if (!lens) return;
      var x = document.createElement("button");
      x.type = "button"; x.className = "fav-remove"; x.setAttribute("aria-label", "Remove from Favorites");
      x.title = "Remove from Favorites"; x.innerHTML = "&times;";
      x.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        store.setFavorites(core.removeFavorite(store.favorites(), lens.id));
      });
      card.style.position = "relative";
      card.appendChild(x);
    });
  }

  function render() {
    var root = document.getElementById("fav-root");
    var favs = store ? store.favorites() : [];
    if (!favs.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
    var groups = core.groupByCategory(favs);
    var cats = Object.keys(groups);
    Promise.all(cats.map(loadCategory)).then(function (maps) {
      var lenses = [];
      cats.forEach(function (cat, i) {
        groups[cat].forEach(function (f) {
          var l = maps[i][f.id];
          if (l) { l = Object.assign({}, l); l._cat = cat; lenses.push(l); }
        });
      });
      if (!lenses.length) { root.innerHTML = emptyState(); wirePrefs(); return; }
      root.innerHTML = '<div class="hub-grid" id="fav-grid"></div>';
      var grid = document.getElementById("fav-grid");
      window.renderHubTiles(grid, lenses, function (id) {
        var l = lenses.find(function (x) { return x.id === id; });
        return window.lensHref(l._cat, id);
      });
      wireRemove(grid, lenses);
      root.insertAdjacentHTML("beforeend", prefsBlock() + disclosure());
      wirePrefs();
    });
  }

  document.addEventListener("DOMContentLoaded", render);
  document.addEventListener("ba:changed", render);   // re-render after toggle/remove/clear
})();
```

- [ ] **Step 3: Append Favorites-page CSS to `dashboards/lens.css`**

```css
/* ---- Favorites page ---- */
.fav-note{color:var(--dim);font-size:.8rem;line-height:1.6;margin-top:1.75rem;
  padding-top:1rem;border-top:1px solid var(--border);max-width:40rem}
.fav-empty{text-align:center;padding:2.5rem 1rem;background:var(--panel);
  border:1px solid var(--border);border-radius:14px;margin-bottom:1.5rem}
.fav-empty-lead{font-size:1.1rem;font-weight:600;color:var(--text);margin-bottom:.4rem}
.fav-empty-sub{color:var(--muted);font-size:.9rem;max-width:28rem;margin:0 auto 1.25rem}
.fav-empty .cta{display:inline-block;text-decoration:none;color:var(--blue);border:1px solid var(--blue);
  border-radius:999px;font-size:.82rem;font-weight:500;padding:.6rem 1.3rem}
.fav-empty .cta:hover{background:var(--blue);color:var(--bg)}
.fav-prefs{margin-top:1.75rem}
.fav-h2{font-size:1rem;font-weight:600;margin-bottom:.75rem}
.fav-pref-row{display:flex;align-items:center;gap:.6rem;color:var(--muted);font-size:.88rem;margin-bottom:1rem}
.fav-pref-row select{background:var(--panel);border:1px solid var(--border);color:var(--text);
  border-radius:8px;padding:.4rem .6rem;font:inherit;font-size:.85rem}
.fav-clear{background:transparent;border:1px solid var(--border);color:var(--muted);
  border-radius:8px;padding:.45rem .9rem;font:inherit;font-size:.82rem;cursor:pointer}
.fav-clear:hover{border-color:var(--red);color:var(--red)}
.fav-remove{position:absolute;top:.6rem;right:.6rem;width:1.6rem;height:1.6rem;line-height:1;
  background:var(--bg);border:1px solid var(--border);border-radius:50%;color:var(--dim);
  font-size:1rem;cursor:pointer;display:flex;align-items:center;justify-content:center}
.fav-remove:hover{border-color:var(--red);color:var(--red)}
.fav-remove:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
```

- [ ] **Step 4: Smoke-check parse**

Run: `node -e "new Function(require('fs').readFileSync('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/dashboards/favorites.js','utf8')); console.log('parse-ok')"`
Expected: `parse-ok`.

- [ ] **Step 5: Commit**

```bash
git add dashboards/favorites.html dashboards/favorites.js dashboards/lens.css
git commit -m "feat(pwa): Favorites page (saved lenses, prefs, local-only disclosure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `tools/pwa_head.py` — idempotent head stamper + tests, then stamp pages

**Files:**
- Create: `scripts/tools/pwa_head.py`, `scripts/tests/test_pwa_head.py`
- Modify (generated by running it): all hand-written `*.html` under root + `dashboards/**` except the exclusions.

**Interfaces — Consumes:** `lenses.pwa.head_tags()`. **Produces:** `pwa_head.main(root=None) -> int`, `pwa_head.process(path) -> bool`, `pwa_head.is_target(path, root) -> bool`, marker `pwa_head.MARKER`.

- [ ] **Step 1: Write the failing test** `scripts/tests/test_pwa_head.py`

```python
import unittest
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import pwa_head  # noqa: E402

HEAD = "<head>\n  <title>x</title>\n</head>"


def page(body_head=HEAD):
    return "<!DOCTYPE html><html><head>\n  <title>x</title>\n</head><body></body></html>"


class TestPwaHead(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "dashboards").mkdir()
        (self.root / "docs").mkdir()
        (self.root / ".superpowers").mkdir()
        (self.root / "dashboards" / "brief").mkdir()
        self._w("index.html")
        self._w("dashboards/recession-watch.html")
        self._w("docs/note.html")
        self._w(".superpowers/mock.html")
        self._w("dashboards/brief.html")          # baked — briefpage owns it
        self._w("dashboards/brief/2026-06-24.html")  # baked archive

    def _w(self, rel):
        p = self.root / rel
        p.write_text(page(), encoding="utf-8")
        return p

    def test_targets_root_and_dashboards_only(self):
        self.assertTrue(pwa_head.is_target(self.root / "index.html", self.root))
        self.assertTrue(pwa_head.is_target(self.root / "dashboards/recession-watch.html", self.root))
        self.assertFalse(pwa_head.is_target(self.root / "docs/note.html", self.root))
        self.assertFalse(pwa_head.is_target(self.root / ".superpowers/mock.html", self.root))
        self.assertFalse(pwa_head.is_target(self.root / "dashboards/brief.html", self.root))
        self.assertFalse(pwa_head.is_target(self.root / "dashboards/brief/2026-06-24.html", self.root))

    def test_stamp_inserts_once_and_is_idempotent(self):
        self.assertEqual(pwa_head.main(root=self.root), 0)
        t1 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t1.count(pwa_head.MARKER), 1)
        self.assertIn('rel="manifest"', t1)
        self.assertTrue(t1.index(pwa_head.MARKER) < t1.index("</head>"))
        pwa_head.main(root=self.root)   # rerun
        t2 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t2, t1)        # no double-stamp

    def test_skips_excluded(self):
        pwa_head.main(root=self.root)
        self.assertNotIn(pwa_head.MARKER, (self.root / "docs/note.html").read_text(encoding="utf-8"))
        self.assertNotIn(pwa_head.MARKER, (self.root / "dashboards/brief.html").read_text(encoding="utf-8"))

    def test_no_head_warns_not_crashes(self):
        p = self.root / "dashboards/nohead.html"
        p.write_text("<html><body>x</body></html>", encoding="utf-8")
        pwa_head.main(root=self.root)
        self.assertNotIn(pwa_head.MARKER, p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run — verify FAIL** (`ImportError`).

- [ ] **Step 3: Implement** `scripts/tools/pwa_head.py`

```python
#!/usr/bin/env python3
"""Idempotent: stamp the PWA head fragment (manifest, theme-color, apple-touch,
personalize scripts) into every hand-written page's <head>. Marker-guarded,
rerunnable. Scope: root *.html + dashboards/**, excluding .git, docs/,
.superpowers/, and the baked dashboards/brief.html + dashboards/brief/ archive
(briefpage.py owns those). Mirrors seo_heads.py / cf_beacon.py; the .superpowers
exclusion is the lesson from the beacon work."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ on path
from lenses.pwa import head_tags  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
MARKER = "<!-- pwa:head -->"


def is_target(p, root):
    parts = p.parts
    if ".git" in parts or ".superpowers" in parts or "docs" in parts:
        return False
    if p.suffix != ".html":
        return False
    # baked brief surfaces (generator-owned)
    if p.parent.name == "brief" and p.parent.parent.name == "dashboards":
        return False
    if p.name == "brief.html" and p.parent.name == "dashboards":
        return False
    rel = p.relative_to(root)
    if len(rel.parts) == 1:
        return True                      # root-level page
    return rel.parts[0] == "dashboards"  # anything under dashboards/


def process(path):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if "</head>" not in text:
        print(f"SKIP (no </head>): {path}")
        return False
    block = f"  {MARKER}\n{head_tags()}\n"
    path.write_text(text.replace("</head>", block + "</head>", 1), encoding="utf-8")
    return True


def main(root=None):
    root = root or ROOT
    pages = [p for p in root.rglob("*.html") if is_target(p, root)]
    changed = [p for p in sorted(pages) if process(p)]
    print(f"Stamped {len(changed)} pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run — verify PASS**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa_head.py" -v` → PASS.

- [ ] **Step 5: Stamp the real pages**

Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tools/pwa_head.py"`
Expected: `Stamped N pages.` (≈48). Verify with: `git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" diff --stat` (only root + `dashboards/**` `.html`, no `docs/`/`.superpowers/`/`brief/`). Spot-check `git diff dashboards/recession-watch.html` shows the block before `</head>`, and that `dashboards/favorites.html` got stamped.

- [ ] **Step 6: Commit**

```bash
git add scripts/tools/pwa_head.py scripts/tests/test_pwa_head.py
git commit -m "feat(pwa): idempotent head stamper (manifest + personalize scripts)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git add -A "*.html"
git commit -m "chore(pwa): stamp PWA head tags into hand-written pages

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `briefpage.py` emits head tags (baked pages) + one-time archive catch-up + `sitemap.py` + static hub link + docs

**Files:**
- Modify: `scripts/lenses/briefpage.py` (insert `head_tags()` in the baked `<head>`)
- Modify: `scripts/lenses/sitemap.py` (add `/dashboards/favorites.html`)
- Modify: `dashboards/index.html` (static Favorites link in the lede, for no-JS/crawler discovery)
- Modify: `CLAUDE.md` (document the subsystem)
- Modify/extend: the brief + sitemap tests
- One-time: stamp existing baked `dashboards/brief.html`, `dashboards/brief/*.html`, `dashboards/brief/index.html`

**Interfaces — Consumes:** `lenses.pwa.head_tags()`.

- [ ] **Step 1: Read the two generators** to find exact insertion points

Read `scripts/lenses/briefpage.py` (locate where its `<head>` string is assembled / where `</head>` is emitted) and `scripts/lenses/sitemap.py` (the URL list). Read the existing `test_sitemap.py` and the brief page test (`test_refresh_publish.py` / `test_refresh_brief.py`) to mirror assertions.

- [ ] **Step 2: Add failing assertions**

In `test_sitemap.py`, add a case asserting the generated sitemap includes `/dashboards/favorites.html`.
In the brief-page test, add an assertion that the baked `brief.html` head contains `rel="manifest"` and `personalize.js`. Run both → FAIL.

- [ ] **Step 3: Implement the generator edits**

- `briefpage.py`: `from lenses.pwa import head_tags` (match existing import style) and insert `"  " + MARKER + "\n" + head_tags() + "\n"` immediately before `</head>` in the baked head — **use the same `<!-- pwa:head -->` marker string** as `pwa_head.py` (import it or duplicate the literal) so the stamper treats baked pages as already-done and re-bakes stay byte-identical. (If briefpage builds the head as a list/f-string, append the block as the last head line.)
- `sitemap.py`: add `"/dashboards/favorites.html"` to the URL set (mirroring how existing dashboard URLs are listed).
- `dashboards/index.html`: in the `<p class="lede">`, after the "Today's Brief" sentence, add: `Save the lenses you check most to <a href="/dashboards/favorites.html" style="color:var(--blue);text-decoration:none">Favorites</a>.`

- [ ] **Step 4: Run — verify PASS** (sitemap + brief tests).

- [ ] **Step 5: One-time baked-archive catch-up**

The stamper skips baked brief pages, and the archive re-render gate won't heal existing dated pages — so stamp them once, byte-identically to what `briefpage` now emits:
```bash
python - <<'PY'
import sys; sys.path.insert(0, "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts")
from pathlib import Path
from lenses.pwa import head_tags
ROOT = Path("C:/Users/jmich/Documents/Business/Repositories/baileyanalytics")
MARKER = "<!-- pwa:head -->"
targets = [ROOT/"dashboards"/"brief.html", *(ROOT/"dashboards"/"brief").glob("*.html")]
block = f"  {MARKER}\n{head_tags()}\n"
n = 0
for p in targets:
    t = p.read_text(encoding="utf-8")
    if MARKER in t or "</head>" not in t: continue
    p.write_text(t.replace("</head>", block + "</head>", 1), encoding="utf-8"); n += 1
print(f"catch-up stamped {n} baked pages")
PY
```
Verify the block in a baked page matches the generator's output exactly (rebuild one brief via `--brief --dry-run` is NOT needed; a textual diff of the inserted block vs `head_tags()` suffices — they share the source).

- [ ] **Step 6: Update `CLAUDE.md`**

Add a short subsection under the baileyanalytics architecture notes describing: the personalization/PWA subsystem (`personalize-core.js` pure + `node:test`, `personalize.js` glue, `favorites.html`/`.js` reusing `renderHubTiles`+`lensHref`), the PWA pieces (`manifest.webmanifest`, `sw.js` network-first/SWR + `CACHE_VERSION` bump-on-deploy, `icons/` via `pwa_icons.py`), the single-source `lenses/pwa.py head_tags()` stamped by `tools/pwa_head.py` + emitted by `briefpage.py`, the JS test command (`node --test scripts/tests/js/`), and the v1.1 light-theme follow-up. Note light theme is deferred.

- [ ] **Step 7: Commit**

```bash
git add scripts/lenses/briefpage.py scripts/lenses/sitemap.py scripts/tests/ dashboards/index.html dashboards/brief.html dashboards/brief/ sitemap.xml CLAUDE.md
git commit -m "feat(pwa): bake head tags into brief pages, sitemap + hub link, docs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Full verification

**Files:** none (verification only).

- [ ] **Step 1: Full Python suite** (redirect to a file — never pipe; pipes mask Python's exit code)

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" 2> "C:/Users/jmich/AppData/Local/Temp/claude/C--Users-jmich-Documents-Business-Repositories/8dda2e24-5765-4a57-936a-6e6bc9aa4003/scratchpad/pytest.txt"; echo "exit=$?"`
Then read the scratchpad file. Expected: `OK`, exit=0, count ≈ 779 + the new tests.

- [ ] **Step 2: Full JS suite**

Run: `node --test "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests/js/"`
Expected: all pass.

- [ ] **Step 3: Manual PWA/personalization smoke (serve locally)**

Start: `python -m http.server 8000` (from `baileyanalytics/`). In a browser:
1. Open a lens page → the ★ shows in the badgerow; click it → fills (★), `aria-pressed=true`. Open `/dashboards/favorites.html` → the lens appears as a tile; the nav shows "Favorites". Remove via ✕ → tile goes; empty state + disclosure show.
2. Change a chart to 5Y on an economic page, reload → it opens at 5Y. Open a banking page → still ≥5Y. Set Favorites → Preferences → range "Auto", reload economic page → back to 1Y.
3. DevTools → Application: manifest parses (icons, start_url `/dashboards/favorites.html`); service worker registers; run Lighthouse → installable. Toggle offline → reload a visited page shows last data + the offline banner; an unvisited route shows `offline.html`.

Record the results for the batched review (this is evidence, not a gate the user runs).

- [ ] **Step 4: No commit** (verification only). If any step fails, fix under systematic-debugging and re-run.

---

## Self-Review

**Spec coverage:** Favorites ★ (T5/T6) ✓; Favorites page + empty state + remove (T7) ✓; default range floor (T1/T5/T6) ✓; local-only disclosure (T7) ✓; manifest+icons+SW+offline+indicator (T2/T3/T4/T6) ✓; cross-page head via single source + stamper + generator (T3/T8/T9) ✓; nav entry JS-injected + static hub link + sitemap (T6/T9) ✓; start_url=favorites (T3, D3) ✓; SW stale-mitigation (T4) ✓; tests Python+JS (all) + manual (T10) ✓; docs (T9) ✓. No gaps.

**Placeholder scan:** every code step contains complete code; Task 9 Steps 1/3 reference reading existing files for exact insertion points (legitimate — those files weren't quoted in the spec) but give the exact import, marker, string, and assertions to add. No "TBD/handle edge cases/similar to".

**Type/name consistency:** `BACore`/`BAStore`/`BAPrefs` consistent across T1/T5/T6/T7; `effectiveRange(userPref,pageDefault)` same everywhere; `head_tags()`/`MARKER`/`is_target`/`process`/`main` consistent T3/T8/T9; `routeStrategy` signature consistent T4; favorite record shape `{id,title,category}` consistent T1/T5/T6/T7; `data-fav-id/title/category` consistent T5/T6.

# Light/Dark Theme (v1.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a polished, Apple-clean **light theme** with a clean nav toggle that honors the OS on first visit and remembers the visitor's explicit choice — across all 7 surfaces that hardcode the dark palette.

**Architecture:** A new inline, render-blocking `<head>` script (single-sourced in `lenses/pwa.py`, stamped by a new idempotent `tools/theme_head.py`, emitted by `briefpage.py`) sets `<html data-theme>` before first paint. CSS flips via `[data-theme="light"]` token overrides in `lens.css` + the two standalone inline-CSS pages; chart chrome reads CSS vars so charts recolor live on a `ba:theme` event dispatched by `personalize.js`'s injected sun/moon toggle. All client-side, zero-build, `localStorage` only.

**Tech Stack:** Hand-written HTML/CSS/JS, Chart.js 4.4.1 (CDN, pinned), Python 3 stdlib (`unittest`), Node 24 `node:test` (zero-dep). Reuses the PWA `personalize-core.js`/`personalize.js` + idempotent head-stamping machinery.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-06-24-light-theme-design.md` — the source of truth for every palette value (§5), surface inventory (§3), and decision (§4). Copy values from there verbatim.
- **Behavior:** honor `prefers-color-scheme` on first visit (live `matchMedia`); 2-state sun/moon toggle **pins** to `ba:prefs.theme` (`"light"`/`"dark"`); pinned overrides OS. **No "System" state.**
- **No-FOUC:** the pre-paint setter is **inline + synchronous** (never `defer`); it sets **only** `document.documentElement` `data-theme`. New marker **`<!-- theme:head -->`** (the `pwa:head` marker is already stamped site-wide and won't re-fire).
- **Theme switch is instant** — no global color transition (D7). Charts `update("none")`.
- **WCAG AA** for every light token (≥4.5 text, ≥3 UI) — enforced by `test_theme_contrast.py`.
- **Three-CSS-places trap:** any shared chrome (the `.theme-toggle` styles) lands in `lens.css` **and** `index.html` inline **and** `about.html` inline.
- **Zero-build static**; `localStorage` only; no backend.
- **Shell (from CLAUDE.md):** never `cd <repo> &&`; use `git -C` + absolute paths; Python via absolute path. **Never pipe a test run** (pipe masks Python's exit code) — redirect to a file, then read it. Work on branch `light-theme`; **do not merge/deploy.**
- **Test commands:**
  - One Python file: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_NAME.py"`
  - Full suite (redirect, don't pipe): `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" > "<scratch>/suite.txt" 2>&1` then read the tail.
  - JS: `node --test baileyanalytics/scripts/tests/js/*.test.js`

## File Structure

**Create:**
- `scripts/tools/theme_head.py` — idempotent stamper for the `<!-- theme:head -->` fragment.
- `scripts/tests/test_theme_head.py` — stamper idempotency/scope tests.
- `scripts/tests/test_theme_contrast.py` — WCAG AA gate over the light palette.

**Modify:**
- `scripts/lenses/pwa.py` — add `theme_head()` + `THEME_COLOR_LIGHT`.
- `scripts/lenses/briefpage.py` — emit `_THEME_HEAD` adjacent to `_PWA_HEAD`.
- `scripts/tests/test_pwa.py` — assert `theme_head()` shape.
- `dashboards/personalize-core.js` — add pure `resolveTheme`.
- `scripts/tests/js/personalize-core.test.js` — `resolveTheme` cases.
- `dashboards/personalize.js` — inject toggle; persist; `theme-color` meta; `ba:theme`; OS listener; theme the offline banner; `BAPrefs.getTheme/setTheme`.
- `dashboards/lens.js` — `chartChrome()` from CSS vars; recession plugin reads a var; recolor charts on `ba:theme`.
- `dashboards/lens.css` — new tokens; replace stray hexes; `[data-theme="light"]` block; `.theme-toggle` styles.
- `index.html` — home `[data-theme="light"]` block + `.theme-toggle` styles.
- `about.html` — convert inline hex → vars + `[data-theme="light"]` + `.theme-toggle`.
- `offline.html`, `404.html` — convert inline hex → vars + `[data-theme="light"]`.

**One-time (Task 12):** run `tools/theme_head.py`; catch-up the baked brief surfaces.

---

### Task 1: Pure `resolveTheme` (foundation)

**Files:**
- Modify: `dashboards/personalize-core.js`
- Test: `scripts/tests/js/personalize-core.test.js`

**Interfaces:**
- Produces: `resolveTheme(pref, prefersDark) → "light"|"dark"` on `self.BACore` / CommonJS export.

- [ ] **Step 1: Write the failing tests** — append to `scripts/tests/js/personalize-core.test.js`:

```js
test("resolveTheme: explicit pref overrides the OS", () => {
  assert.equal(core.resolveTheme("light", true), "light");
  assert.equal(core.resolveTheme("dark", false), "dark");
});
test("resolveTheme: no/unknown pref follows the OS", () => {
  assert.equal(core.resolveTheme(null, true), "dark");
  assert.equal(core.resolveTheme(null, false), "light");
  assert.equal(core.resolveTheme(undefined, true), "dark");
  assert.equal(core.resolveTheme("bogus", false), "light");
});
```

- [ ] **Step 2: Run, verify it fails**
Run: `node --test baileyanalytics/scripts/tests/js/personalize-core.test.js`
Expected: FAIL (`core.resolveTheme is not a function`).

- [ ] **Step 3: Implement** — in `personalize-core.js`, add the function and register it in the `api` object:

```js
function resolveTheme(pref, prefersDark) {
  if (pref === "light" || pref === "dark") return pref;
  return prefersDark ? "dark" : "light";
}
```
Add `resolveTheme: resolveTheme,` to the `var api = { … }` literal.

- [ ] **Step 4: Run, verify it passes**
Run: `node --test baileyanalytics/scripts/tests/js/personalize-core.test.js`
Expected: PASS (all tests, including the pre-existing `effectiveRange`/favorites ones).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/personalize-core.js scripts/tests/js/personalize-core.test.js
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): pure resolveTheme(pref, prefersDark)"
```

---

### Task 2: `pwa.theme_head()` (the pre-paint fragment)

**Files:**
- Modify: `scripts/lenses/pwa.py`
- Test: `scripts/tests/test_pwa.py`

**Interfaces:**
- Produces: `pwa.theme_head() → str` (an inline `<script>` line, **no** marker); `pwa.THEME_COLOR_LIGHT = "#F5F5F7"`.

- [ ] **Step 1: Write the failing test** — append a method to `TestPwa` in `scripts/tests/test_pwa.py`:

```python
    def test_theme_head_is_inline_prepaint(self):
        h = pwa.theme_head()
        self.assertIn("<script>", h)            # inline, not deferred/external
        self.assertNotIn("defer", h)
        self.assertIn("data-theme", h)          # sets the attribute
        self.assertIn('"ba:prefs"', h)          # reads the saved pref
        self.assertIn("prefers-color-scheme", h)  # else follows the OS
        self.assertNotIn("<!--", h)             # marker is added by the caller
```

- [ ] **Step 2: Run, verify it fails**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa.py"`
Expected: FAIL (`AttributeError: module 'lenses.pwa' has no attribute 'theme_head'`).

- [ ] **Step 3: Implement** — in `pwa.py`, add below `THEME_COLOR`:

```python
THEME_COLOR_LIGHT = "#F5F5F7"


def theme_head():
    """Inline, render-blocking pre-paint setter: applies the saved theme (or the
    OS preference) to <html data-theme> BEFORE first paint, so there is no flash
    of the wrong theme. Logic mirrors personalize-core.resolveTheme (cannot import
    in an inline pre-paint context). Callers add the `<!-- theme:head -->` marker."""
    return (
        '  <script>(function(){try{var p=(JSON.parse(localStorage.getItem("ba:prefs"))||{}).theme;'
        'var d=p==="light"||p==="dark"?p:(window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");'
        'document.documentElement.setAttribute("data-theme",d);}catch(e){}})();</script>'
    )
```

- [ ] **Step 4: Run, verify it passes**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa.py"`
Expected: OK.

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/pwa.py scripts/tests/test_pwa.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): single-source pre-paint theme head fragment"
```

---

### Task 3: `tools/theme_head.py` (idempotent stamper)

**Files:**
- Create: `scripts/tools/theme_head.py`
- Test: `scripts/tests/test_theme_head.py`

**Interfaces:**
- Produces: `theme_head.main(root=None) → int`; `theme_head.is_target(p, root) → bool`; `theme_head.MARKER = "<!-- theme:head -->"`. Scope identical to `pwa_head.py`.

- [ ] **Step 1: Write the failing test** — create `scripts/tests/test_theme_head.py` (mirrors `test_pwa_head.py`):

```python
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import theme_head

PAGE = "<!DOCTYPE html><html><head>\n  <title>x</title>\n</head><body></body></html>"


class TestThemeHead(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "dashboards").mkdir()
        (self.root / "docs").mkdir()
        (self.root / ".superpowers").mkdir()
        (self.root / "dashboards" / "brief").mkdir()
        for rel in ["index.html", "dashboards/recession-watch.html", "docs/note.html",
                    ".superpowers/mock.html", "dashboards/brief.html",
                    "dashboards/brief/2026-06-24.html"]:
            (self.root / rel).write_text(PAGE, encoding="utf-8")

    def test_targets_root_and_dashboards_only(self):
        T = lambda r: theme_head.is_target(self.root / r, self.root)
        self.assertTrue(T("index.html"))
        self.assertTrue(T("dashboards/recession-watch.html"))
        self.assertFalse(T("docs/note.html"))
        self.assertFalse(T(".superpowers/mock.html"))
        self.assertFalse(T("dashboards/brief.html"))
        self.assertFalse(T("dashboards/brief/2026-06-24.html"))

    def test_stamp_inserts_once_and_is_idempotent(self):
        self.assertEqual(theme_head.main(root=self.root), 0)
        t1 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t1.count(theme_head.MARKER), 1)
        self.assertIn("data-theme", t1)
        self.assertLess(t1.index(theme_head.MARKER), t1.index("</head>"))
        theme_head.main(root=self.root)
        self.assertEqual((self.root / "index.html").read_text(encoding="utf-8"), t1)

    def test_skips_excluded(self):
        theme_head.main(root=self.root)
        for rel in ["docs/note.html", "dashboards/brief.html", ".superpowers/mock.html"]:
            self.assertNotIn(theme_head.MARKER, (self.root / rel).read_text(encoding="utf-8"))

    def test_no_head_warns_not_crashes(self):
        p = self.root / "dashboards" / "nohead.html"
        p.write_text("<html><body>x</body></html>", encoding="utf-8")
        theme_head.main(root=self.root)
        self.assertNotIn(theme_head.MARKER, p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run, verify it fails**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_theme_head.py"`
Expected: FAIL (`ImportError: cannot import name 'theme_head'`).

- [ ] **Step 3: Implement** — create `scripts/tools/theme_head.py` (mirrors `pwa_head.py`; only the import, marker, and fragment differ):

```python
#!/usr/bin/env python3
"""Idempotent: stamp the inline pre-paint theme setter into every hand-written
page's <head> under its own <!-- theme:head --> marker. Marker-guarded,
rerunnable. Scope mirrors pwa_head.py exactly (root *.html + dashboards/**,
excluding .git, docs/, .superpowers/, and the baked dashboards/brief.html +
dashboards/brief/ archive — briefpage.py owns those). A separate marker is
required because the pwa:head marker is already stamped site-wide."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # scripts/ on path
from lenses.pwa import theme_head  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
MARKER = "<!-- theme:head -->"


def is_target(p, root):
    parts = p.parts
    if ".git" in parts or ".superpowers" in parts or "docs" in parts:
        return False
    if p.suffix != ".html":
        return False
    if p.parent.name == "brief" and p.parent.parent.name == "dashboards":
        return False
    if p.name == "brief.html" and p.parent.name == "dashboards":
        return False
    rel = p.relative_to(root)
    if len(rel.parts) == 1:
        return True
    return rel.parts[0] == "dashboards"


def process(path):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    if "</head>" not in text:
        print(f"SKIP (no </head>): {path}")
        return False
    block = f"  {MARKER}\n{theme_head()}\n"
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

- [ ] **Step 4: Run, verify it passes**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_theme_head.py"`
Expected: OK (4 tests).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tools/theme_head.py scripts/tests/test_theme_head.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): idempotent theme:head stamper"
```

---

### Task 4: `briefpage.py` emits the theme fragment

**Files:**
- Modify: `scripts/lenses/briefpage.py` (`_PWA_HEAD` is defined at line 15; the head templates use `{_PWA_HEAD}` at ~line 258 and ~line 328)
- Test: `scripts/tests/test_pwa.py`

**Interfaces:**
- Consumes: `pwa.theme_head()` (Task 2).
- Produces: baked brief/archive `<head>` contains `<!-- theme:head -->` immediately before `<!-- pwa:head -->` (position parity with the one-time catch-up in Task 12).

- [ ] **Step 1: Write the failing test** — append to `TestPwa` in `test_pwa.py`:

```python
    def test_briefpage_emits_theme_head_before_pwa_head(self):
        import datetime
        from lenses import briefpage
        today = {
            "date": "2026-06-24", "generated_at": "2026-06-24T11:00:00Z",
            "verdict": {"status": "watch", "sentence": "x"}, "categories": [],
            "pressure": [], "transitions": [], "moves": [], "watching": [],
            "relationships": [],
        }
        html = briefpage.render_brief(today, "/og/site.png")
        self.assertIn("<!-- theme:head -->", html)
        self.assertIn(pwa.theme_head().strip(), html)
        self.assertLess(html.index("<!-- theme:head -->"), html.index("<!-- pwa:head -->"))
```
> If `render_brief`'s signature/required keys differ, copy the shape from the existing brief test fixture in `scripts/tests/` (search `render_brief(`) — the assertion logic is what matters.

- [ ] **Step 2: Run, verify it fails**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa.py"`
Expected: FAIL (no `theme:head` in output).

- [ ] **Step 3: Implement** — in `briefpage.py`, below `_PWA_HEAD = …` (line 15) add:
```python
_THEME_HEAD = "<!-- theme:head -->\n" + pwa.theme_head()
```
Then in **both** head templates replace the `{_PWA_HEAD}` line with:
```
  {_THEME_HEAD}
  {_PWA_HEAD}
```
(keep the existing indentation of the `{_PWA_HEAD}` line for the `{_PWA_HEAD}` part).

- [ ] **Step 4: Run, verify it passes**
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_pwa.py"`
Expected: OK. Also run `-p "test_brief*.py"` to confirm existing brief tests still pass (the fragment is additive).

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/lenses/briefpage.py scripts/tests/test_pwa.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): bake theme:head into brief/archive pages"
```

---

### Task 5: `test_theme_contrast.py` (WCAG AA gate)

**Files:**
- Create: `scripts/tests/test_theme_contrast.py`

- [ ] **Step 1: Write the test** (it encodes spec §5.1/5.2 and asserts AA — green on first run with the audited values):

```python
"""WCAG AA gate for the light palette. Keep these values in sync with the
[data-theme="light"] block in dashboards/lens.css (spec 2026-06-24-light-theme §5)."""
import unittest


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hexstr):
    h = hexstr.lstrip("#")
    return (0.2126 * _lin(int(h[0:2], 16)) + 0.7152 * _lin(int(h[2:4], 16))
            + 0.0722 * _lin(int(h[4:6], 16)))


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


BG, PANEL = "#F5F5F7", "#FFFFFF"
# (label, fg, bg, min_ratio)
PAIRS = [
    ("text/bg", "#1D1D1F", BG, 4.5), ("text/panel", "#1D1D1F", PANEL, 4.5),
    ("muted/bg", "#4B4B4F", BG, 4.5), ("dim/bg", "#5E5E63", BG, 4.5),
    ("faint/bg", "#6A6A6F", BG, 4.5),
    ("blue/panel", "#0068D1", PANEL, 4.5), ("white-on-blue", "#FFFFFF", "#0068D1", 4.5),
    ("green/panel", "#1A7F37", PANEL, 4.5), ("amber/panel", "#8A5D00", PANEL, 4.5),
    ("orange/panel", "#C2410C", PANEL, 4.5), ("red/panel", "#D70015", PANEL, 4.5),
    ("badge ok", "#1A7F37", "#ECF8F2", 4.5), ("badge watch", "#8A5D00", "#FBF2DC", 4.5),
    ("badge elevated", "#C2410C", "#FDF0E6", 4.5), ("badge alert", "#D70015", "#FDECEE", 4.5),
    ("badge unknown", "#5E5E63", "#ECECF1", 4.5), ("badge neutral", "#0068D1", "#E6F0FC", 4.5),
    ("focus blue/bg", "#0068D1", BG, 3.0),
]


class TestThemeContrast(unittest.TestCase):
    def test_all_light_pairs_meet_aa(self):
        for label, fg, bg, mn in PAIRS:
            r = contrast(fg, bg)
            self.assertGreaterEqual(round(r, 2), mn, f"{label}: {r:.2f} < {mn}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** — `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_theme_contrast.py"`
Expected: OK. **If any pair fails:** lighten that tint by ~+3–4 per channel (or deepen the text) until ≥4.5, and update the matching value in §5 of the spec + Task 6's `lens.css` block so all three agree.

- [ ] **Step 3: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add scripts/tests/test_theme_contrast.py
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "test(theme): WCAG AA gate for the light palette"
```

---

### Task 6: `lens.css` — tokens, light block, toggle styles

**Files:**
- Modify: `dashboards/lens.css`

No unit test (CSS); verified by Task 5 (values) + Task 12 (manual axe/visual). Make these edits:

- [ ] **Step 1: Add new tokens to `:root`** (line 1–4 block), appending inside `:root{ … }`:
```css
--orange:#FB923C;--hover-wash:rgba(255,255,255,.03);
--chart-grid:#1E293B;--chart-tick:#64748B;--chart-axis:#1E293B;
--chart-tooltip-bg:#0A0E14;--chart-tooltip-border:#1E293B;--chart-tooltip-title:#F8FAFC;--chart-tooltip-body:#CBD5E1;
--chart-recession:rgba(248,113,113,0.09);
```

- [ ] **Step 2: Replace stray hardcoded hexes with the tokens** (preserves the dark look exactly):
  - `.badge.elevated{background:#3a2a17;color:#FB923C}` → `color:var(--orange)` (leave the dark bg; it's overridden in the light block).
  - `.s.elevated{color:#FB923C}`, `.lens-table td.elevated{color:#FB923C}`, `.tpill.elevated{color:#FB923C}` → `color:var(--orange)`.
  - `.chip-dot.elevated{background:#FB923C}` → `background:var(--orange)`.
  - `.brief-trans:hover{background:rgba(255,255,255,.03)}`, `.att-row:hover{background:rgba(255,255,255,.03)}`, and `.lens-chip{…background:rgba(255,255,255,.03)…}` → `var(--hover-wash)`.
  - `.pred-mark.hit{color:#34D399}` → `color:var(--green)`; `.pred-mark.miss{color:#F87171}` → `color:var(--red)`.

- [ ] **Step 3: Make `makeChart`'s tooltip/scale colors token-driven** — *(no change here; handled in Task 7. This task only defines the vars.)*

- [ ] **Step 4: Append the light-theme block + toggle styles** at the end of `lens.css`:
```css
/* ===== Light theme (spec 2026-06-24-light-theme §5) ===== */
[data-theme="light"]{
  --bg:#F5F5F7;--panel:#FFFFFF;--border:#D2D2D7;--text:#1D1D1F;
  --muted:#4B4B4F;--dim:#5E5E63;--faint:#6A6A6F;
  --blue:#0068D1;--green:#1A7F37;--amber:#8A5D00;--red:#D70015;--orange:#C2410C;
  --hover-wash:rgba(0,0,0,.04);
  --chart-grid:#E5E5EA;--chart-tick:#6A6A6F;--chart-axis:#D2D2D7;
  --chart-tooltip-bg:#FFFFFF;--chart-tooltip-border:#D2D2D7;--chart-tooltip-title:#1D1D1F;--chart-tooltip-body:#4B4B4F;
  --chart-recession:rgba(215,0,21,0.07);
}
/* badge pills: pale tint + deepened accent text (text from the flipped token) */
[data-theme="light"] .badge.ok{background:#ECF8F2}
[data-theme="light"] .badge.watch{background:#FBF2DC}
[data-theme="light"] .badge.elevated{background:#FDF0E6}
[data-theme="light"] .badge.alert{background:#FDECEE}
[data-theme="light"] .badge.unknown{background:#ECECF1}
[data-theme="light"] .badge.neutral{background:#E6F0FC}
/* table cells + relationship wash (were dark-only hexes) */
[data-theme="light"] .lens-table td{color:var(--text);border-bottom-color:var(--border)}
[data-theme="light"] .brief-rel{background:rgba(0,104,209,.06)}
/* soft Apple-style card lift */
[data-theme="light"] .signal,[data-theme="light"] .ind,[data-theme="light"] .hub-card,
[data-theme="light"] .cat-card,[data-theme="light"] .state-panel,[data-theme="light"] .state-steady,
[data-theme="light"] .track-stat,[data-theme="light"] .predict{box-shadow:0 1px 3px rgba(0,0,0,.06)}

/* ===== Theme toggle (injected into nav.top-nav by personalize.js) ===== */
.theme-toggle{display:inline-flex;align-items:center;justify-content:center;background:transparent;
  border:0;color:var(--muted);cursor:pointer;padding:.5rem;border-radius:6px;line-height:0;transition:color .2s}
.theme-toggle:hover,.theme-toggle:focus-visible{color:var(--text)}
.theme-toggle:focus-visible{outline:2px solid var(--blue);outline-offset:3px}
.theme-toggle svg{width:1.15rem;height:1.15rem;display:block}
@media(prefers-reduced-motion:reduce){.theme-toggle{transition:none}}
```

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/lens.css
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): light tokens, badge tints, chart vars, toggle styles in lens.css"
```

---

### Task 7: `lens.js` — theme-aware charts

**Files:**
- Modify: `dashboards/lens.js` (`recessionPlugin` ~line 46–65; `makeChart` ~line 67–113)

**Interfaces:**
- Consumes: the `--chart-*` CSS vars (Task 6).
- Reacts to: the `ba:theme` CustomEvent (Task 8).

- [ ] **Step 1: Add a chrome reader** — inside the IIFE, above `recessionPlugin`:
```js
  function cssVar(n){ return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function chartChrome(){
    return {
      grid: cssVar("--chart-grid") || "#1E293B", tick: cssVar("--chart-tick") || "#64748B",
      axis: cssVar("--chart-axis") || "#1E293B", ttBg: cssVar("--chart-tooltip-bg") || "#0A0E14",
      ttBorder: cssVar("--chart-tooltip-border") || "#1E293B",
      ttTitle: cssVar("--chart-tooltip-title") || "#F8FAFC", ttBody: cssVar("--chart-tooltip-body") || "#CBD5E1",
    };
  }
```

- [ ] **Step 2: Recession plugin reads the var** — in `recessionPlugin.beforeDraw`, replace
`ctx.fillStyle = "rgba(248,113,113,0.09)";` with
`ctx.fillStyle = cssVar("--chart-recession") || "rgba(248,113,113,0.09)";`

- [ ] **Step 3: `makeChart` uses `chartChrome()`** — at the top of `makeChart` add `const c = chartChrome();`, then replace the hardcoded colors:
  - tooltip: `backgroundColor: c.ttBg, borderColor: c.ttBorder, … titleColor: c.ttTitle, bodyColor: c.ttBody,`
  - x scale: `ticks: { … color: c.tick, … }` and `border: { color: c.axis }`
  - y scale: `ticks: { color: c.tick, … }` and `grid: { color: c.grid }`

- [ ] **Step 4: Recolor live on `ba:theme`** — register once inside the IIFE (e.g., just before `window.renderLens = …`). Uses Chart.js 4's `Chart.getChart(canvas)` so there are no stale references after range-rebuilds:
```js
  document.addEventListener("ba:theme", function () {
    if (typeof Chart === "undefined" || !Chart.getChart) return;
    var c = chartChrome();
    document.querySelectorAll(".chart-box canvas").forEach(function (cv) {
      var ch = Chart.getChart(cv);
      if (!ch) return;
      var o = ch.options;
      o.plugins.tooltip.backgroundColor = c.ttBg; o.plugins.tooltip.borderColor = c.ttBorder;
      o.plugins.tooltip.titleColor = c.ttTitle;   o.plugins.tooltip.bodyColor = c.ttBody;
      o.scales.x.ticks.color = c.tick; o.scales.x.border.color = c.axis;
      o.scales.y.ticks.color = c.tick; o.scales.y.grid.color = c.grid;
      ch.update("none");
    });
  });
```

- [ ] **Step 5: Verify + commit** — no JS unit test (DOM/Chart glue, matching the repo's other untested renderers; verified live in Task 12). Sanity-check syntax: `node --check baileyanalytics/dashboards/lens.js` → no output.
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/lens.js
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): theme-aware Chart.js chrome + live recolor on ba:theme"
```

---

### Task 8: `personalize.js` — toggle, persistence, OS-follow, banner

**Files:**
- Modify: `dashboards/personalize.js` (the `store` wrapper is lines 9–33; `BAPrefs` lines 35–38; `injectNav`/`offlineBanner`/`init` follow)

**Interfaces:**
- Consumes: `core.resolveTheme` (available but the live path computes directly), `store.getPref/setPref`.
- Produces: a `.theme-toggle` button in `nav.top-nav`; dispatches `ba:theme` `{detail:{theme}}`; `self.BAPrefs.getTheme()/setTheme(key)`.

- [ ] **Step 1: Add theme helpers to `BAPrefs`** — extend the `self.BAPrefs = { … }` object:
```js
    getTheme: function () { return store.getPref("theme"); },
    setTheme: function (key) { store.setPref("theme", key); }
```

- [ ] **Step 2: Add the theme module** — inside the IIFE (after the `store`/`BAPrefs` setup), add:
```js
  // --- Theme toggle (injected; mirrors the Favorites nav entry) ---
  var SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  var THEME_BG = { dark: "#0A0E14", light: "#F5F5F7" };
  var BANNER = { dark: { bg: "#0F172A", fg: "#F8FAFC", bd: "#1E293B" },
                 light: { bg: "#FFFFFF", fg: "#1D1D1F", bd: "#D2D2D7" } };

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }
  function syncMeta(theme) {
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute("content", THEME_BG[theme] || THEME_BG.dark);
  }
  function syncToggle(btn, theme) {
    var toLight = theme === "dark";                 // show the destination icon
    btn.innerHTML = toLight ? SUN : MOON;
    var lbl = "Switch to " + (toLight ? "light" : "dark") + " theme";
    btn.setAttribute("aria-label", lbl); btn.title = lbl;
  }
  function applyTheme(theme, persist) {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist) store.setPref("theme", theme);
    syncMeta(theme);
    try { document.dispatchEvent(new CustomEvent("ba:theme", { detail: { theme: theme } })); } catch (e) {}
  }
  function injectThemeToggle() {
    var nav = document.querySelector("nav.top-nav");
    if (!nav || nav.querySelector("[data-theme-toggle]")) return;
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "theme-toggle"; btn.setAttribute("data-theme-toggle", "");
    syncToggle(btn, currentTheme());
    btn.addEventListener("click", function () {
      var next = currentTheme() === "light" ? "dark" : "light";
      applyTheme(next, true); syncToggle(btn, next);
    });
    nav.appendChild(btn);
  }
  // Follow the OS until the visitor explicitly picks (no stored pref).
  if (window.matchMedia) {
    try {
      matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
        if (store.getPref("theme")) return;
        var theme = e.matches ? "dark" : "light";
        applyTheme(theme, false);
        var btn = document.querySelector("[data-theme-toggle]");
        if (btn) syncToggle(btn, theme);
      });
    } catch (e) { /* old Safari: addListener-only; non-critical */ }
  }
```

- [ ] **Step 3: Theme the offline banner** — in `offlineBanner()`, remove the hardcoded `background`/`color`/`border` from the `cssText` string and instead set them from the theme; recolor on `ba:theme`. Replace the `b.style.cssText = …` colors and add after `document.body.appendChild(b);`:
```js
    function styleBanner() { var c = BANNER[currentTheme()] || BANNER.dark;
      b.style.background = c.bg; b.style.color = c.fg; b.style.borderColor = c.bd; }
    styleBanner();
    document.addEventListener("ba:theme", styleBanner);
```
(Set the remaining static `cssText` to `"position:fixed;left:50%;bottom:1rem;transform:translateX(-50%);z-index:50;border:1px solid;border-radius:999px;padding:.5rem 1rem;font:500 .8rem -apple-system,BlinkMacSystemFont,'Inter',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.4);display:none"` — note `border:1px solid` with the color applied by `styleBanner`.)

- [ ] **Step 4: Wire into `init()`** — change `function init() { injectNav(); offlineBanner(); }` to also call `injectThemeToggle();`:
```js
  function init() { injectNav(); injectThemeToggle(); offlineBanner(); }
```

- [ ] **Step 5: Verify + commit** — `node --check baileyanalytics/dashboards/personalize.js` → no output. (DOM glue, verified live in Task 12.)
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add dashboards/personalize.js
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): nav toggle, persistence, OS-follow, themed offline banner"
```

---

### Task 9: `index.html` (home) light block

**Files:**
- Modify: `index.html` (inline `<style>`, lines 28–340)

- [ ] **Step 1: Append to the home inline `<style>`** (just before `</style>`):
```css
        /* ---- Light theme ---- */
        [data-theme="light"] {
            --bg:#F5F5F7; --panel:#FFFFFF; --border:#D2D2D7; --text:#1D1D1F;
            --muted:#4B4B4F; --faint:#5E5E63; --blue:#0068D1;
        }
        [data-theme="light"] .pill.ok { color:#1A7F37; }
        [data-theme="light"] .pill.watch { color:#8A5D00; }
        [data-theme="light"] .pill.elevated { color:#C2410C; }
        [data-theme="light"] .pill.alert { color:#D70015; }
        [data-theme="light"] .pill.neutral { color:#0068D1; }
        [data-theme="light"] .seclabel .dot { background:#1A7F37; box-shadow:0 0 0 3px rgba(26,127,55,.18); }
        [data-theme="light"] a.email:hover, [data-theme="light"] a.email:focus-visible { color:#0068D1; border-bottom-color:#0068D1; }
        [data-theme="light"] .lens { box-shadow:0 1px 3px rgba(0,0,0,.06); }
        /* theme toggle (three-CSS-places trap: mirrors lens.css) */
        .theme-toggle { display:inline-flex; align-items:center; justify-content:center; background:transparent;
            border:0; color:var(--muted); cursor:pointer; padding:.5rem; border-radius:6px; line-height:0; transition:color .2s; }
        .theme-toggle:hover, .theme-toggle:focus-visible { color:var(--text); }
        .theme-toggle:focus-visible { outline:2px solid var(--blue); outline-offset:3px; }
        .theme-toggle svg { width:1.15rem; height:1.15rem; display:block; }
        @media (prefers-reduced-motion: reduce) { .theme-toggle { transition:none; } }
```
> Home uses `--faint` where lens.css uses `--dim`; mapping `--faint:#5E5E63` (= lens.css light `--dim`) keeps home's caption text at AA. `a.cta`, `.sub-form button`, `a.email`, `.brief-strip-*` already use `var(--blue)`/`var(--bg)` and flip automatically.

- [ ] **Step 2: Verify + commit** — open `http://localhost:8000/` (Task 12 covers the live check). 
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add index.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): home light overrides + toggle styles"
```

---

### Task 10: `about.html` — convert to variables + light block

**Files:**
- Modify: `about.html` (inline `<style>`, lines 17–203)

- [ ] **Step 1: Add a token block** at the very top of about's `<style>` (before the `*` reset):
```css
        :root{ --bg:#0A0E14; --panel:#0F172A; --border:#1E293B; --text:#F8FAFC;
            --muted:#94A3B8; --body:#CBD5E1; --faint:#76879E; --label:#64748B;
            --blue:#38BDF8; --blue-hover:#7DD3FC; }
        [data-theme="light"]{ --bg:#F5F5F7; --panel:#FFFFFF; --border:#D2D2D7; --text:#1D1D1F;
            --muted:#4B4B4F; --body:#2C2C30; --faint:#5E5E63; --label:#6A6A6F;
            --blue:#0068D1; --blue-hover:#0068D1; }
```

- [ ] **Step 2: Replace each literal hex** in about's rules with its token (complete mapping — every literal is covered):

| Literal | → token | Where |
|---|---|---|
| `#0A0E14` | `var(--bg)` | `body` bg; `.sub-form button` color |
| `#F8FAFC` | `var(--text)` | `body`/`h1`/`h2` color; nav `:hover`; `.sub-form input` color |
| `#94A3B8` | `var(--muted)` | `nav a`; `.sub-copy` |
| `#CBD5E1` | `var(--body)` | `p` color |
| `#38BDF8` | `var(--blue)` | nav hover border; `nav a:focus-visible` outline; `a.email`; `a.email:focus-visible` outline; `.sub-form button` bg |
| `#7DD3FC` | `var(--blue-hover)` | `a.email:hover`/`:focus-visible` color + border |
| `#1E293B` | `var(--border)` | `.contact` border-top; `.sub-form input` border |
| `#76879E` | `var(--faint)` | `.disclosure` |
| `#64748B` | `var(--label)` | `.contact-label` |
| `#0F172A` | `var(--panel)` | `.sub-form input` bg |

- [ ] **Step 3: Add the `.theme-toggle` styles** (mirror Task 9 Step 1's `.theme-toggle` block) before `</style>`.

- [ ] **Step 4: Verify** — confirm no `#` hex remains in about's `<style>` except inside the new `:root`/`[data-theme]` token blocks: `grep -n "#" baileyanalytics/about.html` and eyeball the `<style>` region. Live check in Task 12.

- [ ] **Step 5: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add about.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): convert about.html to tokens + light theme"
```

---

### Task 11: `offline.html` + `404.html` — convert + light block

**Files:**
- Modify: `offline.html` (inline `<style>` lines 9–18), `404.html` (inline `<style>` lines 9–16)

- [ ] **Step 1: `offline.html`** — replace the `<style>` body's literals with tokens and add the blocks. Add at the top of `<style>`:
```css
    :root{ --bg:#0A0E14; --text:#F8FAFC; --muted:#94A3B8; --blue:#38BDF8; }
    [data-theme="light"]{ --bg:#F5F5F7; --text:#1D1D1F; --muted:#4B4B4F; --blue:#0068D1; }
```
Then map: `#0A0E14`→`var(--bg)` (body bg), `#F8FAFC`→`var(--text)` (body color), `#94A3B8`→`var(--muted)` (`p`), `#38BDF8`→`var(--blue)` (`a`).

- [ ] **Step 2: `404.html`** — same approach. Add at the top of `<style>`:
```css
    :root{ --bg:#0A0E14; --text:#F8FAFC; --muted:#94A3B8; --blue:#38BDF8; }
    [data-theme="light"]{ --bg:#F5F5F7; --text:#1D1D1F; --muted:#4B4B4F; --blue:#0068D1; }
```
Then map: `#0A0E14`→`var(--bg)`, `#F8FAFC`→`var(--text)`, `#94A3B8`→`var(--muted)` (`p`), `#38BDF8`→`var(--blue)` (`a`).
> These pages have no `nav.top-nav`, so no toggle is injected — they render in the resolved theme via the pre-paint script (acceptable for edge pages).

- [ ] **Step 3: Commit**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add offline.html 404.html
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): theme offline.html + 404.html"
```

---

### Task 12: Stamp pages, catch-up baked brief, full verification

**Files:**
- Modify (machine): the ~50 hand-written pages (theme:head fragment); the baked brief surfaces.

- [ ] **Step 1: Stamp the hand-written pages**
Run: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tools/theme_head.py"`
Expected: `Stamped N pages.` Re-run → `Stamped 0 pages.` (idempotent). Spot-check `git -C … diff -- dashboards/recession-watch.html` shows the `<!-- theme:head -->` line added before `</head>`.

- [ ] **Step 2: Catch-up the existing baked brief surfaces** (so old archive permalinks pick up the theme). Identify the archive re-render path first: `grep -rn "render_brief\|render_archive\|days/" scripts/lenses/today.py scripts/lenses/briefpage.py`. Re-render each baked file (`dashboards/brief.html`, `dashboards/brief/*.html`) from its committed `data/brief/days/*.json` via `briefpage.render_brief(...)`/`render_archive_index(...)` so output is byte-identical to a future bake. If no convenient re-render entry exists, add a one-time `scripts/tools/rebake_brief_archive.py` that loops the days and writes them. **Verify** the only change is the added fragment: `git -C … diff -- dashboards/brief.html dashboards/brief/` should show `<!-- theme:head -->` + the script line, nothing else.

- [ ] **Step 3: Full Python suite** (redirect — never pipe)
Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py" > "C:/Users/jmich/AppData/Local/Temp/claude/C--Users-jmich-Documents-Business-Repositories/0d928ddb-50c4-4a32-bf8d-2f9d5ebfcd26/scratchpad/suite.txt" 2>&1`
Then read the tail. Expected: `OK` (≈+9 new tests; no failures).

- [ ] **Step 4: Full JS suite**
Run: `node --test baileyanalytics/scripts/tests/js/*.test.js`
Expected: all pass (`resolveTheme` added; existing pass).

- [ ] **Step 5: Manual verification** (serve `python -m http.server 8000` from `baileyanalytics/`; batch the results for Michael):
  - Toggle on home, a lens page (confirm **charts recolor instantly**), the brief, about, a hub, track-record, favorites — desktop + a ~375px phone width. Confirm the control is clean/out-of-the-way, no layout shift.
  - **No-FOUC:** hard-reload (Ctrl-F5) with `ba:prefs.theme` set to `light`, to `dark`, and **unset** under an OS set to light and to dark — zero flash of the wrong theme each time.
  - **axe** (DevTools) in **light** mode on home, a lens page, a hub — zero contrast/role violations.
  - `prefers-reduced-motion` on → toggle still flips, icon transition suppressed.
  - Offline banner: DevTools offline → banner shows in the active theme.

- [ ] **Step 6: Commit the machine-generated surfaces**
```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add -A
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" commit -m "feat(theme): stamp theme:head into pages + baked brief catch-up"
```
> Before `add -A`, confirm `git status` shows only theme-related page edits (and **not** the unrelated untracked `2026-06-24-score-explain-order-signals-design.md`, which stays untracked).

---

## Self-Review

**Spec coverage:** §2 behavior → T1/T8; §3 S1 `lens.css` → T6; S2 home → T9; S3 about → T10; S4 charts → T7; S5 banner → T8; S6/S7 → T11; §4 D1–D2 toggle → T8; D3 marker/single-source → T2/T3/T4; D4 meta → T8; D5 live recolor → T7; D6 conversions → T10/T11; D7 instant → T6/T8 (no transition code); D8 out-of-scope → (nothing to do); §5 palette → T6 + T5 gate; §6.2 stamper → T3 + T12; §9 testing → T1/T2/T3/T4/T5 + T12 manual. All covered.

**Placeholder scan:** none — every step has concrete code/commands. The one judgment call (T12 Step 2 archive re-render entry point) has an explicit fallback (write `rebake_brief_archive.py`) and a verification (git diff = fragment only).

**Type/name consistency:** `theme_head()` (Task 2) consumed by `theme_head.py` import (T3) + `briefpage._THEME_HEAD` (T4); marker `<!-- theme:head -->` consistent across T3/T4/T12; `ba:theme` event dispatched in T8, consumed in T7 + the banner (T8); `--chart-*` vars defined in T6, read in T7; `resolveTheme` defined T1, mirrored (not imported) by the inline script T2; `data-theme` attribute + `ba:prefs.theme` key consistent throughout.

## Execution Handoff

Two execution options — **inline is recommended here** (Michael prefers inline over per-task subagent fan-out; the tasks are tightly coupled and share my context).

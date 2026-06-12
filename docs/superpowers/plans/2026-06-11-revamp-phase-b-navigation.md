# Revamp Phase B — Navigation Implementation Plan (READY — spec signed off 2026-06-12)

> **READY (spec signed off 2026-06-12) — execute after Phase A merges.** Decision ②: the merged surface is **Today's Brief at `/dashboards/brief.html`** — all nav/back targets below reflect that. Spec: `docs/superpowers/specs/2026-06-11-website-revamp-design.md` §1, §4, §7, §12.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistent 4-item top nav on every page, breadcrumb + journey-aware back on lens pages, one back-link convention site-wide, the mobile home-header fix, and the tick-label dedupe.

**Architecture:** Pure presentation: HTML nav-line sweep across all pages (mechanical, scripted), `lens.js` render-time breadcrumb/back computation (referrer-based, validated in spec §10), one Chart.js tick-callback fix. No pipeline or JSON changes.

**Tech Stack:** Hand-written HTML/JS + lens.css. No new dependencies.

**Branch:** `revamp-phase-b` off `main` (after Phase A merges).

---

### Task 1: top-nav sweep (every page)

**Files:**
- Modify: every HTML page with `<nav class="top-nav">` — `dashboards/brief.html`, `about.html`, `dashboards/index.html`, `dashboards/track-record.html`, 8 × `dashboards/<cat>/index.html`, 33 lens pages (`dashboards/*.html` + `dashboards/<cat>/*.html`); plus the home `index.html` nav (Task 4 handles home's layout).
- Modify: `dashboards/lens.css` (active-link style)

- [ ] **Step 1:** Add the active-state style to `dashboards/lens.css` after the `nav a:hover` rule:

```css
nav a[aria-current="page"]{color:var(--text);border-bottom-color:var(--blue)}
```

- [ ] **Step 2:** Define the canonical nav line (active page gets `aria-current="page"`):

```html
<nav class="top-nav"><a href="/dashboards/brief.html">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
```

- [ ] **Step 3:** Sweep with `bash` from `baileyanalytics/` — every current nav is the single line `<nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>`:

```bash
NEW='<nav class="top-nav"><a href="/dashboards/brief.html">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>'
OLD='<nav class="top-nav"><a href="/dashboards/">Dashboards</a><a href="/about.html">About</a></nav>'
grep -rl --include="*.html" -F "$OLD" . | while read -r f; do
  python - "$f" "$OLD" "$NEW" <<'EOF'
import sys, pathlib
p, old, new = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
EOF
done
```

Then hand-set `aria-current="page"` on the matching link in the four destination pages: `dashboards/brief.html` (Today's Brief), `dashboards/index.html` (Dashboards), `dashboards/track-record.html` (Track Record), `about.html` (About).

- [ ] **Step 4:** Verify: `grep -rL --include="*.html" "Track Record" . | grep -v docs/ | grep -v economic.html` → only redirect stubs and `index.html` (home, Task 4) may remain.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat(nav): persistent 4-item top nav on every page"`

---

### Task 2: breadcrumb + journey-aware back in `lens.js`

**Files:**
- Modify: `dashboards/lens.js` (`DEFAULT_OPTS` ~line 149, `render()` ~line 198)
- Modify: `dashboards/lens.css` (crumbs styles)
- Modify: the 28 non-economic lens pages already pass `back`/`href` opts — they keep working; the 5 economic lens pages need no edit (new defaults fix them).

- [ ] **Step 1:** Add crumb styles to `dashboards/lens.css` after the `.back` rules:

```css
.crumbs{font-size:.78rem;color:var(--dim);letter-spacing:.03em;margin-bottom:.35rem}
.crumbs a{color:var(--dim);text-decoration:none}
.crumbs a:hover{color:var(--blue)}
.crumbs .sep{margin:0 .4rem;color:var(--faint)}
.crumbs .here{color:var(--muted)}
```

- [ ] **Step 2:** In `lens.js`, fix the economic default (spec B2) — replace `DEFAULT_OPTS`:

```javascript
  const DEFAULT_OPTS = {
    back: "Economic Lenses",
    href: "/dashboards/economic/",
    foot: 'Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">Federal Reserve Economic Data (FRED)</a>, ' +
      'St. Louis Fed. Refreshed daily. The "read" is generated from the latest values by a fixed rule set.',
  };
```

- [ ] **Step 3:** In `lens.js`, add the journey resolver above `render()`:

```javascript
  // Journey-aware back: where the reader CAME FROM (same-origin referrer),
  // falling back to the category hub. Validated against the browser-default
  // strict-origin-when-cross-origin policy — never add a stricter
  // <meta name="referrer"> or this silently degrades to the fallback.
  function journeyBack(opts) {
    try {
      const r = document.referrer ? new URL(document.referrer) : null;
      if (r && r.origin === location.origin) {
        if (r.pathname === "/dashboards/brief.html") return { label: "Back to Today’s Brief", href: "/dashboards/brief.html" };
        if (r.pathname === "/" || r.pathname === "/index.html") return { label: "Back to home", href: "/" };
      }
    } catch (e) { /* malformed referrer: use the fallback */ }
    return { label: opts.back, href: opts.href };
  }
```

- [ ] **Step 4:** In `render()`, replace the back-link line (`<a class="back" href="${esc(opts.href)}">← ${esc(opts.back)}</a>`) with breadcrumb + computed back:

```javascript
    const back = journeyBack(opts);
    root.innerHTML = `
      <div class="crumbs"><a href="/dashboards/">Dashboards</a><span class="sep">›</span><a href="${esc(opts.href)}">${esc(opts.back)}</a><span class="sep">›</span><span class="here">${esc(lens.title)}</span></div>
      <a class="back" href="${esc(back.href)}">← ${esc(back.label)}</a>
```

(rest of the template unchanged).

- [ ] **Step 5:** Verify in a served browser walk: home → economic lens shows "← Back to home"; `/dashboards/brief.html` → any lens shows "← Back to Today’s Brief"; direct open shows "← <Category>"; the crumb's middle link on an economic page goes to `/dashboards/economic/`.

- [ ] **Step 6: Commit** — `git add dashboards/lens.js dashboards/lens.css && git commit -m "feat(nav): breadcrumbs + journey-aware back on lens pages"`

---

### Task 3: back-link convention sweep (one rule: climb one level; destinations have none)

**Files:**
- Modify: `dashboards/track-record.html`
- Verify only: 8 × `dashboards/<cat>/index.html` (keep `← Dashboards` — already the convention), `dashboards/index.html` (destination, no back link — verify none present)

- [ ] **Step 1:** In `dashboards/track-record.html`, delete the back-link line (Phase A re-pointed it to `← Today's Brief`; with the brief in the top nav, destinations carry no back link). Same rule for `dashboards/brief.html`: delete its `← Dashboards` back link — it's a destination now.
- [ ] **Step 2:** Verify the rule sweep: `grep -n 'class="back"' *.html dashboards/*.html dashboards/*/index.html` → hits only in the 8 category hub pages (lens pages render theirs from `lens.js`).
- [ ] **Step 3: Commit** — `git add -A && git commit -m "feat(nav): one back-link convention — climb one level, destinations have none"`

---

### Task 4: home header fix (mobile overlap, audit D1)

**Files:**
- Modify: `index.html` (nav block lines 316–319 and `nav.top-nav` CSS lines 55–62, hero CSS ~line 96)

- [ ] **Step 1:** Replace home's nav content with the 4-item set (same as Task 1, no `aria-current` — home is the wordmark's own page).
- [ ] **Step 2:** In home's inline CSS, scope the fixed nav to wide screens and give the hero clearance on small ones — replace the `nav.top-nav` block with:

```css
        nav.top-nav {
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            z-index: 10;
            display: flex;
            gap: 1.75rem;
        }
        @media (max-width: 640px) {
            nav.top-nav { position: static; justify-content: center; gap: 1rem; flex-wrap: wrap; padding-top: .25rem; }
        }
```

- [ ] **Step 3:** Screenshot home at 390px (headless or device toolbar): title and nav no longer overlap; nav links wrap above the H1.
- [ ] **Step 4: Commit** — `git add index.html && git commit -m "fix(home): mobile header overlap — static nav under 640px"`

---

### Task 5: x-axis tick dedupe (audit D3 — 163 chart-range combos)

**Files:**
- Modify: `dashboards/lens.js` (x-scale `ticks.callback`, ~line 94)

- [ ] **Step 1:** Replace the callback with a deduping version (month and year granularity both):

```javascript
                 callback(v, i, ticks) {
                   const s = this.getLabelForValue(v); if (!s) return s;
                   // annual labels ("2026") have no month part — always show the year
                   const fmt = lbl => (years && years <= 1 && lbl.length >= 7) ? MONTHS[+lbl.slice(5, 7) - 1] : lbl.slice(0, 4);
                   const cur = fmt(s);
                   if (i > 0) {
                     const prev = this.getLabelForValue(ticks[i - 1].value);
                     if (prev && fmt(prev) === cur) return "";
                   }
                   return cur; }
```

- [ ] **Step 2:** Re-run the QA sweep (`node sweep.js` from the audit toolkit — `docs/superpowers/mockups/2026-06-11-revamp/sweep-report.json` documents the before-state) → expect **0** dup-tick findings across all 33 pages × 3 ranges.
- [ ] **Step 3: Commit** — `git add dashboards/lens.js && git commit -m "fix(charts): dedupe consecutive x-axis tick labels (year + month granularity)"`

---

### Task 6: Track Record empty state (audit D4)

**Files:**
- Modify: `dashboards/track-record.js` (the `!tr || !tr.graded` early-return branch, lines 28–32)

- [ ] **Step 1:** The young-record copy already lands in `#since`, but the two stat cards keep their static "—" numbers. Fill them in the same branch:

```javascript
    if (!tr || !tr.graded) {
      document.getElementById("since").textContent =
        "The first predictions are open now — grades land as the prints arrive. Check back this week.";
      document.getElementById("calibration").textContent = "pending";
      document.getElementById("skill").textContent = "pending";
      return;
    }
```

(If the stat-number elements use different ids, match the existing `tr.calibration`/`tr.skill` fill calls at lines 41–42 — same targets.)

- [ ] **Step 2:** Verify: serve locally without `data/predictions/track-record.json` → the cards read "pending" over their captions instead of bare em-dashes.
- [ ] **Step 3: Commit** — `git add dashboards/track-record.js && git commit -m "fix(track-record): label empty stat cards 'pending' instead of em-dashes"`

---

### Task 7: end-to-end verification

- [ ] **Step 1:** Full unittest suite (unchanged by this phase, but run it) → PASS.
- [ ] **Step 2:** Served walk, desktop + 390px: every page shows the 4-item nav; the two flagship journeys round-trip (Brief → lens → "← Back to Today's Brief" → Brief; home → lens → "← Back to home"); Track Record reachable from any page in one click.
- [ ] **Step 3:** `/code-review`; fix findings; stop — merge/push only on Michael's go.

# Distribution Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give baileyanalytics.com its acquisition and retention loops — daily email digest (Buttondown), baked/crawlable brief with dated archive permalinks, og:image verdict cards, sitemap/canonical/JSON-LD, and static lens reads — per the spec `docs/superpowers/specs/2026-06-12-distribution-phase-design.md`.

**Architecture:** New pure renderer modules in `scripts/lenses/` (no network/disk I/O) consumed by `refresh_lenses.py`'s `--brief` pass, which becomes the single publication hook: when the brief's content changed (`wrote` flag), it bakes `dashboards/brief.html`, a dated archive page + JSON, an og card, the archive index, the sitemap, the home-page patches, and the lens static-read patches. A separate `scripts/send_digest.py` (network owner) posts the email to Buttondown, idempotent via the archive manifest + an API already-sent check.

**Tech Stack:** Python 3.12 stdlib + Pillow (new dep), existing `unittest` suite, Buttondown REST API, GitHub Actions.

**Key repo facts the implementer must know:**
- Run everything from the parent dir with absolute paths (per CLAUDE.md — never `cd <repo> &&`). Repo root: `C:/Users/jmich/Documents/Business/Repositories/baileyanalytics`.
- Tests: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"` (~270 tests pass today).
- `build.write_lens_file(path, json)` is content-aware (ignores timestamps), returns True iff written. `refresh_brief` already uses its result as the `wrote` publication-day flag.
- `brief.lens_href(category, lens_id)` maps lens ids → public page paths (handles all slug irregularities). `config.CATEGORIES` is the category list (`id`, `title`, `lenses`).
- `today.json` shapes (all consumed by the new renderers): `generated_at`; `verdict {status, shape, sentence}`; `transitions [{lens_id, lens_title, category, href, from_status, to_status, direction, headline}]`; `top_moves [{lens_id, lens_title, category, href, headline, accent, sparkline, stat_label, stat_value, delta, dir}]`; `watching [{key, indicator, lens, category, title, lens_title, due, point_fmt, implied_status, current_status, change, href}]`; `pressure [{lens_id, lens_title, category, href, status, headline}]`; `categories [{category, title, status, href, sentence}]`; `status_counts {ok, watch, elevated, alert, neutral}`; `lenses [...]`.
- Lens pages are uniform shells: `<main id="lens-root"><div class="status-msg">…</div></main>` + `renderLens("/data/<dir>/<id>.json")`. `lens.js` replaces `#lens-root`'s innerHTML wholesale on success, so baked content inside it needs **no lens.js change**.
- The brief pass needs no network: `_load_brief_indices` reads committed `index.json` files from disk, so `python scripts/refresh_lenses.py --brief` works locally without keys.
- Commit only; **never push** (Michael pushes on his go). Branch: all work on `distribution`.

---

### Task 1: Branch + dependencies + fonts

**Files:**
- Modify: `baileyanalytics/requirements.txt`
- Create: `baileyanalytics/assets/fonts/Inter-Regular.ttf`, `baileyanalytics/assets/fonts/Inter-SemiBold.ttf`, `baileyanalytics/assets/fonts/OFL.txt`

- [ ] **Step 1: Create the feature branch**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" checkout -b distribution
```

- [ ] **Step 2: Add Pillow to requirements.txt**

```
numpy==2.2.6
pandas==2.3.0
statsmodels==0.14.4
Pillow==11.2.1
```

Then: `pip install Pillow==11.2.1` (verify locally installed: `python -c "import PIL; print(PIL.__version__)"` → `11.2.1`). If 11.2.1 is unavailable, use the latest 11.x and pin that exact version in requirements.txt.

- [ ] **Step 3: Download and bundle Inter fonts**

Download the official Inter release and copy two static TTFs plus the license:

```powershell
$tmp = "$env:TEMP\inter-font"; New-Item -ItemType Directory -Force $tmp
Invoke-WebRequest -Uri "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip" -OutFile "$tmp\inter.zip"
Expand-Archive "$tmp\inter.zip" -DestinationPath "$tmp\x" -Force
New-Item -ItemType Directory -Force "C:\Users\jmich\Documents\Business\Repositories\baileyanalytics\assets\fonts"
Copy-Item "$tmp\x\extras\ttf\Inter-Regular.ttf" "C:\Users\jmich\Documents\Business\Repositories\baileyanalytics\assets\fonts\"
Copy-Item "$tmp\x\extras\ttf\Inter-SemiBold.ttf" "C:\Users\jmich\Documents\Business\Repositories\baileyanalytics\assets\fonts\"
Copy-Item "$tmp\x\LICENSE.txt" "C:\Users\jmich\Documents\Business\Repositories\baileyanalytics\assets\fonts\OFL.txt"
```

If the zip layout differs (paths vary by release), locate `Inter-Regular.ttf` / `Inter-SemiBold.ttf` anywhere in the extracted tree (`Get-ChildItem -Recurse -Filter "Inter-Regular.ttf"`) — any static (non-variable) TTF build is fine. Verify both files are >100KB and `python -c "from PIL import ImageFont; ImageFont.truetype('C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/assets/fonts/Inter-SemiBold.ttf', 40)"` exits clean.

- [ ] **Step 4: Commit**

```bash
git -C "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics" add requirements.txt assets/
git commit -m "chore: add Pillow dependency and bundled Inter fonts for og cards"
```
(Run commit with `-C` as well; all later commits follow this pattern.)

---

### Task 2: `regions.py` — marker-region patcher (shared by home patch + lens static reads)

**Files:**
- Create: `baileyanalytics/scripts/lenses/regions.py`
- Test: `baileyanalytics/scripts/tests/test_regions.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import regions

DOC = "<head>\n<!-- og-image:start --><meta old><!-- og-image:end -->\n</head>"


class TestReplaceRegion(unittest.TestCase):
    def test_replaces_content_between_markers(self):
        out, changed = regions.replace_region(DOC, "og-image", "<meta new>")
        self.assertTrue(changed)
        self.assertIn("<!-- og-image:start --><meta new><!-- og-image:end -->", out)
        self.assertNotIn("<meta old>", out)

    def test_unchanged_content_reports_no_change(self):
        out, changed = regions.replace_region(DOC, "og-image", "<meta old>")
        self.assertFalse(changed)
        self.assertEqual(out, DOC)

    def test_missing_markers_is_a_safe_noop(self):
        out, changed = regions.replace_region("<head></head>", "og-image", "<meta new>")
        self.assertFalse(changed)
        self.assertEqual(out, "<head></head>")

    def test_multiline_region(self):
        doc = "a\n<!-- x:start -->\nline1\nline2\n<!-- x:end -->\nb"
        out, changed = regions.replace_region(doc, "x", "new")
        self.assertTrue(changed)
        self.assertIn("<!-- x:start -->new<!-- x:end -->", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_regions.py" -v`
Expected: FAIL/ERROR — `cannot import name 'regions'`.

- [ ] **Step 3: Write the implementation**

```python
"""Marker-region patching for HTML files the pipeline rewrites in place.
A region is delimited by `<!-- name:start -->` / `<!-- name:end -->` comments;
replace_region swaps everything between them (markers preserved, so the next
run can patch again). Missing markers are a safe no-op — an unpatched page can
never be corrupted. Pure: text in, (text, changed) out."""

import re


def replace_region(text, name, content):
    """Replace the region `name` with `content`. Returns (new_text, changed)."""
    pattern = re.compile(
        r"(<!-- " + re.escape(name) + r":start -->).*?(<!-- " + re.escape(name) + r":end -->)",
        re.DOTALL)
    m = pattern.search(text)
    if not m:
        return text, False
    new = pattern.sub(lambda mo: mo.group(1) + content + mo.group(2), text, count=1)
    return new, new != text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_regions.py" -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/regions.py scripts/tests/test_regions.py
git commit -m "feat: marker-region patcher for pipeline-rewritten HTML"
```

---

### Task 3: `sitemap.py` — sitemap renderer

**Files:**
- Create: `baileyanalytics/scripts/lenses/sitemap.py`
- Test: `baileyanalytics/scripts/tests/test_sitemap.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import sitemap


class TestBuildUrls(unittest.TestCase):
    def test_includes_static_pages_hubs_and_lenses(self):
        urls = dict(sitemap.build_urls([]))
        self.assertIn("https://baileyanalytics.com/", urls)
        self.assertIn("https://baileyanalytics.com/about.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/brief.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/economic/", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/banking/", urls)
        # slug irregulars resolved via brief.lens_href:
        self.assertIn("https://baileyanalytics.com/dashboards/recession-watch.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/consumer/credit-stress.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/banking/asset-quality.html", urls)

    def test_archive_dates_become_dated_urls_with_lastmod(self):
        urls = dict(sitemap.build_urls(["2026-06-11", "2026-06-12"]))
        self.assertEqual(urls["https://baileyanalytics.com/dashboards/brief/2026-06-12.html"],
                         "2026-06-12")
        self.assertIn("https://baileyanalytics.com/dashboards/brief/", urls)

    def test_no_duplicates(self):
        locs = [loc for loc, _ in sitemap.build_urls(["2026-06-12"])]
        self.assertEqual(len(locs), len(set(locs)))


class TestRenderSitemap(unittest.TestCase):
    def test_renders_valid_xml_with_lastmod_only_when_known(self):
        xml_text = sitemap.render_sitemap([("https://x.com/a", None),
                                           ("https://x.com/b", "2026-06-12")])
        dom = xml.dom.minidom.parseString(xml_text)  # raises on invalid XML
        self.assertEqual(len(dom.getElementsByTagName("url")), 2)
        self.assertEqual(len(dom.getElementsByTagName("lastmod")), 1)
        self.assertIn("<loc>https://x.com/a</loc>", xml_text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_sitemap.py" -v`
Expected: FAIL — `cannot import name 'sitemap'`.

- [ ] **Step 3: Write the implementation**

```python
"""sitemap.xml for the whole site. Pure: build_urls/render_sitemap take and
return data; refresh_lenses owns disk I/O. The archive manifest supplies the
dated brief pages, so the sitemap grows one URL per publication day."""

from xml.sax.saxutils import escape

from . import brief, config

SITE = "https://baileyanalytics.com"

STATIC_PAGES = [
    "/",
    "/about.html",
    "/dashboards/",
    "/dashboards/brief.html",
    "/dashboards/brief/",
    "/dashboards/track-record.html",
]


def build_urls(archive_dates):
    """All site URLs as (absolute loc, lastmod-or-None), no duplicates.
    archive_dates: iterable of 'YYYY-MM-DD' publication days."""
    urls = [(SITE + p, None) for p in STATIC_PAGES]
    for cat in config.CATEGORIES:
        urls.append((f"{SITE}/dashboards/{cat['id']}/", None))
        for lens in cat["lenses"]:
            urls.append((SITE + brief.lens_href(cat["id"], lens.id), None))
    for d in sorted(archive_dates):
        urls.append((f"{SITE}/dashboards/brief/{d}.html", d))
    seen, out = set(), []
    for loc, mod in urls:
        if loc not in seen:
            seen.add(loc)
            out.append((loc, mod))
    return out


def render_sitemap(urls):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        entry = f"<url><loc>{escape(loc)}</loc>"
        if lastmod:
            entry += f"<lastmod>{lastmod}</lastmod>"
        out.append(entry + "</url>")
    out.append("</urlset>")
    return "\n".join(out)
```

Note: markets' crypto lens isn't in `config.CATEGORIES`'s markets entry (`MARKET_FRED_LENSES` excludes it) — add its page explicitly to `STATIC_PAGES`: append `"/dashboards/markets/crypto-structure.html"` to the list above (and adjust the no-duplicates test expectation if needed).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_sitemap.py" -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/sitemap.py scripts/tests/test_sitemap.py
git commit -m "feat: sitemap renderer covering static pages, hubs, lenses, and brief archive"
```

---

### Task 4: `ogcard.py` — Pillow verdict cards

**Files:**
- Create: `baileyanalytics/scripts/lenses/ogcard.py`
- Test: `baileyanalytics/scripts/tests/test_ogcard.py`

- [ ] **Step 1: Write the failing test**

```python
import io
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import ogcard

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestRenderCard(unittest.TestCase):
    def test_returns_1200x630_png(self):
        png = ogcard.render_card("watch", "Most of the economy is on solid footing.",
                                 "June 12, 2026")
        img = Image.open(io.BytesIO(png))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, (1200, 630))

    def test_long_sentence_does_not_raise(self):
        long = ("Most of the economy is on solid footing — banks are solid and markets "
                "are calm — but energy and commodity costs are squeezing budgets and "
                "household finances are stretched thin across nearly every measure.")
        png = ogcard.render_card("elevated", long, "June 12, 2026")
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1200, 630))

    def test_unknown_status_uses_fallback_color(self):
        png = ogcard.render_card("bogus", "Sentence.", "June 12, 2026")
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_site_card(self):
        png = ogcard.render_site_card()
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1200, 630))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_ogcard.py" -v`
Expected: FAIL — `cannot import name 'ogcard'`.

- [ ] **Step 3: Write the implementation**

```python
"""1200x630 link-preview cards (og:image), drawn with Pillow in the site's
dark visual language. render_card returns PNG bytes (pure given its inputs;
fonts are read from the repo's bundled assets/fonts). Card failure is the
caller's problem to isolate — these functions just raise."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0A0E14"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
FAINT = "#76879E"
BORDER = "#1E293B"
STATUS_COLORS = {"ok": "#34D399", "watch": "#FBBF24", "elevated": "#FB923C",
                 "alert": "#F87171", "neutral": "#38BDF8"}

_FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"


def _font(size, weight="regular"):
    name = "Inter-SemiBold.ttf" if weight == "semibold" else "Inter-Regular.ttf"
    return ImageFont.truetype(str(_FONT_DIR / name), size)


def _wrap(draw, text, font, max_width):
    """Greedy word wrap by rendered width."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def render_card(status, sentence, date_label):
    """The daily verdict card: wordmark, date, status pill, wrapped sentence."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    margin = 80

    # header: wordmark left, date right
    d.text((margin, 64), "BAILEY ANALYTICS", font=_font(34, "semibold"), fill=TEXT)
    date_font = _font(28)
    d.text((W - margin - d.textlength(date_label, font=date_font), 68),
           date_label, font=date_font, fill=MUTED)
    d.line([(margin, 130), (W - margin, 130)], fill=BORDER, width=2)

    # status pill
    color = STATUS_COLORS.get(status, FAINT)
    pill_font = _font(30, "semibold")
    label = status.upper()
    tw = d.textlength(label, font=pill_font)
    px, py, pad_x, pad_y = margin, 180, 28, 12
    d.rounded_rectangle([px, py, px + tw + 2 * pad_x, py + 30 + 2 * pad_y],
                        radius=28, outline=color, width=3)
    d.text((px + pad_x, py + pad_y - 2), label, font=pill_font, fill=color)

    # verdict sentence: shrink until it fits in 4 lines
    max_w = W - 2 * margin
    for size in (54, 48, 42, 36):
        body_font = _font(size, "semibold")
        lines = _wrap(d, sentence, body_font, max_w)
        if len(lines) <= 4:
            break
    y = 290
    for line in lines[:4]:
        d.text((margin, y), line, font=body_font, fill=TEXT)
        y += int(size * 1.35)

    # footer
    d.text((margin, H - 80), "baileyanalytics.com — Today's Brief",
           font=_font(26), fill=FAINT)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_site_card():
    """One-time static brand card for non-brief pages."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    margin = 80
    d.text((margin, 200), "Bailey Analytics", font=_font(72, "semibold"), fill=TEXT)
    tagline = "Daily, plain-English dashboards on the U.S. and global economy"
    for i, line in enumerate(_wrap(d, tagline, _font(34), W - 2 * margin)):
        d.text((margin, 320 + i * 48), line, font=_font(34), fill=MUTED)
    d.text((margin, H - 80), "baileyanalytics.com", font=_font(26), fill=FAINT)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_ogcard.py" -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Eyeball one card locally** (not automated): run
`python -c "import sys; sys.path.insert(0,'C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts'); from lenses import ogcard; open('C:/Users/jmich/AppData/Local/Temp/card.png','wb').write(ogcard.render_card('watch','Most of the economy is on solid footing - banks are solid and markets are calm - but energy costs are squeezing budgets.','June 12, 2026'))"` and view `%TEMP%\card.png`. Verify: readable, nothing clipped, pill aligned.

- [ ] **Step 6: Commit**

```bash
git add scripts/lenses/ogcard.py scripts/tests/test_ogcard.py
git commit -m "feat: Pillow og:image verdict cards (daily + static site card)"
```

---

### Task 5: `today_sample.json` fixture + `briefpage.py` — the baked brief/archive renderer

**Files:**
- Create: `baileyanalytics/scripts/tests/fixtures/today_sample.json`
- Create: `baileyanalytics/scripts/lenses/briefpage.py`
- Test: `baileyanalytics/scripts/tests/test_briefpage.py`

- [ ] **Step 1: Create the fixture** (`scripts/tests/fixtures/today_sample.json`) — a compact but complete `today.json`:

```json
{
  "generated_at": "2026-06-12T15:17:15Z",
  "verdict": {"status": "watch", "shape": "contained-pressure",
              "sentence": "Most of the economy is on solid footing — banks are solid — but energy costs are squeezing budgets."},
  "transitions": [
    {"lens_id": "energy-electricity", "lens_title": "Electricity & the Grid", "category": "energy",
     "href": "/dashboards/energy/electricity.html", "from_status": "watch", "to_status": "elevated",
     "direction": "worsening", "headline": "Electricity prices are well above last year."}
  ],
  "top_moves": [
    {"lens_id": "energy-commodities", "lens_title": "Commodities & Materials", "category": "energy",
     "href": "/dashboards/energy/commodities.html", "headline": "Commodity costs are surging.",
     "accent": "#FB923C", "sparkline": [10.0, 11.0, 12.5, 30.2],
     "stat_label": "Food", "stat_value": "30.20%", "delta": "18.60%", "dir": "up"}
  ],
  "watching": [
    {"key": "energy/energy-electricity/retail-electricity", "indicator": "retail-electricity",
     "lens": "energy-electricity", "category": "energy",
     "title": "Retail Electricity · Residential", "lens_title": "Electricity & the Grid",
     "due": "2026-06-25", "point_fmt": "18.97¢/kWh", "implied_status": "watch",
     "current_status": "elevated", "change": true, "href": "/dashboards/energy/electricity.html"},
    {"key": "economic/fiscal-health/debt-gdp", "indicator": "debt-gdp", "lens": "fiscal-health",
     "category": "economic", "title": "Federal Debt · % of GDP", "lens_title": "Fiscal Health",
     "due": "2026-09-01", "point_fmt": "122.56%", "implied_status": "elevated",
     "current_status": "elevated", "change": false, "href": "/dashboards/fiscal-health.html"}
  ],
  "pressure": [
    {"lens_id": "consumer-sentiment", "lens_title": "Consumer Sentiment", "category": "consumer",
     "href": "/dashboards/consumer/sentiment.html", "status": "alert",
     "headline": "Consumers are deeply pessimistic — sentiment is near record lows."},
    {"lens_id": "cost-of-living", "lens_title": "The Cost of Living", "category": "economic",
     "href": "/dashboards/cost-of-living.html", "status": "elevated",
     "headline": "Inflation is still hot — well above the Fed's target."},
    {"lens_id": "business-credit", "lens_title": "Business Credit", "category": "business",
     "href": "/dashboards/business/credit.html", "status": "watch",
     "headline": "Business credit bears watching — conditions are tightening at the margin."}
  ],
  "categories": [
    {"category": "economic", "title": "Economic Lenses", "status": "watch",
     "href": "/dashboards/economic/", "sentence": "Mostly steady — a corner or two of the economy runs hot."},
    {"category": "banking", "title": "Banking System Health", "status": "ok",
     "href": "/dashboards/banking/", "sentence": "Banks are solid — capital, profits, and loan books look healthy."}
  ],
  "status_counts": {"ok": 17, "watch": 3, "elevated": 8, "alert": 3, "neutral": 2},
  "lenses": []
}
```

- [ ] **Step 2: Write the failing test**

```python
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import briefpage

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestRenderToday(unittest.TestCase):
    def setUp(self):
        self.html = briefpage.render_brief(TODAY, og_image="/og/brief-2026-06-12.png")

    def test_is_complete_static_document(self):
        self.assertTrue(self.html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("Loading", self.html)
        self.assertNotIn("fetch(", self.html)          # fully static, no JS render

    def test_head_essentials(self):
        self.assertIn('<link rel="canonical" href="https://baileyanalytics.com/dashboards/brief.html">', self.html)
        self.assertIn('property="og:image" content="https://baileyanalytics.com/og/brief-2026-06-12.png"', self.html)
        self.assertIn('"@type": "NewsArticle"', self.html)
        self.assertIn('name="twitter:card" content="summary_large_image"', self.html)

    def test_verdict_and_sections(self):
        self.assertIn("Most of the economy is on solid footing", self.html)
        self.assertIn('class="badge watch"', self.html)
        self.assertIn("What changed today", self.html)
        self.assertIn("Electricity &amp; the Grid", self.html)      # escaped title
        self.assertIn("What we&rsquo;re watching next", self.html)
        self.assertIn("18.97¢/kWh", self.html)
        self.assertIn('id="alert"', self.html)                       # deep-link anchors
        self.assertIn("As of June 12, 2026", self.html)

    def test_sparkline_svg_baked(self):
        self.assertIn("<svg class=\"spark\"", self.html)
        self.assertIn("polyline", self.html)

    def test_no_archive_banner_on_today(self):
        self.assertNotIn("archive-banner", self.html)


class TestRenderArchive(unittest.TestCase):
    def setUp(self):
        self.html = briefpage.render_brief(
            TODAY, og_image="/og/brief-2026-06-12.png", archive_date="2026-06-12",
            prev_date="2026-06-11", next_date=None)

    def test_archive_chrome(self):
        self.assertIn("archive-banner", self.html)
        self.assertIn("see today&rsquo;s brief", self.html)
        self.assertIn('href="/dashboards/brief/2026-06-11.html"', self.html)
        self.assertIn('<link rel="canonical" href="https://baileyanalytics.com/dashboards/brief/2026-06-12.html">', self.html)

    def test_next_link_renders_when_given(self):
        html = briefpage.render_brief(TODAY, og_image="/og/x.png",
                                      archive_date="2026-06-11", next_date="2026-06-12")
        self.assertIn('href="/dashboards/brief/2026-06-12.html"', html)


class TestQuietDay(unittest.TestCase):
    def test_no_transitions_message(self):
        quiet = dict(TODAY, transitions=[], top_moves=[])
        html = briefpage.render_brief(quiet, og_image="/og/x.png")
        self.assertIn("No status changes today", html)


class TestArchiveIndex(unittest.TestCase):
    def test_lists_entries_newest_first_grouped_by_month(self):
        manifest = [
            {"date": "2026-06-11", "status": "watch", "sentence": "Calm-ish."},
            {"date": "2026-06-12", "status": "elevated", "sentence": "Strain showing."},
        ]
        html = briefpage.render_archive_index(manifest)
        self.assertIn("June 2026", html)
        self.assertIn('href="/dashboards/brief/2026-06-12.html"', html)
        self.assertLess(html.index("2026-06-12"), html.index("2026-06-11"))
        self.assertIn('class="badge elevated"', html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_briefpage.py" -v`
Expected: FAIL — `cannot import name 'briefpage'`.

- [ ] **Step 4: Write the implementation.** This transcribes the render logic currently in `dashboards/brief.html`'s inline script into Python, using the same lens.css classes, and adds head/SEO chrome. Read `dashboards/brief.html` lines 71–172 first for the markup being mirrored.

```python
"""The baked Today's Brief page: one renderer for /dashboards/brief.html
(today), the dated archive permalinks, and the archive index. Replaces the
page's former client-side render (one renderer instead of a JS/Python sync
pair). Pure: today.json data in, full HTML documents out."""

import json
from datetime import datetime
from html import escape

from . import feed

SITE = "https://baileyanalytics.com"

# Set after Michael creates the Buttondown account; "" hides the form.
BUTTONDOWN_USERNAME = "baileyanalytics"

CATEGORY_LABELS = {"economic": "Economy", "consumer": "Consumer", "banking": "Banking",
                   "business": "Business", "markets": "Markets", "energy": "Energy",
                   "housing": "Housing", "global": "Global"}

PRESSURE_GROUPS = [
    ("alert", "On alert — levels that have historically meant real stress"),
    ("elevated", "Elevated — clearly outside comfortable ranges"),
    ("watch", "On watch — first warnings"),
]


def _date_label(iso_date):
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def _spark(values, accent):
    """Inline sparkline SVG; mirrors the JS math exactly (toFixed(1))."""
    if not values or len(values) < 2:
        return ""
    vals = [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{(i / (len(vals) - 1) * 100):.1f},{(28 - ((v - lo) / rng) * 26):.1f}"
                   for i, v in enumerate(vals))
    return (f'<svg class="spark" aria-hidden="true" viewBox="0 0 100 30" '
            f'preserveAspectRatio="none"><polyline points="{pts}" fill="none" '
            f'stroke="{escape(accent or "#38BDF8", quote=True)}" stroke-width="2"/></svg>')


def _transitions(transitions):
    if not transitions:
        return ('<div class="status-msg" style="text-align:left;padding:.4rem 0">'
                "No status changes today — a quiet day on the board.</div>")
    rows = []
    for t in transitions:
        rows.append(
            f'<a class="att-row" href="{escape(t["href"], quote=True)}">'
            f'<span class="brief-cat">{escape(CATEGORY_LABELS.get(t["category"], t["category"]))}</span>'
            f'<span class="att-title">{escape(t["lens_title"])}</span>'
            f'<span class="badge {escape(t["from_status"])}">{escape(t["from_status"])}</span>'
            f'<span aria-hidden="true">→</span>'
            f'<span class="badge {escape(t["to_status"])}">{escape(t["to_status"])}</span>'
            f'<span class="att-read">{escape(t["headline"])}</span></a>')
    return "".join(rows)


def _movers(moves):
    if not moves:
        return ""
    cards = []
    for m in moves:
        delta = (f' <i class="delta {escape(m.get("dir", ""))}">{escape(m.get("delta", ""))}</i>'
                 if m.get("delta") else "")
        cards.append(
            f'<a class="hub-card" href="{escape(m["href"], quote=True)}">'
            f'<div class="hub-eyebrow" style="color:{escape(m.get("accent") or "#94A3B8", quote=True)}">'
            f'<span class="hub-cat">{escape(CATEGORY_LABELS.get(m["category"], m["category"]))} ·</span> '
            f'{escape(m["lens_title"])}</div>'
            f'<div class="hub-read">{escape(m.get("headline", ""))}</div>'
            f'{_spark(m.get("sparkline"), m.get("accent"))}'
            f'<div class="hub-stats">{escape(m.get("stat_label", ""))} '
            f'<b>{escape(m.get("stat_value", ""))}</b>{delta}</div></a>')
    return ('<section id="moves-sec"><div class="brief-sec-label" id="moves">Biggest movers</div>'
            '<div class="hub-grid" style="margin-top:.5rem">' + "".join(cards) + "</div></section>")


def _watching(watching):
    if not watching:
        return ""
    rows = []
    for x in watching:
        if x.get("change"):
            claim = (f'we expect <strong>{escape(x["point_fmt"])}</strong> — which would tip '
                     f'{escape(x["lens_title"])} to <span class="badge '
                     f'{escape(x["implied_status"])}">{escape(x["implied_status"])}</span>')
        else:
            claim = f'we expect <strong>{escape(x["point_fmt"])}</strong>, no status change'
        rows.append(f'<a class="state-lens" href="{escape(x["href"], quote=True)}">'
                    f'<span class="state-lens-title">{escape(x["title"])}</span>'
                    f'<span class="state-lens-read">{claim}</span></a>')
    rows.append('<a class="state-link" href="/dashboards/track-record.html">Our track record &rarr;</a>')
    return ("<section><h2 class=\"sec-head\">What we&rsquo;re watching next</h2>"
            '<p class="sec-sub">Our published predictions for the most consequential upcoming '
            "prints — each graded in public when the number lands.</p>" + "".join(rows) + "</section>")


def _pressure(rows):
    if not rows:
        return ""
    groups = []
    for status, label in PRESSURE_GROUPS:
        group = [p for p in rows if p["status"] == status]
        if not group:
            continue
        items = "".join(
            f'<a class="att-row" href="{escape(p["href"], quote=True)}">'
            f'<span class="brief-cat">{escape(CATEGORY_LABELS.get(p["category"], p["category"]))}</span>'
            f'<span class="att-title">{escape(p["lens_title"])}</span>'
            f'<span class="badge {escape(p["status"])}">{escape(p["status"])}</span>'
            f'<span class="att-read">{escape(p["headline"])}</span></a>' for p in group)
        groups.append(f'<div class="att-group" id="{status}">'
                      f'<div class="brief-sec-label">{escape(label)}</div>{items}</div>')
    return ('<section><h2 class="sec-head">Where the pressure is</h2>'
            '<p class="sec-sub">Everything currently warranting attention, worst first.</p>'
            + "".join(groups) + "</section>")


def _categories(cats):
    links = "".join(
        f'<a class="state-steady" href="{escape(c["href"], quote=True)}">'
        f'<span class="badge {escape(c["status"])}">{escape(c["status"])}</span>'
        f'{escape(c["title"])}</a>' for c in cats)
    return ('<section><h2 class="sec-head">Across the dashboards</h2>'
            '<p class="sec-sub">Every category&rsquo;s overall read — jump into any of them.</p>'
            + links + "</section>")


def _subscribe():
    if not BUTTONDOWN_USERNAME:
        return ""
    return (
        '<section class="subscribe-band"><h2 class="sec-head">Get this in your inbox</h2>'
        '<p class="sec-sub">Free, every morning the board changes. One email, no spam, '
        "unsubscribe anytime.</p>"
        f'<form class="subscribe-form" action="https://buttondown.com/api/emails/embed-subscribe/'
        f'{BUTTONDOWN_USERNAME}" method="post">'
        '<input type="email" name="email" required placeholder="you@example.com" '
        'aria-label="Email address">'
        "<button type=\"submit\">Subscribe</button></form></section>")


def _jsonld(today, canonical, og_url):
    data = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": (today.get("verdict") or {}).get("sentence", "Today's Brief"),
        "datePublished": today.get("generated_at", ""),
        "dateModified": today.get("generated_at", ""),
        "mainEntityOfPage": canonical, "image": og_url,
        "author": {"@type": "Organization", "name": "Bailey Analytics", "url": SITE},
        "publisher": {"@type": "Organization", "name": "Bailey Analytics", "url": SITE},
    }
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False, indent=2) + "</script>")


def render_brief(today, og_image, archive_date=None, prev_date=None, next_date=None):
    """The full brief HTML document. archive_date switches on archive chrome."""
    day = archive_date or (today.get("generated_at") or "")[:10]
    label = _date_label(day)
    canonical = (f"{SITE}/dashboards/brief/{archive_date}.html" if archive_date
                 else f"{SITE}/dashboards/brief.html")
    og_url = SITE + og_image
    title = (f"Brief for {label} — Bailey Analytics" if archive_date
             else "Today's Brief — Bailey Analytics")
    desc = ((today.get("verdict") or {}).get("sentence")
            or "The daily read on the U.S. and global economy.")

    verdict = today.get("verdict") or {}
    verdict_html = ""
    if verdict.get("sentence"):
        verdict_html = (
            '<section class="state-panel" id="verdict" style="margin-top:1.25rem">'
            f'<div class="state-verdict"><span class="badge {escape(verdict["status"])}">'
            f'{escape(verdict["status"])}</span> <span class="state-sentence">'
            f'{escape(verdict["sentence"])}</span></div></section>')

    banner = ""
    if archive_date:
        banner = (f'<div class="archive-banner">This is the brief from {escape(label)} — '
                  '<a href="/dashboards/brief.html">see today&rsquo;s brief</a>.</div>')
    nav_parts = []
    if prev_date:
        nav_parts.append(f'<a href="/dashboards/brief/{prev_date}.html">&larr; {escape(_date_label(prev_date))}</a>')
    nav_parts.append('<a href="/dashboards/brief/">Archive</a>')
    if next_date:
        nav_parts.append(f'<a href="/dashboards/brief/{next_date}.html">{escape(_date_label(next_date))} &rarr;</a>')
    archive_nav = '<nav class="archive-nav">' + " · ".join(nav_parts) + "</nav>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc, quote=True)}">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(desc, quote=True)}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{og_url}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="alternate" type="application/rss+xml" title="Bailey Analytics — Today&#39;s Brief" href="/feed.xml">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  <style>
    .sec-head {{ font-size: 1.4rem; font-weight: 600; letter-spacing: -0.01em; margin: 2.25rem 0 0.3rem; scroll-margin-top: 1rem; }}
    .sec-sub {{ color: var(--muted); font-size: .92rem; max-width: 42rem; margin-bottom: 1.15rem; }}
    #verdict .state-sentence {{ font-size: 1.15rem; }}
  </style>
  {_jsonld(today, canonical, og_url)}
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/brief.html" aria-current="page">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    {banner}
    <h1>{"Today&rsquo;s Brief" if not archive_date else escape("Brief for " + label)}</h1>
    <p class="lede">The daily read on the U.S. and global economy — where things stand, what changed, and what we&rsquo;re watching next. <strong>Open anything</strong> for the full charts and context.</p>
    <div class="hub-fresh">As of {escape(label)}</div>
    {archive_nav}
    {verdict_html}
    <section><h2 class="sec-head">What changed today</h2>
    <p class="sec-sub">Status changes first — the headline events — then the biggest moves in the data, judged against each indicator&rsquo;s own typical day-to-day swing.</p>
    {_transitions(today.get("transitions") or [])}</section>
    {_movers(today.get("top_moves") or [])}
    {_watching(today.get("watching") or [])}
    {_subscribe()}
    {_pressure(today.get("pressure") or [])}
    {_categories(today.get("categories") or [])}
    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (St. Louis Fed), the <a href="https://banks.data.fdic.gov/" target="_blank" rel="noopener">FDIC</a>, the <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a>, the <a href="https://www.imf.org/en/Publications/WEO" target="_blank" rel="noopener">IMF</a>, the <a href="https://www.newyorkfed.org/research/policy/gscpi" target="_blank" rel="noopener">NY Fed</a>, <a href="https://www.policyuncertainty.com/" target="_blank" rel="noopener">policyuncertainty.com</a>, and <a href="https://www.coingecko.com/" target="_blank" rel="noopener">CoinGecko</a>. Public data, refreshed regularly.
      Get the brief in your reader: <a href="/feed.xml">RSS feed</a>.
    </div>
  </main>
</body>
</html>
"""


def render_archive_index(manifest):
    """The /dashboards/brief/ archive listing, newest first, grouped by month."""
    entries = sorted(manifest, key=lambda e: e["date"], reverse=True)
    by_month, order = {}, []
    for e in entries:
        month = _date_label(e["date"]).split(" ")[0] + " " + e["date"][:4]
        if month not in by_month:
            by_month[month] = []
            order.append(month)
        by_month[month].append(e)
    sections = []
    for month in order:
        rows = "".join(
            f'<a class="att-row" href="/dashboards/brief/{e["date"]}.html">'
            f'<span class="att-title">{escape(_date_label(e["date"]))}</span>'
            f'<span class="badge {escape(e["status"])}">{escape(e["status"])}</span>'
            f'<span class="att-read">{escape(e.get("sentence", ""))}</span></a>'
            for e in by_month[month])
        sections.append(f'<div class="att-group"><div class="brief-sec-label">'
                        f"{escape(month)}</div>{rows}</div>")
    body = "".join(sections) or '<p class="sec-sub">No archived briefs yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Brief Archive — Bailey Analytics</title>
  <meta name="description" content="Every published Today's Brief, by date — the daily plain-English read on the U.S. and global economy.">
  <link rel="canonical" href="{SITE}/dashboards/brief/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Brief Archive — Bailey Analytics">
  <meta property="og:description" content="Every published Today's Brief, by date.">
  <meta property="og:url" content="{SITE}/dashboards/brief/">
  <meta property="og:image" content="{SITE}/og/site.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
</head>
<body>
  <nav class="wordmark"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav"><a href="/dashboards/brief.html" aria-current="page">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    <div class="hub-back"><a href="/dashboards/brief.html">&larr; Today&rsquo;s Brief</a></div>
    <h1>Brief Archive</h1>
    <p class="lede">Every published brief, newest first.</p>
    {body}
  </main>
</body>
</html>
"""
```

Note on `feed` import: it's reserved for `_counts_phrase` reuse if the archive index later shows counts — if unused after writing, **remove the import** (no dead imports).

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_briefpage.py" -v`
Expected: 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/lenses/briefpage.py scripts/tests/test_briefpage.py scripts/tests/fixtures/today_sample.json
git commit -m "feat: baked brief/archive page renderer (replaces client-side brief render)"
```

---

### Task 6: Wire publication into `refresh_brief` — days store, manifest, archive, og cards, sitemap, home patch

**Files:**
- Modify: `baileyanalytics/scripts/refresh_lenses.py`
- Modify: `baileyanalytics/index.html` (markers + og:image region)
- Modify: `baileyanalytics/dashboards/lens.css` (archive + subscribe styles)
- Test: `baileyanalytics/scripts/tests/test_refresh_publish.py`

- [ ] **Step 1: Add marker regions to `index.html`.** Two one-time edits:

In the `<head>`, replace the existing line
`  <meta name="twitter:card" content="summary">` with:

```html
  <meta name="twitter:card" content="summary_large_image">
  <!-- og-image:start --><meta property="og:image" content="https://baileyanalytics.com/og/site.png"><!-- og-image:end -->
  <link rel="canonical" href="https://baileyanalytics.com/">
```

In the hero, replace the line
`            <a class="state-line" id="state-line" href="/dashboards/brief.html" hidden></a>` with:

```html
            <!-- verdict-line:start --><a class="state-line" id="state-line" href="/dashboards/brief.html" hidden></a><!-- verdict-line:end -->
```

(The pipeline will bake badge+sentence into this region so crawlers see it; `brief.js`'s `loadBrief("state-line", {mode:"line"})` still refreshes the same element client-side — its id must remain `state-line`.)

- [ ] **Step 2: Add CSS to `dashboards/lens.css`** (append at end):

```css
/* ---- Brief archive chrome (distribution phase) ---- */
.archive-banner { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: .7rem .9rem; margin: 1rem 0; font-size: .9rem; color: var(--muted); }
.archive-banner a { color: var(--blue); }
.archive-nav { font-size: .82rem; color: var(--faint); margin: .6rem 0 0; }
.archive-nav a { color: var(--muted); text-decoration: none; }
.archive-nav a:hover { color: var(--text); text-decoration: underline; }

/* ---- Email subscribe (distribution phase) ---- */
.subscribe-band { margin-top: 2.25rem; }
.subscribe-form { display: flex; gap: .5rem; max-width: 26rem; }
.subscribe-form input { flex: 1; background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; color: var(--text); padding: .6rem .8rem; font-size: .9rem; }
.subscribe-form button { background: var(--blue); color: var(--bg); border: 0; border-radius: 8px;
  padding: .6rem 1.1rem; font-size: .9rem; font-weight: 600; cursor: pointer; }
.subscribe-form button:hover { filter: brightness(1.1); }
```

(`--blue` exists in lens.css's `:root`; verify with a grep — if the variable name differs there, use the one lens.css defines, e.g. `#38BDF8` literal.)

- [ ] **Step 3: Write the failing test** for the new publication helpers (`scripts/tests/test_refresh_publish.py`). These test the pure decision pieces of the refresh wiring via a temp directory:

```python
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestManifest(unittest.TestCase):
    def test_append_and_replace_same_day(self):
        m = refresh_lenses._update_manifest([], TODAY)
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["date"], "2026-06-12")
        self.assertEqual(m[0]["status"], "watch")
        again = refresh_lenses._update_manifest(m, TODAY)
        self.assertEqual(len(again), 1)          # same-day rerun replaces, not appends

    def test_keeps_history_sorted(self):
        old = [{"date": "2026-06-11", "status": "ok", "sentence": "x"}]
        m = refresh_lenses._update_manifest(old, TODAY)
        self.assertEqual([e["date"] for e in m], ["2026-06-11", "2026-06-12"])


class TestPublishBrief(unittest.TestCase):
    def test_publish_writes_all_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "data" / "brief").mkdir(parents=True)
            (root / "dashboards").mkdir()
            (root / "index.html").write_text(
                "<head><!-- og-image:start --><meta><!-- og-image:end --></head>"
                "<body><!-- verdict-line:start --><a><!-- verdict-line:end --></body>",
                encoding="utf-8")
            refresh_lenses._publish_brief(TODAY, root=root)
            day = "2026-06-12"
            self.assertTrue((root / "dashboards" / "brief.html").exists())
            self.assertTrue((root / "dashboards" / "brief" / f"{day}.html").exists())
            self.assertTrue((root / "dashboards" / "brief" / "index.html").exists())
            self.assertTrue((root / "og" / f"brief-{day}.png").exists())
            self.assertTrue((root / "og" / "site.png").exists())
            self.assertTrue((root / "data" / "brief" / "days" / f"{day}.json").exists())
            self.assertTrue((root / "sitemap.xml").exists())
            home = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn(f"og/brief-{day}.png", home)
            self.assertIn("Most of the economy", home)

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "data" / "brief").mkdir(parents=True)
            (root / "dashboards").mkdir()
            (root / "index.html").write_text(
                "<!-- og-image:start --><m><!-- og-image:end -->"
                "<!-- verdict-line:start --><a><!-- verdict-line:end -->", encoding="utf-8")
            refresh_lenses._publish_brief(TODAY, root=root)
            first = (root / "dashboards" / "brief.html").read_bytes()
            refresh_lenses._publish_brief(TODAY, root=root)
            manifest = json.loads((root / "data" / "brief" / "_archive_index.json")
                                  .read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 1)
            self.assertEqual((root / "dashboards" / "brief.html").read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_refresh_publish.py" -v`
Expected: FAIL — `module 'refresh_lenses' has no attribute '_update_manifest'`.

- [ ] **Step 5: Implement in `refresh_lenses.py`.**

5a. Extend the imports line:
```python
from lenses import brief, briefpage, build, coingecko, config, eia, epu, fdic, feed, fred, imf, nyfed, ogcard, regions, sitemap, staticread, today, util, yahoo
```
(`staticread` lands in Task 9 — until then import without it: add it in Task 9. For this task use the list WITHOUT `staticread`.)

5b. Add path constants near the others:
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BRIEF_OUT_DIR / "_archive_index.json"
```

5c. Add the helpers (place after `refresh_brief`):

```python
def _write_text_if_changed(path, text):
    """Content-aware text write (HTML/XML twin of build.write_lens_file)."""
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == text:
                return False
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _update_manifest(manifest, today_json):
    """Append/replace today's entry; sorted by date ascending."""
    day = (today_json.get("generated_at") or "")[:10]
    verdict = today_json.get("verdict") or {}
    entry = {"date": day, "status": verdict.get("status", "unknown"),
             "sentence": verdict.get("sentence", "")}
    out = [e for e in manifest if e.get("date") != day] + [entry]
    out.sort(key=lambda e: e["date"])
    return out


def _patch_region_file(path, name, content):
    """replace_region applied to a file; safe no-op when markers are missing."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    new, changed = regions.replace_region(text, name, content)
    if changed:
        path.write_text(new, encoding="utf-8")


def _publish_brief(today_json, root=REPO_ROOT):
    """Bake every publication surface for today's brief: dated JSON + archive
    page + og card, the live brief.html, the archive index, the home-page
    verdict/og patches, and the sitemap. Idempotent (content-aware writes), so
    the backup cron and local reruns are free. og-card failure degrades to the
    static site card; nothing here may raise (the caller guards anyway)."""
    from html import escape

    day = (today_json.get("generated_at") or "")[:10]
    brief_dir = root / "data" / "brief"
    pages_dir = root / "dashboards" / "brief"
    og_dir = root / "og"

    # 1. dated JSON (the day's API record; lets us re-render yesterday's page)
    days_dir = brief_dir / "days"
    days_dir.mkdir(parents=True, exist_ok=True)
    build.write_lens_file(days_dir / f"{day}.json", today_json)

    # 2. manifest
    try:
        manifest = json.loads((brief_dir / "_archive_index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = []
    manifest = _update_manifest(manifest, today_json)
    (brief_dir / "_archive_index.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    dates = [e["date"] for e in manifest]

    # 3. og cards (site card once; daily card per publication day)
    og_dir.mkdir(exist_ok=True)
    if not (og_dir / "site.png").exists():
        (og_dir / "site.png").write_bytes(ogcard.render_site_card())
    og_image = "/og/site.png"
    try:
        verdict = today_json.get("verdict") or {}
        card = ogcard.render_card(verdict.get("status", "unknown"),
                                  verdict.get("sentence", ""),
                                  briefpage._date_label(day))
        (og_dir / f"brief-{day}.png").write_bytes(card)
        og_image = f"/og/brief-{day}.png"
    except Exception as exc:  # noqa: BLE001 - card is additive
        print(f"WARN: og card failed ({exc}); using site card", file=sys.stderr)

    # 4. today's pages: live brief.html + dated archive page
    idx = dates.index(day)
    prev_date = dates[idx - 1] if idx > 0 else None
    _write_text_if_changed(root / "dashboards" / "brief.html",
                           briefpage.render_brief(today_json, og_image=og_image))
    pages_dir.mkdir(exist_ok=True)
    _write_text_if_changed(pages_dir / f"{day}.html",
                           briefpage.render_brief(today_json, og_image=og_image,
                                                  archive_date=day, prev_date=prev_date))

    # 5. re-render yesterday's archive page with its new next-link
    if prev_date:
        prior_json_path = days_dir / f"{prev_date}.json"
        if prior_json_path.exists():
            try:
                prior = json.loads(prior_json_path.read_text(encoding="utf-8"))
                prev_prev = dates[idx - 2] if idx > 1 else None
                prior_og = (f"/og/brief-{prev_date}.png"
                            if (og_dir / f"brief-{prev_date}.png").exists() else "/og/site.png")
                _write_text_if_changed(
                    pages_dir / f"{prev_date}.html",
                    briefpage.render_brief(prior, og_image=prior_og, archive_date=prev_date,
                                           prev_date=prev_prev, next_date=day))
            except (OSError, ValueError) as exc:
                print(f"WARN: prior archive re-render failed ({exc})", file=sys.stderr)

    # 6. archive index + sitemap
    _write_text_if_changed(pages_dir / "index.html", briefpage.render_archive_index(manifest))
    _write_text_if_changed(root / "sitemap.xml",
                           sitemap.render_sitemap(sitemap.build_urls(dates)) + "\n")

    # 7. home-page patches: baked verdict line + dated og image
    verdict = today_json.get("verdict") or {}
    if verdict.get("sentence"):
        line = (f'<a class="state-line" id="state-line" href="/dashboards/brief.html">'
                f'<span class="pill {escape(verdict["status"])}">{escape(verdict["status"])}</span>'
                f'<span class="state-sentence">{escape(verdict["sentence"])}</span></a>')
        _patch_region_file(root / "index.html", "verdict-line", line)
    _patch_region_file(root / "index.html", "og-image",
                       f'<meta property="og:image" content="https://baileyanalytics.com{og_image}">')
```

5d. Call it from `refresh_brief` — inside the existing `if wrote:` block, after the feed block:

```python
        if wrote:
            try:
                ... existing feed code ...
            except Exception as exc:  # noqa: BLE001 - feed is additive
                ...
            # Publication surfaces: baked pages, og cards, sitemap, home patch.
            # Guarded separately — a bake hiccup must not read as a brief failure.
            try:
                _publish_brief(today_json)
            except Exception as exc:  # noqa: BLE001 - publication is additive
                print(f"WARN: brief publication failed ({exc}); keeping previous pages",
                      file=sys.stderr)
```

- [ ] **Step 6: Run the new test + full suite**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_*.py"`
Expected: all pass (~285+).

- [ ] **Step 7: First live bake.** Run `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/refresh_lenses.py" --brief`. **Gotcha:** if the committed `today.json` content is unchanged, `wrote` is False and nothing bakes. Force the first bake by deleting the output first: delete `data/brief/today.json` (`git status` will show it restored after the run), then run `--brief`. Verify: `dashboards/brief.html` is now the baked version (open it — no `fetch(`), `dashboards/brief/<today>.html` + `index.html` exist, `og/brief-<today>.png` + `og/site.png` exist, `sitemap.xml` exists, home `index.html` regions show the baked verdict + dated og image. Serve locally (`python -m http.server 8000` from the repo dir) and eyeball `/dashboards/brief.html` and the archive page against production's look.

- [ ] **Step 8: Commit** (the baked artifacts are part of the change — they're what deploys):

```bash
git add scripts/refresh_lenses.py scripts/tests/test_refresh_publish.py index.html dashboards/lens.css dashboards/brief.html dashboards/brief/ og/ sitemap.xml data/brief/
git commit -m "feat: bake brief + archive permalinks + og cards + sitemap + home patches on publication days"
```

---

### Task 7: Replace brief.html's client render — verify nothing else depended on it

The baked `dashboards/brief.html` from Task 6 already replaced the inline script. This task is verification + cleanup.

- [ ] **Step 1:** Grep for stragglers: `renderBriefTransitions` and `briefCategoryLabel` live in `dashboards/brief.js` and were consumed by the old inline script. Check `brief.js`'s remaining consumers: `index.html` (counts strip + hero line). If `renderBriefTransitions` or the `fullPanel`-era helpers are now dead code in `brief.js` (nothing else references them — grep `dashboards/` for each function name), delete those functions from `brief.js`, keeping `loadBrief` (compact strip + line modes) and whatever it calls.
- [ ] **Step 2:** Confirm `dashboards/state.html` (redirect stub) and `dashboards/economic.html` (redirect) are untouched and still redirect.
- [ ] **Step 3:** Serve locally and verify the home page still renders its strip + hero line (open browser console — no errors), and `/dashboards/brief.html` deep links `#alert` / `#elevated` scroll correctly (they're plain anchors now).
- [ ] **Step 4:** Run full test suite; commit:

```bash
git add dashboards/brief.js
git commit -m "chore: drop brief.js render paths orphaned by the baked brief page"
```

---

### Task 8: `digest.py` — the email renderer

**Files:**
- Create: `baileyanalytics/scripts/lenses/digest.py`
- Test: `baileyanalytics/scripts/tests/test_digest.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import digest

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestSubject(unittest.TestCase):
    def test_transition_led_subject(self):
        sub = digest.build_digest(TODAY)["subject"]
        self.assertEqual(
            sub, "Electricity & the Grid tips to ELEVATED — Today's Brief, Jun 12, 2026")

    def test_improving_transition_wording(self):
        t = dict(TODAY)
        t["transitions"] = [dict(TODAY["transitions"][0],
                                 direction="improving", from_status="elevated",
                                 to_status="watch")]
        self.assertIn("improves to WATCH", digest.build_digest(t)["subject"])

    def test_counts_subject_when_no_transitions(self):
        quiet = dict(TODAY, transitions=[])
        sub = digest.build_digest(quiet)["subject"]
        self.assertEqual(sub, "Today's Brief — 3 alert · 8 elevated · 3 on watch, Jun 12, 2026")

    def test_date_token_always_present(self):
        self.assertIn("Jun 12, 2026", digest.build_digest(TODAY)["subject"])
        self.assertEqual(digest.date_token("2026-06-12"), "Jun 12, 2026")


class TestBody(unittest.TestCase):
    def setUp(self):
        self.html = digest.build_digest(TODAY)["html"]

    def test_verdict_and_sections_present(self):
        self.assertIn("Most of the economy is on solid footing", self.html)
        self.assertIn("WATCH", self.html)
        self.assertIn("Electricity &amp; the Grid", self.html)
        self.assertIn("18.97¢/kWh", self.html)

    def test_links_are_absolute_and_permalink_present(self):
        self.assertIn("https://baileyanalytics.com/dashboards/brief/2026-06-12.html", self.html)
        self.assertNotIn('href="/dashboards', self.html)

    def test_unsubscribe_variable_present(self):
        self.assertIn("{{ unsubscribe_url }}", self.html)

    def test_movers_capped_at_five(self):
        t = dict(TODAY, transitions=[],
                 top_moves=[dict(TODAY["top_moves"][0], lens_title=f"Lens {i}")
                            for i in range(8)])
        html = digest.build_digest(t)["html"]
        self.assertIn("Lens 4", html)
        self.assertNotIn("Lens 5", html)

    def test_pressure_count_line(self):
        self.assertIn("14 readings warrant attention", self.html)  # 3+8+3 from status_counts


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_digest.py" -v`
Expected: FAIL — `cannot import name 'digest'`.

- [ ] **Step 3: Write the implementation**

```python
"""The daily email: today.json -> {subject, html}. Pure. Email-safe HTML —
single-column table, inline styles, light theme (the dark site palette is
unreliable across email clients). Text-first: no images, so it loads fast and
keeps spam scores clean. The {{ unsubscribe_url }} placeholder is substituted
by Buttondown at send time."""

from datetime import datetime
from html import escape

from . import feed

SITE = "https://baileyanalytics.com"

BADGE = {"ok": "#059669", "watch": "#B45309", "elevated": "#C2410C",
         "alert": "#DC2626", "neutral": "#0284C7"}
INK = "#111827"
MUTED = "#6B7280"
RULE = "#E5E7EB"
FONT = ("font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "Helvetica,Arial,sans-serif;")

MOVES_CAP = 5


def date_token(iso_date):
    """'Jun 12, 2026' — used in the subject and as the idempotency key."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def _badge(status):
    color = BADGE.get(status, MUTED)
    return (f'<span style="color:{color};border:1px solid {color};border-radius:999px;'
            f'padding:1px 9px;font-size:11px;font-weight:700;letter-spacing:.05em;">'
            f"{escape(status.upper())}</span>")


def _subject(today, token):
    transitions = today.get("transitions") or []
    if transitions:
        t = transitions[0]
        verb = "tips to" if t.get("direction") == "worsening" else "improves to"
        return (f"{t['lens_title']} {verb} {t['to_status'].upper()} "
                f"— Today's Brief, {token}")
    counts = feed._counts_phrase(today.get("status_counts", {}))
    return f"Today's Brief — {counts}, {token}"


def _row(title_html, body_html):
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid {RULE};">'
            f'<div style="{FONT}font-size:13px;color:{INK};font-weight:700;">{title_html}</div>'
            f'<div style="{FONT}font-size:13px;color:{MUTED};margin-top:2px;">{body_html}</div>'
            "</td></tr>")


def _changed_rows(today):
    rows = []
    for t in today.get("transitions") or []:
        rows.append(_row(
            f'<a href="{SITE}{t["href"]}" style="color:{INK};">{escape(t["lens_title"])}</a> '
            f'{_badge(t["from_status"])} &rarr; {_badge(t["to_status"])}',
            escape(t.get("headline", ""))))
    for m in (today.get("top_moves") or [])[:MOVES_CAP]:
        arrow = "&#9660;" if m.get("dir") == "down" else "&#9650;"
        delta = f" {arrow}{escape(m['delta'])}" if m.get("delta") else ""
        rows.append(_row(
            f'<a href="{SITE}{m["href"]}" style="color:{INK};">{escape(m["lens_title"])}</a> '
            f'&middot; {escape(m.get("stat_label", ""))} '
            f'<strong>{escape(m.get("stat_value", ""))}</strong>{delta}',
            escape(m.get("headline", ""))))
    if not rows:
        rows.append(_row("A quiet day on the board", "No status changes or outsized moves."))
    return "".join(rows)


def _watching_rows(today):
    rows = []
    for x in (today.get("watching") or [])[:3]:
        if x.get("change"):
            claim = (f"we expect <strong>{escape(x['point_fmt'])}</strong> — which would tip "
                     f"{escape(x['lens_title'])} to {_badge(x['implied_status'])}")
        else:
            claim = f"we expect <strong>{escape(x['point_fmt'])}</strong>, no status change"
        rows.append(_row(escape(x.get("title", "")), claim))
    return "".join(rows)


def _section(label):
    return (f'<tr><td style="padding:22px 0 4px;{FONT}font-size:11px;font-weight:700;'
            f'letter-spacing:.08em;color:{MUTED};text-transform:uppercase;">{label}</td></tr>')


def build_digest(today):
    day = (today.get("generated_at") or "")[:10]
    token = date_token(day)
    verdict = today.get("verdict") or {}
    counts = today.get("status_counts", {})
    attention = counts.get("watch", 0) + counts.get("elevated", 0) + counts.get("alert", 0)
    permalink = f"{SITE}/dashboards/brief/{day}.html"

    watching = _watching_rows(today)
    watching_block = (_section("What we&rsquo;re watching next") + watching) if watching else ""

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F9FAFB;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid {RULE};border-radius:10px;padding:28px 28px 20px;">
<tr><td style="{FONT}font-size:13px;font-weight:700;letter-spacing:.1em;color:{INK};">BAILEY ANALYTICS</td></tr>
<tr><td style="{FONT}font-size:12px;color:{MUTED};padding-top:2px;">Today&rsquo;s Brief &middot; {escape(token)}</td></tr>
<tr><td style="padding:18px 0 6px;">{_badge(verdict.get("status", "unknown"))}</td></tr>
<tr><td style="{FONT}font-size:17px;line-height:1.5;color:{INK};font-weight:600;">{escape(verdict.get("sentence", ""))}</td></tr>
{_section("What changed today")}
{_changed_rows(today)}
{watching_block}
<tr><td style="padding:22px 0 0;{FONT}font-size:13px;color:{MUTED};">
{attention} readings warrant attention right now &mdash;
<a href="{permalink}#alert" style="color:{INK};">see where the pressure is</a>.
</td></tr>
<tr><td style="padding:18px 0 0;{FONT}font-size:13px;">
<a href="{permalink}" style="color:{INK};font-weight:600;">View this brief on the site &rarr;</a>
</td></tr>
<tr><td style="padding:26px 0 0;{FONT}font-size:11px;color:{MUTED};line-height:1.6;border-top:1px solid {RULE};margin-top:18px;">
Built from public data &mdash; FRED, the FDIC, the U.S. EIA, the IMF, the NY Fed, and more. Not investment advice.<br>
You&rsquo;re getting this because you subscribed at baileyanalytics.com.
<a href="{{{{ unsubscribe_url }}}}" style="color:{MUTED};">Unsubscribe</a>
</td></tr>
</table></td></tr></table>
</body></html>"""
    return {"subject": _subject(today, token), "html": html}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_digest.py" -v`
Expected: 10 tests PASS. (If the pressure-count assertion fails, the fixture's `status_counts` is 3+8+3=14 — keep test and fixture consistent.)

- [ ] **Step 5: Commit**

```bash
git add scripts/lenses/digest.py scripts/tests/test_digest.py
git commit -m "feat: daily email digest renderer (light-theme, email-safe HTML)"
```

---

### Task 9: `send_digest.py` — Buttondown sender + workflow wiring

**Files:**
- Create: `baileyanalytics/scripts/send_digest.py`
- Test: `baileyanalytics/scripts/tests/test_send_digest.py`
- Modify: `baileyanalytics/.github/workflows/refresh-fred.yml`

- [ ] **Step 1: Write the failing test** (pure decision helpers only; network mocked):

```python
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import send_digest

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestShouldSend(unittest.TestCase):
    def test_sends_on_publication_day(self):
        manifest = [{"date": "2026-06-12", "status": "watch", "sentence": "x"}]
        self.assertTrue(send_digest.should_send(manifest, "2026-06-12"))

    def test_skips_quiet_day(self):
        manifest = [{"date": "2026-06-11", "status": "watch", "sentence": "x"}]
        self.assertFalse(send_digest.should_send(manifest, "2026-06-12"))

    def test_skips_empty_manifest(self):
        self.assertFalse(send_digest.should_send([], "2026-06-12"))


class TestAlreadySent(unittest.TestCase):
    def test_detects_existing_email_by_date_token(self):
        emails = {"results": [{"subject": "Today's Brief — 3 alert, Jun 12, 2026"}]}
        self.assertTrue(send_digest.already_sent(emails, "Jun 12, 2026"))

    def test_different_day_not_sent(self):
        emails = {"results": [{"subject": "Today's Brief — calm, Jun 11, 2026"}]}
        self.assertFalse(send_digest.already_sent(emails, "Jun 12, 2026"))

    def test_handles_missing_results(self):
        self.assertFalse(send_digest.already_sent({}, "Jun 12, 2026"))


class TestPublishAt(unittest.TestCase):
    def test_before_11_utc_schedules_for_11(self):
        self.assertEqual(send_digest.publish_at("2026-06-12", "2026-06-12T06:05:00Z"),
                         "2026-06-12T11:00:00Z")

    def test_after_11_utc_sends_now(self):
        self.assertEqual(send_digest.publish_at("2026-06-12", "2026-06-12T13:02:00Z"),
                         "2026-06-12T13:02:00Z")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_send_digest.py" -v`
Expected: FAIL — `No module named 'send_digest'`.

- [ ] **Step 3: Write the implementation** (`scripts/send_digest.py`):

```python
#!/usr/bin/env python3
"""Send Today's Brief as an email via the Buttondown API.

Runs as a workflow step after the --brief pass. Decision chain (each exit is
quiet and exit-code 0 except a real API failure, which exits 1 so the step
shows red):
  1. no BUTTONDOWN_API_KEY            -> skip (forks, local runs)
  2. today isn't a publication day    -> skip (quiet day; manifest has no entry)
  3. Buttondown already has today's   -> skip (backup cron / rerun)
  4. POST the digest, scheduled for max(now, 11:00 UTC)  (~7am ET)

Usage: python scripts/send_digest.py [--dry-run]
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lenses import digest

API = "https://api.buttondown.com/v1/emails"
BRIEF_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"


def should_send(manifest, day):
    """Publication-day gate: the --brief pass appended today to the manifest
    iff the brief's content changed today."""
    return any(e.get("date") == day for e in manifest or [])


def already_sent(emails_json, token):
    """True if any recent Buttondown email's subject carries today's date token
    (every digest subject ends with it — see digest.date_token)."""
    return any(token in (e.get("subject") or "")
               for e in (emails_json or {}).get("results", []))


def publish_at(day, now_iso):
    """Schedule for 11:00 UTC (~7am ET); if we're already past it (the 13:00
    backup cron catching up), send immediately."""
    target = f"{day}T11:00:00Z"
    return now_iso if now_iso > target else target


def _request(url, api_key, payload=None):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Token {api_key}",
                      "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8") if payload else None,
        method="POST" if payload else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv=None):
    dry_run = "--dry-run" in (argv or sys.argv[1:])

    today = json.loads((BRIEF_DIR / "today.json").read_text(encoding="utf-8"))
    day = (today.get("generated_at") or "")[:10]
    built = digest.build_digest(today)

    if dry_run:
        print("SUBJECT:", built["subject"])
        print(built["html"])
        return 0

    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("BUTTONDOWN_API_KEY not set — skipping digest send.")
        return 0

    try:
        manifest = json.loads((BRIEF_DIR / "_archive_index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = []
    if not should_send(manifest, day):
        print(f"No publication entry for {day} — quiet day, no email.")
        return 0

    token = digest.date_token(day)
    try:
        if already_sent(_request(API, api_key), token):
            print(f"Digest for {token} already exists on Buttondown — skipping.")
            return 0
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {"subject": built["subject"], "body": built["html"],
                   "status": "scheduled", "publish_date": publish_at(day, now_iso)}
        created = _request(API, api_key, payload)
        print(f"Digest scheduled: {created.get('id', '?')} — {built['subject']}")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"ERROR: Buttondown API {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}",
              file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: digest send failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest discover -s "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tests" -p "test_send_digest.py" -v`
Expected: 8 tests PASS. Also run `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/send_digest.py" --dry-run` — prints subject + HTML from the repo's current `today.json`.

- [ ] **Step 5: Wire the workflow.** In `.github/workflows/refresh-fred.yml`, insert between the "Rebuild Today's Brief" step and the commit step:

```yaml
      - name: Send the daily email digest (Buttondown)
        if: ${{ success() || failure() }}
        env:
          BUTTONDOWN_API_KEY: ${{ secrets.BUTTONDOWN_API_KEY }}
        run: python scripts/send_digest.py
```

And update the commit step's globs (both the `git status --porcelain` check and the `git add`):

```yaml
          if [[ -n "$(git status --porcelain data/ feed.xml sitemap.xml og/ dashboards/ index.html)" ]]; then
            git add data/ feed.xml sitemap.xml og/ dashboards/ index.html
```

- [ ] **Step 6: Commit**

```bash
git add scripts/send_digest.py scripts/tests/test_send_digest.py .github/workflows/refresh-fred.yml
git commit -m "feat: Buttondown digest sender + workflow step (scheduled ~7am ET, idempotent)"
```

---

### Task 10: SEO statics — `seo_heads.py` tool, robots.txt, 404, repo links, home JSON-LD, subscribe forms

**Files:**
- Create: `baileyanalytics/scripts/tools/seo_heads.py`
- Create: `baileyanalytics/robots.txt`, `baileyanalytics/404.html`
- Modify: `baileyanalytics/about.html`, `baileyanalytics/dashboards/track-record.html`, `baileyanalytics/index.html`, all lens/hub pages (via the tool)

- [ ] **Step 1: Create `robots.txt`** (repo root):

```
User-agent: *
Allow: /

Sitemap: https://baileyanalytics.com/sitemap.xml
```

- [ ] **Step 2: Create `404.html`** (repo root; standalone inline CSS like home/about — GitHub Pages serves it automatically):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page not found — Bailey Analytics</title>
  <meta name="robots" content="noindex">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <style>
    body { background:#0A0E14; color:#F8FAFC; font-family:-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",Roboto,sans-serif;
      min-height:100vh; display:flex; align-items:center; justify-content:center; margin:0; padding:1.5rem; text-align:center; }
    h1 { font-size:2rem; font-weight:600; margin:0 0 .5rem; }
    p { color:#94A3B8; margin:0 0 1.5rem; }
    a { color:#38BDF8; text-decoration:none; margin:0 .6rem; }
    a:hover { text-decoration:underline; }
  </style>
</head>
<body>
  <main>
    <h1>That page isn&rsquo;t on the board.</h1>
    <p>The address may have changed — everything live is reachable from these:</p>
    <nav><a href="/dashboards/brief.html">Today&rsquo;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/">Home</a></nav>
  </main>
</body>
</html>
```

- [ ] **Step 3: Write the one-time idempotent head tool** (`scripts/tools/seo_heads.py`). It derives each page's canonical from its existing `og:url` meta, upgrades the twitter card, and adds og:image + canonical. It skips `brief.html` (baked) and any page already carrying `rel="canonical"`:

```python
#!/usr/bin/env python3
"""One-time, idempotent SEO head pass over the hand-written pages: canonical
(from each page's existing og:url), og:image (static site card), and
twitter:card upgraded to summary_large_image. Skips dashboards/brief.html
(baked by the pipeline) and anything already done. Rerunnable anytime."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SKIP = {ROOT / "dashboards" / "brief.html", ROOT / "404.html",
        ROOT / "index.html"}  # home was done by hand (dated og-image region)

OG_IMAGE = '  <meta property="og:image" content="https://baileyanalytics.com/og/site.png">'


def process(path):
    text = path.read_text(encoding="utf-8")
    if 'rel="canonical"' in text:
        return False
    m = re.search(r'<meta property="og:url" content="([^"]+)"\s*/?>', text)
    if not m:
        print(f"SKIP (no og:url): {path}")
        return False
    canonical = m.group(1)
    text = text.replace('<meta name="twitter:card" content="summary">',
                        '<meta name="twitter:card" content="summary_large_image">')
    insert = f'{OG_IMAGE}\n  <link rel="canonical" href="{canonical}">'
    text = re.sub(r'(<meta name="twitter:card"[^>]*>)', r"\1\n" + insert, text, count=1)
    path.write_text(text, encoding="utf-8")
    return True


def main():
    pages = [p for p in ROOT.rglob("*.html")
             if ".git" not in p.parts and "docs" not in p.parts
             and "brief" != p.parent.name  # skip baked archive pages
             and p not in SKIP]
    changed = [p for p in sorted(pages) if process(p)]
    print(f"Patched {len(changed)} pages.")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tool**: `python "C:/Users/jmich/Documents/Business/Repositories/baileyanalytics/scripts/tools/seo_heads.py"`. Expected: "Patched ~43 pages" (33 lenses + 8 hubs + dashboards hub + about + track-record, minus any without og:url — investigate each SKIP it prints; `state.html`/`economic.html` redirect stubs without og:url are fine to leave). Rerun → "Patched 0 pages" (idempotence proof). Spot-check `dashboards/recession-watch.html` and a hub by eye.

- [ ] **Step 5: Home JSON-LD** — add to `index.html` `<head>` after the canonical line:

```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Bailey Analytics",
    "url": "https://baileyanalytics.com/",
    "description": "Daily, plain-English dashboards on the U.S. and global economy, built from public data.",
    "publisher": {"@type": "Organization", "name": "Bailey Analytics", "url": "https://baileyanalytics.com/", "email": "michael@baileyanalytics.com"}
  }
  </script>
```

- [ ] **Step 6: Repo links.** In `dashboards/track-record.html`, replace the foot line
`The full ledger lives in this site&rsquo;s repository under <code>data/predictions/</code>.` with:

```html
      The full ledger lives in <a href="https://github.com/jmichaelbailey4-prog/baileyanalytics" target="_blank" rel="noopener">this site&rsquo;s public repository</a> under <code><a href="https://github.com/jmichaelbailey4-prog/baileyanalytics/tree/main/data/predictions" target="_blank" rel="noopener">data/predictions/</a></code>.
```

In `about.html`, find the paragraph about data/methodology (the "The data comes straight from primary public sources" paragraph) and append one sentence inside it:

```html
 The site is <a href="https://github.com/jmichaelbailey4-prog/baileyanalytics" target="_blank" rel="noopener">built in the open</a> — every pipeline, rule set, and prediction is public.
```

- [ ] **Step 7: Subscribe forms (home + about).** The brief's form is baked (Task 5). Home — insert directly after the `.cta-wrap` div in `index.html`:

```html
            <div class="sub-band">
                <div class="sub-copy">Get Today&rsquo;s Brief in your inbox — free, every morning the board changes.</div>
                <form class="sub-form" action="https://buttondown.com/api/emails/embed-subscribe/baileyanalytics" method="post">
                    <input type="email" name="email" required placeholder="you@example.com" aria-label="Email address">
                    <button type="submit">Subscribe</button>
                </form>
            </div>
```

And add to home's inline `<style>` (home does NOT load lens.css — per CLAUDE.md every shared-chrome change is duplicated):

```css
        .sub-band { margin-top: 2rem; text-align: center; }
        .sub-copy { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.7rem; }
        .sub-form { display: flex; gap: 0.5rem; max-width: 26rem; margin: 0 auto; }
        .sub-form input { flex: 1; background: var(--panel); border: 1px solid var(--border);
            border-radius: 8px; color: var(--text); padding: 0.6rem 0.8rem; font-size: 0.9rem; }
        .sub-form button { background: var(--blue); color: var(--bg); border: 0; border-radius: 8px;
            padding: 0.6rem 1.1rem; font-size: 0.9rem; font-weight: 600; cursor: pointer; }
```

About (`about.html` — also standalone inline CSS): add the same form + styles in the "Get in touch" section, with copy "Or get the daily brief by email:". Match about.html's existing CSS variable names (open the file and reuse its tokens).

- [ ] **Step 8: Verify + commit.** Serve locally; check home, about, a lens page, track-record render correctly; run the full test suite (no Python changes, but cheap).

```bash
git add robots.txt 404.html scripts/tools/seo_heads.py index.html about.html dashboards/
git commit -m "feat: SEO statics — canonical/og:image/JSON-LD heads, robots, 404, repo links, subscribe forms"
```

---

### Task 11: `staticread.py` — lens static reads + markers + pipeline hook

**Files:**
- Create: `baileyanalytics/scripts/lenses/staticread.py`
- Create: `baileyanalytics/scripts/tools/add_baked_read_markers.py`
- Modify: `baileyanalytics/scripts/refresh_lenses.py` (hook into the brief pass)
- Test: `baileyanalytics/scripts/tests/test_staticread.py`

- [ ] **Step 1: Write the failing test**

```python
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import staticread

LENS = {
    "id": "recession-watch", "title": "Recession Watch", "status": "ok",
    "headline_read": "The economy looks steady — no major recession signals right now.",
    "last_updated": "2026-06-12T06:01:00Z",
    "indicators": [
        {"id": "yield-curve", "title": "Yield Curve · 10-Year minus 2-Year",
         "short": "Yield curve", "unit": "%", "value_format": "decimal",
         "latest": {"date": "2026-06-11", "value": "0.40"},
         "read": "The gap between 10-year and 2-year Treasury yields is positive."},
        {"id": "payrolls", "title": "Payrolls", "short": "Payrolls", "unit": "",
         "value_format": "thousands", "latest": {"date": "2026-05-01", "value": "172000"},
         "read": "Hiring is holding up."},
        {"id": "broken", "title": "No Data", "short": "n/a", "unit": "%",
         "value_format": "decimal", "latest": None, "read": "No data yet."},
    ],
}


class TestRenderFragment(unittest.TestCase):
    def setUp(self):
        self.html = staticread.render_fragment(LENS)

    def test_wraps_in_baked_read_section(self):
        self.assertTrue(self.html.startswith('<section id="baked-read">'))
        self.assertTrue(self.html.endswith("</section>"))

    def test_headline_and_reads_present_escaped(self):
        self.assertIn("The economy looks steady", self.html)
        self.assertIn("Yield Curve · 10-Year minus 2-Year", self.html)
        self.assertIn("positive", self.html)

    def test_values_formatted_like_fmtval(self):
        self.assertIn("0.40%", self.html)        # decimal + % stays tight
        self.assertIn("172,000", self.html)      # thousands format

    def test_missing_latest_renders_dash(self):
        self.assertIn("—", self.html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**, then **Step 3: implement**:

```python
"""Static lens reads for crawlers and no-JS readers: a lens JSON -> a plain
HTML fragment (headline read + each indicator's latest value and read). The
pipeline patches it into each lens page's `baked-read` marker region; lens.js
replaces #lens-root's innerHTML wholesale on render, so the interactive view
needs no change. Pure. Formatting reuses build._fmt so the static text always
matches what the charts show."""

from html import escape

from . import build


def render_fragment(lens_json):
    parts = [f'<section id="baked-read">',
             f"<h2>{escape(lens_json.get('headline_read', ''))}</h2>"]
    for ind in lens_json.get("indicators", []):
        latest = ind.get("latest")
        value = (build._fmt(latest["value"], ind.get("unit", ""),
                            ind.get("value_format", "decimal"))
                 if latest else "—")
        parts.append(
            f"<h3>{escape(ind.get('title', ''))}</h3>"
            f"<p><strong>{escape(ind.get('short', ''))}: {escape(value)}</strong>"
            f" — {escape(ind.get('read', ''))}</p>")
    parts.append("</section>")
    return "".join(parts)
```

- [ ] **Step 4: Tests pass**, commit module + test:
```bash
git add scripts/lenses/staticread.py scripts/tests/test_staticread.py
git commit -m "feat: static lens-read fragment renderer"
```

- [ ] **Step 5: One-time marker insertion tool** (`scripts/tools/add_baked_read_markers.py`) — wraps every lens page's `#lens-root` placeholder in the marker region:

```python
#!/usr/bin/env python3
"""One-time, idempotent: wrap each lens page's loading placeholder in the
baked-read marker region the pipeline patches. Lens pages share one uniform
shell, so this is a literal string swap."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OLD = ('<main id="lens-root"><div class="status-msg"><span class="js-only">Loading&hellip;</span>'
       "<noscript>The interactive dashboards require JavaScript.</noscript></div></main>")
NEW = ('<main id="lens-root"><!-- baked-read:start --><div class="status-msg">'
       '<span class="js-only">Loading&hellip;</span><noscript>The interactive dashboards '
       "require JavaScript.</noscript></div><!-- baked-read:end --></main>")


def main():
    changed = 0
    for path in sorted(ROOT.glob("dashboards/**/*.html")):
        text = path.read_text(encoding="utf-8")
        if "baked-read:start" in text or OLD not in text:
            continue
        path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
        changed += 1
        print(f"marked: {path.relative_to(ROOT)}")
    print(f"{changed} pages marked.")


if __name__ == "__main__":
    main()
```

Run it. Expected: exactly **33** pages marked (every lens page; hubs/brief/track-record don't match the shell string). If fewer, diff a non-matching lens page against the `OLD` string — whitespace variants must be handled by adjusting OLD per the actual shell (verify against `dashboards/recession-watch.html` line 22 first).

- [ ] **Step 6: Pipeline hook.** In `refresh_lenses.py`: add `staticread` to the `from lenses import ...` line, then add:

```python
def _patch_lens_pages(root=REPO_ROOT):
    """Patch every lens page's baked-read region from its committed lens JSON.
    Runs in the --brief pass (after all category passes), so one hook covers
    all categories; content-aware, so quiet lenses produce no diff."""
    for category, out_dir in _brief_index_dirs().items():
        for lens_file in sorted(out_dir.glob("*.json")):
            if lens_file.name.startswith("_") or lens_file.name == "index.json":
                continue
            try:
                lens_json = json.loads(lens_file.read_text(encoding="utf-8"))
                href = brief.lens_href(category, lens_json.get("id", ""))
                page = root / href.lstrip("/")
                if page.exists():
                    _patch_region_file(page, "baked-read",
                                       staticread.render_fragment(lens_json))
            except (ValueError, OSError) as exc:
                print(f"WARN: static read failed for {lens_file.name}: {exc}",
                      file=sys.stderr)
```

Call it at the end of `refresh_brief` (outside the `if wrote:` block — lens data can change on days the *brief* digest doesn't, and the patch is content-aware so it's free):

```python
        try:
            _patch_lens_pages()
        except Exception as exc:  # noqa: BLE001 - static reads are additive
            print(f"WARN: lens static reads failed ({exc})", file=sys.stderr)
```

(Place this inside `refresh_brief`'s outer `try`, right before the final `except`.)

- [ ] **Step 7: Run it live**: `python .../refresh_lenses.py --brief` → every lens page's region now carries its fragment. Open `dashboards/recession-watch.html` raw: headline + reads present between markers. Serve locally and confirm the page still renders charts identically (JS wipes the block), and with JS disabled (DevTools) the baked read shows.
- [ ] **Step 8: Full suite + commit**:

```bash
git add scripts/refresh_lenses.py scripts/tools/add_baked_read_markers.py dashboards/
git commit -m "feat: bake static lens reads into all 33 lens pages on each brief pass"
```

---

### Task 12: Docs, final verification, and Michael's launch checklist

**Files:**
- Modify: `baileyanalytics/CLAUDE.md` (the repo-root one at `Repositories/CLAUDE.md`)
- Modify: `baileyanalytics/.github/workflows/refresh-fred.yml` (verify only)

- [ ] **Step 1: Full test suite** — `python -m unittest discover -s ".../scripts/tests" -p "test_*.py"`. Expected: ~300 tests, 0 failures.
- [ ] **Step 2: Dry-run check** — `python .../refresh_lenses.py --dry-run --brief` builds from fixtures without error. Then restore real data: `git -C ... checkout -- data/ dashboards/ index.html sitemap.xml og/` (dry-run overwrites publication surfaces too now).
- [ ] **Step 3: Visual sweep** — serve locally, screenshot at 1440/390: home (verdict baked + subscribe form), brief (baked, archive link), archive page (banner + prev/next), archive index, one lens page, 404 (`/nope`). Compare against production for visual regressions.
- [ ] **Step 4: Update `Repositories/CLAUDE.md`** — in the lens-pipeline section, update the `--brief` description to mention: publication surfaces (baked `dashboards/brief.html` + `dashboards/brief/YYYY-MM-DD.html` archive + `og/` cards + `sitemap.xml` + home patches + lens static reads — all content-aware, only on change); new modules (`briefpage.py`, `digest.py`, `ogcard.py`, `sitemap.py`, `staticread.py`, `regions.py`, `scripts/send_digest.py`); new secret `BUTTONDOWN_API_KEY`; extend the dry-run warning ("a `--dry-run` now also overwrites `dashboards/brief*.html`, `index.html` regions, `og/`, and `sitemap.xml`"); note that `dashboards/` + `index.html` are now machine-committed surfaces (pull-before-push applies); Pillow joined requirements.
- [ ] **Step 5: Verify the workflow file end-to-end** — read `refresh-fred.yml` top to bottom: digest step present with secret, commit globs cover `data/ feed.xml sitemap.xml og/ dashboards/ index.html`.
- [ ] **Step 6: Commit docs; then request code review** per the standing workflow (`/code-review` gate before merge).

```bash
git add ../CLAUDE.md
git commit -m "docs: distribution phase — publication surfaces, new modules, BUTTONDOWN_API_KEY"
```

**Michael's pre-merge checklist (cannot be automated):**
1. Create the Buttondown account — try username `baileyanalytics` (it's baked into the form URLs; if taken, pick another and update `briefpage.BUTTONDOWN_USERNAME` + the two hand-written forms in `index.html`/`about.html`).
2. In Buttondown settings: enable double opt-in; set reply-to `michael@baileyanalytics.com`; set the newsletter name ("Bailey Analytics — Today's Brief").
3. Add `BUTTONDOWN_API_KEY` to the repo's Actions secrets.
4. Subscribe yourself; after merge, watch the first scheduled send (~7am ET).

**Post-deploy verification (first day live):**
1. `https://baileyanalytics.com/sitemap.xml` and `/robots.txt` serve our content (confirm Cloudflare's managed robots prepends rather than replaces; if it replaces, toggle the managed content-signals setting in the Cloudflare dashboard).
2. Submit the sitemap in Google Search Console (Michael's account; create one if needed).
3. Share the brief URL in a private Slack/iMessage — the dated og card should unfurl.
4. Confirm the archive page for day one exists and the email's "view on site" link resolves.

---

## Self-review notes (already applied)

- **Spec coverage:** A = Tasks 3, 10 (+ canonical/JSON-LD inside Task 5's renderer); B = Tasks 4, 5, 6, 7; C = Tasks 8, 9 (+ forms in 10); D = Tasks 2, 11; tests woven throughout; docs/checklist = Task 12. The spec's "archive manifest is the idempotency source of truth" is implemented as `should_send` (Task 9) reading the manifest written in Task 6.
- **Type consistency:** `regions.replace_region(text, name, content) -> (text, changed)` used by Tasks 6 & 11 via `_patch_region_file`; `briefpage.render_brief(today, og_image, archive_date, prev_date, next_date)` consistent across Tasks 5/6; `digest.date_token` consumed by `send_digest`; manifest entry shape `{date, status, sentence}` consistent across Tasks 6/9 and `render_archive_index`.
- **Known judgment calls for the implementer:** exact insertion points in `about.html` require reading that file first (it wasn't transcribed here); the `OLD` shell string in Task 11's marker tool must be verified against one real lens page before running; Inter zip layout may vary (Task 1 includes the fallback search).

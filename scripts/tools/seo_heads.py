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

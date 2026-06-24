#!/usr/bin/env python3
"""Idempotent injector that stamps the Cloudflare Web Analytics beacon into every
hand-written page's <head>. Modeled on seo_heads.py.

The baked brief + dated archive pages get the beacon from briefpage.py directly (never
hand-edit machine-baked output), so they're skipped here. Pages that already carry the
beacon are left untouched, so this is safe to rerun whenever a new hand-written page is
added. The snippet itself lives in lenses/analytics.py (single source of truth)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lenses import analytics  # noqa: E402 - needs ROOT/scripts on the path first


def inject(html):
    """Return html with the beacon inserted just before </head>, or unchanged if the
    beacon is already present or there is no </head> to anchor to. Idempotency keys off
    the Cloudflare comment marker (stable even if the beacon's script URL ever changes),
    not the script src."""
    if analytics.BEACON_START in html:
        return html
    if "</head>" not in html:
        return html
    return html.replace("</head>", f"  {analytics.beacon_tag()}\n</head>", 1)


def is_baked(path, root):
    """True for pages briefpage.py owns (brief.html + dashboards/brief/*.html)."""
    return path == root / "dashboards" / "brief.html" or path.parent.name == "brief"


def site_pages(root):
    """The real published pages — root-level *.html plus everything under
    dashboards/, minus the brief pages briefpage.py bakes. Deliberately scoped, NOT a
    repo-wide rglob: that would also catch brainstorm mockups under .superpowers/,
    docs, and any other stray .html that isn't a shipped page."""
    pages = list(root.glob("*.html")) + list((root / "dashboards").rglob("*.html"))
    return [p for p in pages if not is_baked(p, root)]


def main(root=ROOT):
    changed = skipped = 0
    for path in sorted(site_pages(root)):
        html = path.read_text(encoding="utf-8")
        new = inject(html)
        if new != html:
            path.write_text(new, encoding="utf-8")
            changed += 1
        elif analytics.BEACON_START not in html:
            # unchanged AND no beacon == we couldn't anchor it (no </head>): surface it
            # loudly rather than silently shipping a page with no analytics.
            skipped += 1
            print(f"WARNING: no </head> in {path}; beacon not injected.", file=sys.stderr)
    msg = f"Injected the Cloudflare beacon into {changed} page(s)."
    if skipped:
        msg += f" {skipped} page(s) skipped (no </head> — see warnings)."
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())

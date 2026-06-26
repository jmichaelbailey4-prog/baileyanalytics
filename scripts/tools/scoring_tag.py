#!/usr/bin/env python3
"""Idempotent injector that stamps the scoring.js <script> tag onto every lens page,
right after predict.js. Modeled on cf_beacon.py.

Scoped to pages that already load predict.js (the 33 lens pages) — scoring.js only
does anything where there are .ind[data-indicator] cards and a lens:rendered event.
Pages without predict.js, and the baked brief pages, are left untouched, so this is
safe to rerun whenever a new lens page is added."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

PREDICT_TAG = '<script defer src="/dashboards/predict.js"></script>'
SCORING_TAG = '<script defer src="/dashboards/scoring.js"></script>'


def inject(html):
    """Insert the scoring.js tag immediately after the predict.js tag, once. No-op if
    scoring.js is already present or the page doesn't load predict.js."""
    if SCORING_TAG in html or PREDICT_TAG not in html:
        return html
    return html.replace(PREDICT_TAG, PREDICT_TAG + "\n  " + SCORING_TAG, 1)


def is_baked(path, root):
    """True for pages briefpage.py owns (brief.html + dashboards/brief/*.html)."""
    return path == root / "dashboards" / "brief.html" or path.parent.name == "brief"


def site_pages(root):
    """Real published pages — root *.html + everything under dashboards/, minus the
    baked brief pages. Deliberately scoped (not a repo-wide rglob)."""
    pages = list(root.glob("*.html")) + list((root / "dashboards").rglob("*.html"))
    return [p for p in pages if not is_baked(p, root)]


def main(root=None):
    root = root or ROOT  # late-bind so a test can pass a temp root (CLAUDE.md rule)
    changed = 0
    for path in sorted(site_pages(root)):
        html = path.read_text(encoding="utf-8")
        new = inject(html)
        if new != html:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"Stamped scoring.js onto {changed} lens page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

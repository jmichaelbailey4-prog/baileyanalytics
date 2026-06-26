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
    # baked brief surfaces (generator-owned) — stamper leaves them to briefpage.py
    if p.parent.name == "brief" and p.parent.parent.name == "dashboards":
        return False
    if p.name == "brief.html" and p.parent.name == "dashboards":
        return False
    rel = p.relative_to(root)
    if len(rel.parts) == 1:
        return True                       # root-level page
    return rel.parts[0] == "dashboards"   # anything under dashboards/


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

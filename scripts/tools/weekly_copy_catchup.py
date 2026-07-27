#!/usr/bin/env python3
"""One-time catch-up that swaps the retired DAILY subscribe copy for the weekly
copy on the already-baked brief pages. Modeled on cf_beacon.py.

Why a tool rather than the pipeline: refresh_lenses only re-renders an archive
page when its next-link changes or the page is missing, so the back catalogue
would keep promising a daily email indefinitely. Those pages are historical
documents, but their subscribe band is a LIVE call to action — a reader landing
there from search must see the cadence we actually send.

The replacement text is read out of briefpage._subscribe(), so this can never
drift from the renderer. Idempotent: pages already carrying the new copy are
left untouched, and a re-bake of any page produces the same bytes this writes.

Usage: python scripts/tools/weekly_copy_catchup.py [--dry-run]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from lenses import briefpage  # noqa: E402 - needs ROOT/scripts on the path first

# The retired copy, verbatim as baked. Kept here (not in briefpage) because it
# is history: the renderer only knows the current copy.
OLD_HEADING = '<h2 class="sec-head">Get this in your inbox</h2>'
OLD_BLURB = ('<p class="sec-sub">Free, every morning the board changes. '
             "One email, no spam, unsubscribe anytime.</p>")


def current_copy():
    """(heading, blurb) as briefpage renders them today."""
    band = briefpage._subscribe()
    heading = re.search(r"<h2 class=\"sec-head\">.*?</h2>", band, re.S)
    blurb = re.search(r"<p class=\"sec-sub\">.*?</p>", band, re.S)
    if not heading or not blurb:
        raise SystemExit("Could not read the current subscribe copy from briefpage.")
    return heading.group(0), blurb.group(0)


def update(html, heading, blurb):
    return html.replace(OLD_HEADING, heading).replace(OLD_BLURB, blurb)


def baked_pages(root):
    """The pages briefpage.py owns: the live brief plus every dated archive
    permalink. Deliberately scoped — nothing else carries this band."""
    return [root / "dashboards" / "brief.html"] + \
        sorted((root / "dashboards" / "brief").glob("*.html"))


def main(argv=None, root=ROOT):
    dry_run = "--dry-run" in (argv if argv is not None else sys.argv[1:])
    heading, blurb = current_copy()
    changed = 0
    for path in baked_pages(root):
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        new = update(html, heading, blurb)
        if new == html:
            continue
        changed += 1
        if not dry_run:
            path.write_text(new, encoding="utf-8")
    verb = "Would update" if dry_run else "Updated"
    print(f"{verb} the subscribe copy on {changed} baked brief page(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

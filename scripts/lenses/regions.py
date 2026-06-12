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

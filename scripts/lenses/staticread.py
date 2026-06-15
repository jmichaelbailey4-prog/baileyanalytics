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

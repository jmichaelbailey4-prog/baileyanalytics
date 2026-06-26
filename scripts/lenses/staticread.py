"""Static lens reads for crawlers and no-JS readers: a lens JSON -> a plain
HTML fragment (headline read + each indicator's latest value and read). The
pipeline patches it into each lens page's `baked-read` marker region; lens.js
replaces #lens-root's innerHTML wholesale on render, so the interactive view
needs no change. Pure. Formatting reuses build._fmt so the static text always
matches what the charts show."""

from html import escape

from . import build, methodology, synthesis, util

# Recent observations the per-indicator 'why' reads. Bounds the 'recent readings'
# scope so a "fresh high" claim stays honestly recent rather than all-time.
WHY_WINDOW = 40


def _recent_values(ind):
    """The indicator's last WHY_WINDOW numeric observation values — the series the
    self-grounded 'why' reads. Baked values are strings; missing/'.' ones are
    dropped via the shared util.to_float (one parser for baked values across the
    pipeline)."""
    vals = [f for f in (util.to_float(o.get("value")) for o in ind.get("observations") or [])
            if f is not None]
    return vals[-WHY_WINDOW:]


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
        # static band summary + methodology deep link for scored signals (no-JS/crawlers
        # mirror of the scoring.js strip); None for info/momentum/custom/unknown signals
        sb = methodology.static_bands(lens_json.get("id", ""), ind.get("id", ""))
        if sb:
            ranges = " · ".join(f"{escape(st)} {escape(rng)}" for st, rng in sb["rows"])
            parts.append(
                f'<p class="hub-bands">How we score this: {ranges} '
                f'<a href="/dashboards/methodology.html#{escape(sb["anchor"], quote=True)}">'
                "full method</a></p>")
        # why a signal carries no score / forecast (the matrix), for no-JS/crawlers
        note = build.signal_note(ind.get("no_severity_reason"), ind.get("no_prediction_reason"))
        if note:
            parts.append(f'<p class="signal-note"><strong>{escape(note[0])}:</strong> '
                         f'{escape(note[1])}</p>')
        # the self-grounded per-indicator 'why' (INV-1), reusing the .hub-why
        # style; omitted when the series clears no signal (honest silence)
        why = synthesis.indicator_why(ind.get("short", ""), _recent_values(ind))
        if why:
            parts.append(f'<p class="hub-why">{escape(why)}</p>')
    parts.append("</section>")
    return "".join(parts)

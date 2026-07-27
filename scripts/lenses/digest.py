"""The daily email: today.json -> {subject, html}. Pure.

Chrome (palette, rows, badges, the document shell) lives in emailkit, shared
with the weekly roundup. NOTE (2026-07-27): the shipped cadence is weekly —
see weekly_digest.py. Nothing schedules this any more; send_digest.py remains
the manual one-off sender for a mid-week event worth its own email.
"""

from html import escape

from . import emailkit, feed

SITE = emailkit.SITE
BADGE = emailkit.BADGE
INK = emailkit.INK
MUTED = emailkit.MUTED
RULE = emailkit.RULE
FONT = emailkit.FONT

MOVES_CAP = 5

# Re-exported so callers (send_digest) keep a single import.
date_token = emailkit.date_token
_badge = emailkit.badge
_row = emailkit.row
_section = emailkit.section
_watching_rows = emailkit.watching_rows


def _subject(today, token):
    transitions = today.get("transitions") or []
    if transitions:
        t = transitions[0]
        verb = "tips to" if t.get("direction") == "worsening" else "improves to"
        return (f"{t['lens_title']} {verb} {t['to_status'].upper()} "
                f"— Today's Brief, {token}")
    counts = feed._counts_phrase(today.get("status_counts", {}))
    return f"Today's Brief — {counts}, {token}"


def _changed_rows(today):
    rows = []
    for t in today.get("transitions") or []:
        rows.append(_row(
            f'<a href="{escape(SITE + t["href"], quote=True)}" style="color:{INK};">{escape(t["lens_title"])}</a> '
            f'{_badge(t["from_status"])} &rarr; {_badge(t["to_status"])}',
            escape(t.get("headline", ""))))
    for m in (today.get("top_moves") or [])[:MOVES_CAP]:
        arrow = "&#9660;" if m.get("dir") == "down" else "&#9650;"
        delta = f" {arrow}{escape(m['delta'])}" if m.get("delta") else ""
        body = escape(m.get("headline", ""))
        if m.get("why"):  # the self-grounded "why" rides along on its own muted line
            body += (f'<br><span style="font-style:italic;color:{MUTED};">'
                     f'{escape(m["why"])}</span>')
        rows.append(_row(
            f'<a href="{escape(SITE + m["href"], quote=True)}" style="color:{INK};">{escape(m["lens_title"])}</a> '
            f'&middot; {escape(m.get("stat_label", ""))} '
            f'<strong>{escape(m.get("stat_value", ""))}</strong>{delta}',
            body))
    if not rows:
        rows.append(_row("A quiet day on the board", "No status changes or outsized moves."))
    return "".join(rows)


def _relationship_lead(today):
    """The curated relationship lead (spec §3) at the top of 'What changed today'
    — the day's single most defensible cross-category connection. '' when the map
    is silent today. Honesty-gated upstream (compose_relationships); this only
    escapes. Email-safe: a left-accented table row, no images."""
    rels = [s for s in ((today.get("synthesis") or {}).get("relationships") or []) if s]
    if not rels:
        return ""
    body = "<br>".join(escape(s) for s in rels)
    return (f'<tr><td style="{FONT}font-size:14px;line-height:1.5;color:{INK};'
            f'padding:10px 0 10px 12px;border-left:3px solid {BADGE["neutral"]};">'
            f"{body}</td></tr>")


def build_digest(today):
    day = (today.get("generated_at") or "1970-01-01")[:10]
    token = date_token(day)
    verdict = today.get("verdict") or {}
    counts = today.get("status_counts", {})
    attention = counts.get("watch", 0) + counts.get("elevated", 0) + counts.get("alert", 0)
    permalink = f"{SITE}/dashboards/brief/{day}.html"

    watching = _watching_rows(today.get("watching"))
    watching_block = (_section("What we&rsquo;re watching next") + watching) if watching else ""

    body = f"""{_section("What changed today")}
{_relationship_lead(today)}
{_changed_rows(today)}
{watching_block}
<tr><td style="padding:22px 0 0;{FONT}font-size:13px;color:{MUTED};">
{attention} readings warrant attention right now &mdash;
<a href="{permalink}#alert" style="color:{INK};">see where the pressure is</a>.
</td></tr>
<tr><td style="padding:18px 0 0;{FONT}font-size:13px;">
<a href="{permalink}" style="color:{INK};font-weight:600;">View this brief on the site &rarr;</a>
</td></tr>"""

    html = emailkit.document(
        f"Today&rsquo;s Brief &middot; {escape(token)}",
        verdict.get("status", "unknown"), verdict.get("sentence", ""), body)
    return {"subject": _subject(today, token), "html": html}

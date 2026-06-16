"""The daily email: today.json -> {subject, html}. Pure. Email-safe HTML —
single-column table, inline styles, light theme (the dark site palette is
unreliable across email clients). Text-first: no images, so it loads fast and
keeps spam scores clean. The {{ unsubscribe_url }} placeholder is substituted
by Buttondown at send time."""

from html import escape

from . import feed, util

SITE = "https://baileyanalytics.com"

BADGE = {"ok": "#059669", "watch": "#B45309", "elevated": "#C2410C",
         "alert": "#DC2626", "neutral": "#0284C7"}
INK = "#111827"
MUTED = "#6B7280"
RULE = "#E5E7EB"
FONT = ("font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "Helvetica,Arial,sans-serif;")

MOVES_CAP = 5


def date_token(iso_date):
    """'Jun 12, 2026' — used in the subject and as the idempotency key.
    Shares util.human_date with the brief page so the two never drift."""
    return util.human_date(iso_date, short=True)


def _badge(status):
    color = BADGE.get(status, MUTED)
    return (f'<span style="color:{color};border:1px solid {color};border-radius:999px;'
            f'padding:1px 9px;font-size:11px;font-weight:700;letter-spacing:.05em;">'
            f"{escape(status.upper())}</span>")


def _subject(today, token):
    transitions = today.get("transitions") or []
    if transitions:
        t = transitions[0]
        verb = "tips to" if t.get("direction") == "worsening" else "improves to"
        return (f"{t['lens_title']} {verb} {t['to_status'].upper()} "
                f"— Today's Brief, {token}")
    counts = feed._counts_phrase(today.get("status_counts", {}))
    return f"Today's Brief — {counts}, {token}"


def _row(title_html, body_html):
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid {RULE};">'
            f'<div style="{FONT}font-size:13px;color:{INK};font-weight:700;">{title_html}</div>'
            f'<div style="{FONT}font-size:13px;color:{MUTED};margin-top:2px;">{body_html}</div>'
            "</td></tr>")


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


def _watching_rows(today):
    rows = []
    for x in (today.get("watching") or [])[:3]:
        if x.get("change"):
            claim = (f"we expect <strong>{escape(x['point_fmt'])}</strong> — which would tip "
                     f"{escape(x['lens_title'])} to {_badge(x['implied_status'])}")
        else:
            claim = f"we expect <strong>{escape(x['point_fmt'])}</strong>, no status change"
        rows.append(_row(escape(x.get("title", "")), claim))
    return "".join(rows)


def _section(label):
    return (f'<tr><td style="padding:22px 0 4px;{FONT}font-size:11px;font-weight:700;'
            f'letter-spacing:.08em;color:{MUTED};text-transform:uppercase;">{label}</td></tr>')


def build_digest(today):
    day = (today.get("generated_at") or "1970-01-01")[:10]
    token = date_token(day)
    verdict = today.get("verdict") or {}
    counts = today.get("status_counts", {})
    attention = counts.get("watch", 0) + counts.get("elevated", 0) + counts.get("alert", 0)
    permalink = f"{SITE}/dashboards/brief/{day}.html"

    watching = _watching_rows(today)
    watching_block = (_section("What we&rsquo;re watching next") + watching) if watching else ""

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F9FAFB;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid {RULE};border-radius:10px;padding:28px 28px 20px;">
<tr><td style="{FONT}font-size:13px;font-weight:700;letter-spacing:.1em;color:{INK};">BAILEY ANALYTICS</td></tr>
<tr><td style="{FONT}font-size:12px;color:{MUTED};padding-top:2px;">Today&rsquo;s Brief &middot; {escape(token)}</td></tr>
<tr><td style="padding:18px 0 6px;">{_badge(verdict.get("status", "unknown"))}</td></tr>
<tr><td style="{FONT}font-size:17px;line-height:1.5;color:{INK};font-weight:600;">{escape(verdict.get("sentence", ""))}</td></tr>
{_section("What changed today")}
{_changed_rows(today)}
{watching_block}
<tr><td style="padding:22px 0 0;{FONT}font-size:13px;color:{MUTED};">
{attention} readings warrant attention right now &mdash;
<a href="{permalink}#alert" style="color:{INK};">see where the pressure is</a>.
</td></tr>
<tr><td style="padding:18px 0 0;{FONT}font-size:13px;">
<a href="{permalink}" style="color:{INK};font-weight:600;">View this brief on the site &rarr;</a>
</td></tr>
<tr><td style="padding:26px 0 0;{FONT}font-size:11px;color:{MUTED};line-height:1.6;border-top:1px solid {RULE};margin-top:18px;">
Built from public data &mdash; FRED, the FDIC, the U.S. EIA, the IMF, the NY Fed, and more. Not investment advice.<br>
You&rsquo;re getting this because you subscribed at baileyanalytics.com.
<a href="{{{{ unsubscribe_url }}}}" style="color:{MUTED};">Unsubscribe</a>
</td></tr>
</table></td></tr></table>
</body></html>"""
    return {"subject": _subject(today, token), "html": html}

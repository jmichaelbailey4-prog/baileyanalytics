"""Shared chrome for the outbound emails (the daily digest and the weekly
roundup). Pure. Email-safe HTML — single-column table, inline styles, light
theme (the dark site palette is unreliable across email clients). Text-first:
no images, so it loads fast and keeps spam scores clean.

Extracted from digest.py so the two emails can never drift apart on palette,
row markup, or the outer document. The {{ unsubscribe_url }} placeholder is
substituted by Buttondown at send time.
"""

from html import escape

from . import util

SITE = "https://baileyanalytics.com"

BADGE = {"ok": "#059669", "watch": "#B45309", "elevated": "#C2410C",
         "alert": "#DC2626", "neutral": "#0284C7"}
INK = "#111827"
MUTED = "#6B7280"
RULE = "#E5E7EB"
FONT = ("font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "Helvetica,Arial,sans-serif;")


def date_token(iso_date):
    """'Jun 12, 2026' — used in subjects and as the idempotency key.
    Shares util.human_date with the brief page so the two never drift."""
    return util.human_date(iso_date, short=True)


def badge(status):
    color = BADGE.get(status, MUTED)
    return (f'<span style="color:{color};border:1px solid {color};border-radius:999px;'
            f'padding:1px 9px;font-size:11px;font-weight:700;letter-spacing:.05em;">'
            f"{escape(status.upper())}</span>")


def row(title_html, body_html):
    return (f'<tr><td style="padding:14px 0;border-bottom:1px solid {RULE};">'
            f'<div style="{FONT}font-size:13px;color:{INK};font-weight:700;">{title_html}</div>'
            f'<div style="{FONT}font-size:13px;color:{MUTED};margin-top:2px;">{body_html}</div>'
            "</td></tr>")


def section(label):
    return (f'<tr><td style="padding:22px 0 4px;{FONT}font-size:11px;font-weight:700;'
            f'letter-spacing:.08em;color:{MUTED};text-transform:uppercase;">{label}</td></tr>')


def watching_rows(watching, limit=3):
    """"What we're watching next" — the open predictions block, identical in
    both emails. `watching` is today.json's already-ranked list."""
    rows = []
    for x in (watching or [])[:limit]:
        if x.get("change"):
            # Mirrors briefpage: improving changes "ease", worsening ones "tip".
            verb = ("ease" if util.STATUS_ORDER.get(x.get("implied_status"), 0)
                    < util.STATUS_ORDER.get(x.get("current_status"), 0) else "tip")
            claim = (f"we expect <strong>{escape(x['point_fmt'])}</strong> — which would {verb} "
                     f"{escape(x['lens_title'])} to {badge(x['implied_status'])}")
        else:
            claim = f"we expect <strong>{escape(x['point_fmt'])}</strong>, no status change"
        rows.append(row(escape(x.get("title", "")), claim))
    return "".join(rows)


def document(eyebrow_html, status, headline, body):
    """The full email document: masthead, eyebrow line, status badge, headline
    sentence, the caller's `body` rows, and the shared footer.

    `eyebrow_html` and `body` are raw markup the caller has already escaped
    (both are assembled from module constants plus machine-generated dates);
    `headline` is plain text and is escaped here."""
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#F9FAFB;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#FFFFFF;border:1px solid {RULE};border-radius:10px;padding:28px 28px 20px;">
<tr><td style="{FONT}font-size:13px;font-weight:700;letter-spacing:.1em;color:{INK};">BAILEY ANALYTICS</td></tr>
<tr><td style="{FONT}font-size:12px;color:{MUTED};padding-top:2px;">{eyebrow_html}</td></tr>
<tr><td style="padding:18px 0 6px;">{badge(status)}</td></tr>
<tr><td style="{FONT}font-size:17px;line-height:1.5;color:{INK};font-weight:600;">{escape(headline)}</td></tr>
{body}
<tr><td style="padding:26px 0 0;{FONT}font-size:11px;color:{MUTED};line-height:1.6;border-top:1px solid {RULE};margin-top:18px;">
Built from public data &mdash; FRED, the FDIC, the U.S. EIA, the IMF, the NY Fed, and more. Not investment advice.<br>
You&rsquo;re getting this because you subscribed at baileyanalytics.com.
<a href="{{{{ unsubscribe_url }}}}" style="color:{MUTED};">Unsubscribe</a>
</td></tr>
</table></td></tr></table>
</body></html>"""

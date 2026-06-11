"""RSS feed for Today's Brief. Pure: build_item / merge_items / render_feed
take and return data; refresh_lenses owns all disk I/O. One item per day,
newest first, so any RSS reader (or RSS-to-email service) becomes a push
channel for the daily brief."""

from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

SITE = "https://baileyanalytics.com"
BRIEF_URL = f"{SITE}/dashboards/brief.html"


def _counts_phrase(counts):
    parts = []
    for status, label in (("alert", "alert"), ("elevated", "elevated"), ("watch", "on watch")):
        if counts.get(status):
            parts.append(f"{counts[status]} {label}")
    return " · ".join(parts) if parts else "All clear across the dashboards"


def build_item(today):
    """One feed item summarizing a day's brief (today.json shape)."""
    day = (today.get("generated_at") or "")[:10]
    title = f"Today's Brief — {_counts_phrase(today.get('status_counts', {}))}"
    lines = []
    for t in today.get("transitions", []):
        lines.append(f"{t['lens_title']}: {t['from_status']} → {t['to_status']} — {t['headline']}")
    for m in today.get("top_moves", []):
        arrow = "▼" if m.get("dir") == "down" else "▲"
        lines.append(f"{m['lens_title']}: {m['stat_label']} {m['stat_value']} ({arrow}{m['delta']})")
    if not lines:
        lines.append("No status changes or outsized moves today.")
    return {"date": day, "title": title, "description": "\n".join(lines)}


def merge_items(existing, new_item, cap=30):
    """Prepend new_item, replacing any same-day item; keep the newest `cap`."""
    items = [i for i in (existing or []) if i.get("date") != new_item["date"]]
    items.insert(0, new_item)
    items.sort(key=lambda i: i["date"], reverse=True)
    return items[:cap]


def render_feed(items):
    """Render RSS 2.0 XML. Item pubDates are midnight UTC of the brief date."""
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
        "<title>Bailey Analytics — Today&#39;s Brief</title>",
        f"<link>{BRIEF_URL}</link>",
        f'<atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>',
        "<description>Daily plain-English status changes and movers across the "
        "Bailey Analytics economic dashboards.</description>",
    ]
    for item in items:
        dt = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        out.append("<item>")
        out.append(f"<title>{escape(item['title'])}</title>")
        out.append(f"<link>{BRIEF_URL}</link>")
        out.append(f'<guid isPermaLink="false">brief-{item["date"]}</guid>')
        out.append(f"<pubDate>{format_datetime(dt)}</pubDate>")
        out.append(f"<description>{escape(item['description'])}</description>")
        out.append("</item>")
    out.append("</channel></rss>")
    return "\n".join(out)

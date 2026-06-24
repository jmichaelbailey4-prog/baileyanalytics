"""The baked Today's Brief page: one renderer for /dashboards/brief.html
(today), the dated archive permalinks, and the archive index. Replaces the
page's former client-side render (one renderer instead of a JS/Python sync
pair). Pure: today.json data in, full HTML documents out."""

import json
from html import escape

from . import analytics, pwa, util

SITE = "https://baileyanalytics.com"

# The PWA head block, emitted directly here because the stamper (tools/pwa_head.py)
# skips baked surfaces. Same marker + content, so re-bakes stay byte-identical.
_PWA_HEAD = "<!-- pwa:head -->\n" + pwa.head_tags()
_THEME_HEAD = "<!-- theme:head -->\n" + pwa.theme_head()

# Set after Michael creates the Buttondown account; "" hides the form.
BUTTONDOWN_USERNAME = "baileyanalytics"

CATEGORY_LABELS = {"economic": "Economy", "consumer": "Consumer", "banking": "Banking",
                   "business": "Business", "markets": "Markets", "energy": "Energy",
                   "housing": "Housing", "global": "Global"}  # short labels for the brief rows; add here when config.CATEGORIES gains a category

PRESSURE_GROUPS = [
    ("alert", "On alert — levels that have historically meant real stress"),
    ("elevated", "Elevated — clearly outside comfortable ranges"),
    ("watch", "On watch — first warnings"),
]


def _date_label(iso_date):
    """'YYYY-MM-DD' -> 'June 12, 2026' (delegates to the shared util helper)."""
    return util.human_date(iso_date)


def _spark(values, accent):
    """Inline sparkline SVG; mirrors the JS math exactly (toFixed(1))."""
    if not values:
        return ""
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{(i / (len(vals) - 1) * 100):.1f},{(28 - ((v - lo) / rng) * 26):.1f}"
                   for i, v in enumerate(vals))
    return (f'<svg class="spark" aria-hidden="true" viewBox="0 0 100 30" '
            f'preserveAspectRatio="none"><polyline points="{pts}" fill="none" '
            f'stroke="{escape(accent or "#38BDF8", quote=True)}" stroke-width="2"/></svg>')


def _relationships(rels):
    """The curated relationship lead (spec §3) — the day's single most defensible
    cross-category connection, shown above the status changes in 'What changed
    today'. Each sentence is honesty-gated upstream (synthesis.compose_relationships
    renders only tier-valid edges whose endpoints are active), so this is pure
    escaping. '' when no edge is active today — quiet-day silence."""
    return "".join(f'<p class="brief-rel">{escape(s)}</p>' for s in (rels or []) if s)


def _transitions(transitions):
    if not transitions:
        return ('<div class="status-msg" style="text-align:left;padding:.4rem 0">'
                "No status changes today — a quiet day on the board.</div>")
    # Mirrors the old brief.js transitionRow markup so lens.css's dedicated
    # .brief-trans / .brief-arrow styling applies (status changes are the
    # flagship event — they must not collapse into pressure-row styling).
    rows = []
    for t in transitions:
        cat = CATEGORY_LABELS.get(t["category"])
        cat_html = f'<span class="brief-cat">{escape(cat)}</span>' if cat else ""
        rows.append(
            f'<a class="brief-trans" href="{escape(t["href"], quote=True)}">'
            f'{cat_html}'
            f'<span class="brief-trans-title">{escape(t["lens_title"])}</span>'
            f'<span class="brief-arrow">'
            f'<span class="badge {escape(t["from_status"])}">{escape(t["from_status"])}</span>'
            f' &rarr; '
            f'<span class="badge {escape(t["to_status"])}">{escape(t["to_status"])}</span></span>'
            f'<span class="brief-trans-read">{escape(t["headline"])}</span></a>')
    return "".join(rows)


def _movers(moves):
    if not moves:
        return ""
    cards = []
    for m in moves:
        delta = (f' <i class="delta {escape(m.get("dir", ""))}">{escape(m.get("delta", ""))}</i>'
                 if m.get("delta") else "")
        why = (f'<div class="hub-why">{escape(m["why"])}</div>' if m.get("why") else "")
        cards.append(
            f'<a class="hub-card" href="{escape(m["href"], quote=True)}">'
            f'<div class="hub-eyebrow" style="color:{escape(m.get("accent") or "#94A3B8", quote=True)}">'
            f'<span class="hub-cat">{escape(CATEGORY_LABELS.get(m["category"], m["category"]))} ·</span> '
            f'{escape(m["lens_title"])}</div>'
            f'<div class="hub-read">{escape(m.get("headline", ""))}</div>'
            f'{why}'
            f'{_spark(m.get("sparkline"), m.get("accent"))}'
            f'<div class="hub-stats">{escape(m.get("stat_label", ""))} '
            f'<b>{escape(m.get("stat_value", ""))}</b>{delta}</div></a>')
    return ('<section id="moves-sec"><div class="brief-sec-label" id="moves">Biggest movers</div>'
            '<div class="hub-grid" style="margin-top:.5rem">' + "".join(cards) + "</div></section>")


def _watching(watching):
    if not watching:
        return ""
    rows = []
    for x in watching:
        if x.get("change"):
            _imp = escape(x.get("implied_status") or "unknown")
            claim = (f'we expect <strong>{escape(x["point_fmt"])}</strong> — which would tip '
                     f'{escape(x["lens_title"])} to <span class="badge '
                     f'{_imp}">{_imp}</span>')
        else:
            claim = f'we expect <strong>{escape(x["point_fmt"])}</strong>, no status change'
        rows.append(f'<a class="state-lens" href="{escape(x["href"], quote=True)}">'
                    f'<span class="state-lens-title">{escape(x["title"])}</span>'
                    f'<span class="state-lens-read">{claim}</span></a>')
    rows.append('<a class="state-link" href="/dashboards/track-record.html">Our track record &rarr;</a>')
    return ("<section><h2 class=\"sec-head\">What we&rsquo;re watching next</h2>"
            '<p class="sec-sub">Our published predictions for the most consequential upcoming '
            "prints — each graded in public when the number lands.</p>" + "".join(rows) + "</section>")


def _pressure(rows):
    if not rows:
        return ""
    groups = []
    for status, label in PRESSURE_GROUPS:
        group = [p for p in rows if p["status"] == status]
        if not group:
            continue
        items = "".join(
            f'<a class="att-row" href="{escape(p["href"], quote=True)}">'
            f'<span class="brief-cat">{escape(CATEGORY_LABELS.get(p["category"], p["category"]))}</span>'
            f'<span class="att-title">{escape(p["lens_title"])}</span>'
            f'<span class="badge {escape(p["status"])}">{escape(p["status"])}</span>'
            f'<span class="att-read">{escape(p["headline"])}</span></a>' for p in group)
        groups.append(f'<div class="att-group" id="{status}">'
                      f'<div class="brief-sec-label">{escape(label)}</div>{items}</div>')
    return ('<section id="pressure"><h2 class="sec-head">Where the pressure is</h2>'
            '<p class="sec-sub">Everything currently warranting attention, worst first.</p>'
            + "".join(groups) + "</section>")


def _categories(cats):
    links = "".join(
        f'<a class="state-steady" href="{escape(c["href"], quote=True)}">'
        f'<span class="badge {escape(c["status"])}">{escape(c["status"])}</span>'
        f'{escape(c["title"])}</a>' for c in cats)
    return ('<section><h2 class="sec-head">Across the dashboards</h2>'
            '<p class="sec-sub">Every category&rsquo;s overall read — jump into any of them.</p>'
            + links + "</section>")


def _subscribe():
    if not BUTTONDOWN_USERNAME:
        return ""
    return (
        '<section class="subscribe-band"><h2 class="sec-head">Get this in your inbox</h2>'
        '<p class="sec-sub">Free, every morning the board changes. One email, no spam, '
        "unsubscribe anytime.</p>"
        f'<form class="subscribe-form" action="https://buttondown.com/api/emails/embed-subscribe/'
        f'{BUTTONDOWN_USERNAME}" method="post">'
        '<input type="email" name="email" required placeholder="you@example.com" '
        'aria-label="Email address">'
        "<button type=\"submit\">Subscribe</button></form></section>")


def _jsonld(today, canonical, og_url):
    data = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": (today.get("verdict") or {}).get("sentence", "Today's Brief"),
        "datePublished": today.get("generated_at", ""),
        "dateModified": today.get("generated_at", ""),
        "mainEntityOfPage": canonical, "image": og_url,
        "author": {"@type": "Organization", "name": "Bailey Analytics", "url": SITE},
        "publisher": {"@type": "Organization", "name": "Bailey Analytics", "url": SITE},
    }
    # Harden against breaking out of <script>: escape <, >, & as \uXXXX (still
    # valid inside JSON strings) so a future verdict sentence containing
    # "</script>" or "<" can never terminate the block early.
    payload = (json.dumps(data, ensure_ascii=False, indent=2)
               .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    return '<script type="application/ld+json">' + payload + "</script>"


def render_brief(today, og_image, archive_date=None, prev_date=None, next_date=None):
    """The full brief HTML document. archive_date switches on archive chrome."""
    day = archive_date or (today.get("generated_at") or "1970-01-01")[:10]
    label = _date_label(day)
    canonical = (f"{SITE}/dashboards/brief/{archive_date}.html" if archive_date
                 else f"{SITE}/dashboards/brief.html")
    og_url = SITE + og_image
    title = (f"Brief for {label} — Bailey Analytics" if archive_date
             else "Today's Brief — Bailey Analytics")
    desc = ((today.get("verdict") or {}).get("sentence")
            or "The daily read on the U.S. and global economy.")

    verdict = today.get("verdict") or {}
    cooccur = (today.get("synthesis") or {}).get("cooccurrence") or ""
    rels_html = _relationships((today.get("synthesis") or {}).get("relationships"))
    verdict_html = ""
    if verdict.get("sentence"):
        vstatus = escape(verdict.get("status", "unknown"))
        cooccur_html = (f'<div class="state-cooccur">{escape(cooccur)}</div>'
                        if cooccur else "")
        verdict_html = (
            '<section class="state-panel" id="verdict" style="margin-top:1.25rem">'
            f'<div class="state-verdict"><span class="badge {vstatus}">'
            f'{vstatus}</span> <span class="state-sentence">'
            f'{escape(verdict["sentence"])}</span></div>{cooccur_html}</section>')

    banner = ""
    if archive_date:
        banner = (f'<div class="archive-banner">This is the brief from {escape(label)} — '
                  '<a href="/dashboards/brief.html">see today&rsquo;s brief</a>.</div>')
    nav_parts = []
    if prev_date:
        nav_parts.append(
            f'<a href="/dashboards/brief/{prev_date}.html">&larr; {escape(_date_label(prev_date))}</a>')
    nav_parts.append('<a href="/dashboards/brief/">Archive</a>')
    if next_date:
        nav_parts.append(
            f'<a href="/dashboards/brief/{next_date}.html">{escape(_date_label(next_date))} &rarr;</a>')
    archive_nav = '<nav class="archive-nav" aria-label="Brief archive">' + " · ".join(nav_parts) + "</nav>"

    h1 = "Today&rsquo;s Brief" if not archive_date else escape(f"Brief for {label}")

    brief_aria = ' aria-current="page"' if not archive_date else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(desc, quote=True)}">
  <link rel="canonical" href="{escape(canonical, quote=True)}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(desc, quote=True)}">
  <meta property="og:url" content="{escape(canonical, quote=True)}">
  <meta property="og:image" content="{escape(og_url, quote=True)}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="alternate" type="application/rss+xml" title="Bailey Analytics — Today&#39;s Brief" href="/feed.xml">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  <style>
    .sec-head {{ font-size: 1.4rem; font-weight: 600; letter-spacing: -0.01em; margin: 2.25rem 0 0.3rem; scroll-margin-top: 1rem; }}
    .sec-sub {{ color: var(--muted); font-size: .92rem; max-width: 42rem; margin-bottom: 1.15rem; }}
    #verdict .state-sentence {{ font-size: 1.15rem; }}
  </style>
  {_jsonld(today, canonical, og_url)}
  {analytics.beacon_tag()}
  {_THEME_HEAD}
  {_PWA_HEAD}
</head>
<body>
  <nav class="wordmark" aria-label="Bailey Analytics home"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav" aria-label="Primary"><a href="/dashboards/brief.html"{brief_aria}>Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    {banner}
    <h1>{h1}</h1>
    <p class="lede">The daily read on the U.S. and global economy — where things stand, what changed, and what we&rsquo;re watching next. <strong>Open anything</strong> for the full charts and context.</p>
    <div class="hub-fresh">As of {escape(label)}</div>
    {archive_nav}
    {verdict_html}
    <section><h2 class="sec-head">What changed today</h2>
    {rels_html}
    <p class="sec-sub">Status changes first — the headline events — then the biggest moves in the data, judged against each indicator&rsquo;s own typical day-to-day swing.</p>
    {_transitions(today.get("transitions") or [])}</section>
    {_movers(today.get("top_moves") or [])}
    {_watching(today.get("watching") or [])}
    {_subscribe()}
    {_pressure(today.get("pressure") or [])}
    {_categories(today.get("categories") or [])}
    <div class="foot">
      Data: <a href="https://fred.stlouisfed.org/" target="_blank" rel="noopener">FRED</a> (St. Louis Fed), the <a href="https://banks.data.fdic.gov/" target="_blank" rel="noopener">FDIC</a>, the <a href="https://www.eia.gov/opendata/" target="_blank" rel="noopener">U.S. EIA</a>, the <a href="https://www.imf.org/en/Publications/WEO" target="_blank" rel="noopener">IMF</a>, the <a href="https://www.newyorkfed.org/research/policy/gscpi" target="_blank" rel="noopener">NY Fed</a>, <a href="https://www.policyuncertainty.com/" target="_blank" rel="noopener">policyuncertainty.com</a>, and <a href="https://www.coingecko.com/" target="_blank" rel="noopener">CoinGecko</a>. Public data, refreshed regularly.
      Get the brief in your reader: <a href="/feed.xml">RSS feed</a>.
    </div>
  </main>
</body>
</html>
"""


def render_archive_index(manifest):
    """The /dashboards/brief/ archive listing, newest first, grouped by month."""
    entries = sorted(manifest, key=lambda e: e["date"], reverse=True)
    by_month, order = {}, []
    for e in entries:
        month = _date_label(e["date"]).split(" ")[0] + " " + e["date"][:4]
        if month not in by_month:
            by_month[month] = []
            order.append(month)
        by_month[month].append(e)
    sections = []
    for month in order:
        rows = "".join(
            f'<a class="att-row" href="/dashboards/brief/{e["date"]}.html">'
            f'<span class="att-title">{escape(_date_label(e["date"]))}</span>'
            f'<span class="badge {escape(e["status"])}">{escape(e["status"])}</span>'
            f'<span class="att-read">{escape(e.get("sentence", ""))}</span></a>'
            for e in by_month[month])
        sections.append(f'<div class="att-group"><div class="brief-sec-label">'
                        f"{escape(month)}</div>{rows}</div>")
    body = "".join(sections) or '<p class="sec-sub">No archived briefs yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Brief Archive — Bailey Analytics</title>
  <meta name="description" content="Every published Today&#39;s Brief, by date — the daily plain-English read on the U.S. and global economy.">
  <link rel="canonical" href="{SITE}/dashboards/brief/">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Bailey Analytics">
  <meta property="og:title" content="Brief Archive — Bailey Analytics">
  <meta property="og:description" content="Every published Today&#39;s Brief, by date.">
  <meta property="og:url" content="{SITE}/dashboards/brief/">
  <meta property="og:image" content="{SITE}/og/site.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="stylesheet" href="/dashboards/lens.css">
  {analytics.beacon_tag()}
  {_THEME_HEAD}
  {_PWA_HEAD}
</head>
<body>
  <nav class="wordmark" aria-label="Bailey Analytics home"><a href="/">Bailey Analytics</a></nav>
  <nav class="top-nav" aria-label="Primary"><a href="/dashboards/brief.html">Today&#39;s Brief</a><a href="/dashboards/">Dashboards</a><a href="/dashboards/track-record.html">Track Record</a><a href="/about.html">About</a></nav>
  <main>
    <a class="back" href="/dashboards/brief.html">&larr; Today&rsquo;s Brief</a>
    <h1>Brief Archive</h1>
    <p class="lede">Every published brief, newest first.</p>
    {body}
  </main>
</body>
</html>
"""

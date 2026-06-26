"""sitemap.xml for the whole site. Pure: build_urls/render_sitemap take and
return data; refresh_lenses owns disk I/O. The archive manifest supplies the
dated brief pages, so the sitemap grows one URL per publication day."""

from xml.sax.saxutils import escape

from . import brief, config

SITE = "https://baileyanalytics.com"

STATIC_PAGES = [
    "/",
    "/about.html",
    "/dashboards/",
    "/dashboards/brief.html",
    "/dashboards/brief/",
    "/dashboards/methodology.html",
    "/dashboards/track-record.html",
    # favorites.html is deliberately NOT here: it's noindex (a per-visitor PWA
    # start_url with no shareable content), and a noindex URL in the sitemap
    # trips Search Console's "Submitted URL marked noindex" warning. It stays
    # discoverable via the Dashboards-hub link and the injected nav entry.
    # the crypto lens is injected (not in config.CATEGORIES' markets entry)
    "/dashboards/markets/crypto-structure.html",
]


def build_urls(archive_dates):
    """All site URLs as (absolute loc, lastmod-or-None), no duplicates.
    archive_dates: iterable of 'YYYY-MM-DD' publication days."""
    urls = [(SITE + p, None) for p in STATIC_PAGES]
    for cat in config.CATEGORIES:
        urls.append((f"{SITE}/dashboards/{cat['id']}/", None))
        for lens in cat["lenses"]:
            urls.append((SITE + brief.lens_href(cat["id"], lens.id), None))
    for d in sorted(archive_dates):
        urls.append((f"{SITE}/dashboards/brief/{d}.html", d))
    seen, out = set(), []
    for loc, mod in urls:
        if loc not in seen:
            seen.add(loc)
            out.append((loc, mod))
    return out


def render_sitemap(urls):
    """Render Sitemap Protocol 0.9 XML from (loc, lastmod-or-None) pairs."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        entry = f"<url><loc>{escape(loc)}</loc>"
        if lastmod:
            entry += f"<lastmod>{lastmod}</lastmod>"
        out.append(entry + "</url>")
    out.append("</urlset>")
    return "\n".join(out)

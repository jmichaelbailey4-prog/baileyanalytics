"""Cross-category 'Today's Brief': diff lens statuses for transitions and rank
the most significant moves. Pure synthesis over already-built index.json data —
no network, no disk I/O (callers pass data in and get data out)."""

# Severity ladder for transition direction. Mirrors the home page's SEVERITY
# (index.html) and util.STATUS_ORDER; neutral/info/unknown are intentionally
# absent — only these four can "transition".
SEVERITY = {"ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def pct_change(sparkline):
    """Signed percent change of the last point vs the one before it, or None when
    there are <2 points or the prior value is zero. The sparkline already carries
    the primary indicator's raw numeric series (build.build_index)."""
    if not sparkline or len(sparkline) < 2:
        return None
    prior, latest = sparkline[-2], sparkline[-1]
    if prior == 0:
        return None
    return (latest - prior) / prior * 100.0


# Lens-id -> page-slug maps, mirroring dashboards/index.html (keep in sync).
_MARKET_SLUGS = {
    "market-risk-sentiment": "risk-sentiment",
    "market-scoreboard": "scoreboard",
    "market-liquidity": "liquidity",
    "crypto-structure": "crypto-structure",
}
_ENERGY_SLUGS = {
    "energy-oil-fuels": "oil-fuels",
    "energy-natural-gas": "natural-gas",
    "energy-electricity": "electricity",
    "energy-commodities": "commodities",
}
_CONSUMER_SLUGS = {
    "consumer-spending": "spending",
    "consumer-credit": "credit-stress",
    "consumer-income-savings": "income-savings",
    "consumer-sentiment": "sentiment",
}
_HOUSING_SLUGS = {
    "housing-home-prices": "home-prices",
    "housing-affordability": "affordability",
    "housing-supply-construction": "supply-construction",
    "housing-rent-shelter": "rent-shelter",
}


def lens_href(category, lens_id):
    """Public page path for a lens, mirroring dashboards/index.html slug logic."""
    if category == "economic":
        return f"/dashboards/{lens_id}.html"
    if category == "banking":
        return f"/dashboards/banking/{lens_id.replace('bank-', '', 1)}.html"
    if category == "markets":
        return f"/dashboards/markets/{_MARKET_SLUGS.get(lens_id, lens_id)}.html"
    if category == "energy":
        return f"/dashboards/energy/{_ENERGY_SLUGS.get(lens_id, lens_id)}.html"
    if category == "consumer":
        return f"/dashboards/consumer/{_CONSUMER_SLUGS.get(lens_id, lens_id)}.html"
    if category == "housing":
        return f"/dashboards/housing/{_HOUSING_SLUGS.get(lens_id, lens_id)}.html"
    return "/dashboards/"


# Category order for the brief (drives tie-break ordering only).
CATEGORIES = ["economic", "consumer", "banking", "markets", "energy", "housing"]


def _flatten_lenses(category_indices):
    """Flatten {category: index_json} into a list of lens records carrying
    category, href, status, headline, key_stats, and sparkline."""
    flat = []
    for category in CATEGORIES:
        index = category_indices.get(category)
        if not index:
            continue
        for lens in index.get("lenses", []):
            flat.append({
                "lens_id": lens["id"],
                "lens_title": lens["title"],
                "category": category,
                "href": lens_href(category, lens["id"]),
                "status": lens.get("status", "unknown"),
                "headline": lens.get("headline_read", ""),
                "key_stats": lens.get("key_stats", []),
                "sparkline": lens.get("sparkline", []),
            })
    return flat


def detect_transitions(prior_statuses, flat_lenses):
    """Lenses whose severity status changed vs. prior_statuses. Only ok/watch/
    elevated/alert transitions count (neutral/info/unknown are skipped). Sorted
    worsening-first by size of the severity jump, then improving."""
    out = []
    for r in flat_lenses:
        new = r["status"]
        old = prior_statuses.get(r["lens_id"])
        if old is None or old == new:
            continue
        if old not in SEVERITY or new not in SEVERITY:
            continue
        jump = SEVERITY[new] - SEVERITY[old]
        out.append({
            "lens_id": r["lens_id"],
            "lens_title": r["lens_title"],
            "category": r["category"],
            "href": r["href"],
            "from_status": old,
            "to_status": new,
            "direction": "worsening" if jump > 0 else "improving",
            "headline": r["headline"],
            "_jump": jump,
        })
    # Worsening (positive jump) first, largest jump first; then improving.
    out.sort(key=lambda t: -t["_jump"])
    for t in out:
        del t["_jump"]
    return out

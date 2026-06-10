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

"""Cross-category 'Today's Brief': diff lens statuses for transitions and rank
the most significant moves. Pure synthesis over already-built index.json data —
no network, no disk I/O (callers pass data in and get data out)."""

import statistics
from datetime import datetime, timezone

# Severity ladder for transition direction. Mirrors the home page's SEVERITY
# (index.html) and util.STATUS_ORDER; neutral/info/unknown are intentionally
# absent — only these four can "transition".
SEVERITY = {"ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def move_score(sparkline):
    """Significance of a series' latest step, normalized by the volatility of its
    earlier steps — a dimensionless z-score, so moves are comparable across
    indicators measured in different units (a 0.1-point move in a normally-quiet
    rate and a 50-point move in the S&P are each judged against their own typical
    step). The sparkline carries the primary indicator's raw numeric series
    (build.build_index). Returns a non-negative score; None when there's too
    little history (<4 points) or the series didn't move; inf when a perfectly
    flat series moves at all (so it ranks first but never reaches the JSON)."""
    if not sparkline or len(sparkline) < 4:
        return None
    steps = [sparkline[i] - sparkline[i - 1] for i in range(1, len(sparkline))]
    latest = steps[-1]
    if latest == 0:
        return None
    vol = statistics.pstdev(steps[:-1])  # volatility of the PRIOR steps
    if vol == 0:
        return float("inf")
    return abs(latest) / vol


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
_GLOBAL_SLUGS = {
    "global-dollar-currencies": "dollar-currencies",
    "global-growth": "growth",
    "global-trade-supply": "trade-supply",
    "global-uncertainty": "uncertainty",
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
    if category == "global":
        return f"/dashboards/global/{_GLOBAL_SLUGS.get(lens_id, lens_id)}.html"
    return "/dashboards/"


# Category order for the brief (drives tie-break ordering only).
CATEGORIES = ["economic", "consumer", "banking", "markets", "energy", "housing", "global"]


def _flatten_lenses(category_indices):
    """Flatten {category: index_json} into a list of lens records carrying
    category, href, status, headline, key_stats, and sparkline."""
    flat = []
    for category in CATEGORIES:
        index = category_indices.get(category)
        if not index:
            continue
        for lens in index.get("lenses", []):
            lens_id = lens.get("id")
            if not lens_id:  # a lens with no id can't be linked or keyed — skip it
                continue
            flat.append({
                "lens_id": lens_id,
                "lens_title": lens.get("title", ""),
                "category": category,
                "href": lens_href(category, lens_id),
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


MOVE_THRESHOLD_SIGMA = 1.0  # ignore moves smaller than ~1 typical step (noise floor)


def rank_moves(flat_lenses, transition_ids, limit=5):
    """Up to `limit` non-transition lenses ranked by the significance of the
    primary indicator's latest move (move_score, descending), keeping only moves
    of at least MOVE_THRESHOLD_SIGMA. Carries the first key_stat's display fields
    straight through. The score is used only for ranking — it never reaches the
    output (so a flat-series inf can't produce invalid JSON)."""
    scored = []
    for r in flat_lenses:
        if r["lens_id"] in transition_ids:
            continue
        score = move_score(r["sparkline"])
        if score is None or score < MOVE_THRESHOLD_SIGMA:
            continue
        stat = (r["key_stats"] or [{}])[0]
        scored.append((score, {
            "lens_id": r["lens_id"],
            "lens_title": r["lens_title"],
            "category": r["category"],
            "href": r["href"],
            "stat_label": stat.get("k", ""),
            "stat_value": stat.get("v", "—"),
            "delta": stat.get("d", ""),
            "dir": stat.get("dir", ""),
        }))
    scored.sort(key=lambda x: -x[0])
    return [move for _, move in scored[:limit]]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _status_counts(flat_lenses):
    counts = {"ok": 0, "watch": 0, "elevated": 0, "alert": 0, "neutral": 0}
    for r in flat_lenses:
        s = r["status"]
        if s in counts:
            counts[s] += 1
    return counts


def build_brief(category_indices, prior_state):
    """Assemble (today_json, new_state) from per-category index data and the
    prior state. prior_state shape: {"statuses": {lens_id: status}}."""
    prior_statuses = (prior_state or {}).get("statuses", {})
    flat = _flatten_lenses(category_indices)

    transitions = detect_transitions(prior_statuses, flat)
    transition_ids = {t["lens_id"] for t in transitions}
    moves = rank_moves(flat, transition_ids, limit=max(0, 5 - len(transitions)))

    today = {
        "generated_at": _now(),
        "transitions": transitions,
        "top_moves": moves,
        # Every lens (id/title/category/href/status), so the brief page can group
        # and deep-link without re-deriving the slug maps client-side.
        "lenses": [{"lens_id": r["lens_id"], "lens_title": r["lens_title"],
                    "category": r["category"], "href": r["href"], "status": r["status"]}
                   for r in flat],
        "status_counts": _status_counts(flat),
    }
    new_state = {"captured_at": today["generated_at"],
                 "statuses": {r["lens_id"]: r["status"] for r in flat}}
    return today, new_state

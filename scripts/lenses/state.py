"""The State of Things: one consolidated read over the per-category indexes —
an overall verdict (status token + one assembled plain-English sentence),
pressure points, a holding-steady roll-up, and a pointer into Today's Brief.
Pure synthesis like brief.py — callers pass data in and get data out (no
network, no disk I/O). Editorial rules and the copy bank are specified in
docs/superpowers/specs/2026-06-11-state-of-things-design.md."""

import zlib
from datetime import datetime, timezone

from . import brief, config, util

PRESSURE_STATUSES = ("elevated", "alert")

# Display titles come from the pipeline's single source of truth.
TITLES = {c["id"]: c["title"] for c in config.CATEGORIES}

# --- Copy bank (reviewed by Michael with the spec; edit there first) ---

# Short noun phrases for naming a category mid-sentence (watch lists).
NOUN = {
    "economic": "the core economy",
    "consumer": "household finances",
    "banking": "the banks",
    "business": "business health",
    "markets": "markets",
    "energy": "energy costs",
    "housing": "housing",
    "global": "the global backdrop",
}

# Clause naming a category under pressure, keyed by its blended status. These
# describe the CATEGORY badge (the precise lens headlines appear verbatim in
# the Pressure Points block, so the sentence stays at category altitude).
PRESSURE_CLAUSES = {
    "economic": {"elevated": "the core economy is under real strain",
                 "alert": "the core economy is flashing serious warnings"},
    "consumer": {"elevated": "household finances are stretched thin",
                 "alert": "households are in real distress"},
    "banking": {"elevated": "cracks are showing in the banking system",
                "alert": "the banking system is under serious stress"},
    "business": {"elevated": "business health is deteriorating",
                 "alert": "corporate America is in real trouble"},
    "markets": {"elevated": "financial markets are under stress",
                "alert": "financial markets are in turmoil"},
    "energy": {"elevated": "energy and commodity costs are squeezing budgets",
               "alert": "energy and commodity costs are surging"},
    "housing": {"elevated": "the housing market is out of balance",
                "alert": "the housing market is in serious trouble"},
    "global": {"elevated": "the global backdrop is turning hostile",
               "alert": "the global economy is in serious stress"},
}

# Clause naming a steady category (the sentence's reassurance).
STEADY_CLAUSES = {
    "banking": "banks are solid",
    "markets": "markets are calm",
    "economic": "the core economy is steady",
    "business": "business health is holding up",
    "consumer": "households are keeping pace",
    "housing": "housing is balanced",
    "energy": "energy costs are behaving",
    "global": "the global backdrop is quiet",
}

# Most-reassuring-first order for picking the steady anchors named in the sentence.
ANCHOR_PRIORITY = ["banking", "markets", "economic", "business",
                   "consumer", "housing", "energy", "global"]

# Skeletons per shape, 3 rotating variants each. Slots: {p} pressure clauses,
# {a} anchor clause, {w} watch nouns ({thing}/{is}/{lone} agree in number).
# Shapes whose slot can be empty carry a fallback template; the rotation picks
# the variant, the data picks the template within it.
SKELETONS = {
    "all-clear": [
        {"watch": "The economy reads broadly healthy: {a}, with {w} the only {thing} worth watching.",
         "no_watch": "The economy reads broadly healthy: {a} — nothing on the board is flashing."},
        {"watch": "A calm read across the board — {a}; the only {thing} worth watching {is} {w}.",
         "no_watch": "A calm read across the board — {a}; nothing is flashing."},
        {"watch": "Most everything reads steady right now: {a}; {w} {is} {lone}.",
         "no_watch": "Most everything reads steady right now: {a}, with no watch items on the board."},
    ],
    "mixed-watch": [
        {"a": "Nothing is flashing red, but several corners bear watching — {w} — while {a}.",
         "no_a": "Nothing is flashing red, but several corners bear watching: {w}."},
        {"a": "A wait-and-see picture: {a}, but {w} all bear watching.",
         "no_a": "A wait-and-see picture: {w} all bear watching."},
        {"a": "Steady on the surface with caution underneath — {a}, while {w} warrant attention.",
         "no_a": "Caution across the board — {w} all warrant attention."},
    ],
    "contained-pressure": [
        {"a": "The economy is holding up, but not without strain: {p}, while {a}.",
         "no_a": "The economy is holding up, but not without strain — {p}, and the rest bears watching."},
        {"a": "Pressure is real but contained: {p}; meanwhile {a}.",
         "no_a": "Pressure is real but contained: {p}; the rest of the board bears watching."},
        {"a": "Most of the economy is on solid footing — {a} — but {p}.",
         "no_a": "Little of the board is fully in the clear — {p}, and the rest bears watching."},
    ],
    "spreading-stress": [
        {"a": "Stress is spreading: {p}; {a}.",
         "no_a": "Stress is spreading: {p}, and little of the board reads steady."},
        {"a": "The strain is no longer contained — {p} — and the steady list is getting shorter; for now {a}.",
         "no_a": "The strain is no longer contained — {p} — and the steady list has run out."},
        {"a": "More of the economy is under strain than not: {p}; the relative bright spots: {a}.",
         "no_a": "More of the economy is under strain than not: {p}, with no real bright spots."},
    ],
    "broad-stress": [
        {"p": "Serious stress across the economy: {p}."},
        {"p": "The board is mostly red — {p} — and safe harbors are scarce."},
        {"p": "A genuinely bad stretch: {p}, and almost nothing on the board reads steady."},
    ],
}


def _join(items):
    """Oxford-comma list join: a / a and b / a, b, and c."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def classify_shape(overall, has_pressure):
    """Map the overall token (+ whether any category is elevated/alert) to the
    sentence shape. Complete partition: overall ok mathematically excludes any
    pressure category (one elevated among eight already blends to watch)."""
    if overall == "alert":
        return "broad-stress"
    if overall == "elevated":
        return "spreading-stress"
    if overall == "watch":
        return "contained-pressure" if has_pressure else "mixed-watch"
    return "all-clear"


def _variant(iso_date, shape):
    """Deterministic daily rotation: same sentence all day (no intraday commit
    churn), varies across days, reproducible for any given date."""
    return zlib.crc32(iso_date.encode("utf-8")) % len(SKELETONS[shape])


def _sentence(shape, variant_idx, p_clauses, anchor, watch_nouns):
    """Fill the chosen skeleton. p_clauses/watch_nouns are ordered lists of
    lowercase fragments; anchor is a pre-joined clause ('' when no category is
    ok, which selects the variant's fallback template)."""
    tpl = SKELETONS[shape][variant_idx]
    p = _join(p_clauses)
    w = _join(watch_nouns)
    if shape == "broad-stress":
        return tpl["p"].format(p=p)
    if shape in ("contained-pressure", "spreading-stress"):
        return tpl["a"].format(p=p, a=anchor) if anchor else tpl["no_a"].format(p=p)
    if shape == "mixed-watch":
        return tpl["a"].format(w=w, a=anchor) if anchor else tpl["no_a"].format(w=w)
    # all-clear: an ok category always exists (RMS < 0.6 forces at least one 0),
    # so the anchor is never empty here — only the watch slot varies.
    if not watch_nouns:
        return tpl["no_watch"].format(a=anchor)
    n = len(watch_nouns)
    fields = {"a": anchor, "w": w,
              "thing": "thing" if n == 1 else "things",
              "is": "is" if n == 1 else "are",
              "lone": "the lone watch item" if n == 1 else "the watch items"}
    return tpl["watch"].format(**fields)


MIN_CATEGORIES = 4
INSUFFICIENT_SENTENCE = "Not enough data to read the overall picture right now."
PRESSURE_CAP = 3          # categories in the Pressure Points block
LENSES_PER_PRESSURE = 2   # worst lenses quoted per pressure category
# Contained keeps the sentence tight (2 clauses); other shapes use the full
# pressure list, which PRESSURE_CAP already bounds.
CLAUSE_CAP = {"contained-pressure": 2}
ANCHOR_CAP = 2            # steady clauses named in the sentence
WATCH_NOUN_CAP = 4        # watch categories named in mixed-watch sentences
BRIEF_HREF = "/dashboards/brief.html"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _categories(category_indices):
    """Flatten {category: index_json} into canonical-order records. The blend
    is recomputed from lens statuses when an index lacks the baked category
    status (stale index or fixture) — mirrors the home page's fallback."""
    cats = []
    for cid in brief.CATEGORIES:
        index = category_indices.get(cid)
        if not index:
            continue
        lenses = [l for l in index.get("lenses", []) if l.get("id")]
        statuses = [l.get("status", "unknown") for l in lenses]
        cats.append({
            "category": cid,
            "title": TITLES.get(cid, cid),
            "status": index.get("status") or util.status_blend(statuses),
            "href": f"/dashboards/{cid}/",
            "score": util.status_score(statuses) or 0.0,
            "lenses": lenses,
        })
    return cats


def _public(cat):
    return {"category": cat["category"], "title": cat["title"],
            "status": cat["status"], "href": cat["href"]}


def _worst_lenses(cat):
    """The lens cards a pressure category wears: worst first, capped, with the
    verbatim headline_read and the shared slug logic for hrefs. Only stressed
    lenses (watch+) qualify — an ok lens never explains a pressure point."""
    sev = [l for l in cat["lenses"] if util.STATUS_ORDER.get(l.get("status"), -1) >= 1]
    sev.sort(key=lambda l: -util.STATUS_ORDER[l["status"]])  # stable: config order ties
    return [{"id": l["id"], "title": l.get("title", ""), "status": l["status"],
             "headline": l.get("headline_read", ""),
             "href": brief.lens_href(cat["category"], l["id"])}
            for l in sev[:LENSES_PER_PRESSURE]]


def _steady(cats, pressure_ids):
    """Everything not under pressure — watch first (most interesting), then the
    rest, canonical order within each group."""
    rest = [c for c in cats if c["category"] not in pressure_ids]
    return ([_public(c) for c in rest if c["status"] == "watch"]
            + [_public(c) for c in rest if c["status"] != "watch"])


def _pressure_clause(cat):
    clause = PRESSURE_CLAUSES.get(cat["category"], {}).get(cat["status"])
    # Unauthored copy (a brand-new category) degrades to generic copy, never a
    # crash. Phrased so the noun is never the subject — grammatical whether the
    # noun phrase is singular or plural ("housing" / "household finances").
    return clause or f"stress is showing in {NOUN.get(cat['category'], cat['title'].lower())}"


def _steady_clause(cat):
    return (STEADY_CLAUSES.get(cat["category"])
            or f"conditions are steady in {NOUN.get(cat['category'], cat['title'].lower())}")


WATCHING_CAP = 3


def build_watching(open_predictions):
    """'What we're watching next': up to 3 open predictions ranked by
    consequence — predicted badge changes first (alert-ward before ok-ward,
    bigger jumps first), then nearest-due. Spec: predictions design §7."""
    from . import build as _build  # _fmt: keep hub/page formatting identical
    sev = util.STATUS_ORDER

    def _is_change(p):
        return (p.get("implied_status") != p.get("current_status")
                and p.get("implied_status") in sev and p.get("current_status") in sev)

    def _rank(p):
        if _is_change(p):
            dist = sev[p["implied_status"]] - sev[p["current_status"]]
            # alert-ward (positive dist) first, bigger jumps first, then due
            return (0, 0 if dist > 0 else 1, -abs(dist), p.get("due") or "9999")
        return (1, 0, 0, p.get("due") or "9999")

    ranked = sorted((p for p in open_predictions or []), key=_rank)[:WATCHING_CAP]
    return [{
        "key": p["key"], "indicator": p["indicator"], "lens": p["lens"],
        "category": p["category"], "title": p.get("title", ""),
        "lens_title": p.get("lens_title", ""), "due": p.get("due"),
        "point_fmt": _build._fmt(p.get("point"), p.get("unit", ""),
                                 p.get("value_format", "decimal")),
        "implied_status": p.get("implied_status"),
        "current_status": p.get("current_status"),
        "change": _is_change(p), "href": p.get("href", "/dashboards/"),
    } for p in ranked]


def build_state(category_indices, brief_today, open_predictions=None):
    """Assemble the State of Things JSON from per-category index data and
    today's brief (or None). Pure — no network, no disk I/O."""
    generated = _now()
    cats = _categories(category_indices)
    overall = util.status_blend([c["status"] for c in cats])

    if len(cats) < MIN_CATEGORIES or overall not in brief.SEVERITY:
        out = {"generated_at": generated,
               "verdict": {"status": "unknown", "shape": "insufficient",
                           "sentence": INSUFFICIENT_SENTENCE},
               "pressure_points": [],
               "steady": _steady(cats, set())}
    else:
        pressure = sorted([c for c in cats if c["status"] in PRESSURE_STATUSES],
                          key=lambda c: -c["score"])[:PRESSURE_CAP]
        shape = classify_shape(overall, bool(pressure))
        by_id = {c["category"]: c for c in cats}
        anchors = [cid for cid in ANCHOR_PRIORITY
                   if cid in by_id and by_id[cid]["status"] == "ok"][:ANCHOR_CAP]
        anchor = _join([_steady_clause(by_id[cid]) for cid in anchors])
        p_clauses = [_pressure_clause(c) for c in pressure[:CLAUSE_CAP.get(shape, PRESSURE_CAP)]]
        watch_nouns = [NOUN.get(c["category"], c["title"].lower())
                       for c in cats if c["status"] == "watch"][:WATCH_NOUN_CAP]
        sentence = _sentence(shape, _variant(generated[:10], shape),
                             p_clauses, anchor, watch_nouns)
        out = {"generated_at": generated,
               "verdict": {"status": overall, "shape": shape, "sentence": sentence},
               "pressure_points": [dict(_public(c), lenses=_worst_lenses(c))
                                   for c in pressure],
               "steady": _steady(cats, {c["category"] for c in pressure})}
    if brief_today and isinstance(brief_today.get("transitions"), list):
        out["changed"] = {"transitions": len(brief_today["transitions"]),
                          "href": BRIEF_HREF}
    if open_predictions:
        out["watching"] = build_watching(open_predictions)
    out["categories"] = [_public(c) for c in cats]
    return out

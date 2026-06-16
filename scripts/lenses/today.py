"""Today's Brief, merged: the brief JSON extended with the absorbed State of
Things content (verdict + watching + flat pressure rows + category roll-up
with authored tile sentences). A thin composer over the existing pure
builders — brief.build_brief supplies change detection and the flat lens
list; state.build_state supplies the verdict, watching block, and category
records. Pure like both of them — no network, no disk I/O. Spec:
docs/superpowers/specs/2026-06-11-website-revamp-design.md (§2, §12, App. A)."""

from . import brief, state, synthesis

SEVERITY = brief.SEVERITY  # ok/watch/elevated/alert ladder

# --- Tile copy bank (spec Appendix A, signed off 2026-06-12) ---
# One sentence per (category, blended status): the home tile's read, authored
# at category altitude so it can never contradict the badge it sits beside.
# elevated/alert rows reuse state.PRESSURE_CLAUSES vocabulary on purpose.
CATEGORY_SENTENCES = {
    "economic": {
        "ok": "The core economy is steady — no major warning lights.",
        "watch": "Mostly steady — a corner or two of the economy runs hot.",
        "elevated": "The core economy is under real strain.",
        "alert": "The core economy is flashing serious warnings.",
    },
    "consumer": {
        "ok": "Households are keeping pace — spending, credit, and savings look healthy.",
        "watch": "Households are keeping up, but cracks are starting to show.",
        "elevated": "Household finances are stretched thin.",
        "alert": "Households are in real distress.",
    },
    "banking": {
        "ok": "Banks are solid — capital, profits, and loan books look healthy.",
        "watch": "Banks are solid overall, but parts of the system bear watching.",
        "elevated": "Cracks are showing in the banking system.",
        "alert": "The banking system is under serious stress.",
    },
    "business": {
        "ok": "Business health is holding up — profits and investment look solid.",
        "watch": "Business health is holding up, but conditions are tightening at the margin.",
        "elevated": "Business health is deteriorating.",
        "alert": "Corporate America is in real trouble.",
    },
    "markets": {
        "ok": "Markets are calm — no stress in financial conditions.",
        "watch": "Markets are mostly calm, but a few cracks are showing.",
        "elevated": "Financial markets are under stress.",
        "alert": "Financial markets are in turmoil.",
    },
    "energy": {
        "ok": "Energy costs are behaving — no unusual pressure at the pump or on the power bill.",
        "watch": "Energy costs bear watching — some prices are drifting the wrong way.",
        "elevated": "Energy and commodity costs are squeezing budgets.",
        "alert": "Energy and commodity costs are surging.",
    },
    "housing": {
        "ok": "Housing is balanced — prices, supply, and rents read normal.",
        "watch": "Housing is mostly balanced, but parts of the market are drifting out of balance.",
        "elevated": "The housing market is out of balance.",
        "alert": "The housing market is in serious trouble.",
    },
    "global": {
        "ok": "The global backdrop is quiet — trade, growth, and currencies read calm.",
        "watch": "The global backdrop is mostly quiet, but risks are ticking up.",
        "elevated": "The global backdrop is turning hostile.",
        "alert": "The global economy is in serious stress.",
    },
}


def _sentence(cat):
    """Authored sentence for a category record; a new category or a non-severity
    status degrades to generic copy, never a crash or an empty tile."""
    authored = CATEGORY_SENTENCES.get(cat["category"], {}).get(cat["status"])
    return authored or f"{cat['title']} reads {cat['status']} right now."


def build_today(category_indices, prior_state, open_predictions=None):
    """Assemble (today_json, new_state). today_json is brief.build_brief's
    output with the absorbed state content added beside it — existing keys
    keep their shape so feed.build_item and the strip/panel renderers read
    the file unchanged. new_state is the brief's transition memory."""
    brief_today, new_state = brief.build_brief(category_indices, prior_state)
    try:
        state_today = state.build_state(category_indices, brief_today,
                                        open_predictions=open_predictions)
    except Exception:  # noqa: BLE001 - the verdict is additive; never lose the brief
        # The renderers all guard on the merged keys, so a brief without them
        # still publishes today's transitions/movers instead of going stale.
        return dict(brief_today), new_state

    pressure = [dict(r) for r in brief_today["lenses"]
                if SEVERITY.get(r["status"], 0) >= 1]
    pressure.sort(key=lambda r: (-SEVERITY[r["status"]],
                                 brief.CATEGORIES.index(r["category"])))

    today_json = dict(brief_today)
    today_json.update({
        "verdict": state_today["verdict"],
        "watching": state_today.get("watching", []),
        "pressure": pressure,
        "categories": [dict(c, sentence=_sentence(c))
                       for c in state_today["categories"]],
    })
    _attach_synthesis(today_json, pressure)
    return today_json, new_state


def _attach_synthesis(today_json, pressure):
    """Add the synthesis layer (spec 2026-06-16): a self-grounded 'why' per mover
    and a structural co-occurrence read. Guarded — a synthesis hiccup must never
    lose the day's brief, so it degrades to no-why / no-synthesis. The relationship
    NARRATIVE is deferred (spec §6): the engine is wired but the authored map is
    not yet shipped, so `relationships` stays []."""
    try:
        today_json["top_moves"] = [dict(m, why=synthesis.mover_why(m))
                                   for m in today_json.get("top_moves", [])]
        today_json["synthesis"] = {
            "cooccurrence": synthesis.cooccurrence(pressure),
            "relationships": [],  # deferred: authored map pending (spec §6)
        }
    except Exception:  # noqa: BLE001 - synthesis is additive; never lose the brief
        today_json.setdefault("synthesis", {"cooccurrence": "", "relationships": []})

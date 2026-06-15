"""Which indicators get predictions: derived from lenses.config by rule.

Rule (spec 2026-06-15-predictions-coverage §2): we forecast nearly every
published series, badge-driving or not — coverage and badge-scoring are
orthogonal. Rostered iff the indicator's source is fred/eia with a real
fetchable route, its lens is not neutral (asset scoreboard / crypto), its
category is not banking (quarterly FDIC — needs FDIC fetch plumbing, deferred),
and it isn't an asset/market *price* (FX, commodity indices — the contested
Tier C, gated below). Info-only ("descriptive") series ARE rostered now and
flagged `descriptive=True`; we forecast them without claiming a badge."""

from dataclasses import dataclass

from lenses import config, narrative

# Hand exclusions for anything the rules can't express. Keep commented.
EXTRA_EXCLUDE = {
    # e.g. "economic/cost-of-money/fed-funds",
}

# Market/asset *prices* that happen to carry an info rule: FX rates and
# commodity-price indices. Forecastable, but near-random-walk and a dated public
# number reads as a price target — same integrity question as the scoreboard
# (see spec §4, DECISIONS-PENDING #1). Excluded pending Michael's asset-price
# call; enabling Tier C = empty this set (and lift the NEUTRAL_LENSES skip).
ASSET_PRICE_LIKE = {
    "global/global-dollar-currencies/euro",
    "global/global-dollar-currencies/yen",
    "global/global-dollar-currencies/yuan",
    "energy/energy-commodities/copper",
    "energy/energy-commodities/broad-commodities",
}


# Synthetic probe series: 40 years of monthly dates, gently trending + wavy so
# level/YoY/trend rules all see plausible numbers. Only the *status token* is
# inspected; info rules return "info" regardless of values.
def _probe_obs():
    out = []
    for i in range(480):
        year, month = 1986 + i // 12, 1 + i % 12
        out.append((f"{year:04d}-{month:02d}-01", 100.0 + i * 0.1 + (i % 7) * 0.3))
    return out


def _is_info_rule(rule):
    try:
        _, status = rule(_probe_obs())
    except Exception:  # noqa: BLE001 - a crashing probe never blocks the roster
        return False
    return status == "info"


@dataclass(frozen=True)
class RosterEntry:
    key: str          # "category/lens-id/indicator-id"
    category: str
    lens_id: str
    indicator: object  # the lenses.config Indicator
    descriptive: bool = False  # info-only series: forecast it, but it carries no badge


def build_roster():
    entries = []
    for cat in config.CATEGORIES:
        if cat["id"] == "banking":
            continue
        for lens in cat["lenses"]:
            if lens.id in narrative.NEUTRAL_LENSES:
                continue
            for ind in lens.indicators:
                if ind.source not in ("fred", "eia"):
                    continue
                if ind.source == "eia" and not ind.eia_route:
                    continue  # computed/injected (generation shares)
                key = f"{cat['id']}/{lens.id}/{ind.id}"
                if key in EXTRA_EXCLUDE or key in ASSET_PRICE_LIKE:
                    continue
                # Info-only series are now rostered (coverage != scoring); we tag
                # them descriptive so the surfaces don't imply a badge for them.
                entries.append(RosterEntry(key, cat["id"], lens.id, ind,
                                           descriptive=_is_info_rule(ind.rule)))
    return entries

"""Which indicators get predictions: derived from lenses.config by rule.

Rule (spec §2): we predict what can move a badge. Rostered iff the indicator's
source is fred/eia with a real fetchable route, its rule can emit severity
statuses (probed — info-only rules always return "info"), its lens is not
neutral, and its category is not banking (quarterly FDIC, deferred)."""

from dataclasses import dataclass

from lenses import config, narrative

# Hand exclusions for anything the rules can't express. Keep commented.
EXTRA_EXCLUDE = {
    # e.g. "economic/cost-of-money/fed-funds",
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
                if key in EXTRA_EXCLUDE:
                    continue
                if _is_info_rule(ind.rule):
                    continue
                entries.append(RosterEntry(key, cat["id"], lens.id, ind))
    return entries

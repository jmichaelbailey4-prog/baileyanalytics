"""Which indicators get predictions: derived from lenses.config by rule.

Rule (spec 2026-06-15-predictions-coverage): we forecast nearly every published
series, badge-driving or not — coverage and badge-scoring are orthogonal. As of
2026-06-15 (Michael: predict everything, even neutral / info-only) the only
hold-outs are the ones we can't yet *fetch* or honestly grade:
  - banking (quarterly FDIC) — needs FDIC fetch plumbing (next increment);
  - computed / injected series (rate-expectations spread, profit-share, …) and
    crypto-structure (CoinGecko, accumulated history) — not a plain fetch;
  - non-FRED/EIA/Yahoo sources (IMF annual — infeasible; GSCPI, EPU) — need
    fetch plumbing;
  - EIA series with no route (generation shares — computed).
Each rostered entry is flagged `descriptive` (carries no badge: info-only OR a
neutral lens) and `market_price` (a tradeable price: the scoreboard, FX, or a
commodity index — gets a not-investment-advice note on the surface and is held
out of the headline *edge* stat)."""

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
    descriptive: bool = False    # carries no badge (info-only or a neutral lens)
    market_price: bool = False   # a tradeable price (scoreboard / FX / commodity index)


def build_roster():
    entries = []
    for cat in config.CATEGORIES:
        if cat["id"] == "banking":
            continue
        for lens in cat["lenses"]:
            neutral = lens.id in narrative.NEUTRAL_LENSES
            for ind in lens.indicators:
                if ind.source not in ("fred", "eia", "yahoo"):
                    continue  # coingecko/computed/imf/nyfed/epu: not a plain fetch
                if ind.source == "eia" and not ind.eia_route:
                    continue  # computed/injected (generation shares)
                key = f"{cat['id']}/{lens.id}/{ind.id}"
                if key in EXTRA_EXCLUDE:
                    continue
                entries.append(RosterEntry(
                    key, cat["id"], lens.id, ind,
                    descriptive=neutral or _is_info_rule(ind.rule),
                    market_price=neutral or ind.market_price))
    return entries

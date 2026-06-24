"""Which indicators get predictions: derived from lenses.config by rule.

Rule (spec 2026-06-15-predictions-coverage): we forecast nearly every published
series, badge-driving or not — coverage and badge-scoring are orthogonal. As of
2026-06-15 (Michael: predict everything, even neutral / info-only) we cover both
the series predict.py fetches directly (fred/eia/yahoo) AND the ones it can only
read from their already-baked lens JSON (`baked` below): banking (quarterly
FDIC), the computed spreads (rate-expectations, profit-share, hp-share), GSCPI
(NYFed) and EPU. The remaining hold-outs can't be honestly graded:
  - IMF (annual) — too few backtest origins to earn an empirical 80% band;
  - crypto-structure (CoinGecko) — built outside config.CATEGORIES, too little
    accumulated history;
  - EIA series with no route (generation shares — computed/injected).
Each rostered entry is flagged `descriptive` (carries no badge: info-only OR a
neutral lens), `market_price` (a tradeable price: the scoreboard, FX, or a
commodity index — gets a not-investment-advice note on the surface and is held
out of the headline *edge* stat), and `baked` (read from the lens JSON rather
than fetched — the runner must NOT re-apply ind.derive to these)."""

from dataclasses import dataclass

from lenses import config, narrative

# predict.py fetches these live; everything else is read from the baked lens
# JSON. IMF (annual) and CoinGecko (crypto-structure) stay out entirely.
DIRECT_SOURCES = ("fred", "eia", "yahoo")
BAKED_SOURCES = ("fdic", "computed", "nyfed", "epu")

# Hand exclusions for anything the rules can't express. Keep commented.
EXTRA_EXCLUDE = {
    # e.g. "economic/cost-of-money/fed-funds",
}


@dataclass(frozen=True)
class RosterEntry:
    key: str          # "category/lens-id/indicator-id"
    category: str
    lens_id: str
    indicator: object  # the lenses.config Indicator (or BankingIndicator)
    descriptive: bool = False    # carries no badge (info-only or a neutral lens)
    market_price: bool = False   # a tradeable price (scoreboard / FX / commodity index)
    baked: bool = False          # read from the lens JSON; runner must not re-derive


def build_roster():
    entries = []
    for cat in config.CATEGORIES:
        for lens in cat["lenses"]:
            neutral = lens.id in narrative.NEUTRAL_LENSES
            for ind in lens.indicators:
                if not config.is_predictable(ind):
                    continue  # imf (annual) / coingecko / computed-injected shares
                key = f"{cat['id']}/{lens.id}/{ind.id}"
                if key in EXTRA_EXCLUDE:
                    continue
                entries.append(RosterEntry(
                    key, cat["id"], lens.id, ind,
                    descriptive=neutral or narrative.rule_kind(ind.rule) == "info",
                    # market_price travels on the config Indicator (1deeb0d); banking's
                    # BankingIndicator has no such field, so read it defensively.
                    market_price=neutral or getattr(ind, "market_price", False),
                    baked=ind.source in BAKED_SOURCES))
    return entries

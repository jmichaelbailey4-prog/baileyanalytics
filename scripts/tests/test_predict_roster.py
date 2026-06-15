import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import roster  # noqa: E402


class TestRoster(unittest.TestCase):
    def setUp(self):
        self.entries = roster.build_roster()
        self.keys = {e.key for e in self.entries}

    def test_severity_fred_indicators_included(self):
        self.assertIn("economic/cost-of-living/cpi", self.keys)
        self.assertIn("economic/recession-watch/jobless-claims", self.keys)
        self.assertIn("markets/market-risk-sentiment/hy-spread", self.keys)
        self.assertIn("housing/housing-affordability/mortgage-rate", self.keys)

    def test_scoreboard_now_predicted_and_flagged(self):
        # Michael 2026-06-15: predict everything, even neutral. The scoreboard
        # (S&P/oil/gold/BTC/ETH) is now rostered, flagged descriptive (no badge)
        # and market_price (gets the not-advice note + held out of the edge stat).
        by_key = {e.key: e for e in self.entries}
        for ind_id in ("sp500", "oil", "gold", "btc", "eth"):
            e = by_key.get(f"markets/market-scoreboard/{ind_id}")
            self.assertIsNotNone(e, ind_id)
            self.assertTrue(e.descriptive and e.market_price, ind_id)

    def test_yahoo_gold_included(self):
        gold = next(e for e in self.entries if e.key == "markets/market-scoreboard/gold")
        self.assertEqual(gold.indicator.source, "yahoo")

    def test_crypto_structure_not_in_config_roster(self):
        # crypto-structure is built outside config.CATEGORIES, so it isn't
        # reachable here (predicting it needs CoinGecko/accumulated-history
        # plumbing — a next increment).
        self.assertFalse(any(e.lens_id == "crypto-structure" for e in self.entries))

    def test_info_macro_indicators_now_included(self):
        # Coverage != scoring (spec 2026-06-15-predictions-coverage §2): info-only
        # macro/physical series are forecast descriptively, not excluded.
        for key in ("markets/market-liquidity/fed-balance-sheet",
                    "markets/market-liquidity/bank-reserves",
                    "economic/fiscal-health/receipts",
                    "energy/energy-oil-fuels/crude-stocks",
                    "housing/housing-rent-shelter/homeownership"):
            self.assertIn(key, self.keys)

    def test_info_indicators_flagged_descriptive(self):
        # The info-only ones carry descriptive=True; badge-driving ones don't.
        by_key = {e.key: e for e in self.entries}
        self.assertTrue(by_key["markets/market-liquidity/fed-balance-sheet"].descriptive)
        self.assertFalse(by_key["economic/cost-of-living/cpi"].descriptive)

    def test_market_price_series_predicted_and_flagged(self):
        # FX rates + commodity-price indices are forecast too, flagged
        # market_price (via the config Indicator field) so they get the
        # disclaimer and are held out of the edge stat.
        by_key = {e.key: e for e in self.entries}
        for key in ("global/global-dollar-currencies/euro",
                    "global/global-dollar-currencies/yen",
                    "global/global-dollar-currencies/yuan",
                    "energy/energy-commodities/copper",
                    "energy/energy-commodities/broad-commodities"):
            self.assertIn(key, self.keys)
            self.assertTrue(by_key[key].market_price, key)

    def test_market_price_flag_comes_from_config(self):
        # The flag travels with the series definition (config.py is the single
        # source of truth) — not a hardcoded key-set in the roster module.
        self.assertFalse(hasattr(roster, "ASSET_PRICE_LIKE"))
        by_key = {e.key: e for e in self.entries}
        self.assertFalse(by_key["economic/cost-of-living/cpi"].market_price)

    def test_banking_and_non_fetchable_sources_excluded(self):
        self.assertFalse(any(e.category == "banking" for e in self.entries))
        # predict.py can fetch fred/eia/yahoo; coingecko/computed/imf/nyfed/epu
        # need plumbing and stay out for now.
        for e in self.entries:
            self.assertIn(e.indicator.source, ("fred", "eia", "yahoo"))

    def test_computed_eia_routes_excluded(self):
        # renewables-share etc. have no eia_route; they're injected/computed
        for e in self.entries:
            if e.indicator.source == "eia":
                self.assertTrue(e.indicator.eia_route)

    def test_duplicate_series_kept_per_lens_home(self):
        # unemployment appears in recession-watch AND job-market; both are
        # legitimate display homes — each gets its own (identical) prediction.
        self.assertIn("economic/recession-watch/unemployment", self.keys)
        self.assertIn("economic/job-market/unemployment", self.keys)

    def test_roster_is_reasonably_sized(self):
        # ~92 after full coverage (59 badge-drivers + ~23 info macro + scoreboard
        # + FX + commodities); guard both that the extension landed and that we
        # didn't accidentally sweep in banking / non-fetchable sources.
        self.assertGreater(len(self.entries), 85)
        self.assertLess(len(self.entries), 105)

    def test_keys_unique(self):
        self.assertEqual(len(self.keys), len(self.entries))


if __name__ == "__main__":
    unittest.main()

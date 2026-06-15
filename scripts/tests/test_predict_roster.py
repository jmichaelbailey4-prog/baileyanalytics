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

    def test_banking_and_computed_now_rostered_via_baked_history(self):
        # Coverage extension 2026-06-15 (spec §3/§5 Q2-Q4): banking (FDIC) plus
        # computed/nyfed/epu series can't be fetched directly, but the pipeline
        # already bakes their history into the lens JSON. We read that, so they
        # join the roster flagged `baked`. Banking is badge-driving SIGNAL.
        by_key = {e.key: e for e in self.entries}
        self.assertTrue(any(e.category == "banking" for e in self.entries))
        nq = by_key["banking/bank-asset-quality/noncurrent"]
        self.assertTrue(nq.baked)
        self.assertFalse(nq.descriptive)    # severity badge-driver -> counts toward edge
        self.assertFalse(nq.market_price)
        for key in ("economic/cost-of-money/rate-expectations",
                    "business/business-profitability/profit-share",
                    "business/business-formation/hp-share",
                    "global/global-trade-supply/gscpi",
                    "global/global-uncertainty/us-epu",
                    "global/global-uncertainty/gepu"):
            self.assertIn(key, self.keys)
            self.assertTrue(by_key[key].baked, key)

    def test_direct_fetch_sources_not_flagged_baked(self):
        by_key = {e.key: e for e in self.entries}
        self.assertFalse(by_key["economic/cost-of-living/cpi"].baked)   # fred
        self.assertFalse(by_key["markets/market-scoreboard/gold"].baked)  # yahoo

    def test_imf_and_coingecko_still_excluded(self):
        # IMF is annual (can't earn an empirical 80% band from ~5 backtest
        # origins); crypto-structure (CoinGecko) lives outside config.CATEGORIES
        # and has too little baked history. Both correctly deferred.
        for e in self.entries:
            self.assertNotIn(e.indicator.source, ("imf", "coingecko"))
        self.assertFalse(any(e.lens_id == "crypto-structure" for e in self.entries))

    def test_all_baked_indicators_have_a_lens_file_to_read(self):
        # the read path resolves category -> out dir -> lens-id file; assert the
        # mapping holds for every baked entry so a live run never KeyErrors.
        import os
        from lenses import config
        out = {c["id"]: c["out"] for c in config.CATEGORIES}
        for e in self.entries:
            if e.baked:
                path = os.path.join("data", out[e.category], f"{e.lens_id}.json")
                self.assertTrue(os.path.exists(path), path)

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
        # 107 after the baked-history extension: 92 directly-fetchable + 9 banking
        # + 3 computed (rate-expectations, profit-share, hp-share) + GSCPI + 2 EPU.
        # A change here means recount coverage (and update the spec/memory).
        self.assertEqual(len([e for e in self.entries if e.category == "banking"]), 9)
        self.assertEqual(len(self.entries), 107)

    def test_keys_unique(self):
        self.assertEqual(len(self.keys), len(self.entries))


if __name__ == "__main__":
    unittest.main()

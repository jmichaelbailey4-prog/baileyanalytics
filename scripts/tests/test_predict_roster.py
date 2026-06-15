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

    def test_neutral_lenses_excluded(self):
        self.assertFalse(any(e.lens_id in ("market-scoreboard", "crypto-structure")
                             for e in self.entries))

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

    def test_asset_price_like_info_series_still_excluded(self):
        # FX rates + commodity-price indices read as price targets — held out
        # pending the asset-price decision (spec §4, DECISIONS-PENDING #1).
        for key in roster.ASSET_PRICE_LIKE:
            self.assertNotIn(key, self.keys)

    def test_banking_and_non_fred_eia_excluded(self):
        self.assertFalse(any(e.category == "banking" for e in self.entries))
        for e in self.entries:
            self.assertIn(e.indicator.source, ("fred", "eia"))

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
        # ~82 after the Tier A coverage extension (59 badge-drivers + ~23 info
        # macro series); guard both that the extension landed and that we didn't
        # accidentally sweep in banking / asset prices / non-fetcher sources.
        self.assertGreater(len(self.entries), 70)
        self.assertLess(len(self.entries), 100)

    def test_keys_unique(self):
        self.assertEqual(len(self.keys), len(self.entries))


if __name__ == "__main__":
    unittest.main()

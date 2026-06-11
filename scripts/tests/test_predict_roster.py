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

    def test_info_indicators_excluded(self):
        self.assertNotIn("markets/market-liquidity/fed-balance-sheet", self.keys)
        self.assertNotIn("markets/market-liquidity/bank-reserves", self.keys)
        self.assertNotIn("economic/fiscal-health/receipts", self.keys)

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
        self.assertGreater(len(self.entries), 40)
        self.assertLess(len(self.entries), 110)

    def test_keys_unique(self):
        self.assertEqual(len(self.keys), len(self.entries))


if __name__ == "__main__":
    unittest.main()

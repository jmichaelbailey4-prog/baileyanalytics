import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative

class TestRateExpectations(unittest.TestCase):
    def test_deep_negative_reads_cuts(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", -1.1)])
        self.assertIn("cut", text.lower())
        self.assertEqual(status, "info")

    def test_mild_negative_leans_cuts(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", -0.4)])
        self.assertIn("lean", text.lower())
        self.assertEqual(status, "info")

    def test_near_zero_reads_hold(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", 0.05)])
        self.assertIn("hold", text.lower())
        self.assertEqual(status, "info")

    def test_positive_reads_hikes(self):
        text, status = narrative.rule_rate_expectations([("2026-06-01", 0.8)])
        self.assertIn("hike", text.lower())
        self.assertEqual(status, "info")

    def test_empty(self):
        self.assertEqual(narrative.rule_rate_expectations([]), narrative._NO_DATA)


class TestCostOfMoneyConfig(unittest.TestCase):
    def test_has_computed_spread_indicator(self):
        lens = config.COST_OF_MONEY
        self.assertEqual(len(lens.indicators), 4)
        spread = lens.indicators[-1]
        self.assertEqual(spread.id, "rate-expectations")
        self.assertEqual(spread.source, "computed")
        self.assertEqual(spread.series_id, "DGS2_FEDFUNDS_SPREAD")


if __name__ == "__main__":
    unittest.main()

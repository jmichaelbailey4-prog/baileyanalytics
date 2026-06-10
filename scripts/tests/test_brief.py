import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief


class TestPctChange(unittest.TestCase):
    def test_normal_rise(self):
        self.assertAlmostEqual(brief.pct_change([100.0, 110.0]), 10.0)

    def test_normal_fall(self):
        self.assertAlmostEqual(brief.pct_change([200.0, 150.0]), -25.0)

    def test_uses_last_two_only(self):
        self.assertAlmostEqual(brief.pct_change([1.0, 2.0, 4.0, 5.0]), 25.0)

    def test_single_point_is_none(self):
        self.assertIsNone(brief.pct_change([5.0]))

    def test_empty_is_none(self):
        self.assertIsNone(brief.pct_change([]))

    def test_zero_prior_is_none(self):
        self.assertIsNone(brief.pct_change([0.0, 3.0]))

    def test_none_arg_is_none(self):
        self.assertIsNone(brief.pct_change(None))


class TestLensHref(unittest.TestCase):
    def test_economic_is_flat_dashboards(self):
        self.assertEqual(brief.lens_href("economic", "fiscal-health"),
                         "/dashboards/fiscal-health.html")

    def test_banking_strips_bank_prefix(self):
        self.assertEqual(brief.lens_href("banking", "bank-asset-quality"),
                         "/dashboards/banking/asset-quality.html")

    def test_markets_uses_slug_map(self):
        self.assertEqual(brief.lens_href("markets", "market-risk-sentiment"),
                         "/dashboards/markets/risk-sentiment.html")
        self.assertEqual(brief.lens_href("markets", "crypto-structure"),
                         "/dashboards/markets/crypto-structure.html")

    def test_energy_uses_slug_map(self):
        self.assertEqual(brief.lens_href("energy", "energy-oil-fuels"),
                         "/dashboards/energy/oil-fuels.html")

    def test_consumer_uses_slug_map(self):
        self.assertEqual(brief.lens_href("consumer", "consumer-credit"),
                         "/dashboards/consumer/credit-stress.html")

    def test_housing_uses_slug_map(self):
        self.assertEqual(brief.lens_href("housing", "housing-home-prices"),
                         "/dashboards/housing/home-prices.html")


if __name__ == "__main__":
    unittest.main()

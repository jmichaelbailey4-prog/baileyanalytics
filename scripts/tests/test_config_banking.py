import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestBankingConfig(unittest.TestCase):
    def test_four_banking_lenses(self):
        self.assertEqual(len(config.BANKING_LENSES), 4)
        self.assertEqual(config.BANKING_LENSES[0].id, "bank-asset-quality")

    def test_indicators_are_fdic_with_metric_dicts(self):
        for lens in config.BANKING_LENSES:
            for ind in lens.indicators:
                self.assertEqual(ind.source, "fdic")
                self.assertIsInstance(ind.metric, dict)
                # each metric is either weighted-average or sum-then-ratio
                self.assertTrue(("ratio_field" in ind.metric) or ("numerator" in ind.metric))

    def test_categories_registry(self):
        ids = [c["id"] for c in config.CATEGORIES]
        self.assertIn("economic", ids)
        self.assertIn("banking", ids)
        banking = next(c for c in config.CATEGORIES if c["id"] == "banking")
        self.assertEqual(banking["out"], "banking")
        self.assertTrue(banking["disclaimer"])  # banking carries the legal disclaimer

    def test_tier_metrics_have_rules(self):
        for lens in config.BANKING_LENSES:
            for m in lens.tier_metrics:
                self.assertIn("rule", m)
                self.assertTrue(("numerator" in m) or ("ratio_field" in m))


if __name__ == "__main__":
    unittest.main()

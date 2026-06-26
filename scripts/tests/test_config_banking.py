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

    def test_cre_spotlight_requires_a_real_loan_book(self):
        # The CRE-delinquency spotlight must drop custody/processing charters whose
        # tiny loan book posts an unrepresentative delinquency ratio (e.g. State
        # Street, loans ~13% of assets) — the same loans>=40%-of-assets gate that
        # bank-profitability already uses to read as mainstream lenders.
        aq = next(l for l in config.BANKING_LENSES if l.id == "bank-asset-quality")
        rk = aq.rankings[0]
        self.assertTrue(
            any(f.get("num") == ["LNLSNET"] and f.get("den") == ["ASSET"] and f.get("min") == 0.40
                for f in rk.get("ratio_filters", [])),
            "asset-quality CRE ranking should require loans >= 40% of assets")


if __name__ == "__main__":
    unittest.main()

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative


class TestBusinessConfig(unittest.TestCase):
    def test_four_lenses(self):
        ids = [l.id for l in config.BUSINESS_LENSES]
        self.assertEqual(ids, ["business-profitability", "business-formation",
                               "business-investment", "business-credit"])

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "business")
        self.assertEqual(cat["out"], "business")
        self.assertEqual(cat["title"], "Corporate & Business Health")
        self.assertEqual(len(cat["lenses"]), 4)

    def test_every_indicator_has_rule_context_and_headline(self):
        for lens in config.BUSINESS_LENSES:
            self.assertIn(lens.id, narrative.HEADLINES)
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)

    def test_lead_indicators_first(self):
        leads = {l.id: l.indicators[0].id for l in config.BUSINESS_LENSES}
        self.assertEqual(leads, {
            "business-profitability": "profit-growth",
            "business-formation": "applications",
            "business-investment": "core-capex",
            "business-credit": "baa-spread",
        })

    def test_computed_shares_are_not_fred_fetched(self):
        import refresh_lenses
        specs = refresh_lenses.unique_specs(config.BUSINESS_LENSES)
        self.assertNotIn("CP_GDP_SHARE:lin", specs)
        self.assertNotIn("BFS_HP_SHARE:lin", specs)
        self.assertIn("CP:lin", specs)
        self.assertNotIn("GDP:lin", specs)  # GDP is share input only, no chart


if __name__ == "__main__":
    unittest.main()

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestHousingConfig(unittest.TestCase):
    def test_four_housing_lenses_in_order(self):
        ids = [l.id for l in config.HOUSING_LENSES]
        self.assertEqual(ids, ["housing-home-prices", "housing-affordability",
                               "housing-supply-construction", "housing-rent-shelter"])

    def test_all_indicators_are_fred(self):
        for lens in config.HOUSING_LENSES:
            for ind in lens.indicators:
                self.assertEqual(ind.source, "fred", ind.id)

    def test_mortgage_rate_lives_only_in_housing(self):
        # the de-dup: MORTGAGE30US must appear exactly once across all categories
        hits = []
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                for ind in lens.indicators:
                    if getattr(ind, "series_id", "") == "MORTGAGE30US":
                        hits.append(lens.id)
        self.assertEqual(hits, ["housing-affordability"])

    def test_cost_of_money_has_three_indicators(self):
        self.assertEqual(len(config.COST_OF_MONEY.indicators), 3)
        ids = [i.id for i in config.COST_OF_MONEY.indicators]
        self.assertNotIn("mortgage-30y", ids)

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "housing")
        self.assertEqual(cat["out"], "housing")
        self.assertEqual(cat["disclaimer"], "")

    def test_each_lens_has_a_severity_driver(self):
        # first indicator of each lens carries the verdict (severity token, not info)
        for lens in config.HOUSING_LENSES:
            first = lens.indicators[0]
            _, status = first.rule([("2025-01-01", 100.0), ("2026-01-01", 100.0)])
            self.assertIn(status, {"ok", "watch", "elevated", "alert"}, lens.id)


if __name__ == "__main__":
    unittest.main()

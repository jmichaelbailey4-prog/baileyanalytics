import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestEnergyConfig(unittest.TestCase):
    def test_four_energy_lenses_in_order(self):
        ids = [l.id for l in config.ENERGY_LENSES]
        self.assertEqual(ids, ["energy-oil-fuels", "energy-natural-gas",
                               "energy-electricity", "energy-commodities"])

    def test_eia_lenses_have_routes_or_computed(self):
        for lid in ("energy-oil-fuels", "energy-natural-gas", "energy-electricity"):
            lens = next(l for l in config.ENERGY_LENSES if l.id == lid)
            for ind in lens.indicators:
                self.assertEqual(ind.source, "eia")
            # at least one directly-fetched (routed) EIA indicator per lens
            self.assertTrue(any(ind.eia_route for ind in lens.indicators))

    def test_commodities_lens_is_fred(self):
        lens = next(l for l in config.ENERGY_LENSES if l.id == "energy-commodities")
        self.assertTrue(all(ind.source == "fred" for ind in lens.indicators))
        self.assertIn("PFOODINDEXM", {i.series_id for i in lens.indicators})

    def test_each_lens_has_a_severity_price_indicator(self):
        # the first indicator of each lens is the consumer-cost (severity) driver
        for lens in config.ENERGY_LENSES:
            first = lens.indicators[0]
            _, status = first.rule([("2025-01-01", 100.0), ("2026-01-01", 100.0)])
            self.assertIn(status, {"ok", "watch", "elevated", "alert"})

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "energy")
        self.assertEqual(cat["out"], "energy")
        self.assertEqual(cat["disclaimer"], "")


if __name__ == "__main__":
    unittest.main()

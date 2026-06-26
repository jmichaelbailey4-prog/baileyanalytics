"""Classification helpers that ordering + the 'why absent' notes rely on:
narrative.rule_kind (severity / info / momentum / unknown) and
config.is_predictable (the roster inclusion rule, hoisted into config)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative
from predictions.roster import build_roster


class RuleKindTest(unittest.TestCase):
    def test_severity_rule(self):
        self.assertEqual(narrative.rule_kind(narrative.rule_inflation), "severity")

    def test_info_factory_rule(self):
        self.assertEqual(narrative.rule_kind(narrative.energy_level("X")), "info")
        self.assertEqual(narrative.rule_kind(narrative.yoy_info("X")), "info")

    def test_momentum_rule(self):
        self.assertEqual(
            narrative.rule_kind(narrative.market_level("X", up=5, down=-5)), "momentum")

    def test_imf_severity_rule_is_safe_to_probe(self):
        # world_growth calls forecast(); classification must not crash and must
        # read as severity (it drives the Global Growth lead).
        self.assertEqual(
            narrative.rule_kind(narrative.world_growth(lambda: None)), "severity")


class IsPredictableTest(unittest.TestCase):
    def _ind(self, lens_id, ind_id):
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                if lens.id == lens_id:
                    for ind in lens.indicators:
                        if ind.id == ind_id:
                            return ind
        raise AssertionError(f"{lens_id}/{ind_id} not found")

    def test_fred_is_predictable(self):
        self.assertTrue(config.is_predictable(self._ind("fiscal-health", "debt-gdp")))

    def test_eia_with_route_is_predictable(self):
        self.assertTrue(config.is_predictable(self._ind("energy-oil-fuels", "gasoline")))

    def test_eia_computed_share_not_predictable(self):
        self.assertFalse(
            config.is_predictable(self._ind("energy-electricity", "renewables-share")))

    def test_imf_not_predictable(self):
        self.assertFalse(config.is_predictable(self._ind("global-growth", "world-growth")))

    def test_computed_spread_is_predictable(self):
        self.assertTrue(
            config.is_predictable(self._ind("cost-of-money", "rate-expectations")))


class RosterParityTest(unittest.TestCase):
    def test_membership_matches_is_predictable(self):
        roster_keys = {e.key for e in build_roster()}
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                for ind in lens.indicators:
                    key = f"{cat['id']}/{lens.id}/{ind.id}"
                    self.assertEqual(
                        key in roster_keys, config.is_predictable(ind), key)


if __name__ == "__main__":
    unittest.main()

"""Severity rules carry a .band_spec built from their real thresholds.
(The exhaustive, drift-locking probe of every live rule is test_bands.py.)"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative  # noqa: E402


class TestFactorySpecs(unittest.TestCase):
    def test_restrictive_rate(self):
        r = narrative.restrictive_rate("The 10-year Treasury", 4.5, 5.5)
        self.assertEqual(r.band_spec.kind, "level")
        self.assertEqual(r.band_spec.edges, (4.5, 5.5))
        self.assertEqual(r.band_spec.segments, ("ok", "watch", "elevated"))
        self.assertEqual(r.band_tag, "restrictive_rate")

    def test_consumer_cost(self):
        r = narrative.consumer_cost("Gasoline", 10, 25, 40)
        self.assertEqual(r.band_spec.kind, "yoy_computed")
        self.assertEqual(r.band_spec.edges, (10, 25, 40))
        self.assertEqual(r.band_spec.segments, ("ok", "watch", "elevated", "alert"))

    def test_yoy_band_two_sided_sorted_edges(self):
        r = narrative.yoy_band_two_sided("Retail sales", hot=(8, 15, 25), cold=(-1, -4, -8))
        self.assertEqual(r.band_spec.kind, "yoy")
        self.assertEqual(r.band_spec.edges, (-8, -4, -1, 8, 15, 25))
        self.assertEqual(r.band_spec.segments,
                         ("alert", "elevated", "watch", "ok", "watch", "elevated", "alert"))

    def test_market_health_is_yoy_computed(self):
        r = narrative.market_health("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))
        self.assertEqual(r.band_spec.kind, "yoy_computed")
        self.assertEqual(r.band_spec.edges, (-10, -5, -2, 6, 10, 15))

    def test_credit_spread(self):
        r = narrative.credit_spread("high-yield", 4.0, 6.0)
        self.assertEqual(r.band_spec.edges, (4.0, 6.0))
        self.assertEqual(r.band_spec.segments, ("ok", "watch", "elevated"))

    def test_yoy_contraction_band(self):
        r = narrative.yoy_contraction_band("Corporate profits", 0, -5, -15)
        self.assertEqual(r.band_spec.edges, (-15, -5, 0))
        self.assertEqual(r.band_spec.segments, ("alert", "elevated", "watch", "ok"))
        self.assertEqual(r.band_spec.kind, "yoy")

    def test_epu_band_cap(self):
        r = narrative.epu_band("Global policy uncertainty", cap="watch")
        self.assertEqual(r.band_spec.edges, (120, 200, 300))
        self.assertEqual(r.band_spec.cap, "watch")

    def test_world_growth(self):
        r = narrative.world_growth(lambda: None)
        self.assertEqual(r.band_spec.edges, (2.0, 2.5, 3.2))
        self.assertEqual(r.band_spec.segments, ("alert", "elevated", "watch", "ok"))


class TestBespokeSpecs(unittest.TestCase):
    def test_mortgage(self):
        self.assertEqual(narrative.rule_mortgage.band_spec.edges, (5.5, 6.5, 7.5))
        self.assertEqual(narrative.rule_mortgage.band_tag, "rule_mortgage")

    def test_sentiment_descending(self):
        self.assertEqual(narrative.rule_sentiment.band_spec.edges, (55, 70, 85))
        self.assertEqual(narrative.rule_sentiment.band_spec.segments,
                         ("alert", "elevated", "watch", "ok"))

    def test_dollar_yoy_two_sided(self):
        self.assertEqual(narrative.rule_dollar_yoy.band_spec.edges, (-12, -9, -5, 5, 9, 12))

    def test_claims_thousands(self):
        self.assertEqual(narrative.rule_claims.band_spec.value_format, "thousands")
        self.assertEqual(narrative.rule_claims.band_spec.edges, (250000, 300000))

    def test_yield_curve_custom_no_probe(self):
        self.assertEqual(narrative.rule_yield_curve.band_spec.kind, "custom")
        self.assertFalse(narrative.rule_yield_curve.band_spec.probe)


if __name__ == "__main__":
    unittest.main()

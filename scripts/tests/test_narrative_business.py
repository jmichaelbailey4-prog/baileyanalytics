import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def _obs(v):
    return [("2026-01-01", v)]


class TestYoyContractionBand(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.yoy_contraction_band("Corporate profits", 0, -5, -15)

    def test_growing_is_ok(self):
        text, status = self.rule(_obs(17.4))
        self.assertEqual(status, "ok")
        self.assertIn("growing 17.4%", text)

    def test_sub_one_percent_is_flat_ok(self):
        text, status = self.rule(_obs(0.4))
        self.assertEqual(status, "ok")
        self.assertIn("roughly flat", text)

    def test_small_decline_is_watch(self):
        text, status = self.rule(_obs(-2.0))
        self.assertEqual(status, "watch")
        self.assertIn("shrinking", text)

    def test_sharp_decline_is_elevated(self):
        text, status = self.rule(_obs(-9.8))
        self.assertEqual(status, "elevated")
        self.assertIn("contracting sharply", text)

    def test_collapse_is_alert(self):
        text, status = self.rule(_obs(-46.0))
        self.assertEqual(status, "alert")
        self.assertIn("severe contraction", text)

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([]), ("Data unavailable.", "unknown"))


class TestBaaSpread(unittest.TestCase):
    def test_bands(self):
        cases = [(1.62, "ok"), (2.2, "watch"), (2.8, "elevated"), (6.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_baa_spread(_obs(v))
            self.assertEqual(status, want, f"spread {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_baa_spread([]), ("Data unavailable.", "unknown"))


class TestLendingStandards(unittest.TestCase):
    def test_bands(self):
        cases = [(-10.0, "ok"), (0.0, "ok"), (8.1, "watch"), (35.0, "elevated"), (83.6, "alert")]
        for v, want in cases:
            _, status = narrative.rule_lending_standards(_obs(v))
            self.assertEqual(status, want, f"net tightening {v}")

    def test_easing_text(self):
        text, _ = narrative.rule_lending_standards(_obs(-10.0))
        self.assertIn("easing", text)

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_lending_standards([]), ("Data unavailable.", "unknown"))


class TestBusinessDelinquency(unittest.TestCase):
    def test_bands(self):
        cases = [(1.34, "ok"), (1.8, "watch"), (3.0, "elevated"), (4.4, "alert")]
        for v, want in cases:
            _, status = narrative.rule_business_delinquency(_obs(v))
            self.assertEqual(status, want, f"rate {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_business_delinquency([]), ("Data unavailable.", "unknown"))


class TestInventoriesSales(unittest.TestCase):
    def test_bands(self):
        cases = [(1.32, "ok"), (1.44, "watch"), (1.55, "elevated")]
        for v, want in cases:
            _, status = narrative.rule_inventories_sales(_obs(v))
            self.assertEqual(status, want, f"ratio {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_inventories_sales([]), ("Data unavailable.", "unknown"))


class TestBusinessHeadlines(unittest.TestCase):
    def test_all_business_lenses_have_full_headline_sets(self):
        for lens_id in ("business-profitability", "business-formation",
                        "business-investment", "business-credit"):
            self.assertIn(lens_id, narrative.HEADLINES)
            for status in ("ok", "watch", "elevated", "alert", "unknown"):
                self.assertTrue(narrative.HEADLINES[lens_id].get(status), f"{lens_id}/{status}")


if __name__ == "__main__":
    unittest.main()

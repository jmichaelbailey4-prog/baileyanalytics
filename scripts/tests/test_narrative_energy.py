import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def yr(a, b):
    """Two points a year apart so the YoY helper resolves a prior value."""
    return [("2025-01-01", a), ("2026-01-01", b)]


class TestConsumerCost(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.consumer_cost("Gasoline", 10, 25, 40)

    def test_falling_is_ok(self):
        self.assertEqual(self.rule(yr(4.00, 3.50))[1], "ok")

    def test_small_rise_is_ok(self):
        self.assertEqual(self.rule(yr(4.00, 4.20))[1], "ok")   # +5%

    def test_watch_band(self):
        self.assertEqual(self.rule(yr(4.00, 4.60))[1], "watch")  # +15%

    def test_elevated_band(self):
        self.assertEqual(self.rule(yr(4.00, 5.20))[1], "elevated")  # +30%

    def test_alert_band(self):
        self.assertEqual(self.rule(yr(4.00, 6.00))[1], "alert")   # +50%

    def test_no_baseline_is_ok(self):
        self.assertEqual(self.rule([("2026-01-01", 4.00)])[1], "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([])[1], "unknown")


class TestInfoRules(unittest.TestCase):
    def test_energy_level_is_info(self):
        text, status = narrative.energy_level("Crude inventories")(yr(400.0, 430.0))
        self.assertEqual(status, "info")
        self.assertIn("Crude inventories", text)

    def test_generation_share_is_info(self):
        text, status = narrative.generation_share("Renewables")(yr(20.0, 24.0))
        self.assertEqual(status, "info")
        self.assertIn("%", text)


class TestEnergySynthesis(unittest.TestCase):
    def test_info_ignored_price_severity_drives_badge(self):
        # one price severity (elevated) + physical info -> lens reads elevated
        headline, overall = narrative.synthesize("energy-oil-fuels",
                                                 ["elevated", "info", "info"])
        self.assertEqual(overall, "elevated")
        self.assertTrue(headline)

    def test_all_info_is_unknown(self):
        _, overall = narrative.synthesize("energy-electricity", ["info", "info"])
        self.assertEqual(overall, "unknown")


if __name__ == "__main__":
    unittest.main()

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def _yoy(prior, latest):
    """Two observations exactly one year apart."""
    return [("2025-01-01", prior), ("2026-01-01", latest)]


class TestMarketHealth(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.market_health("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))

    def test_hot_alert(self):
        text, status = self.rule(_yoy(100.0, 116.0))  # +16%
        self.assertEqual(status, "alert")
        self.assertIn("overheating", text)

    def test_hot_elevated(self):
        _, status = self.rule(_yoy(100.0, 111.0))  # +11%
        self.assertEqual(status, "elevated")

    def test_hot_watch(self):
        _, status = self.rule(_yoy(100.0, 107.0))  # +7%
        self.assertEqual(status, "watch")

    def test_cold_alert(self):
        text, status = self.rule(_yoy(100.0, 89.0))  # -11%
        self.assertEqual(status, "alert")
        self.assertIn("freeze", text)

    def test_cold_elevated(self):
        _, status = self.rule(_yoy(100.0, 94.0))  # -6%
        self.assertEqual(status, "elevated")

    def test_cold_watch(self):
        _, status = self.rule(_yoy(100.0, 97.0))  # -3%
        self.assertEqual(status, "watch")

    def test_steady_is_ok(self):
        text, status = self.rule(_yoy(100.0, 101.0))  # +1% -> steady growth, not "flat"
        self.assertEqual(status, "ok")
        self.assertIn("steady pace", text)

    def test_flat_is_little_changed(self):
        text, status = self.rule(_yoy(100.0, 100.4))  # +0.4%
        self.assertEqual(status, "ok")
        self.assertIn("little changed", text)

    def test_short_history_is_ok_not_crash(self):
        _, status = self.rule([("2026-01-01", 100.0)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([]), ("Data unavailable.", "unknown"))


class TestAffordability(unittest.TestCase):
    def test_bands(self):
        cases = [(135.0, "ok"), (115.0, "watch"), (105.6, "elevated"), (90.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_affordability([("2026-05-01", v)])
            self.assertEqual(status, want, f"index {v}")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_affordability([]), ("Data unavailable.", "unknown"))


class TestMortgageDelinquency(unittest.TestCase):
    def test_bands(self):
        cases = [(1.89, "ok"), (2.5, "watch"), (5.0, "elevated"), (9.0, "alert")]
        for v, want in cases:
            _, status = narrative.rule_mortgage_delinquency([("2026-01-01", v)])
            self.assertEqual(status, want, f"rate {v}")


class TestMonthsSupply(unittest.TestCase):
    def test_two_sided_bands(self):
        cases = [(2.5, "elevated"), (3.5, "watch"), (5.0, "ok"),
                 (7.0, "watch"), (9.4, "elevated"), (11.0, "alert")]
        for v, want in cases:
            text, status = narrative.rule_months_supply([("2026-04-01", v)])
            self.assertEqual(status, want, f"supply {v}: {text}")

    def test_glut_text_mentions_glut(self):
        text, _ = narrative.rule_months_supply([("2026-04-01", 9.4)])
        self.assertIn("glut", text)


class TestRentalVacancy(unittest.TestCase):
    def test_two_sided_bands(self):
        cases = [(4.5, "elevated"), (5.5, "watch"), (7.3, "ok"),
                 (9.0, "watch"), (11.0, "elevated")]
        for v, want in cases:
            _, status = narrative.rule_rental_vacancy([("2026-01-01", v)])
            self.assertEqual(status, want, f"vacancy {v}")


class TestLevelPoints(unittest.TestCase):
    def test_info_with_direction(self):
        rule = narrative.level_points("The homeownership rate")
        text, status = rule([("2025-01-01", 65.7), ("2026-01-01", 65.3)])
        self.assertEqual(status, "info")
        self.assertIn("65.3%", text)
        self.assertIn("down 0.4 points", text)

    def test_info_steady(self):
        rule = narrative.level_points("The homeownership rate")
        text, status = rule([("2025-01-01", 65.3), ("2026-01-01", 65.3)])
        self.assertEqual(status, "info")
        self.assertIn("little changed", text)


class TestHousingHeadlines(unittest.TestCase):
    LENS_IDS = ["housing-home-prices", "housing-affordability",
                "housing-supply-construction", "housing-rent-shelter"]

    def test_every_lens_has_all_severity_headlines(self):
        for lid in self.LENS_IDS:
            for status in ("alert", "elevated", "watch", "ok", "unknown"):
                self.assertTrue(narrative.HEADLINES.get(lid, {}).get(status),
                                f"missing {lid}/{status}")

    def test_synthesize_aggregates_to_worst(self):
        headline, overall = narrative.synthesize(
            "housing-affordability", ["elevated", "ok", "info", "ok"])
        self.assertEqual(overall, "elevated")
        self.assertTrue(headline)


if __name__ == "__main__":
    unittest.main()

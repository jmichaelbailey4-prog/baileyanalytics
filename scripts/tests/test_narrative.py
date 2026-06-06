import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


class TestYieldCurve(unittest.TestCase):
    def test_inverted_is_elevated(self):
        obs = [("2026-05-01", -0.5), ("2026-06-01", -0.3)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "elevated")
        self.assertIn("inverted", text)

    def test_recent_uninversion_is_watch(self):
        obs = [("2026-01-01", -0.2), ("2026-05-01", 0.1), ("2026-06-01", 0.30)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "watch")
        self.assertIn("un-inverted", text)

    def test_long_positive_is_ok(self):
        obs = [("2026-01-01", 0.8)] * 5 + [("2026-06-01", 0.9)]
        text, status = narrative.rule_yield_curve(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_yield_curve([]), ("Data unavailable.", "unknown"))


class TestSahm(unittest.TestCase):
    def test_triggered_is_alert(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.55)])
        self.assertEqual(status, "alert")
        self.assertIn("triggered", text)

    def test_near_trigger_is_watch(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.43)])
        self.assertEqual(status, "watch")

    def test_low_is_ok(self):
        text, status = narrative.rule_sahm([("2026-06-01", 0.10)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_sahm([]), ("Data unavailable.", "unknown"))


class TestClaims(unittest.TestCase):
    def test_low_is_ok(self):
        text, status = narrative.rule_claims([("2026-06-01", 219000.0)])
        self.assertEqual(status, "ok")
        self.assertIn("219,000", text)

    def test_creeping_is_watch(self):
        _, status = narrative.rule_claims([("2026-06-01", 275000.0)])
        self.assertEqual(status, "watch")

    def test_high_is_elevated(self):
        _, status = narrative.rule_claims([("2026-06-01", 340000.0)])
        self.assertEqual(status, "elevated")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_claims([]), ("Data unavailable.", "unknown"))


class TestUnemploymentTrend(unittest.TestCase):
    def test_rising_from_low_is_watch(self):
        obs = [("m1", 3.6), ("m2", 3.7), ("m3", 3.9), ("m4", 4.1), ("m5", 4.2)]
        text, status = narrative.rule_unemployment_trend(obs)
        self.assertEqual(status, "watch")
        self.assertIn("0.6", text)  # 4.2 - 3.6

    def test_steady_is_ok(self):
        obs = [("m1", 4.1), ("m2", 4.0), ("m3", 4.1), ("m4", 4.2)]
        _, status = narrative.rule_unemployment_trend(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_unemployment_trend([]), ("Data unavailable.", "unknown"))


class TestSynthesize(unittest.TestCase):
    def test_watch_headline(self):
        headline, overall = narrative.synthesize("recession-watch", ["ok", "watch", "ok", "watch"])
        self.assertEqual(overall, "watch")
        self.assertIn("warning lights", headline)

    def test_alert_headline(self):
        headline, overall = narrative.synthesize("recession-watch", ["alert", "watch"])
        self.assertEqual(overall, "alert")
        self.assertIn("flashing", headline)

    def test_unknown_lens_returns_empty_headline(self):
        headline, overall = narrative.synthesize("does-not-exist", ["ok"])
        self.assertEqual(overall, "ok")
        self.assertEqual(headline, "")

    def test_cost_of_money_watch_headline(self):
        headline, overall = narrative.synthesize("cost-of-money", ["watch", "ok", "ok"])
        self.assertEqual(overall, "watch")
        self.assertIn("expensive", headline)


class TestFedFunds(unittest.TestCase):
    def test_climbing_high_is_watch(self):
        obs = [("2025-06-01", 3.0), ("2026-06-01", 4.5)]
        text, status = narrative.rule_fed_funds(obs)
        self.assertEqual(status, "watch")
        self.assertIn("climbing", text)

    def test_low_holding_is_ok(self):
        obs = [("2025-06-01", 2.0), ("2026-06-01", 2.0)]
        text, status = narrative.rule_fed_funds(obs)
        self.assertEqual(status, "ok")
        self.assertIn("steady", text)

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_fed_funds([]), ("Data unavailable.", "unknown"))


class TestRateTrend(unittest.TestCase):
    def test_up_over_year(self):
        obs = [("2025-06-01", 3.5), ("2026-06-01", 4.4)]
        text, status = narrative.rule_rate_trend(obs)
        self.assertEqual(status, "ok")
        self.assertIn("up", text)

    def test_little_changed(self):
        obs = [("2025-06-01", 4.35), ("2026-06-01", 4.38)]
        _, status = narrative.rule_rate_trend(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_rate_trend([]), ("Data unavailable.", "unknown"))


class TestMortgage(unittest.TestCase):
    def test_high_is_watch(self):
        text, status = narrative.rule_mortgage([("2026-06-01", 6.84)])
        self.assertEqual(status, "watch")
        self.assertIn("stretched", text)

    def test_moderate_is_ok(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 4.2)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_mortgage([]), ("Data unavailable.", "unknown"))


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

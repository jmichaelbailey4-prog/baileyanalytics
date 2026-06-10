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
        text, status = self.rule(_yoy(100.0, 101.0))  # +1%
        self.assertEqual(status, "ok")
        self.assertIn("little changed", text)

    def test_short_history_is_ok_not_crash(self):
        _, status = self.rule([("2026-01-01", 100.0)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(self.rule([]), ("Data unavailable.", "unknown"))


if __name__ == "__main__":
    unittest.main()

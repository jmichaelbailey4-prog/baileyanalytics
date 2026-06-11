import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import explain, models  # noqa: E402


class TestStreak(unittest.TestCase):
    def test_rising_streak(self):
        self.assertEqual(explain.streak([1.0, 2.0, 3.0, 4.0]), ("risen", 3))

    def test_falling_streak(self):
        self.assertEqual(explain.streak([5.0, 4.0, 3.0]), ("fallen", 2))

    def test_no_streak(self):
        self.assertIsNone(explain.streak([1.0, 2.0, 1.5]))
        self.assertIsNone(explain.streak([1.0]))


class TestWhy(unittest.TestCase):
    def test_every_model_family_has_copy(self):
        for name in models.MODEL_NAMES:
            why = explain.why(name, "monthly", [1.0, 2.0, 1.5], "CPI")
            self.assertTrue(why and why[0].isupper() and why.endswith("."))

    def test_streak_lead_in(self):
        why = explain.why("ets-seasonal", "monthly", [1.0, 2.0, 3.0, 4.0], "CPI")
        self.assertIn("CPI has risen 3 straight months", why)

    def test_no_streak_no_lead_in(self):
        why = explain.why("naive", "weekly", [1.0, 2.0, 1.5], "Claims")
        self.assertNotIn("straight", why)


if __name__ == "__main__":
    unittest.main()

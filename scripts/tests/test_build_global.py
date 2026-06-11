import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build


class TestFmtGlobal(unittest.TestCase):
    def test_negative_money_sign_before_dollar(self):
        self.assertEqual(build._fmt("-55.9", "$B"), "-$55.90B")

    def test_negative_thousands_money(self):
        self.assertEqual(build._fmt("-1500", "$B", "thousands"), "-$1,500B")

    def test_positive_money_unchanged(self):
        self.assertEqual(build._fmt("2.4", "$T"), "$2.40T")
        self.assertEqual(build._fmt("4.15", "$"), "$4.15")

    def test_sigma_unit_stays_tight(self):
        self.assertEqual(build._fmt("1.77", "σ"), "1.77σ")

    def test_word_unit_keeps_space(self):
        self.assertEqual(build._fmt("9.4", "months"), "9.40 months")

    def test_negative_percent(self):
        self.assertEqual(build._fmt("-0.9", "%"), "-0.90%")


if __name__ == "__main__":
    unittest.main()

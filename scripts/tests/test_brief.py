import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief


class TestPctChange(unittest.TestCase):
    def test_normal_rise(self):
        self.assertAlmostEqual(brief.pct_change([100.0, 110.0]), 10.0)

    def test_normal_fall(self):
        self.assertAlmostEqual(brief.pct_change([200.0, 150.0]), -25.0)

    def test_uses_last_two_only(self):
        self.assertAlmostEqual(brief.pct_change([1.0, 2.0, 4.0, 5.0]), 25.0)

    def test_single_point_is_none(self):
        self.assertIsNone(brief.pct_change([5.0]))

    def test_empty_is_none(self):
        self.assertIsNone(brief.pct_change([]))

    def test_zero_prior_is_none(self):
        self.assertIsNone(brief.pct_change([0.0, 3.0]))

    def test_none_arg_is_none(self):
        self.assertIsNone(brief.pct_change(None))


if __name__ == "__main__":
    unittest.main()

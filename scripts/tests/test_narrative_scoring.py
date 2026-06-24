"""New / reworked scoring rules from the score-explain-order feature."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def _o(v):
    """A single-value obs list (rules only read obs[-1])."""
    return [("2026-01-01", v)]


def _series(*vals):
    return [(f"2026-{i + 1:02d}-01", v) for i, v in enumerate(vals)]


class RestrictiveRateTest(unittest.TestCase):
    def setUp(self):
        self.rule = narrative.restrictive_rate("The 10-year Treasury", 4.5, 5.5)

    def test_moderate_is_ok(self):
        self.assertEqual(self.rule(_o(4.1))[1], "ok")

    def test_above_comfort_is_watch(self):
        self.assertEqual(self.rule(_o(4.9))[1], "watch")

    def test_high_is_elevated_never_alert(self):
        self.assertEqual(self.rule(_o(7.0))[1], "elevated")

    def test_empty(self):
        self.assertEqual(self.rule([])[1], "unknown")


class AutoSalesTest(unittest.TestCase):
    def test_healthy(self):
        self.assertEqual(narrative.rule_auto_sales(_o(16.0))[1], "ok")

    def test_softening(self):
        self.assertEqual(narrative.rule_auto_sales(_o(14.0))[1], "watch")

    def test_weak(self):
        self.assertEqual(narrative.rule_auto_sales(_o(13.0))[1], "elevated")

    def test_collapse(self):
        self.assertEqual(narrative.rule_auto_sales(_o(10.0))[1], "alert")


class MortgageDebtServiceTest(unittest.TestCase):
    def test_manageable(self):
        self.assertEqual(narrative.rule_mortgage_debt_service(_o(4.0))[1], "ok")

    def test_above_comfort(self):
        self.assertEqual(narrative.rule_mortgage_debt_service(_o(5.0))[1], "watch")

    def test_heavy(self):
        self.assertEqual(narrative.rule_mortgage_debt_service(_o(6.0))[1], "elevated")

    def test_danger(self):
        self.assertEqual(narrative.rule_mortgage_debt_service(_o(7.0))[1], "alert")


class InterestBurdenTest(unittest.TestCase):
    def test_manageable(self):
        self.assertEqual(narrative.rule_interest_burden(_o(8.0))[1], "ok")

    def test_rising_claim(self):
        self.assertEqual(narrative.rule_interest_burden(_o(15.0))[1], "watch")

    def test_crowding_out(self):
        self.assertEqual(narrative.rule_interest_burden(_o(23.0))[1], "elevated")

    def test_extreme(self):
        self.assertEqual(narrative.rule_interest_burden(_o(27.0))[1], "alert")


class WageGrowthBandsTest(unittest.TestCase):
    def test_solid_pay_is_ok(self):
        self.assertEqual(narrative.rule_wage_growth(_o(4.2))[1], "ok")

    def test_cooling_is_watch(self):
        self.assertEqual(narrative.rule_wage_growth(_o(2.5))[1], "watch")

    def test_stalled_is_elevated(self):
        self.assertEqual(narrative.rule_wage_growth(_o(1.5))[1], "elevated")

    def test_is_now_severity_capable(self):
        self.assertEqual(narrative.rule_kind(narrative.rule_wage_growth), "severity")


if __name__ == "__main__":
    unittest.main()

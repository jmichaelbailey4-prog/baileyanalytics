import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


class TestNoncurrent(unittest.TestCase):
    def test_low_is_ok(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 0.7)])
        self.assertEqual(s, "ok")

    def test_creeping_is_watch(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 1.2)])
        self.assertEqual(s, "watch")

    def test_high_is_elevated(self):
        _, s = narrative.rule_noncurrent([("2024-12-31", 2.1)])
        self.assertEqual(s, "elevated")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_noncurrent([]), ("Data unavailable.", "unknown"))


class TestChargeOffs(unittest.TestCase):
    def test_low_is_ok(self):
        _, s = narrative.rule_charge_offs([("2024-12-31", 0.4)])
        self.assertEqual(s, "ok")

    def test_high_is_elevated(self):
        _, s = narrative.rule_charge_offs([("2024-12-31", 1.5)])
        self.assertEqual(s, "elevated")


class TestCreConcentration(unittest.TestCase):
    def test_above_flag_is_elevated(self):
        _, s = narrative.rule_cre_concentration([("2024-12-31", 320)])
        self.assertEqual(s, "elevated")

    def test_manageable_is_ok(self):
        _, s = narrative.rule_cre_concentration([("2024-12-31", 150)])
        self.assertEqual(s, "ok")


class TestUninsuredShare(unittest.TestCase):
    def test_high_is_watch(self):
        t, s = narrative.rule_uninsured_share([("2024-12-31", 45.0)])
        self.assertEqual(s, "watch")
        self.assertIn("45.0%", t)

    def test_low_is_ok(self):
        _, s = narrative.rule_uninsured_share([("2024-12-31", 25.0)])
        self.assertEqual(s, "ok")


class TestCapitalRatio(unittest.TestCase):
    def test_healthy_is_ok(self):
        _, s = narrative.rule_capital_ratio([("2024-12-31", 11.5)])
        self.assertEqual(s, "ok")

    def test_thin_is_elevated(self):
        _, s = narrative.rule_capital_ratio([("2024-12-31", 7.0)])
        self.assertEqual(s, "elevated")


class TestRiskBasedCapital(unittest.TestCase):
    def test_well_capitalized_is_ok(self):
        _, s = narrative.rule_risk_based_capital([("2024-12-31", 15.3)])
        self.assertEqual(s, "ok")

    def test_below_minimum_is_elevated(self):
        _, s = narrative.rule_risk_based_capital([("2024-12-31", 7.0)])
        self.assertEqual(s, "elevated")


class TestNetMargin(unittest.TestCase):
    def test_compressed_is_watch(self):
        _, s = narrative.rule_net_margin([("2024-12-31", 2.1)])
        self.assertEqual(s, "watch")

    def test_healthy_is_ok(self):
        _, s = narrative.rule_net_margin([("2024-12-31", 3.2)])
        self.assertEqual(s, "ok")


class TestRoa(unittest.TestCase):
    def test_solid_is_ok(self):
        _, s = narrative.rule_roa([("2024-12-31", 1.17)])
        self.assertEqual(s, "ok")

    def test_weak_is_elevated(self):
        _, s = narrative.rule_roa([("2024-12-31", 0.3)])
        self.assertEqual(s, "elevated")


class TestLoansDeposits(unittest.TestCase):
    def test_stretched_is_watch(self):
        _, s = narrative.rule_loans_deposits([("2024-12-31", 92)])
        self.assertEqual(s, "watch")

    def test_comfortable_is_ok(self):
        _, s = narrative.rule_loans_deposits([("2024-12-31", 66)])
        self.assertEqual(s, "ok")


class TestBankingHeadline(unittest.TestCase):
    def test_asset_quality_watch(self):
        h, o = narrative.synthesize("bank-asset-quality", ["ok", "watch", "ok"])
        self.assertEqual(o, "watch")
        self.assertTrue(h)

    def test_concentrations_ok(self):
        h, o = narrative.synthesize("bank-concentrations-funding", ["ok", "ok"])
        self.assertEqual(o, "ok")
        self.assertIn("stable", h)


if __name__ == "__main__":
    unittest.main()

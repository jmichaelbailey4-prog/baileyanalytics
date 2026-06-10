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

    def test_short_history_omits_year_phrase(self):
        obs = [("2026-04-01", 4.30), ("2026-05-01", 4.38)]
        text, status = narrative.rule_rate_trend(obs)
        self.assertEqual(status, "ok")
        self.assertNotIn("over the past year", text)


class TestMortgage(unittest.TestCase):
    def test_punishing_is_alert(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 7.8)])
        self.assertEqual(status, "alert")

    def test_high_is_elevated(self):
        text, status = narrative.rule_mortgage([("2026-06-01", 6.84)])
        self.assertEqual(status, "elevated")
        self.assertIn("stretched", text)

    def test_above_comfort_is_watch(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 5.9)])
        self.assertEqual(status, "watch")

    def test_moderate_is_ok(self):
        _, status = narrative.rule_mortgage([("2026-06-01", 4.2)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_mortgage([]), ("Data unavailable.", "unknown"))


class TestPayrolls(unittest.TestCase):
    def test_healthy_is_ok(self):
        text, status = narrative.rule_payrolls([("2026-05-01", 177000.0)])
        self.assertEqual(status, "ok")
        self.assertIn("177,000", text)

    def test_slow_is_watch(self):
        _, status = narrative.rule_payrolls([("2026-05-01", 60000.0)])
        self.assertEqual(status, "watch")

    def test_negative_is_alert(self):
        text, status = narrative.rule_payrolls([("2026-05-01", -40000.0)])
        self.assertEqual(status, "alert")
        self.assertIn("cut", text)

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_payrolls([]), ("Data unavailable.", "unknown"))


class TestJobOpenings(unittest.TestCase):
    def test_easing_below_threshold_is_watch(self):
        obs = [("2025-05-01", 8.0), ("2026-05-01", 7.2)]
        text, status = narrative.rule_job_openings(obs)
        self.assertEqual(status, "watch")
        self.assertIn("easing", text)

    def test_high_is_ok(self):
        obs = [("2025-05-01", 9.0), ("2026-05-01", 9.2)]
        _, status = narrative.rule_job_openings(obs)
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_job_openings([]), ("Data unavailable.", "unknown"))


class TestWageGrowth(unittest.TestCase):
    def test_above_inflation_is_ok(self):
        text, status = narrative.rule_wage_growth([("2026-05-01", 4.0)])
        self.assertEqual(status, "ok")
        self.assertIn("4.0%", text)

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_wage_growth([]), ("Data unavailable.", "unknown"))


class TestJobMarketHeadline(unittest.TestCase):
    def test_cooling_is_watch(self):
        headline, overall = narrative.synthesize("job-market", ["watch", "ok", "watch"])
        self.assertEqual(overall, "watch")
        self.assertIn("cooling", headline)


class TestInflation(unittest.TestCase):
    def test_hot_is_elevated(self):
        _, status = narrative.rule_inflation([("2026-05-01", 4.5)])
        self.assertEqual(status, "elevated")

    def test_above_target_is_watch(self):
        text, status = narrative.rule_inflation([("2026-05-01", 3.1)])
        self.assertEqual(status, "watch")
        self.assertIn("3.1%", text)

    def test_near_target_is_ok(self):
        _, status = narrative.rule_inflation([("2026-05-01", 2.1)])
        self.assertEqual(status, "ok")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_inflation([]), ("Data unavailable.", "unknown"))


class TestRealWages(unittest.TestCase):
    def test_positive_is_ok(self):
        text, status = narrative.rule_real_wages([("2026-05-01", 0.7)])
        self.assertEqual(status, "ok")
        self.assertIn("outpacing", text)

    def test_negative_is_watch(self):
        _, status = narrative.rule_real_wages([("2026-05-01", -0.5)])
        self.assertEqual(status, "watch")

    def test_empty_is_unknown(self):
        self.assertEqual(narrative.rule_real_wages([]), ("Data unavailable.", "unknown"))


class TestCostOfLivingHeadline(unittest.TestCase):
    def test_still_above_target_is_watch(self):
        headline, overall = narrative.synthesize("cost-of-living", ["watch", "watch", "ok"])
        self.assertEqual(overall, "watch")
        self.assertIn("target", headline)


class TestYoyBand(unittest.TestCase):
    """One-sided cost severity applied to a series that is ALREADY a YoY % rate."""

    def test_bands(self):
        rule = narrative.yoy_band("Rent", 4, 6, 9)
        self.assertEqual(rule([("d", 10.0)])[1], "alert")
        self.assertEqual(rule([("d", 7.0)])[1], "elevated")
        self.assertEqual(rule([("d", 4.5)])[1], "watch")
        self.assertEqual(rule([("d", 1.0)])[1], "ok")
        self.assertEqual(rule([("d", -5.0)])[1], "ok")

    def test_text_uses_value_directly(self):
        text, _ = narrative.yoy_band("Rent", 4, 6, 9)([("d", 4.5)])
        self.assertIn("4.5%", text)

    def test_falling_reads_as_relief(self):
        text, _ = narrative.yoy_band("Rent", 4, 6, 9)([("d", -5.0)])
        self.assertIn("falling", text)

    def test_empty(self):
        self.assertEqual(narrative.yoy_band("Rent", 4, 6, 9)([]), ("Data unavailable.", "unknown"))


class TestYoyBandTwoSided(unittest.TestCase):
    """Two-sided market-health severity applied to an already-YoY % series."""

    def test_hot_and_cold_bands(self):
        rule = narrative.yoy_band_two_sided("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))
        self.assertEqual(rule([("d", 16.0)])[1], "alert")
        self.assertEqual(rule([("d", 11.0)])[1], "elevated")
        self.assertEqual(rule([("d", 7.0)])[1], "watch")
        self.assertEqual(rule([("d", 2.0)])[1], "ok")
        self.assertEqual(rule([("d", -3.0)])[1], "watch")
        self.assertEqual(rule([("d", -6.0)])[1], "elevated")
        self.assertEqual(rule([("d", -11.0)])[1], "alert")

    def test_text(self):
        text, _ = narrative.yoy_band_two_sided("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))([("d", 3.2)])
        self.assertIn("3.2%", text)
        self.assertIn("little changed", text)

    def test_empty(self):
        rule = narrative.yoy_band_two_sided("X", hot=(6, 10, 15), cold=(-2, -5, -10))
        self.assertEqual(rule([]), ("Data unavailable.", "unknown"))


class TestYoyInfo(unittest.TestCase):
    def test_directions(self):
        rule = narrative.yoy_info("Owners' equivalent rent")
        text, status = rule([("d", 3.4)])
        self.assertEqual(status, "info")
        self.assertIn("rising 3.4%", text)
        self.assertIn("falling 2.0%", rule([("d", -2.0)])[0])
        self.assertIn("roughly flat", rule([("d", 0.1)])[0])

    def test_empty(self):
        self.assertEqual(narrative.yoy_info("X")([]), ("Data unavailable.", "unknown"))


class TestFiscalRules(unittest.TestCase):
    def test_debt_gdp_bands(self):
        self.assertEqual(narrative.rule_debt_gdp([("d", 135.0)])[1], "alert")
        self.assertEqual(narrative.rule_debt_gdp([("d", 121.0)])[1], "elevated")
        self.assertEqual(narrative.rule_debt_gdp([("d", 95.0)])[1], "watch")
        self.assertEqual(narrative.rule_debt_gdp([("d", 75.0)])[1], "ok")
        self.assertIn("121% of GDP", narrative.rule_debt_gdp([("d", 121.0)])[0])

    def test_deficit_bands(self):
        self.assertEqual(narrative.rule_deficit_12m([("d", 3.1)])[1], "alert")
        self.assertEqual(narrative.rule_deficit_12m([("d", 1.9)])[1], "elevated")
        self.assertEqual(narrative.rule_deficit_12m([("d", 1.0)])[1], "watch")
        self.assertEqual(narrative.rule_deficit_12m([("d", 0.5)])[1], "ok")
        text, status = narrative.rule_deficit_12m([("d", -0.2)])
        self.assertEqual(status, "ok")
        self.assertIn("surplus", text)
        self.assertIn("$1.9 trillion", narrative.rule_deficit_12m([("d", 1.9)])[0])

    def test_empty(self):
        self.assertEqual(narrative.rule_debt_gdp([]), ("Data unavailable.", "unknown"))
        self.assertEqual(narrative.rule_deficit_12m([]), ("Data unavailable.", "unknown"))


class TestEnergyLevelFmt(unittest.TestCase):
    def test_custom_format(self):
        rule = narrative.energy_level("The number of homes for sale", fmt="{:,.2f} million")
        text, status = rule([("2025-05-01", 1.00), ("2026-05-01", 1.06)])
        self.assertEqual(status, "info")
        self.assertIn("1.06 million", text)

    def test_default_format_unchanged(self):
        text, _ = narrative.energy_level("Copper")([("2026-05-01", 13484.2)])
        self.assertIn("13,484", text)


if __name__ == "__main__":
    unittest.main()

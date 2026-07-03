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

    def test_status_is_sampling_invariant_for_an_old_inversion(self):
        # The lens feeds DAILY data; the predictions runner feeds a WEEKLY-resampled
        # version of the SAME path. An inversion that ended >6 months ago must not
        # flip a currently-positive curve to 'watch' on the longer (weekly) series
        # just because it reaches back to the old dip — the recent-inversion window
        # is date-based (~6 months), not a fixed point count. (Regression: the lens
        # read 'ok' while the prediction re-derived 'watch' and the predict block
        # contradicted the badge.)
        import datetime as dt
        now = dt.date(2026, 6, 26)
        def at(d):  # inverted until >9 months before `now`, positive since
            return -0.20 if d < dt.date(2025, 9, 1) else 0.30
        def series(step_days, start):
            out, d = [], start
            while d <= now:
                out.append((d.isoformat(), at(d)))
                d += dt.timedelta(days=step_days)
            return out
        weekly = series(7, dt.date(2024, 1, 5))                  # ~2.4y; old dip is in the tail
        daily = series(1, now - dt.timedelta(days=180))          # last 6 months only
        self.assertEqual(narrative.rule_yield_curve(daily)[1], "ok")
        self.assertEqual(narrative.rule_yield_curve(weekly)[1], "ok")

    def test_inversion_within_six_months_still_watch(self):
        # The date-based window must still flag a genuinely recent un-inversion.
        obs = [("2026-02-01", -0.10), ("2026-04-01", 0.05), ("2026-06-20", 0.25)]
        self.assertEqual(narrative.rule_yield_curve(obs)[1], "watch")

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
        rule = narrative.yoy_band_two_sided("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10))
        text, _ = rule([("d", 3.2)])
        self.assertIn("3.2%", text)
        self.assertIn("steady pace", text)  # 1%..watch reads as steady growth, not "flat"
        self.assertIn("little changed", rule([("d", 0.4)])[0])

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


class TestConsumerRules(unittest.TestCase):
    def test_delinquency_factory_bands(self):
        rule = narrative.consumer_delinquency("Credit-card", 2.5, 4, 6)
        self.assertEqual(rule([("d", 6.5)])[1], "alert")
        self.assertEqual(rule([("d", 4.5)])[1], "elevated")
        self.assertEqual(rule([("d", 2.92)])[1], "watch")
        self.assertEqual(rule([("d", 1.8)])[1], "ok")
        self.assertIn("Credit-card delinquencies", rule([("d", 2.92)])[0])

    def test_revolving_credit(self):
        self.assertEqual(narrative.rule_revolving_credit([("d", 13.0)])[1], "elevated")
        self.assertEqual(narrative.rule_revolving_credit([("d", 9.0)])[1], "watch")
        self.assertEqual(narrative.rule_revolving_credit([("d", 4.0)])[1], "ok")
        text, status = narrative.rule_revolving_credit([("d", -3.0)])
        self.assertEqual(status, "ok")
        self.assertIn("paying down", text)

    def test_debt_service(self):
        self.assertEqual(narrative.rule_debt_service([("d", 13.1)])[1], "alert")
        self.assertEqual(narrative.rule_debt_service([("d", 12.3)])[1], "elevated")
        self.assertEqual(narrative.rule_debt_service([("d", 11.3)])[1], "watch")
        self.assertEqual(narrative.rule_debt_service([("d", 9.8)])[1], "ok")

    def test_saving_rate(self):
        self.assertEqual(narrative.rule_saving_rate([("d", 2.6)])[1], "elevated")
        self.assertEqual(narrative.rule_saving_rate([("d", 4.0)])[1], "watch")
        self.assertEqual(narrative.rule_saving_rate([("d", 6.5)])[1], "ok")

    def test_real_income(self):
        self.assertEqual(narrative.rule_real_income([("d", -2.5)])[1], "elevated")
        self.assertEqual(narrative.rule_real_income([("d", -0.5)])[1], "watch")
        self.assertEqual(narrative.rule_real_income([("d", 1.2)])[1], "ok")

    def test_sentiment(self):
        self.assertEqual(narrative.rule_sentiment([("d", 49.8)])[1], "alert")
        self.assertEqual(narrative.rule_sentiment([("d", 62.0)])[1], "elevated")
        self.assertEqual(narrative.rule_sentiment([("d", 78.0)])[1], "watch")
        self.assertEqual(narrative.rule_sentiment([("d", 95.0)])[1], "ok")

    def test_sentiment_record_low_read(self):
        # A fresh all-time low in the shown history must say so — not "near
        # record lows" while the chart bottoms below every prior point.
        obs = [("2022-06-01", 50.0), ("2024-01-01", 70.0), ("2026-05-01", 44.8)]
        text, status = narrative.rule_sentiment(obs)
        self.assertEqual(status, "alert")
        self.assertIn("a record low", text)
        self.assertNotIn("near record lows", text)
        # Below 55 but above a past low -> the "near record lows" wording.
        obs2 = [("2022-06-01", 44.0), ("2024-01-01", 70.0), ("2026-05-01", 50.2)]
        text2, status2 = narrative.rule_sentiment(obs2)
        self.assertEqual(status2, "alert")
        self.assertIn("near record lows", text2)

    def test_inflation_expectations(self):
        self.assertEqual(narrative.rule_inflation_expectations([("d", 5.6)])[1], "alert")
        self.assertEqual(narrative.rule_inflation_expectations([("d", 4.7)])[1], "elevated")
        self.assertEqual(narrative.rule_inflation_expectations([("d", 3.4)])[1], "watch")
        self.assertEqual(narrative.rule_inflation_expectations([("d", 2.8)])[1], "ok")

    def test_m2_growth(self):
        self.assertEqual(narrative.rule_m2_growth([("d", 11.0)])[1], "elevated")
        self.assertEqual(narrative.rule_m2_growth([("d", 8.0)])[1], "watch")
        self.assertEqual(narrative.rule_m2_growth([("d", 4.0)])[1], "ok")
        self.assertEqual(narrative.rule_m2_growth([("d", -1.5)])[1], "watch")
        self.assertEqual(narrative.rule_m2_growth([("d", -4.0)])[1], "elevated")

    def test_two_sided_verb_override(self):
        rule = narrative.yoy_band_two_sided("Real consumer spending", hot=(4, 6, 9), cold=(-1, -3, -5), verb="is")
        text, _ = rule([("d", 2.0)])
        self.assertIn("Real consumer spending is", text)

    def test_empty_rules_unknown(self):
        for rule in [narrative.rule_revolving_credit, narrative.rule_debt_service,
                     narrative.rule_saving_rate, narrative.rule_real_income,
                     narrative.rule_sentiment, narrative.rule_inflation_expectations,
                     narrative.rule_m2_growth]:
            self.assertEqual(rule([]), ("Data unavailable.", "unknown"))


if __name__ == "__main__":
    unittest.main()

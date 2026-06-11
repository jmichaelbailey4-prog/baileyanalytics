import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def yoy_obs(v):
    """A minimal already-YoY series ending at value v."""
    return [("2025-05", 0.0), ("2026-05", v)]


def level_obs(prior, latest):
    """A two-point level series exactly one year apart."""
    return [("2025-05-01", prior), ("2026-05-01", latest)]


class TestRuleDollarYoy(unittest.TestCase):
    def test_alert_up(self):
        text, status = narrative.rule_dollar_yoy(yoy_obs(13.0))
        self.assertEqual(status, "alert")
        self.assertIn("up 13.0%", text)

    def test_alert_down_direction_aware(self):
        text, status = narrative.rule_dollar_yoy(yoy_obs(-12.5))
        self.assertEqual(status, "alert")
        self.assertIn("down 12.5%", text)

    def test_elevated_band(self):
        _, status = narrative.rule_dollar_yoy(yoy_obs(9.5))
        self.assertEqual(status, "elevated")
        _, status = narrative.rule_dollar_yoy(yoy_obs(-10.0))
        self.assertEqual(status, "elevated")

    def test_watch_band(self):
        text, status = narrative.rule_dollar_yoy(yoy_obs(5.5))
        self.assertEqual(status, "watch")
        self.assertIn("up 5.5%", text)

    def test_ok_drift_states_direction(self):
        text, status = narrative.rule_dollar_yoy(yoy_obs(-2.3))
        self.assertEqual(status, "ok")
        self.assertIn("down 2.3%", text)

    def test_little_changed_below_one_percent(self):
        text, status = narrative.rule_dollar_yoy(yoy_obs(-0.9))
        self.assertEqual(status, "ok")
        self.assertIn("little changed", text)

    def test_no_data(self):
        self.assertEqual(narrative.rule_dollar_yoy([]), ("Data unavailable.", "unknown"))


class TestFxYoy(unittest.TestCase):
    def test_euro_up_means_stronger(self):
        rule = narrative.fx_yoy("The euro")
        text, status = rule(level_obs(1.00, 1.08))
        self.assertEqual(status, "info")
        self.assertIn("strengthened 8.0%", text)

    def test_weaker_when_up_inverts(self):
        rule = narrative.fx_yoy("The yen", weaker_when_up=True)
        text, status = rule(level_obs(140.0, 154.0))
        self.assertEqual(status, "info")
        self.assertIn("weakened 10.0%", text)

    def test_weaker_when_up_falling_strengthens(self):
        rule = narrative.fx_yoy("The yuan", weaker_when_up=True)
        text, _ = rule(level_obs(7.30, 7.00))
        self.assertIn("strengthened 4.1%", text)

    def test_flat(self):
        rule = narrative.fx_yoy("The euro")
        text, _ = rule(level_obs(1.08, 1.083))
        self.assertIn("little changed", text)


class TestWorldGrowth(unittest.TestCase):
    def annual(self, v):
        return [("2025", 3.4), ("2026", v)]

    def test_bands(self):
        for v, want in [(3.3, "ok"), (3.06, "watch"), (2.2, "elevated"), (1.5, "alert")]:
            rule = narrative.world_growth(lambda: None)
            _, status = rule(self.annual(v))
            self.assertEqual(status, want, f"value {v}")

    def test_forecast_appended_when_available(self):
        rule = narrative.world_growth(lambda: {"year": "2027", "value": 3.224})
        text, _ = rule(self.annual(3.06))
        self.assertIn("IMF projects 3.2% for 2027", text)

    def test_no_forecast_no_mention(self):
        rule = narrative.world_growth(lambda: None)
        text, _ = rule(self.annual(3.06))
        self.assertNotIn("projects", text)

    def test_mentions_year_and_value(self):
        rule = narrative.world_growth(lambda: None)
        text, _ = rule(self.annual(3.06))
        self.assertIn("3.1%", text)
        self.assertIn("2026", text)


class TestAnnualGrowth(unittest.TestCase):
    def test_grew_slowing(self):
        rule = narrative.annual_growth("China's economy")
        text, status = rule([("2025", 5.0), ("2026", 4.4)])
        self.assertEqual(status, "info")
        self.assertIn("grew 4.4% in 2026", text)
        self.assertIn("slowing", text)

    def test_grew_accelerating(self):
        rule = narrative.annual_growth("The euro area's economy")
        text, _ = rule([("2025", 0.8), ("2026", 1.3)])
        self.assertIn("grew 1.3% in 2026", text)
        self.assertIn("up from 0.8%", text)

    def test_shrank(self):
        rule = narrative.annual_growth("China's economy")
        text, _ = rule([("2025", 1.0), ("2026", -0.5)])
        self.assertIn("shrank 0.5% in 2026", text)


class TestWorldInflation(unittest.TestCase):
    def test_info_with_direction(self):
        text, status = narrative.rule_world_inflation([("2025", 5.0), ("2026", 4.4)])
        self.assertEqual(status, "info")
        self.assertIn("4.4%", text)
        self.assertIn("2026", text)
        self.assertIn("easing", text)

    def test_rising(self):
        text, _ = narrative.rule_world_inflation([("2025", 4.0), ("2026", 5.4)])
        self.assertIn("up from 4.0%", text)


class TestRuleGscpi(unittest.TestCase):
    def test_bands(self):
        for v, want in [(0.2, "ok"), (0.8, "watch"), (1.77, "elevated"), (3.4, "alert")]:
            _, status = narrative.rule_gscpi(yoy_obs(v))
            self.assertEqual(status, want, f"value {v}")

    def test_negative_sigma_ok_looser(self):
        text, status = narrative.rule_gscpi(yoy_obs(-0.8))
        self.assertEqual(status, "ok")
        self.assertIn("looser", text)


class TestRuleTradeDeficit(unittest.TestCase):
    # The series is derived to positive deficit magnitudes (scaled(-1000, 1))
    # so the hub delta arrow reads intuitively: up = deficit widening.
    def test_deficit_wider_info(self):
        obs = level_obs(48.0, 55.9)
        text, status = narrative.rule_trade_deficit(obs)
        self.assertEqual(status, "info")
        self.assertIn("$55.9B", text)
        self.assertIn("wider", text)

    def test_deficit_narrower(self):
        text, _ = narrative.rule_trade_deficit(level_obs(70.0, 55.9))
        self.assertIn("narrower", text)

    def test_deficit_flat(self):
        text, _ = narrative.rule_trade_deficit(level_obs(56.0, 55.9))
        self.assertIn("about the same", text)

    def test_surplus_branch(self):
        text, _ = narrative.rule_trade_deficit(level_obs(-2.0, -3.5))
        self.assertIn("surplus", text)


class TestEpuBand(unittest.TestCase):
    def test_bands(self):
        rule = narrative.epu_band("U.S. policy uncertainty")
        for v, want in [(95.0, "ok"), (150.0, "watch"), (296.0, "elevated"), (371.0, "alert")]:
            _, status = rule(yoy_obs(v))
            self.assertEqual(status, want, f"value {v}")

    def test_text_carries_level_and_norm(self):
        rule = narrative.epu_band("Global policy uncertainty")
        text, _ = rule(yoy_obs(371.0))
        self.assertIn("371", text)
        self.assertIn("100", text)

    def test_cap_limits_status_but_keeps_text(self):
        # GEPU publishes ~6 months late: it may sanity-check the lens to
        # watch, but a stale print must never drive an elevated/alert badge.
        rule = narrative.epu_band("Global policy uncertainty", cap="watch")
        text, status = rule(yoy_obs(371.0))
        self.assertEqual(status, "watch")
        self.assertIn("extreme", text)

    def test_cap_does_not_lift_ok(self):
        rule = narrative.epu_band("Global policy uncertainty", cap="watch")
        _, status = rule(yoy_obs(95.0))
        self.assertEqual(status, "ok")


class TestHeadlines(unittest.TestCase):
    LENSES = ["global-dollar-currencies", "global-growth",
              "global-trade-supply", "global-uncertainty"]

    def test_all_lenses_all_severities(self):
        for lens in self.LENSES:
            self.assertIn(lens, narrative.HEADLINES)
            for sev in ("ok", "watch", "elevated", "alert", "unknown"):
                self.assertTrue(narrative.HEADLINES[lens].get(sev),
                                f"{lens} missing {sev}")

    def test_synthesize_aggregates_worst(self):
        headline, overall = narrative.synthesize(
            "global-trade-supply", ["elevated", "watch", "info"])
        self.assertEqual(overall, "elevated")
        self.assertEqual(headline,
                         narrative.HEADLINES["global-trade-supply"]["elevated"])


if __name__ == "__main__":
    unittest.main()

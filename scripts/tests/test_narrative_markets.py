import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import narrative


def obs(*vals):
    """Build (date, value) tuples a year apart so _value_year_ago has a baseline."""
    return [(f"{2020 + i}-01-01", v) for i, v in enumerate(vals)]


class TestRiskSentimentRules(unittest.TestCase):
    def test_vix_bands(self):
        self.assertEqual(narrative.rule_vix([("d", 14.0)])[1], "ok")
        self.assertEqual(narrative.rule_vix([("d", 24.0)])[1], "watch")
        self.assertEqual(narrative.rule_vix([("d", 38.0)])[1], "elevated")
        self.assertEqual(narrative.rule_vix([])[1], "unknown")

    def test_credit_spread_factory(self):
        hy = narrative.credit_spread("high-yield", 4.0, 6.0)
        self.assertEqual(hy([("d", 3.2)])[1], "ok")
        self.assertEqual(hy([("d", 5.0)])[1], "watch")
        self.assertEqual(hy([("d", 7.5)])[1], "elevated")
        ig = narrative.credit_spread("investment-grade", 1.5, 2.5)
        self.assertEqual(ig([("d", 1.2)])[1], "ok")
        self.assertEqual(ig([("d", 3.0)])[1], "elevated")

    def test_financial_conditions(self):
        self.assertEqual(narrative.rule_financial_conditions([("d", -0.4)])[1], "ok")
        self.assertEqual(narrative.rule_financial_conditions([("d", 0.2)])[1], "watch")
        self.assertEqual(narrative.rule_financial_conditions([("d", 0.8)])[1], "elevated")


class TestMarketLevel(unittest.TestCase):
    def test_up_down_flat(self):
        rule = narrative.market_level("The S&P 500")
        self.assertEqual(rule(obs(100.0, 130.0))[1], "up")     # +30%
        self.assertEqual(rule(obs(100.0, 70.0))[1], "down")    # -30%
        self.assertEqual(rule(obs(100.0, 101.0))[1], "flat")   # +1%

    def test_no_year_baseline_is_flat(self):
        rule = narrative.market_level("Gold")
        self.assertEqual(rule([("2026-01-01", 2000.0)])[1], "flat")

    def test_text_includes_label_and_value(self):
        text, _ = narrative.market_level("Bitcoin")(obs(50000.0, 65000.0))
        self.assertIn("Bitcoin", text)
        self.assertIn("65,000", text)


class TestMarketSynthesis(unittest.TestCase):
    def test_risk_sentiment_is_severity_based(self):
        headline, overall = narrative.synthesize("market-risk-sentiment", ["ok", "watch", "ok"])
        self.assertEqual(overall, "watch")
        self.assertTrue(headline)

    def test_scoreboard_is_neutral_regardless_of_statuses(self):
        headline, overall = narrative.synthesize("market-scoreboard", ["up", "down", "flat"])
        self.assertEqual(overall, "neutral")
        self.assertTrue(headline)

    def test_crypto_is_neutral(self):
        headline, overall = narrative.synthesize("crypto-structure", ["info", "info"])
        self.assertEqual(overall, "neutral")
        self.assertTrue(headline)


class TestCryptoRules(unittest.TestCase):
    def test_rotation_risk_on_off_balanced(self):
        # 90-point window: last value vs ~90 ago.
        rising = [(f"2026-{i:02d}", 100.0 + i) for i in range(1, 13)]
        self.assertEqual(narrative.rule_crypto_rotation(rising)[1], "info")
        self.assertIn("alts", narrative.rule_crypto_rotation(rising)[0].lower())

    def test_dominance_text(self):
        text, status = narrative.rule_btc_dominance([("d", 54.0)])
        self.assertEqual(status, "info")
        self.assertIn("54", text)

    def test_btc_eth_relative(self):
        self.assertEqual(narrative.rule_btc_eth_relative([("2026-01-01", 20.0)])[1], "info")
        self.assertEqual(narrative.rule_btc_eth_relative([])[1], "unknown")


if __name__ == "__main__":
    unittest.main()

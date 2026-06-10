import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, narrative


class TestConsumerConfig(unittest.TestCase):
    def test_four_lenses(self):
        ids = [l.id for l in config.CONSUMER_LENSES]
        self.assertEqual(ids, ["consumer-spending", "consumer-credit",
                               "consumer-income-savings", "consumer-sentiment"])

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "consumer")
        self.assertEqual(cat["out"], "consumer")
        self.assertEqual(len(cat["lenses"]), 4)

    def test_every_indicator_has_rule_context_and_headline(self):
        for lens in config.CONSUMER_LENSES:
            self.assertIn(lens.id, narrative.HEADLINES)
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)

    def test_liquidity_lens_in_markets(self):
        ids = [l.id for l in config.MARKET_FRED_LENSES]
        self.assertEqual(ids, ["market-risk-sentiment", "market-scoreboard", "market-liquidity"])
        self.assertIn("market-liquidity", narrative.HEADLINES)


if __name__ == "__main__":
    unittest.main()

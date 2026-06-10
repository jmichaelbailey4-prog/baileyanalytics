import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


def _yr(a, b):
    """Two observations a year apart so market_level resolves a prior value."""
    return [("2020-01-01", a), ("2021-01-01", b)]


class TestMarketConfig(unittest.TestCase):
    def test_three_fred_market_lenses(self):
        ids = [l.id for l in config.MARKET_FRED_LENSES]
        self.assertEqual(ids, ["market-risk-sentiment", "market-scoreboard", "market-liquidity"])

    def test_risk_sentiment_series(self):
        risk = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-risk-sentiment")
        series = {i.series_id for i in risk.indicators}
        self.assertEqual(series, {"VIXCLS", "BAMLH0A0HYM2", "BAMLC0A0CM", "NFCI"})

    def test_scoreboard_has_six_assets_incl_crypto(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertEqual(series,
            {"SP500", "DCOILWTICO", "XAUUSD", "DTWEXBGS", "CBBTCUSD", "CBETHUSD"})

    def test_scoreboard_has_no_treasury_series(self):
        # Rates are owned by Cost of Money; the scoreboard must not duplicate them.
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertNotIn("DGS10", series)
        self.assertNotIn("DGS2", series)

    def test_gold_is_stooq_sourced(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        gold = next(i for i in board.indicators if i.id == "gold")
        self.assertEqual(gold.source, "yahoo")
        self.assertEqual(gold.series_id, "XAUUSD")

    def test_other_scoreboard_assets_are_fred(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        non_gold = [i for i in board.indicators if i.id != "gold"]
        self.assertTrue(all(i.source == "fred" for i in non_gold))

    def test_scoreboard_momentum_bands_are_per_asset(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        rules = {i.id: i.rule for i in board.indicators}
        # S&P 500: +/-5% band
        self.assertEqual(rules["sp500"](_yr(100.0, 103.0))[1], "flat")  # +3%
        self.assertEqual(rules["sp500"](_yr(100.0, 106.0))[1], "up")    # +6%
        # Dollar index: +/-3% band
        self.assertEqual(rules["dollar"](_yr(100.0, 102.0))[1], "flat") # +2%
        self.assertEqual(rules["dollar"](_yr(100.0, 96.0))[1], "down")  # -4%
        # WTI oil: +/-15% band
        self.assertEqual(rules["oil"](_yr(100.0, 110.0))[1], "flat")    # +10%
        self.assertEqual(rules["oil"](_yr(100.0, 120.0))[1], "up")      # +20%
        # Bitcoin: +/-25% band
        self.assertEqual(rules["btc"](_yr(100.0, 120.0))[1], "flat")    # +20%
        self.assertEqual(rules["btc"](_yr(100.0, 130.0))[1], "up")      # +30%

    def test_ice_spread_indicators_use_short_window(self):
        risk = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-risk-sentiment")
        by_id = {i.id: i for i in risk.indicators}
        for ind_id in ("hy-spread", "ig-spread"):
            ind = by_id[ind_id]
            self.assertEqual(ind.limit, 900)
            self.assertIn("rolling", ind.context.lower())

    def test_markets_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "markets")
        self.assertEqual(cat["out"], "markets")
        self.assertEqual(cat["disclaimer"], "")


if __name__ == "__main__":
    unittest.main()

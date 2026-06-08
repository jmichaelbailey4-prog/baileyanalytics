import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestMarketConfig(unittest.TestCase):
    def test_two_fred_market_lenses(self):
        ids = [l.id for l in config.MARKET_FRED_LENSES]
        self.assertEqual(ids, ["market-risk-sentiment", "market-scoreboard"])

    def test_risk_sentiment_series(self):
        risk = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-risk-sentiment")
        series = {i.series_id for i in risk.indicators}
        self.assertEqual(series, {"VIXCLS", "BAMLH0A0HYM2", "BAMLC0A0CM", "NFCI"})

    def test_scoreboard_has_six_assets_incl_crypto(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertEqual(series,
            {"SP500", "DCOILWTICO", "GOLDAMGBD228NLBM", "DTWEXBGS", "CBBTCUSD", "CBETHUSD"})

    def test_scoreboard_has_no_treasury_series(self):
        # Rates are owned by Cost of Money; the scoreboard must not duplicate them.
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        series = {i.series_id for i in board.indicators}
        self.assertNotIn("DGS10", series)
        self.assertNotIn("DGS2", series)

    def test_markets_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "markets")
        self.assertEqual(cat["out"], "markets")
        self.assertEqual(cat["disclaimer"], "")


if __name__ == "__main__":
    unittest.main()

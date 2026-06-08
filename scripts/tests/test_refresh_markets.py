import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config


class TestMarketsDryRun(unittest.TestCase):
    def _build(self):
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        return [build.build_lens(l, fetched) for l in config.MARKET_FRED_LENSES]

    def test_builds_two_fred_market_lenses(self):
        jsons = self._build()
        self.assertEqual({j["id"] for j in jsons},
                         {"market-risk-sentiment", "market-scoreboard"})

    def test_scoreboard_status_is_neutral_and_has_momentum_signals(self):
        board = next(j for j in self._build() if j["id"] == "market-scoreboard")
        self.assertEqual(board["status"], "neutral")
        statuses = {i["signal_status"] for i in board["indicators"]}
        self.assertTrue(statuses <= {"up", "down", "flat"})

    def test_markets_flag_runs_dry(self):
        # Redirect output to a temp dir so the dry-run never clobbers tracked
        # data/markets/ files (both the lens dir and the crypto-history file).
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig_dir, orig_hist = refresh_lenses.MARKETS_OUT_DIR, refresh_lenses.CRYPTO_HISTORY
            refresh_lenses.MARKETS_OUT_DIR = tmp
            refresh_lenses.CRYPTO_HISTORY = tmp / "_crypto_history.json"
            try:
                rc = refresh_lenses.main(["--markets", "--dry-run"])
            finally:
                refresh_lenses.MARKETS_OUT_DIR = orig_dir
                refresh_lenses.CRYPTO_HISTORY = orig_hist
        self.assertEqual(rc, 0)


class TestCryptoBuild(unittest.TestCase):
    def test_build_crypto_offline(self):
        fresh = json.loads(refresh_lenses.CRYPTO_FIXTURE.read_text(encoding="utf-8"))
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        btc_eth = refresh_lenses._btc_eth_ratio(fetched)
        lj = build.build_crypto_lens(fresh["rotation"], [fresh["dominance_point"]], btc_eth)
        self.assertEqual(lj["id"], "crypto-structure")
        self.assertTrue(lj["indicators"][2]["observations"])  # BTC/ETH ratio present

    def test_btc_eth_ratio_from_fred(self):
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        ratio = refresh_lenses._btc_eth_ratio(fetched)
        # 65000 / 3100 ≈ 20.97 on the latest shared date
        self.assertAlmostEqual(ratio[-1]["value"], 65000.0 / 3100.0, places=2)


if __name__ == "__main__":
    unittest.main()

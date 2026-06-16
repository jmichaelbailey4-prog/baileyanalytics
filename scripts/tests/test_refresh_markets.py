import sys
import pathlib
import json
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config, coingecko


class TestMarketsDryRun(unittest.TestCase):
    def _build(self):
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        return [build.build_lens(l, fetched) for l in config.MARKET_FRED_LENSES]

    def test_builds_three_fred_market_lenses(self):
        jsons = self._build()
        self.assertEqual({j["id"] for j in jsons},
                         {"market-risk-sentiment", "market-scoreboard", "market-liquidity"})

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


class TestCryptoDominanceNullGuard(unittest.TestCase):
    """A successful /global response that omits BTC dominance returns
    dominance_point.value == None (no exception, so the caller's fallback never
    fires). That None must NOT be merged into the accumulated history — its date
    key never recurs, so it would persist forever (the bug merge_series exists to
    avoid). Rotation must still accumulate, and prior dominance be preserved."""

    def _run_with_dominance(self, value):
        fetched = json.loads(refresh_lenses.MARKET_FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            hist_path = tmp / "_crypto_history.json"
            hist_path.write_text(json.dumps({
                "rotation": [{"date": "2026-06-10", "value": 100.0}],
                "dominance": [{"date": "2026-06-10", "value": 56.0}],
            }), encoding="utf-8")
            fresh = {"rotation": [{"date": "2026-06-11", "value": 101.0}],
                     "dominance_point": {"date": "2026-06-11", "value": value}}
            orig_dir, orig_hist = refresh_lenses.MARKETS_OUT_DIR, refresh_lenses.CRYPTO_HISTORY
            refresh_lenses.MARKETS_OUT_DIR = tmp
            refresh_lenses.CRYPTO_HISTORY = hist_path
            try:
                with mock.patch.object(coingecko, "crypto_market_structure", return_value=fresh):
                    refresh_lenses._build_crypto(False, fetched)
                return json.loads(hist_path.read_text(encoding="utf-8"))
            finally:
                refresh_lenses.MARKETS_OUT_DIR = orig_dir
                refresh_lenses.CRYPTO_HISTORY = orig_hist

    def test_none_dominance_not_baked_prior_preserved(self):
        saved = self._run_with_dominance(None)
        self.assertNotIn(None, [p["value"] for p in saved["dominance"]])
        self.assertEqual(saved["dominance"], [{"date": "2026-06-10", "value": 56.0}])
        self.assertEqual(len(saved["rotation"]), 2)  # rotation still accumulates

    def test_real_dominance_still_accumulates(self):
        saved = self._run_with_dominance(54.0)
        self.assertEqual(saved["dominance"],
                         [{"date": "2026-06-10", "value": 56.0},
                          {"date": "2026-06-11", "value": 54.0}])


if __name__ == "__main__":
    unittest.main()

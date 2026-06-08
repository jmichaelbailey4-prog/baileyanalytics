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
        rc = refresh_lenses.main(["--markets", "--dry-run"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

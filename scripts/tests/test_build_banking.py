import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config


class TestBuildBanking(unittest.TestCase):
    def _build(self):
        lens = config.BANK_ASSET_QUALITY
        series = {
            "noncurrent": [{"date": "2024-12-31", "value": "0.68"}],
            "charge-offs": [{"date": "2024-12-31", "value": "0.60"}],
        }
        tier_rows = [
            {"tier": "Community (<$10B)", "values": [{"value": 1.1}, {"value": 0.4}]},
            {"tier": "Large (>$250B)", "values": [{"value": 0.6}, {"value": 0.5}]},
        ]
        ranking_rows = {"Highest commercial-real-estate delinquency":
                        [{"name": "X BANK", "location": "Denver, CO", "asset": "$3.2B", "value": 6.4}]}
        return build.build_banking_lens(lens, series, tier_rows, ranking_rows)

    def test_assembles_indicators(self):
        out = self._build()
        self.assertEqual(out["id"], "bank-asset-quality")
        self.assertEqual(len(out["indicators"]), 2)
        self.assertEqual(out["indicators"][0]["signal_status"], "ok")  # 0.68% noncurrent
        self.assertTrue(out["headline_read"])

    def test_tiers_formatted_with_status(self):
        out = self._build()
        self.assertEqual(out["tiers"]["columns"][0]["label"], "Noncurrent")
        first = out["tiers"]["rows"][0]
        self.assertEqual(first["tier"], "Community (<$10B)")
        self.assertEqual(first["values"][0]["value"], "1.10%")
        self.assertEqual(first["values"][0]["status"], "watch")  # 1.1% noncurrent -> watch

    def test_rankings_formatted_with_status(self):
        out = self._build()
        rk = out["rankings"][0]
        self.assertEqual(rk["rows"][0]["name"], "X BANK")
        self.assertEqual(rk["rows"][0]["value"], "6.40%")
        self.assertEqual(rk["rows"][0]["status"], "elevated")  # 6.4% via rule_noncurrent


if __name__ == "__main__":
    unittest.main()

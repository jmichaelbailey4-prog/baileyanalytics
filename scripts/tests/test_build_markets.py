import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build


class TestBuildCryptoLens(unittest.TestCase):
    def setUp(self):
        self.rotation = [{"date": "2026-01-01", "value": 100.0},
                         {"date": "2026-04-01", "value": 108.0}]
        self.dominance = [{"date": "2026-04-01", "value": 54.0}]
        self.btc_eth = [{"date": "2026-04-01", "value": 20.5}]

    def test_shape_and_ids(self):
        lj = build.build_crypto_lens(self.rotation, self.dominance, self.btc_eth)
        self.assertEqual(lj["id"], "crypto-structure")
        self.assertEqual(lj["status"], "neutral")
        ids = [i["id"] for i in lj["indicators"]]
        self.assertEqual(ids, ["crypto-rotation", "btc-dominance", "btc-eth-ratio"])
        self.assertEqual(lj["indicators"][0]["observations"], self.rotation)
        self.assertEqual(lj["indicators"][0]["latest"]["value"], 108.0)

    def test_renders_in_index(self):
        lj = build.build_crypto_lens(self.rotation, self.dominance, self.btc_eth)
        idx = build.build_index([lj])
        self.assertEqual(idx["lenses"][0]["id"], "crypto-structure")
        self.assertTrue(idx["lenses"][0]["sparkline"])


if __name__ == "__main__":
    unittest.main()

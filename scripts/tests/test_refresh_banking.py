import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBankingDryRun(unittest.TestCase):
    def test_builds_four_banking_lenses_offline(self):
        jsons = refresh_lenses.build_banking_from_fixture()
        self.assertEqual(len(jsons), 4)
        ids = {j["id"] for j in jsons}
        self.assertEqual(ids, {"bank-asset-quality", "bank-profitability",
                               "bank-capital-solvency", "bank-concentrations-funding"})

    def test_asset_quality_has_series_and_tiers(self):
        jsons = refresh_lenses.build_banking_from_fixture()
        aq = next(j for j in jsons if j["id"] == "bank-asset-quality")
        self.assertTrue(aq["indicators"][0]["observations"])
        self.assertIsNotNone(aq["tiers"])
        self.assertTrue(aq["rankings"][0]["rows"])


if __name__ == "__main__":
    unittest.main()

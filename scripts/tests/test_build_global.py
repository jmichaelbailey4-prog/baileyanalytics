import json
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config, imf

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "global_sample.json"


class TestFmtGlobal(unittest.TestCase):
    def test_negative_money_sign_before_dollar(self):
        self.assertEqual(build._fmt("-55.9", "$B"), "-$55.90B")

    def test_negative_thousands_money(self):
        self.assertEqual(build._fmt("-1500", "$B", "thousands"), "-$1,500B")

    def test_positive_money_unchanged(self):
        self.assertEqual(build._fmt("2.4", "$T"), "$2.40T")
        self.assertEqual(build._fmt("4.15", "$"), "$4.15")

    def test_sigma_unit_stays_tight(self):
        self.assertEqual(build._fmt("1.77", "σ"), "1.77σ")

    def test_word_unit_keeps_space(self):
        self.assertEqual(build._fmt("9.4", "months"), "9.40 months")

    def test_negative_percent(self):
        self.assertEqual(build._fmt("-0.9", "%"), "-0.90%")


class TestGlobalBuildIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fetched = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls._saved = dict(imf.FORECASTS)
        imf.FORECASTS.clear()
        imf.FORECASTS.update(fetched.get("_forecasts", {}))
        cls.built = {lens.id: build.build_lens(lens, fetched)
                     for lens in config.GLOBAL_LENSES}

    @classmethod
    def tearDownClass(cls):
        imf.FORECASTS.clear()
        imf.FORECASTS.update(cls._saved)

    def test_all_four_lenses_build(self):
        self.assertEqual(set(self.built),
                         {"global-dollar-currencies", "global-growth",
                          "global-trade-supply", "global-uncertainty"})
        for lj in self.built.values():
            self.assertTrue(lj["indicators"], lj["id"])
            for ind in lj["indicators"]:
                self.assertIsNotNone(ind["latest"], ind["id"])

    def test_expected_statuses(self):
        self.assertEqual(self.built["global-dollar-currencies"]["status"], "ok")
        self.assertEqual(self.built["global-growth"]["status"], "watch")
        self.assertEqual(self.built["global-trade-supply"]["status"], "elevated")
        self.assertEqual(self.built["global-uncertainty"]["status"], "alert")

    def test_trade_balance_derived_to_billions(self):
        trade = self.built["global-trade-supply"]
        bal = next(i for i in trade["indicators"] if i["id"] == "trade-balance")
        self.assertEqual(bal["latest"]["value"], "-55.9")
        self.assertEqual(bal["unit"], "$B")

    def test_world_growth_read_mentions_forecast(self):
        growth = self.built["global-growth"]
        world = next(i for i in growth["indicators"] if i["id"] == "world-growth")
        self.assertIn("IMF projects 3.2% for 2027", world["read"])

    def test_annual_observations_survive_as_years(self):
        growth = self.built["global-growth"]
        world = next(i for i in growth["indicators"] if i["id"] == "world-growth")
        for o in world["observations"]:
            self.assertRegex(o["date"], r"^\d{4}$")
        self.assertEqual(world["latest"]["date"], "2026")

    def test_hub_index_formats_key_stats(self):
        index = build.build_index(list(self.built.values()))
        by_id = {l["id"]: l for l in index["lenses"]}
        trade_stats = {s["k"]: s["v"]
                       for s in by_id["global-trade-supply"]["key_stats"]}
        self.assertEqual(trade_stats["Trade balance"], "-$55.90B")
        self.assertEqual(trade_stats["Supply chain"], "1.77σ")


if __name__ == "__main__":
    unittest.main()

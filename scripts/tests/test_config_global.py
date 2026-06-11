import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


SEVERITY = {"ok", "watch", "elevated", "alert", "unknown"}


class TestGlobalConfig(unittest.TestCase):
    def lens(self, lens_id):
        return next(l for l in config.GLOBAL_LENSES if l.id == lens_id)

    def test_four_lenses_in_order(self):
        ids = [l.id for l in config.GLOBAL_LENSES]
        self.assertEqual(ids, ["global-dollar-currencies", "global-growth",
                               "global-trade-supply", "global-uncertainty"])

    def test_source_map(self):
        sources = {}
        for lens in config.GLOBAL_LENSES:
            for ind in lens.indicators:
                sources[ind.id] = ind.source
        self.assertEqual(sources["dollar-yoy"], "fred")
        self.assertEqual(sources["euro"], "fred")
        self.assertEqual(sources["world-growth"], "imf")
        self.assertEqual(sources["china-growth"], "imf")
        self.assertEqual(sources["euro-growth"], "imf")
        self.assertEqual(sources["world-inflation"], "imf")
        self.assertEqual(sources["ea-gdp-quarterly"], "fred")
        self.assertEqual(sources["gscpi"], "nyfed")
        self.assertEqual(sources["trade-balance"], "fred")
        self.assertEqual(sources["import-prices"], "fred")
        self.assertEqual(sources["china-exports"], "fred")
        self.assertEqual(sources["us-epu"], "epu")
        self.assertEqual(sources["gepu"], "epu")

    def test_imf_indicators_carry_dotted_imf_key(self):
        for lens in config.GLOBAL_LENSES:
            for ind in lens.indicators:
                if ind.source == "imf":
                    self.assertIn(".", ind.imf_key, ind.id)
                else:
                    self.assertEqual(ind.imf_key, "", ind.id)

    def test_world_growth_imf_key(self):
        growth = self.lens("global-growth")
        world = next(i for i in growth.indicators if i.id == "world-growth")
        self.assertEqual(world.imf_key, "G001.NGDP_RPCH")
        self.assertEqual(world.series_id, "WEO_G001_NGDP_RPCH")

    def test_dtwexbgs_lives_only_in_global(self):
        homes = []
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                for ind in lens.indicators:
                    if getattr(ind, "series_id", "") == "DTWEXBGS":
                        homes.append((cat["id"], lens.id))
        self.assertEqual(homes, [("global", "global-dollar-currencies")])

    def test_dollar_yoy_is_pc1(self):
        dollar = self.lens("global-dollar-currencies").indicators[0]
        self.assertEqual(dollar.id, "dollar-yoy")
        self.assertEqual(dollar.units_transform, "pc1")
        self.assertEqual(dollar.unit, "%")

    def test_scoreboard_has_five_indicators(self):
        board = next(l for l in config.MARKET_FRED_LENSES if l.id == "market-scoreboard")
        self.assertEqual(len(board.indicators), 5)

    def test_category_registered(self):
        cat = next(c for c in config.CATEGORIES if c["id"] == "global")
        self.assertEqual(cat["out"], "global")
        self.assertEqual(cat["title"], "Global Economy")
        self.assertEqual(cat["back"], "Global Economy")
        self.assertEqual(cat["source_label"],
                         "FRED, IMF World Economic Outlook, NY Fed, and policyuncertainty.com")
        self.assertEqual(cat["disclaimer"], "")
        self.assertIs(cat["lenses"], config.GLOBAL_LENSES)

    def test_lead_indicators_return_severity(self):
        cases = {
            "global-dollar-currencies": [("2025-05", 0.0), ("2026-05", 13.0)],
            "global-growth": [("2025", 3.4), ("2026", 3.06)],
            "global-trade-supply": [("2026-04", 0.7), ("2026-05", 1.77)],
            "global-uncertainty": [("2026-04", 412.0), ("2026-05", 296.0)],
        }
        for lens_id, obs in cases.items():
            lead = self.lens(lens_id).indicators[0]
            _, status = lead.rule(obs)
            self.assertIn(status, SEVERITY, lens_id)
            self.assertNotEqual(status, "unknown", lens_id)

    def test_trade_balance_scaled_to_billions(self):
        trade = self.lens("global-trade-supply")
        bal = next(i for i in trade.indicators if i.id == "trade-balance")
        self.assertEqual(bal.unit, "$B")
        self.assertIsNotNone(bal.derive)
        derived = bal.derive([{"date": "2026-04", "value": "-55900"}])
        # scaled(-1000, 1): negative balance -> positive deficit size
        self.assertEqual(derived[0]["value"], "55.9")

    def test_uncertainty_value_format_thousands(self):
        unc = self.lens("global-uncertainty")
        for ind in unc.indicators:
            self.assertEqual(ind.value_format, "thousands", ind.id)


if __name__ == "__main__":
    unittest.main()

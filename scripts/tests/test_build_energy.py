import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "energy_sample.json"


def _fetched():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestBuildEnergy(unittest.TestCase):
    def test_all_four_lenses_build(self):
        fetched = _fetched()
        jsons = [build.build_lens(l, fetched) for l in config.ENERGY_LENSES]
        self.assertEqual([j["id"] for j in jsons],
                         ["energy-oil-fuels", "energy-natural-gas",
                          "energy-electricity", "energy-commodities"])

    def test_oil_lens_badge_is_severity_from_gasoline(self):
        fetched = _fetched()
        oil = build.build_lens(config.ENERGY_OIL_FUELS, fetched)
        # gasoline +22.6% -> watch (band 10/25/40); badge should be a severity token
        self.assertIn(oil["status"], {"ok", "watch", "elevated", "alert"})
        gas = next(i for i in oil["indicators"] if i["id"] == "gasoline")
        self.assertEqual(gas["signal_status"], "watch")

    def test_physical_indicators_are_info(self):
        fetched = _fetched()
        oil = build.build_lens(config.ENERGY_OIL_FUELS, fetched)
        prod = next(i for i in oil["indicators"] if i["id"] == "crude-production")
        self.assertEqual(prod["signal_status"], "info")

    def test_electricity_shares_present(self):
        fetched = _fetched()
        elec = build.build_lens(config.ENERGY_ELECTRICITY, fetched)
        renew = next(i for i in elec["indicators"] if i["id"] == "renewables-share")
        self.assertTrue(renew["observations"])
        self.assertEqual(renew["signal_status"], "info")


if __name__ == "__main__":
    unittest.main()

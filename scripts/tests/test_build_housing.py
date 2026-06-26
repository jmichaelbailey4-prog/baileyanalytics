import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "housing_sample.json"


def _fetched():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestBuildHousing(unittest.TestCase):
    def test_all_four_lenses_build(self):
        jsons = [build.build_lens(l, _fetched()) for l in config.HOUSING_LENSES]
        self.assertEqual([j["id"] for j in jsons],
                         ["housing-home-prices", "housing-affordability",
                          "housing-supply-construction", "housing-rent-shelter"])

    def test_home_prices_badge_is_elevated_hot(self):
        lj = build.build_lens(config.HOUSING_HOME_PRICES, _fetched())
        cs = next(i for i in lj["indicators"] if i["id"] == "case-shiller")
        self.assertEqual(cs["signal_status"], "elevated")  # +10% YoY, hot band
        self.assertEqual(lj["status"], "elevated")

    def test_affordability_badge_from_drivers(self):
        lj = build.build_lens(config.HOUSING_AFFORDABILITY, _fetched())
        self.assertEqual(lj["status"], "elevated")  # mortgage 6.84 + FIXHAI 105.6
        ds = next(i for i in lj["indicators"] if i["id"] == "debt-service")
        self.assertEqual(ds["signal_status"], "ok")  # MDSP now scored; 5.92% is below its median

    def test_supply_glut_is_elevated(self):
        lj = build.build_lens(config.HOUSING_SUPPLY_CONSTRUCTION, _fetched())
        ms = next(i for i in lj["indicators"] if i["id"] == "months-supply")
        self.assertEqual(ms["signal_status"], "elevated")  # 9.4 months = glut

    def test_home_sales_derived_to_millions(self):
        lj = build.build_lens(config.HOUSING_HOME_PRICES, _fetched())
        sales = next(i for i in lj["indicators"] if i["id"] == "existing-home-sales")
        self.assertEqual(sales["latest"]["value"], "4.17")  # 4,170,000 -> 4.17M
        self.assertEqual(sales["unit"], "M")

    def test_rent_shelter_watch_from_rent_cpi(self):
        lj = build.build_lens(config.HOUSING_RENT_SHELTER, _fetched())
        self.assertEqual(lj["status"], "watch")  # rent +4.4% YoY


if __name__ == "__main__":
    unittest.main()

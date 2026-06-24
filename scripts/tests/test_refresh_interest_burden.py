"""The fiscal interest-burden computed series (interest / receipts) is injected
from already-fetched inputs and reads as a scored signal."""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config


def _fixture():
    return json.loads(refresh_lenses.FIXTURE.read_text(encoding="utf-8"))


class InterestBurdenInjectionTest(unittest.TestCase):
    def test_inject_adds_spread_and_burden(self):
        fetched = _fixture()
        refresh_lenses._inject_economic_computed(fetched, refresh_lenses.OUT_DIR)
        self.assertTrue(fetched["DGS2_FEDFUNDS_SPREAD:lin"])      # unchanged behavior
        self.assertTrue(fetched["INTEREST_RECEIPTS_SHARE:lin"])  # new computed series

    def test_burden_builds_into_a_scored_indicator(self):
        fetched = _fixture()
        refresh_lenses._inject_economic_computed(fetched, refresh_lenses.OUT_DIR)
        lj = build.build_lens(config.FISCAL_HEALTH, fetched)
        burden = next(i for i in lj["indicators"] if i["id"] == "interest-burden")
        self.assertIn(burden["signal_status"], {"ok", "watch", "elevated", "alert"})
        self.assertTrue(10 < float(burden["latest"]["value"]) < 30)  # ~19% on the fixture


if __name__ == "__main__":
    unittest.main()

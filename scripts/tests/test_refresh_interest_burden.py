"""The fiscal interest-burden computed series (interest / receipts) is injected
from already-fetched inputs and reads as a scored signal."""

import json
import pathlib
import sys
import unittest
from unittest import mock

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
        # interest / TOTAL receipts (W018) ~ 1041/5917 = 17.6% on the fixture
        self.assertTrue(15 < float(burden["latest"]["value"]) < 22)


class LiveTotalReceiptsFetchTest(unittest.TestCase):
    """The live path fetches W018 (total receipts) on demand — only the dry-run
    branch is fixture-fed, so cover the fetch wiring + its failure fallback."""

    def _fetched_without_w018(self):
        fetched = _fixture()
        fetched.pop("W018RC1Q027SBEA:lin", None)  # force the on-demand fetch
        return fetched

    def test_live_branch_fetches_total_receipts_by_id(self):
        fetched = self._fetched_without_w018()
        fake = [{"date": "2025-01-01", "value": "5650"},
                {"date": "2026-01-01", "value": "5917"}]
        with mock.patch.object(refresh_lenses.fred, "fetch_observations",
                               return_value=fake) as m:
            refresh_lenses._inject_economic_computed(fetched, refresh_lenses.OUT_DIR, "KEY")
        m.assert_called_once()
        self.assertEqual(m.call_args[0][0], "W018RC1Q027SBEA")  # right series id
        self.assertTrue(fetched["INTEREST_RECEIPTS_SHARE:lin"])

    def test_live_fetch_failure_degrades_without_crash(self):
        fetched = self._fetched_without_w018()
        with mock.patch.object(refresh_lenses.fred, "fetch_observations",
                               side_effect=Exception("boom")):
            refresh_lenses._inject_economic_computed(fetched, refresh_lenses.OUT_DIR, "KEY")
        # falls back to prior baked obs (empty here) — key present, no exception raised
        self.assertIn("INTEREST_RECEIPTS_SHARE:lin", fetched)


if __name__ == "__main__":
    unittest.main()

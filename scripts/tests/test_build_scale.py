"""build.py bakes a per-signal scale_now (the rule's decision-axis value) for the
in-context scoring strip — only for scored indicators, and consistent with the
baked status."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import bands, build, config  # noqa: E402

FIX = pathlib.Path(__file__).parent / "fixtures" / "fetched_sample.json"
FDIC_FIX = pathlib.Path(__file__).parent / "fixtures" / "fdic_sample.json"


def _ind(lens_json, ind_id):
    return next(i for i in lens_json["indicators"] if i["id"] == ind_id)


class TestScaleNow(unittest.TestCase):
    def setUp(self):
        self.fetched = json.loads(FIX.read_text(encoding="utf-8"))
        self.by_id = {l.id: l for l in config.LENSES}

    def test_severity_indicator_has_scale_now(self):
        lj = build.build_lens(self.by_id["cost-of-living"], self.fetched)
        cpi = _ind(lj, "cpi")
        self.assertIn("scale_now", cpi)
        self.assertIsInstance(cpi["scale_now"], (int, float))

    def test_scale_now_is_consistent_with_status(self):
        lj = build.build_lens(self.by_id["cost-of-living"], self.fetched)
        cpi = _ind(lj, "cpi")
        spec = next(i for i in config.COST_OF_LIVING.indicators if i.id == "cpi").rule.band_spec
        self.assertEqual(bands.status_at(spec, cpi["scale_now"]), cpi["signal_status"])

    def test_info_indicator_has_no_scale_now(self):
        lj = build.build_lens(self.by_id["job-market"], self.fetched)
        self.assertNotIn("scale_now", _ind(lj, "participation"))

    def test_custom_axis_indicator_has_no_scale_now(self):
        # yield-curve is kind="custom" (history-dependent) -> no static decision axis.
        lj = build.build_lens(self.by_id["recession-watch"], self.fetched)
        self.assertNotIn("scale_now", _ind(lj, "yield-curve"))


class TestYoyComputedScaleNow(unittest.TestCase):
    """The yoy_computed marker uses bands' own _value_year_ago; confirm the baked
    scale_now lands in the same band the rule scored (existing-home-sales = market_health)."""
    def test_yoy_computed_scale_now_matches_status(self):
        fetched = json.loads((pathlib.Path(__file__).parent / "fixtures"
                              / "housing_sample.json").read_text(encoding="utf-8"))
        lens = next(l for l in config.HOUSING_LENSES if l.id == "housing-home-prices")
        lj = build.build_lens(lens, fetched)
        ehs = _ind(lj, "existing-home-sales")
        spec = next(i for i in lens.indicators if i.id == "existing-home-sales").rule.band_spec
        self.assertEqual(spec.kind, "yoy_computed")
        self.assertIn("scale_now", ehs)
        self.assertEqual(bands.status_at(spec, ehs["scale_now"]), ehs["signal_status"])


class TestBankingScaleNow(unittest.TestCase):
    def test_banking_severity_indicator_has_scale_now(self):
        data = json.loads(FDIC_FIX.read_text(encoding="utf-8"))
        lens = config.BANK_ASSET_QUALITY
        series, tiers, rankings = data[lens.id]
        lj = build.build_banking_lens(lens, series, tiers, rankings)
        self.assertIn("scale_now", _ind(lj, "noncurrent"))


if __name__ == "__main__":
    unittest.main()

import json as _json
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, config


class TestConfig(unittest.TestCase):
    def test_recession_watch_lens_present(self):
        ids = [lens.id for lens in config.LENSES]
        self.assertIn("recession-watch", ids)

    def test_indicator_fetch_key(self):
        lens = next(l for l in config.LENSES if l.id == "recession-watch")
        ind = lens.indicators[0]
        self.assertEqual(ind.fetch_key, f"{ind.series_id}:lin")

    def test_every_indicator_has_rule_and_context(self):
        for lens in config.LENSES:
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)


def _load_fixture():
    p = pathlib.Path(__file__).resolve().parent / "fixtures" / "fetched_sample.json"
    return _json.loads(p.read_text(encoding="utf-8"))


class TestBuildLens(unittest.TestCase):
    def setUp(self):
        self.fetched = _load_fixture()
        self.lens_json = build.build_lens(config.RECESSION_WATCH, self.fetched)

    def test_top_level_shape(self):
        lj = self.lens_json
        self.assertEqual(lj["id"], "recession-watch")
        self.assertEqual(lj["status"], "watch")  # un-inverted curve + near-trigger Sahm
        self.assertIn("warning lights", lj["headline_read"])
        self.assertEqual(len(lj["indicators"]), 4)
        self.assertEqual(lj["recessions"], [{"start": "2020-02-01", "end": "2020-05-01"}])

    def test_indicator_shape(self):
        ind = self.lens_json["indicators"][0]
        self.assertEqual(ind["id"], "yield-curve")
        self.assertEqual(ind["latest"], {"date": "2026-06-02", "value": "0.30"})
        self.assertEqual(ind["signal_status"], "watch")
        self.assertTrue(ind["context"])
        self.assertIn("un-inverted", ind["read"])
        self.assertTrue(len(ind["observations"]) == 3)


class TestBuildIndex(unittest.TestCase):
    def test_index_entry(self):
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        idx = build.build_index([lj])
        entry = idx["lenses"][0]
        self.assertEqual(entry["id"], "recession-watch")
        self.assertEqual(entry["status"], "watch")
        self.assertEqual(entry["key_stats"][0]["k"], "Yield curve")
        self.assertTrue(entry["sparkline"])  # non-empty list of numbers

    def test_key_stats_carry_delta_vs_prior_observation(self):
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        stat = build.build_index([lj])["lenses"][0]["key_stats"][0]
        # fixture yield curve: 0.05 (2026-04-01) -> 0.30 (2026-06-02) => +0.25
        self.assertEqual(stat["d"], "0.25%")
        self.assertEqual(stat["dir"], "up")

    def test_no_delta_with_single_observation(self):
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        for ind in lj["indicators"]:
            ind["observations"] = ind["observations"][-1:]
        stat = build.build_index([lj])["lenses"][0]["key_stats"][0]
        self.assertNotIn("d", stat)
        self.assertNotIn("dir", stat)


class TestFmt(unittest.TestCase):
    """_fmt must mirror lens.js fmtVal: $ is a prefix, word units get a space,
    symbol units stay tight."""

    def test_percent_stays_tight(self):
        self.assertEqual(build._fmt("4.30", "%"), "4.30%")

    def test_dollar_is_prefix(self):
        self.assertEqual(build._fmt("4.146", "$"), "$4.15")

    def test_dollar_prefix_thousands(self):
        self.assertEqual(build._fmt("13484.2", "$", "thousands"), "$13,484")

    def test_word_unit_gets_space(self):
        self.assertEqual(build._fmt("9.4", "months"), "9.40 months")

    def test_capitalized_word_unit_gets_space(self):
        self.assertEqual(build._fmt("2578", "Bcf", "thousands"), "2,578 Bcf")

    def test_single_letter_unit_stays_tight(self):
        self.assertEqual(build._fmt("4.17", "M"), "4.17M")

    def test_dollar_compound_units_prefix_and_suffix(self):
        self.assertEqual(build._fmt("2.4", "$T"), "$2.40T")
        self.assertEqual(build._fmt("1012.3", "$B", "thousands"), "$1,012B")

    def test_missing_value(self):
        self.assertEqual(build._fmt(None, "%"), "—")


class TestFmtParityGoldens(unittest.TestCase):
    """The shared golden battery for the five formatting twins (build._fmt +
    the four JS fmtVal copies). The SAME table
    runs against lens.js / predict.js / scoring.js / track-record.js in
    scripts/tests/js/fmtval-parity.test.js — keep the two tables identical, so
    drifting any one twin turns a suite red on one side or the other."""

    GOLDENS = [
        (2578.5, "Bcf", "thousands", "2,579 Bcf"),   # half-up, the drift case
        (0.5, "", "thousands", "1"),
        (-55.9, "$B", "decimal", "-$55.90B"),
        (2.4, "$T", "decimal", "$2.40T"),
        (4.153, "$", "decimal", "$4.15"),
        (9.4, "months", "decimal", "9.40 months"),
        (4.17, "M", "decimal", "4.17M"),
        (215000, "", "thousands", "215,000"),
        (-1.234, "%", "decimal", "-1.23%"),
        (1.77, "σ", "decimal", "1.77σ"),
        (7483.24, "", "thousands", "7,483"),
    ]

    def test_goldens(self):
        for value, unit, vf, want in self.GOLDENS:
            self.assertEqual(build._fmt(value, unit, vf), want,
                             f"_fmt({value!r}, {unit!r}, {vf!r})")


class TestWriteOutputs(unittest.TestCase):
    def test_skips_unchanged_file(self):
        import tempfile
        lj = build.build_lens(config.RECESSION_WATCH, _load_fixture())
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d)
            first = build.write_lens_file(out / "recession-watch.json", lj)
            second = build.write_lens_file(out / "recession-watch.json", lj)
            self.assertTrue(first)    # wrote
            self.assertFalse(second)  # unchanged -> skipped


class TestBuildCostOfMoney(unittest.TestCase):
    def test_builds_with_four_indicators(self):
        # 3 policy rates + the computed rate-expectations spread
        lj = build.build_lens(config.COST_OF_MONEY, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-money")
        self.assertEqual(len(lj["indicators"]), 4)
        self.assertEqual(lj["status"], "watch")  # fed funds 4.33 >= 4.0
        ids = [i["id"] for i in lj["indicators"]]
        self.assertNotIn("yield-curve", ids)
        self.assertNotIn("mortgage-30y", ids)


class TestBuildJobMarket(unittest.TestCase):
    def test_builds_with_derived_payrolls(self):
        lj = build.build_lens(config.JOB_MARKET, _load_fixture())
        self.assertEqual(lj["id"], "job-market")
        self.assertEqual(len(lj["indicators"]), 6)  # + quits (2026-07-03)
        payrolls = next(i for i in lj["indicators"] if i["id"] == "payrolls")
        self.assertEqual(payrolls["latest"], {"date": "2026-05-01", "value": "177000"})
        self.assertEqual(payrolls["value_format"], "thousands")


class TestBuildCostOfLiving(unittest.TestCase):
    def test_builds_with_four_indicators(self):
        lj = build.build_lens(config.COST_OF_LIVING, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-living")
        self.assertEqual(len(lj["indicators"]), 5)  # + core PCE (2026-07-03)
        self.assertEqual(lj["status"], "watch")


if __name__ == "__main__":
    unittest.main()

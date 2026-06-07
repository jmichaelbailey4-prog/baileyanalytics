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
    def test_builds_with_five_indicators(self):
        lj = build.build_lens(config.COST_OF_MONEY, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-money")
        self.assertEqual(len(lj["indicators"]), 5)
        self.assertEqual(lj["status"], "watch")


class TestBuildJobMarket(unittest.TestCase):
    def test_builds_with_derived_payrolls(self):
        lj = build.build_lens(config.JOB_MARKET, _load_fixture())
        self.assertEqual(lj["id"], "job-market")
        self.assertEqual(len(lj["indicators"]), 5)
        payrolls = next(i for i in lj["indicators"] if i["id"] == "payrolls")
        self.assertEqual(payrolls["latest"], {"date": "2026-05-01", "value": "177000"})
        self.assertEqual(payrolls["value_format"], "thousands")


class TestBuildCostOfLiving(unittest.TestCase):
    def test_builds_with_four_indicators(self):
        lj = build.build_lens(config.COST_OF_LIVING, _load_fixture())
        self.assertEqual(lj["id"], "cost-of-living")
        self.assertEqual(len(lj["indicators"]), 3)
        self.assertEqual(lj["status"], "watch")


if __name__ == "__main__":
    unittest.main()

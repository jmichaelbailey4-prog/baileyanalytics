import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestHousingDryRun(unittest.TestCase):
    def test_housing_flag_runs_dry_into_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.HOUSING_OUT_DIR
            refresh_lenses.HOUSING_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--housing", "--dry-run"])
            finally:
                refresh_lenses.HOUSING_OUT_DIR = orig
            self.assertEqual(rc, 0)
            for name in ("housing-home-prices.json", "housing-affordability.json",
                         "housing-supply-construction.json", "housing-rent-shelter.json",
                         "index.json"):
                self.assertTrue((tmp / name).exists(), name)


class TestWindowedAccumulation(unittest.TestCase):
    def test_affordability_history_accumulates_across_refreshes(self):
        """FRED serves FIXHAI only as a rolling ~14-month window (NAR licensing,
        audit 2026-07-03). A refresh must MERGE the fresh window with prior baked
        observations, so months we already published can never fall off the site."""
        import json
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.HOUSING_OUT_DIR
            refresh_lenses.HOUSING_OUT_DIR = tmp
            try:
                self.assertEqual(refresh_lenses.main(["--housing", "--dry-run"]), 0)
                path = tmp / "housing-affordability.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                ind = next(i for i in data["indicators"] if i["id"] == "affordability-index")
                # Simulate a previously-published month older than the fetch window.
                ind["observations"].insert(0, {"date": "2019-01-01", "value": "160.0"})
                path.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(refresh_lenses.main(["--housing", "--dry-run"]), 0)
                data2 = json.loads(path.read_text(encoding="utf-8"))
                ind2 = next(i for i in data2["indicators"] if i["id"] == "affordability-index")
                dates = [o["date"] for o in ind2["observations"]]
                self.assertIn("2019-01-01", dates)          # old month survives
                self.assertEqual(dates, sorted(dates))       # still chronological
            finally:
                refresh_lenses.HOUSING_OUT_DIR = orig


if __name__ == "__main__":
    unittest.main()

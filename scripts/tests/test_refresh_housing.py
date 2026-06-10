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


if __name__ == "__main__":
    unittest.main()

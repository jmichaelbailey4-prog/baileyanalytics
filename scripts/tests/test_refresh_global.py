import sys
import pathlib
import json
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import imf


class TestGlobalDryRun(unittest.TestCase):
    def run_dry(self):
        """Run --global --dry-run with every out-dir pointed at a tempdir."""
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            dirs = {}
            for name in ("OUT_DIR", "BANK_OUT_DIR", "MARKETS_OUT_DIR",
                         "ENERGY_OUT_DIR", "HOUSING_OUT_DIR",
                         "CONSUMER_OUT_DIR", "BRIEF_OUT_DIR", "GLOBAL_OUT_DIR"):
                dirs[name] = getattr(refresh_lenses, name)
                setattr(refresh_lenses, name, tmp / name.lower())
            saved_forecasts = dict(imf.FORECASTS)
            imf.FORECASTS.clear()
            try:
                rc = refresh_lenses.main(["--global", "--dry-run"])
                global_dir = refresh_lenses.GLOBAL_OUT_DIR
                written = sorted(p.name for p in global_dir.glob("*.json"))
                others = [n for n in dirs
                          if n != "GLOBAL_OUT_DIR"
                          and getattr(refresh_lenses, n).exists()
                          and any(getattr(refresh_lenses, n).iterdir())]
                forecasts = dict(imf.FORECASTS)
            finally:
                for name, orig in dirs.items():
                    setattr(refresh_lenses, name, orig)
                imf.FORECASTS.clear()
                imf.FORECASTS.update(saved_forecasts)
            return rc, written, others, forecasts

    def test_writes_four_lenses_plus_index(self):
        rc, written, _, _ = self.run_dry()
        self.assertEqual(rc, 0)
        self.assertEqual(written,
                         ["global-dollar-currencies.json", "global-growth.json",
                          "global-trade-supply.json", "global-uncertainty.json",
                          "index.json"])

    def test_dry_run_populates_forecasts(self):
        _, _, _, forecasts = self.run_dry()
        self.assertIn("G001.NGDP_RPCH", forecasts)
        self.assertEqual(forecasts["G001.NGDP_RPCH"]["year"], "2026")

    def test_scoped_run_leaves_other_categories_alone(self):
        _, _, others, _ = self.run_dry()
        self.assertEqual(others, [])


class TestPriorObsGeneralization(unittest.TestCase):
    def test_prior_obs_reads_any_out_dir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            (tmp / "global-trade-supply.json").write_text(json.dumps({
                "indicators": [{"id": "gscpi",
                                "observations": [{"date": "2026-04", "value": "1.81"}]}]
            }), encoding="utf-8")
            obs = refresh_lenses._prior_obs(tmp, "global-trade-supply", "gscpi")
            self.assertEqual(obs, [{"date": "2026-04", "value": "1.81"}])
            self.assertEqual(refresh_lenses._prior_obs(tmp, "missing", "x"), [])


if __name__ == "__main__":
    unittest.main()

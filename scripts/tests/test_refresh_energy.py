import sys
import pathlib
import json
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses
from lenses import build, config


class TestEnergyDryRun(unittest.TestCase):
    def _build(self):
        fetched = json.loads(refresh_lenses.ENERGY_FIXTURE.read_text(encoding="utf-8"))
        return [build.build_lens(l, fetched) for l in config.ENERGY_LENSES]

    def test_builds_four_energy_lenses(self):
        ids = {j["id"] for j in self._build()}
        self.assertEqual(ids, {"energy-oil-fuels", "energy-natural-gas",
                               "energy-electricity", "energy-commodities"})

    def test_energy_flag_runs_dry_into_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.ENERGY_OUT_DIR
            refresh_lenses.ENERGY_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--energy", "--dry-run"])
            finally:
                refresh_lenses.ENERGY_OUT_DIR = orig
            self.assertEqual(rc, 0)
            self.assertTrue((tmp / "energy-oil-fuels.json").exists())
            self.assertTrue((tmp / "index.json").exists())


class TestGenerationShareInjection(unittest.TestCase):
    def test_pct_share_used_for_renewables(self):
        from lenses import util
        share = util.pct_share([{"date": "2026-01", "value": "24"}],
                               [{"date": "2026-01", "value": "100"}])
        self.assertEqual(share, [{"date": "2026-01", "value": "24.0"}])


if __name__ == "__main__":
    unittest.main()

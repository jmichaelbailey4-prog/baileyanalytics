import json
import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBusinessDryRun(unittest.TestCase):
    def _run(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.BUSINESS_OUT_DIR
            refresh_lenses.BUSINESS_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--business", "--dry-run"])
                files = {p.name: json.loads(p.read_text(encoding="utf-8"))
                         for p in tmp.glob("*.json")}
            finally:
                refresh_lenses.BUSINESS_OUT_DIR = orig
            return rc, files

    def test_business_flag_runs_dry_into_tempdir(self):
        rc, files = self._run()
        self.assertEqual(rc, 0)
        for name in ("business-profitability.json", "business-formation.json",
                     "business-investment.json", "business-credit.json", "index.json"):
            self.assertIn(name, files)

    def test_profit_share_injected_from_cp_and_gdp(self):
        _, files = self._run()
        prof = files["business-profitability.json"]
        share = next(i for i in prof["indicators"] if i["id"] == "profit-share")
        self.assertEqual(share["latest"]["value"], "12.3")  # 3917.2/31819.5*100
        self.assertEqual(share["signal_status"], "info")

    def test_hp_share_injected_from_bahba_and_baba(self):
        _, files = self._run()
        form = files["business-formation.json"]
        share = next(i for i in form["indicators"] if i["id"] == "hp-share")
        self.assertEqual(share["latest"]["value"], "28.0")  # 146555/523971*100

    def test_statuses_match_calibration(self):
        _, files = self._run()
        self.assertEqual(files["business-profitability.json"]["status"], "ok")
        self.assertEqual(files["business-credit.json"]["status"], "watch")  # SLOOS 8.1


if __name__ == "__main__":
    unittest.main()

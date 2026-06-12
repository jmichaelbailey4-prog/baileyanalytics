import json
import shutil
import sys
import pathlib
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import ledger, roster, runner  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "predict_histories_sample.json"

# The tournament is the expensive part (~100 rolling refits per model); run it
# once for the whole module and copy its models.json into each test's dir.
_SHARED = tempfile.TemporaryDirectory()
_SHARED_DIR = pathlib.Path(_SHARED.name)
_TOURNAMENT_RAN = {"n": None}


def _fixture_entries():
    keys = set(json.loads(FIXTURE.read_text(encoding="utf-8")))
    return [e for e in roster.build_roster() if e.key in keys]


def _shared_tournament():
    if _TOURNAMENT_RAN["n"] is None:
        _TOURNAMENT_RAN["n"] = runner.run_tournament(
            _SHARED_DIR, dry_run=True, entries=_fixture_entries())
    return _TOURNAMENT_RAN["n"]


class TestTournamentRun(unittest.TestCase):
    def test_dry_run_tournament_writes_models(self):
        n = _shared_tournament()
        self.assertEqual(n, 2)
        models_json = json.loads((_SHARED_DIR / "models.json").read_text(encoding="utf-8"))
        rec = models_json["indicators"]["economic/cost-of-living/cpi"]
        for k in ("champion", "cadence", "season", "mae", "snaive_mae",
                  "err_lo", "err_hi", "skill", "explain"):
            self.assertIn(k, rec)
        self.assertEqual(rec["cadence"], "monthly")


class TestDailyRun(unittest.TestCase):
    def _bootstrap(self, pred_dir):
        _shared_tournament()
        shutil.copy2(_SHARED_DIR / "models.json", pred_dir / "models.json")

    def test_first_daily_emits_open_predictions(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            opens = ledger.load_open(pred_dir)
            self.assertEqual(len(opens), 2)
            e = next(o for o in opens if o["key"] == "economic/cost-of-living/cpi")
            for k in ("id", "point", "lo", "hi", "due", "made_at", "model", "why",
                      "implied_status", "current_status", "prev_value", "href",
                      "horizon", "target_period", "unit", "title", "lens_title"):
                self.assertIn(k, e)
            self.assertIsNone(e["grade"])
            self.assertIn("@", e["model"])

    def test_second_daily_is_stable_no_new_print(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            first = ledger.load_open(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            second = ledger.load_open(pred_dir)
            self.assertEqual([e["id"] for e in first], [e["id"] for e in second])
            self.assertEqual([e["point"] for e in first], [e["point"] for e in second])
            self.assertEqual(ledger.load_all_graded(pred_dir), [])

    def test_new_print_grades_and_rolls_forward(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            # Simulate the next month's print arriving: extend the fixture history.
            hist = json.loads(FIXTURE.read_text(encoding="utf-8"))
            cpi = hist["economic/cost-of-living/cpi"]
            last = cpi[-1]
            y, m = int(last["date"][:4]), int(last["date"][5:7]) + 1
            if m > 12:
                y, m = y + 1, 1
            cpi.append({"date": f"{y:04d}-{m:02d}-01",
                        "value": f"{float(last['value']) + 0.05:.5f}"})
            with mock.patch.object(runner, "_load_fixture_histories", return_value=hist):
                runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            graded = ledger.load_all_graded(pred_dir)
            self.assertEqual(len(graded), 1)
            self.assertEqual(graded[0]["key"], "economic/cost-of-living/cpi")
            self.assertIsNotNone(graded[0]["grade"]["actual"])
            opens = ledger.load_open(pred_dir)
            cpi_open = next(o for o in opens if o["key"] == "economic/cost-of-living/cpi")
            self.assertGreater(cpi_open["target_period"], graded[0]["target_period"])
            # views regenerated
            self.assertTrue((pred_dir / "recent.json").exists())
            self.assertTrue((pred_dir / "track-record.json").exists())

    def test_missing_models_json_grades_but_emits_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            self.assertEqual(ledger.load_open(pred_dir), [])

    def test_empty_fetch_keeps_prior_open_entry(self):
        # A source hiccup that returns an empty series (no exception) must not
        # drop the open prediction — same contract as the exception path.
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            hist = json.loads(FIXTURE.read_text(encoding="utf-8"))
            hist["economic/cost-of-living/cpi"] = []
            with mock.patch.object(runner, "_load_fixture_histories", return_value=hist):
                runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            opens = ledger.load_open(pred_dir)
            self.assertEqual(len(opens), 2)
            self.assertIn("economic/cost-of-living/cpi", [o["key"] for o in opens])

    def test_one_indicator_failure_never_blanks_the_rest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            self._bootstrap(pred_dir)
            real = runner.models.predict_one
            calls = {"n": 0}

            def flaky(name, values, season):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise runner.models.ModelError("boom")
                return real(name, values, season)

            with mock.patch.object(runner.models, "predict_one", side_effect=flaky):
                runner.run_daily(pred_dir, dry_run=True, entries=_fixture_entries())
            self.assertEqual(len(ledger.load_open(pred_dir)), 1)


if __name__ == "__main__":
    unittest.main()

import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import predict
from predictions import runner


class TestPredictCli(unittest.TestCase):
    def test_tournament_exit_code_and_dry_run_filter(self):
        # the dry-run filter narrows the roster to fixture keys; the tournament's
        # exit code is 0 only when at least one champion was chosen, else 1.
        fixture_keys = set(json.loads(runner.FIXTURE.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(predict, "PRED_DIR", pathlib.Path(td)), \
                 mock.patch.object(runner, "run_tournament", return_value=3) as rt:
                rc = predict.main(["tournament", "--dry-run"])
            self.assertEqual(rc, 0)                       # champions chosen -> 0
            passed = rt.call_args.args[2]                 # (pred_dir, dry_run, entries)
            self.assertTrue(passed)
            self.assertTrue(all(e.key in fixture_keys for e in passed))
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(predict, "PRED_DIR", pathlib.Path(td)), \
                 mock.patch.object(runner, "run_tournament", return_value=0):
                self.assertEqual(predict.main(["tournament", "--dry-run"]), 1)  # none -> 1

    def test_daily_returns_zero(self):
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(predict, "PRED_DIR", pathlib.Path(td)), \
                 mock.patch.object(runner, "run_daily", return_value=None) as rd:
                rc = predict.main(["daily", "--dry-run"])
            self.assertEqual(rc, 0)
            rd.assert_called_once()


if __name__ == "__main__":
    unittest.main()

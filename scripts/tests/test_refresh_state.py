import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestStateDryRun(unittest.TestCase):
    def setUp(self):
        # Redirect output dirs so tests never touch real repo files; the brief
        # dir is redirected too because refresh_state reads today.json from it.
        self._td = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._td.name)
        self._orig_state = refresh_lenses.STATE_OUT_DIR
        self._orig_brief = refresh_lenses.BRIEF_OUT_DIR
        self._orig_feed = refresh_lenses.FEED_PATH
        refresh_lenses.STATE_OUT_DIR = tmp / "state"
        refresh_lenses.BRIEF_OUT_DIR = tmp / "brief"
        refresh_lenses.FEED_PATH = tmp / "feed.xml"

    def tearDown(self):
        refresh_lenses.STATE_OUT_DIR = self._orig_state
        refresh_lenses.BRIEF_OUT_DIR = self._orig_brief
        refresh_lenses.FEED_PATH = self._orig_feed
        self._td.cleanup()

    def read_today(self):
        return json.loads((refresh_lenses.STATE_OUT_DIR / "today.json")
                          .read_text(encoding="utf-8"))

    def test_state_flag_writes_today(self):
        rc = refresh_lenses.main(["--state", "--dry-run"])
        self.assertEqual(rc, 0)
        today = self.read_today()
        self.assertEqual(today["verdict"]["status"], "watch")
        self.assertEqual(today["verdict"]["shape"], "contained-pressure")
        self.assertEqual([p["category"] for p in today["pressure_points"]], ["energy"])
        self.assertIn("energy and commodity costs are squeezing budgets",
                      today["verdict"]["sentence"])
        # no brief written by --state alone -> changed block absent
        self.assertNotIn("changed", today)

    def test_state_after_brief_carries_transition_count(self):
        refresh_lenses.main(["--brief", "--dry-run"])
        refresh_lenses.main(["--state", "--dry-run"])
        today = self.read_today()
        self.assertIn("changed", today)
        self.assertEqual(today["changed"]["href"], "/dashboards/brief.html")
        self.assertIsInstance(today["changed"]["transitions"], int)

    def test_unchanged_rerun_does_not_rewrite(self):
        import itertools
        stamps = (f"2026-06-10T00:00:{n:02d}Z" for n in itertools.count(1))
        orig_now = refresh_lenses.state._now
        refresh_lenses.state._now = lambda: next(stamps)
        try:
            refresh_lenses.main(["--state", "--dry-run"])
            first = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
            refresh_lenses.main(["--state", "--dry-run"])
            second = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        finally:
            refresh_lenses.state._now = orig_now
        self.assertEqual(first, second)

    def test_failure_keeps_previous_file(self):
        refresh_lenses.main(["--state", "--dry-run"])
        before = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        orig = refresh_lenses.state.build_state
        refresh_lenses.state.build_state = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            rc = refresh_lenses.main(["--state", "--dry-run"])
        finally:
            refresh_lenses.state.build_state = orig
        self.assertEqual(rc, 0)  # a state failure never breaks the run
        after = (refresh_lenses.STATE_OUT_DIR / "today.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_full_dry_run_includes_state(self):
        # No flag = everything; the brief+state tail must both run.
        rc = refresh_lenses.main(["--brief", "--state", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertTrue((refresh_lenses.STATE_OUT_DIR / "today.json").exists())


if __name__ == "__main__":
    unittest.main()

import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestMergedBriefRefresh(unittest.TestCase):
    """The --brief pass builds the MERGED surface (brief + absorbed state).
    Ports the verdict/failure cases from the retired test_refresh_state.py."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._td.name)
        self._orig_dir = refresh_lenses.BRIEF_OUT_DIR
        self._orig_feed = refresh_lenses.FEED_PATH
        self._orig_root = refresh_lenses.REPO_ROOT
        refresh_lenses.BRIEF_OUT_DIR = tmp / "brief"
        refresh_lenses.FEED_PATH = tmp / "feed.xml"
        # The publication pass (_publish_brief) bakes under REPO_ROOT —
        # redirect it too so tests never touch real repo files.
        refresh_lenses.REPO_ROOT = tmp

    def tearDown(self):
        refresh_lenses.BRIEF_OUT_DIR = self._orig_dir
        refresh_lenses.FEED_PATH = self._orig_feed
        refresh_lenses.REPO_ROOT = self._orig_root
        self._td.cleanup()

    def read_today(self):
        return json.loads((refresh_lenses.BRIEF_OUT_DIR / "today.json")
                          .read_text(encoding="utf-8"))

    def test_brief_writes_merged_shape(self):
        rc = refresh_lenses.main(["--brief", "--dry-run"])
        self.assertEqual(rc, 0)
        today = self.read_today()
        for key in ("transitions", "top_moves", "status_counts", "lenses",
                    "verdict", "pressure", "categories"):
            self.assertIn(key, today)

    def test_verdict_content_from_fixture(self):
        # ported from test_refresh_state: fixture blends to watch with energy
        # as the lone pressure category.
        refresh_lenses.main(["--brief", "--dry-run"])
        today = self.read_today()
        self.assertEqual(today["verdict"]["status"], "watch")
        self.assertEqual(today["verdict"]["shape"], "contained-pressure")
        self.assertIn("energy and commodity costs are squeezing budgets",
                      today["verdict"]["sentence"])
        self.assertTrue(any(r["category"] == "energy" for r in today["pressure"]))
        # the dry-run fixture ships 6 of the 8 categories; full coverage of the
        # sentence bank itself lives in test_today.py
        self.assertTrue(today["categories"])
        self.assertTrue(all(c.get("sentence") for c in today["categories"]))

    def test_state_pass_is_gone(self):
        self.assertFalse(hasattr(refresh_lenses, "refresh_state"))
        self.assertFalse(hasattr(refresh_lenses, "STATE_OUT_DIR"))

    def test_state_flag_is_deprecated_alias(self):
        rc = refresh_lenses.main(["--state", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verdict", self.read_today())

    def test_failure_keeps_previous_file(self):
        # ported from test_refresh_state: a composer failure never breaks the
        # run and never blanks the previous file.
        refresh_lenses.main(["--brief", "--dry-run"])
        before = (refresh_lenses.BRIEF_OUT_DIR / "today.json").read_text(encoding="utf-8")
        orig = refresh_lenses.today.build_today
        refresh_lenses.today.build_today = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            rc = refresh_lenses.main(["--brief", "--dry-run"])
        finally:
            refresh_lenses.today.build_today = orig
        self.assertEqual(rc, 0)
        after = (refresh_lenses.BRIEF_OUT_DIR / "today.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

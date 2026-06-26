import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBriefDryRun(unittest.TestCase):
    def setUp(self):
        # Redirect every output path so tests never touch real repo files —
        # REPO_ROOT included, since refresh_brief's publication pass
        # (_publish_brief) bakes pages/og/sitemap/home under it.
        self._td = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._td.name)
        self._orig_dir = refresh_lenses.BRIEF_OUT_DIR
        self._orig_feed = refresh_lenses.FEED_PATH
        self._orig_root = refresh_lenses.REPO_ROOT
        refresh_lenses.BRIEF_OUT_DIR = tmp / "brief"
        refresh_lenses.FEED_PATH = tmp / "feed.xml"
        refresh_lenses.REPO_ROOT = tmp

    def tearDown(self):
        refresh_lenses.BRIEF_OUT_DIR = self._orig_dir
        refresh_lenses.FEED_PATH = self._orig_feed
        refresh_lenses.REPO_ROOT = self._orig_root
        self._td.cleanup()

    def test_brief_flag_writes_today_and_state(self):
        tmp = refresh_lenses.BRIEF_OUT_DIR
        rc = refresh_lenses.main(["--brief", "--dry-run"])
        self.assertEqual(rc, 0)
        today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
        state = json.loads((tmp / "_prior_state.json").read_text(encoding="utf-8"))
        self.assertIn("generated_at", today)
        self.assertIn("transitions", today)
        self.assertIn("top_moves", today)
        self.assertIn("status_counts", today)
        # fixture has fiscal-health elevated -> captured in state
        self.assertEqual(state["statuses"]["fiscal-health"], "elevated")
        self.assertTrue(any(l["lens_id"] == "fiscal-health" and l["status"] == "elevated"
                            for l in today["lenses"]))

    def test_brief_bakes_methodology_page_and_json(self):
        tmp = refresh_lenses.REPO_ROOT
        refresh_lenses.main(["--brief", "--dry-run"])
        page = tmp / "dashboards" / "methodology.html"
        data = tmp / "data" / "methodology.json"
        self.assertTrue(page.exists())
        self.assertTrue(data.exists())
        self.assertIn('id="cost-of-living--cpi"', page.read_text(encoding="utf-8"))
        self.assertIn("cost-of-living::cpi",
                      json.loads(data.read_text(encoding="utf-8"))["signals"])

    def test_brief_run_writes_feed(self):
        refresh_lenses.main(["--brief", "--dry-run"])
        xml_text = refresh_lenses.FEED_PATH.read_text(encoding="utf-8")
        self.assertTrue(xml_text.startswith("<?xml"))
        self.assertIn("<rss", xml_text)
        items = json.loads((refresh_lenses.BRIEF_OUT_DIR / "_feed_items.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(len(items), 1)

    def test_unchanged_rerun_does_not_rewrite(self):
        # An identical second run must be a no-op (content-aware write), so the
        # daily workflow's "skip commit when nothing changed" still holds — a
        # fresh generated_at/captured_at alone must not rewrite the files.
        # Force DISTINCT timestamps each run so an unconditional write would
        # change the files (the test would be vacuous within one wall-clock sec).
        import itertools
        stamps = (f"2026-06-10T00:00:{n:02d}Z" for n in itertools.count(1))
        tmp = refresh_lenses.BRIEF_OUT_DIR
        orig_now = refresh_lenses.brief._now
        refresh_lenses.brief._now = lambda: next(stamps)
        try:
            refresh_lenses.main(["--brief", "--dry-run"])
            today_1 = (tmp / "today.json").read_text(encoding="utf-8")
            state_1 = (tmp / "_prior_state.json").read_text(encoding="utf-8")
            feed_1 = refresh_lenses.FEED_PATH.read_text(encoding="utf-8")
            refresh_lenses.main(["--brief", "--dry-run"])
            today_2 = (tmp / "today.json").read_text(encoding="utf-8")
            state_2 = (tmp / "_prior_state.json").read_text(encoding="utf-8")
            feed_2 = refresh_lenses.FEED_PATH.read_text(encoding="utf-8")
        finally:
            refresh_lenses.brief._now = orig_now
        self.assertEqual(today_1, today_2)
        self.assertEqual(state_1, state_2)
        self.assertEqual(feed_1, feed_2)

    def test_second_run_detects_transition_from_seeded_state(self):
        tmp = refresh_lenses.BRIEF_OUT_DIR
        tmp.mkdir(parents=True, exist_ok=True)
        # seed a prior state where fiscal-health was 'ok' (fixture says 'elevated')
        (tmp / "_prior_state.json").write_text(
            json.dumps({"statuses": {"fiscal-health": "ok"}}) + "\n", encoding="utf-8")
        refresh_lenses.main(["--brief", "--dry-run"])
        today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
        ids = [t["lens_id"] for t in today["transitions"]]
        self.assertIn("fiscal-health", ids)
        t = next(t for t in today["transitions"] if t["lens_id"] == "fiscal-health")
        self.assertEqual(t["from_status"], "ok")
        self.assertEqual(t["to_status"], "elevated")
        # The transition lands in the feed item too.
        self.assertIn("Fiscal Health", refresh_lenses.FEED_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

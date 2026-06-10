import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestBriefDryRun(unittest.TestCase):
    def test_brief_flag_writes_today_and_state(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.BRIEF_OUT_DIR
            refresh_lenses.BRIEF_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--brief", "--dry-run"])
            finally:
                refresh_lenses.BRIEF_OUT_DIR = orig
            self.assertEqual(rc, 0)
            today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
            state = json.loads((tmp / "_prior_state.json").read_text(encoding="utf-8"))
            self.assertIn("generated_at", today)
            self.assertIn("transitions", today)
            self.assertIn("top_moves", today)
            self.assertIn("status_counts", today)
            # fixture has fiscal-health elevated -> captured in state
            self.assertEqual(state["statuses"]["fiscal-health"], "elevated")

    def test_second_run_detects_transition_from_seeded_state(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            # seed a prior state where fiscal-health was 'ok' (fixture says 'elevated')
            (tmp / "_prior_state.json").write_text(
                json.dumps({"statuses": {"fiscal-health": "ok"}}) + "\n", encoding="utf-8")
            orig = refresh_lenses.BRIEF_OUT_DIR
            refresh_lenses.BRIEF_OUT_DIR = tmp
            try:
                refresh_lenses.main(["--brief", "--dry-run"])
            finally:
                refresh_lenses.BRIEF_OUT_DIR = orig
            today = json.loads((tmp / "today.json").read_text(encoding="utf-8"))
            ids = [t["lens_id"] for t in today["transitions"]]
            self.assertIn("fiscal-health", ids)
            t = next(t for t in today["transitions"] if t["lens_id"] == "fiscal-health")
            self.assertEqual(t["from_status"], "ok")
            self.assertEqual(t["to_status"], "elevated")


if __name__ == "__main__":
    unittest.main()

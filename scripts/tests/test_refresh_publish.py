import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestManifest(unittest.TestCase):
    def test_append_and_replace_same_day(self):
        m = refresh_lenses._update_manifest([], TODAY)
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["date"], "2026-06-12")
        self.assertEqual(m[0]["status"], "watch")
        again = refresh_lenses._update_manifest(m, TODAY)
        self.assertEqual(len(again), 1)          # same-day rerun replaces, not appends

    def test_keeps_history_sorted(self):
        old = [{"date": "2026-06-11", "status": "ok", "sentence": "x"}]
        m = refresh_lenses._update_manifest(old, TODAY)
        self.assertEqual([e["date"] for e in m], ["2026-06-11", "2026-06-12"])


class TestPublishBrief(unittest.TestCase):
    def test_publish_writes_all_surfaces(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "data" / "brief").mkdir(parents=True)
            (root / "dashboards").mkdir()
            (root / "index.html").write_text(
                "<head><!-- og-image:start --><meta><!-- og-image:end --></head>"
                "<body><!-- verdict-line:start --><a><!-- verdict-line:end --></body>",
                encoding="utf-8")
            refresh_lenses._publish_brief(TODAY, root=root)
            day = "2026-06-12"
            self.assertTrue((root / "dashboards" / "brief.html").exists())
            self.assertTrue((root / "dashboards" / "brief" / f"{day}.html").exists())
            self.assertTrue((root / "dashboards" / "brief" / "index.html").exists())
            self.assertTrue((root / "og" / f"brief-{day}.png").exists())
            self.assertTrue((root / "og" / "site.png").exists())
            self.assertTrue((root / "data" / "brief" / "days" / f"{day}.json").exists())
            self.assertTrue((root / "sitemap.xml").exists())
            home = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn(f"og/brief-{day}.png", home)
            self.assertIn("Most of the economy", home)

    def test_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "data" / "brief").mkdir(parents=True)
            (root / "dashboards").mkdir()
            (root / "index.html").write_text(
                "<!-- og-image:start --><m><!-- og-image:end -->"
                "<!-- verdict-line:start --><a><!-- verdict-line:end -->", encoding="utf-8")
            refresh_lenses._publish_brief(TODAY, root=root)
            first = (root / "dashboards" / "brief.html").read_bytes()
            refresh_lenses._publish_brief(TODAY, root=root)
            manifest = json.loads((root / "data" / "brief" / "_archive_index.json")
                                  .read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 1)
            self.assertEqual((root / "dashboards" / "brief.html").read_bytes(), first)


if __name__ == "__main__":
    unittest.main()

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

    def test_missing_archive_page_is_healed(self):
        # A prior bake that failed mid-run can leave a manifest entry whose
        # archive page never got written. The next publication day must recreate
        # it from its stored JSON (otherwise the sitemap lists a permanent 404).
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "data" / "brief").mkdir(parents=True)
            (root / "dashboards").mkdir()
            (root / "index.html").write_text(
                "<!-- og-image:start --><m><!-- og-image:end -->"
                "<!-- verdict-line:start --><a><!-- verdict-line:end -->", encoding="utf-8")
            refresh_lenses._publish_brief(TODAY, root=root)
            day2 = dict(TODAY, generated_at="2026-06-13T00:00:00Z")
            # Simulate the interrupted earlier bake: day-1 page is gone but its
            # data record and manifest entry survive.
            (root / "dashboards" / "brief" / "2026-06-12.html").unlink()
            refresh_lenses._publish_brief(day2, root=root)
            healed = root / "dashboards" / "brief" / "2026-06-12.html"
            self.assertTrue(healed.exists())
            # ...and it carries a forward link to the day that healed it.
            self.assertIn("2026-06-13.html", healed.read_text(encoding="utf-8"))


class TestCategoryListSync(unittest.TestCase):
    def test_brief_index_dirs_match_brief_categories(self):
        # _patch_lens_pages iterates _brief_index_dirs(); brief.lens_href only
        # resolves real page paths for categories in brief.CATEGORIES. If the two
        # drift, a category's lens pages silently never get static reads.
        from lenses import brief
        self.assertEqual(set(refresh_lenses._brief_index_dirs()),
                         set(brief.CATEGORIES))


class TestPublishLensCards(unittest.TestCase):
    def test_bakes_one_card_per_lens_page_write_if_changed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            refresh_lenses._publish_lens_cards(root=root)
            cards = sorted((root / "og").glob("lens-*.png"))
            # 32 config lenses + the injected crypto lens = every lens page
            self.assertEqual(len(cards), 33)
            self.assertIn("lens-economic-recession-watch.png", [c.name for c in cards])
            before = {c: c.stat().st_mtime_ns for c in cards}
            refresh_lenses._publish_lens_cards(root=root)  # unchanged -> no rewrite
            self.assertEqual(before, {c: c.stat().st_mtime_ns for c in cards})


if __name__ == "__main__":
    unittest.main()

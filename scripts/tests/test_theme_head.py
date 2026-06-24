import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import theme_head

PAGE = "<!DOCTYPE html><html><head>\n  <title>x</title>\n</head><body></body></html>"


class TestThemeHead(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / "dashboards").mkdir()
        (self.root / "docs").mkdir()
        (self.root / ".superpowers").mkdir()
        (self.root / "dashboards" / "brief").mkdir()
        for rel in ["index.html", "dashboards/recession-watch.html", "docs/note.html",
                    ".superpowers/mock.html", "dashboards/brief.html",
                    "dashboards/brief/2026-06-24.html"]:
            (self.root / rel).write_text(PAGE, encoding="utf-8")

    def test_targets_root_and_dashboards_only(self):
        T = lambda r: theme_head.is_target(self.root / r, self.root)
        self.assertTrue(T("index.html"))
        self.assertTrue(T("dashboards/recession-watch.html"))
        self.assertFalse(T("docs/note.html"))
        self.assertFalse(T(".superpowers/mock.html"))
        self.assertFalse(T("dashboards/brief.html"))
        self.assertFalse(T("dashboards/brief/2026-06-24.html"))

    def test_stamp_inserts_once_and_is_idempotent(self):
        self.assertEqual(theme_head.main(root=self.root), 0)
        t1 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t1.count(theme_head.MARKER), 1)
        self.assertIn("data-theme", t1)
        self.assertLess(t1.index(theme_head.MARKER), t1.index("</head>"))
        theme_head.main(root=self.root)
        self.assertEqual((self.root / "index.html").read_text(encoding="utf-8"), t1)

    def test_skips_excluded(self):
        theme_head.main(root=self.root)
        for rel in ["docs/note.html", "dashboards/brief.html", ".superpowers/mock.html"]:
            self.assertNotIn(theme_head.MARKER, (self.root / rel).read_text(encoding="utf-8"))

    def test_no_head_warns_not_crashes(self):
        p = self.root / "dashboards" / "nohead.html"
        p.write_text("<html><body>x</body></html>", encoding="utf-8")
        theme_head.main(root=self.root)
        self.assertNotIn(theme_head.MARKER, p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

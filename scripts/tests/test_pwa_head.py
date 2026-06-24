import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import pwa_head

PAGE = "<!DOCTYPE html><html><head>\n  <title>x</title>\n</head><body></body></html>"


class TestPwaHead(unittest.TestCase):
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
        T = lambda r: pwa_head.is_target(self.root / r, self.root)
        self.assertTrue(T("index.html"))
        self.assertTrue(T("dashboards/recession-watch.html"))
        self.assertFalse(T("docs/note.html"))
        self.assertFalse(T(".superpowers/mock.html"))
        self.assertFalse(T("dashboards/brief.html"))          # baked, briefpage-owned
        self.assertFalse(T("dashboards/brief/2026-06-24.html"))  # baked archive

    def test_stamp_inserts_once_and_is_idempotent(self):
        self.assertEqual(pwa_head.main(root=self.root), 0)
        t1 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t1.count(pwa_head.MARKER), 1)
        self.assertIn('rel="manifest"', t1)
        self.assertLess(t1.index(pwa_head.MARKER), t1.index("</head>"))
        pwa_head.main(root=self.root)   # rerun
        t2 = (self.root / "index.html").read_text(encoding="utf-8")
        self.assertEqual(t2, t1)        # no double-stamp

    def test_skips_excluded(self):
        pwa_head.main(root=self.root)
        self.assertNotIn(pwa_head.MARKER, (self.root / "docs/note.html").read_text(encoding="utf-8"))
        self.assertNotIn(pwa_head.MARKER, (self.root / "dashboards/brief.html").read_text(encoding="utf-8"))
        self.assertNotIn(pwa_head.MARKER, (self.root / ".superpowers/mock.html").read_text(encoding="utf-8"))

    def test_no_head_warns_not_crashes(self):
        p = self.root / "dashboards" / "nohead.html"
        p.write_text("<html><body>x</body></html>", encoding="utf-8")
        pwa_head.main(root=self.root)
        self.assertNotIn(pwa_head.MARKER, p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

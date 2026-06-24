"""Tests for the hand-written-page beacon injector."""

import contextlib
import io
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import analytics
from tools import cf_beacon


class InjectTests(unittest.TestCase):
    def test_inserts_beacon_inside_head(self):
        html = "<html><head><title>x</title></head><body>y</body></html>"
        out = cf_beacon.inject(html)
        self.assertIn("static.cloudflareinsights.com/beacon.min.js", out)
        self.assertLess(out.index("beacon.min.js"), out.index("</head>"))

    def test_is_idempotent(self):
        once = cf_beacon.inject("<head></head>")
        twice = cf_beacon.inject(once)
        self.assertEqual(once, twice)
        self.assertEqual(once.count("beacon.min.js"), 1)

    def test_recognises_existing_beacon_by_marker_not_script_url(self):
        # Idempotency keys off the Cloudflare comment marker, so it still holds if the
        # beacon's script URL ever changes (e.g. a self-hosted/proxied beacon).
        page = f"<head>{analytics.BEACON_START}<script src='/elsewhere.js'></script></head>"
        self.assertEqual(cf_beacon.inject(page), page)

    def test_page_without_head_is_left_unchanged(self):
        html = "<html><body>no head here</body></html>"
        self.assertEqual(cf_beacon.inject(html), html)


class IsBakedTests(unittest.TestCase):
    def test_skips_pages_briefpage_bakes(self):
        # brief.html and the dated archive (dashboards/brief/*.html) get the beacon
        # from briefpage.py — never hand-stamp machine-baked output.
        root = cf_beacon.ROOT
        self.assertTrue(cf_beacon.is_baked(root / "dashboards" / "brief.html", root))
        self.assertTrue(cf_beacon.is_baked(root / "dashboards" / "brief" / "2026-06-24.html", root))

    def test_covers_every_hand_written_page(self):
        root = cf_beacon.ROOT
        self.assertFalse(cf_beacon.is_baked(root / "index.html", root))
        self.assertFalse(cf_beacon.is_baked(root / "dashboards" / "recession-watch.html", root))
        self.assertFalse(cf_beacon.is_baked(root / "dashboards" / "consumer" / "spending.html", root))


class SitePagesTests(unittest.TestCase):
    def test_targets_real_pages_only(self):
        rel = {str(p.relative_to(cf_beacon.ROOT)).replace("\\", "/")
               for p in cf_beacon.site_pages(cf_beacon.ROOT)}
        # Real published pages are present...
        self.assertIn("index.html", rel)
        self.assertIn("dashboards/recession-watch.html", rel)
        # ...and non-site html is NOT (brainstorm mockups under .superpowers/, docs,
        # and the brief pages briefpage.py bakes).
        self.assertFalse(any(".superpowers" in r for r in rel),
                         "must not touch brainstorm mockups under .superpowers/")
        self.assertFalse(any(r.startswith("docs/") for r in rel))
        self.assertNotIn("dashboards/brief.html", rel)
        self.assertFalse(any(r.startswith("dashboards/brief/") for r in rel))


class MainTests(unittest.TestCase):
    """End-to-end over a tmp tree — the file walk + write that the pure helpers don't
    cover: it stamps real pages, skips baked ones, and warns (not silently) on no-head."""

    def _tree(self, root):
        (root / "dashboards" / "brief").mkdir(parents=True)
        (root / "index.html").write_text("<head></head>", encoding="utf-8")
        (root / "dashboards" / "lens.html").write_text("<head></head>", encoding="utf-8")
        (root / "dashboards" / "brief.html").write_text("<head></head>", encoding="utf-8")
        (root / "dashboards" / "brief" / "2026.html").write_text("<head></head>", encoding="utf-8")
        (root / "dashboards" / "nohead.html").write_text("<p>no head</p>", encoding="utf-8")

    def test_stamps_real_pages_skips_baked_and_warns_on_no_head(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._tree(root)
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                cf_beacon.main(root=root)

            def body(p):
                return (root / p).read_text(encoding="utf-8")

            self.assertIn("beacon.min.js", body("index.html"))             # stamped
            self.assertIn("beacon.min.js", body("dashboards/lens.html"))   # stamped
            self.assertNotIn("beacon.min.js", body("dashboards/brief.html"))       # baked
            self.assertNotIn("beacon.min.js", body("dashboards/brief/2026.html"))  # baked
            self.assertNotIn("beacon.min.js", body("dashboards/nohead.html"))      # no </head>
            self.assertIn("nohead.html", err.getvalue())                   # ...and warned about it

    def test_is_idempotent_over_a_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._tree(root)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                cf_beacon.main(root=root)
                first = (root / "index.html").read_text(encoding="utf-8")
                cf_beacon.main(root=root)
            self.assertEqual((root / "index.html").read_text(encoding="utf-8"), first)


if __name__ == "__main__":
    unittest.main()

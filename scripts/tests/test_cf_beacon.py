"""Tests for the hand-written-page beacon injector's pure logic."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
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

    def test_page_without_head_is_left_unchanged(self):
        html = "<html><body>no head here</body></html>"
        self.assertEqual(cf_beacon.inject(html), html)


class IsBakedTests(unittest.TestCase):
    def test_skips_pages_briefpage_bakes(self):
        # brief.html and the dated archive (dashboards/brief/*.html) get the beacon
        # from briefpage.py — never hand-stamp machine-baked output.
        root = cf_beacon.ROOT
        self.assertTrue(cf_beacon.is_baked(root / "dashboards" / "brief.html"))
        self.assertTrue(cf_beacon.is_baked(root / "dashboards" / "brief" / "2026-06-24.html"))

    def test_covers_every_hand_written_page(self):
        root = cf_beacon.ROOT
        self.assertFalse(cf_beacon.is_baked(root / "index.html"))
        self.assertFalse(cf_beacon.is_baked(root / "dashboards" / "recession-watch.html"))
        self.assertFalse(cf_beacon.is_baked(root / "dashboards" / "consumer" / "spending.html"))


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

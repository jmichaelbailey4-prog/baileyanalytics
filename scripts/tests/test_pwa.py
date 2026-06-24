import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import pwa

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestPwa(unittest.TestCase):
    def test_head_tags_contents(self):
        h = pwa.head_tags()
        self.assertIn('rel="manifest" href="/manifest.webmanifest"', h)
        self.assertIn('name="theme-color"', h)
        self.assertIn('rel="apple-touch-icon" href="/apple-touch-icon.png"', h)
        self.assertIn('src="/dashboards/personalize-core.js"', h)
        self.assertIn('src="/dashboards/personalize.js"', h)
        # core must precede personalize (load order matters)
        self.assertLess(h.index("personalize-core.js"), h.index('/personalize.js"'))

    def test_manifest_dict(self):
        m = pwa.manifest_dict()
        self.assertEqual(m["start_url"], "/")
        self.assertEqual(m["display"], "standalone")
        self.assertEqual(m["scope"], "/")
        self.assertEqual({i["purpose"] for i in m["icons"]}, {"any", "maskable"})

    def test_manifest_file_matches_source(self):
        disk = (ROOT / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertEqual(json.loads(disk), pwa.manifest_dict())

    def test_offline_page_exists(self):
        self.assertTrue((ROOT / "offline.html").exists())


if __name__ == "__main__":
    unittest.main()

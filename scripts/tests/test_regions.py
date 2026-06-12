import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import regions

DOC = "<head>\n<!-- og-image:start --><meta old><!-- og-image:end -->\n</head>"


class TestReplaceRegion(unittest.TestCase):
    def test_replaces_content_between_markers(self):
        out, changed = regions.replace_region(DOC, "og-image", "<meta new>")
        self.assertTrue(changed)
        self.assertIn("<!-- og-image:start --><meta new><!-- og-image:end -->", out)
        self.assertNotIn("<meta old>", out)

    def test_unchanged_content_reports_no_change(self):
        out, changed = regions.replace_region(DOC, "og-image", "<meta old>")
        self.assertFalse(changed)
        self.assertEqual(out, DOC)

    def test_missing_markers_is_a_safe_noop(self):
        out, changed = regions.replace_region("<head></head>", "og-image", "<meta new>")
        self.assertFalse(changed)
        self.assertEqual(out, "<head></head>")

    def test_multiline_region(self):
        doc = "a\n<!-- x:start -->\nline1\nline2\n<!-- x:end -->\nb"
        out, changed = regions.replace_region(doc, "x", "new")
        self.assertTrue(changed)
        self.assertIn("<!-- x:start -->new<!-- x:end -->", out)

    def test_content_containing_end_marker_raises(self):
        with self.assertRaises(ValueError):
            regions.replace_region(DOC, "og-image", "x<!-- og-image:end -->y")


if __name__ == "__main__":
    unittest.main()

import io
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import ogcard

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestRenderCard(unittest.TestCase):
    def test_returns_1200x630_png(self):
        png = ogcard.render_card("watch", "Most of the economy is on solid footing.",
                                 "June 12, 2026")
        img = Image.open(io.BytesIO(png))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, (1200, 630))

    def test_long_sentence_does_not_raise(self):
        long = ("Most of the economy is on solid footing — banks are solid and markets "
                "are calm — but energy and commodity costs are squeezing budgets and "
                "household finances are stretched thin across nearly every measure.")
        png = ogcard.render_card("elevated", long, "June 12, 2026")
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1200, 630))

    def test_unknown_status_uses_fallback_color(self):
        png = ogcard.render_card("bogus", "Sentence.", "June 12, 2026")
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_site_card(self):
        png = ogcard.render_site_card()
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1200, 630))

    def test_unsplittable_word_still_renders_canvas(self):
        png = ogcard.render_card("ok", "https://example.com/" + "x" * 120, "June 12, 2026")
        self.assertEqual(Image.open(io.BytesIO(png)).size, (1200, 630))


if __name__ == "__main__":
    unittest.main()

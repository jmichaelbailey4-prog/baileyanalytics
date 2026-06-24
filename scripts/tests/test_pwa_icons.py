import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import pwa_icons

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestPwaIcons(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        pwa_icons.generate(root=self.tmp)

    def test_sizes(self):
        self.assertEqual(Image.open(self.tmp / "icons/icon-192.png").size, (192, 192))
        self.assertEqual(Image.open(self.tmp / "icons/icon-512.png").size, (512, 512))
        self.assertEqual(Image.open(self.tmp / "icons/icon-192-maskable.png").size, (192, 192))
        self.assertEqual(Image.open(self.tmp / "icons/icon-512-maskable.png").size, (512, 512))
        self.assertEqual(Image.open(self.tmp / "apple-touch-icon.png").size, (180, 180))

    def test_apple_touch_is_opaque(self):
        # iOS rejects transparency on apple-touch-icon
        self.assertEqual(Image.open(self.tmp / "apple-touch-icon.png").mode, "RGB")

    def test_maskable_bleeds_to_corner(self):
        # maskable: the panel bg fills the corner (safe-zone art is inset)
        px = Image.open(self.tmp / "icons/icon-512-maskable.png").convert("RGBA").getpixel((4, 4))
        self.assertEqual(px[:3], (15, 23, 42))      # #0F172A panel
        self.assertEqual(px[3], 255)

    def test_standard_corner_is_transparent(self):
        # non-maskable: the rounded corner is transparent
        px = Image.open(self.tmp / "icons/icon-512.png").convert("RGBA").getpixel((1, 1))
        self.assertEqual(px[3], 0)

    def test_generate_returns_paths(self):
        out = pwa_icons.generate(root=self.tmp)
        self.assertIn("icons/icon-192.png", out)
        self.assertIn("apple-touch-icon.png", out)


if __name__ == "__main__":
    unittest.main()

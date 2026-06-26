"""WCAG AA gate for the light palette. Keep these values in sync with the
[data-theme="light"] block in dashboards/lens.css (spec 2026-06-24-light-theme §5)."""
import unittest


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(hexstr):
    h = hexstr.lstrip("#")
    return (0.2126 * _lin(int(h[0:2], 16)) + 0.7152 * _lin(int(h[2:4], 16))
            + 0.0722 * _lin(int(h[4:6], 16)))


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


BG, PANEL = "#F5F5F7", "#FFFFFF"
# (label, fg, bg, min_ratio)
PAIRS = [
    ("text/bg", "#1D1D1F", BG, 4.5), ("text/panel", "#1D1D1F", PANEL, 4.5),
    ("muted/bg", "#4B4B4F", BG, 4.5), ("dim/bg", "#5E5E63", BG, 4.5),
    ("faint/bg", "#6A6A6F", BG, 4.5),
    ("blue/panel", "#0068D1", PANEL, 4.5), ("white-on-blue", "#FFFFFF", "#0068D1", 4.5),
    ("green/panel", "#1A7F37", PANEL, 4.5), ("amber/panel", "#8A5D00", PANEL, 4.5),
    ("orange/panel", "#C2410C", PANEL, 4.5), ("red/panel", "#D70015", PANEL, 4.5),
    ("badge ok", "#1A7F37", "#ECF8F2", 4.5), ("badge watch", "#8A5D00", "#FBF2DC", 4.5),
    ("badge elevated", "#C2410C", "#FDF0E6", 4.5), ("badge alert", "#D70015", "#FDECEE", 4.5),
    ("badge unknown", "#5E5E63", "#ECECF1", 4.5), ("badge neutral", "#0068D1", "#E6F0FC", 4.5),
    ("focus blue/bg", "#0068D1", BG, 3.0),
]


class TestThemeContrast(unittest.TestCase):
    def test_all_light_pairs_meet_aa(self):
        for label, fg, bg, mn in PAIRS:
            r = contrast(fg, bg)
            self.assertGreaterEqual(round(r, 2), mn, f"{label}: {r:.2f} < {mn}")


if __name__ == "__main__":
    unittest.main()

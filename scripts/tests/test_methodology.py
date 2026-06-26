"""methodology.build_methodology() + render_methodology(): the scoring methodology
data + static page, generated from the band specs + taxonomy + curated why."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import methodology, reasons  # noqa: E402


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.data = methodology.build_methodology()

    def test_shape(self):
        self.assertIn("generated_at", self.data)
        self.assertIn("signals", self.data)
        self.assertIn("taxonomy", self.data)

    def test_severity_signal_has_bands_and_why(self):
        s = self.data["signals"]["cost-of-living::cpi"]
        self.assertEqual(s["taxonomy"], "severity")
        self.assertIn("segments", s)
        self.assertEqual(s["axis"]["unit"], "%")
        self.assertEqual(s["why"], reasons.BAND_WHY["rule_inflation"])
        # segments carry status + range bounds
        self.assertTrue(all("status" in seg for seg in s["segments"]))

    def test_info_signal_has_note_not_bands(self):
        s = self.data["signals"]["market-scoreboard::sp500"]
        self.assertIn(s["taxonomy"], {"info", "momentum", "neutral"})
        self.assertNotIn("segments", s)
        self.assertTrue(s["note"])

    def test_custom_severity_has_why_but_no_segments(self):
        s = self.data["signals"]["recession-watch::yield-curve"]
        self.assertEqual(s["taxonomy"], "severity")
        self.assertNotIn("segments", s)
        self.assertEqual(s["why"], reasons.BAND_WHY["rule_yield_curve"])

    def test_crypto_lens_is_covered(self):
        self.assertIn("crypto-structure::btc-dominance", self.data["signals"])

    def test_every_config_indicator_present(self):
        from lenses import config
        for cat in config.CATEGORIES:
            for lens in cat["lenses"]:
                for ind in lens.indicators:
                    self.assertIn(f"{lens.id}::{ind.id}", self.data["signals"])


class TestRender(unittest.TestCase):
    def setUp(self):
        self.html = methodology.render_methodology(methodology.build_methodology())

    def test_is_a_document_with_nav_and_anchor(self):
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn("Today&#39;s Brief", self.html)       # the 4-item nav
        self.assertIn('id="cost-of-living--cpi"', self.html)  # deep-link anchor

    def test_contains_bands_and_why(self):
        self.assertIn("year-over-year inflation rate", self.html)  # curated why text
        self.assertIn("badge watch", self.html)                    # a band swatch


class TestPwaStamperExcludesMethodology(unittest.TestCase):
    def test_methodology_is_not_a_stamp_target(self):
        # methodology.py emits its own head (like brief.html), so the pwa-head
        # stamper must leave it alone — else the head would be double-stamped.
        from tools import pwa_head
        root = pathlib.Path("/repo")
        self.assertFalse(pwa_head.is_target(root / "dashboards" / "methodology.html", root))
        # control: an ordinary lens page IS a target
        self.assertTrue(pwa_head.is_target(root / "dashboards" / "recession-watch.html", root))


if __name__ == "__main__":
    unittest.main()

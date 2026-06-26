"""Pure helpers in lenses.bands: BandSpec + axis math (no network, no deps)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import bands  # noqa: E402


class TestBandSpec(unittest.TestCase):
    def test_construct_defaults(self):
        s = bands.BandSpec(kind="level", unit="%", edges=(5.5, 6.5, 7.5),
                           segments=("ok", "watch", "elevated", "alert"))
        self.assertTrue(s.probe)
        self.assertEqual(s.cap, "")
        self.assertEqual(s.axis_label, "")


class TestSynthAndDecision(unittest.TestCase):
    def test_level_roundtrip(self):
        obs = bands.synth_obs("level", 6.0)
        self.assertEqual(obs[-1][1], 6.0)
        self.assertEqual(bands.decision_value("level", obs), 6.0)

    def test_yoy_roundtrip(self):
        obs = bands.synth_obs("yoy", 3.0)
        self.assertEqual(bands.decision_value("yoy", obs), 3.0)

    def test_yoy_computed_roundtrip(self):
        obs = bands.synth_obs("yoy_computed", 12.0)
        self.assertAlmostEqual(bands.decision_value("yoy_computed", obs), 12.0, places=6)

    def test_yoy_computed_negative(self):
        obs = bands.synth_obs("yoy_computed", -4.0)
        self.assertAlmostEqual(bands.decision_value("yoy_computed", obs), -4.0, places=6)

    def test_delta_from_low_roundtrip(self):
        obs = bands.synth_obs("delta_from_low", 0.6)
        self.assertAlmostEqual(bands.decision_value("delta_from_low", obs), 0.6, places=6)

    def test_empty_obs_is_none(self):
        self.assertIsNone(bands.decision_value("level", []))
        self.assertIsNone(bands.decision_value("yoy_computed", []))

    def test_custom_kind_has_no_value(self):
        self.assertIsNone(bands.decision_value("custom", bands.synth_obs("level", 1.0)))


class TestStatusAt(unittest.TestCase):
    def setUp(self):
        self.s = bands.BandSpec(kind="level", unit="%", edges=(5.5, 6.5, 7.5),
                                segments=("ok", "watch", "elevated", "alert"))

    def test_below_first_edge(self):
        self.assertEqual(bands.status_at(self.s, 5.0), "ok")

    def test_middle_segment(self):
        self.assertEqual(bands.status_at(self.s, 7.0), "elevated")

    def test_above_last_edge(self):
        self.assertEqual(bands.status_at(self.s, 8.0), "alert")


class TestSegmentRanges(unittest.TestCase):
    def test_ranges(self):
        s = bands.BandSpec(kind="level", unit="%", edges=(5.5, 6.5, 7.5),
                           segments=("ok", "watch", "elevated", "alert"))
        r = bands.segment_ranges(s)
        self.assertEqual(len(r), 4)
        self.assertEqual(r[0], {"status": "ok", "lo": None, "hi": 5.5})
        self.assertEqual(r[1], {"status": "watch", "lo": 5.5, "hi": 6.5})
        self.assertEqual(r[3], {"status": "alert", "lo": 7.5, "hi": None})


if __name__ == "__main__":
    unittest.main()

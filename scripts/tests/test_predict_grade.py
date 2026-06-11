import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import grade  # noqa: E402


def _open_entry(point=4.31, lo=4.02, hi=4.6, prev=4.17, target="2026-06-01"):
    return {"id": f"economic/cost-of-living/cpi@{target}",
            "key": "economic/cost-of-living/cpi",
            "target_period": target, "point": point, "lo": lo, "hi": hi,
            "prev_value": prev, "implied_status": "elevated", "grade": None}


CLEANED = [("2026-04-01", 3.78), ("2026-05-01", 4.17), ("2026-06-01", 4.30)]


class TestMatchActual(unittest.TestCase):
    def test_first_obs_at_or_after_target(self):
        self.assertEqual(grade.match_actual(CLEANED, "2026-06-01"), ("2026-06-01", 4.30))

    def test_holiday_shifted_date_still_matches(self):
        obs = [("2026-06-06", 1.0), ("2026-06-14", 2.0)]  # target Sat slid to Sun
        self.assertEqual(grade.match_actual(obs, "2026-06-13"), ("2026-06-14", 2.0))

    def test_not_arrived_returns_none(self):
        self.assertIsNone(grade.match_actual(CLEANED, "2026-07-01"))

    def test_double_print_grades_only_target(self):
        # cron skipped a day; two new prints exist. First obs >= target IS the
        # target print.
        obs = CLEANED + [("2026-07-01", 4.4)]
        self.assertEqual(grade.match_actual(obs, "2026-06-01"), ("2026-06-01", 4.30))


class TestGradeEntry(unittest.TestCase):
    def test_hit_inside_band(self):
        g = grade.grade_entry(_open_entry(), 4.30, "elevated")
        self.assertTrue(g["hit"])
        self.assertAlmostEqual(g["abs_error"], 0.01, places=6)
        self.assertTrue(g["direction_hit"])   # predicted up (4.31>4.17), actual up
        self.assertTrue(g["status_hit"])
        self.assertAlmostEqual(g["naive_error"], 0.13, places=6)  # |4.30-4.17|
        self.assertIsNone(g["revised_to"])

    def test_miss_outside_band(self):
        g = grade.grade_entry(_open_entry(), 4.9, "alert")
        self.assertFalse(g["hit"])
        self.assertFalse(g["status_hit"])

    def test_direction_flat_epsilon(self):
        e = _open_entry(point=4.17)            # predicted flat
        g = grade.grade_entry(e, 4.17, "elevated")
        self.assertTrue(g["direction_hit"])    # both flat -> hit
        g2 = grade.grade_entry(e, 4.5, "elevated")
        self.assertFalse(g2["direction_hit"])  # predicted flat, actual up


if __name__ == "__main__":
    unittest.main()

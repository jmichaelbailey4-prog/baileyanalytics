import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import cadence  # noqa: E402


def _monthly(n, start_year=2020):
    return [(f"{start_year + i // 12:04d}-{1 + i % 12:02d}-01", float(i)) for i in range(n)]


class TestInfer(unittest.TestCase):
    def test_monthly(self):
        self.assertEqual(cadence.infer(_monthly(30)), "monthly")

    def test_weekly(self):
        obs = [(f"2026-{m:02d}-{d:02d}", 1.0) for m, d in
               [(1, 3), (1, 10), (1, 17), (1, 24), (1, 31), (2, 7), (2, 14), (2, 21), (2, 28), (3, 7)]]
        self.assertEqual(cadence.infer(obs), "weekly")

    def test_daily(self):
        obs = [(f"2026-03-{d:02d}", 1.0) for d in range(2, 28) if d % 7 not in (0, 1)]
        self.assertEqual(cadence.infer(obs), "daily")

    def test_quarterly(self):
        obs = [("2024-01-01", 1.0), ("2024-04-01", 1.0), ("2024-07-01", 1.0),
               ("2024-10-01", 1.0), ("2025-01-01", 1.0)]
        self.assertEqual(cadence.infer(obs), "quarterly")

    def test_eia_monthly_yyyy_mm(self):
        obs = [(f"2025-{m:02d}", 1.0) for m in range(1, 12)]
        self.assertEqual(cadence.infer(obs), "monthly")

    def test_annual(self):
        obs = [(f"{y}-01-01", 1.0) for y in range(2018, 2026)]
        self.assertEqual(cadence.infer(obs), "annual")


class TestWeeklyResample(unittest.TestCase):
    def test_last_obs_per_iso_week_dated_friday(self):
        obs = [("2026-06-01", 1.0), ("2026-06-02", 2.0), ("2026-06-03", 3.0),  # wk 23
               ("2026-06-08", 4.0), ("2026-06-09", 5.0)]                        # wk 24
        out = cadence.weekly_resample(obs)
        self.assertEqual(out, [("2026-06-05", 3.0), ("2026-06-12", 5.0)])


class TestNextPeriod(unittest.TestCase):
    def test_monthly(self):
        self.assertEqual(cadence.next_period("2026-05-01", "monthly"), "2026-06-01")
        self.assertEqual(cadence.next_period("2026-12-01", "monthly"), "2027-01-01")

    def test_eia_monthly(self):
        self.assertEqual(cadence.next_period("2026-05", "monthly"), "2026-06")

    def test_weekly(self):
        self.assertEqual(cadence.next_period("2026-06-06", "weekly"), "2026-06-13")

    def test_quarterly(self):
        self.assertEqual(cadence.next_period("2026-04-01", "quarterly"), "2026-07-01")
        self.assertEqual(cadence.next_period("2026-10-01", "quarterly"), "2027-01-01")


class TestDue(unittest.TestCase):
    def test_monthly_mid_following_month(self):
        self.assertEqual(cadence.due_estimate("2026-06-01", "monthly"), "2026-07-15")

    def test_weekly_five_days(self):
        self.assertEqual(cadence.due_estimate("2026-06-13", "weekly"), "2026-06-18")

    def test_quarterly_late_following_month(self):
        self.assertEqual(cadence.due_estimate("2026-04-01", "quarterly"), "2026-07-28")


if __name__ == "__main__":
    unittest.main()

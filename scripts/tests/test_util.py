import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import util


class TestUtil(unittest.TestCase):
    def test_to_float_parses_numbers(self):
        self.assertEqual(util.to_float("4.2"), 4.2)

    def test_to_float_returns_none_for_fred_null(self):
        self.assertIsNone(util.to_float("."))
        self.assertIsNone(util.to_float(None))

    def test_clean_drops_nulls_and_keeps_order(self):
        raw = [
            {"date": "2026-01-01", "value": "1.0"},
            {"date": "2026-02-01", "value": "."},
            {"date": "2026-03-01", "value": "2.5"},
        ]
        self.assertEqual(util.clean(raw), [("2026-01-01", 1.0), ("2026-03-01", 2.5)])

    def test_status_max_picks_most_severe(self):
        self.assertEqual(util.status_max(["ok", "watch", "elevated"]), "elevated")

    def test_status_max_ignores_unknown_when_others_present(self):
        self.assertEqual(util.status_max(["unknown", "ok"]), "ok")

    def test_status_max_all_unknown(self):
        self.assertEqual(util.status_max(["unknown", "unknown"]), "unknown")


class TestMergeSeries(unittest.TestCase):
    def test_new_wins_and_old_is_retained(self):
        old = [{"date": "2026-01-01", "value": 1.0}, {"date": "2026-01-02", "value": 2.0}]
        new = [{"date": "2026-01-02", "value": 9.0}, {"date": "2026-01-03", "value": 3.0}]
        self.assertEqual(util.merge_series(old, new), [
            {"date": "2026-01-01", "value": 1.0},
            {"date": "2026-01-02", "value": 9.0},
            {"date": "2026-01-03", "value": 3.0},
        ])

    def test_handles_none(self):
        self.assertEqual(util.merge_series(None, [{"date": "2026-01-01", "value": 1.0}]),
                         [{"date": "2026-01-01", "value": 1.0}])


class TestPctShare(unittest.TestCase):
    def test_matched_dates_only_and_rounded(self):
        num = [{"date": "2026-01", "value": "30"}, {"date": "2026-02", "value": "40"}]
        den = [{"date": "2026-01", "value": "120"}, {"date": "2026-03", "value": "200"}]
        # only 2026-01 is in both: 30/120 = 25.0%
        self.assertEqual(util.pct_share(num, den), [{"date": "2026-01", "value": "25.0"}])

    def test_skips_zero_denominator(self):
        self.assertEqual(util.pct_share([{"date": "d", "value": "5"}],
                                        [{"date": "d", "value": "0"}]), [])


class TestSpreadFfill(unittest.TestCase):
    def test_subtracts_with_forward_fill(self):
        # daily minuend, monthly subtrahend: each a-date uses the latest b at or before it
        a = [{"date": "2026-01-02", "value": "4.20"}, {"date": "2026-02-03", "value": "4.00"}]
        b = [{"date": "2026-01-01", "value": "4.50"}, {"date": "2026-02-01", "value": "4.40"}]
        self.assertEqual(util.spread_ffill(a, b), [
            {"date": "2026-01-02", "value": "-0.30"},
            {"date": "2026-02-03", "value": "-0.40"},
        ])

    def test_skips_dates_before_subtrahend_starts(self):
        a = [{"date": "2025-12-31", "value": "4.20"}]
        b = [{"date": "2026-01-01", "value": "4.50"}]
        self.assertEqual(util.spread_ffill(a, b), [])

    def test_skips_missing_values(self):
        a = [{"date": "2026-01-02", "value": "."}, {"date": "2026-01-03", "value": "4.00"}]
        b = [{"date": "2026-01-01", "value": "4.50"}]
        self.assertEqual(util.spread_ffill(a, b),
                         [{"date": "2026-01-03", "value": "-0.50"}])

    def test_handles_none(self):
        self.assertEqual(util.spread_ffill(None, []), [])


class TestThinObservations(unittest.TestCase):
    def test_recent_window_kept_in_full(self):
        obs = [{"date": f"2026-05-{d:02d}", "value": str(d)} for d in range(1, 31)]
        self.assertEqual(util.thin_observations(obs, keep_years=2), obs)

    def test_mid_window_daily_points_thinned_to_weekly(self):
        # daily points 2-5 years back thin to one per ISO week
        old = [{"date": f"2024-03-{d:02d}", "value": str(d)} for d in range(4, 18)]  # 14 days
        recent = [{"date": "2026-05-01", "value": "x"}]
        out = util.thin_observations(old + recent, keep_years=2)
        kept = [o["date"] for o in out if o["date"].startswith("2024")]
        # Mar 4 2024 is a Monday: the 14 days cover ISO weeks 10 and 11 -> 2 survivors
        self.assertEqual(kept, ["2024-03-04", "2024-03-11"])
        self.assertIn(recent[0], out)

    def test_old_daily_points_thinned_to_monthly(self):
        # daily points more than 5 years back thin to one per calendar month
        old = [{"date": f"2020-03-{d:02d}", "value": str(d)} for d in range(2, 16)]
        recent = [{"date": "2026-05-01", "value": "x"}]
        out = util.thin_observations(old + recent, keep_years=2)
        kept = [o["date"] for o in out if o["date"].startswith("2020")]
        self.assertEqual(kept, ["2020-03-02"])
        self.assertIn(recent[0], out)

    def test_old_monthly_points_untouched(self):
        obs = [{"date": f"20{y:02d}-{m:02d}-01", "value": "1"} for y in range(20, 27) for m in (1, 7)]
        self.assertEqual(util.thin_observations(obs, keep_years=2), obs)

    def test_eia_monthly_dates_pass_through(self):
        # EIA monthly periods have no day part ("YYYY-MM"); they never thin
        obs = [{"date": f"20{y:02d}-{m:02d}", "value": "1"} for y in range(20, 27) for m in (1, 7)]
        self.assertEqual(util.thin_observations(obs, keep_years=2), obs)

    def test_empty(self):
        self.assertEqual(util.thin_observations([], keep_years=2), [])


if __name__ == "__main__":
    unittest.main()

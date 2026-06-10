import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import derive


class TestPayrollChange(unittest.TestCase):
    def test_month_over_month_in_jobs(self):
        raw = [
            {"date": "2026-03-01", "value": "159000"},
            {"date": "2026-04-01", "value": "159150"},
            {"date": "2026-05-01", "value": "159327"},
        ]
        out = derive.payroll_change(raw)
        self.assertEqual(out[-1], {"date": "2026-05-01", "value": "177000"})
        self.assertEqual(len(out), 2)  # first month has no prior

    def test_resets_across_null(self):
        raw = [
            {"date": "2026-03-01", "value": "159000"},
            {"date": "2026-04-01", "value": "."},
            {"date": "2026-05-01", "value": "159327"},
        ]
        # a null breaks the chain; we never diff across a gap (would be a false "last month")
        self.assertEqual(derive.payroll_change(raw), [])


class TestYoyPct(unittest.TestCase):
    def test_year_over_year_percent(self):
        raw = [
            {"date": "2025-04-01", "value": "100.0"},
            {"date": "2025-05-01", "value": "100.0"},
            {"date": "2026-04-01", "value": "104.2"},
            {"date": "2026-05-01", "value": "103.0"},
        ]
        out = derive.yoy_pct(raw)
        self.assertEqual(out, [
            {"date": "2026-04-01", "value": "4.2"},
            {"date": "2026-05-01", "value": "3.0"},
        ])

    def test_skips_missing_prior_and_nulls(self):
        raw = [
            {"date": "2025-05-01", "value": "."},
            {"date": "2026-05-01", "value": "103.0"},
            {"date": "2026-06-01", "value": "104.0"},
        ]
        # no valid value one year before either point
        self.assertEqual(derive.yoy_pct(raw), [])

    def test_zero_prior_skipped(self):
        raw = [
            {"date": "2025-05-01", "value": "0"},
            {"date": "2026-05-01", "value": "103.0"},
        ]
        self.assertEqual(derive.yoy_pct(raw), [])


class TestTrailing12mDeficit(unittest.TestCase):
    def test_rolls_12_months_to_trillions_positive_deficit(self):
        # 11 months of -150,000 ($M) then a +50,000 surplus month, then -200,000
        raw = ([{"date": f"2025-{m:02d}-01", "value": "-150000"} for m in range(1, 12)]
               + [{"date": "2025-12-01", "value": "50000"},
                  {"date": "2026-01-01", "value": "-200000"}])
        out = derive.trailing_12m_deficit(raw)
        # first full window ends 2025-12: 11*-150k + 50k = -1.6M ($M) -> $1.60T deficit
        self.assertEqual(out[0], {"date": "2025-12-01", "value": "1.60"})
        # next window drops 2025-01 (-150k), adds -200k: -1.65M -> $1.65T
        self.assertEqual(out[1], {"date": "2026-01-01", "value": "1.65"})
        self.assertEqual(len(out), 2)

    def test_gap_restarts_window(self):
        raw = ([{"date": f"2025-{m:02d}-01", "value": "-100000"} for m in range(1, 7)]
               + [{"date": "2025-07-01", "value": "."}]
               + [{"date": f"2025-{m:02d}-01", "value": "-100000"} for m in range(8, 13)])
        self.assertEqual(derive.trailing_12m_deficit(raw), [])


class TestToMillions(unittest.TestCase):
    def test_thousands_to_millions(self):
        raw = [{"date": "2026-05-01", "value": "7200"}]
        self.assertEqual(derive.to_millions(raw), [{"date": "2026-05-01", "value": "7.2"}])

    def test_skips_nulls(self):
        self.assertEqual(derive.to_millions([{"date": "2026-05-01", "value": "."}]), [])


if __name__ == "__main__":
    unittest.main()

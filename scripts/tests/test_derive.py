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


class TestToMillions(unittest.TestCase):
    def test_thousands_to_millions(self):
        raw = [{"date": "2026-05-01", "value": "7200"}]
        self.assertEqual(derive.to_millions(raw), [{"date": "2026-05-01", "value": "7.2"}])

    def test_skips_nulls(self):
        self.assertEqual(derive.to_millions([{"date": "2026-05-01", "value": "."}]), [])


if __name__ == "__main__":
    unittest.main()

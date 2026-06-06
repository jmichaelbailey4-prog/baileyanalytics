import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import recessions


class TestRecessions(unittest.TestCase):
    def test_extracts_one_period(self):
        obs = [
            {"date": "2020-01-01", "value": "0"},
            {"date": "2020-02-01", "value": "1"},
            {"date": "2020-03-01", "value": "1"},
            {"date": "2020-04-01", "value": "0"},
        ]
        self.assertEqual(
            recessions.recession_periods(obs),
            [{"start": "2020-02-01", "end": "2020-04-01"}],
        )

    def test_open_ended_period_uses_last_date(self):
        obs = [
            {"date": "2026-01-01", "value": "0"},
            {"date": "2026-02-01", "value": "1"},
        ]
        self.assertEqual(
            recessions.recession_periods(obs),
            [{"start": "2026-02-01", "end": "2026-02-01"}],
        )

    def test_no_recession(self):
        obs = [{"date": "2026-01-01", "value": "0"}]
        self.assertEqual(recessions.recession_periods(obs), [])

    def test_open_ended_with_trailing_null(self):
        obs = [
            {"date": "2026-01-01", "value": "0"},
            {"date": "2026-02-01", "value": "1"},
            {"date": "2026-03-01", "value": "."},
        ]
        # end should be the last non-null date, not the trailing null entry
        self.assertEqual(
            recessions.recession_periods(obs),
            [{"start": "2026-02-01", "end": "2026-02-01"}],
        )


if __name__ == "__main__":
    unittest.main()

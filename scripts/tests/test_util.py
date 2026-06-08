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


if __name__ == "__main__":
    unittest.main()

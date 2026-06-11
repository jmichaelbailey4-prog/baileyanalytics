import json
import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import ledger  # noqa: E402


def _entry(key="economic/cost-of-living/cpi", target="2026-06-01", grade=None,
           made="2026-06-12T06:10:00Z"):
    return {"id": f"{key}@{target}", "key": key,
            "category": "economic", "lens": "cost-of-living", "indicator": "cpi",
            "series_id": "CPIAUCSL", "horizon": "next-print",
            "target_period": target, "due": "2026-07-15", "made_at": made,
            "model": "ets-seasonal@1", "point": 4.31, "lo": 4.02, "hi": 4.6,
            "unit": "%", "value_format": "decimal", "prev_value": 4.17,
            "why": "w", "implied_status": "elevated", "current_status": "elevated",
            "title": "Inflation · CPI (year-over-year)", "short": "CPI",
            "lens_title": "The Cost of Living", "href": "/dashboards/cost-of-living.html",
            "grade": grade}


def _grade(actual=4.17):
    return {"actual": actual, "graded_at": "2026-07-15T06:08:00Z", "hit": True,
            "abs_error": 0.14, "direction_hit": True, "status_hit": True,
            "naive_error": 0.31, "revised_to": None}


class TestLedgerIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_and_load_year_files(self):
        ledger.append_graded(self.dir, _entry(grade=_grade()))
        ledger.append_graded(self.dir, _entry(target="2026-07-01", grade=_grade()))
        rows = ledger.load_all_graded(self.dir)
        self.assertEqual(len(rows), 2)
        self.assertTrue((self.dir / "ledger" / "2026.json").exists())

    def test_append_is_idempotent_per_id(self):
        e = _entry(grade=_grade())
        ledger.append_graded(self.dir, e)
        ledger.append_graded(self.dir, e)
        self.assertEqual(len(ledger.load_all_graded(self.dir)), 1)

    def test_year_rollover(self):
        ledger.append_graded(self.dir, _entry(grade=_grade()))
        e2 = _entry(target="2027-01-01", grade=_grade())
        e2["made_at"] = "2027-01-05T06:00:00Z"
        ledger.append_graded(self.dir, e2)
        self.assertTrue((self.dir / "ledger" / "2027.json").exists())

    def test_set_revision_footnote_only(self):
        e = _entry(grade=_grade())
        ledger.append_graded(self.dir, e)
        changed = ledger.set_revision(self.dir, e["id"], "2026", 4.21)
        self.assertTrue(changed)
        row = ledger.load_all_graded(self.dir)[0]
        self.assertEqual(row["grade"]["revised_to"], 4.21)
        self.assertTrue(row["grade"]["hit"])  # hit never changes
        # idempotent: same revision again is a no-op
        self.assertFalse(ledger.set_revision(self.dir, e["id"], "2026", 4.21))

    def test_open_write_skip_when_unchanged(self):
        wrote1 = ledger.write_open(self.dir, [_entry()])
        wrote2 = ledger.write_open(self.dir, [_entry()])
        self.assertTrue(wrote1)
        self.assertFalse(wrote2)
        data = json.loads((self.dir / "open.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["predictions"]), 1)


class TestAggregates(unittest.TestCase):
    def test_track_record_math(self):
        graded = [
            dict(_entry(grade=_grade()),
                 grade=dict(_grade(), hit=True, abs_error=0.1, naive_error=0.2)),
            dict(_entry(target="2026-07-01"),
                 grade=dict(_grade(), hit=False, abs_error=0.4, naive_error=0.2,
                            direction_hit=False, status_hit=False)),
        ]
        tr = ledger.track_record(graded)
        self.assertEqual(tr["graded"], 2)
        self.assertAlmostEqual(tr["calibration"], 0.5)
        self.assertAlmostEqual(tr["skill"], 1.0 - 0.5 / 0.4)  # 1 - sum(err)/sum(naive)
        self.assertAlmostEqual(tr["direction"], 0.5)
        self.assertAlmostEqual(tr["status"], 0.5)
        self.assertEqual(tr["categories"]["economic"]["graded"], 2)

    def test_recent_shape(self):
        graded = [dict(_entry(grade=_grade()), grade=dict(_grade()))]
        recent = ledger.recent(graded, feed_size=50)
        self.assertIn("economic/cost-of-living/cpi", recent["last"])
        self.assertEqual(len(recent["feed"]), 1)


if __name__ == "__main__":
    unittest.main()

"""Baked-history read path (coverage extension 2026-06-15, spec §3/§5 Q2-Q4).

Banking (FDIC, quarterly), computed spreads, GSCPI (NYFed) and EPU can't be
fetched directly by predict.py — but the lens pipeline already bakes their full
observation history into data/<out>/<lens>.json. predict.py reads those baked
observations instead of re-implementing the fetchers. Two invariants matter:

  1. baked observations are ALREADY post-derive (and post-thin), so the runner
     must NOT re-apply ind.derive (the double-derive trap); and
  2. banking's BankingIndicator has no `series_id`/`derive` attributes at all,
     so the runner must read them defensively.
"""

import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import ledger, roster, runner  # noqa: E402


def _q(i):
    """Quarter-end date for quarter index i, starting 2008-Q1."""
    y = 2008 + i // 4
    month, day = [(3, "31"), (6, "30"), (9, "30"), (12, "31")][i % 4]
    return f"{y:04d}-{month:02d}-{day}"


def _entry(baked, derive=None):
    ind = SimpleNamespace(derive=derive)
    return roster.RosterEntry(key="x/y/z", category="x", lens_id="y",
                              indicator=ind, descriptive=False,
                              market_price=False, baked=baked)


class TestNoDoubleDerive(unittest.TestCase):
    RAW = [{"date": "2020-03-31", "value": "10"}, {"date": "2020-06-30", "value": "20"},
           {"date": "2020-09-30", "value": "30"}, {"date": "2020-12-31", "value": "40"}]

    @staticmethod
    def _zero(obs):  # a derive whose effect is unmistakable
        return [{"date": o["date"], "value": "0"} for o in obs]

    def test_baked_entry_is_not_re_derived(self):
        cleaned, _, _ = runner._prepared_series(
            _entry(baked=True, derive=self._zero), [dict(o) for o in self.RAW])
        self.assertEqual([v for _, v in cleaned], [10.0, 20.0, 30.0, 40.0])

    def test_direct_fetch_entry_is_still_derived(self):
        cleaned, _, _ = runner._prepared_series(
            _entry(baked=False, derive=self._zero), [dict(o) for o in self.RAW])
        self.assertEqual([v for _, v in cleaned], [0.0, 0.0, 0.0, 0.0])


class TestBakedHistory(unittest.TestCase):
    def test_reads_observations_from_lens_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp)
            (data / "banking").mkdir()
            (data / "banking" / "bank-asset-quality.json").write_text(json.dumps({
                "indicators": [
                    {"id": "noncurrent", "observations": [
                        {"date": "2020-03-31", "value": "0.9"},
                        {"date": "2020-06-30", "value": "1.0"}]},
                    {"id": "charge-offs", "observations": [
                        {"date": "2020-03-31", "value": "0.3"}]},
                ]}), encoding="utf-8")
            e = next(x for x in roster.build_roster()
                     if x.key == "banking/bank-asset-quality/noncurrent")
            obs = runner._baked_history(e, data_dir=data)
            self.assertEqual(obs, [{"date": "2020-03-31", "value": "0.9"},
                                   {"date": "2020-06-30", "value": "1.0"}])

    def test_missing_lens_file_degrades_to_empty(self):
        # a not-yet-baked lens file must read as a data gap ([]), not a crash —
        # the runner then keeps the prior open entry (same as _prior_obs does).
        with tempfile.TemporaryDirectory() as tmp:
            e = next(x for x in roster.build_roster()
                     if x.key == "banking/bank-asset-quality/noncurrent")
            self.assertEqual(runner._baked_history(e, data_dir=pathlib.Path(tmp)), [])

    def test_missing_indicator_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp)
            (data / "banking").mkdir()
            (data / "banking" / "bank-asset-quality.json").write_text(
                json.dumps({"indicators": []}), encoding="utf-8")
            e = next(x for x in roster.build_roster()
                     if x.key == "banking/bank-asset-quality/noncurrent")
            self.assertEqual(runner._baked_history(e, data_dir=data), [])

    def test_real_banking_lens_json_is_quarterly_and_long(self):
        # the production baked file: no derive attr, prepares cleanly as quarterly
        e = next(x for x in roster.build_roster()
                 if x.key == "banking/bank-asset-quality/noncurrent")
        self.assertFalse(hasattr(e.indicator, "derive"))
        raw = runner._baked_history(e)
        self.assertTrue(raw)
        cleaned, cad, _ = runner._prepared_series(e, raw)
        self.assertEqual(cad, "quarterly")
        self.assertGreater(len(cleaned), 36)


class TestBankingDryRunFlow(unittest.TestCase):
    def test_banking_tournament_then_daily_emits_open(self):
        e = next(x for x in roster.build_roster()
                 if x.key == "banking/bank-asset-quality/noncurrent")
        hist = {e.key: [{"date": _q(i), "value": f"{0.8 + 0.012 * i + 0.05 * (i % 4):.4f}"}
                        for i in range(60)]}
        with tempfile.TemporaryDirectory() as tmp:
            pred_dir = pathlib.Path(tmp)
            with mock.patch.object(runner, "_load_fixture_histories", return_value=hist):
                n = runner.run_tournament(pred_dir, dry_run=True, entries=[e])
                self.assertEqual(n, 1)
                rec = json.loads((pred_dir / "models.json").read_text(
                    encoding="utf-8"))["indicators"][e.key]
                self.assertEqual(rec["cadence"], "quarterly")
                self.assertEqual(rec["season"], 4)
                runner.run_daily(pred_dir, dry_run=True, entries=[e])
            opens = ledger.load_open(pred_dir)
            self.assertEqual(len(opens), 1)
            o = opens[0]
            self.assertEqual(o["key"], e.key)
            self.assertLessEqual(o["lo"], o["point"])
            self.assertLessEqual(o["point"], o["hi"])
            self.assertIsNone(o["grade"])
            self.assertFalse(o["descriptive"])     # banking is badge-driving signal
            self.assertFalse(o["market_price"])
            # series_id is absent on BankingIndicator; the open entry still carries the field
            self.assertIn("series_id", o)


if __name__ == "__main__":
    unittest.main()

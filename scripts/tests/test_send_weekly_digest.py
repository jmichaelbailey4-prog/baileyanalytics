"""The weekly sender's decision logic: which days form the window, the
publication gate, idempotency, and the guarantee that --dry-run never POSTs."""

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import send_weekly_digest
from lenses import buttondown
from test_weekly_digest import BOARD, day, lens, transition


class WeekOnDisk(unittest.TestCase):
    """A temp data/brief/days/ directory, so no test ever reads live repo data."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.days_dir = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_day(self, date, **kwargs):
        payload = day(date, kwargs.pop("lenses", BOARD), **kwargs)
        (self.days_dir / f"{date}.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload


class TestLoadWeek(WeekOnDisk):
    def test_reads_only_days_inside_the_window(self):
        for date in ("2026-07-18", "2026-07-24", "2026-07-27", "2026-07-31"):
            self.write_day(date)
        loaded = send_weekly_digest.load_week(self.days_dir, "2026-07-31")
        self.assertEqual([(d["generated_at"] or "")[:10] for d in loaded],
                         ["2026-07-27", "2026-07-31"])

    def test_returns_days_in_chronological_order(self):
        for date in ("2026-07-31", "2026-07-27", "2026-07-29"):
            self.write_day(date)
        loaded = send_weekly_digest.load_week(self.days_dir, "2026-07-31")
        self.assertEqual([(d["generated_at"] or "")[:10] for d in loaded],
                         ["2026-07-27", "2026-07-29", "2026-07-31"])

    def test_a_corrupt_day_file_is_skipped_not_fatal(self):
        self.write_day("2026-07-27")
        (self.days_dir / "2026-07-29.json").write_text("{not json", encoding="utf-8")
        loaded = send_weekly_digest.load_week(self.days_dir, "2026-07-31")
        self.assertEqual([(d["generated_at"] or "")[:10] for d in loaded], ["2026-07-27"])

    def test_missing_directory_is_an_empty_week(self):
        self.assertEqual(
            send_weekly_digest.load_week(self.days_dir / "nope", "2026-07-31"), [])


class TestTargetDay(unittest.TestCase):
    def test_date_flag_overrides(self):
        self.assertEqual(send_weekly_digest.target_day(["--date", "2026-07-31"]),
                         "2026-07-31")

    def test_defaults_to_today_utc(self):
        self.assertEqual(send_weekly_digest.target_day([]),
                         datetime.now(timezone.utc).date().isoformat())


class TestMain(WeekOnDisk):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(send_weekly_digest, "DAYS_DIR", self.days_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.list_emails = self.enterContext(
            mock.patch.object(buttondown, "list_emails", return_value={"results": []}))
        self.create = self.enterContext(
            mock.patch.object(buttondown, "create_scheduled", return_value={"id": "e1"}))
        self.enterContext(mock.patch.dict(os.environ, {"BUTTONDOWN_API_KEY": "KEY"}))

    def run_main(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = send_weekly_digest.main(list(args))
        return code, out.getvalue()

    def test_dry_run_prints_and_never_posts(self):
        self.write_day("2026-07-31")
        code, out = self.run_main("--dry-run", "--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.assertIn("The Week in Review, Jul 31, 2026", out)
        self.create.assert_not_called()
        self.list_emails.assert_not_called()

    def test_dry_run_survives_a_non_utf8_stdout(self):
        """Windows consoles and redirects default to cp1252, but brief prose
        carries σ (move sizes) and en-dashes. A dry run must not die on it."""
        self.write_day("2026-07-31", sentence="Payrolls made a 2.3σ move.")
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", newline="")
        with redirect_stdout(stream):
            code = send_weekly_digest.main(["--dry-run", "--date", "2026-07-31"])
            stream.flush()
        self.assertEqual(code, 0)
        self.assertIn("2.3σ", raw.getvalue().decode("utf-8"))

    def test_quiet_week_sends_nothing(self):
        code, out = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_not_called()
        self.assertIn("no email", out.lower())

    def test_a_week_with_one_publication_day_still_sends(self):
        self.write_day("2026-07-28")
        code, _ = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_called_once()

    def test_sends_the_week_scheduled_for_11_utc(self):
        self.write_day("2026-07-27", short="Monday read.")
        self.write_day("2026-07-31", lenses=[lens("job-market", "watch")] + BOARD[1:],
                       transitions=[transition("job-market", "ok", "watch")])
        with mock.patch.object(buttondown, "now_iso", return_value="2026-07-31T10:35:00Z"):
            code, _ = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        _key, subject, html, publish_date = self.create.call_args.args
        self.assertTrue(subject.endswith("The Week in Review, Jul 31, 2026"), subject)
        self.assertEqual(publish_date, "2026-07-31T11:00:00Z")
        self.assertIn("Monday read.", html)

    def test_skips_when_buttondown_already_has_this_week(self):
        self.write_day("2026-07-31")
        self.list_emails.return_value = {
            "results": [{"subject": "calm — The Week in Review, Jul 31, 2026"}]}
        code, out = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_not_called()
        self.assertIn("already", out.lower())

    def test_last_week_s_email_does_not_suppress_this_week(self):
        self.write_day("2026-07-31")
        self.list_emails.return_value = {
            "results": [{"subject": "calm — The Week in Review, Jul 24, 2026"}]}
        code, _ = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_called_once()

    def test_a_legacy_daily_subject_does_not_suppress_the_weekly(self):
        """Daily subjects carry a bare date token; the weekly's is distinct."""
        self.write_day("2026-07-31")
        self.list_emails.return_value = {
            "results": [{"subject": "Today's Brief — 3 alert, Jul 31, 2026"}]}
        code, _ = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_called_once()

    def test_missing_api_key_is_a_quiet_skip(self):
        self.write_day("2026-07-31")
        with mock.patch.dict(os.environ, {}, clear=True):
            code, out = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 0)
        self.create.assert_not_called()
        self.assertIn("BUTTONDOWN_API_KEY", out)

    def test_api_failure_exits_red(self):
        self.write_day("2026-07-31")
        self.create.side_effect = RuntimeError("boom")
        code, _ = self.run_main("--date", "2026-07-31")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

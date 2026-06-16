import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import send_digest

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestShouldSend(unittest.TestCase):
    def test_sends_on_publication_day(self):
        manifest = [{"date": "2026-06-12", "status": "watch", "sentence": "x"}]
        self.assertTrue(send_digest.should_send(manifest, "2026-06-12"))

    def test_skips_quiet_day(self):
        manifest = [{"date": "2026-06-11", "status": "watch", "sentence": "x"}]
        self.assertFalse(send_digest.should_send(manifest, "2026-06-12"))

    def test_skips_empty_manifest(self):
        self.assertFalse(send_digest.should_send([], "2026-06-12"))


class TestAlreadySent(unittest.TestCase):
    def test_detects_existing_email_by_date_token(self):
        emails = {"results": [{"subject": "Today's Brief — 3 alert, Jun 12, 2026"}]}
        self.assertTrue(send_digest.already_sent(emails, "Jun 12, 2026"))

    def test_different_day_not_sent(self):
        emails = {"results": [{"subject": "Today's Brief — calm, Jun 11, 2026"}]}
        self.assertFalse(send_digest.already_sent(emails, "Jun 12, 2026"))

    def test_handles_missing_results(self):
        self.assertFalse(send_digest.already_sent({}, "Jun 12, 2026"))


class TestPublishAt(unittest.TestCase):
    def test_before_11_utc_schedules_for_11(self):
        self.assertEqual(send_digest.publish_at("2026-06-12", "2026-06-12T06:05:00Z"),
                         "2026-06-12T11:00:00Z")

    def test_after_11_utc_schedules_a_few_minutes_out_not_now(self):
        # Past the 11:00 target -> now + buffer, never exactly "now" (Buttondown
        # 400s a scheduled publish_date that isn't safely in the future).
        out = send_digest.publish_at("2026-06-12", "2026-06-12T13:02:00Z")
        self.assertEqual(out, "2026-06-12T13:07:00Z")
        self.assertGreater(out, "2026-06-12T13:02:00Z")

    def test_publish_date_is_always_in_the_future(self):
        for now in ("2026-06-12T00:00:00Z", "2026-06-12T11:00:00Z",
                    "2026-06-12T13:02:00Z", "2026-06-12T23:59:00Z"):
            self.assertGreater(send_digest.publish_at("2026-06-12", now), now)


if __name__ == "__main__":
    unittest.main()

"""The shared Buttondown client used by both senders."""

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import buttondown


class TestPublishAt(unittest.TestCase):
    def test_before_11_utc_schedules_for_11(self):
        self.assertEqual(buttondown.publish_at("2026-06-12", "2026-06-12T06:05:00Z"),
                         "2026-06-12T11:00:00Z")

    def test_after_11_utc_schedules_a_few_minutes_out_not_now(self):
        # Buttondown 400s a scheduled publish_date that isn't safely in the future.
        self.assertEqual(buttondown.publish_at("2026-06-12", "2026-06-12T13:02:00Z"),
                         "2026-06-12T13:07:00Z")

    def test_publish_date_is_always_in_the_future(self):
        for now in ("2026-06-12T00:00:00Z", "2026-06-12T11:00:00Z",
                    "2026-06-12T13:02:00Z", "2026-06-12T23:59:00Z"):
            self.assertGreater(buttondown.publish_at("2026-06-12", now), now)


class TestAlreadySent(unittest.TestCase):
    def test_detects_existing_email_by_token(self):
        emails = {"results": [{"subject": "3 alert — The Week in Review, Jul 31, 2026"}]}
        self.assertTrue(buttondown.already_sent(emails, "The Week in Review, Jul 31, 2026"))

    def test_different_week_not_sent(self):
        emails = {"results": [{"subject": "calm — The Week in Review, Jul 24, 2026"}]}
        self.assertFalse(buttondown.already_sent(emails, "The Week in Review, Jul 31, 2026"))

    def test_handles_missing_results(self):
        self.assertFalse(buttondown.already_sent({}, "The Week in Review, Jul 31, 2026"))
        self.assertFalse(buttondown.already_sent(None, "The Week in Review, Jul 31, 2026"))


class TestApiCalls(unittest.TestCase):
    def test_list_emails_asks_for_newest_first(self):
        """The dedup scan reads the first page, so ordering must be explicit."""
        with mock.patch.object(buttondown, "request", return_value={"results": []}) as req:
            buttondown.list_emails("KEY")
        req.assert_called_once_with(buttondown.LIST_URL, "KEY")
        self.assertIn("ordering=-creation_date", buttondown.LIST_URL)

    def test_create_scheduled_posts_a_scheduled_email(self):
        with mock.patch.object(buttondown, "request", return_value={"id": "abc"}) as req:
            out = buttondown.create_scheduled("KEY", "Subject", "<p>Body</p>",
                                              "2026-07-31T11:00:00Z")
        self.assertEqual(out, {"id": "abc"})
        req.assert_called_once_with(
            buttondown.API, "KEY",
            {"subject": "Subject", "body": "<p>Body</p>",
             "status": "scheduled", "publish_date": "2026-07-31T11:00:00Z"})


if __name__ == "__main__":
    unittest.main()

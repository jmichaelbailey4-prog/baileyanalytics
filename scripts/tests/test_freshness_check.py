"""Unit tests for the pipeline freshness monitor's pure logic.

The monitor (scripts/tools/freshness_check.py) is split into a pure decision
core (tested here) and a thin GitHub API I/O shell (not unit-tested — it only
wires the core to urllib). Everything that decides *whether the pipeline is
stale* and *what to do about it* lives in the functions exercised below.
"""

import pathlib
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import freshness_check as fc


def _run(conclusion, updated_at, status="completed"):
    """A minimal GitHub Actions workflow-run object (only the fields we read)."""
    return {
        "conclusion": conclusion,
        "status": status,
        "updated_at": updated_at,
        "html_url": "https://github.com/o/r/actions/runs/1",
    }


class LatestSuccessTests(unittest.TestCase):
    def test_returns_updated_at_of_most_recent_success(self):
        runs = [
            _run("success", "2026-06-17T13:05:00Z"),
            _run("success", "2026-06-17T06:05:00Z"),
        ]
        self.assertEqual(fc.latest_success(runs), "2026-06-17T13:05:00Z")

    def test_ignores_non_success_runs(self):
        # A failed run and an in-progress run (conclusion null) must not count —
        # only a *successful completion* proves the pipeline ran end to end.
        runs = [
            _run("failure", "2026-06-17T13:05:00Z"),
            _run(None, "2026-06-17T13:00:00Z", status="in_progress"),
            _run("success", "2026-06-17T06:05:00Z"),
        ]
        self.assertEqual(fc.latest_success(runs), "2026-06-17T06:05:00Z")

    def test_picks_max_updated_at_regardless_of_list_order(self):
        # The API returns newest-first, but never rely on that — take the max.
        runs = [
            _run("success", "2026-06-15T06:05:00Z"),
            _run("success", "2026-06-17T13:05:00Z"),
            _run("success", "2026-06-16T06:05:00Z"),
        ]
        self.assertEqual(fc.latest_success(runs), "2026-06-17T13:05:00Z")

    def test_returns_none_when_no_successful_run(self):
        self.assertIsNone(fc.latest_success([_run("failure", "2026-06-17T13:05:00Z")]))

    def test_returns_none_for_empty(self):
        self.assertIsNone(fc.latest_success([]))


class EvaluateTests(unittest.TestCase):
    NOW = datetime(2026, 6, 17, 14, 0, 0, tzinfo=timezone.utc)

    def test_fresh_when_within_threshold(self):
        r = fc.evaluate("2026-06-17T13:00:00Z", self.NOW, threshold_hours=30)
        self.assertFalse(r["stale"])
        self.assertAlmostEqual(r["age_hours"], 1.0, places=3)
        self.assertEqual(r["last_success"], "2026-06-17T13:00:00Z")
        self.assertEqual(r["threshold_hours"], 30)

    def test_stale_when_older_than_threshold(self):
        r = fc.evaluate("2026-06-16T00:00:00Z", self.NOW, threshold_hours=30)  # 38h
        self.assertTrue(r["stale"])
        self.assertAlmostEqual(r["age_hours"], 38.0, places=3)

    def test_not_stale_exactly_at_threshold(self):
        last = (self.NOW - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = fc.evaluate(last, self.NOW, threshold_hours=30)
        self.assertFalse(r["stale"])  # strictly-greater semantics

    def test_stale_when_no_success_at_all(self):
        r = fc.evaluate(None, self.NOW, threshold_hours=30)
        self.assertTrue(r["stale"])
        self.assertIsNone(r["age_hours"])
        self.assertIn("no successful", r["reason"].lower())


class FindMonitorIssueTests(unittest.TestCase):
    MARKER = "<!-- freshness-monitor -->"

    def test_finds_open_issue_carrying_the_marker(self):
        issues = [
            {"number": 1, "body": "something unrelated"},
            {"number": 2, "body": f"Pipeline looks stale {self.MARKER} more text"},
        ]
        self.assertEqual(fc.find_monitor_issue(issues, self.MARKER)["number"], 2)

    def test_skips_pull_requests_even_with_marker(self):
        # The list-issues endpoint also returns PRs; they carry a pull_request key.
        issues = [
            {"number": 5, "body": self.MARKER, "pull_request": {"url": "x"}},
            {"number": 6, "body": self.MARKER},
        ]
        self.assertEqual(fc.find_monitor_issue(issues, self.MARKER)["number"], 6)

    def test_returns_none_when_marker_absent(self):
        self.assertIsNone(fc.find_monitor_issue([{"number": 1, "body": "nope"}], self.MARKER))

    def test_tolerates_missing_or_null_body(self):
        self.assertIsNone(fc.find_monitor_issue([{"number": 1, "body": None}], self.MARKER))
        self.assertIsNone(fc.find_monitor_issue([{"number": 1}], self.MARKER))


class DecideActionTests(unittest.TestCase):
    def test_stale_and_no_existing_issue_creates(self):
        self.assertEqual(fc.decide_action({"stale": True}, None), "create")

    def test_stale_and_existing_issue_updates(self):
        self.assertEqual(fc.decide_action({"stale": True}, {"number": 1}), "update")

    def test_fresh_and_existing_issue_resolves(self):
        self.assertEqual(fc.decide_action({"stale": False}, {"number": 1}), "resolve")

    def test_fresh_and_no_issue_is_noop(self):
        self.assertEqual(fc.decide_action({"stale": False}, None), "noop")


class BuildTextTests(unittest.TestCase):
    def test_parse_iso_treats_z_suffix_as_utc(self):
        self.assertEqual(
            fc.parse_iso("2026-06-17T14:23:34Z"),
            datetime(2026, 6, 17, 14, 23, 34, tzinfo=timezone.utc),
        )

    def test_alert_body_carries_marker_and_key_facts(self):
        result = {
            "stale": True, "age_hours": 38.0, "last_success": "2026-06-16T00:00:00Z",
            "threshold_hours": 30, "reason": "last success 38.0h ago",
        }
        body = fc.build_alert_body(
            result, repo="jmichaelbailey4-prog/baileyanalytics",
            workflow="refresh-fred.yml", runs_url="https://github.com/o/r/actions",
            marker=fc.MARKER,
        )
        self.assertIn(fc.MARKER, body)            # so the next run finds this issue
        self.assertIn("refresh-fred.yml", body)
        self.assertIn("38", body)                 # age
        self.assertIn("30", body)                 # threshold

    def test_alert_title_is_nonempty_and_stable(self):
        self.assertTrue(fc.build_alert_title().strip())

    def test_recovery_comment_reports_the_recovery(self):
        c = fc.build_recovery_comment(
            {"last_success": "2026-06-17T13:00:00Z", "age_hours": 1.0, "threshold_hours": 30})
        self.assertTrue(c.strip())
        self.assertIn("2026-06-17T13:00:00Z", c)


if __name__ == "__main__":
    unittest.main()

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import build, util


class TestStatusBlend(unittest.TestCase):
    def test_all_ok_is_ok(self):
        self.assertEqual(util.status_blend(["ok", "ok", "ok"]), "ok")

    def test_one_watch_among_four_ok_stays_ok(self):
        # RMS = sqrt(1/4) = 0.5 < 0.6 — a single first-warning lens doesn't
        # flip a broadly healthy category.
        self.assertEqual(util.status_blend(["ok", "ok", "ok", "watch"]), "ok")

    def test_one_watch_of_two_is_watch(self):
        # RMS = sqrt(1/2) ≈ 0.707 — more concentrated, fair to flag.
        self.assertEqual(util.status_blend(["ok", "watch"]), "watch")

    def test_economy_profile_is_watch(self):
        # 3 ok + 2 elevated: RMS = sqrt(8/5) ≈ 1.26
        self.assertEqual(util.status_blend(["ok", "ok", "ok", "elevated", "elevated"]),
                         "watch")

    def test_consumer_profile_is_elevated(self):
        # ok+watch+elevated+alert: RMS = sqrt(14/4) ≈ 1.87 — the alert is the
        # callout's job; the category reads elevated.
        self.assertEqual(util.status_blend(["ok", "watch", "elevated", "alert"]),
                         "elevated")

    def test_broad_stress_is_alert(self):
        # alert+alert+elevated+elevated: RMS = sqrt(26/4) ≈ 2.55
        self.assertEqual(util.status_blend(["alert", "alert", "elevated", "elevated"]),
                         "alert")

    def test_single_lens_alert_is_alert(self):
        self.assertEqual(util.status_blend(["alert"]), "alert")

    def test_one_alert_among_three_ok_is_elevated(self):
        # RMS = sqrt(9/4) = exactly 1.5, the watch/elevated edge: a lone alert
        # lifts the category one notch (the alert itself is the tile callout's
        # job). Changing this band is a deliberate semantic decision.
        self.assertEqual(util.status_blend(["alert", "ok", "ok", "ok"]), "elevated")

    def test_neutral_info_unknown_excluded(self):
        self.assertEqual(util.status_blend(["ok", "neutral", "info", "unknown", "ok"]),
                         "ok")

    def test_no_severity_lenses_is_neutral(self):
        self.assertEqual(util.status_blend(["neutral", "info"]), "neutral")
        self.assertEqual(util.status_blend([]), "neutral")


class TestBuildIndexStatus(unittest.TestCase):
    def _lens(self, status):
        return {"id": f"l-{status}", "title": "L", "accent": "#a", "status": status,
                "headline_read": "h",
                "indicators": [{"short": "s", "unit": "%", "observations": [],
                                "latest": None}]}

    def test_index_carries_blended_status(self):
        idx = build.build_index([self._lens("ok"), self._lens("ok"),
                                 self._lens("ok"), self._lens("elevated"),
                                 self._lens("elevated")])
        self.assertEqual(idx["status"], "watch")

    def test_index_neutral_when_no_severity(self):
        idx = build.build_index([self._lens("neutral")])
        self.assertEqual(idx["status"], "neutral")


if __name__ == "__main__":
    unittest.main()

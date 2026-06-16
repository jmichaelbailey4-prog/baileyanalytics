import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import digest

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestSubject(unittest.TestCase):
    def test_transition_led_subject(self):
        sub = digest.build_digest(TODAY)["subject"]
        self.assertEqual(
            sub, "Electricity & the Grid tips to ELEVATED — Today's Brief, Jun 12, 2026")

    def test_improving_transition_wording(self):
        t = dict(TODAY)
        t["transitions"] = [dict(TODAY["transitions"][0],
                                 direction="improving", from_status="elevated",
                                 to_status="watch")]
        self.assertIn("improves to WATCH", digest.build_digest(t)["subject"])

    def test_counts_subject_when_no_transitions(self):
        quiet = dict(TODAY, transitions=[])
        sub = digest.build_digest(quiet)["subject"]
        self.assertEqual(sub, "Today's Brief — 3 alert · 8 elevated · 3 on watch, Jun 12, 2026")

    def test_date_token_always_present(self):
        self.assertIn("Jun 12, 2026", digest.build_digest(TODAY)["subject"])
        self.assertEqual(digest.date_token("2026-06-12"), "Jun 12, 2026")


class TestBody(unittest.TestCase):
    def setUp(self):
        self.html = digest.build_digest(TODAY)["html"]

    def test_verdict_and_sections_present(self):
        self.assertIn("Most of the economy is on solid footing", self.html)
        self.assertIn("WATCH", self.html)
        self.assertIn("Electricity &amp; the Grid", self.html)
        self.assertIn("18.97¢/kWh", self.html)

    def test_links_are_absolute_and_permalink_present(self):
        self.assertIn("https://baileyanalytics.com/dashboards/brief/2026-06-12.html", self.html)
        self.assertNotIn('href="/dashboards', self.html)

    def test_unsubscribe_variable_present(self):
        self.assertIn("{{ unsubscribe_url }}", self.html)

    def test_movers_capped_at_five(self):
        t = dict(TODAY, transitions=[],
                 top_moves=[dict(TODAY["top_moves"][0], lens_title=f"Lens {i}")
                            for i in range(8)])
        html = digest.build_digest(t)["html"]
        self.assertIn("Lens 4", html)
        self.assertNotIn("Lens 5", html)

    def test_pressure_count_line(self):
        self.assertIn("14 readings warrant attention", self.html)  # 3+8+3 from status_counts

    def test_mover_why_in_body(self):
        # the self-grounded mover "why" rides along in the email mover row
        self.assertIn("up 3 readings in a row", self.html)


if __name__ == "__main__":
    unittest.main()

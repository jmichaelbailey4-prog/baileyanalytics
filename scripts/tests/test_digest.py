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

    def test_relationship_lead_renders_in_body(self):
        # D6: the curated relationship lead (from the fixture) appears in the email
        self.assertIn("real incomes fall by definition", self.html)

    def test_relationship_lead_leads_changed_section(self):
        sentence = "Real incomes and spending have moved together over time."
        t = dict(TODAY, synthesis={"cooccurrence": "", "relationships": [sentence]})
        html = digest.build_digest(t)["html"]
        self.assertIn(sentence, html)
        self.assertLess(html.index("What changed today"), html.index(sentence))

    def test_no_relationship_lead_when_silent(self):
        t = dict(TODAY, synthesis={"cooccurrence": "", "relationships": []})
        html = digest.build_digest(t)["html"]
        self.assertNotIn("real incomes fall by definition", html)  # silent path emits nothing
        self.assertIn("What changed today", html)                  # section still renders

    def test_relationship_lead_is_escaped(self):
        t = dict(TODAY, synthesis={"relationships": ["risk & reward <note>"]})
        html = digest.build_digest(t)["html"]
        self.assertIn("risk &amp; reward &lt;note&gt;", html)


class TestWatchingVerb(unittest.TestCase):
    def _row(self, current, implied):
        return {"key": "k", "title": "Months of New-Home Supply", "lens_title":
                "Supply & Construction", "point_fmt": "10.00 months", "change": True,
                "current_status": current, "implied_status": implied, "href": "/x"}

    def test_worsening_says_tip(self):
        t = dict(TODAY, watching=[self._row("watch", "elevated")])
        self.assertIn("would tip", digest.build_digest(t)["html"])

    def test_improving_says_ease(self):
        t = dict(TODAY, watching=[self._row("alert", "elevated")])
        html = digest.build_digest(t)["html"]
        self.assertIn("would ease", html)
        self.assertNotIn("would tip", html)


if __name__ == "__main__":
    unittest.main()

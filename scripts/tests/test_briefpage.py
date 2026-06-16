import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import briefpage

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "today_sample.json"
TODAY = json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestRenderToday(unittest.TestCase):
    def setUp(self):
        self.html = briefpage.render_brief(TODAY, og_image="/og/brief-2026-06-12.png")

    def test_is_complete_static_document(self):
        self.assertTrue(self.html.startswith("<!DOCTYPE html>"))
        self.assertNotIn("Loading", self.html)
        self.assertNotIn("fetch(", self.html)          # fully static, no JS render

    def test_head_essentials(self):
        self.assertIn('<link rel="canonical" href="https://baileyanalytics.com/dashboards/brief.html">', self.html)
        self.assertIn('property="og:image" content="https://baileyanalytics.com/og/brief-2026-06-12.png"', self.html)
        self.assertIn('"@type": "NewsArticle"', self.html)
        self.assertIn('name="twitter:card" content="summary_large_image"', self.html)

    def test_jsonld_cannot_break_out_of_script(self):
        # a verdict sentence containing </script> or < must be \uXXXX-escaped in
        # the JSON-LD payload so it can't terminate the <script> block early.
        t = dict(TODAY, verdict={"status": "watch", "sentence": "Risk </script><b> & fell."})
        html = briefpage.render_brief(t, og_image="/og/x.png")
        ld = html.split('application/ld+json">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<", ld)
        self.assertNotIn(">", ld)
        self.assertIn("\\u003c", ld)

    def test_verdict_and_sections(self):
        self.assertIn("Most of the economy is on solid footing", self.html)
        self.assertIn('class="badge watch"', self.html)
        self.assertIn("What changed today", self.html)
        self.assertIn("Electricity &amp; the Grid", self.html)      # escaped title
        self.assertIn("What we&rsquo;re watching next", self.html)
        self.assertIn("18.97¢/kWh", self.html)
        self.assertIn('id="alert"', self.html)                       # deep-link anchors
        self.assertIn("As of June 12, 2026", self.html)

    def test_transitions_use_dedicated_brief_trans_markup(self):
        # Status changes are the flagship event — they must carry the
        # .brief-trans / .brief-arrow classes lens.css styles, not collapse
        # into the generic .att-row pressure styling.
        self.assertIn('class="brief-trans"', self.html)
        self.assertIn('class="brief-arrow"', self.html)
        self.assertIn('class="brief-trans-read"', self.html)

    def test_sparkline_svg_baked(self):
        self.assertIn("<svg class=\"spark\"", self.html)
        self.assertIn("polyline", self.html)

    def test_mover_why_renders(self):
        # the per-mover 'why' appears as its own line inside the mover card
        self.assertIn('class="hub-why"', self.html)
        self.assertIn("up 3 readings in a row", self.html)

    def test_cooccurrence_renders_under_verdict(self):
        # the structural synthesis line sits with the verdict
        self.assertIn("Four of today", self.html)
        self.assertIn("about the cost of living", self.html)

    def test_relationship_lead_renders_in_what_changed(self):
        # D6: the curated relationship sentence leads the "What changed today"
        # section (above the status changes), in its own .brief-rel element.
        sentence = "Real incomes and consumer spending move together over time."
        t = dict(TODAY, synthesis={"cooccurrence": "", "relationships": [sentence]})
        html = briefpage.render_brief(t, og_image="/og/x.png")
        self.assertIn('class="brief-rel"', html)
        self.assertIn(sentence, html)
        # it leads the section: appears after the "What changed today" heading but
        # before the first status-change row
        self.assertLess(html.index("What changed today"), html.index(sentence))
        self.assertLess(html.index(sentence), html.index('class="brief-trans"'))

    def test_no_relationship_line_when_map_silent(self):
        # quiet-day: no active edge -> no .brief-rel element at all
        t = dict(TODAY, synthesis={"cooccurrence": "", "relationships": []})
        html = briefpage.render_brief(t, og_image="/og/x.png")
        self.assertNotIn('class="brief-rel"', html)

    def test_relationship_line_is_escaped(self):
        # reader-facing copy is HTML-escaped like every other rendered string
        t = dict(TODAY, synthesis={"relationships": ["A <b>risk</b> & reward note."]})
        html = briefpage.render_brief(t, og_image="/og/x.png")
        self.assertIn("A &lt;b&gt;risk&lt;/b&gt; &amp; reward note.", html)
        self.assertNotIn("<b>risk</b>", html)

    def test_no_archive_banner_on_today(self):
        self.assertNotIn("archive-banner", self.html)


class TestRenderArchive(unittest.TestCase):
    def setUp(self):
        self.html = briefpage.render_brief(
            TODAY, og_image="/og/brief-2026-06-12.png", archive_date="2026-06-12",
            prev_date="2026-06-11", next_date=None)

    def test_archive_chrome(self):
        self.assertIn("archive-banner", self.html)
        self.assertIn("see today&rsquo;s brief", self.html)
        self.assertIn('href="/dashboards/brief/2026-06-11.html"', self.html)
        self.assertIn('<link rel="canonical" href="https://baileyanalytics.com/dashboards/brief/2026-06-12.html">', self.html)

    def test_next_link_renders_when_given(self):
        html = briefpage.render_brief(TODAY, og_image="/og/x.png",
                                      archive_date="2026-06-11", next_date="2026-06-12")
        self.assertIn('href="/dashboards/brief/2026-06-12.html"', html)


class TestQuietDay(unittest.TestCase):
    def test_no_transitions_message(self):
        quiet = dict(TODAY, transitions=[], top_moves=[])
        html = briefpage.render_brief(quiet, og_image="/og/x.png")
        self.assertIn("No status changes today", html)

    def test_empty_today_does_not_raise(self):
        html = briefpage.render_brief({}, og_image="/og/x.png")
        self.assertTrue(html.startswith("<!DOCTYPE html>"))

    def test_verdict_missing_status_does_not_raise(self):
        t = dict(TODAY, verdict={"sentence": "Sentence only."})
        html = briefpage.render_brief(t, og_image="/og/x.png")
        self.assertIn("Sentence only.", html)
        self.assertIn('class="badge unknown"', html)


class TestArchiveIndex(unittest.TestCase):
    def test_lists_entries_newest_first_grouped_by_month(self):
        manifest = [
            {"date": "2026-06-11", "status": "watch", "sentence": "Calm-ish."},
            {"date": "2026-06-12", "status": "elevated", "sentence": "Strain showing."},
        ]
        html = briefpage.render_archive_index(manifest)
        self.assertIn("June 2026", html)
        self.assertIn('href="/dashboards/brief/2026-06-12.html"', html)
        self.assertLess(html.index("2026-06-12"), html.index("2026-06-11"))
        self.assertIn('class="badge elevated"', html)

    def test_back_link_uses_defined_back_class(self):
        # the archive listing's back link must use the styled .back class, not the
        # undefined .hub-back (which renders unstyled).
        html = briefpage.render_archive_index(
            [{"date": "2026-06-12", "status": "ok", "sentence": "x."}])
        self.assertIn('class="back"', html)
        self.assertNotIn("hub-back", html)


if __name__ == "__main__":
    unittest.main()

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import staticread

LENS = {
    "id": "recession-watch", "title": "Recession Watch", "status": "ok",
    "headline_read": "The economy looks steady — no major recession signals right now.",
    "last_updated": "2026-06-12T06:01:00Z",
    "indicators": [
        {"id": "yield-curve", "title": "Yield Curve · 10-Year minus 2-Year",
         "short": "Yield curve", "unit": "%", "value_format": "decimal",
         "latest": {"date": "2026-06-11", "value": "0.40"},
         "observations": [{"date": "2026-01-01", "value": "1.20"},
                          {"date": "2026-02-01", "value": "0.95"},
                          {"date": "2026-03-01", "value": "0.85"},
                          {"date": "2026-04-01", "value": "0.70"},
                          {"date": "2026-05-01", "value": "0.55"},
                          {"date": "2026-06-11", "value": "0.40"}],
         "read": "The gap between 10-year and 2-year Treasury yields is positive."},
        {"id": "payrolls", "title": "Payrolls", "short": "Payrolls", "unit": "",
         "value_format": "thousands", "latest": {"date": "2026-05-01", "value": "172000"},
         "read": "Hiring is holding up."},
        {"id": "broken", "title": "No Data", "short": "n/a", "unit": "%",
         "value_format": "decimal", "latest": None, "read": "No data yet."},
    ],
}


class TestRenderFragment(unittest.TestCase):
    def setUp(self):
        self.html = staticread.render_fragment(LENS)

    def test_wraps_in_baked_read_section(self):
        self.assertTrue(self.html.startswith('<section id="baked-read">'))
        self.assertTrue(self.html.endswith("</section>"))

    def test_headline_and_reads_present_escaped(self):
        self.assertIn("The economy looks steady", self.html)
        self.assertIn("Yield Curve · 10-Year minus 2-Year", self.html)
        self.assertIn("positive", self.html)

    def test_headline_is_a_top_level_h1(self):
        # No-JS readers/crawlers need an <h1>; the fragment used to lead with <h2>
        # so the static document had no top-level heading. lens.js wipes #lens-root
        # and renders its own <h1 class="read-hero">, so JS users never see two.
        self.assertIn("<h1>The economy looks steady", self.html)
        self.assertNotIn("<h2>", self.html)   # the headline was the only h2

    def test_values_formatted_like_fmtval(self):
        self.assertIn("0.40%", self.html)        # decimal + % stays tight
        self.assertIn("172,000", self.html)      # thousands format

    def test_missing_latest_renders_dash(self):
        self.assertIn("—", self.html)

    def test_indicator_why_renders_when_observations_present(self):
        # the self-grounded per-indicator why (period-neutral wording for the
        # static read), reusing the .hub-why style
        self.assertIn('class="hub-why"', self.html)
        self.assertIn("Yield curve: down 5 readings in a row", self.html)
        self.assertIn("recent readings", self.html)

    def test_only_indicators_with_a_signal_get_a_why(self):
        # payrolls + the broken indicator carry no observations -> no why line;
        # only the yield-curve series clears the bar
        self.assertEqual(self.html.count('class="hub-why"'), 1)

    def test_why_carries_no_causal_token(self):
        # INV-1 holds on the rendered fragment too — extract every why robustly
        import re
        from lenses import synthesis
        whys = re.findall(r'<p class="hub-why">(.*?)</p>', self.html)
        self.assertTrue(whys)  # the fixture's yield-curve series yields one
        for w in whys:
            self.assertEqual(synthesis.find_causal_tokens(w), [], f"causal token in why: {w!r}")


class TestStaticBands(unittest.TestCase):
    """No-JS readers get a static band summary + a deep link to the methodology
    page, for scored signals only (matched by real config lens/indicator ids)."""
    def _frag(self, lens_id, ind_id):
        lens = {"id": lens_id, "title": "T", "status": "ok", "headline_read": "H",
                "last_updated": "2026-06-12T06:01:00Z",
                "indicators": [{"id": ind_id, "title": "I", "short": "I", "unit": "",
                                "value_format": "decimal", "observations": [],
                                "latest": {"date": "2026-05-01", "value": "260000"},
                                "read": "r."}]}
        return staticread.render_fragment(lens)

    def test_severity_indicator_gets_bands_and_methodology_link(self):
        html = self._frag("recession-watch", "jobless-claims")  # rule_claims, level
        self.assertIn('class="hub-bands"', html)
        self.assertIn("/dashboards/methodology.html#recession-watch--jobless-claims", html)
        self.assertIn("250,000", html)  # an edge, formatted thousands from the spec

    def test_custom_axis_indicator_has_no_bands(self):
        self.assertNotIn('class="hub-bands"', self._frag("recession-watch", "yield-curve"))

    def test_unknown_indicator_has_no_bands(self):
        self.assertNotIn('class="hub-bands"', self._frag("recession-watch", "not-a-real-id"))


class TestSignalNote(unittest.TestCase):
    def _html(self, **reasons):
        lens = {"id": "x", "title": "X", "status": "ok", "headline_read": "H",
                "last_updated": "2026-06-12T06:01:00Z",
                "indicators": [dict({"id": "i", "title": "I", "short": "I", "unit": "%",
                                     "value_format": "decimal", "latest": None,
                                     "observations": [], "read": "r."}, **reasons)]}
        return staticread.render_fragment(lens)

    def test_combined_note_when_both_reasons(self):
        html = self._html(no_severity_reason="No score.", no_prediction_reason="No forecast.")
        self.assertIn('class="signal-note"', html)
        self.assertIn("Why it isn’t scored or forecast", html)  # curly ’, matches lens.js
        self.assertIn("No score. No forecast.", html)

    def test_no_note_when_scored_and_predicted(self):
        self.assertNotIn('class="signal-note"', self._html())


class TestEscaping(unittest.TestCase):
    def test_special_chars_in_all_fields_are_escaped(self):
        # the #baked-read fragment is HTML; every data-derived field must be
        # escaped (headline, indicator title/short/read). A literal '&' already
        # occurs in machine copy, and a future label could carry '<'/'>'.
        lens = {
            "id": "x", "title": "X", "status": "ok",
            "headline_read": "Risk <b> & reward.",
            "last_updated": "2026-06-12T06:01:00Z",
            "indicators": [
                {"id": "i", "title": "P&L < risk", "short": "P&L",
                 "unit": "%", "value_format": "decimal",
                 "latest": {"date": "2026-06-11", "value": "0.40"},
                 "observations": [], "read": "Tight <spread> & wide."},
            ],
        }
        html = staticread.render_fragment(lens)
        self.assertIn("Risk &lt;b&gt; &amp; reward.", html)
        self.assertIn("P&amp;L &lt; risk", html)
        self.assertIn("Tight &lt;spread&gt; &amp; wide.", html)
        self.assertNotIn("<b>", html)
        self.assertNotIn("<spread>", html)


if __name__ == "__main__":
    unittest.main()

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
        # INV-1 holds on the rendered fragment too
        from lenses import synthesis
        self.assertEqual(synthesis.find_causal_tokens(self.html.split("hub-why")[1][:120]
                                                       if "hub-why" in self.html else ""), [])


if __name__ == "__main__":
    unittest.main()

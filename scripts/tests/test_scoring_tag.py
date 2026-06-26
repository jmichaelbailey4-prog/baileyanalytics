"""tools/scoring_tag.py idempotently stamps scoring.js after predict.js on lens pages."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools import scoring_tag  # noqa: E402

PREDICT = '<script defer src="/dashboards/predict.js"></script>'
SCORING = '<script defer src="/dashboards/scoring.js"></script>'


class TestInject(unittest.TestCase):
    def test_inserts_after_predict(self):
        html = "<body>\n  " + PREDICT + "\n</body>"
        out = scoring_tag.inject(html)
        self.assertIn(SCORING, out)
        self.assertLess(out.index(PREDICT), out.index(SCORING))

    def test_idempotent(self):
        html = "<body>\n  " + PREDICT + "\n  " + SCORING + "\n</body>"
        self.assertEqual(scoring_tag.inject(html), html)

    def test_skips_pages_without_predict(self):
        html = '<body>\n  <script defer src="/dashboards/lens.js"></script>\n</body>'
        self.assertEqual(scoring_tag.inject(html), html)


if __name__ == "__main__":
    unittest.main()

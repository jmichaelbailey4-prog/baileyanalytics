"""The Buttondown username is the source of truth in briefpage.py, but the home
and About pages carry hand-written subscribe forms with the action URL baked in.
This guards against the three drifting apart at account-creation time (the
failure the code review flagged: a silently-broken form with no test on it)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import briefpage

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestSubscribeFormConsistency(unittest.TestCase):
    def test_handwritten_forms_match_buttondown_username(self):
        expected = ("buttondown.com/api/emails/embed-subscribe/"
                    f"{briefpage.BUTTONDOWN_USERNAME}")
        for page in ("index.html", "about.html"):
            html = (REPO / page).read_text(encoding="utf-8")
            self.assertIn(expected, html,
                          f"{page} subscribe form action is out of sync with "
                          "briefpage.BUTTONDOWN_USERNAME")


if __name__ == "__main__":
    unittest.main()

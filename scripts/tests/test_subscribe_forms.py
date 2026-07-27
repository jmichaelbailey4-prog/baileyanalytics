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


# The email went weekly on 2026-07-27. A sign-up promise that still says "every
# morning" is a promise the pipeline no longer keeps, so no shipped surface may
# carry the old cadence — including the already-baked archive back catalogue,
# whose subscribe band is a live CTA even though the page itself is historical.
DAILY_PROMISES = ("every morning the board changes", "Want this read daily",
                  "daily brief by email", "Get Today&rsquo;s Brief in your inbox")


def shipped_pages():
    """Every hand-written or baked reader-facing surface. Excludes docs/ and
    .superpowers/ (design notes legitimately quote the retired copy)."""
    skip = {"docs", ".superpowers", "scripts", "node_modules", ".git"}
    for path in list(REPO.glob("*.html")) + list(REPO.glob("dashboards/**/*.html")) \
            + list(REPO.glob("dashboards/*.js")):
        if not skip & set(path.relative_to(REPO).parts):
            yield path


class TestEmailCadenceCopy(unittest.TestCase):
    def test_no_shipped_surface_promises_a_daily_email(self):
        offenders = [
            f"{path.relative_to(REPO)}: {promise!r}"
            for path in shipped_pages()
            for promise in DAILY_PROMISES
            if promise in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [], "stale daily-email promise still shipping")

    def test_the_baked_subscribe_band_names_the_weekly_cadence(self):
        self.assertIn("Friday", briefpage._subscribe())

    def test_handwritten_pages_name_the_weekly_cadence(self):
        for page in ("index.html", "about.html"):
            self.assertIn("Friday", (REPO / page).read_text(encoding="utf-8"), page)


if __name__ == "__main__":
    unittest.main()

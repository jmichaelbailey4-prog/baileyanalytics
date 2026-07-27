"""The weekly roundup builder: window selection, net status changes across the
week, move dedup, and the assembled email."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import weekly_digest

# Sparklines engineered for a predictable brief.move_score (|last step| / pstdev
# of the prior steps): the prior steps are always +1,-1,+1,-1 (pstdev 1.0), so
# the score is just the size of the final step.
def spark(final_step):
    return [1.0, 2.0, 1.0, 2.0, 1.0, 1.0 + final_step]


def lens(lens_id, status, title=None, headline="A read.", category="economic"):
    return {"lens_id": lens_id, "lens_title": title or lens_id.title(),
            "category": category, "href": f"/dashboards/{lens_id}.html",
            "status": status, "headline": headline}


def transition(lens_id, from_status, to_status, title=None, headline="It moved."):
    return {"lens_id": lens_id, "lens_title": title or lens_id.title(),
            "category": "economic", "href": f"/dashboards/{lens_id}.html",
            "from_status": from_status, "to_status": to_status,
            "direction": "worsening" if from_status < to_status else "improving",
            "headline": headline}


def move(lens_id, final_step, title=None, stat_value="10.00%", delta="1.00%",
         why="Up three readings in a row."):
    return {"lens_id": lens_id, "lens_title": title or lens_id.title(),
            "category": "economic", "href": f"/dashboards/{lens_id}.html",
            "headline": f"{lens_id} is moving.", "accent": "#38BDF8",
            "sparkline": spark(final_step), "stat_label": "Headline stat",
            "stat_value": stat_value, "delta": delta, "dir": "up", "why": why}


def day(date, lenses=(), transitions=(), moves=(), status="watch",
        sentence="The economy is holding up.", short="Holding up.", watching=()):
    return {
        "generated_at": f"{date}T06:10:00Z",
        "transitions": list(transitions),
        "top_moves": list(moves),
        "lenses": list(lenses),
        "status_counts": {"ok": 20, "watch": 3, "elevated": 8, "alert": 2, "neutral": 0},
        "verdict": {"status": status, "shape": "contained-pressure",
                    "sentence": sentence, "short": short},
        "watching": list(watching),
        "pressure": [], "categories": [],
        "synthesis": {"cooccurrence": "", "relationships": []},
    }


BOARD = [lens("job-market", "ok"), lens("cost-of-living", "watch"),
         lens("fiscal-health", "elevated")]


class TestWindow(unittest.TestCase):
    def test_window_is_seven_days_ending_on_the_send_day(self):
        self.assertEqual(weekly_digest.window_dates("2026-07-31"),
                         ["2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28",
                          "2026-07-29", "2026-07-30", "2026-07-31"])

    def test_window_crosses_a_month_boundary(self):
        self.assertEqual(weekly_digest.window_dates("2026-03-02", span=3),
                         ["2026-02-28", "2026-03-01", "2026-03-02"])

    def test_build_ignores_days_outside_the_window(self):
        days = [day("2026-07-18", BOARD), day("2026-07-31", BOARD)]
        built = weekly_digest.build_weekly(days, end_iso="2026-07-31")
        # The Jul 18 brief is a week too old — its permalink must not appear.
        self.assertNotIn("brief/2026-07-18.html", built["html"])
        self.assertIn("brief/2026-07-31.html", built["html"])

    def test_days_are_sorted_even_when_supplied_out_of_order(self):
        days = [day("2026-07-31", BOARD, short="Friday read."),
                day("2026-07-27", BOARD, short="Monday read.")]
        built = weekly_digest.build_weekly(days, end_iso="2026-07-31")
        # The verdict is the LATEST day's, whatever order the files arrived in.
        self.assertIn("Friday read.", built["html"])


class TestWeekLabel(unittest.TestCase):
    def test_same_month_collapses_to_one_month_name(self):
        self.assertEqual(weekly_digest.week_label("2026-07-25", "2026-07-31"),
                         "Jul 25–31, 2026")

    def test_across_months_names_both(self):
        self.assertEqual(weekly_digest.week_label("2026-06-28", "2026-07-04"),
                         "Jun 28 – Jul 4, 2026")

    def test_across_years_names_both_years(self):
        self.assertEqual(weekly_digest.week_label("2026-12-28", "2027-01-03"),
                         "Dec 28, 2026 – Jan 3, 2027")


class TestSubjectToken(unittest.TestCase):
    def test_token_is_weekly_specific(self):
        self.assertEqual(weekly_digest.subject_token("2026-07-31"),
                         "The Week in Review, Jul 31, 2026")

    def test_every_subject_variant_ends_with_the_token(self):
        token = weekly_digest.subject_token("2026-07-31")
        quiet = weekly_digest.build_weekly([day("2026-07-31", BOARD)], end_iso="2026-07-31")
        moved = weekly_digest.build_weekly(
            [day("2026-07-27", BOARD),
             day("2026-07-31", [lens("job-market", "watch")] + BOARD[1:],
                 transitions=[transition("job-market", "ok", "watch")])],
            end_iso="2026-07-31")
        self.assertTrue(quiet["subject"].endswith(token), quiet["subject"])
        self.assertTrue(moved["subject"].endswith(token), moved["subject"])


class TestNetTransitions(unittest.TestCase):
    def test_flip_flop_cancels(self):
        """ok -> watch -> ok across the week is noise, not a weekly headline."""
        days = [
            day("2026-07-27", BOARD),
            day("2026-07-28", [lens("job-market", "watch")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "watch")]),
            day("2026-07-31", BOARD,
                transitions=[transition("job-market", "watch", "ok")]),
        ]
        self.assertEqual(weekly_digest.net_transitions(days), [])

    def test_sustained_change_survives_with_the_latest_headline(self):
        days = [
            day("2026-07-27", BOARD),
            day("2026-07-31", [lens("job-market", "elevated", headline="Layoffs are rising.")]
                + BOARD[1:],
                transitions=[transition("job-market", "ok", "elevated")]),
        ]
        nets = weekly_digest.net_transitions(days)
        self.assertEqual(len(nets), 1)
        self.assertEqual(nets[0]["lens_id"], "job-market")
        self.assertEqual(nets[0]["from_status"], "ok")
        self.assertEqual(nets[0]["to_status"], "elevated")
        self.assertEqual(nets[0]["headline"], "Layoffs are rising.")

    def test_change_landing_on_the_first_in_window_day_is_not_lost(self):
        """The first available snapshot may itself be the day the status moved
        (Sat/Sun quiet, Monday publishes the change). Reverting that day's own
        transitions recovers the true start-of-week board."""
        days = [
            day("2026-07-27", [lens("job-market", "alert")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "alert")]),
            day("2026-07-31", [lens("job-market", "alert")] + BOARD[1:]),
        ]
        nets = weekly_digest.net_transitions(days)
        self.assertEqual([(n["from_status"], n["to_status"]) for n in nets],
                         [("ok", "alert")])

    def test_net_move_reported_end_to_end_not_step_by_step(self):
        """ok -> watch -> elevated is one ok -> elevated row, not two."""
        days = [
            day("2026-07-27", BOARD),
            day("2026-07-29", [lens("job-market", "watch")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "watch")]),
            day("2026-07-31", [lens("job-market", "elevated")] + BOARD[1:],
                transitions=[transition("job-market", "watch", "elevated")]),
        ]
        nets = weekly_digest.net_transitions(days)
        self.assertEqual([(n["from_status"], n["to_status"]) for n in nets],
                         [("ok", "elevated")])

    def test_worsening_ranks_above_improving(self):
        start = [lens("job-market", "ok"), lens("fiscal-health", "alert")]
        end = [lens("job-market", "elevated"), lens("fiscal-health", "watch")]
        days = [day("2026-07-27", start), day("2026-07-31", end)]
        self.assertEqual([n["lens_id"] for n in weekly_digest.net_transitions(days)],
                         ["job-market", "fiscal-health"])

    def test_single_day_week_reports_that_day_s_own_transitions(self):
        days = [day("2026-07-31", [lens("job-market", "watch")] + BOARD[1:],
                    transitions=[transition("job-market", "ok", "watch")])]
        self.assertEqual([(n["from_status"], n["to_status"])
                          for n in weekly_digest.net_transitions(days)],
                         [("ok", "watch")])

    def test_a_flip_that_starts_on_the_first_in_window_day_reports_nothing(self):
        """Regression guard for a phantom 'improvement': the week opens with the
        change already applied, then it reverts. Without the baseline reversion
        this reads as watch -> ok, an improvement that never happened."""
        days = [
            day("2026-07-27", [lens("job-market", "watch")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "watch")]),
            day("2026-07-31", BOARD,
                transitions=[transition("job-market", "watch", "ok")]),
        ]
        self.assertEqual(weekly_digest.net_transitions(days), [])

    def test_a_lens_added_mid_week_is_not_a_transition(self):
        """A lens absent from the start-of-week board has no 'from' status."""
        days = [day("2026-07-27", BOARD),
                day("2026-07-31", BOARD + [lens("new-lens", "alert")])]
        self.assertEqual(weekly_digest.net_transitions(days), [])


class TestWeekMoves(unittest.TestCase):
    def test_a_lens_moving_on_two_days_appears_once(self):
        days = [day("2026-07-27", BOARD, moves=[move("cost-of-living", 2.0)]),
                day("2026-07-31", BOARD, moves=[move("cost-of-living", 4.0)])]
        moves = weekly_digest.week_moves(days)
        self.assertEqual([m["lens_id"] for m in moves], ["cost-of-living"])

    def test_dedup_keeps_the_most_significant_occurrence(self):
        days = [day("2026-07-27", BOARD, moves=[move("cost-of-living", 4.0,
                                                     stat_value="BIG")]),
                day("2026-07-31", BOARD, moves=[move("cost-of-living", 2.0,
                                                     stat_value="small")])]
        moves = weekly_digest.week_moves(days)
        self.assertEqual(moves[0]["stat_value"], "BIG")
        self.assertEqual(moves[0]["date"], "2026-07-27")

    def test_moves_are_ranked_by_significance_across_the_week(self):
        days = [day("2026-07-27", BOARD, moves=[move("a", 1.0), move("b", 5.0)]),
                day("2026-07-31", BOARD, moves=[move("c", 3.0)])]
        self.assertEqual([m["lens_id"] for m in weekly_digest.week_moves(days)],
                         ["b", "c", "a"])

    def test_moves_are_capped(self):
        days = [day("2026-07-31", BOARD,
                    moves=[move(f"lens-{i}", float(i + 1)) for i in range(9)])]
        self.assertEqual(len(weekly_digest.week_moves(days)), weekly_digest.MOVES_CAP)

    def test_each_move_carries_the_day_it_happened(self):
        days = [day("2026-07-29", BOARD, moves=[move("cost-of-living", 3.0)])]
        self.assertEqual(weekly_digest.week_moves(days)[0]["date"], "2026-07-29")

    def test_a_lens_that_also_changed_status_is_not_repeated_as_a_mover(self):
        """The status change is the stronger story; don't say it twice."""
        days = [
            day("2026-07-27", BOARD),
            day("2026-07-31", [lens("job-market", "watch")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "watch")],
                moves=[move("job-market", 5.0), move("cost-of-living", 1.0)]),
        ]
        built = weekly_digest.build_weekly(days, end_iso="2026-07-31")
        self.assertEqual(built["html"].count("job-market.html"), 1)


class TestWeekByDay(unittest.TestCase):
    """A week that holds steady must not pad the email with seven identical
    lines — consecutive days sharing a read collapse into one dated stretch."""

    def rows(self, *days):
        return weekly_digest._week_rows(list(days))

    def test_identical_consecutive_reads_collapse_to_one_row(self):
        html = self.rows(day("2026-07-27", BOARD, short="Steady."),
                         day("2026-07-28", BOARD, short="Steady."),
                         day("2026-07-29", BOARD, short="Steady."))
        self.assertEqual(html.count("Steady."), 1)
        self.assertIn("Mon, Jul 27 – Wed, Jul 29", html)

    def test_a_changed_read_starts_a_new_row(self):
        html = self.rows(day("2026-07-27", BOARD, short="Steady."),
                         day("2026-07-28", BOARD, short="Softening."))
        self.assertIn("Steady.", html)
        self.assertIn("Softening.", html)
        self.assertIn("Monday, Jul 27", html)
        self.assertIn("Tuesday, Jul 28", html)

    def test_a_stretch_links_to_the_day_the_read_began(self):
        html = self.rows(day("2026-07-27", BOARD, short="Steady."),
                         day("2026-07-29", BOARD, short="Steady."))
        self.assertIn("/dashboards/brief/2026-07-27.html", html)
        self.assertNotIn("/dashboards/brief/2026-07-29.html", html)

    def test_a_read_that_returns_later_is_its_own_row(self):
        html = self.rows(day("2026-07-27", BOARD, short="Steady."),
                         day("2026-07-28", BOARD, short="Softening."),
                         day("2026-07-29", BOARD, short="Steady."))
        self.assertEqual(html.count("Steady."), 2)

    def test_a_status_change_alone_splits_the_stretch(self):
        html = self.rows(day("2026-07-27", BOARD, short="Steady.", status="watch"),
                         day("2026-07-28", BOARD, short="Steady.", status="elevated"))
        self.assertEqual(html.count("Steady."), 2)


class TestBuildWeekly(unittest.TestCase):
    def setUp(self):
        self.days = [
            day("2026-07-27", BOARD, short="Monday read.",
                moves=[move("cost-of-living", 3.0)]),
            day("2026-07-29", [lens("job-market", "watch")] + BOARD[1:],
                transitions=[transition("job-market", "ok", "watch",
                                        headline="Hiring has slowed.")],
                short="Wednesday read.", moves=[move("fiscal-health", 2.0)]),
            day("2026-07-31", [lens("job-market", "watch")] + BOARD[1:],
                sentence="The economy is holding up, but hiring has slowed.",
                short="Friday read.",
                watching=[{"key": "k", "title": "Unemployment Rate",
                           "lens_title": "Job Market", "point_fmt": "4.40%",
                           "change": True, "current_status": "ok",
                           "implied_status": "watch", "href": "/dashboards/job-market.html"}]),
        ]
        self.built = weekly_digest.build_weekly(self.days, end_iso="2026-07-31")

    def test_quiet_week_sends_nothing(self):
        self.assertIsNone(weekly_digest.build_weekly([], end_iso="2026-07-31"))
        self.assertIsNone(weekly_digest.build_weekly(
            [day("2026-07-01", BOARD)], end_iso="2026-07-31"))

    def test_subject_leads_with_the_net_status_change(self):
        self.assertEqual(
            self.built["subject"],
            "Job-Market tips to WATCH — The Week in Review, Jul 31, 2026")

    def test_subject_counts_extra_changes(self):
        days = [day("2026-07-27", [lens("job-market", "ok"), lens("fiscal-health", "ok")]),
                day("2026-07-31", [lens("job-market", "watch"), lens("fiscal-health", "alert")])]
        self.assertIn("(+1 more)", weekly_digest.build_weekly(days, end_iso="2026-07-31")["subject"])

    def test_subject_falls_back_to_counts_when_nothing_changed(self):
        quiet = weekly_digest.build_weekly([day("2026-07-31", BOARD)], end_iso="2026-07-31")
        self.assertEqual(
            quiet["subject"],
            "2 alert · 8 elevated · 3 on watch — The Week in Review, Jul 31, 2026")

    def test_improving_change_reads_as_improvement(self):
        days = [day("2026-07-27", [lens("fiscal-health", "alert")]),
                day("2026-07-31", [lens("fiscal-health", "watch")])]
        self.assertIn("improves to WATCH",
                      weekly_digest.build_weekly(days, end_iso="2026-07-31")["subject"])

    def test_header_names_the_week_not_the_day(self):
        self.assertIn("The Week in Review", self.built["html"])
        self.assertIn("Jul 25–31, 2026", self.built["html"])

    def test_verdict_is_the_latest_day_s(self):
        self.assertIn("The economy is holding up, but hiring has slowed.", self.built["html"])

    def test_sections_present(self):
        for label in ("What changed this week", "Biggest moves this week",
                      "The week, day by day", "What we&rsquo;re watching next"):
            self.assertIn(label, self.built["html"])

    def test_movers_are_date_stamped(self):
        """A Monday reading in a Friday email must not read as current, so the
        stamp has to be inside the movers section itself."""
        html = self.built["html"]
        movers = html[html.index("Biggest moves this week"):html.index("The week, day by day")]
        self.assertIn("Jul 27", movers)   # cost-of-living moved Monday
        self.assertIn("Jul 29", movers)   # fiscal-health moved Wednesday

    def test_day_by_day_links_every_publication_day(self):
        for d in ("2026-07-27", "2026-07-29", "2026-07-31"):
            self.assertIn(f"https://baileyanalytics.com/dashboards/brief/{d}.html",
                          self.built["html"])
        for short in ("Monday read.", "Wednesday read.", "Friday read."):
            self.assertIn(short, self.built["html"])

    def test_watching_block_renders_from_the_latest_day(self):
        self.assertIn("Unemployment Rate", self.built["html"])
        self.assertIn("would tip", self.built["html"])

    def test_links_are_absolute(self):
        self.assertNotIn('href="/dashboards', self.built["html"])

    def test_archive_link_present(self):
        self.assertIn("https://baileyanalytics.com/dashboards/brief/", self.built["html"])

    def test_unsubscribe_variable_present(self):
        self.assertIn("{{ unsubscribe_url }}", self.built["html"])

    def test_pressure_count_line(self):
        self.assertIn("13 readings warrant attention", self.built["html"])  # 3+8+2

    def test_mover_why_rides_along(self):
        self.assertIn("Up three readings in a row.", self.built["html"])

    def test_content_is_escaped(self):
        days = [day("2026-07-31", [lens("x", "ok", title="Risk & <Reward>")],
                    sentence="Bonds & <equities> diverged.")]
        html = weekly_digest.build_weekly(days, end_iso="2026-07-31")["html"]
        self.assertIn("Bonds &amp; &lt;equities&gt; diverged.", html)
        self.assertNotIn("<Reward>", html)

    def test_no_movers_or_changes_still_renders_a_body(self):
        html = weekly_digest.build_weekly([day("2026-07-31", BOARD)],
                                          end_iso="2026-07-31")["html"]
        self.assertIn("No status changes", html)


if __name__ == "__main__":
    unittest.main()

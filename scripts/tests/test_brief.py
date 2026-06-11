import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief


class TestMoveScore(unittest.TestCase):
    def test_score_is_latest_step_over_prior_volatility(self):
        # steps = [2, -1, 8]; prior steps [2, -1] -> pstdev 1.5; latest 8 -> 8/1.5
        self.assertAlmostEqual(brief.move_score([1.0, 3.0, 2.0, 10.0]), 8.0 / 1.5)

    def test_larger_final_step_scores_higher(self):
        small = brief.move_score([1.0, 3.0, 2.0, 4.0])
        big = brief.move_score([1.0, 3.0, 2.0, 10.0])
        self.assertGreater(big, small)

    def test_too_few_points_is_none(self):
        self.assertIsNone(brief.move_score([1.0, 2.0, 3.0]))
        self.assertIsNone(brief.move_score([1.0, 2.0]))
        self.assertIsNone(brief.move_score([]))
        self.assertIsNone(brief.move_score(None))

    def test_no_move_is_none(self):
        self.assertIsNone(brief.move_score([1.0, 2.0, 3.0, 3.0]))  # latest step is 0

    def test_flat_prior_then_move_is_inf(self):
        self.assertEqual(brief.move_score([5.0, 5.0, 5.0, 9.0]), float("inf"))


class TestLensHref(unittest.TestCase):
    def test_economic_is_flat_dashboards(self):
        self.assertEqual(brief.lens_href("economic", "fiscal-health"),
                         "/dashboards/fiscal-health.html")

    def test_banking_strips_bank_prefix(self):
        self.assertEqual(brief.lens_href("banking", "bank-asset-quality"),
                         "/dashboards/banking/asset-quality.html")

    def test_markets_uses_slug_map(self):
        self.assertEqual(brief.lens_href("markets", "market-risk-sentiment"),
                         "/dashboards/markets/risk-sentiment.html")
        self.assertEqual(brief.lens_href("markets", "crypto-structure"),
                         "/dashboards/markets/crypto-structure.html")

    def test_energy_uses_slug_map(self):
        self.assertEqual(brief.lens_href("energy", "energy-oil-fuels"),
                         "/dashboards/energy/oil-fuels.html")

    def test_consumer_uses_slug_map(self):
        self.assertEqual(brief.lens_href("consumer", "consumer-credit"),
                         "/dashboards/consumer/credit-stress.html")

    def test_housing_uses_slug_map(self):
        self.assertEqual(brief.lens_href("housing", "housing-home-prices"),
                         "/dashboards/housing/home-prices.html")

    def test_global_uses_slug_map(self):
        self.assertEqual(brief.lens_href("global", "global-growth"),
                         "/dashboards/global/growth.html")
        self.assertEqual(brief.lens_href("global", "global-dollar-currencies"),
                         "/dashboards/global/dollar-currencies.html")
        self.assertEqual(brief.lens_href("global", "global-trade-supply"),
                         "/dashboards/global/trade-supply.html")
        self.assertEqual(brief.lens_href("global", "global-uncertainty"),
                         "/dashboards/global/uncertainty.html")

    def test_global_in_brief_categories(self):
        self.assertIn("global", brief.CATEGORIES)


def _indices():
    return {
        "economic": {"lenses": [
            {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
             "status": "elevated", "headline_read": "Debt is climbing.",
             "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "0.30%", "dir": "up"}],
             "sparkline": [120.0, 124.0]},
        ]},
        "markets": {"lenses": [
            {"id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#b",
             "status": "neutral", "headline_read": "Crypto is mixed.",
             "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "2.00%", "dir": "up"}],
             "sparkline": [50.0, 56.0]},
        ]},
    }


class TestFlatten(unittest.TestCase):
    def test_flattens_with_category_and_href(self):
        flat = brief._flatten_lenses(_indices())
        self.assertEqual(len(flat), 2)
        fiscal = next(r for r in flat if r["lens_id"] == "fiscal-health")
        self.assertEqual(fiscal["category"], "economic")
        self.assertEqual(fiscal["href"], "/dashboards/fiscal-health.html")
        self.assertEqual(fiscal["status"], "elevated")
        self.assertEqual(fiscal["headline"], "Debt is climbing.")
        self.assertEqual(fiscal["lens_title"], "Fiscal Health")

    def test_skips_missing_categories(self):
        flat = brief._flatten_lenses({"economic": None, "markets": {"lenses": []}})
        self.assertEqual(flat, [])

    def test_skips_lens_without_id(self):
        idx = {"economic": {"lenses": [{"title": "No ID"},
                                       {"id": "ok-lens", "title": "OK"}]}}
        flat = brief._flatten_lenses(idx)
        self.assertEqual([r["lens_id"] for r in flat], ["ok-lens"])

    def test_tolerates_missing_title(self):
        idx = {"economic": {"lenses": [{"id": "x"}]}}
        flat = brief._flatten_lenses(idx)
        self.assertEqual(flat[0]["lens_title"], "")


class TestDetectTransitions(unittest.TestCase):
    def _flat(self, *pairs):
        # pairs: (lens_id, status)
        return [{"lens_id": i, "lens_title": i.title(), "category": "economic",
                 "href": "/x", "status": s, "headline": f"{i} read.",
                 "key_stats": [], "sparkline": []} for i, s in pairs]

    def test_status_change_is_a_transition(self):
        prior = {"job-market": "watch"}
        flat = self._flat(("job-market", "elevated"))
        out = brief.detect_transitions(prior, flat)
        self.assertEqual(len(out), 1)
        t = out[0]
        self.assertEqual(t["from_status"], "watch")
        self.assertEqual(t["to_status"], "elevated")
        self.assertEqual(t["direction"], "worsening")
        self.assertEqual(t["lens_id"], "job-market")
        self.assertEqual(t["headline"], "job-market read.")

    def test_unchanged_status_is_not_a_transition(self):
        prior = {"job-market": "watch"}
        flat = self._flat(("job-market", "watch"))
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_first_run_no_prior_yields_no_transitions(self):
        flat = self._flat(("job-market", "elevated"))
        self.assertEqual(brief.detect_transitions({}, flat), [])

    def test_new_lens_not_in_prior_is_skipped(self):
        prior = {"job-market": "ok"}
        flat = self._flat(("brand-new", "alert"))
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_neutral_lens_excluded(self):
        prior = {"crypto-structure": "neutral"}
        flat = [{"lens_id": "crypto-structure", "lens_title": "Crypto", "category": "markets",
                 "href": "/x", "status": "ok", "headline": "h", "key_stats": [], "sparkline": []}]
        # 'neutral' is not in SEVERITY, so a neutral->ok change is not a transition
        self.assertEqual(brief.detect_transitions(prior, flat), [])

    def test_worsening_sorts_before_improving_and_by_jump(self):
        prior = {"a": "ok", "b": "watch", "c": "alert"}
        flat = self._flat(("a", "alert"), ("b", "ok"), ("c", "elevated"))
        out = brief.detect_transitions(prior, flat)
        # a: ok->alert (+3 worsening), c: alert->elevated (-1 improving),
        # b: watch->ok (-1 improving). Worsening first, then improving.
        self.assertEqual(out[0]["lens_id"], "a")
        self.assertEqual(out[0]["direction"], "worsening")
        self.assertTrue(all(t["direction"] == "improving" for t in out[1:]))


class TestRankMoves(unittest.TestCase):
    # All sparklines share the prior pattern [0,1,0,1] (prior-step volatility
    # pstdev([1,-1,1]) ≈ 0.9428); the 5th point sets the final step, hence the score.
    def _lens(self, lens_id, spark, d="1.00%", dir_="up", k="Stat", v="1.00%"):
        return {"lens_id": lens_id, "lens_title": lens_id.title(), "category": "economic",
                "href": "/x", "status": "ok", "headline": "h",
                "key_stats": [{"k": k, "v": v, "d": d, "dir": dir_}], "sparkline": spark}

    def test_ranks_by_significance_desc(self):
        flat = [self._lens("small", [0.0, 1.0, 0.0, 1.0, 2.5]),   # step +1.5 -> ~1.6σ
                self._lens("big", [0.0, 1.0, 0.0, 1.0, 10.0]),    # step +9   -> ~9.5σ
                self._lens("mid", [0.0, 1.0, 0.0, 1.0, -4.0])]    # step -5   -> ~5.3σ
        moves = brief.rank_moves(flat, transition_ids=set(), limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["big", "mid", "small"])

    def test_excludes_transition_lenses(self):
        flat = [self._lens("big", [0.0, 1.0, 0.0, 1.0, 10.0]),
                self._lens("mid", [0.0, 1.0, 0.0, 1.0, -4.0])]
        moves = brief.rank_moves(flat, transition_ids={"big"}, limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["mid"])

    def test_threshold_filters_small_moves(self):
        # step +0.5 -> ~0.53σ, below the 1.0σ floor
        flat = [self._lens("tiny", [0.0, 1.0, 0.0, 1.0, 1.5])]
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_limit_caps_results(self):
        flat = [self._lens(f"l{i}", [0.0, 1.0, 0.0, 1.0, 5.0 + i]) for i in range(6)]
        moves = brief.rank_moves(flat, set(), limit=3)
        self.assertEqual(len(moves), 3)

    def test_sparkline_too_short_is_skipped(self):
        flat = [self._lens("flat", [100.0])]
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_move_carries_display_fields_without_score(self):
        flat = [self._lens("big", [0.0, 1.0, 0.0, 1.0, 10.0], d="10.00%", dir_="up",
                            k="Debt-to-GDP", v="124.50%")]
        m = brief.rank_moves(flat, set(), limit=5)[0]
        self.assertEqual(m["stat_label"], "Debt-to-GDP")
        self.assertEqual(m["stat_value"], "124.50%")
        self.assertEqual(m["delta"], "10.00%")
        self.assertEqual(m["dir"], "up")
        self.assertEqual(m["href"], "/x")
        # the ranking score is internal — it must not leak into the output (it can be inf)
        self.assertNotIn("score", m)
        self.assertNotIn("pct_change", m)

    def test_neutral_lens_eligible_for_moves(self):
        crypto = self._lens("crypto-structure", [50.0, 51.0, 50.0, 51.0, 56.0])
        crypto["status"] = "neutral"
        moves = brief.rank_moves([crypto], set(), limit=5)
        self.assertEqual(len(moves), 1)


class TestBuildBrief(unittest.TestCase):
    def _indices(self):
        # sparklines share the [x,x+1,x,x+1] prior pattern; the final point is a
        # clear (>1σ) move so each lens qualifies as a mover when not a transition.
        return {
            "economic": {"lenses": [
                {"id": "job-market", "title": "Job Market", "accent": "#a",
                 "status": "elevated", "headline_read": "Hiring is slowing.",
                 "key_stats": [{"k": "Unemployment", "v": "4.50%", "d": "0.20%", "dir": "up"}],
                 "sparkline": [4.0, 4.2, 4.0, 4.2, 4.5]},
                {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
                 "status": "ok", "headline_read": "Finances steady.",
                 "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "0.30%", "dir": "up"}],
                 "sparkline": [100.0, 101.0, 100.0, 101.0, 112.0]},  # big final step
            ]},
            "markets": {"lenses": [
                {"id": "crypto-structure", "title": "Crypto", "accent": "#b",
                 "status": "neutral", "headline_read": "Crypto mixed.",
                 "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "2.00%", "dir": "up"}],
                 "sparkline": [50.0, 51.0, 50.0, 51.0, 56.0]},  # big final step
            ]},
        }

    def test_transition_detected_and_state_returned(self):
        prior = {"statuses": {"job-market": "watch", "fiscal-health": "ok",
                              "crypto-structure": "neutral"}}
        today, state = brief.build_brief(self._indices(), prior)
        self.assertEqual(len(today["transitions"]), 1)
        self.assertEqual(today["transitions"][0]["lens_id"], "job-market")
        self.assertEqual(today["transitions"][0]["to_status"], "elevated")
        # new state captures every current status
        self.assertEqual(state["statuses"]["job-market"], "elevated")
        self.assertEqual(state["statuses"]["crypto-structure"], "neutral")

    def test_moves_exclude_the_transition_lens(self):
        prior = {"statuses": {"job-market": "watch", "fiscal-health": "ok",
                              "crypto-structure": "neutral"}}
        today, _ = brief.build_brief(self._indices(), prior)
        ids = [m["lens_id"] for m in today["top_moves"]]
        self.assertNotIn("job-market", ids)    # it's the transition, excluded from moves
        self.assertIn("fiscal-health", ids)    # big final step
        self.assertIn("crypto-structure", ids) # neutral but eligible

    def test_status_counts_tally(self):
        today, _ = brief.build_brief(self._indices(), {"statuses": {}})
        self.assertEqual(today["status_counts"],
                         {"ok": 1, "watch": 0, "elevated": 1, "alert": 0, "neutral": 1})

    def test_first_run_empty_prior(self):
        today, state = brief.build_brief(self._indices(), {})
        self.assertEqual(today["transitions"], [])
        self.assertTrue(today["top_moves"])  # moves still populate
        self.assertIn("generated_at", today)
        self.assertEqual(state["statuses"]["job-market"], "elevated")

    def test_combined_headline_count_capped_at_five(self):
        # 6 transitions -> 0 move slots
        prior_statuses = {f"l{i}": "ok" for i in range(6)}
        idx = {"economic": {"lenses": [
            {"id": f"l{i}", "title": f"L{i}", "accent": "#a", "status": "alert",
             "headline_read": "h", "key_stats": [{"k": "x", "v": "1", "d": "1", "dir": "up"}],
             "sparkline": [1.0, 2.0, 3.0, 4.0]} for i in range(6)]}}
        today, _ = brief.build_brief(idx, {"statuses": prior_statuses})
        self.assertEqual(len(today["transitions"]), 6)
        self.assertEqual(today["top_moves"], [])


class TestBriefLensesList(unittest.TestCase):
    def test_today_includes_flat_lenses_list(self):
        idx = {"economic": {"lenses": [
            {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
             "status": "elevated", "headline_read": "h",
             "key_stats": [], "sparkline": []}]},
               "housing": {"lenses": [
            {"id": "housing-home-prices", "title": "Price Stability", "accent": "#b",
             "status": "ok", "headline_read": "h2",
             "key_stats": [], "sparkline": []}]}}
        today, _ = brief.build_brief(idx, {})
        self.assertEqual(len(today["lenses"]), 2)
        fiscal = next(l for l in today["lenses"] if l["lens_id"] == "fiscal-health")
        self.assertEqual(fiscal, {"lens_id": "fiscal-health", "lens_title": "Fiscal Health",
                                  "category": "economic", "href": "/dashboards/fiscal-health.html",
                                  "status": "elevated"})
        homes = next(l for l in today["lenses"] if l["lens_id"] == "housing-home-prices")
        self.assertEqual(homes["href"], "/dashboards/housing/home-prices.html")


if __name__ == "__main__":
    unittest.main()

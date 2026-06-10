import sys
import pathlib
import json
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief


class TestPctChange(unittest.TestCase):
    def test_normal_rise(self):
        self.assertAlmostEqual(brief.pct_change([100.0, 110.0]), 10.0)

    def test_normal_fall(self):
        self.assertAlmostEqual(brief.pct_change([200.0, 150.0]), -25.0)

    def test_uses_last_two_only(self):
        self.assertAlmostEqual(brief.pct_change([1.0, 2.0, 4.0, 5.0]), 25.0)

    def test_single_point_is_none(self):
        self.assertIsNone(brief.pct_change([5.0]))

    def test_empty_is_none(self):
        self.assertIsNone(brief.pct_change([]))

    def test_zero_prior_is_none(self):
        self.assertIsNone(brief.pct_change([0.0, 3.0]))

    def test_none_arg_is_none(self):
        self.assertIsNone(brief.pct_change(None))


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
    def _lens(self, lens_id, spark, d="1.00%", dir_="up", k="Stat", v="1.00%"):
        return {"lens_id": lens_id, "lens_title": lens_id.title(), "category": "economic",
                "href": "/x", "status": "ok", "headline": "h",
                "key_stats": [{"k": k, "v": v, "d": d, "dir": dir_}], "sparkline": spark}

    def test_ranks_by_abs_pct_change_desc(self):
        flat = [self._lens("small", [100.0, 101.0]),   # +1%
                self._lens("big", [100.0, 110.0]),     # +10%
                self._lens("mid", [100.0, 95.0])]      # -5%
        moves = brief.rank_moves(flat, transition_ids=set(), limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["big", "mid", "small"])

    def test_excludes_transition_lenses(self):
        flat = [self._lens("big", [100.0, 110.0]), self._lens("mid", [100.0, 95.0])]
        moves = brief.rank_moves(flat, transition_ids={"big"}, limit=5)
        self.assertEqual([m["lens_id"] for m in moves], ["mid"])

    def test_threshold_filters_small_moves(self):
        flat = [self._lens("tiny", [100.0, 100.3])]   # +0.3% < 0.5%
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_limit_caps_results(self):
        flat = [self._lens(f"l{i}", [100.0, 100.0 + i + 1]) for i in range(6)]
        moves = brief.rank_moves(flat, set(), limit=3)
        self.assertEqual(len(moves), 3)

    def test_sparkline_too_short_is_skipped(self):
        flat = [self._lens("flat", [100.0])]
        self.assertEqual(brief.rank_moves(flat, set(), limit=5), [])

    def test_move_carries_display_fields(self):
        flat = [self._lens("big", [100.0, 110.0], d="10.00%", dir_="up",
                            k="Debt-to-GDP", v="124.50%")]
        m = brief.rank_moves(flat, set(), limit=5)[0]
        self.assertEqual(m["stat_label"], "Debt-to-GDP")
        self.assertEqual(m["stat_value"], "124.50%")
        self.assertEqual(m["delta"], "10.00%")
        self.assertEqual(m["dir"], "up")
        self.assertAlmostEqual(m["pct_change"], 10.0)
        self.assertEqual(m["href"], "/x")

    def test_neutral_lens_eligible_for_moves(self):
        crypto = self._lens("crypto-structure", [50.0, 56.0])
        crypto["status"] = "neutral"
        moves = brief.rank_moves([crypto], set(), limit=5)
        self.assertEqual(len(moves), 1)


class TestBuildBrief(unittest.TestCase):
    def _indices(self):
        return {
            "economic": {"lenses": [
                {"id": "job-market", "title": "Job Market", "accent": "#a",
                 "status": "elevated", "headline_read": "Hiring is slowing.",
                 "key_stats": [{"k": "Unemployment", "v": "4.50%", "d": "0.20%", "dir": "up"}],
                 "sparkline": [4.0, 4.5]},
                {"id": "fiscal-health", "title": "Fiscal Health", "accent": "#a",
                 "status": "ok", "headline_read": "Finances steady.",
                 "key_stats": [{"k": "Debt-to-GDP", "v": "124.50%", "d": "0.30%", "dir": "up"}],
                 "sparkline": [100.0, 112.0]},  # +12% move
            ]},
            "markets": {"lenses": [
                {"id": "crypto-structure", "title": "Crypto", "accent": "#b",
                 "status": "neutral", "headline_read": "Crypto mixed.",
                 "key_stats": [{"k": "BTC dominance", "v": "56.00%", "d": "2.00%", "dir": "up"}],
                 "sparkline": [50.0, 56.0]},  # +12% move
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
        self.assertNotIn("job-market", ids)
        self.assertIn("fiscal-health", ids)   # +12% move
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
             "sparkline": [1.0, 2.0]} for i in range(6)]}}
        today, _ = brief.build_brief(idx, {"statuses": prior_statuses})
        self.assertEqual(len(today["transitions"]), 6)
        self.assertEqual(today["top_moves"], [])


if __name__ == "__main__":
    unittest.main()

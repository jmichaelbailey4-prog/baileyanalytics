"""Tests for the synthesis / 'why' layer (spec 2026-06-16-synthesis-why-layer).

Honesty is the gating constraint, so the four invariants of the spec §2 are
encoded here as tests:
  INV-1  per-mover whys carry no causal token (self-grounded, descriptive)
  INV-2  the co-occurrence sentence carries no causal token (a count, not a cause)
  INV-3  relationship language matches its edge's strength tier
  INV-4  determinism (same input -> same output)
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import synthesis


# --- signal helpers -------------------------------------------------------

class TestStreak(unittest.TestCase):
    def test_up_run(self):
        self.assertEqual(synthesis._streak([1, 2, 3, 4]), ("up", 3))

    def test_down_run(self):
        self.assertEqual(synthesis._streak([4, 3, 2, 1]), ("down", 3))

    def test_zigzag_has_no_streak(self):
        self.assertIsNone(synthesis._streak([1, 2, 1, 2, 1]))

    def test_too_short(self):
        self.assertIsNone(synthesis._streak([1, 2, 3]))  # only 2 steps < MIN_STREAK

    def test_breaks_on_reversal(self):
        # last three up, but the run is measured from the end
        self.assertEqual(synthesis._streak([9, 1, 2, 3, 4]), ("up", 3))


class TestFreshExtreme(unittest.TestCase):
    def test_fresh_high(self):
        self.assertEqual(synthesis._fresh_extreme([1, 2, 3, 5]), "high")

    def test_fresh_low(self):
        self.assertEqual(synthesis._fresh_extreme([5, 3, 2, 1]), "low")

    def test_interior_value_is_not_extreme(self):
        self.assertIsNone(synthesis._fresh_extreme([1, 5, 3, 4]))

    def test_flat_series_is_not_extreme(self):
        self.assertIsNone(synthesis._fresh_extreme([3, 3, 3, 3]))

    def test_tie_at_top_without_a_move_is_not_fresh(self):
        self.assertIsNone(synthesis._fresh_extreme([1, 2, 3, 3]))


class TestOutsized(unittest.TestCase):
    def test_flat_then_jump_is_outsized(self):
        self.assertTrue(synthesis._outsized([10, 10, 10, 10, 40]))

    def test_smooth_ramp_is_not_outsized(self):
        self.assertFalse(synthesis._outsized([1, 2, 3, 4, 5]))

    def test_big_step_against_noise_is_outsized(self):
        self.assertTrue(synthesis._outsized([5, 6, 5, 6, 5, 6, 15]))

    def test_small_noise_is_not_outsized(self):
        self.assertFalse(synthesis._outsized([5.0, 5.1, 4.9, 5.05, 4.95, 5.0, 5.1]))


# --- per-mover why (INV-1) ------------------------------------------------

def _mover(stat_label, sparkline):
    return {"lens_id": "x", "lens_title": "X", "category": "energy",
            "stat_label": stat_label, "sparkline": sparkline}


class TestMoverWhy(unittest.TestCase):
    def test_up_streak_to_fresh_high(self):
        why = synthesis.mover_why(_mover("Food", [10, 11, 12.5, 30.2]))
        self.assertTrue(why.startswith("Food: "))
        self.assertIn("in a row", why)
        self.assertIn("fresh high", why)

    def test_down_streak_to_fresh_low(self):
        why = synthesis.mover_why(_mover("Saving rate", [4.3, 3.6, 3.2, 2.6]))
        self.assertIn("down 3 readings in a row", why)
        self.assertIn("lowest", why)

    def test_no_signal_returns_empty(self):
        # interior value, no streak, no outsized step -> honest silence
        self.assertEqual(synthesis.mover_why(_mover("Dollar", [1, 5, 3, 4])), "")

    def test_too_short_series_returns_empty(self):
        self.assertEqual(synthesis.mover_why(_mover("X", [1, 2])), "")

    def test_outsized_only_describes_the_jump(self):
        why = synthesis.mover_why(_mover("S&P 500", [10, 10, 10, 10, 40]))
        self.assertIn("sharpest", why)

    def test_no_label_capitalizes(self):
        why = synthesis.mover_why(_mover("", [1, 2, 3, 4]))
        self.assertTrue(why[0].isupper())
        self.assertNotIn(":", why)

    def test_inv1_no_causal_token_in_any_why(self):
        samples = [
            [10, 11, 12.5, 30.2], [4.3, 3.6, 3.2, 2.6], [10, 10, 10, 10, 40],
            [1, 2, 3, 4, 5, 6, 7], [7, 6, 5, 4, 3, 2, 1],
        ]
        for s in samples:
            why = synthesis.mover_why(_mover("Series", s))
            self.assertEqual(synthesis.find_causal_tokens(why), [],
                             f"causal token leaked into a per-mover why: {why!r}")

    def test_inv4_deterministic(self):
        m = _mover("Food", [10, 11, 12.5, 30.2])
        self.assertEqual(synthesis.mover_why(m), synthesis.mover_why(m))


# --- structural co-occurrence (INV-2) -------------------------------------

def _p(lens_id, status):
    return {"lens_id": lens_id, "lens_title": lens_id, "status": status,
            "category": "x", "href": "/", "headline": "h"}


class TestCooccurrence(unittest.TestCase):
    def test_price_cluster_is_named_with_a_count(self):
        rows = [_p("energy-oil-fuels", "alert"), _p("energy-commodities", "alert"),
                _p("energy-electricity", "elevated"), _p("cost-of-living", "elevated"),
                _p("consumer-credit", "watch")]
        s = synthesis.cooccurrence(rows)
        self.assertIn("Four", s)                 # the honest count, spelled out
        self.assertIn("cost of living", s)       # the shared subject
        self.assertIn("fuel", s)                 # a named member

    def test_below_threshold_is_silent(self):
        rows = [_p("energy-oil-fuels", "alert"), _p("housing-affordability", "elevated")]
        self.assertEqual(synthesis.cooccurrence(rows), "")

    def test_empty_is_silent(self):
        self.assertEqual(synthesis.cooccurrence([]), "")

    def test_inv2_no_causal_token(self):
        rows = [_p("energy-oil-fuels", "alert"), _p("energy-commodities", "alert"),
                _p("energy-electricity", "elevated"), _p("cost-of-living", "elevated")]
        s = synthesis.cooccurrence(rows)
        self.assertEqual(synthesis.find_causal_tokens(s), [])

    def test_picks_largest_cluster(self):
        rows = [_p("energy-oil-fuels", "alert"), _p("energy-commodities", "alert"),
                _p("energy-electricity", "elevated"),  # prices = 3
                _p("housing-affordability", "elevated"), _p("housing-supply-construction", "elevated")]  # housing = 2
        s = synthesis.cooccurrence(rows)
        self.assertIn("cost of living", s)
        self.assertNotIn("housing market", s)

    def test_inv4_deterministic(self):
        rows = [_p("energy-oil-fuels", "alert"), _p("energy-commodities", "alert"),
                _p("cost-of-living", "elevated")]
        self.assertEqual(synthesis.cooccurrence(rows), synthesis.cooccurrence(rows))


# --- honesty primitives ---------------------------------------------------

class TestHonestyPrimitives(unittest.TestCase):
    def test_finds_causal_tokens(self):
        self.assertTrue(synthesis.find_causal_tokens("energy is driving sentiment down"))
        self.assertTrue(synthesis.find_causal_tokens("sentiment fell because of prices"))
        self.assertTrue(synthesis.find_causal_tokens("the drop is due to inflation"))

    def test_clean_text_has_no_causal_tokens(self):
        self.assertEqual(synthesis.find_causal_tokens("Food: up 4 readings in a row."), [])

    def test_finds_hedge_tokens(self):
        self.assertTrue(synthesis.find_hedge_tokens("rates near 7% have historically cooled demand"))
        self.assertTrue(synthesis.find_hedge_tokens("higher rates tend to slow sales"))

    def test_no_hedge_in_bare_text(self):
        self.assertEqual(synthesis.find_hedge_tokens("fuel and food costs are up"), [])


# --- relationship engine (INV-3) ------------------------------------------

DEFINITIONAL = {"source": "cost-of-living", "target": "consumer-income-savings",
                "strength": "definitional",
                "link": "Real income is pay after inflation, so a hotter cost of living lowers it by definition.",
                "note": "identity"}
EMPIRICAL = {"source": "housing-affordability", "target": "housing-home-prices",
             "strength": "empirical",
             "link": "Mortgage rates near 7% have historically cooled buyer demand.",
             "note": "well-established but not deterministic"}
COOCCURRENCE = {"source": "energy-commodities", "target": "consumer-income-savings",
                "strength": "co-occurrence",
                "link": "Food costs jumped at the same time as the saving rate hit a new low.",
                "note": "two facts, no mechanism claimed"}


class TestRelationshipSentence(unittest.TestCase):
    def test_definitional_may_state_causation(self):
        self.assertTrue(synthesis.relationship_sentence(DEFINITIONAL))

    def test_empirical_with_hedge_renders(self):
        self.assertIn("historically", synthesis.relationship_sentence(EMPIRICAL))

    def test_empirical_without_hedge_is_rejected(self):
        bad = dict(EMPIRICAL, link="Higher rates cool buyer demand.")  # bare causation, no hedge
        with self.assertRaises(ValueError):
            synthesis.relationship_sentence(bad)

    def test_cooccurrence_with_causal_verb_is_rejected(self):
        bad = dict(COOCCURRENCE, link="Food costs are driving the saving rate down.")
        with self.assertRaises(ValueError):
            synthesis.relationship_sentence(bad)

    def test_cooccurrence_clean_renders(self):
        self.assertIn("same time", synthesis.relationship_sentence(COOCCURRENCE))


class TestComposeRelationships(unittest.TestCase):
    EDGES = [DEFINITIONAL, EMPIRICAL, COOCCURRENCE]

    def test_only_active_edges_compose(self):
        active = {"cost-of-living", "consumer-income-savings"}  # only the definitional edge
        out = synthesis.compose_relationships(self.EDGES, active, cap=5)
        self.assertEqual(len(out), 1)
        self.assertIn("Real income", out[0])

    def test_no_active_edges_is_silent(self):
        self.assertEqual(synthesis.compose_relationships(self.EDGES, set(), cap=5), [])

    def test_respects_cap(self):
        active = {e["source"] for e in self.EDGES} | {e["target"] for e in self.EDGES}
        out = synthesis.compose_relationships(self.EDGES, active, cap=1)
        self.assertEqual(len(out), 1)

    def test_active_keys_from_today(self):
        today = {"pressure": [{"lens_id": "cost-of-living"}],
                 "top_moves": [{"lens_id": "energy-commodities"}],
                 "transitions": [{"lens_id": "energy-electricity"}]}
        keys = synthesis.active_keys(today)
        self.assertEqual(keys, {"cost-of-living", "energy-commodities", "energy-electricity"})


class TestRelationshipMapIntegrity(unittest.TestCase):
    """Every authored edge in relationships.py must be structurally valid and
    honest-by-tier — a malformed or dishonest edge fails CI (spec §4 Q6)."""

    def test_every_edge_is_valid_and_honest(self):
        from lenses import relationships
        valid_lens_ids = synthesis._valid_lens_ids()
        for e in relationships.RELATIONSHIPS:
            for field in ("source", "target", "strength", "link", "note"):
                self.assertTrue(e.get(field), f"edge missing {field}: {e}")
            self.assertIn(e["strength"],
                          ("definitional", "empirical", "co-occurrence"), e)
            self.assertIn(e["source"], valid_lens_ids, f"unknown source: {e['source']}")
            self.assertIn(e["target"], valid_lens_ids, f"unknown target: {e['target']}")
            # honesty: rendering enforces the tier<->grammar invariant (raises if violated)
            self.assertTrue(synthesis.relationship_sentence(e))


if __name__ == "__main__":
    unittest.main()

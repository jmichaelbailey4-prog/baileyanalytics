import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import state  # noqa: E402


class TestJoin(unittest.TestCase):
    def test_join(self):
        self.assertEqual(state._join([]), "")
        self.assertEqual(state._join(["a"]), "a")
        self.assertEqual(state._join(["a", "b"]), "a and b")
        self.assertEqual(state._join(["a", "b", "c"]), "a, b, and c")


class TestClassifyShape(unittest.TestCase):
    def test_partition(self):
        self.assertEqual(state.classify_shape("alert", True), "broad-stress")
        self.assertEqual(state.classify_shape("elevated", True), "spreading-stress")
        self.assertEqual(state.classify_shape("elevated", False), "spreading-stress")
        self.assertEqual(state.classify_shape("watch", True), "contained-pressure")
        self.assertEqual(state.classify_shape("watch", False), "mixed-watch")
        self.assertEqual(state.classify_shape("ok", False), "all-clear")


class TestCopyBank(unittest.TestCase):
    CATEGORIES = ["economic", "consumer", "banking", "business",
                  "markets", "energy", "housing", "global"]

    def test_every_category_has_copy(self):
        for cid in self.CATEGORIES:
            self.assertIn(cid, state.NOUN)
            self.assertIn(cid, state.STEADY_CLAUSES)
            self.assertIn(cid, state.ANCHOR_PRIORITY)
            self.assertEqual(set(state.PRESSURE_CLAUSES[cid]), {"elevated", "alert"})

    def test_fragments_splice_cleanly(self):
        # Fragments are clauses: lowercase start, no terminal punctuation.
        frags = (list(state.NOUN.values()) + list(state.STEADY_CLAUSES.values())
                 + [c for d in state.PRESSURE_CLAUSES.values() for c in d.values()])
        for f in frags:
            self.assertFalse(f[0].isupper(), f)
            self.assertNotIn(f[-1], ".;,", f)

    def test_every_shape_has_three_variants(self):
        for shape in ("all-clear", "mixed-watch", "contained-pressure",
                      "spreading-stress", "broad-stress"):
            self.assertEqual(len(state.SKELETONS[shape]), 3)


class TestVariant(unittest.TestCase):
    def test_deterministic_and_in_range(self):
        for shape in state.SKELETONS:
            v = state._variant("2026-06-11", shape)
            self.assertEqual(v, state._variant("2026-06-11", shape))
            self.assertIn(v, (0, 1, 2))

    def test_varies_across_dates(self):
        dates = [f"2026-06-{d:02d}" for d in range(1, 31)]
        variants = {state._variant(d, "all-clear") for d in dates}
        self.assertGreater(len(variants), 1)


class TestSentence(unittest.TestCase):
    P2 = ["energy and commodity costs are squeezing budgets",
          "household finances are stretched thin"]
    A = "banks are solid and markets are calm"

    def test_contained_with_anchor_every_variant(self):
        for v in range(3):
            s = state._sentence("contained-pressure", v, self.P2, self.A, [])
            self.assertIn(self.P2[0], s)
            self.assertIn(self.P2[1], s)
            self.assertIn(self.A, s)
            self.assertTrue(s[0].isupper())
            self.assertTrue(s.endswith("."))
            self.assertNotIn("..", s)

    def test_contained_without_anchor_falls_back(self):
        s = state._sentence("contained-pressure", 0, self.P2, "", [])
        self.assertIn("the rest bears watching", s)
        self.assertNotIn("{", s)

    def test_pressure_order_is_preserved(self):
        s = state._sentence("contained-pressure", 0, self.P2, self.A, [])
        self.assertLess(s.index(self.P2[0]), s.index(self.P2[1]))

    def test_broad_stress_uses_three_clauses(self):
        p3 = self.P2 + ["cracks are showing in the banking system"]
        s = state._sentence("broad-stress", 0, p3, "", [])
        for clause in p3:
            self.assertIn(clause, s)

    def test_all_clear_number_agreement(self):
        one = state._sentence("all-clear", 1, [], self.A, ["business health"])
        self.assertIn("the only thing worth watching is business health", one)
        two = state._sentence("all-clear", 1, [], self.A,
                              ["business health", "housing"])
        self.assertIn("the only things worth watching are business health and housing",
                      two)

    def test_all_clear_no_watch_ending(self):
        s = state._sentence("all-clear", 0, [], self.A, [])
        self.assertIn("nothing on the board is flashing", s)

    def test_mixed_watch_with_and_without_anchor(self):
        w = ["the core economy", "household finances", "housing"]
        with_a = state._sentence("mixed-watch", 0, [], self.A, w)
        self.assertIn("the core economy, household finances, and housing", with_a)
        self.assertIn(self.A, with_a)
        no_a = state._sentence("mixed-watch", 0, [], "", w)
        self.assertIn("bear watching", no_a)
        self.assertNotIn("{", no_a)

    def test_spreading_no_ok_fallback(self):
        s = state._sentence("spreading-stress", 0, self.P2, "", [])
        self.assertIn("little of the board reads steady", s)


if __name__ == "__main__":
    unittest.main()

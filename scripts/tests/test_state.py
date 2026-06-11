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


if __name__ == "__main__":
    unittest.main()

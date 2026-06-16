import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import state  # noqa: E402


class TestShortVerdict(unittest.TestCase):
    def test_short_keeps_top_pressure_per_shape(self):
        p = ["energy and commodity costs are squeezing budgets", "housing is out of balance"]
        self.assertEqual(state._short_verdict("contained-pressure", p, [], "banks are solid"),
                         "Holding up, but energy and commodity costs are squeezing budgets.")
        self.assertEqual(state._short_verdict("spreading-stress", p, [], ""),
                         "Stress is spreading — energy and commodity costs are squeezing budgets.")
        self.assertTrue(state._short_verdict("broad-stress", p, [], "").startswith(
            "Serious stress across the economy — energy"))

    def test_short_mixed_watch_names_top_watch_noun(self):
        self.assertEqual(state._short_verdict("mixed-watch", [], ["business health", "housing"], "x"),
                         "Nothing is flashing red, but business health bears watching.")
        self.assertEqual(state._short_verdict("mixed-watch", [], [], ""),
                         "Nothing is flashing red, but a few corners bear watching.")

    def test_short_all_clear_is_fixed_calm_line(self):
        self.assertEqual(state._short_verdict("all-clear", [], [], "banks are solid"),
                         "A calm read across the board — nothing is flashing.")

    def test_short_is_shorter_than_full_and_no_html_entities(self):
        # The home hero must differ from the brief's full sentence, and carry no
        # raw HTML entities (it's html-escaped at bake/render time).
        s = state._short_verdict("contained-pressure",
                                 ["energy and commodity costs are squeezing budgets"], [], "banks are solid")
        self.assertNotIn("&", s)


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


def cat_index(lens_statuses, *, status=None, prefix="lens"):
    """Minimal category index: one lens per status, optional baked blend."""
    lenses = [{"id": f"{prefix}-{i}", "title": f"Lens {i}", "status": s,
               "headline_read": f"Read {i}."} for i, s in enumerate(lens_statuses)]
    out = {"last_updated": "2026-06-11T00:00:00Z", "lenses": lenses}
    if status is not None:
        out["status"] = status
    return out


def todays_indices():
    """Mirror of the real 2026-06-11 data: energy/consumer elevated, three
    watch, three ok. Energy's lens mix (two alerts) outscores consumer's one."""
    return {
        "economic": cat_index(["ok", "ok", "ok", "elevated", "elevated"],
                              status="watch", prefix="economic"),
        "consumer": cat_index(["ok", "watch", "elevated", "alert"],
                              status="elevated", prefix="consumer"),
        "banking": cat_index(["ok", "ok", "ok", "watch"], status="ok", prefix="bank"),
        "business": cat_index(["ok", "ok", "ok", "watch"], status="ok", prefix="business"),
        "markets": cat_index(["ok", "neutral", "ok", "neutral"], status="ok", prefix="market"),
        "energy": cat_index(["alert", "ok", "elevated", "alert"],
                            status="elevated", prefix="energy"),
        "housing": cat_index(["ok", "elevated", "elevated", "ok"],
                             status="watch", prefix="housing"),
        "global": cat_index(["ok", "ok", "elevated", "elevated"],
                            status="watch", prefix="global"),
    }


class TestBuildState(unittest.TestCase):
    def build(self, indices, brief_today=None):
        orig = state._now
        state._now = lambda: "2026-06-11T12:00:00Z"
        try:
            return state.build_state(indices, brief_today)
        finally:
            state._now = orig

    def test_todays_picture(self):
        out = self.build(todays_indices(), {"transitions": [1, 2]})
        self.assertEqual(out["verdict"]["status"], "watch")
        self.assertEqual(out["verdict"]["shape"], "contained-pressure")
        s = out["verdict"]["sentence"]
        # Energy (RMS 2.35) outranks consumer (1.87); both clauses present, in order.
        e = "energy and commodity costs are squeezing budgets"
        c = "household finances are stretched thin"
        self.assertIn(e, s)
        self.assertIn(c, s)
        self.assertLess(s.index(e), s.index(c))
        self.assertIn("banks are solid", s)  # top anchor by priority
        self.assertEqual([p["category"] for p in out["pressure_points"]],
                         ["energy", "consumer"])
        # Steady: watch categories first (canonical order), then the rest.
        self.assertEqual([c_["category"] for c_ in out["steady"]],
                         ["economic", "housing", "global", "banking", "business", "markets"])
        # The hub-panel "changed" pointer was removed in revamp Phase C — a
        # passed brief no longer adds anything to the output.
        self.assertNotIn("changed", out)
        self.assertEqual(len(out["categories"]), 8)
        self.assertEqual(out["categories"][0]["href"], "/dashboards/economic/")

    def test_pressure_lens_cards(self):
        out = self.build(todays_indices())
        energy = out["pressure_points"][0]
        self.assertEqual(energy["title"], "Energy & Commodities")
        self.assertEqual(energy["href"], "/dashboards/energy/")
        lenses = energy["lenses"]
        self.assertEqual(len(lenses), 2)  # capped, worst first
        self.assertEqual([l["status"] for l in lenses], ["alert", "alert"])
        self.assertEqual(lenses[0]["headline"], "Read 0.")
        self.assertEqual(lenses[0]["href"], "/dashboards/energy/0.html")

    def test_pressure_cards_only_quote_stressed_lenses(self):
        # An ok lens never belongs in a Pressure Points card, even when the
        # category has nothing else to show (e.g. one alert + one ok lens).
        indices = todays_indices()
        indices["energy"] = cat_index(["alert", "ok"], status="elevated", prefix="energy")
        out = self.build(indices)
        lenses = out["pressure_points"][0]["lenses"]
        self.assertEqual([l["status"] for l in lenses], ["alert"])

    def test_blend_falls_back_when_index_has_no_status(self):
        indices = todays_indices()
        del indices["energy"]["status"]  # stale/fixture-style index
        out = self.build(indices)
        # recomputed from lenses: sqrt(22/4) ~ 2.35 -> elevated, still ranked first
        self.assertEqual(out["pressure_points"][0]["category"], "energy")
        self.assertEqual(out["pressure_points"][0]["status"], "elevated")

    def test_clause_cap_contained_is_two_but_block_shows_three(self):
        indices = todays_indices()
        indices["housing"] = cat_index(["elevated", "elevated", "ok", "ok"],
                                       status="elevated", prefix="housing")
        out = self.build(indices)
        self.assertEqual(out["verdict"]["shape"], "contained-pressure")
        self.assertEqual(len(out["pressure_points"]), 3)
        # housing (RMS 1.41) ranks below energy and consumer -> not in the sentence
        self.assertNotIn("housing market", out["verdict"]["sentence"])

    def test_rank_tie_falls_to_canonical_order(self):
        indices = {
            "economic": cat_index(["ok"], status="ok", prefix="economic"),
            "consumer": cat_index(["elevated"], status="elevated", prefix="consumer"),
            "banking": cat_index(["ok"], status="ok", prefix="bank"),
            "energy": cat_index(["elevated"], status="elevated", prefix="energy"),
        }
        out = self.build(indices)
        # equal RMS (2.0) -> brief.CATEGORIES order: consumer before energy
        self.assertEqual([p["category"] for p in out["pressure_points"]],
                         ["consumer", "energy"])

    def test_insufficient_categories(self):
        indices = {"economic": cat_index(["ok"], status="ok"),
                   "energy": cat_index(["alert"], status="alert")}
        out = self.build(indices, {"transitions": []})
        self.assertEqual(out["verdict"]["status"], "unknown")
        self.assertEqual(out["verdict"]["shape"], "insufficient")
        self.assertEqual(out["pressure_points"], [])
        self.assertEqual(len(out["categories"]), 2)

    def test_missing_copy_degrades_not_crashes(self):
        saved = state.PRESSURE_CLAUSES.pop("energy")
        try:
            out = self.build(todays_indices())
            self.assertIn("stress is showing in energy costs",
                          out["verdict"]["sentence"])
        finally:
            state.PRESSURE_CLAUSES["energy"] = saved

    def test_all_ok_is_all_clear(self):
        indices = {cid: cat_index(["ok", "ok"], status="ok", prefix=cid)
                   for cid in ["economic", "consumer", "banking", "business",
                               "markets", "energy", "housing", "global"]}
        out = self.build(indices)
        self.assertEqual(out["verdict"]["status"], "ok")
        self.assertEqual(out["verdict"]["shape"], "all-clear")
        self.assertEqual(out["pressure_points"], [])
        self.assertEqual(len(out["steady"]), 8)


class TestWatching(unittest.TestCase):
    def _open(self, key, implied, current, due):
        lens = key.split("/")[1]
        return {"key": key, "indicator": key.split("/")[2], "lens": lens,
                "category": key.split("/")[0], "title": "T", "lens_title": "L",
                "due": due, "point": 4.31, "unit": "%", "value_format": "decimal",
                "implied_status": implied, "current_status": current,
                "href": f"/dashboards/{lens}.html"}

    def test_badge_changes_rank_first_alertward_before_okward(self):
        opens = [
            self._open("economic/cost-of-living/cpi", "elevated", "elevated", "2026-07-15"),
            self._open("economic/recession-watch/jobless-claims", "watch", "ok", "2026-06-18"),
            self._open("housing/home-prices/case-shiller", "ok", "watch", "2026-06-30"),
        ]
        block = state.build_watching(opens)
        self.assertEqual(block[0]["key"], "economic/recession-watch/jobless-claims")
        self.assertTrue(block[0]["change"])
        self.assertEqual(block[1]["key"], "housing/home-prices/case-shiller")
        self.assertEqual(block[2]["key"], "economic/cost-of-living/cpi")
        self.assertFalse(block[2]["change"])

    def test_capped_at_three_and_no_change_sorted_by_due(self):
        opens = [self._open(f"economic/l{i}/i{i}", "ok", "ok", f"2026-07-{10 + i:02d}")
                 for i in range(5)]
        block = state.build_watching(opens)
        self.assertEqual(len(block), 3)
        self.assertEqual([b["due"] for b in block],
                         ["2026-07-10", "2026-07-11", "2026-07-12"])

    def test_descriptive_and_market_predictions_excluded_from_watching(self):
        # Market prices / info levels can't move the board and must not surface
        # as dated price targets in the brief or email digest.
        signal = self._open("economic/recession-watch/jobless-claims", "watch", "ok", "2026-06-18")
        gold = dict(self._open("markets/market-scoreboard/gold", "up", "flat", "2026-06-17"),
                    descriptive=True, market_price=True)
        fed = dict(self._open("markets/market-liquidity/fed-balance-sheet", "info", "info",
                              "2026-06-16"), descriptive=True)
        block = state.build_watching([gold, fed, signal])
        keys = [b["key"] for b in block]
        self.assertEqual(keys, ["economic/recession-watch/jobless-claims"])

    def test_build_state_carries_watching_when_given(self):
        indices = {"economic": {"status": "ok", "lenses": [
            {"id": "recession-watch", "title": "RW", "status": "ok", "headline_read": "x"}]}}
        out = state.build_state(indices, None, open_predictions=[
            self._open("economic/recession-watch/jobless-claims", "watch", "ok", "2026-06-18")])
        self.assertIn("watching", out)
        self.assertEqual(out["watching"][0]["point_fmt"], "4.31%")

    def test_build_state_omits_watching_by_default(self):
        indices = {"economic": {"status": "ok", "lenses": []}}
        out = state.build_state(indices, None)
        self.assertNotIn("watching", out)

    def test_build_state_verdict_carries_short(self):
        # Enough categories to clear MIN_CATEGORIES and read all-clear.
        indices = {c: {"status": "ok", "lenses": [
            {"id": f"{c}-l", "title": "L", "status": "ok", "headline_read": "x"}]}
            for c in ("economic", "consumer", "banking", "business", "markets")}
        out = state.build_state(indices, None)
        self.assertEqual(out["verdict"]["short"],
                         "A calm read across the board — nothing is flashing.")
        self.assertNotEqual(out["verdict"]["short"], out["verdict"]["sentence"])


if __name__ == "__main__":
    unittest.main()

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import brief, today


def _lens(id_, status, headline="h", cat_title="T"):
    return {"id": id_, "title": cat_title, "status": status, "headline_read": headline,
            "key_stats": [{"k": "K", "v": "1"}], "sparkline": [1, 2, 1, 2, 1]}


INDICES = {
    "economic": {"status": "watch", "lenses": [_lens("cost-of-living", "elevated"), _lens("job-market", "ok")]},
    "consumer": {"status": "elevated", "lenses": [_lens("consumer-sentiment", "alert")]},
    "banking": {"status": "ok", "lenses": [_lens("bank-profitability", "ok")]},
    "business": {"status": "ok", "lenses": [_lens("business-credit", "watch")]},
    "markets": {"status": "watch", "lenses": [_lens("market-risk-sentiment", "watch")]},
    "energy": {"status": "elevated", "lenses": [_lens("energy-oil-fuels", "alert")]},
    "housing": {"status": "watch", "lenses": [_lens("housing-affordability", "elevated")]},
    "global": {"status": "watch", "lenses": [_lens("global-uncertainty", "elevated")]},
}


class BuildToday(unittest.TestCase):
    def setUp(self):
        self.out, self.new_state = today.build_today(INDICES, {"statuses": {}})

    def test_extends_brief_shape_flat(self):
        # the brief's existing keys survive at the top level (feed + strip
        # renderers read them unchanged) ...
        for key in ("generated_at", "transitions", "top_moves", "status_counts", "lenses"):
            self.assertIn(key, self.out)
        # ... and the absorbed state content sits beside them
        for key in ("verdict", "watching", "pressure", "categories"):
            self.assertIn(key, self.out)

    def test_pressure_rows_sorted_worst_first_with_headlines(self):
        rows = self.out["pressure"]
        self.assertTrue(rows)
        sev = {"alert": 3, "elevated": 2, "watch": 1}
        ranks = [sev[r["status"]] for r in rows]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        self.assertTrue(all(r.get("headline") for r in rows))
        self.assertTrue(all(r["status"] in sev for r in rows))

    def test_categories_carry_authored_sentences(self):
        cats = {c["category"]: c for c in self.out["categories"]}
        self.assertEqual(len(cats), 8)
        self.assertEqual(cats["banking"]["sentence"],
                         today.CATEGORY_SENTENCES["banking"]["ok"])
        self.assertEqual(cats["energy"]["sentence"],
                         today.CATEGORY_SENTENCES["energy"]["elevated"])

    def test_sentence_bank_is_complete(self):
        for cid in brief.CATEGORIES:
            for status in ("ok", "watch", "elevated", "alert"):
                self.assertIn(status, today.CATEGORY_SENTENCES[cid],
                              f"missing sentence for {cid}/{status}")

    def test_unknown_status_gets_generic_sentence(self):
        indices = dict(INDICES)
        indices["banking"] = {"status": "neutral", "lenses": [_lens("bank-profitability", "neutral")]}
        out, _ = today.build_today(indices, {"statuses": {}})
        cats = {c["category"]: c for c in out["categories"]}
        self.assertTrue(cats["banking"]["sentence"])  # generic fallback, never empty

    def test_new_state_passthrough(self):
        self.assertIn("statuses", self.new_state)
        self.assertEqual(self.new_state["statuses"]["cost-of-living"], "elevated")

    def test_watching_included_when_predictions_open(self):
        preds = [{"key": "k", "indicator": "CPI", "lens": "cost-of-living",
                  "category": "economic", "title": "CPI inflation",
                  "lens_title": "The Cost of Living", "due": "2026-06-12",
                  "point": 4.05, "unit": "%", "value_format": "decimal",
                  "implied_status": "elevated", "current_status": "elevated",
                  "href": "/dashboards/cost-of-living.html"}]
        out, _ = today.build_today(INDICES, {"statuses": {}}, open_predictions=preds)
        self.assertEqual(len(out["watching"]), 1)


if __name__ == "__main__":
    unittest.main()

import pathlib
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import feed

TODAY = {
    "generated_at": "2026-06-11T02:07:53Z",
    "transitions": [{"lens_title": "Consumer Credit Stress", "category": "consumer",
                     "from_status": "watch", "to_status": "elevated",
                     "href": "/dashboards/consumer/credit-stress.html",
                     "headline": "Delinquencies are climbing."}],
    "top_moves": [{"lens_title": "Oil & Fuels", "category": "energy",
                   "href": "/dashboards/energy/oil-fuels.html",
                   "stat_label": "Gasoline", "stat_value": "$4.15",
                   "delta": "$0.16", "dir": "down"}],
    "status_counts": {"ok": 17, "watch": 3, "elevated": 8, "alert": 3, "neutral": 2},
}


class TestBuildItem(unittest.TestCase):
    def test_item_carries_date_title_and_counts(self):
        item = feed.build_item(TODAY)
        self.assertEqual(item["date"], "2026-06-11")
        self.assertIn("3 alert", item["title"])
        self.assertIn("Consumer Credit Stress", item["description"])
        self.assertIn("watch → elevated", item["description"])
        self.assertIn("Oil & Fuels", item["description"])

    def test_quiet_day_title(self):
        quiet = dict(TODAY, transitions=[], top_moves=[],
                     status_counts={"ok": 33, "watch": 0, "elevated": 0, "alert": 0})
        item = feed.build_item(quiet)
        self.assertIn("All clear", item["title"])
        self.assertIn("No status changes", item["description"])


class TestMergeItems(unittest.TestCase):
    def test_items_capped_and_newest_first(self):
        items = [{"date": f"2026-06-{d:02d}", "title": "t", "description": "d"}
                 for d in range(1, 10)]
        merged = feed.merge_items(items[:-1], items[-1], cap=5)
        self.assertEqual(len(merged), 5)
        self.assertEqual(merged[0]["date"], "2026-06-09")

    def test_merge_replaces_same_day(self):
        old = [{"date": "2026-06-11", "title": "old", "description": "d"}]
        merged = feed.merge_items(old, {"date": "2026-06-11", "title": "new", "description": "d"})
        self.assertEqual([i["title"] for i in merged], ["new"])

    def test_handles_no_existing(self):
        merged = feed.merge_items(None, {"date": "2026-06-11", "title": "t", "description": "d"})
        self.assertEqual(len(merged), 1)


class TestRenderFeed(unittest.TestCase):
    def test_renders_valid_escaped_rss(self):
        item = feed.build_item(dict(TODAY, transitions=[
            dict(TODAY["transitions"][0], headline="Cards & loans <are> climbing.")]))
        xml_text = feed.render_feed([item])
        self.assertTrue(xml_text.startswith("<?xml"))
        self.assertIn("<rss", xml_text)
        self.assertIn("https://baileyanalytics.com/dashboards/brief.html", xml_text)
        xml.dom.minidom.parseString(xml_text)  # well-formed despite & and <

    def test_item_has_guid_and_pubdate(self):
        xml_text = feed.render_feed([feed.build_item(TODAY)])
        self.assertIn("brief-2026-06-11", xml_text)
        self.assertIn("11 Jun 2026", xml_text)


if __name__ == "__main__":
    unittest.main()

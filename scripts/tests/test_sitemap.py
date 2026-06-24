import pathlib
import sys
import unittest
import xml.dom.minidom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import sitemap


class TestBuildUrls(unittest.TestCase):
    def test_includes_static_pages_hubs_and_lenses(self):
        urls = dict(sitemap.build_urls([]))
        self.assertIn("https://baileyanalytics.com/", urls)
        self.assertIn("https://baileyanalytics.com/about.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/brief.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/economic/", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/banking/", urls)
        # favorites.html is intentionally absent — it's noindex, and a noindex URL
        # in the sitemap trips Search Console's "Submitted URL marked noindex".
        self.assertNotIn("https://baileyanalytics.com/dashboards/favorites.html", urls)
        # slug irregulars resolved via brief.lens_href:
        self.assertIn("https://baileyanalytics.com/dashboards/recession-watch.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/consumer/credit-stress.html", urls)
        self.assertIn("https://baileyanalytics.com/dashboards/banking/asset-quality.html", urls)
        # the crypto lens isn't in config.CATEGORIES' markets entry — listed explicitly:
        self.assertIn("https://baileyanalytics.com/dashboards/markets/crypto-structure.html", urls)

    def test_archive_dates_become_dated_urls_with_lastmod(self):
        urls = dict(sitemap.build_urls(["2026-06-11", "2026-06-12"]))
        self.assertEqual(urls["https://baileyanalytics.com/dashboards/brief/2026-06-12.html"],
                         "2026-06-12")
        self.assertIn("https://baileyanalytics.com/dashboards/brief/", urls)

    def test_no_duplicates(self):
        locs = [loc for loc, _ in sitemap.build_urls(["2026-06-12"])]
        self.assertEqual(len(locs), len(set(locs)))


class TestRenderSitemap(unittest.TestCase):
    def test_renders_valid_xml_with_lastmod_only_when_known(self):
        xml_text = sitemap.render_sitemap([("https://x.com/a", None),
                                           ("https://x.com/b", "2026-06-12")])
        dom = xml.dom.minidom.parseString(xml_text)  # raises on invalid XML
        self.assertEqual(len(dom.getElementsByTagName("url")), 2)
        self.assertEqual(len(dom.getElementsByTagName("lastmod")), 1)
        self.assertIn("<loc>https://x.com/a</loc>", xml_text)

    def test_locs_are_xml_escaped(self):
        xml_text = sitemap.render_sitemap([("https://x.com/path?a=1&b=2", None)])
        self.assertIn("&amp;", xml_text)
        self.assertNotIn("?a=1&b=2</loc>", xml_text)


if __name__ == "__main__":
    unittest.main()

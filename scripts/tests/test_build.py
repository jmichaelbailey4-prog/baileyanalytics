import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config


class TestConfig(unittest.TestCase):
    def test_recession_watch_lens_present(self):
        ids = [lens.id for lens in config.LENSES]
        self.assertIn("recession-watch", ids)

    def test_indicator_fetch_key(self):
        lens = next(l for l in config.LENSES if l.id == "recession-watch")
        ind = lens.indicators[0]
        self.assertEqual(ind.fetch_key, f"{ind.series_id}:lin")

    def test_every_indicator_has_rule_and_context(self):
        for lens in config.LENSES:
            for ind in lens.indicators:
                self.assertTrue(callable(ind.rule))
                self.assertTrue(ind.context)


if __name__ == "__main__":
    unittest.main()

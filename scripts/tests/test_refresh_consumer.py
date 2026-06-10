import sys
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestConsumerDryRun(unittest.TestCase):
    def test_consumer_flag_runs_dry_into_tempdir(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            orig = refresh_lenses.CONSUMER_OUT_DIR
            refresh_lenses.CONSUMER_OUT_DIR = tmp
            try:
                rc = refresh_lenses.main(["--consumer", "--dry-run"])
            finally:
                refresh_lenses.CONSUMER_OUT_DIR = orig
            self.assertEqual(rc, 0)
            for name in ("consumer-spending.json", "consumer-credit.json",
                         "consumer-income-savings.json", "consumer-sentiment.json",
                         "index.json"):
                self.assertTrue((tmp / name).exists(), name)


if __name__ == "__main__":
    unittest.main()

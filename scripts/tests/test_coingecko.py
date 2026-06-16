import sys
import pathlib
import io
import json
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import coingecko


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestTopCoins(unittest.TestCase):
    def test_excludes_stablecoins(self):
        payload = [
            {"id": "bitcoin", "symbol": "btc", "current_price": 60000, "market_cap": 1.2e12},
            {"id": "tether", "symbol": "usdt", "current_price": 1.0, "market_cap": 9e10},
            {"id": "ethereum", "symbol": "eth", "current_price": 3000, "market_cap": 4e11},
            {"id": "some-usd", "symbol": "x", "current_price": 1.0, "market_cap": 1e10},
            {"id": "solana", "symbol": "sol", "current_price": 150, "market_cap": 7e10},
        ]
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            coins = coingecko.top_coins(3)
        self.assertEqual([c["id"] for c in coins], ["bitcoin", "ethereum", "solana"])

    def test_market_cap_history_parses_ms_to_date(self):
        payload = {"market_caps": [[1700000000000, 1.0e12], [1700086400000, 1.1e12]]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            hist = coingecko.market_cap_history("bitcoin", days=2)
        self.assertEqual(hist[0]["date"], "2023-11-14")
        self.assertEqual(hist[1]["value"], 1.1e12)

    def test_global_metrics_extracts_btc_dominance(self):
        payload = {"data": {"market_cap_percentage": {"btc": 54.3, "eth": 17.1}}}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.coingecko.urllib.request.urlopen", return_value=fake):
            self.assertEqual(coingecko.global_metrics()["btc_dominance"], 54.3)


class TestCompute(unittest.TestCase):
    def test_basket_history_sums_by_date(self):
        a = [{"date": "2026-01-01", "value": 10.0}, {"date": "2026-01-02", "value": 12.0}]
        b = [{"date": "2026-01-01", "value": 5.0}, {"date": "2026-01-02", "value": 6.0}]
        out = coingecko.basket_history([a, b])
        self.assertEqual(out, [{"date": "2026-01-01", "value": 15.0},
                               {"date": "2026-01-02", "value": 18.0}])

    def test_compute_rotation_indexes_and_ratios(self):
        # large doubles, small triples -> small outperforms -> ratio rises above 100.
        large = [{"date": "2026-01-01", "value": 100.0}, {"date": "2026-01-02", "value": 200.0}]
        small = [{"date": "2026-01-01", "value": 50.0}, {"date": "2026-01-02", "value": 150.0}]
        out = coingecko.compute_rotation(large, small)
        self.assertEqual(out[0]["value"], 100.0)          # base date indexed to 100/100
        self.assertEqual(out[1]["value"], 150.0)          # (300/100)/(200/100)*100 = 150

    def test_compute_rotation_handles_no_overlap(self):
        self.assertEqual(coingecko.compute_rotation([], []), [])


class TestRetry(unittest.TestCase):
    def test_retries_transient_5xx_then_succeeds(self):
        payload = {"data": {"market_cap_percentage": {"btc": 50.0}}}
        ok = FakeResponse(json.dumps(payload).encode())
        err = urllib.error.HTTPError("http://x", 503, "Service Unavailable", None, None)
        with mock.patch("lenses.coingecko.time.sleep"), \
             mock.patch("lenses.coingecko.urllib.request.urlopen", side_effect=[err, ok]):
            self.assertEqual(coingecko.global_metrics()["btc_dominance"], 50.0)

    def test_client_error_4xx_raises_immediately_without_backoff(self):
        err = urllib.error.HTTPError("http://x", 404, "Not Found", None, None)
        with mock.patch("lenses.coingecko.time.sleep") as slept, \
             mock.patch("lenses.coingecko.urllib.request.urlopen", side_effect=err):
            with self.assertRaises(urllib.error.HTTPError):
                coingecko.global_metrics()
        slept.assert_not_called()


if __name__ == "__main__":
    unittest.main()

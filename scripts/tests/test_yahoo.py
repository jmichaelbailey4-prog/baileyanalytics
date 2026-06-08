import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import yahoo


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


PAYLOAD = {
    "chart": {
        "result": [
            {
                "timestamp": [1700000000, 1700086400, 1700172800],
                "indicators": {"quote": [{"close": [2680.5, None, 2710.25]}]},
            }
        ]
    }
}


class TestGoldHistory(unittest.TestCase):
    def test_parses_timestamps_and_closes(self):
        fake = FakeResponse(json.dumps(PAYLOAD).encode())
        with mock.patch("lenses.yahoo.urllib.request.urlopen", return_value=fake):
            hist = yahoo.gold_history()
        # the middle (null close) row is skipped
        self.assertEqual(hist, [
            {"date": "2023-11-14", "value": "2680.50"},
            {"date": "2023-11-16", "value": "2710.25"},
        ])

    def test_empty_result_returns_empty(self):
        fake = FakeResponse(json.dumps({"chart": {"result": []}}).encode())
        with mock.patch("lenses.yahoo.urllib.request.urlopen", return_value=fake):
            self.assertEqual(yahoo.gold_history(), [])


if __name__ == "__main__":
    unittest.main()

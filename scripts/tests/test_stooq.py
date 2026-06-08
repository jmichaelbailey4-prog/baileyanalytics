import sys
import pathlib
import io
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import stooq


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-06-02,2680.0,2700.0,2675.0,2695.50,0\n"
    "2026-06-03,2695.5,2720.0,2690.0,2710.25,0\n"
    "2026-06-04,N/D,N/D,N/D,N/D,0\n"  # a bad row Stooq sometimes emits — must be skipped
)


class TestGoldHistory(unittest.TestCase):
    def test_parses_date_and_close(self):
        fake = FakeResponse(CSV.encode())
        with mock.patch("lenses.stooq.urllib.request.urlopen", return_value=fake):
            hist = stooq.gold_history()
        self.assertEqual(hist[0], {"date": "2026-06-02", "value": "2695.50"})
        self.assertEqual(hist[-1], {"date": "2026-06-03", "value": "2710.25"})  # N/D row dropped

    def test_limit_keeps_most_recent(self):
        fake = FakeResponse(CSV.encode())
        with mock.patch("lenses.stooq.urllib.request.urlopen", return_value=fake):
            hist = stooq.gold_history(limit=1)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["date"], "2026-06-03")


if __name__ == "__main__":
    unittest.main()

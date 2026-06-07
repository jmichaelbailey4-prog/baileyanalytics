import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import fred


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TestFred(unittest.TestCase):
    def test_returns_chronological_observations(self):
        payload = {
            "observations": [
                {"date": "2026-06-02", "value": "0.30", "realtime_start": "x"},
                {"date": "2026-06-01", "value": "0.28", "realtime_start": "x"},
            ]
        }
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fred.urllib.request.urlopen", return_value=fake) as m:
            obs = fred.fetch_observations("T10Y2Y", api_key="KEY", limit=500)
        self.assertEqual(obs, [
            {"date": "2026-06-01", "value": "0.28"},
            {"date": "2026-06-02", "value": "0.30"},
        ])
        called_url = m.call_args[0][0]
        self.assertIn("series_id=T10Y2Y", called_url)
        self.assertIn("api_key=KEY", called_url)
        self.assertIn("sort_order=desc", called_url)

    def test_includes_units_transform_when_given(self):
        fake = FakeResponse(json.dumps({"observations": []}).encode())
        with mock.patch("lenses.fred.urllib.request.urlopen", return_value=fake) as m:
            fred.fetch_observations("CPIAUCSL", api_key="KEY", limit=240, units="pc1")
        self.assertIn("units=pc1", m.call_args[0][0])


if __name__ == "__main__":
    unittest.main()

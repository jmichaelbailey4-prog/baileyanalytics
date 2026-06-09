import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import eia


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# EIA returns newest-first; one row has a null value to be dropped.
PAYLOAD = {
    "response": {
        "data": [
            {"period": "2026-03-06", "value": 3.25},
            {"period": "2026-02-27", "value": None},
            {"period": "2026-02-20", "value": 3.10},
        ]
    }
}


class TestFetchSeries(unittest.TestCase):
    def test_parses_oldest_first_and_drops_nulls(self):
        fake = FakeResponse(json.dumps(PAYLOAD).encode())
        with mock.patch("lenses.eia.urllib.request.urlopen", return_value=fake) as m:
            rows = eia.fetch_series("petroleum/pri/gnd",
                                    [("series", "EMM_EPMR_PTE_NUS_DPG")],
                                    "weekly", "KEY", length=10)
        self.assertEqual(rows, [
            {"date": "2026-02-20", "value": "3.1"},
            {"date": "2026-03-06", "value": "3.25"},
        ])
        called_url = m.call_args.args[0]
        self.assertIn("petroleum/pri/gnd/data/", called_url)
        self.assertIn("api_key=KEY", called_url)
        self.assertIn("frequency=weekly", called_url)

    def test_custom_data_column(self):
        payload = {"response": {"data": [{"period": "2026-01", "price": 12.5}]}}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.eia.urllib.request.urlopen", return_value=fake):
            rows = eia.fetch_series("electricity/retail-sales", [("sectorid", "RES")],
                                    "monthly", "KEY", data_col="price")
        self.assertEqual(rows, [{"date": "2026-01", "value": "12.5"}])


if __name__ == "__main__":
    unittest.main()

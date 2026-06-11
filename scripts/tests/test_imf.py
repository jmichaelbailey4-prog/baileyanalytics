import sys
import pathlib
import io
import datetime
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import imf

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "imf_sample.xml"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestParseWeo(unittest.TestCase):
    def test_series_keyed_by_country_dot_indicator(self):
        series = imf.parse_weo(FIXTURE.read_bytes())
        self.assertEqual(set(series),
                         {"G001.NGDP_RPCH", "CHN.NGDP_RPCH", "G001.PCPIPCH"})

    def test_observations_sorted_oldest_first(self):
        series = imf.parse_weo(FIXTURE.read_bytes())
        chn = series["CHN.NGDP_RPCH"]  # fixture lists 2026 before 2025
        self.assertEqual([o["date"] for o in chn], ["2025", "2026"])
        self.assertEqual(chn[0]["value"], "4.958804")

    def test_values_are_strings_fred_style(self):
        series = imf.parse_weo(FIXTURE.read_bytes())
        for obs in series["G001.NGDP_RPCH"]:
            self.assertIsInstance(obs["value"], str)


class TestSplitActuals(unittest.TestCase):
    OBS = [{"date": "2025", "value": "3.4"}, {"date": "2026", "value": "3.1"},
           {"date": "2027", "value": "3.2"}, {"date": "2028", "value": "3.2"}]

    def test_truncates_at_current_year(self):
        actuals, _ = imf.split_actuals(self.OBS, today=datetime.date(2026, 6, 10))
        self.assertEqual([o["date"] for o in actuals], ["2025", "2026"])

    def test_forecast_is_next_year(self):
        _, forecast = imf.split_actuals(self.OBS, today=datetime.date(2026, 6, 10))
        self.assertEqual(forecast, {"year": "2027", "value": 3.2})

    def test_no_forecast_when_next_year_absent(self):
        _, forecast = imf.split_actuals(self.OBS[:2], today=datetime.date(2026, 6, 10))
        self.assertIsNone(forecast)


class TestForecastFor(unittest.TestCase):
    def test_late_binding_lookup(self):
        lookup = imf.forecast_for("G001.NGDP_RPCH")
        imf.FORECASTS.pop("G001.NGDP_RPCH", None)
        self.assertIsNone(lookup())
        imf.FORECASTS["G001.NGDP_RPCH"] = {"year": "2027", "value": 3.2}
        try:
            self.assertEqual(lookup(), {"year": "2027", "value": 3.2})
        finally:
            imf.FORECASTS.pop("G001.NGDP_RPCH", None)


class TestWeoSeries(unittest.TestCase):
    def test_batched_url_and_parse(self):
        fake = FakeResponse(FIXTURE.read_bytes())
        with mock.patch("lenses.imf.urllib.request.urlopen", return_value=fake) as m:
            series = imf.weo_series(["G001", "CHN", "G163"], ["NGDP_RPCH", "PCPIPCH"])
        req = m.call_args.args[0]
        self.assertIn("IMF.RES,WEO/G001+CHN+G163.NGDP_RPCH+PCPIPCH.A", req.full_url)
        self.assertIn("startPeriod=1980", req.full_url)
        self.assertTrue(req.get_header("User-agent", "").startswith("Mozilla"))
        self.assertIn("G001.NGDP_RPCH", series)


if __name__ == "__main__":
    unittest.main()

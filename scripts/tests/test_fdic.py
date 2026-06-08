import sys
import pathlib
import io
import json
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import fdic


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestQuarterEnds(unittest.TestCase):
    def test_lists_quarter_ends_through_latest(self):
        self.assertEqual(
            fdic.quarter_ends(2023, "20240630"),
            ["20230331", "20230630", "20230930", "20231231", "20240331", "20240630"],
        )

    def test_stops_at_latest_partial_year(self):
        self.assertEqual(fdic.quarter_ends(2024, "20240331"), ["20240331"])


class TestNationalQuarterly(unittest.TestCase):
    def test_weighted_average_per_quarter(self):
        q1 = [{"NCLNLSR": 1.0, "LNLSNET": 1000}]
        q2 = [{"NCLNLSR": 2.0, "LNLSNET": 1000}]
        metric = {"key": "noncurrent", "ratio_field": "NCLNLSR", "weight_field": "LNLSNET"}
        with mock.patch("lenses.fdic._fetch_all_financials", side_effect=[q1, q2]):
            series = fdic.national_quarterly([metric], ["20240331", "20240630"])
        self.assertEqual(series["noncurrent"], [
            {"date": "2024-03-31", "value": "1.0000"},
            {"date": "2024-06-30", "value": "2.0000"},
        ])

    def test_sum_then_ratio_metric(self):
        banks = [{"EQ": 100, "ASSET": 1000}, {"EQ": 50, "ASSET": 1000}]
        metric = {"key": "capital", "numerator": ["EQ"], "denominator": ["ASSET"], "scale": 100.0}
        with mock.patch("lenses.fdic._fetch_all_financials", return_value=banks):
            series = fdic.national_quarterly([metric], ["20241231"])
        # (100+50)/(1000+1000)*100 = 7.5
        self.assertEqual(series["capital"], [{"date": "2024-12-31", "value": "7.5000"}])


class TestRanking(unittest.TestCase):
    def test_ranks_and_applies_hygiene_floor(self):
        payload = {"data": [
            {"data": {"NAME": "BIG CRE BANK", "CITY": "Denver", "STALP": "CO",
                      "ASSET": 3200000, "NCRER": 6.4}},
            {"data": {"NAME": "OK BANK", "CITY": "Tampa", "STALP": "FL",
                      "ASSET": 1800000, "NCRER": 5.1}},
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake) as m:
            rows = fdic.ranking(metric_field="NCRER", repdte="20241231",
                                asset_min=1000000, limit=10)
        self.assertEqual(rows[0]["name"], "BIG CRE BANK")
        self.assertEqual(rows[0]["location"], "Denver, CO")
        self.assertEqual(rows[0]["asset"], "$3.2B")
        self.assertEqual(rows[0]["value"], 6.4)
        url = m.call_args[0][0]
        self.assertIn("sort_by=NCRER", url)
        self.assertIn("sort_order=DESC", url)

    def test_filters_outliers_by_cap_and_materiality(self):
        payload = {"data": [
            # 36% but a tiny CRE book ($6M < $250M floor) — exploded ratio, drop it
            {"data": {"NAME": "TINY CRE", "CITY": "X", "STALP": "TX", "ASSET": 2000000,
                      "NCRER": 36.0, "LNRENRES": 5000, "LNREMULT": 1000}},
            # 25% on a real book — above the 20% sanity cap, drop it
            {"data": {"NAME": "HUGE OUTLIER", "CITY": "Z", "STALP": "FL", "ASSET": 5000000,
                      "NCRER": 25.0, "LNRENRES": 900000, "LNREMULT": 200000}},
            # 8% on a $500M CRE book — a real, material signal, keep it
            {"data": {"NAME": "REAL STRESS", "CITY": "Y", "STALP": "OH", "ASSET": 3000000,
                      "NCRER": 8.0, "LNRENRES": 400000, "LNREMULT": 100000}},
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            rows = fdic.ranking("NCRER", "20241231", 1_000_000, 10,
                                min_base_fields=["LNRENRES", "LNREMULT"],
                                min_base=250_000, max_value=20.0)
        self.assertEqual([r["name"] for r in rows], ["REAL STRESS"])

    def test_min_value_floor_for_ascending_metrics(self):
        payload = {"data": [
            {"data": {"NAME": "FAILING", "CITY": "X", "STALP": "TX", "ASSET": 2000000, "EQV": 1.0}},
            {"data": {"NAME": "THIN BUT REAL", "CITY": "Y", "STALP": "OH", "ASSET": 3000000, "EQV": 4.5}},
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            rows = fdic.ranking("EQV", "20241231", 1_000_000, 10, sort_order="ASC", min_value=3.0)
        self.assertEqual([r["name"] for r in rows], ["THIN BUT REAL"])


class TestTiers(unittest.TestCase):
    def test_buckets_by_asset_band_and_sums(self):
        payload = {"data": [
            {"data": {"ASSET": 5000000, "NALNLS": 60, "LNLSNET": 6000}},      # community
            {"data": {"ASSET": 400000000, "NALNLS": 60, "LNLSNET": 12000}},   # large
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        tiers = [("Community (<$10B)", 0, 10_000_000),
                 ("Large (>$250B)", 250_000_000, None)]
        metric = {"key": "noncurrent", "numerator": ["NALNLS"], "denominator": ["LNLSNET"], "scale": 100.0}
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            rows = fdic.tier_aggregates([metric], repdte="20241231", tiers=tiers)
        self.assertEqual(rows[0]["tier"], "Community (<$10B)")
        self.assertEqual(rows[0]["values"][0]["value"], 1.0)
        self.assertEqual(rows[1]["values"][0]["value"], 0.5)

    def test_weighted_average_ratio_metric(self):
        payload = {"data": [
            {"data": {"ASSET": 5000000, "NCLNLSR": 2.0, "LNLSNET": 1000}},
            {"data": {"ASSET": 6000000, "NCLNLSR": 1.0, "LNLSNET": 3000}},
        ]}
        fake = FakeResponse(json.dumps(payload).encode())
        tiers = [("Community (<$10B)", 0, 10_000_000)]
        metric = {"key": "noncurrent", "ratio_field": "NCLNLSR", "weight_field": "LNLSNET"}
        with mock.patch("lenses.fdic.urllib.request.urlopen", return_value=fake):
            rows = fdic.tier_aggregates([metric], repdte="20241231", tiers=tiers)
        # (2.0*1000 + 1.0*3000) / (1000+3000) = 1.25
        self.assertEqual(rows[0]["values"][0]["value"], 1.25)


if __name__ == "__main__":
    unittest.main()

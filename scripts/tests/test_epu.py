import sys
import pathlib
import io
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import epu

FIXDIR = pathlib.Path(__file__).resolve().parent / "fixtures"
US = FIXDIR / "epu_us_sample.xlsx"
GLOBAL = FIXDIR / "epu_global_sample.xlsx"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestParseEpuUS(unittest.TestCase):
    def parsed(self):
        return epu.parse_epu(US.read_bytes(), ("News_Based",))

    def test_ascending_yyyy_mm_dates(self):
        obs = self.parsed()
        self.assertEqual([o["date"] for o in obs],
                         ["1985-01", "2026-03", "2026-04", "2026-05"])

    def test_values_two_dp_strings(self):
        obs = self.parsed()
        self.assertEqual(obs[-1]["value"], "296.34")

    def test_citation_trailer_skipped(self):
        for o in self.parsed():
            self.assertRegex(o["date"], r"^\d{4}-\d{2}$")


class TestParseEpuGlobal(unittest.TestCase):
    def test_picks_gepu_current_not_ppp(self):
        obs = epu.parse_epu(GLOBAL.read_bytes(), ("GEPU_current",))
        self.assertEqual(obs[-1]["date"], "2025-11")
        self.assertEqual(obs[-1]["value"], "371.32")
        self.assertEqual(obs[0]["value"], "88.30")


class TestFetchers(unittest.TestCase):
    def test_us_epu_url_and_ua(self):
        fake = FakeResponse(US.read_bytes())
        with mock.patch("lenses.epu.urllib.request.urlopen",
                        return_value=fake) as m:
            obs = epu.us_epu()
        req = m.call_args.args[0]
        self.assertIn("US_Policy_Uncertainty_Data.xlsx", req.full_url)
        self.assertTrue(req.get_header("User-agent", "").startswith("Mozilla"))
        self.assertEqual(obs[-1]["date"], "2026-05")

    def test_global_epu_url(self):
        fake = FakeResponse(GLOBAL.read_bytes())
        with mock.patch("lenses.epu.urllib.request.urlopen",
                        return_value=fake) as m:
            obs = epu.global_epu()
        req = m.call_args.args[0]
        self.assertIn("Global_Policy_Uncertainty_Data.xlsx", req.full_url)
        self.assertEqual(obs[-1]["value"], "371.32")


if __name__ == "__main__":
    unittest.main()

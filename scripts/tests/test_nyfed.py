import sys
import pathlib
import io
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import nyfed

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "gscpi_sample.csv"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class TestParseGscpi(unittest.TestCase):
    def parsed(self):
        return nyfed.parse_gscpi(FIXTURE.read_text())

    def test_takes_last_non_na_column_per_row(self):
        obs = self.parsed()
        by_date = {o["date"]: o["value"] for o in obs}
        self.assertEqual(by_date["2026-03"], "0.68")  # last vintage is #N/A
        self.assertEqual(by_date["2026-04"], "1.82")
        self.assertEqual(by_date["2026-05"], "1.77")

    def test_skips_serial_header_and_emits_yyyy_mm(self):
        obs = self.parsed()
        self.assertEqual(obs[0]["date"], "1997-09")
        for o in obs:
            self.assertRegex(o["date"], r"^\d{4}-\d{2}$")

    def test_oldest_first_two_dp_strings(self):
        obs = self.parsed()
        self.assertEqual([o["date"] for o in obs],
                         sorted(o["date"] for o in obs))
        self.assertEqual(obs[0]["value"], "-0.40")


class TestGscpiFetch(unittest.TestCase):
    def test_browser_user_agent_and_url(self):
        fake = FakeResponse(FIXTURE.read_bytes())
        with mock.patch("lenses.nyfed.urllib.request.urlopen",
                        return_value=fake) as m:
            obs = nyfed.gscpi()
        req = m.call_args.args[0]
        self.assertIn("newyorkfed.org", req.full_url)
        self.assertIn("gscpi_interactive_data.csv", req.full_url)
        self.assertTrue(req.get_header("User-agent", "").startswith("Mozilla"))
        self.assertEqual(obs[-1]["date"], "2026-05")


if __name__ == "__main__":
    unittest.main()

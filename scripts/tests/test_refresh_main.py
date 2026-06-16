import sys
import pathlib
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import refresh_lenses


class TestMainControlFlow(unittest.TestCase):
    def test_economic_failure_does_not_abort_later_categories(self):
        # A missing FRED key makes the FRED categories return non-zero. Economic
        # runs first; it must NOT abort the no-key categories (banking) or the
        # brief in a full run (it previously hard-returned, skipping everything).
        names = ("refresh_economic", "refresh_markets", "refresh_energy",
                 "refresh_housing", "refresh_consumer", "refresh_global",
                 "refresh_business", "refresh_banking", "refresh_brief")
        with mock.patch.multiple(refresh_lenses, **{n: mock.DEFAULT for n in names}) as m:
            for n in names[:7]:           # every FRED category "fails" (no key)
                m[n].return_value = 1
            m["refresh_banking"].return_value = None
            m["refresh_brief"].return_value = None
            rc = refresh_lenses.main([])
        m["refresh_economic"].assert_called_once()
        m["refresh_banking"].assert_called_once()   # reached despite economic failing
        m["refresh_brief"].assert_called_once()      # reached despite economic failing
        self.assertNotEqual(rc, 0)                   # the failure is still surfaced


if __name__ == "__main__":
    unittest.main()

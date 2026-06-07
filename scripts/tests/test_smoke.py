import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # add scripts/ to path


class TestSmoke(unittest.TestCase):
    def test_package_imports(self):
        import lenses  # noqa: F401
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

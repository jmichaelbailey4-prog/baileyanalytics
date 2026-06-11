import sys
import math
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import models  # noqa: E402

TREND = [100.0 + 2.0 * i for i in range(60)]                       # clean linear trend
SEASONAL = [100.0 + 2.0 * i + 10.0 * math.sin(2 * math.pi * i / 12) for i in range(72)]


class TestBaselines(unittest.TestCase):
    def test_naive(self):
        self.assertEqual(models.predict_one("naive", TREND, 12), TREND[-1])

    def test_seasonal_naive(self):
        self.assertEqual(models.predict_one("seasonal-naive", SEASONAL, 12), SEASONAL[-12])

    def test_seasonal_naive_short_history_falls_back_to_naive(self):
        self.assertEqual(models.predict_one("seasonal-naive", [1.0, 2.0], 12), 2.0)

    def test_drift_extends_trend(self):
        self.assertAlmostEqual(models.predict_one("drift", TREND, 12), TREND[-1] + 2.0, places=6)


class TestStatsmodels(unittest.TestCase):
    def test_ets_tracks_trend(self):
        p = models.predict_one("ets", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=1.0)

    def test_ets_seasonal_beats_naive_on_seasonal_series(self):
        p_seasonal = models.predict_one("ets-seasonal", SEASONAL, 12)
        truth = 100.0 + 2.0 * 72 + 10.0 * math.sin(2 * math.pi * 72 / 12)
        self.assertLess(abs(p_seasonal - truth), abs(SEASONAL[-1] - truth))

    def test_theta_runs(self):
        p = models.predict_one("theta", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=3.0)

    def test_sarima_runs(self):
        p = models.predict_one("sarima", TREND, 1)
        self.assertAlmostEqual(p, TREND[-1] + 2.0, delta=3.0)

    def test_too_short_raises(self):
        with self.assertRaises(models.ModelError):
            models.predict_one("ets", [1.0, 2.0, 3.0], 1)

    def test_unknown_model_raises(self):
        with self.assertRaises(models.ModelError):
            models.predict_one("bogus", TREND, 1)

    def test_versions_cover_all_models(self):
        for name in models.MODEL_NAMES:
            self.assertIn(name, models.VERSIONS)


if __name__ == "__main__":
    unittest.main()

import sys
import math
import pathlib
import random
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from predictions import backtest, models  # noqa: E402

random.seed(7)
SEASONAL = [100.0 + 0.5 * i + 8.0 * math.sin(2 * math.pi * i / 12)
            + random.gauss(0, 0.5) for i in range(240)]


class TestRollingOrigin(unittest.TestCase):
    def test_no_leakage_planted_break(self):
        # Flat at 100 then jumps to 1000 at index 150. A model standing at any
        # origin <= 150 must not benefit from post-break data: its prediction
        # must stay near 100, so the error AT the break is ~900 for every model.
        series = [100.0] * 150 + [1000.0] * 50
        for name in ("naive", "drift", "ets"):
            errors = backtest.rolling_errors(name, series, season=1,
                                             origins=backtest.pick_origins(len(series), 60))
            err_at_break = next(e for i, e in errors if i == 150)
            self.assertGreater(abs(err_at_break), 800.0,
                               f"{name} leaked future data across the break")

    def test_errors_are_signed_actual_minus_predicted(self):
        series = [1.0, 2.0, 3.0, 4.0, 5.0]
        errors = backtest.rolling_errors("naive", series, 1, [4])
        self.assertEqual(errors, [(4, 1.0)])  # actual 5.0 - naive 4.0


class TestTournament(unittest.TestCase):
    def test_seasonal_model_beats_naive_on_seasonal_series(self):
        result = backtest.tournament(SEASONAL, season=12, max_origins=60)
        self.assertNotIn(result["champion"], ("naive",))
        self.assertLess(result["mae"], result["snaive_mae"] + 1e-9)

    def test_random_walk_ships_baseline(self):
        # On a pure random walk, any model's backtest edge over naive is
        # sampling luck (measured ~2% on this seed); the MIN_SKILL margin
        # must hand the championship back to a baseline.
        rw = [0.0]
        for _ in range(299):
            rw.append(rw[-1] + random.gauss(0, 1))
        result = backtest.tournament(rw, season=1, max_origins=60)
        self.assertIn(result["champion"], models.BASELINES)

    def test_non_baseline_champion_implies_real_skill(self):
        result = backtest.tournament(SEASONAL, season=12, max_origins=60)
        if result["champion"] not in models.BASELINES:
            self.assertGreaterEqual(result["skill"], backtest.MIN_SKILL)

    def test_bands_cover_about_80pct(self):
        result = backtest.tournament(SEASONAL, season=12, max_origins=100)
        lo, hi = result["err_lo"], result["err_hi"]
        errors = [e for _, e in backtest.rolling_errors(
            result["champion"], SEASONAL, 12, backtest.pick_origins(len(SEASONAL), 100))]
        covered = sum(1 for e in errors if lo <= e <= hi) / len(errors)
        self.assertGreater(covered, 0.7)
        self.assertLess(covered, 0.95)

    def test_result_shape(self):
        r = backtest.tournament(SEASONAL, season=12, max_origins=40)
        for k in ("champion", "mae", "naive_mae", "snaive_mae",
                  "err_lo", "err_hi", "n_origins", "skill"):
            self.assertIn(k, r)
        self.assertLessEqual(r["err_lo"], 0.0)
        self.assertGreaterEqual(r["err_hi"], 0.0)

    def test_too_short_series_returns_none(self):
        self.assertIsNone(backtest.tournament([1.0] * 10, season=1, max_origins=40))


if __name__ == "__main__":
    unittest.main()

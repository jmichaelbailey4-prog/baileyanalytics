"""The model toolbox: six families behind one one-step-ahead interface.
All deterministic. Each family has a one-sentence explanation in explain.py —
a model that can't be explained in a sentence doesn't ship (brand rule)."""

import warnings

import numpy as np
import pandas as pd

VERSIONS = {"naive": 1, "seasonal-naive": 1, "drift": 1,
            "ets": 1, "ets-seasonal": 1, "theta": 1, "sarima": 1}
MODEL_NAMES = tuple(VERSIONS)
BASELINES = ("naive", "seasonal-naive", "drift")
MIN_POINTS = 24          # statsmodels families need real history
TRAIN_WINDOW = 480       # cap fits at the trailing window: faster, recent-weighted


class ModelError(Exception):
    pass


def _naive(v, s):
    return v[-1]


def _seasonal_naive(v, s):
    return v[-s] if s > 1 and len(v) >= s else v[-1]


def _drift(v, s):
    if len(v) < 2:
        return v[-1]
    return v[-1] + (v[-1] - v[0]) / (len(v) - 1)


def _ets(v, s, seasonal=False):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    arr = np.asarray(v, dtype=float)
    kwargs = {"trend": "add", "damped_trend": True}
    if seasonal:
        if s <= 1 or len(arr) < 2 * s + 4:
            raise ModelError("not enough history for a seasonal fit")
        kwargs.update(seasonal="add", seasonal_periods=s)
    fit = ExponentialSmoothing(arr, **kwargs).fit()
    return float(fit.forecast(1)[0])


def _theta(v, s):
    from statsmodels.tsa.forecasting.theta import ThetaModel
    series = pd.Series(np.asarray(v, dtype=float))
    deseasonalize = s > 1 and len(v) >= 2 * s
    fit = ThetaModel(series, period=max(s, 1), deseasonalize=deseasonalize).fit()
    return float(fit.forecast(1).iloc[0])


def _sarima(v, s):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    arr = np.asarray(v, dtype=float)
    seasonal_order = (0, 1, 1, s) if s > 1 and len(arr) >= 3 * s else (0, 0, 0, 0)
    fit = SARIMAX(arr, order=(1, 1, 1), seasonal_order=seasonal_order,
                  enforce_stationarity=False, enforce_invertibility=False
                  ).fit(disp=False, maxiter=50)
    return float(fit.forecast(1)[0])


_FAMILIES = {
    "naive": _naive,
    "seasonal-naive": _seasonal_naive,
    "drift": _drift,
    "ets": lambda v, s: _ets(v, s, seasonal=False),
    "ets-seasonal": lambda v, s: _ets(v, s, seasonal=True),
    "theta": _theta,
    "sarima": _sarima,
}


def predict_one(name, values, season):
    """One-step-ahead point forecast. Raises ModelError on anything unusable —
    callers treat that as 'this model sits this one out'."""
    fn = _FAMILIES.get(name)
    if fn is None:
        raise ModelError(f"unknown model {name!r}")
    v = [float(x) for x in values][-TRAIN_WINDOW:]
    if name not in BASELINES and len(v) < MIN_POINTS:
        raise ModelError(f"{name}: only {len(v)} points")
    if not v:
        raise ModelError("empty series")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = fn(v, int(season))
    except ModelError:
        raise
    except Exception as exc:  # noqa: BLE001 - statsmodels failure modes are many
        raise ModelError(f"{name}: {exc}") from exc
    if out is None or not np.isfinite(out):
        raise ModelError(f"{name}: non-finite forecast")
    return float(out)

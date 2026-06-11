"""Rolling-origin backtesting and the per-indicator tournament.

At each origin i, every model is fitted on values[:i] ONLY and predicts
values[i]. Champion = lowest MAE, but it ships only if it beats seasonal-naive
(spec §4) — otherwise the baseline itself ships, which is an honest prediction.
Bands are the empirical 10th–90th percentile of the champion's signed errors:
bands history earned, not parametric formulas. A model failing >10% of its
origins is disqualified for that series."""

from . import models

MIN_TRAIN = 36           # smallest training slice an origin may stand on
ERR_QUANTILES = (0.10, 0.90)
MAX_FAIL_SHARE = 0.10
# A non-baseline champion must beat seasonal-naive by this margin. A 2%
# backtest edge on ~100 origins is sampling luck (measured on synthetic
# random walks); real structure shows up as 20%+ skill.
MIN_SKILL = 0.05


def pick_origins(n, max_origins):
    """The last `max_origins` indices that leave >= MIN_TRAIN training points."""
    first = max(MIN_TRAIN, n - max_origins)
    return list(range(first, n))


def rolling_errors(name, values, season, origins):
    """[(origin_index, signed_error actual-minus-predicted)] — failures skipped."""
    out = []
    for i in origins:
        try:
            p = models.predict_one(name, values[:i], season)
        except models.ModelError:
            continue
        out.append((i, values[i] - p))
    return out


def _quantile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    pos = q * (len(sorted_vals) - 1)
    lo, hi = int(pos), min(int(pos) + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def tournament(values, season, max_origins):
    """Run every model through the same origins; return the champion record
    (spec §4 models.json fields) or None when the series is too short."""
    n = len(values)
    if n < MIN_TRAIN + 5:
        return None
    origins = pick_origins(n, max_origins)
    maes, errors_by_model = {}, {}
    for name in models.MODEL_NAMES:
        errs = rolling_errors(name, values, season, origins)
        if len(errs) < len(origins) * (1 - MAX_FAIL_SHARE):
            continue  # disqualified: too flaky for this series
        abs_errs = [abs(e) for _, e in errs]
        maes[name] = sum(abs_errs) / len(abs_errs)
        errors_by_model[name] = [e for _, e in errs]
    if "naive" not in maes:
        return None
    snaive_mae = maes.get("seasonal-naive", maes["naive"])
    champion = min(maes, key=maes.get)
    if champion not in models.BASELINES and maes[champion] > snaive_mae * (1 - MIN_SKILL):
        champion = "seasonal-naive" if "seasonal-naive" in maes else "naive"
    errs = sorted(errors_by_model[champion])
    err_lo = min(_quantile(errs, ERR_QUANTILES[0]), 0.0)
    err_hi = max(_quantile(errs, ERR_QUANTILES[1]), 0.0)
    return {
        "champion": champion,
        "mae": maes[champion],
        "naive_mae": maes["naive"],
        "snaive_mae": snaive_mae,
        "err_lo": err_lo,
        "err_hi": err_hi,
        "n_origins": len(errors_by_model[champion]),
        "skill": 1.0 - (maes[champion] / snaive_mae) if snaive_mae > 0 else 0.0,
    }

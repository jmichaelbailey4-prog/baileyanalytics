"""Derived series computed from raw FRED observations (post-fetch transforms)."""

from . import util


def payroll_change(raw):
    """PAYEMS (employment level, thousands) -> month-over-month change in jobs.

    Returns observations whose value is the number of jobs added/lost versus the
    prior month (level diff x 1000), as a string. The first month has no prior
    and is dropped.
    """
    out = []
    prev = None
    for obs in raw:
        v = util.to_float(obs["value"])
        if v is None:
            prev = None  # a gap breaks the chain — never diff across a missing month
            continue
        if prev is not None:
            out.append({"date": obs["date"], "value": str(round((v - prev) * 1000))})
        prev = v
    return out


def trailing_12m_deficit(raw):
    """MTSDS133FMS (monthly federal surplus/deficit, $millions, deficits negative)
    -> the trailing-12-month deficit in $trillions, positive = deficit.

    Each output point sums the 12 most recent monthly values (the monthly series
    is wildly seasonal — April runs a surplus), flips the sign so a deficit reads
    as a positive size, and rescales millions -> trillions. The first 11 months
    have no full window and are dropped; a missing month breaks the window.
    """
    values = []
    out = []
    for obs in raw:
        v = util.to_float(obs["value"])
        if v is None:
            values = []  # a gap would understate the year — restart the window
            continue
        values.append(v)
        if len(values) >= 12:
            window = sum(values[-12:])
            out.append({"date": obs["date"], "value": f"{-window / 1_000_000:.2f}"})
    return out


def yoy_pct(raw):
    """Convert a level/index series into its year-over-year % change, 1 decimal.

    For each observation, the prior value is the one dated exactly one year
    earlier (FRED monthly dates are first-of-month, so the match is exact).
    Points without a valid year-ago value are dropped — the displayed series
    is the rate of change, which is what index-level series actually mean.
    """
    by_date = {obs["date"]: util.to_float(obs["value"]) for obs in raw}
    out = []
    for obs in raw:
        v = util.to_float(obs["value"])
        if v is None:
            continue
        d = obs["date"]
        prior = by_date.get(f"{int(d[:4]) - 1}{d[4:]}")
        if prior:
            out.append({"date": d, "value": f"{(v - prior) / abs(prior) * 100:.1f}"})
    return out


def to_millions(raw):
    """Convert a level reported in thousands into millions, 1 decimal (7200 -> '7.2')."""
    out = []
    for obs in raw:
        v = util.to_float(obs["value"])
        if v is None:
            continue
        out.append({"date": obs["date"], "value": f"{v / 1000:.1f}"})
    return out


def units_to_millions(raw):
    """Convert a level reported in raw units into millions, 2 decimals (4170000 -> '4.17')."""
    out = []
    for obs in raw:
        v = util.to_float(obs["value"])
        if v is None:
            continue
        out.append({"date": obs["date"], "value": f"{v / 1_000_000:.2f}"})
    return out

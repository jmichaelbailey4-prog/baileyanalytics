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

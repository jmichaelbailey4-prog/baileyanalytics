"""Grading: match the first-observed actual, freeze the grade (spec §3).
The actual for a target is the FIRST observation dated >= target_period —
robust to holiday-shifted dates and to a skipped cron delivering two prints
(the first new print is still the one the prediction targeted)."""

from datetime import datetime, timezone

FLAT_EPS = 1e-9


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def match_actual(cleaned, target_period):
    """First (date, value) at/after target_period, or None if not yet printed.
    EIA 'YYYY-MM' and full ISO dates both compare correctly as strings within
    a series, and a series never mixes the two formats."""
    for d, v in cleaned:
        if d >= target_period:
            return (d, v)
    return None


def _direction(delta):
    if abs(delta) < FLAT_EPS:
        return "flat"
    return "up" if delta > 0 else "down"


def grade_entry(entry, actual, actual_status):
    """The frozen grade block. naive_error = what guessing the last known value
    (prev_value at made_at) would have missed by — stored so the skill stat is
    recomputable from the ledger by anyone."""
    prev = entry["prev_value"]
    return {
        "actual": actual,
        "graded_at": _now(),
        "hit": entry["lo"] <= actual <= entry["hi"],
        "abs_error": abs(actual - entry["point"]),
        "direction_hit": _direction(entry["point"] - prev) == _direction(actual - prev),
        "status_hit": entry["implied_status"] == actual_status,
        "naive_error": abs(actual - prev),
        "revised_to": None,
    }

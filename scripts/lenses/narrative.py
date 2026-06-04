"""Rule-based narrative engine. Pure functions of cleaned observations.

Each rule takes a chronological list of (date, float) tuples and returns
(text, status). Status is one of: ok, watch, elevated, alert, unknown.
"""

from . import util

_NO_DATA = ("Data unavailable.", "unknown")


def rule_yield_curve(obs):
    """T10Y2Y: inverted (<0) warns; a recent un-inversion warrants vigilance."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    recent = [val for _, val in obs[-126:]]  # ~6 months of daily data
    was_inverted = any(val < 0 for val in recent[:-1])
    if v < 0:
        return (
            f"The curve is inverted by {abs(v):.2f} points — a classic recession "
            "warning that has preceded every U.S. recession since the 1970s.",
            "elevated",
        )
    if was_inverted:
        return (
            f"The curve recently un-inverted to +{v:.2f} after an extended inversion. "
            "Recessions historically begin after the curve climbs back above zero — "
            "a reason for more vigilance, not less.",
            "watch",
        )
    return (
        f"The curve is positive (+{v:.2f}) with no recent inversion — "
        "no recession warning from the curve right now.",
        "ok",
    )


def rule_sahm(obs):
    """SAHMREALTIME: trips at 0.50; 0.35-0.50 is a warning band."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 0.50:
        return (
            f"The Sahm rule has triggered at {v:.2f}, historically consistent with "
            "a recession already underway.",
            "alert",
        )
    if v >= 0.35:
        return (
            f"The Sahm rule is at {v:.2f}, climbing toward its 0.50 recession "
            "trigger but not there yet.",
            "watch",
        )
    return (f"The Sahm rule is at {v:.2f}, well below its 0.50 recession trigger.", "ok")


def rule_claims(obs):
    """ICSA (weekly level): <250k low, 250-300k creeping, >=300k elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    k = v / 1000
    if v < 250000:
        return (
            f"Initial jobless claims are low at ~{k:.0f}k — employers aren't "
            "shedding workers.",
            "ok",
        )
    if v < 300000:
        return (f"Jobless claims at ~{k:.0f}k are creeping up from their lows.", "watch")
    return (
        f"Jobless claims have risen to ~{k:.0f}k, a sign of accelerating layoffs.",
        "elevated",
    )


def rule_unemployment_trend(obs):
    """UNRATE: a rise of >=0.5pts above the trailing 12-month low is a warning."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    window = [val for _, val in obs[-12:]]
    low = min(window)
    delta = v - low
    if delta >= 0.5:
        return (
            f"Unemployment at {v:.1f}% is up {delta:.1f} points from its recent low — "
            "the kind of rise that has preceded past downturns.",
            "watch",
        )
    return (f"Unemployment is steady at {v:.1f}%, near its recent lows.", "ok")

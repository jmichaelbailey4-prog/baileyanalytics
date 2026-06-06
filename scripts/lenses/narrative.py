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
    if v < 250000:
        return (
            f"Initial jobless claims are low at {v:,.0f} — employers aren't "
            "shedding workers.",
            "ok",
        )
    if v < 300000:
        return (f"Jobless claims at {v:,.0f} are creeping up from their lows.", "watch")
    return (
        f"Jobless claims have risen to {v:,.0f}, a sign of accelerating layoffs.",
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


def _value_year_ago(obs):
    """Value from ~one year before the latest observation (frequency-agnostic)."""
    last_date = obs[-1][0]
    target = f"{int(last_date[:4]) - 1}{last_date[4:]}"
    chosen = obs[0][1]
    for d, val in obs:
        if d <= target:
            chosen = val
        else:
            break
    return chosen


def rule_fed_funds(obs):
    """FEDFUNDS: the policy-rate level and its ~12-month direction."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    delta = v - _value_year_ago(obs)
    if delta >= 0.25:
        stance = "and still climbing as the Fed leans against inflation"
    elif delta <= -0.25:
        stance = "and easing as the Fed pivots toward cuts"
    else:
        stance = "holding roughly steady as the Fed waits for more data"
    status = "watch" if v >= 4.0 else "ok"
    return (f"The Fed's policy rate is {v:.2f}%, {stance}.", status)


def rule_rate_trend(obs):
    """Generic market-rate read: current level and ~12-month direction."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    delta = v - _value_year_ago(obs)
    if delta >= 0.1:
        move = f"up {delta:.2f} points over the past year"
    elif delta <= -0.1:
        move = f"down {abs(delta):.2f} points over the past year"
    else:
        move = "little changed over the past year"
    return (f"Now {v:.2f}%, {move}.", "ok")


def rule_mortgage(obs):
    """MORTGAGE30US: the rate level plus an affordability read."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 6.5:
        return (f"30-year mortgages are at {v:.2f}%, keeping home affordability stretched.", "watch")
    return (f"30-year mortgages are at {v:.2f}%, moderate by recent standards.", "ok")


def rule_payrolls(obs):
    """Monthly change in nonfarm payrolls (jobs added or lost)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0:
        return (f"Employers cut {abs(v):,.0f} jobs last month — an outright contraction.", "alert")
    if v < 75000:
        return (f"Employers added just {v:,.0f} jobs last month — hiring has slowed sharply.", "watch")
    if v < 150000:
        return (f"Employers added {v:,.0f} jobs last month — a cooler but still-positive pace.", "watch")
    return (f"Employers added {v:,.0f} jobs last month — a healthy clip.", "ok")


def rule_job_openings(obs):
    """JTSJOL in millions: how hungry employers are to hire."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if v < prior - 0.3:
        trend = "easing as labor demand cools"
    elif v > prior + 0.3:
        trend = "rising as employers compete for workers"
    else:
        trend = "holding roughly steady"
    status = "watch" if v < 7.5 else "ok"
    return (f"{v:.1f} million open jobs, {trend}.", status)


def rule_wage_growth(obs):
    """Average hourly earnings, year-over-year percent."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    pace = "running ahead of recent inflation" if v >= 3.5 else "a modest pace"
    return (f"Pay is up {v:.1f}% from a year ago, {pace}.", "ok")


HEADLINES = {
    "recession-watch": {
        "alert": "Recession signals are flashing — multiple indicators have tripped.",
        "elevated": "Recession risk is elevated — the yield curve is warning.",
        "watch": "No recession underway — but the warning lights are no longer all green.",
        "ok": "The economy looks steady — no major recession signals right now.",
        "unknown": "Some recession signals are temporarily unavailable.",
    },
    "cost-of-money": {
        "alert": "Borrowing costs are extreme — money is very expensive.",
        "elevated": "Borrowing costs are high and restrictive across the board.",
        "watch": "Borrowing is still expensive — rates remain elevated.",
        "ok": "Borrowing costs have eased back toward normal.",
        "unknown": "Some rate data is temporarily unavailable.",
    },
    "job-market": {
        "alert": "The job market is contracting — employers are cutting jobs.",
        "elevated": "The job market is weakening on several fronts.",
        "watch": "The job market is cooling — still solid, but losing momentum.",
        "ok": "The job market is healthy — hiring and pay are holding up.",
        "unknown": "Some labor-market data is temporarily unavailable.",
    },
}


def synthesize(lens_id, statuses):
    """Combine indicator statuses into (headline_read, overall_status)."""
    overall = util.status_max(statuses)
    headline = HEADLINES.get(lens_id, {}).get(overall, "")
    return headline, overall

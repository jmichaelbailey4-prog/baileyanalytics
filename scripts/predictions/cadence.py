"""Cadence inference + target/due dates. Dates are ISO strings throughout
(EIA monthly uses 'YYYY-MM'). Daily series are resampled to weekly (last
observation of each ISO week, dated that week's Friday) — predicting tomorrow
on a daily series is churn without insight (spec §2)."""

from datetime import date, timedelta

SEASON = {"weekly": 52, "monthly": 12, "quarterly": 4, "annual": 1, "daily": 52}
PERIOD_NOUN = {"weekly": "week", "monthly": "month", "quarterly": "quarter", "daily": "week"}


def _parse(d):
    parts = d.split("-")
    if len(parts) == 2:  # EIA "YYYY-MM"
        return date(int(parts[0]), int(parts[1]), 1)
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def infer(obs):
    """Cadence from the median gap of the last ~12 observations."""
    if len(obs) < 3:
        return "unknown"
    dates = [_parse(d) for d, _ in obs[-13:]]
    gaps = sorted((b - a).days for a, b in zip(dates, dates[1:]))
    med = gaps[len(gaps) // 2]
    if med <= 4:
        return "daily"
    if med <= 10:
        return "weekly"
    if med <= 45:
        return "monthly"
    if med <= 130:
        return "quarterly"
    return "annual"


def weekly_resample(obs):
    """[(date,val)] daily -> last obs per ISO week, dated that week's Friday."""
    out, cur_week, cur = [], None, None
    for d, v in obs:
        dt = _parse(d)
        wk = dt.isocalendar()[:2]
        if wk != cur_week:
            if cur is not None:
                out.append(cur)
            cur_week = wk
        friday = dt + timedelta(days=5 - dt.isocalendar()[2])  # ISO weekday: Fri = 5
        cur = (friday.isoformat(), v)
    if cur is not None:
        out.append(cur)
    return out


def _is_yyyy_mm(d):
    return len(d) == 7


def next_period(last_date, cad):
    dt = _parse(last_date)
    if cad in ("weekly", "daily"):
        return (dt + timedelta(days=7)).isoformat()
    months = 3 if cad == "quarterly" else 1
    y, m = dt.year, dt.month + months
    if m > 12:
        y, m = y + 1, m - 12
    return f"{y:04d}-{m:02d}" if _is_yyyy_mm(last_date) else f"{y:04d}-{m:02d}-01"


def due_estimate(target_period, cad):
    """Approximate release date — rendered with '~' by the UI (no fake precision)."""
    dt = _parse(target_period)
    if cad in ("weekly", "daily"):
        return (dt + timedelta(days=5)).isoformat()
    if cad == "quarterly":
        y, m = (dt.year + 1, dt.month - 9) if dt.month + 3 > 12 else (dt.year, dt.month + 3)
        return f"{y:04d}-{m:02d}-28"
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return f"{y:04d}-{m:02d}-15"

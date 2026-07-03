"""Small pure helpers shared across the pipeline."""

from datetime import date, datetime

STATUS_ORDER = {"unknown": -1, "ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def oxford_join(items):
    """Oxford-comma list join: a / a and b / a, b, and c. The single home for the
    grammar shared by state.py (verdict sentence) and synthesis.py (co-occurrence)."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def human_date(iso_date, short=False):
    """'YYYY-MM-DD' -> 'June 12, 2026' (short=False) or 'Jun 12, 2026' (short=True).
    Locale-independent and Windows-safe (no %-d / %e). The single source of date
    formatting for the brief page and the email digest."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    month = dt.strftime("%b") if short else dt.strftime("%B")
    return f"{month} {dt.day}, {dt.year}"


def thin_observations(raw_observations, keep_years=2, monthly_after_years=5,
                      quarterly_after_years=15):
    """Shrink a published series: keep every point in the trailing `keep_years`
    window, thin to one per ISO week out to `monthly_after_years`, one per
    calendar month out to `quarterly_after_years`, and one per quarter beyond
    that. Weekly and slower cadences pass through the weekly tier unchanged;
    monthly and slower pass through it too; quarterly and slower pass through
    every tier.

    Rules only look back ~1 year from the latest point, so they are unaffected.
    This thins only the *published* JSON — sources retain full history, so
    nothing is lost for future modeling work. The quarterly tier (added
    2026-07-03 with the percentile-context fetch-depth raises) keeps decades of
    Max-chart history to a bounded payload.
    """
    if not raw_observations:
        return raw_observations
    last = raw_observations[-1]["date"]
    weekly_boundary = f"{int(last[:4]) - keep_years}{last[4:]}"
    monthly_boundary = f"{int(last[:4]) - monthly_after_years}{last[4:]}"
    quarterly_boundary = f"{int(last[:4]) - quarterly_after_years}{last[4:]}"
    out, seen_weeks, seen_months, seen_quarters = [], set(), set(), set()
    for obs in raw_observations:
        if obs["date"] >= weekly_boundary:
            out.append(obs)
            continue
        parts = obs["date"].split("-")
        if len(parts) < 3:  # EIA monthly periods are "YYYY-MM" — monthly never thins
            out.append(obs)
            continue
        if obs["date"] < quarterly_boundary:
            quarter = (parts[0], (int(parts[1]) - 1) // 3)
            if quarter not in seen_quarters:
                seen_quarters.add(quarter)
                out.append(obs)
            continue
        if obs["date"] < monthly_boundary:
            month = (parts[0], parts[1])
            if month not in seen_months:
                seen_months.add(month)
                out.append(obs)
            continue
        week = date(int(parts[0]), int(parts[1]), int(parts[2])).isocalendar()[:2]
        if week not in seen_weeks:
            seen_weeks.add(week)
            out.append(obs)
    return out


def percentile_context(cleaned, min_points=40):
    """Where the latest reading sits in the series' own fetched history:
    {"p": 0-100 (share of past readings strictly below the latest, 1dp),
     "since": first year} — or None when history is too short to be honest.
    Computed on the full pre-thin series, so `since` matches the Max chart."""
    if len(cleaned) < min_points:
        return None
    latest = cleaned[-1][1]
    below = sum(1 for _, v in cleaned if v < latest)
    return {"p": round(100.0 * below / len(cleaned), 1),
            "since": int(cleaned[0][0][:4])}


def to_float(value):
    """Parse a FRED value string to float, or None for missing values ('.', None)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean(raw_observations):
    """Convert raw [{'date','value'}] into chronological [(date, float)], dropping nulls."""
    out = []
    for obs in raw_observations:
        f = to_float(obs.get("value"))
        if f is not None:
            out.append((obs["date"], f))
    return out


def status_max(statuses):
    """Return the most severe status; 'unknown' only if nothing else is present."""
    known = [s for s in statuses if s in STATUS_ORDER and s != "unknown"]
    if not known:
        return "unknown"
    return max(known, key=lambda s: STATUS_ORDER[s])


def status_score(statuses):
    """The un-banded severity behind status_blend: the quadratic mean (RMS) of
    the severity values, ignoring neutral/info/unknown. None when nothing
    severity-graded is present."""
    sev = [STATUS_ORDER[s] for s in statuses if STATUS_ORDER.get(s, -1) >= 0]
    if not sev:
        return None
    return (sum(v * v for v in sev) / len(sev)) ** 0.5


def status_blend(statuses):
    """Category-level status: the quadratic mean (RMS) of lens severities, banded
    back to a token. Squaring makes bad readings count more than good ones offset,
    without letting a single stressed lens brand the whole category (that's the
    worst-lens callout's job on the home tile). One watch among four ok lenses
    stays ok (0.5 < 0.6); a category reads alert only when stress is broad
    (e.g. alert+alert+elevated+elevated ≈ 2.55). neutral/info/unknown are
    excluded; with no severity lenses at all the category is 'neutral'."""
    score = status_score(statuses)
    if score is None:
        return "neutral"
    if score < 0.6:
        return "ok"
    if score < 1.5:
        return "watch"
    if score < 2.5:
        return "elevated"
    return "alert"


def merge_series(old, new):
    """Merge two [{'date','value'}] lists by date; `new` wins on conflicts. Sorted.

    Used to accumulate crypto history across daily refreshes so it grows past
    CoinGecko's free 365-day window: today's recomputed points refresh the recent
    window, while older points beyond the window persist from prior runs.
    """
    merged = {p["date"]: p["value"] for p in (old or [])}
    for p in (new or []):
        merged[p["date"]] = p["value"]
    return [{"date": d, "value": merged[d]} for d in sorted(merged)]


def spread_ffill(minuend, subtrahend):
    """a - b on a's dates, forward-filling b (e.g. a daily yield minus a monthly
    policy rate). Skips a-dates before b begins and missing values on either
    side. Returns [{'date','value'}] with 2-dp string values, sorted by date."""
    if not minuend or not subtrahend:
        return []
    b = sorted((p["date"], to_float(p["value"])) for p in subtrahend)
    out, bi, last_b = [], 0, None
    for p in sorted(minuend, key=lambda r: r["date"]):
        a = to_float(p["value"])
        while bi < len(b) and b[bi][0] <= p["date"]:
            if b[bi][1] is not None:
                last_b = b[bi][1]
            bi += 1
        if a is None or last_b is None:
            continue
        out.append({"date": p["date"], "value": f"{a - last_b:.2f}"})
    return out


def pct_share(numerator, denominator):
    """Percent share (numerator / denominator * 100) on dates present in both.

    Inputs are [{'date','value'}] (values numeric or numeric strings). Returns
    [{'date','value'}] with the share rounded to 1 dp as a string, sorted by date.
    Skips dates where the denominator is missing or zero.
    """
    den = {p["date"]: to_float(p["value"]) for p in (denominator or [])}
    out = []
    for p in (numerator or []):
        d = den.get(p["date"])
        n = to_float(p["value"])
        if n is not None and d:
            out.append({"date": p["date"], "value": f"{n / d * 100:.1f}"})
    return sorted(out, key=lambda r: r["date"])

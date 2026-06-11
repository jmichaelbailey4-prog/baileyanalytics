"""Small pure helpers shared across the pipeline."""

from datetime import date

STATUS_ORDER = {"unknown": -1, "ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def thin_observations(raw_observations, keep_years=2):
    """Shrink a published series: keep every point in the trailing `keep_years`
    window, thin older points to one per ISO week (the first observation of
    each week). Daily series shed ~80% of their old points; weekly and slower
    cadences pass through unchanged, since at most one point falls in a week.

    Rules only look back ~1 year from the latest point, so they are unaffected.
    """
    if not raw_observations:
        return raw_observations
    last = raw_observations[-1]["date"]
    boundary = f"{int(last[:4]) - keep_years}{last[4:]}"
    out, seen_weeks = [], set()
    for obs in raw_observations:
        if obs["date"] >= boundary:
            out.append(obs)
            continue
        parts = obs["date"].split("-")
        if len(parts) < 3:  # EIA monthly periods are "YYYY-MM" — monthly never thins
            out.append(obs)
            continue
        week = date(int(parts[0]), int(parts[1]), int(parts[2])).isocalendar()[:2]
        if week not in seen_weeks:
            seen_weeks.add(week)
            out.append(obs)
    return out


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


def status_blend(statuses):
    """Category-level status: the quadratic mean (RMS) of lens severities, banded
    back to a token. Squaring makes bad readings count more than good ones offset,
    without letting a single stressed lens brand the whole category (that's the
    worst-lens callout's job on the home tile). One watch among four ok lenses
    stays ok (0.5 < 0.6); a category reads alert only when stress is broad
    (e.g. alert+alert+elevated+elevated ≈ 2.55). neutral/info/unknown are
    excluded; with no severity lenses at all the category is 'neutral'."""
    sev = [STATUS_ORDER[s] for s in statuses if STATUS_ORDER.get(s, -1) >= 0]
    if not sev:
        return "neutral"
    score = (sum(v * v for v in sev) / len(sev)) ** 0.5
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

"""Small pure helpers shared across the pipeline."""

STATUS_ORDER = {"unknown": -1, "ok": 0, "watch": 1, "elevated": 2, "alert": 3}


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

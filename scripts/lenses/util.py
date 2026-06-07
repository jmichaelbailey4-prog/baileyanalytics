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

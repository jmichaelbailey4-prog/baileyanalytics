"""Cross-category 'Today's Brief': diff lens statuses for transitions and rank
the most significant moves. Pure synthesis over already-built index.json data —
no network, no disk I/O (callers pass data in and get data out)."""

# Severity ladder for transition direction. Mirrors the home page's SEVERITY
# (index.html) and util.STATUS_ORDER; neutral/info/unknown are intentionally
# absent — only these four can "transition".
SEVERITY = {"ok": 0, "watch": 1, "elevated": 2, "alert": 3}


def pct_change(sparkline):
    """Signed percent change of the last point vs the one before it, or None when
    there are <2 points or the prior value is zero. The sparkline already carries
    the primary indicator's raw numeric series (build.build_index)."""
    if not sparkline or len(sparkline) < 2:
        return None
    prior, latest = sparkline[-2], sparkline[-1]
    if prior == 0:
        return None
    return (latest - prior) / prior * 100.0

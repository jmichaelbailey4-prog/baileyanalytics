"""Convert the USREC indicator (1 = in recession) into date ranges for shading."""

from . import util


def recession_periods(usrec_obs):
    """Return [{'start','end'}] periods where USREC == 1 (chronological input)."""
    periods = []
    start = None
    last_date = None
    for obs in usrec_obs:
        v = util.to_float(obs.get("value"))
        if v is None:
            continue
        last_date = obs["date"]
        if v >= 0.5 and start is None:
            start = obs["date"]
        elif v < 0.5 and start is not None:
            periods.append({"start": start, "end": obs["date"]})
            start = None
    if start is not None and last_date is not None:
        periods.append({"start": start, "end": last_date})
    return periods

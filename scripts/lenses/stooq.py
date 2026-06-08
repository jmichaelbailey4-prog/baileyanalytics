"""Stooq API access — free, no-key daily price history for instruments FRED doesn't
serve. Currently used only for gold (XAUUSD), after FRED dropped its LBMA gold series.

Stooq is a long-running free financial-data aggregator (not an official source); the
refresh pipeline treats a failed fetch as non-fatal and keeps prior data.
"""

import urllib.request

GOLD_URL = "https://stooq.com/q/d/l/?s=xauusd&i=d"


def gold_history(limit=2600, timeout=15):
    """Daily gold (XAUUSD) price history: [{'date','value'}], oldest-first.

    Returns the most recent `limit` rows (~10 years of trading days) to match the
    depth of the FRED-sourced scoreboard series. Values are kept as strings (FRED
    style); rows without a numeric close (e.g. Stooq's "N/D") are skipped.
    """
    with urllib.request.urlopen(GOLD_URL, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
    out = []
    for line in text.strip().splitlines()[1:]:  # skip the Date,Open,... header
        parts = line.split(",")
        if len(parts) < 5:
            continue
        date, close = parts[0], parts[4]
        try:
            float(close)
        except ValueError:
            continue
        out.append({"date": date, "value": close})
    return out[-limit:] if limit else out

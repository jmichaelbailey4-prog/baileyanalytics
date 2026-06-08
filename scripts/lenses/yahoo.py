"""Yahoo Finance chart API — free, no-key daily price history for instruments FRED
doesn't serve. Currently used only for gold (GC=F, COMEX continuous futures), after
FRED dropped its LBMA gold series and Stooq's CSV endpoint went behind a JS bot-check.

Needs a browser User-Agent or Yahoo returns 401/429. A failed fetch is treated as
non-fatal upstream (refresh_markets falls back to prior gold data).
"""

import json
import time
import urllib.request

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
GOLD_SYMBOL = "GC=F"


def _chart(symbol, rng, interval, timeout):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?range={rng}&interval={interval}")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def gold_history(rng="10y", timeout=15):
    """Daily gold (GC=F) price history: [{'date','value'}], oldest-first.

    `range=10y` returns ~10 years of trading days, matching the depth of the
    FRED-sourced scoreboard series. Values are kept as strings (FRED style); days
    with a null close (Yahoo gaps) are skipped.
    """
    data = _chart(GOLD_SYMBOL, rng, "1d", timeout)
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return []
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    out = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        d = time.strftime("%Y-%m-%d", time.gmtime(ts))
        out.append({"date": d, "value": f"{close:.2f}"})
    return out

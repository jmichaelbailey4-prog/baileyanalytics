"""EIA API v2 access — energy data (the physical economy). Mirrors fred.py.

Returns the same oldest-first [{'date','value'}] shape FRED returns, so the
existing build pipeline consumes it unchanged. Only this module (plus fred /
fdic / coingecko / yahoo) touches the network. Values are stored as strings to
match FRED's convention; display precision is handled by each indicator's
value_format.
"""

import json
import urllib.parse
import urllib.request

BASE = "https://api.eia.gov/v2"

# Net-generation dataset (monthly, all-sector) used for the electricity mix.
# fueltypeid facets: ALL = total, REN = renewables, NG = natural gas.
_GEN_ROUTE = "electricity/electric-power-operational-data"
_GEN_FACETS = {"total": "ALL", "renewable": "REN", "natgas": "NG"}
_GEN_COL = "generation"


def fetch_series(route, facets, frequency, api_key, length=520, data_col="value", timeout=20):
    """Fetch one EIA v2 series as oldest-first [{'date','value'}].

    facets: iterable of (key, value) -> facets[key][]=value. Values are kept as
    strings (str()) to match FRED; null values are dropped.
    """
    params = [
        ("api_key", api_key),
        ("frequency", frequency),
        ("data[0]", data_col),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", length),
    ]
    for k, v in facets:
        params.append((f"facets[{k}][]", v))
    url = f"{BASE}/{route}/data/?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    rows = payload.get("response", {}).get("data", [])
    out = []
    for r in rows:
        val = r.get(data_col)
        if val is None:
            continue
        out.append({"date": r["period"], "value": str(val)})
    out.reverse()  # API returns newest-first
    return out


def generation_mix(api_key, timeout=20):
    """Fetch monthly net generation for total / renewable / natural-gas as a dict
    of oldest-first [{'date','value'}] series. The caller computes shares."""
    out = {}
    for name, fuel in _GEN_FACETS.items():
        out[name] = fetch_series(
            _GEN_ROUTE,
            [("fueltypeid", fuel), ("location", "US"), ("sectorid", "99")],
            "monthly", api_key, length=240, data_col=_GEN_COL, timeout=timeout)
    return out

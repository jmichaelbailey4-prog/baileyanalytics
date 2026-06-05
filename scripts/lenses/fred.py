"""FRED API access — the only module that touches the network."""

import json
import urllib.parse
import urllib.request

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def fetch_observations(series_id, api_key, limit, units=None, timeout=15):
    """Fetch the most recent `limit` observations, returned oldest-first.

    Returns a list of {"date", "value"} dicts (values are raw strings, may be ".").
    """
    params = {
        "series_id": series_id,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
        "api_key": api_key,
    }
    if units:
        params["units"] = units
    url = f"{FRED_BASE}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read())
    observations = [
        {"date": o["date"], "value": o["value"]}
        for o in payload.get("observations", [])
    ]
    observations.reverse()
    return observations

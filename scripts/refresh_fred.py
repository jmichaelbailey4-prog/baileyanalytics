#!/usr/bin/env python3
"""Fetch FRED series and write to data/economic.json for the dashboard."""

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
import urllib.parse
import urllib.request

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES = [
    {
        "id": "UNRATE",
        "title": "Unemployment Rate",
        "subtitle": "Monthly, Seasonally Adjusted",
        "unit": "%",
        "limit": 120,
        "color": "#38BDF8",
    },
    {
        "id": "DGS10",
        "title": "10-Year Treasury Yield",
        "subtitle": "Daily",
        "unit": "%",
        "limit": 520,
        "color": "#34D399",
    },
]


def fetch_series(series_id: str, limit: int, api_key: str) -> list[dict]:
    """Fetch the most recent `limit` observations, returned in chronological order."""
    params = urllib.parse.urlencode({
        "series_id": series_id,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
        "api_key": api_key,
    })
    url = f"{FRED_BASE}?{params}"
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.loads(response.read())
    observations = [
        {"date": obs["date"], "value": obs["value"]}
        for obs in payload.get("observations", [])
        if obs.get("value") not in (None, ".")
    ]
    observations.reverse()
    return observations


def main() -> int:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("FRED_API_KEY not set", file=sys.stderr)
        return 1

    series_data = {}
    for series in SERIES:
        try:
            observations = fetch_series(series["id"], series["limit"], api_key)
        except Exception as exc:
            print(f"Failed to fetch {series['id']}: {exc}", file=sys.stderr)
            return 2

        series_data[series["id"]] = {
            "title": series["title"],
            "subtitle": series["subtitle"],
            "unit": series["unit"],
            "color": series["color"],
            "observations": observations,
        }

    output = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Federal Reserve Economic Data (FRED), St. Louis Fed",
        "series": series_data,
    }

    out_path = Path(__file__).resolve().parent.parent / "data" / "economic.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

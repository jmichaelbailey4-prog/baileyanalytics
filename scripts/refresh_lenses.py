#!/usr/bin/env python3
"""Fetch FRED data for all lenses and write data/lenses/*.json.

Usage:
  python scripts/refresh_lenses.py            # live (needs FRED_API_KEY)
  python scripts/refresh_lenses.py --dry-run  # offline, uses test fixture data
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `lenses` importable
from lenses import build, config, fred

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "lenses"
FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fetched_sample.json"


def unique_specs(lenses):
    """Map fetch_key -> (series_id, units_transform, max_limit) across all lenses."""
    specs = {}
    for lens in lenses:
        for ind in lens.indicators:
            cur = specs.get(ind.fetch_key)
            limit = ind.limit if cur is None else max(cur[2], ind.limit)
            specs[ind.fetch_key] = (ind.series_id, ind.units_transform, limit)
    return specs


def fetch_all(lenses, api_key):
    """Fetch every needed series once. Returns (fetched, failed_keys)."""
    fetched, failed = {}, set()
    for key, (series_id, units, limit) in unique_specs(lenses).items():
        try:
            fetched[key] = fred.fetch_observations(series_id, api_key, limit, units)
        except Exception as exc:  # noqa: BLE001 - keep going, skip dependent lenses
            print(f"WARN: fetch failed for {series_id}: {exc}", file=sys.stderr)
            failed.add(key)
    if config.USREC_KEY not in fetched:
        try:
            fetched[config.USREC_KEY] = fred.fetch_observations("USREC", api_key, config.USREC_LIMIT)
        except Exception as exc:  # noqa: BLE001 - shading is non-critical
            print(f"WARN: USREC fetch failed: {exc}", file=sys.stderr)
            fetched[config.USREC_KEY] = []
    return fetched, failed


def lens_ready(lens, failed):
    return not any(ind.fetch_key in failed for ind in lens.indicators)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    args = parser.parse_args(argv)

    if args.dry_run:
        fetched = json.loads(FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.LENSES, api_key)

    ready = [lens for lens in config.LENSES if lens_ready(lens, failed)]
    for lens in config.LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No lenses could be built", file=sys.stderr)
        return 2

    lens_jsons = [build.build_lens(lens, fetched) for lens in ready]
    written = build.write_outputs(lens_jsons, OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all lens data up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

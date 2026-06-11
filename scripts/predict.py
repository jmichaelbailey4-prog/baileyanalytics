#!/usr/bin/env python3
"""Predictions CLI — runs alongside refresh_lenses.py, never inside it.

Usage:
  python scripts/predict.py tournament            # weekly: backtest + pick champions
  python scripts/predict.py daily                 # daily: grade -> footnote -> predict
  python scripts/predict.py daily --dry-run       # fixtures, no network
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make packages importable

from predictions import roster, runner  # noqa: E402

PRED_DIR = Path(__file__).resolve().parent.parent / "data" / "predictions"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prediction pipeline.")
    parser.add_argument("job", choices=["daily", "tournament"])
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    args = parser.parse_args(argv)
    entries = roster.build_roster()
    if args.dry_run:
        import json
        keys = set(json.loads(runner.FIXTURE.read_text(encoding="utf-8")))
        entries = [e for e in entries if e.key in keys]
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    if args.job == "tournament":
        n = runner.run_tournament(PRED_DIR, args.dry_run, entries)
        print(f"tournament complete: {n} champions")
        return 0 if n else 1
    runner.run_daily(PRED_DIR, args.dry_run, entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())

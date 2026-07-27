#!/usr/bin/env python3
"""Send the weekly roundup email via the Buttondown API.

Runs on its own Friday workflow (.github/workflows/weekly-digest.yml). Reads
only committed data — the daily refresh has already written the week's brief
snapshots to data/brief/days/ — and writes nothing back to the repo.

Decision chain (each exit is quiet and exit-code 0 except a real API failure,
which exits 1 so the step shows red):
  1. no publication day in the window -> skip (quiet week; never an empty email)
  2. no BUTTONDOWN_API_KEY            -> skip (forks, local runs)
  3. Buttondown already has this week -> skip (backup cron / rerun)
  4. POST the roundup, scheduled for 11:00 UTC (~7am ET), or now+5min if a
     catch-up run is already past 11:00

Usage: python scripts/send_weekly_digest.py [--dry-run] [--date YYYY-MM-DD]

The window is the 7 days ENDING on --date (default: today UTC). The cron makes
that a Friday in production; a manual dispatch on any other day therefore sends
an honest trailing-7-day roundup rather than re-sending a stale Friday.
"""

import json
import os
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lenses import buttondown, weekly_digest

BRIEF_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"
DAYS_DIR = BRIEF_DIR / "days"


def target_day(argv):
    """The day the window ends on: --date if given, else today (UTC)."""
    if "--date" in argv:
        return argv[argv.index("--date") + 1]
    return datetime.now(timezone.utc).date().isoformat()


def load_week(days_dir, end_iso, span=weekly_digest.WINDOW_DAYS):
    """The window's brief snapshots, chronological. A day file exists iff that
    day was a publication day, so this doubles as the publication gate: an empty
    list is a quiet week. An unreadable file is skipped rather than fatal — one
    corrupt snapshot must not cost the whole week's email."""
    days = []
    for date in weekly_digest.window_dates(end_iso, span):
        path = Path(days_dir) / f"{date}.json"
        try:
            days.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            if path.exists():
                print(f"Skipping unreadable {path.name} ({exc}).", file=sys.stderr)
    return days


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    dry_run = "--dry-run" in argv
    end_iso = target_day(argv)

    days = load_week(DAYS_DIR, end_iso)
    built = weekly_digest.build_weekly(days, end_iso=end_iso)
    if not built:
        print(f"No published briefs in the week ending {end_iso} — no email.")
        return 0

    if dry_run:
        buttondown.print_preview(built["subject"], built["html"])
        return 0

    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("BUTTONDOWN_API_KEY not set — skipping weekly send.")
        return 0

    token = weekly_digest.subject_token(end_iso)
    try:
        if buttondown.already_sent(buttondown.list_emails(api_key), token):
            print(f"'{token}' already exists on Buttondown — skipping.")
            return 0
        created = buttondown.create_scheduled(
            api_key, built["subject"], built["html"],
            buttondown.publish_at(end_iso, buttondown.now_iso()))
        print(f"Weekly roundup scheduled: {created.get('id', '?')} — {built['subject']}")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"ERROR: Buttondown API {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}",
              file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: weekly send failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Send ONE day's brief as an email via the Buttondown API.

NOTE (2026-07-27): the shipped subscriber cadence is WEEKLY — see
scripts/send_weekly_digest.py and .github/workflows/weekly-digest.yml. No
workflow schedules this script any more; it stays as the manual one-off sender
for a mid-week event worth its own email (run it locally with a key, or wire it
to a workflow_dispatch).

Decision chain (each exit is quiet and exit-code 0 except a real API failure,
which exits 1 so the step shows red):
  1. no BUTTONDOWN_API_KEY            -> skip (forks, local runs)
  2. today isn't a publication day    -> skip (quiet day; manifest has no entry)
  3. Buttondown already has today's   -> skip (rerun)
  4. POST the digest, scheduled for 11:00 UTC (~7am ET), or now+5min if a
     catch-up run is already past 11:00 (never exactly "now" — Buttondown
     rejects a scheduled publish_date that isn't safely in the future)

Usage: python scripts/send_digest.py [--dry-run]
"""

import json
import os
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lenses import buttondown, digest

# Re-exported so existing callers and tests keep one import surface; the logic
# now lives in lenses/buttondown.py, shared with the weekly sender.
publish_at = buttondown.publish_at
already_sent = buttondown.already_sent

BRIEF_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"


def should_send(manifest, day):
    """Publication-day gate: the --brief pass appended today to the manifest
    iff the brief's content changed today."""
    return any(e.get("date") == day for e in manifest or [])


def main(argv=None):
    dry_run = "--dry-run" in (argv or sys.argv[1:])

    # A missing or corrupt today.json is a quiet skip, not a red step — the
    # send is always downstream of a brief build that may not have produced one.
    try:
        today = json.loads((BRIEF_DIR / "today.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"No readable today.json ({exc}) — skipping digest.", file=sys.stderr)
        return 0
    day = (today.get("generated_at") or "1970-01-01")[:10]
    built = digest.build_digest(today)

    if dry_run:
        buttondown.print_preview(built["subject"], built["html"])
        return 0

    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("BUTTONDOWN_API_KEY not set — skipping digest send.")
        return 0

    try:
        manifest = json.loads((BRIEF_DIR / "_archive_index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = []
    if not should_send(manifest, day):
        print(f"No publication entry for {day} — quiet day, no email.")
        return 0

    token = digest.date_token(day)
    try:
        if already_sent(buttondown.list_emails(api_key), token):
            print(f"Digest for {token} already exists on Buttondown — skipping.")
            return 0
        created = buttondown.create_scheduled(
            api_key, built["subject"], built["html"],
            publish_at(day, buttondown.now_iso()))
        print(f"Digest scheduled: {created.get('id', '?')} — {built['subject']}")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"ERROR: Buttondown API {exc.code}: {exc.read().decode('utf-8', 'replace')[:500]}",
              file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: digest send failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Send Today's Brief as an email via the Buttondown API.

Runs as a workflow step after the --brief pass. Decision chain (each exit is
quiet and exit-code 0 except a real API failure, which exits 1 so the step
shows red):
  1. no BUTTONDOWN_API_KEY            -> skip (forks, local runs)
  2. today isn't a publication day    -> skip (quiet day; manifest has no entry)
  3. Buttondown already has today's   -> skip (backup cron / rerun)
  4. POST the digest, scheduled for max(now, 11:00 UTC)  (~7am ET)

Usage: python scripts/send_digest.py [--dry-run]
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lenses import digest

API = "https://api.buttondown.com/v1/emails"
# Explicit newest-first ordering so the already-sent dedup check reliably sees
# today's email (sent minutes/hours earlier) on the first page, regardless of
# Buttondown's default sort. The archive-manifest publication gate is the
# primary guard; this is the backstop against a same-day duplicate send.
LIST_URL = API + "?ordering=-creation_date"
BRIEF_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"


def should_send(manifest, day):
    """Publication-day gate: the --brief pass appended today to the manifest
    iff the brief's content changed today."""
    return any(e.get("date") == day for e in manifest or [])


def already_sent(emails_json, token):
    """True if any recent Buttondown email's subject carries today's date token
    (every digest subject ends with it — see digest.date_token)."""
    return any(token in (e.get("subject") or "")
               for e in (emails_json or {}).get("results", []))


def publish_at(day, now_iso):
    """Schedule for 11:00 UTC (~7am ET); if we're already past it (the 13:00
    backup cron catching up), send immediately."""
    target = f"{day}T11:00:00Z"
    return now_iso if now_iso > target else target


def _request(url, api_key, payload=None):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Token {api_key}",
                      "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8") if payload else None,
        method="POST" if payload else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


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
        print("SUBJECT:", built["subject"])
        print(built["html"])
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
        if already_sent(_request(LIST_URL, api_key), token):
            print(f"Digest for {token} already exists on Buttondown — skipping.")
            return 0
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {"subject": built["subject"], "body": built["html"],
                   "status": "scheduled", "publish_date": publish_at(day, now_iso)}
        created = _request(API, api_key, payload)
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

"""Buttondown API client — the only outbound-email code in the pipeline.

Shared by the (unscheduled) daily sender and the weekly roundup sender so the
scheduling and duplicate-send guards exist once. Stdlib only.
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.buttondown.com/v1/emails"
# Explicit newest-first ordering so the already-sent dedup check reliably sees
# a just-scheduled email on the first page, regardless of Buttondown's default
# sort. The publication gate is the primary guard; this is the backstop against
# a backup-cron duplicate.
LIST_URL = API + "?ordering=-creation_date"

# A catch-up run (backup cron / manual dispatch past the target hour) must not
# schedule at exactly "now": Buttondown 400s ("publish date is in the past") a
# scheduled email whose publish_date isn't comfortably in the future by the time
# the request lands. Push it a few minutes out instead.
SEND_BUFFER = timedelta(minutes=5)
SEND_HOUR_UTC = "11:00:00"  # ~7am ET
_FMT = "%Y-%m-%dT%H:%M:%SZ"


def now_iso():
    return datetime.now(timezone.utc).strftime(_FMT)


def publish_at(day, now_iso):
    """Schedule for 11:00 UTC (~7am ET); if we're already past it (backup cron or
    a manual catch-up run), schedule a few minutes out rather than at 'now' so the
    publish_date is always safely in the future. `now_iso` is a UTC 'Z' string."""
    target = f"{day}T{SEND_HOUR_UTC}Z"
    if now_iso < target:
        return target
    soon = datetime.strptime(now_iso, _FMT).replace(tzinfo=timezone.utc) + SEND_BUFFER
    return soon.strftime(_FMT)


def already_sent(emails_json, token):
    """True if any recent Buttondown email's subject carries this send's token
    (every subject ends with it)."""
    return any(token in (e.get("subject") or "")
               for e in (emails_json or {}).get("results", []))


def request(url, api_key, payload=None):
    req = urllib.request.Request(
        url, headers={"Authorization": f"Token {api_key}",
                      "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8") if payload else None,
        method="POST" if payload else "GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_emails(api_key):
    """Recent emails, newest first — the duplicate-send check reads page one."""
    return request(LIST_URL, api_key)


def print_preview(subject, html):
    """Print what WOULD be sent (--dry-run). A Windows console or redirect
    defaults to cp1252 while brief prose carries σ (move sizes) and en-dashes,
    so widen the stream to UTF-8 first — an encoding hiccup must never fail a
    dry run. Streams that can't be reconfigured (a test's StringIO) don't need it."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # detached or already-consumed stream
            pass
    print("SUBJECT:", subject)
    print(html)


def create_scheduled(api_key, subject, html, publish_date):
    return request(API, api_key, {"subject": subject, "body": html,
                                  "status": "scheduled", "publish_date": publish_date})

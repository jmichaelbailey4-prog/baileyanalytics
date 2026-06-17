#!/usr/bin/env python3
"""Pipeline freshness monitor — a dead-man's-switch for the daily publish.

Stale data on the site is invisible: on a weekend FRED publishes nothing, so the
daily refresh legitimately commits nothing — "no new commit" is NOT a failure.
The real signal is pipeline *execution*: did `refresh-fred.yml` last *complete
successfully* recently? This script queries the GitHub Actions API for that
workflow's most recent successful run and, if it is older than a threshold:

  * opens (or refreshes) a single GitHub issue describing the staleness, and
  * exits non-zero, so the scheduled run is marked failed and GitHub's
    failed-workflow email fires too.

When a successful run reappears it closes the issue automatically. Designed to
tolerate one skipped cron slot but catch a fully-dead pipeline within ~a day.

Threshold rationale: the daily job runs twice (06:00 + 13:00 UTC), so in healthy
operation the newest success is at most ~17h old. 30h tolerates one fully-skipped
slot plus several hours of the cron lateness GitHub exhibits, while still flagging
a pipeline that has missed multiple consecutive slots. Override with the
FRESHNESS_THRESHOLD_HOURS env var if the cron drifts.

Design: a pure decision core (parse_iso / latest_success / evaluate /
find_monitor_issue / decide_action / build_*), unit-tested in
scripts/tests/test_freshness_check.py, plus a thin stdlib-urllib I/O shell that
wires it to the GitHub REST API (not unit-tested — only glue).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
WORKFLOW = "refresh-fred.yml"
DEFAULT_REPO = "jmichaelbailey4-prog/baileyanalytics"
DEFAULT_THRESHOLD_HOURS = 30.0
# Hidden marker stamped into the alert issue's body so subsequent runs recognise
# their own issue without depending on labels or an exact title.
MARKER = "<!-- freshness-monitor -->"


# --------------------------------------------------------------------------- #
# Pure decision core (unit-tested)
# --------------------------------------------------------------------------- #

def parse_iso(s):
    """Parse a GitHub ISO-8601 timestamp ('...Z') into an aware UTC datetime."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def latest_success(runs):
    """The `updated_at` of the most recent successfully-completed run, or None.

    Only conclusion=="success" counts (a failed or in-progress run does not prove
    the pipeline ran end to end). The API returns newest-first, but we never rely
    on ordering — take the chronological max.
    """
    successes = [r for r in (runs or [])
                 if r.get("conclusion") == "success" and r.get("updated_at")]
    if not successes:
        return None
    return max(successes, key=lambda r: parse_iso(r["updated_at"]))["updated_at"]


def evaluate(last_success_iso, now, threshold_hours):
    """Decide whether the pipeline is stale. Returns a plain dict (JSON-friendly)."""
    if last_success_iso is None:
        return {
            "stale": True,
            "age_hours": None,
            "last_success": None,
            "threshold_hours": threshold_hours,
            "reason": "no successful run found in the recent window",
        }
    age_hours = (now - parse_iso(last_success_iso)).total_seconds() / 3600.0
    stale = age_hours > threshold_hours
    reason = (
        f"last success {age_hours:.1f}h ago exceeds {threshold_hours}h threshold"
        if stale else
        f"last success {age_hours:.1f}h ago, within {threshold_hours}h threshold"
    )
    return {
        "stale": stale,
        "age_hours": age_hours,
        "last_success": last_success_iso,
        "threshold_hours": threshold_hours,
        "reason": reason,
    }


def threshold_from_env(environ, default=DEFAULT_THRESHOLD_HOURS):
    """Parse FRESHNESS_THRESHOLD_HOURS from an env mapping; fall back to default on
    a missing or malformed value so a typo can't crash the monitor (the safety net
    must not die silently when someone tries to tune it)."""
    raw = (environ.get("FRESHNESS_THRESHOLD_HOURS") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"WARN: ignoring malformed FRESHNESS_THRESHOLD_HOURS={raw!r}; "
              f"using {default}h.", file=sys.stderr)
        return default


def find_monitor_issue(issues, marker):
    """The first open issue carrying our marker, skipping PRs (the list-issues
    endpoint returns pull requests too, distinguished by a `pull_request` key)."""
    for item in issues or []:
        if "pull_request" in item:
            continue
        if marker in (item.get("body") or ""):
            return item
    return None


def decide_action(result, existing_issue):
    """create | update | resolve | noop — the whole orchestration in one place."""
    if result.get("stale"):
        return "create" if existing_issue is None else "update"
    return "resolve" if existing_issue is not None else "noop"


def build_alert_title():
    return "⚠️ Data pipeline may have stopped (freshness monitor)"


def build_alert_body(result, repo, workflow, runs_url, marker):
    owner = repo.split("/")[0]
    age = result.get("age_hours")
    age_txt = (f"{age:.1f} hours ago" if age is not None
               else "never — no successful run found in the recent window")
    return (
        f"{marker}\n\n"
        f"**The `{workflow}` pipeline may have stopped publishing.** (cc @{owner})\n\n"
        f"- Last successful run: {result.get('last_success') or '—'} ({age_txt})\n"
        f"- Staleness threshold: {result.get('threshold_hours')} hours\n"
        f"- Repository: `{repo}`\n\n"
        f"The daily refresh normally completes ~twice a day (06:00 and 13:00 UTC); "
        f"a gap this long usually means the scheduled workflow is failing or no "
        f"longer firing (note: a quiet weekend with no data change is normal and "
        f"still counts as a successful run, so this is about *execution*, not data).\n\n"
        f"Check the recent runs: {runs_url}\n\n"
        f"_Opened and closed automatically by the freshness monitor "
        f"(`.github/workflows/freshness-check.yml`). It will close itself once a "
        f"successful refresh run is detected._"
    )


def build_recovery_comment(result):
    last = result.get("last_success")
    age = result.get("age_hours")
    age_txt = f"{age:.1f}h ago" if age is not None else "recently"
    return (
        f"✅ **Recovered.** A successful `{WORKFLOW}` run was detected "
        f"(last success {last} — {age_txt}), within the "
        f"{result.get('threshold_hours')}h freshness threshold. "
        f"Closing this alert automatically."
    )


# --------------------------------------------------------------------------- #
# Thin GitHub REST I/O shell (glue; not unit-tested)
# --------------------------------------------------------------------------- #

# Transient statuses worth retrying on the read path (rate-limit / GitHub 5xx) so a
# momentary API blip doesn't crash the monitor and masquerade as a pipeline failure.
_RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}


def _request(method, url, token, payload=None, retries=1):
    data = json.dumps(payload).encode() if payload is not None else None
    last_exc = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "baileyanalytics-freshness-monitor")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code not in _RETRYABLE_STATUS or attempt == retries:
                raise
        except urllib.error.URLError as exc:
            last_exc = exc
            if attempt == retries:
                raise
        time.sleep(2 * attempt)
    raise last_exc  # pragma: no cover - loop always returns or raises above


def fetch_runs(repo, workflow, token, per_page=30):
    # status=success + branch=main: count only clean runs on the production branch,
    # so a burst of failed/in-progress runs can't crowd the last success out of the
    # window. (refresh_lenses catches per-source failures and still exits 0, so a
    # 'failure' conclusion is a genuine problem, not routine source flakiness — and
    # the 30h threshold tolerates a transient one-off failed slot.)
    url = (f"{API}/repos/{repo}/actions/workflows/{workflow}/runs"
           f"?status=success&branch=main&per_page={per_page}")
    return _request("GET", url, token, retries=3).get("workflow_runs", [])


def fetch_open_issues(repo, token, per_page=100):
    # Sort by most-recently-updated: the monitor PATCHes its own alert issue each
    # run, so it stays on the first page even if unrelated open issues pile up —
    # keeping find_monitor_issue's dedup guarantee robust without paginating.
    url = (f"{API}/repos/{repo}/issues"
           f"?state=open&sort=updated&direction=desc&per_page={per_page}")
    result = _request("GET", url, token, retries=3)
    return result if isinstance(result, list) else []


def create_issue(repo, token, title, body):
    return _request("POST", f"{API}/repos/{repo}/issues", token,
                    {"title": title, "body": body})


def comment_issue(repo, token, number, body):
    return _request("POST", f"{API}/repos/{repo}/issues/{number}/comments", token,
                    {"body": body})


def update_issue(repo, token, number, **fields):
    return _request("PATCH", f"{API}/repos/{repo}/issues/{number}", token, fields)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Query and evaluate, print the decision, but make no issue changes "
             "(still exits with the real stale/fresh code).")
    args = parser.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN is not set; cannot query the GitHub API.",
              file=sys.stderr)
        return 2
    repo = os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    threshold = threshold_from_env(os.environ)
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    runs_url = f"{server}/{repo}/actions/workflows/{WORKFLOW}"

    runs = fetch_runs(repo, WORKFLOW, token)
    result = evaluate(latest_success(runs), datetime.now(timezone.utc), threshold)
    existing = find_monitor_issue(fetch_open_issues(repo, token), MARKER)
    action = decide_action(result, existing)

    print(f"[freshness] {result['reason']} -> action={action}"
          + (" (dry-run)" if args.dry_run else ""))

    if not args.dry_run:
        if action == "create":
            created = create_issue(
                repo, token, build_alert_title(),
                build_alert_body(result, repo, WORKFLOW, runs_url, MARKER))
            print(f"[freshness] opened issue #{created.get('number')}")
        elif action == "update":
            update_issue(repo, token, existing["number"],
                         body=build_alert_body(result, repo, WORKFLOW, runs_url, MARKER))
            print(f"[freshness] refreshed issue #{existing['number']}")
        elif action == "resolve":
            # Close first, then comment: if the close were to fail after a posted
            # comment, the next run would re-comment on a still-open issue (spam).
            # Comments are allowed on a closed issue, so this ordering can't spam.
            update_issue(repo, token, existing["number"],
                         state="closed", state_reason="completed")
            comment_issue(repo, token, existing["number"],
                          build_recovery_comment(result))
            print(f"[freshness] closed issue #{existing['number']} (recovered)")

    return 1 if result["stale"] else 0


if __name__ == "__main__":
    sys.exit(main())

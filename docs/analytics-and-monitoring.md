# Analytics & pipeline freshness monitoring

Two small infrastructure additions (branch `analytics-and-monitoring`):
**(A)** privacy-friendly web analytics, and **(B)** a dead-man's-switch that
alerts if the daily publishing pipeline silently stops. Both fit the zero-build
static + Python-pipeline model.

---

## A. Web analytics — Cloudflare Web Analytics (edge injection)

**Decision: Cloudflare Web Analytics, injected automatically at the edge.** No
code ships for this; it is a single dashboard toggle.

**Why this path.** `baileyanalytics.com` is proxied through Cloudflare
(confirmed: responses carry `cf-ray` + `cf-cache-status`). For a proxied zone,
Cloudflare can inject its analytics beacon into every HTML response as it passes
through the edge — so **all ~50 pages, plus every page added later, are covered
with zero code and zero drift.** That directly solves this site's main coverage
risk: there is no shared `<head>` template (the 33 lens pages and the category
hubs are hand-written, `dashboards/brief*.html` + archive pages are baked by
`scripts/lenses/briefpage.py`, and `index.html`/`about.html`/`404.html` have
standalone heads), so any in-page snippet would have to be stamped into all of
them *and* the baked-page generator and kept in sync forever. Edge injection
sidesteps that entirely.

It is also privacy-first by default: no cookies, no consent banner, no PII, no
cross-site ad tracking; the beacon is loaded async and reports to the
same-domain `/cdn-cgi/rum` endpoint, so it never blocks rendering. Google
Analytics was explicitly out of scope.

**Prerequisite — satisfied.** Automatic injection is skipped if the origin sends
`Cache-Control: ... no-transform`. Our pages send `Cache-Control: max-age=600`
(no `no-transform`), so Cloudflare can inject. Nothing to change.

**What it answers.** Pageviews, top pages (Paths), referrers/sources, countries,
browsers/devices — all without cookies.

**Known limitation (and how email/RSS attribution still works).** Cloudflare Web
Analytics does **not** log query strings, so UTM campaign tags would be invisible
there — which is exactly why no UTM tags were added (they'd be dead weight). You
can still tell whether the email/RSS drive traffic two ways:
1. The **Referrers** report (feed readers and webmail referrers show up there).
2. The email and RSS both link to **dated permalinks**
   (`/dashboards/brief/YYYY-MM-DD.html`). Nobody reaches a specific dated archive
   page organically, so hits on those paths in the **Paths** report are an
   inherent email/RSS signal — no UTM needed.

If campaign-level attribution ever becomes important, the clean upgrade is
Plausible (a single in-page script via the injection-tool approach below) or
GA4 — but that reintroduces the snippet-drift problem edge injection avoids.

### Manual step (only you can do this)
1. Cloudflare dashboard → **Analytics & Logs → Web Analytics**.
2. Add `baileyanalytics.com` (if not already listed) and **Manage site →
   enable automatic setup** (a.k.a. "Add the JavaScript snippet automatically").
   Because the zone is proxied, this injects the beacon on every page under the
   domain. No DNS or code change.
3. Verify (see below).

### Verify it's live
- `curl -s https://baileyanalytics.com/ | grep -o 'cloudflareinsights\|/cdn-cgi/rum\|beacon.min.js'`
  should match once injection is on (it returns nothing today, pre-toggle).
- Open any page in a browser, check DevTools → Network for a `beacon.min.js` /
  `/cdn-cgi/rum` request, then confirm the hit appears in the Web Analytics dash.

### Alternative if you ever prefer code-controlled analytics
Not built (edge injection is better for this site), but one command away if
wanted: an idempotent injector modeled on `scripts/tools/seo_heads.py` that
stamps a `<script defer>` beacon into every hand-written page's `<head>` **and**
into `briefpage.py`'s head builder (so baked pages get it too), rerun whenever
pages are added. Say the word and provide a CF Web Analytics token or Plausible
domain and it's a short follow-up.

---

## B. Pipeline freshness monitor — self-hosted dead-man's-switch

**Decision: a self-hosted GitHub Actions check** (no external account → no manual
step, no secret to add). `.github/workflows/freshness-check.yml` runs
`scripts/tools/freshness_check.py` on a schedule.

**What it monitors — execution, not data.** On weekends/holidays FRED publishes
nothing, so the daily refresh legitimately commits nothing; "no new commit" is
**not** a failure. The signal is whether **`refresh-fred.yml` last *completed
successfully*** recently. The script queries the Actions API for that workflow's
most recent `conclusion == "success"` run and compares its age to a threshold.

**On staleness it does two things** (two independent notification channels):
- opens — or refreshes, if already open — a single GitHub issue describing the
  gap (found via a hidden `<!-- freshness-monitor -->` marker in the body, so it
  never opens duplicates), and
- exits non-zero, marking the scheduled run failed, which triggers GitHub's
  failed-workflow email to the repo owner.

When a successful run reappears, the next check **closes the issue
automatically** with a recovery comment — so a transient blip self-heals.

**Threshold = 30h** (override via the `FRESHNESS_THRESHOLD_HOURS` env var in the
workflow). Rationale: the daily job runs twice (06:00 + 13:00 UTC), so a healthy
newest-success is ≤ ~17h old. 30h tolerates one fully-skipped cron slot plus the
several-hours cron lateness GitHub exhibits (runs firing at 19:52Z/22:04Z for
earlier slots have been observed), while still catching a pipeline that has
missed multiple consecutive slots (silent > ~1.25 days). Because the alert
issue auto-closes on recovery, a rare lateness false-alarm is cheap and
self-resolving — so the threshold is tuned for sensitivity. Bump it to 36–48h if
cron drift ever produces a nuisance alert.

**Schedule.** Twice daily at 04:00 and 16:00 UTC — offset from the refresh slots,
and redundant so the monitor survives one of *its own* skipped cron slots. It is
deliberately **outside** the `write-main` concurrency group the data workflows
share (it never writes to `main`; it only reads runs and manages one issue).

**Permissions.** `issues: write` (manage the alert issue), `actions: read` (read
run history), `contents: read` (checkout). Uses the auto-provided
`GITHUB_TOKEN` — no secret to configure.

### Code shape (TDD'd)
A pure decision core — `parse_iso`, `latest_success`, `evaluate`,
`find_monitor_issue`, `decide_action`, `build_alert_*` — unit-tested in
`scripts/tests/test_freshness_check.py` (21 tests), plus a thin stdlib-`urllib`
GitHub I/O shell (glue, not unit-tested). Stdlib only, so the workflow needs no
`pip install`.

### Test / operate it
- Unit tests: `python -m unittest tests.test_freshness_check` from `scripts/`.
- Live read-only smoke test (no issue changes, prints the decision + real exit
  code): `GITHUB_TOKEN=<token> python scripts/tools/freshness_check.py --dry-run`.
- Manually trigger the real check anytime from the Actions tab
  (**Pipeline freshness check → Run workflow**).
- Make sure GitHub Actions **failure notifications** are on for your account
  (default on) so the non-zero exit emails you.

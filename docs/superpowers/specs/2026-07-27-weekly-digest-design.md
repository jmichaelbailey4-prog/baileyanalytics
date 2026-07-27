# Weekly email digest — design

**Date:** 2026-07-27
**Branch:** `weekly-digest`
**Status:** built, awaiting Michael's review/merge

## Decision (signed off before the build)

The subscriber email moves from **daily** to a **weekly roundup**, delivered **Friday
morning (~7am ET / 11:00 UTC)**. The website keeps publishing Today's Brief **daily** —
this is an **email-only** change.

Three points were decided up front and are not re-litigated here:

1. A **weekly roundup that recaps the whole week**, not a once-a-week snapshot of a
   single day. A reader who opens one email a week must not be shown Friday's brief
   and told it is "the week".
2. **Friday**, ~7am ET. That is the existing 11:00 UTC slot, so nothing about the
   scheduling math changes — only its cadence.
3. **Website/brief stays daily.** `refresh-fred.yml` keeps publishing every day; only
   the send step moves out.

## Why the shape it has

The daily email is a *diff*: what changed since yesterday. A weekly email cannot be a
diff of a single day, and it cannot be seven diffs concatenated — that is a digest of
digests, and it double-counts a lens that wobbled ok → watch → ok.

So the weekly is a **net** view, assembled from the committed daily archive
(`data/brief/days/YYYY-MM-DD.json`, one full snapshot per publication day):

| Section | Source | Rule |
|---|---|---|
| Verdict (hero) | latest day in window | The week's closing read — where things stand *now*, not an average. |
| What changed this week | first vs. last day's `lenses` status board | **Net** move per lens. Flip-flops cancel by construction. |
| Biggest moves this week | union of each day's `top_moves` | Dedup by `lens_id`, keep the most significant occurrence, rank, cap 5. **Each row is date-stamped.** |
| The week, day by day | each day's `verdict` | One line per publication day → its archive permalink. |
| What we're watching next | latest day's `watching` | Same three predictions the site shows. |

### The baseline trick (how "net" is computed exactly)

Comparing the window's first and last *available* snapshot is not quite right: if
Sat/Sun are quiet and Monday is the first file, a change that landed Monday morning is
relative to *last* Friday — inside our week, but invisible to an endpoint comparison.

Each day file carries its own `transitions` (what changed to produce that board), so
the true start-of-week board is recoverable:

```
baseline = first_day.lenses statuses, with each lens named in first_day.transitions
           reverted to its from_status
```

That is exactly the board as of the end of the previous week's email, whether the first
in-window file is Saturday or Wednesday (quiet days publish nothing, so the board did
not move on them). Net changes are then `brief.detect_transitions(baseline, last_day.lenses)`
— the same tested function the daily brief uses, so ordering and severity rules cannot drift.

### Ranking moves across a week

`delta` strings are unit-heterogeneous ("18.60%", "$2.40T", "9.40 months") and cannot be
compared across indicators. But each published move carries its `sparkline`, so
`brief.move_score(sparkline)` recovers the exact dimensionless z-score the brief ranked
it by that day. The weekly re-uses it: dedup by `lens_id` keeping the highest-scoring
occurrence (ties → most recent), then rank by score.

**Movers are date-stamped** ("Wed, Jul 22"). A Tuesday reading presented in a Friday
email without a date would read as current; that would be dishonest.

### Two things the first dry run changed

Reading the real rendered email against live data caught both:

1. **"The week, day by day" collapses runs.** Seven rows, six of them the identical
   sentence, is padding dressed as a recap. Consecutive days sharing the same
   (status, short verdict) now fold into one dated stretch — "Sat, Jul 18 – Thu, Jul 23"
   — linking to the day that read began. The live week went from 7 rows to 2.
2. **`--dry-run` crashed on Windows.** Brief prose carries `σ` (move sizes) and
   en-dashes; a cp1252 console or redirect can't encode them, so the preview died with
   exit 1. `buttondown.print_preview` widens stdout to UTF-8 first. The daily sender had
   the same latent bug and now shares the fix.

### Deviation from the brief: `watching` comes from the day file, not `open.json`

The build spec suggested reading `data/predictions/open.json`. The weekly instead uses
the latest day's `watching` array. That array *is* `open.json` — already filtered,
consequence-ranked and formatted by `today.py`/`state.py` — so reading it keeps the
email identical to the site and avoids a second, divergent ranking of the same data.

## Window, cadence, idempotency

- **Window** = the 7 days ending on the send day, inclusive (Sat → Fri in production).
- **Send day** = today (UTC). The cron guarantees Friday; a `workflow_dispatch` on any
  other day produces an honest trailing-7-day roundup rather than re-sending a stale
  Friday. `--date YYYY-MM-DD` overrides it for testing.
- **Quiet week** (no publication day in the window) → **send nothing**. Same philosophy
  as the daily quiet-day skip; never an empty email.
- **Idempotency key** = the literal `"The Week in Review, <Mon D, YYYY>"`, which every
  subject variant ends with. Distinct from the daily digest's bare date token, so a
  legacy daily subject can never suppress a weekly send.
- **Schedule** = 11:00 UTC that day, or now + 5 min on a catch-up run (unchanged
  `publish_at` logic — Buttondown rejects a `publish_date` that is not safely future).

## Code layout

New:

- `scripts/lenses/emailkit.py` — the shared email chrome: palette, `badge`, `row`,
  `section`, `watching_rows`, `date_token`, and the `document()` shell. Extracted from
  `digest.py`; the daily's rendered HTML is byte-identical after the extraction.
- `scripts/lenses/buttondown.py` — the shared Buttondown client: `publish_at`,
  `already_sent`, `list_emails`, `create_scheduled`. Extracted from `send_digest.py`,
  which re-exports `publish_at`/`already_sent` so existing callers and tests are unmoved.
- `scripts/lenses/weekly_digest.py` — pure builder: `build_weekly(days, end_iso, span)
  -> {subject, html}` (or `None` for a quiet week).
- `scripts/send_weekly_digest.py` — loads the window from `data/brief/days/`, gates on
  ≥1 publication day, POSTs to Buttondown. `--dry-run` prints and never POSTs.
- `.github/workflows/weekly-digest.yml` — Friday 10:30 UTC + a 15:00 UTC same-day backup
  (mirrors refresh-fred's dual-cron self-heal) + `workflow_dispatch`. Reads committed
  data only, commits nothing, so it needs no repo write permission and stays out of the
  `write-main` concurrency group.

Changed:

- `.github/workflows/refresh-fred.yml` — the *"Send the daily email digest"* step is
  **removed**. It was the only scheduled sender (`refresh-banking.yml` and
  `tournament.yml` never sent).
- Subscriber-facing copy, daily → weekly: `scripts/lenses/briefpage.py` (baked brief +
  archive), `index.html`, `about.html`, `dashboards/lens.js`. Plus a one-time catch-up
  over the already-baked archive back catalog (`scripts/tools/weekly_copy_catchup.py`),
  because archive pages are only re-rendered when their prev/next links change — their
  subscribe band is a live CTA and must not keep promising a daily email.

Kept but **unscheduled**: `scripts/send_digest.py` + `scripts/lenses/digest.py`. Nothing
dispatches them any more; they remain the manual one-off sender (e.g. a genuinely
market-moving transition mid-week). Deleting them is a one-line follow-up if Michael
prefers zero ambiguity.

## Tests

- `scripts/tests/test_weekly_digest.py` — window selection, the baseline/net-transition
  rule (including a flip-flop that must cancel and a change on the first in-window day
  that must survive), move dedup across days, date stamps, subject variants, quiet-week
  `None`, escaping.
- `scripts/tests/test_send_weekly_digest.py` — the ≥1-publication-day gate, window
  loading off disk, idempotency token, `--dry-run` never POSTs.
- `scripts/tests/test_buttondown.py` — the extracted client surface.
- `scripts/tests/test_digest.py` unchanged — it is the regression lock proving the
  `emailkit` extraction did not move the daily's output.

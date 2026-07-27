"""The weekly roundup email: a week of data/brief/days/*.json -> {subject, html}.

Pure. Shares its chrome with the daily digest via emailkit, so the two can
never drift on palette or row markup.

A weekly email cannot be a diff of one day, and seven daily diffs concatenated
would double-count a lens that wobbled ok -> watch -> ok. So the roundup is a
NET view of the window:

  * status changes  -> the start-of-week board vs. the end-of-week board, so
    flip-flops cancel by construction and ok -> watch -> elevated reads as one
    ok -> elevated move.
  * biggest moves   -> the union of each day's top_moves, deduped per lens,
    ranked by the same dimensionless z-score the brief ranked them by, and
    DATE-STAMPED (a Tuesday reading in a Friday email must not read as current).
  * verdict         -> the latest day's, i.e. where things stand now.

The start-of-week board is recovered exactly, even when the window opens on
quiet days: each day file carries the transitions that produced its own board,
so reverting the first in-window day's transitions yields the board as of the
end of last week's email.
"""

from datetime import date, timedelta
from html import escape

from . import brief, emailkit, feed

SITE = emailkit.SITE
INK = emailkit.INK
MUTED = emailkit.MUTED
FONT = emailkit.FONT

WINDOW_DAYS = 7
MOVES_CAP = 5
DAYS_CAP = 7
ARCHIVE_URL = f"{SITE}/dashboards/brief/"


def _day_date(day):
    return (day.get("generated_at") or "")[:10]


def _permalink(iso_date):
    return f"{SITE}/dashboards/brief/{iso_date}.html"


def window_dates(end_iso, span=WINDOW_DAYS):
    """The `span` ISO dates ending on `end_iso`, ascending and inclusive."""
    end = date.fromisoformat(end_iso)
    return [(end - timedelta(days=n)).isoformat() for n in range(span - 1, -1, -1)]


def week_label(start_iso, end_iso):
    """'Jul 25–31, 2026' / 'Jun 28 – Jul 4, 2026' / 'Dec 28, 2026 – Jan 3, 2027'.
    Windows-safe (no %-d) and locale-independent."""
    a, b = date.fromisoformat(start_iso), date.fromisoformat(end_iso)
    am, bm = a.strftime("%b"), b.strftime("%b")
    if a.year != b.year:
        return f"{am} {a.day}, {a.year} – {bm} {b.day}, {b.year}"
    if a.month != b.month:
        return f"{am} {a.day} – {bm} {b.day}, {b.year}"
    return f"{am} {a.day}–{b.day}, {b.year}"


def subject_token(iso_date):
    """The idempotency key, carried by every subject variant. Deliberately more
    than a bare date: a legacy daily subject can never suppress a weekly send."""
    return f"The Week in Review, {emailkit.date_token(iso_date)}"


def select_days(days, end_iso, span=WINDOW_DAYS):
    """The day snapshots falling inside the window, ascending by date."""
    wanted = set(window_dates(end_iso, span))
    return sorted((d for d in days if _day_date(d) in wanted), key=_day_date)


def baseline_statuses(first_day):
    """The board as it stood at the START of the week: the first in-window day's
    statuses with its own transitions reverted to their from_status. Quiet days
    publish nothing, so this holds whether the window opens on Saturday or on
    the following Wednesday."""
    board = {lens["lens_id"]: lens.get("status")
             for lens in first_day.get("lenses") or [] if lens.get("lens_id")}
    for t in first_day.get("transitions") or []:
        if t.get("lens_id") in board:
            board[t["lens_id"]] = t.get("from_status")
    return board


def net_transitions(days):
    """Lenses whose status differs between the start and end of the week.
    Delegates the severity/ordering rules to brief.detect_transitions — the same
    function the daily brief uses — so the two can't drift."""
    days = sorted(days, key=_day_date)
    if not days:
        return []
    return brief.detect_transitions(baseline_statuses(days[0]),
                                    days[-1].get("lenses") or [])


def week_moves(days, limit=MOVES_CAP, exclude=()):
    """The week's biggest moves, one per lens. Delta strings carry incomparable
    units across indicators, but every published move carries its sparkline —
    so brief.move_score recovers the exact dimensionless score the brief ranked
    it by that day, and the week can rank them against each other honestly.
    Ties go to the more recent day. Each move gains a `date`."""
    best = {}
    for day in sorted(days, key=_day_date):
        stamp = _day_date(day)
        for m in day.get("top_moves") or []:
            lens_id = m.get("lens_id")
            if not lens_id or lens_id in exclude:
                continue
            score = brief.move_score(m.get("sparkline"))
            score = -1.0 if score is None else score
            if lens_id not in best or score >= best[lens_id][0]:
                best[lens_id] = (score, dict(m, date=stamp))
    ranked = sorted(best.values(), key=lambda pair: -pair[0])
    return [m for _, m in ranked[:limit]]


def _lens_link(record):
    return (f'<a href="{escape(SITE + record["href"], quote=True)}" style="color:{INK};">'
            f'{escape(record["lens_title"])}</a>')


def _changed_rows(transitions):
    if not transitions:
        return emailkit.row("No status changes this week",
                            "Every lens ended the week where it started.")
    return "".join(
        emailkit.row(f'{_lens_link(t)} {emailkit.badge(t["from_status"])} &rarr; '
                     f'{emailkit.badge(t["to_status"])}',
                     escape(t.get("headline", "")))
        for t in transitions)


def _stamp(iso_date):
    d = date.fromisoformat(iso_date)
    return f'<span style="color:{MUTED};font-weight:400;">&middot; {d.strftime("%b")} {d.day}</span>'


def _move_rows(moves):
    rows = []
    for m in moves:
        arrow = "&#9660;" if m.get("dir") == "down" else "&#9650;"
        delta = f" {arrow}{escape(m['delta'])}" if m.get("delta") else ""
        body = escape(m.get("headline", ""))
        if m.get("why"):  # the self-grounded "why" rides along on its own muted line
            body += (f'<br><span style="font-style:italic;color:{MUTED};">'
                     f'{escape(m["why"])}</span>')
        rows.append(emailkit.row(
            f'{_lens_link(m)} &middot; {escape(m.get("stat_label", ""))} '
            f'<strong>{escape(m.get("stat_value", ""))}</strong>{delta} '
            f'{_stamp(m["date"])}',
            body))
    return "".join(rows)


def _weekday(iso_date, short=False):
    d = date.fromisoformat(iso_date)
    return f'{d.strftime("%a" if short else "%A")}, {d.strftime("%b")} {d.day}'


def _week_rows(days):
    """The week as it unfolded, oldest first. Consecutive days carrying the same
    read collapse into one dated stretch — six identical lines is padding, not a
    recap — and each stretch links to the day that read began."""
    runs = []
    for day in days[-DAYS_CAP:]:
        verdict = day.get("verdict") or {}
        read = (verdict.get("status", "unknown"),
                verdict.get("short") or verdict.get("sentence", ""))
        if runs and runs[-1][0] == read:
            runs[-1][1].append(_day_date(day))
        else:
            runs.append((read, [_day_date(day)]))

    rows = []
    for (status, read), dates in runs:
        label = (_weekday(dates[0]) if len(dates) == 1
                 else f"{_weekday(dates[0], short=True)} – {_weekday(dates[-1], short=True)}")
        rows.append(emailkit.row(
            f'<a href="{_permalink(dates[0])}" style="color:{INK};">{escape(label)}</a> '
            f"{emailkit.badge(status)}",
            escape(read)))
    return "".join(rows)


def _subject(transitions, counts, token):
    if transitions:
        t = transitions[0]
        verb = "tips to" if t.get("direction") == "worsening" else "improves to"
        more = f" (+{len(transitions) - 1} more)" if len(transitions) > 1 else ""
        return (f"{t['lens_title']} {verb} {t['to_status'].upper()}{more} "
                f"— {token}")
    # `token` already opens with "The Week in Review", so the counts lead in
    # front of it rather than repeating the phrase.
    return f"{feed._counts_phrase(counts)} — {token}"


def build_weekly(days, end_iso=None, span=WINDOW_DAYS):
    """The weekly roundup for the window ending on `end_iso` (default: the
    latest day supplied). Returns None for a quiet week — no publication days in
    the window means no email, never an empty one."""
    days = [d for d in (days or []) if _day_date(d)]
    if not days:
        return None
    end_iso = end_iso or max(_day_date(d) for d in days)
    days = select_days(days, end_iso, span)
    if not days:
        return None

    window = window_dates(end_iso, span)
    latest = days[-1]
    # No readings at all (every category failed to load) makes status_counts all
    # zeros, and the counts phrase would then announce "All clear across the
    # dashboards" — a confident lie. Nothing to report means no email.
    if not latest.get("lenses"):
        return None
    counts = latest.get("status_counts") or {}
    attention = counts.get("watch", 0) + counts.get("elevated", 0) + counts.get("alert", 0)
    verdict = latest.get("verdict") or {}
    permalink = _permalink(_day_date(latest))

    transitions = net_transitions(days)
    moves = week_moves(days, exclude={t["lens_id"] for t in transitions})

    watching = emailkit.watching_rows(latest.get("watching"))
    watching_block = (emailkit.section("What we&rsquo;re watching next") + watching
                      if watching else "")
    moves_block = (emailkit.section("Biggest moves this week") + _move_rows(moves)
                   if moves else "")

    body = f"""{emailkit.section("What changed this week")}
{_changed_rows(transitions)}
{moves_block}
{emailkit.section("The week, day by day")}
{_week_rows(days)}
{watching_block}
<tr><td style="padding:22px 0 0;{FONT}font-size:13px;color:{MUTED};">
{attention} readings warrant attention right now &mdash;
<a href="{permalink}#alert" style="color:{INK};">see where the pressure is</a>.
</td></tr>
<tr><td style="padding:18px 0 0;{FONT}font-size:13px;">
<a href="{permalink}" style="color:{INK};font-weight:600;">Read the latest brief in full &rarr;</a>
&nbsp;&middot;&nbsp;
<a href="{ARCHIVE_URL}" style="color:{MUTED};">Browse the archive</a>
</td></tr>"""

    html = emailkit.document(
        f"The Week in Review &middot; {escape(week_label(window[0], window[-1]))}",
        verdict.get("status", "unknown"), verdict.get("sentence", ""), body)
    return {"subject": _subject(transitions, counts, subject_token(end_iso)),
            "html": html}

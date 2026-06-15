"""Ledger I/O + aggregates. The ledger/YYYY.json files are the permanent
append-only record (append is idempotent per entry id; a graded entry is
frozen forever — spec §3) and are written directly, only when a row is
appended or footnoted. open/recent/track-record are derived views written
via lenses.build.write_lens_file (write-if-changed)."""

import json
from datetime import datetime, timezone

from lenses import build


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _year_path(pred_dir, entry):
    return pred_dir / "ledger" / f"{entry['made_at'][:4]}.json"


def _load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return default


def append_graded(pred_dir, entry):
    """Append one graded entry to its year file. Idempotent per id; an id that
    already exists is left untouched (first-print grades never mutate)."""
    path = _year_path(pred_dir, entry)
    rows = _load(path, [])
    if any(r.get("id") == entry["id"] for r in rows):
        return False
    rows.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return True


def set_revision(pred_dir, entry_id, made_year, revised_to):
    """The one sanctioned mutation: fill grade.revised_to (footnote, spec §3)."""
    path = pred_dir / "ledger" / f"{made_year}.json"
    rows = _load(path, [])
    changed = False
    for r in rows:
        if (r.get("id") == entry_id and r.get("grade")
                and r["grade"].get("revised_to") != revised_to):
            r["grade"]["revised_to"] = revised_to
            changed = True
    if changed:
        path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return changed


def load_all_graded(pred_dir):
    rows = []
    ledger_dir = pred_dir / "ledger"
    if ledger_dir.exists():
        for path in sorted(ledger_dir.glob("*.json")):
            rows.extend(_load(path, []))
    return rows


def write_open(pred_dir, entries):
    return build.write_lens_file(
        pred_dir / "open.json",
        {"generated_at": _now(), "predictions": entries})


def load_open(pred_dir):
    return _load(pred_dir / "open.json", {}).get("predictions", [])


def recent(graded, feed_size=50):
    """Last grade per key + a newest-first feed of recent grades."""
    by_graded_at = sorted(graded, key=lambda e: e["grade"]["graded_at"])
    last = {}
    for e in by_graded_at:
        last[e["key"]] = e
    return {"generated_at": _now(), "last": last,
            "feed": list(reversed(by_graded_at))[:feed_size]}


def track_record(graded):
    """Aggregates recomputable by anyone from the ledger (spec §6)."""
    def _bucket(rows):
        n = len(rows)
        if not n:
            return {"graded": 0}
        s_err = sum(e["grade"]["abs_error"] for e in rows)
        s_naive = sum(e["grade"]["naive_error"] for e in rows)
        # Status accuracy is only meaningful for badge-driving series: a
        # descriptive (info) series predicts info -> info, so status_hit is
        # trivially True and would inflate the figure. Exclude them from the
        # status bucket (None when there are no scored rows). Calibration and
        # skill stay over all rows — band coverage and error-vs-naive are
        # meaningful for any series. (See DECISIONS-PENDING #1b re: whether
        # descriptive rows should also be split out of the headline skill.)
        scored = [e for e in rows if not e.get("descriptive")]
        return {
            "graded": n,
            "calibration": sum(1 for e in rows if e["grade"]["hit"]) / n,
            "direction": sum(1 for e in rows if e["grade"]["direction_hit"]) / n,
            "status": (sum(1 for e in scored if e["grade"]["status_hit"]) / len(scored)
                       if scored else None),
            "skill": (1.0 - s_err / s_naive) if s_naive > 0 else 0.0,
        }
    cats = {}
    for e in graded:
        cats.setdefault(e["category"], []).append(e)
    out = {"generated_at": _now(),
           "since": min((e["made_at"] for e in graded), default=None)}
    out.update(_bucket(graded))
    out["categories"] = {c: _bucket(rows) for c, rows in sorted(cats.items())}
    return out


def write_views(pred_dir, open_entries, graded):
    """Write open.json, recent.json, track-record.json (all write-if-changed)."""
    wrote = []
    if write_open(pred_dir, open_entries):
        wrote.append("open.json")
    if build.write_lens_file(pred_dir / "recent.json", recent(graded)):
        wrote.append("recent.json")
    if build.write_lens_file(pred_dir / "track-record.json", track_record(graded)):
        wrote.append("track-record.json")
    return wrote

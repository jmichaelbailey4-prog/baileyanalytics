"""Assemble lens JSON + hub index from config and fetched data; write to disk."""

import json
from datetime import datetime, timezone

from . import config, narrative, recessions, util


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latest_raw(raw):
    """Last observation with a real (non-null) value."""
    for obs in reversed(raw):
        if obs["value"] not in (None, "."):
            return {"date": obs["date"], "value": obs["value"]}
    return None


def _fmt(value, unit):
    f = util.to_float(value)
    if f is None:
        return "—"
    return f"{f:.2f}{unit}"


def build_lens(lens, fetched):
    """Build the full JSON dict for one lens."""
    indicators = []
    statuses = []
    for ind in lens.indicators:
        raw = fetched.get(ind.fetch_key, [])
        cleaned = util.clean(raw)
        text, status = ind.rule(cleaned)
        statuses.append(status)
        indicators.append({
            "id": ind.id,
            "title": ind.title,
            "short": ind.short,
            "unit": ind.unit,
            "color": ind.color,
            "series_id": ind.series_id,
            "observations": raw,
            "latest": _latest_raw(raw),
            "context": ind.context,
            "read": text,
            "signal_status": status,
        })
    headline, overall = narrative.synthesize(lens.id, statuses)
    return {
        "id": lens.id,
        "title": lens.title,
        "accent": lens.accent,
        "last_updated": _now(),
        "status": overall,
        "headline_read": headline,
        "recessions": recessions.recession_periods(fetched.get(config.USREC_KEY, [])),
        "indicators": indicators,
    }


def build_index(lens_jsons):
    """Build the hub index from already-built lens JSONs."""
    lenses = []
    for lj in lens_jsons:
        primary = lj["indicators"][0]
        spark = [
            f for f in (util.to_float(o["value"]) for o in primary["observations"])
            if f is not None
        ][-40:]
        key_stats = []
        for ind in lj["indicators"][:2]:
            if ind["latest"]:
                key_stats.append({"k": ind["short"], "v": _fmt(ind["latest"]["value"], ind["unit"])})
        lenses.append({
            "id": lj["id"],
            "title": lj["title"],
            "accent": lj["accent"],
            "status": lj["status"],
            "headline_read": lj["headline_read"],
            "key_stats": key_stats,
            "sparkline": spark,
        })
    return {"last_updated": _now(), "lenses": lenses}


def _strip_volatile(d):
    out = dict(d)
    out.pop("last_updated", None)
    return out


def write_lens_file(path, lens_json):
    """Write a lens/index JSON, skipping if data (ignoring last_updated) is unchanged.

    Returns True if written, False if skipped.
    """
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if _strip_volatile(existing) == _strip_volatile(lens_json):
                return False
        except (ValueError, OSError):
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lens_json, indent=2) + "\n", encoding="utf-8")
    return True


def write_outputs(lens_jsons, out_dir):
    """Write each lens file + index.json. Returns list of paths actually written."""
    written = []
    for lj in lens_jsons:
        path = out_dir / f"{lj['id']}.json"
        if write_lens_file(path, lj):
            written.append(path)
    index_path = out_dir / "index.json"
    if write_lens_file(index_path, build_index(lens_jsons)):
        written.append(index_path)
    return written

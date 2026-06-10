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


def _fmt(value, unit, value_format="decimal"):
    """Format a value + unit the way lens.js fmtVal does: '$' is a prefix,
    word units ('months', 'Bcf') get a space, symbol units ('%', 'M') stay tight."""
    f = util.to_float(value)
    if f is None:
        return "—"
    num = f"{round(f):,}" if value_format == "thousands" else f"{f:.2f}"
    if not unit:
        return num
    if unit.startswith("$"):  # "$" -> "$4.15"; "$T" -> "$2.40T"; "$B" -> "$1,012B"
        return f"${num}{unit[1:]}"
    if len(unit) > 1 and unit[0].isalpha():
        return f"{num} {unit}"
    return f"{num}{unit}"


def build_lens(lens, fetched):
    """Build the full JSON dict for one lens."""
    indicators = []
    statuses = []
    for ind in lens.indicators:
        raw = fetched.get(ind.fetch_key, [])
        if ind.derive:
            raw = ind.derive(raw)
        # thin AFTER derive: diffs/YoY need the full-resolution chain
        raw = util.thin_observations(raw)
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
            "value_format": ind.value_format,
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


def _status_of(value, rule):
    """Run a single value through a narrative rule to get its status string."""
    obs = [("x", value)] if value is not None else []
    _, status = rule(obs)
    return status


def build_banking_lens(lens, series_by_key, tier_rows, ranking_rows):
    """Assemble one banking lens JSON: time-series indicators + tiers + rankings.

    series_by_key: {indicator_id: [{date, value}]}
    tier_rows:     [{tier, values:[{value}]}]  (from fdic.tier_aggregates, metric order)
    ranking_rows:  {ranking_title: [{name, location, asset, value}]}
    """
    indicators, statuses = [], []
    for ind in lens.indicators:
        raw = series_by_key.get(ind.id, [])
        cleaned = util.clean(raw)
        text, status = ind.rule(cleaned)
        statuses.append(status)
        indicators.append({
            "id": ind.id, "title": ind.title, "short": ind.short, "unit": ind.unit,
            "color": ind.color, "observations": raw, "latest": _latest_raw(raw),
            "context": ind.context, "read": text, "signal_status": status,
            "value_format": ind.value_format,
        })
    headline, overall = narrative.synthesize(lens.id, statuses)

    tiers = None
    if lens.tier_metrics and tier_rows:
        columns = [{"key": m["key"], "label": m["label"]} for m in lens.tier_metrics]
        rows = []
        for tr in tier_rows:
            cells = []
            for m, cell in zip(lens.tier_metrics, tr["values"]):
                v = cell.get("value")
                cells.append({
                    "value": "—" if v is None else f"{v:.2f}%",
                    "status": _status_of(v, m["rule"]),
                })
            rows.append({"tier": tr["tier"], "values": cells})
        tiers = {"label": "Across the system — by bank size",
                 "subtitle": "Where is the stress concentrated?",
                 "columns": columns, "rows": rows}

    rankings = []
    for spec in lens.rankings:
        rows = []
        for r in ranking_rows.get(spec["title"], []):
            v = r.get("value")
            fv = None if v in (None, "") else float(v)
            rows.append({
                "name": r["name"], "location": r["location"], "asset": r["asset"],
                "value": "—" if fv is None else f"{fv:.2f}{spec.get('unit', '')}",
                "status": _status_of(fv, spec["rule"]),
            })
        rankings.append({"title": spec["title"], "subtitle": spec["subtitle"],
                         "value_label": spec["value_label"], "rows": rows})

    return {
        "id": lens.id, "title": lens.title, "accent": lens.accent, "last_updated": _now(),
        "status": overall, "headline_read": headline, "recessions": [],
        "indicators": indicators, "tiers": tiers, "rankings": rankings,
    }


def build_crypto_lens(rotation_obs, dominance_obs, btc_eth_obs):
    """Assemble the CoinGecko/FRED crypto-structure lens JSON from three prepared
    series. Produces the standard lens shape (no tiers/rankings), so lens.js renders
    it with the existing single-line chart component."""
    # Dominance leads: it's the one crypto-structure number that reads instantly
    # on the hub ("BTC dominance 56%"); the rotation index is explained on-page.
    specs = [
        ("btc-dominance", "Bitcoin Dominance", "BTC dominance", "%", "#FBBF24",
         dominance_obs, narrative.rule_btc_dominance,
         ("Bitcoin's share of total cryptocurrency market value. A rising share signals "
          "caution; a falling share signals risk appetite. History accumulates daily."), "decimal"),
        ("crypto-rotation", "Large-vs-Small Rotation", "Alt rotation", "", "#818CF8",
         rotation_obs, narrative.rule_crypto_rotation,
         ("Small- and mid-cap coins' market value relative to Bitcoin and Ether, indexed to "
          "100 at the start of the window. Rising means alts are outperforming (risk-on); "
          "falling means a flight to the majors."), "decimal"),
        ("btc-eth-ratio", "Bitcoin / Ether Ratio", "BTC/ETH", "", "#A78BFA",
         btc_eth_obs, narrative.rule_btc_eth_relative,
         ("The price of Bitcoin divided by the price of Ether — which of the two largest coins "
          "is leading. Sourced from FRED's decade-long price history."), "decimal"),
    ]
    indicators, statuses = [], []
    for id_, title, short, unit, color, obs, rule, context, vfmt in specs:
        obs = util.thin_observations(obs)
        text, status = rule(util.clean(obs))
        statuses.append(status)
        indicators.append({
            "id": id_, "title": title, "short": short, "unit": unit, "color": color,
            "observations": obs, "latest": _latest_raw(obs), "context": context,
            "read": text, "signal_status": status, "value_format": vfmt,
        })
    headline, overall = narrative.synthesize("crypto-structure", statuses)
    return {
        "id": "crypto-structure", "title": "Crypto Market Structure", "accent": "#818CF8",
        "last_updated": _now(), "status": overall, "headline_read": headline,
        "recessions": [], "indicators": indicators,
    }


def _delta(ind):
    """Change of the latest observation vs the one before it, as
    {"d": "0.25%", "dir": "up"} — or {} when there's no prior point or no move.
    `dir` carries the sign (the UI renders it as ▲/▼). The cadence is the
    series' own: daily series read "since yesterday", quarterly ones "since
    last quarter"."""
    values = [f for f in (util.to_float(o["value"]) for o in ind["observations"]) if f is not None]
    if len(values) < 2 or values[-1] == values[-2]:
        return {}
    diff = values[-1] - values[-2]
    return {"d": _fmt(abs(diff), ind["unit"], ind.get("value_format", "decimal")),
            "dir": "up" if diff > 0 else "down"}


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
                stat = {"k": ind["short"], "v": _fmt(ind["latest"]["value"], ind["unit"], ind.get("value_format", "decimal"))}
                stat.update(_delta(ind))
                key_stats.append(stat)
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

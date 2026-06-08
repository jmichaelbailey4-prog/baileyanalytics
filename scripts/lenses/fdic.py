"""FDIC BankFind API access — the only banking module that touches the network.

National series are computed sum-then-divide across the per-state summary rows
(never by averaging per-entity ratios). Returns FRED-style [{date, value}] so the
rest of the pipeline is reused unchanged.
"""

import json
import urllib.parse
import urllib.request

SUMMARY_BASE = "https://api.fdic.gov/banks/summary"
FINANCIALS_BASE = "https://api.fdic.gov/banks/financials"


def _query(params):
    """Encode params the way the FDIC API expects: spaces as %20 (not +), with
    `:` `*` left literal so range filters like `REPDTE:[X TO Y]` parse correctly."""
    return urllib.parse.urlencode(params, safe=":*", quote_via=urllib.parse.quote)


def _get(url, timeout):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def _rows(payload):
    return [r.get("data", r) for r in payload.get("data", [])]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def quarter_ends(start_year, latest_repdte):
    """Quarter-end REPDTEs (YYYYMMDD), chronological, from start_year through latest."""
    ends = []
    for year in range(start_year, int(latest_repdte[:4]) + 1):
        for md in ("0331", "0630", "0930", "1231"):
            rep = f"{year}{md}"
            if rep <= latest_repdte:
                ends.append(rep)
    return ends


def national_quarterly(metrics, quarters, timeout=40):
    """National value per quarter for each metric, aggregated from /financials.

    Fetches every bank once per quarter (union of all metric fields) and
    aggregates via `_metric_value` (the same sum-then-ratio / weighted-average
    logic used for tiers). FDIC's per-bank ratio fields are already annualized
    where relevant, so no YTD de-cumulation is needed.

    `metrics`: list of dicts, each with a "key" plus either
      {"numerator": [...], "denominator": [...], "scale": float}  (dollar fields), or
      {"ratio_field": F, "weight_field": W, "scale": float}        (per-bank ratio).
    Returns {metric_key: [{date, value}]} chronological.
    """
    fields = set()
    for m in metrics:
        fields.update(_metric_fields(m))
    fields = sorted(fields)
    series = {m["key"]: [] for m in metrics}
    for rep in quarters:
        banks = _fetch_all_financials(fields, rep, timeout)
        date = f"{rep[:4]}-{rep[4:6]}-{rep[6:]}"
        for m in metrics:
            v = _metric_value(m, banks)
            if v is not None:
                series[m["key"]].append({"date": date, "value": f"{v:.4f}"})
    return series


def latest_repdte(timeout=25):
    """The most recent reporting date available in /financials, as YYYYMMDD."""
    params = {"fields": "REPDTE", "sort_by": "REPDTE", "sort_order": "DESC",
              "limit": 1, "format": "json"}
    url = f"{FINANCIALS_BASE}?{_query(params)}"
    rows = _rows(_get(url, timeout))
    rep = str(rows[0].get("REPDTE", ""))[:10] if rows else ""
    return rep.replace("-", "")


def _fmt_assets(thousands):
    """FDIC ASSET is in $000s. Render as $X.YB / $XXXm."""
    dollars = _num(thousands) * 1000
    if dollars >= 1e9:
        return f"${dollars / 1e9:.1f}B"
    return f"${dollars / 1e6:.0f}m"


def ranking(metric_field, repdte, asset_min, limit, sort_order="DESC",
            min_base_fields=None, min_base=0, max_value=None, timeout=25):
    """Top-`limit` banks by `metric_field` for one quarter, with outlier filtering.

    `asset_min` (in $000s) is the size floor. To keep the ranking *insightful* rather
    than a list of idiosyncratic distressed micro-cases, two further filters apply:
      * `min_base_fields` + `min_base`: require a material denominator book (in $000s),
        e.g. a real CRE-loan book — so a tiny book can't post an exploded ratio.
      * `max_value`: drop values above this sanity ceiling (a backstop for anomalies).
    A larger candidate pool is fetched so `limit` clean rows remain after filtering.
    `sort_order` is "DESC" (worst-is-highest) or "ASC" (worst-is-lowest, e.g. capital).
    """
    pool = max(limit * 8, 80)
    fields = ["NAME", "CITY", "STALP", "ASSET", metric_field] + list(min_base_fields or [])
    params = {
        "filters": f"REPDTE:{repdte} AND ASSET:[{asset_min} TO *]",
        "fields": ",".join(fields),
        "sort_by": metric_field,
        "sort_order": sort_order,
        "limit": pool,
        "format": "json",
    }
    url = f"{FINANCIALS_BASE}?{_query(params)}"
    out = []
    for row in _rows(_get(url, timeout)):
        v = _num(row.get(metric_field))
        if max_value is not None and v > max_value:
            continue
        if min_base_fields and sum(_num(row.get(f)) for f in min_base_fields) < min_base:
            continue
        out.append({
            "name": row.get("NAME", ""),
            "location": f"{row.get('CITY', '')}, {row.get('STALP', '')}".strip(", "),
            "asset": _fmt_assets(row.get("ASSET")),
            "value": row.get(metric_field),
        })
        if len(out) >= limit:
            break
    return out


def _fetch_all_financials(fields, repdte, timeout, page=10000):
    """Page through every bank's financials for one quarter."""
    out, offset = [], 0
    while True:
        params = {
            "filters": f"REPDTE:{repdte}",
            "fields": ",".join(fields),
            "limit": page,
            "offset": offset,
            "format": "json",
        }
        url = f"{FINANCIALS_BASE}?{_query(params)}"
        rows = _rows(_get(url, timeout))
        out.extend(rows)
        if len(rows) < page:
            return out
        offset += page


def _metric_fields(m):
    """The financials fields a tier metric needs."""
    if "ratio_field" in m:
        return [m["ratio_field"], m["weight_field"]]
    return list(m["numerator"]) + list(m["denominator"])


def _metric_value(m, members):
    """Aggregate one tier metric across `members`.

    Two modes:
    - sum-then-ratio: {"numerator": [...], "denominator": [...]} on dollar fields
      (value = scale * Σnumerator / Σdenominator; scale default 100).
    - weighted average: {"ratio_field": F, "weight_field": W} on a per-bank ratio
      field (value = Σ(ratio*weight)/Σweight; scale default 1, since the field is
      already a percent). Use this when the dollar numerator is unreliable/null.
    """
    if "ratio_field" in m:
        scale = m.get("scale", 1.0)
        wsum = sum(_num(b.get(m["weight_field"])) for b in members)
        if not wsum:
            return None
        acc = sum(_num(b.get(m["ratio_field"])) * _num(b.get(m["weight_field"])) for b in members)
        return round(scale * acc / wsum, 4)
    scale = m.get("scale", 100.0)
    num = sum(_num(b.get(f)) for b in members for f in m["numerator"])
    den = sum(_num(b.get(f)) for b in members for f in m["denominator"])
    return round(scale * num / den, 4) if den else None


def tier_aggregates(metrics, repdte, tiers, timeout=25):
    """Per-size-tier values for one quarter.

    Pulls all banks' fields once, buckets by asset band, aggregates each metric
    per band. `tiers` is a list of (label, asset_min_000s, asset_max_000s_or_None).
    Each metric is either sum-then-ratio (dollar fields) or weighted-average
    (per-bank ratio field) — see `_metric_value`.
    """
    fields = {"ASSET"}
    for m in metrics:
        fields.update(_metric_fields(m))
    banks = _fetch_all_financials(sorted(fields), repdte, timeout)
    rows = []
    for label, lo, hi in tiers:
        members = [
            b for b in banks
            if _num(b.get("ASSET")) >= lo and (hi is None or _num(b.get("ASSET")) < hi)
        ]
        values = [{"value": _metric_value(m, members)} for m in metrics]
        rows.append({"tier": label, "values": values})
    return rows

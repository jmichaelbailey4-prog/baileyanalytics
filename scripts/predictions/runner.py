"""Orchestration for the two jobs (spec §4–§5). The only module here that
touches the network — via the lens pipeline's own fetchers, read-only.
Every per-indicator body is wrapped: one failure skips that indicator and
never blanks the rest (house pattern)."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from lenses import brief, build, config, eia, fred, util, yahoo

from . import backtest, cadence, explain, grade, ledger, models

FIXTURE = (Path(__file__).resolve().parent.parent / "tests" / "fixtures"
           / "predict_histories_sample.json")
DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # baked lens JSON lives here
FRED_FULL_LIMIT = 100000
MAX_ORIGINS = {"weekly": 104, "monthly": 96, "quarterly": 32, "daily": 104}
REVISION_LOOKBACK = 3  # re-check grades for this many trailing periods


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_fixture_histories():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _find_cat(category):
    for cat in config.CATEGORIES:
        if cat["id"] == category:
            return cat
    return None


def _baked_history(entry, data_dir=None):
    """Read an already-baked indicator history from its lens JSON, for sources
    predict.py can't fetch directly (fdic/computed/nyfed/epu). These observations
    are POST-derive and post-thin — _prepared_series must NOT re-derive them.
    Mirrors lenses.refresh_lenses._prior_obs (degrade to [] on a missing/locked
    file → the runner keeps the prior open entry); kept local so the lightweight
    predictions package needn't import the heavy refresh_lenses module (Pillow)."""
    cat = _find_cat(entry.category)
    out = cat["out"] if cat else entry.category
    path = (Path(data_dir) if data_dir else DATA_DIR) / out / f"{entry.lens_id}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    for ind in data.get("indicators", []):
        if ind.get("id") == entry.indicator.id:
            return ind.get("observations", [])
    return []


def _fetch_history(entry, dry_run, fixture_cache):
    """Raw full history for one roster entry ([{'date','value'}])."""
    ind = entry.indicator
    if dry_run:
        return fixture_cache.get(entry.key, [])
    if entry.baked:
        return _baked_history(entry)  # banking/computed/nyfed/epu: read the baked JSON
    if ind.source == "eia":
        return eia.fetch_series(ind.eia_route, ind.eia_facets, ind.eia_freq,
                                os.environ["EIA_API_KEY"], max(ind.limit, 2000),
                                ind.eia_col)
    if ind.source == "yahoo":
        if ind.series_id != "XAUUSD":  # gold (GC=F) is the only Yahoo series we fetch
            raise ValueError(f"no Yahoo prediction fetch wired for {ind.series_id}")
        return yahoo.gold_history()
    return fred.fetch_observations(ind.series_id, os.environ["FRED_API_KEY"],
                                   FRED_FULL_LIMIT, ind.units_transform)


def _prepared_series(entry, raw):
    """(cleaned [(date,float)], cadence) — derive applied, dailies resampled weekly.
    Baked entries are already post-derive, so we skip ind.derive for them (and
    BankingIndicator carries no `derive` attribute at all)."""
    derive = getattr(entry.indicator, "derive", None)
    if derive and not entry.baked:
        raw = derive(raw)
    cleaned = util.clean(raw)
    cad = cadence.infer(cleaned)
    if cad == "daily":
        cleaned = cadence.weekly_resample(cleaned)
    return cleaned, cad


def run_tournament(pred_dir, dry_run, entries):
    """Backtest every model per indicator; write models.json. Returns the
    number of indicators that got a champion."""
    fixture_cache = _load_fixture_histories() if dry_run else {}
    registry = {}
    for entry in entries:
        try:
            cleaned, cad = _prepared_series(entry, _fetch_history(entry, dry_run, fixture_cache))
            if cad in ("annual", "unknown"):
                continue
            season = cadence.SEASON[cad]
            values = [v for _, v in cleaned]
            result = backtest.tournament(values, season, MAX_ORIGINS[cad])
            if result is None:
                continue
            registry[entry.key] = dict(
                result, cadence=cad, season=season,
                champion=f"{result['champion']}@{models.VERSIONS[result['champion']]}",
                explain=explain.SKELETONS[result["champion"]],
            )
            print(f"tournament: {entry.key} -> {registry[entry.key]['champion']} "
                  f"(skill {result['skill']:.2f})")
        except Exception as exc:  # noqa: BLE001 - one series never sinks the job
            print(f"WARN: tournament failed for {entry.key}: {exc}", file=sys.stderr)
    build.write_lens_file(pred_dir / "models.json",
                          {"generated_at": _now(), "indicators": registry})
    return len(registry)


def _lens_title(entry):
    cat = _find_cat(entry.category)
    if cat:
        for lens in cat["lenses"]:
            if lens.id == entry.lens_id:
                return lens.title
    return entry.lens_id


def _make_open_entry(entry, cleaned, cad, champ_rec):
    ind = entry.indicator
    name = champ_rec["champion"].split("@")[0]
    values = [v for _, v in cleaned]
    point = models.predict_one(name, values, champ_rec["season"])
    target = cadence.next_period(cleaned[-1][0], cad)
    _, current_status = ind.rule(cleaned)
    _, implied_status = ind.rule(cleaned + [(target, point)])
    return {
        "id": f"{entry.key}@{target}", "key": entry.key,
        "category": entry.category, "lens": entry.lens_id, "indicator": ind.id,
        "series_id": getattr(ind, "series_id", ""),  # BankingIndicator has none
        "horizon": "next-print",
        "target_period": target, "due": cadence.due_estimate(target, cad),
        "made_at": _now(), "model": champ_rec["champion"],
        "point": round(point, 4),
        "lo": round(point + champ_rec["err_lo"], 4),
        "hi": round(point + champ_rec["err_hi"], 4),
        "unit": ind.unit, "value_format": ind.value_format,
        "prev_value": values[-1],
        "why": explain.why(name, cad, values, ind.short),
        "implied_status": implied_status, "current_status": current_status,
        "descriptive": entry.descriptive,    # carries no badge (info / neutral lens)
        "market_price": entry.market_price,  # tradeable price -> market-price note + held out of edge stat
        "title": ind.title, "short": ind.short,
        "lens_title": _lens_title(entry),
        "href": brief.lens_href(entry.category, entry.lens_id),
        "grade": None,
    }


def _check_revisions(pred_dir, entry, cleaned, graded_rows):
    """Footnote pass: recently graded entries whose source value moved get
    grade.revised_to set. Never alters hit (spec §3). graded_rows is the
    ledger loaded once per run — safe because this pass never reads the one
    field set_revision mutates (grade.revised_to)."""
    recent_dates = {d for d, _ in cleaned[-(REVISION_LOOKBACK + 2):]}
    for row in graded_rows:
        if row["key"] != entry.key or not row.get("grade"):
            continue
        m = grade.match_actual(cleaned, row["target_period"])
        if not m:
            continue
        actual_date, current_value = m
        if actual_date in recent_dates and abs(current_value - row["grade"]["actual"]) > 1e-9:
            ledger.set_revision(pred_dir, row["id"], row["made_at"][:4], current_value)


def run_daily(pred_dir, dry_run, entries):
    """Grade -> footnote -> predict, per indicator (spec §5)."""
    fixture_cache = _load_fixture_histories() if dry_run else {}
    models_path = pred_dir / "models.json"
    registry = {}
    if models_path.exists():
        try:
            registry = json.loads(models_path.read_text(encoding="utf-8")).get("indicators", {})
        except (ValueError, OSError):
            pass
    open_by_key = {e["key"]: e for e in ledger.load_open(pred_dir)}
    graded_rows = ledger.load_all_graded(pred_dir)
    next_open = []
    for entry in entries:
        graded_this_run = False
        try:
            cleaned, cad = _prepared_series(entry, _fetch_history(entry, dry_run, fixture_cache))
            if not cleaned or cad in ("annual", "unknown"):
                if entry.key in open_by_key:
                    next_open.append(open_by_key[entry.key])  # data gap: keep prior open entry
                continue
            prior = open_by_key.get(entry.key)
            if prior:
                m = grade.match_actual(cleaned, prior["target_period"])
                if m:
                    actual_date, actual = m
                    upto = [(d, v) for d, v in cleaned if d <= actual_date]
                    _, actual_status = entry.indicator.rule(upto)
                    graded = dict(prior, grade=grade.grade_entry(prior, actual, actual_status))
                    ledger.append_graded(pred_dir, graded)
                    prior = None  # consumed; a fresh prediction follows
                    graded_this_run = True
            _check_revisions(pred_dir, entry, cleaned, graded_rows)
            if prior is not None:
                next_open.append(prior)          # target not printed yet: stays open
            elif entry.key in registry:
                next_open.append(_make_open_entry(entry, cleaned, cad, registry[entry.key]))
            # no champion (pre-bootstrap): grade/footnote ran, nothing emitted
        except Exception as exc:  # noqa: BLE001 - one series never sinks the job
            print(f"WARN: daily prediction failed for {entry.key}: {exc}", file=sys.stderr)
            # Keep the prior open entry — unless its target was already graded this
            # run (a post-grade failure must not resurrect a now-graded prediction
            # as a duplicate "open" id).
            if entry.key in open_by_key and not graded_this_run:
                next_open.append(open_by_key[entry.key])
    wrote = ledger.write_views(pred_dir, next_open, ledger.load_all_graded(pred_dir))
    print(f"predictions: {len(next_open)} open; wrote {', '.join(wrote) or 'nothing (unchanged)'}")
    return len(next_open)

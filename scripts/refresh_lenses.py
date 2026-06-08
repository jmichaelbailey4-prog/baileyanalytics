#!/usr/bin/env python3
"""Fetch FRED data for all lenses and write data/lenses/*.json.

Usage:
  python scripts/refresh_lenses.py            # live (needs FRED_API_KEY)
  python scripts/refresh_lenses.py --dry-run  # offline, uses test fixture data
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `lenses` importable
from datetime import date

from lenses import build, coingecko, config, fdic, fred, stooq, util

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "lenses"
BANK_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "banking"
MARKETS_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "markets"
FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fetched_sample.json"
FDIC_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fdic_sample.json"
MARKET_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "markets_sample.json"
CRYPTO_HISTORY = MARKETS_OUT_DIR / "_crypto_history.json"
CRYPTO_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "coingecko_sample.json"


def unique_specs(lenses):
    """Map fetch_key -> (series_id, units_transform, max_limit) across all lenses."""
    specs = {}
    for lens in lenses:
        for ind in lens.indicators:
            if getattr(ind, "source", "fred") != "fred":
                continue  # non-FRED indicators (e.g. Stooq gold) are injected separately
            cur = specs.get(ind.fetch_key)
            limit = ind.limit if cur is None else max(cur[2], ind.limit)
            specs[ind.fetch_key] = (ind.series_id, ind.units_transform, limit)
    return specs


def fetch_all(lenses, api_key):
    """Fetch every needed series once. Returns (fetched, failed_keys)."""
    fetched, failed = {}, set()
    for key, (series_id, units, limit) in unique_specs(lenses).items():
        try:
            fetched[key] = fred.fetch_observations(series_id, api_key, limit, units)
        except Exception as exc:  # noqa: BLE001 - keep going, skip dependent lenses
            print(f"WARN: fetch failed for {series_id}: {exc}", file=sys.stderr)
            failed.add(key)
    if config.USREC_KEY not in fetched:
        try:
            fetched[config.USREC_KEY] = fred.fetch_observations("USREC", api_key, config.USREC_LIMIT)
        except Exception as exc:  # noqa: BLE001 - shading is non-critical
            print(f"WARN: USREC fetch failed: {exc}", file=sys.stderr)
            fetched[config.USREC_KEY] = []
    return fetched, failed


def lens_ready(lens, failed):
    return not any(ind.fetch_key in failed for ind in lens.indicators)


YEARS_OF_HISTORY = 20


def _indicator_metric(ind):
    """The metric spec for an indicator, keyed by its id for national_quarterly."""
    return dict(ind.metric, key=ind.id)


def fetch_banking():
    """Fetch every banking series/tier/ranking live. Returns {lens_id: (series, tiers, rankings)}.

    National series are aggregated quarterly across all banks from /financials — one
    bank fetch per quarter, shared across every indicator. Tiers and rankings use the
    latest reporting quarter.
    """
    latest = fdic.latest_repdte()
    quarters = fdic.quarter_ends(date.today().year - YEARS_OF_HISTORY, latest)

    # One global pass: every banking indicator's metric, fetched once per quarter.
    all_metrics = [_indicator_metric(ind) for lens in config.BANKING_LENSES for ind in lens.indicators]
    all_series = fdic.national_quarterly(all_metrics, quarters)

    result = {}
    for lens in config.BANKING_LENSES:
        series = {ind.id: all_series.get(ind.id, []) for ind in lens.indicators}
        tiers = fdic.tier_aggregates(lens.tier_metrics, latest, config.TIERS) if lens.tier_metrics else []
        rankings = {spec["title"]: fdic.ranking(
                        spec["metric_field"], latest, spec["asset_min"], spec["limit"],
                        sort_order=spec.get("sort_order", "DESC"),
                        min_base_fields=spec.get("min_base_fields"),
                        min_base=spec.get("min_base", 0),
                        max_value=spec.get("max_value"),
                        min_value=spec.get("min_value"),
                        ratio_filters=spec.get("ratio_filters"))
                    for spec in lens.rankings}
        result[lens.id] = (series, tiers, rankings)
    return result


def build_banking(fetched):
    """Build the four banking lens JSONs from a {lens_id: (series, tiers, rankings)} dict."""
    out = []
    for lens in config.BANKING_LENSES:
        series, tiers, rankings = fetched[lens.id]
        out.append(build.build_banking_lens(lens, series, tiers, rankings))
    return out


def build_banking_from_fixture():
    data = json.loads(FDIC_FIXTURE.read_text(encoding="utf-8"))
    return build_banking(data)


def refresh_economic(dry_run):
    """Build + write the economic (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    if dry_run:
        fetched = json.loads(FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.LENSES, api_key)

    ready = [lens for lens in config.LENSES if lens_ready(lens, failed)]
    for lens in config.LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready], OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all economic lens data up to date.")
    return 0


def refresh_banking(dry_run):
    """Build + write the banking (FDIC) lenses. Additive — never raises."""
    try:
        bank_jsons = build_banking_from_fixture() if dry_run else build_banking(fetch_banking())
        written = build.write_outputs(bank_jsons, BANK_OUT_DIR)
        for path in written:
            print(f"Wrote {path}")
        if not written:
            print("No changes — all banking data up to date.")
    except Exception as exc:  # noqa: BLE001 - never break the run on a banking failure
        print(f"WARN: banking refresh failed ({exc}); keeping previous banking data", file=sys.stderr)


def _btc_eth_ratio(fetched):
    """BTC/ETH price ratio from already-fetched FRED series (no extra network call)."""
    btc = {o["date"]: util.to_float(o["value"]) for o in fetched.get("CBBTCUSD:lin", [])}
    eth = {o["date"]: util.to_float(o["value"]) for o in fetched.get("CBETHUSD:lin", [])}
    out = []
    for d in sorted(set(btc) & set(eth)):
        if btc[d] is not None and eth[d] not in (None, 0):
            out.append({"date": d, "value": round(btc[d] / eth[d], 4)})
    return out


def _load_crypto_history():
    if CRYPTO_HISTORY.exists():
        try:
            return json.loads(CRYPTO_HISTORY.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {"rotation": [], "dominance": []}


def _build_crypto(dry_run, fetched):
    """Build the crypto-structure lens JSON, accumulating history. Additive — on any
    failure, keep the prior crypto data (re-read it so the markets index stays complete)."""
    try:
        if dry_run:
            fresh = json.loads(CRYPTO_FIXTURE.read_text(encoding="utf-8"))
        else:
            fresh = coingecko.crypto_market_structure()
        hist = _load_crypto_history()
        rotation = util.merge_series(hist.get("rotation"), fresh["rotation"])
        dominance = util.merge_series(hist.get("dominance"), [fresh["dominance_point"]])
        CRYPTO_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        CRYPTO_HISTORY.write_text(
            json.dumps({"rotation": rotation, "dominance": dominance}, indent=2) + "\n",
            encoding="utf-8")
        return build.build_crypto_lens(rotation, dominance, _btc_eth_ratio(fetched))
    except Exception as exc:  # noqa: BLE001 - never break the run on a crypto failure
        print(f"WARN: crypto refresh failed ({exc}); keeping previous crypto data", file=sys.stderr)
        prior = MARKETS_OUT_DIR / "crypto-structure.json"
        if prior.exists():
            try:
                return json.loads(prior.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None
        return None


def _prior_scoreboard_gold():
    """Prior gold observations from the existing scoreboard JSON (fallback if Stooq fails)."""
    path = MARKETS_OUT_DIR / "market-scoreboard.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ind in data.get("indicators", []):
                if ind.get("id") == "gold":
                    return ind.get("observations", [])
        except (ValueError, OSError):
            pass
    return []


def _inject_gold(fetched, dry_run):
    """Fetch gold from Stooq and inject it under its scoreboard fetch_key (FRED dropped
    its gold series). Additive — on failure, fall back to prior data so the lens still
    builds. In dry-run the markets fixture already carries XAUUSD:lin."""
    if dry_run:
        return
    key = "XAUUSD:lin"
    try:
        rows = stooq.gold_history()
        if not rows:
            raise ValueError("empty gold series")
        fetched[key] = rows
    except Exception as exc:  # noqa: BLE001 - never break the run on a gold failure
        print(f"WARN: gold (Stooq) fetch failed ({exc}); keeping previous gold data", file=sys.stderr)
        fetched[key] = _prior_scoreboard_gold()


def refresh_markets(dry_run):
    """Build + write the markets lenses (FRED lenses + Stooq gold + the CoinGecko crypto
    lens). Returns an exit code (0 ok, non-zero error). The gold and crypto pieces are
    additive — a Stooq/CoinGecko failure never aborts the run; the FRED lenses still publish.
    """
    if dry_run:
        fetched = json.loads(MARKET_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.MARKET_FRED_LENSES, api_key)

    _inject_gold(fetched, dry_run)

    ready = [lens for lens in config.MARKET_FRED_LENSES if lens_ready(lens, failed)]
    for lens in config.MARKET_FRED_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)

    market_jsons = [build.build_lens(lens, fetched) for lens in ready]
    crypto_json = _build_crypto(dry_run, fetched)
    if crypto_json:
        market_jsons.append(crypto_json)

    written = build.write_outputs(market_jsons, MARKETS_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all markets data up to date.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refresh dashboard data from public sources.")
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    parser.add_argument("--economic", action="store_true", help="refresh only the economic (FRED) lenses")
    parser.add_argument("--banking", action="store_true", help="refresh only the banking (FDIC) lenses")
    parser.add_argument("--markets", action="store_true", help="refresh only the markets lenses")
    args = parser.parse_args(argv)

    # No source flag = refresh everything (handy for manual/local runs); each
    # flag scopes the run so a workflow can give each source its own cadence.
    any_flag = args.economic or args.banking or args.markets
    do_economic = args.economic or not any_flag
    do_banking = args.banking or not any_flag
    do_markets = args.markets or not any_flag

    code = 0
    if do_economic:
        code = refresh_economic(args.dry_run)
        if code:
            return code
    if do_markets:
        mc = refresh_markets(args.dry_run)
        if mc:
            code = mc
    if do_banking:
        refresh_banking(args.dry_run)
    return code


if __name__ == "__main__":
    sys.exit(main())

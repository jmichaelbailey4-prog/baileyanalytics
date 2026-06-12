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

from lenses import brief, build, coingecko, config, eia, epu, fdic, feed, fred, imf, nyfed, today, util, yahoo

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "lenses"
BANK_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "banking"
MARKETS_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "markets"
ENERGY_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "energy"
HOUSING_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "housing"
CONSUMER_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "consumer"
GLOBAL_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "global"
BUSINESS_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "business"
FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fetched_sample.json"
FDIC_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "fdic_sample.json"
MARKET_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "markets_sample.json"
ENERGY_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "energy_sample.json"
HOUSING_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "housing_sample.json"
CONSUMER_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "consumer_sample.json"
GLOBAL_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "global_sample.json"
BUSINESS_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "business_sample.json"
CRYPTO_HISTORY = MARKETS_OUT_DIR / "_crypto_history.json"
CRYPTO_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "coingecko_sample.json"
BRIEF_OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "brief"
BRIEF_FIXTURE = Path(__file__).resolve().parent / "tests" / "fixtures" / "brief_indices_sample.json"
# Repo root, so GitHub Pages serves it at /feed.xml (the workflow commit step
# must include this path alongside data/).
FEED_PATH = Path(__file__).resolve().parent.parent / "feed.xml"

# category -> the module-global out-dir whose index.json feeds the brief.
# 'economic' lives in data/lenses/ (not data/economic/).
def _brief_index_dirs():
    return {
        "economic": OUT_DIR,
        "banking": BANK_OUT_DIR,
        "markets": MARKETS_OUT_DIR,
        "energy": ENERGY_OUT_DIR,
        "housing": HOUSING_OUT_DIR,
        "consumer": CONSUMER_OUT_DIR,
        "business": BUSINESS_OUT_DIR,
        "global": GLOBAL_OUT_DIR,
    }


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

    # Computed: 2y-vs-Fed spread for the rate-expectations indicator (mirrors
    # the business-shares pattern; falls back to prior data if an input failed).
    spread = util.spread_ffill(fetched.get("DGS2:lin"), fetched.get("FEDFUNDS:lin"))
    fetched["DGS2_FEDFUNDS_SPREAD:lin"] = (
        spread or _prior_obs(OUT_DIR, "cost-of-money", "rate-expectations"))

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
    """Fetch gold from Yahoo Finance and inject it under its scoreboard fetch_key (FRED
    dropped its gold series). Additive — on failure, fall back to prior data so the lens
    still builds. In dry-run the markets fixture already carries XAUUSD:lin."""
    if dry_run:
        return
    key = "XAUUSD:lin"
    try:
        rows = yahoo.gold_history()
        if not rows:
            raise ValueError("empty gold series")
        fetched[key] = rows
    except Exception as exc:  # noqa: BLE001 - never break the run on a gold failure
        print(f"WARN: gold (Yahoo) fetch failed ({exc}); keeping previous gold data", file=sys.stderr)
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


def _prior_obs(out_dir, lens_id, ind_id):
    """Prior observations for one indicator from its existing lens JSON
    (fallback when an injected source's fetch fails)."""
    path = out_dir / f"{lens_id}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ind in data.get("indicators", []):
                if ind.get("id") == ind_id:
                    return ind.get("observations", [])
        except (ValueError, OSError):
            pass
    return []


def _prior_energy_obs(lens_id, ind_id):
    return _prior_obs(ENERGY_OUT_DIR, lens_id, ind_id)


def _inject_generation_shares(fetched, api_key):
    """Compute renewables/natural-gas share of generation + total net generation
    from EIA's generation-mix dataset, inject under their indicator fetch_keys."""
    mix = eia.generation_mix(api_key)
    fetched["NET_GEN_TOTAL:lin"] = mix["total"]
    fetched["RENEW_SHARE:lin"] = util.pct_share(mix["renewable"], mix["total"])
    fetched["NG_SHARE:lin"] = util.pct_share(mix["natgas"], mix["total"])


def _inject_eia(fetched, dry_run):
    """Populate every EIA indicator (lenses 1-3). Additive: on a missing key or a
    fetch failure, fall back to prior data so the FRED commodities lens and any
    unaffected lenses still publish. In dry-run the fixture already carries the keys."""
    if dry_run:
        return
    api_key = os.environ.get("EIA_API_KEY")
    computed = {"renewables-share", "natgas-share", "net-generation"}
    if not api_key:
        print("WARN: EIA_API_KEY not set; keeping previous energy data", file=sys.stderr)
        for lens in config.ENERGY_EIA_LENSES:
            for ind in lens.indicators:
                fetched[ind.fetch_key] = _prior_energy_obs(lens.id, ind.id)
        return
    # Directly-routed EIA indicators
    for lens in config.ENERGY_EIA_LENSES:
        for ind in lens.indicators:
            if ind.id in computed or not ind.eia_route:
                continue
            try:
                fetched[ind.fetch_key] = eia.fetch_series(
                    ind.eia_route, ind.eia_facets, ind.eia_freq, api_key, ind.limit, ind.eia_col)
            except Exception as exc:  # noqa: BLE001 - keep prior on failure
                print(f"WARN: EIA fetch failed for {ind.series_id}: {exc}", file=sys.stderr)
                fetched[ind.fetch_key] = _prior_energy_obs(lens.id, ind.id)
    # Computed generation shares (renewables/natgas/total)
    try:
        _inject_generation_shares(fetched, api_key)
    except Exception as exc:  # noqa: BLE001 - keep prior on failure
        print(f"WARN: EIA generation mix failed ({exc}); keeping previous data", file=sys.stderr)
        for ind_id, key in (("net-generation", "NET_GEN_TOTAL:lin"),
                            ("renewables-share", "RENEW_SHARE:lin"),
                            ("natgas-share", "NG_SHARE:lin")):
            fetched[key] = _prior_energy_obs("energy-electricity", ind_id)


def refresh_energy(dry_run):
    """Build + write the energy lenses (EIA lenses 1-3 + the FRED commodities lens).
    Additive — an EIA failure never aborts the run; the FRED lens still publishes."""
    if dry_run:
        fetched = json.loads(ENERGY_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.ENERGY_LENSES, api_key)

    _inject_eia(fetched, dry_run)

    ready = [lens for lens in config.ENERGY_LENSES if lens_ready(lens, failed)]
    for lens in config.ENERGY_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready], ENERGY_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all energy data up to date.")
    return 0


def refresh_housing(dry_run):
    """Build + write the housing (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    if dry_run:
        fetched = json.loads(HOUSING_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.HOUSING_LENSES, api_key)

    ready = [lens for lens in config.HOUSING_LENSES if lens_ready(lens, failed)]
    for lens in config.HOUSING_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No housing lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  HOUSING_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all housing data up to date.")
    return 0


def refresh_consumer(dry_run):
    """Build + write the consumer (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    if dry_run:
        fetched = json.loads(CONSUMER_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.CONSUMER_LENSES, api_key)

    ready = [lens for lens in config.CONSUMER_LENSES if lens_ready(lens, failed)]
    for lens in config.CONSUMER_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No consumer lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  CONSUMER_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all consumer data up to date.")
    return 0


def _prior_business_obs(lens_id, ind_id):
    """Prior observations for one business indicator from its existing lens JSON
    (fallback when a share input is unavailable)."""
    path = BUSINESS_OUT_DIR / f"{lens_id}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for ind in data.get("indicators", []):
                if ind.get("id") == ind_id:
                    return ind.get("observations", [])
        except (ValueError, OSError):
            pass
    return []


def _inject_business_shares(fetched, api_key):
    """Compute the two cross-series shares and inject them under their computed
    fetch keys (mirrors the electricity generation-share pattern). The high-
    propensity share needs no extra network call; the profit share needs GDP,
    fetched here solely as the denominator (dry-run fixtures carry GDP:lin).
    Additive: a missing input falls back to prior published data."""
    hp = util.pct_share(fetched.get("BAHBATOTALSAUS:lin"), fetched.get("BABATOTALSAUS:lin"))
    fetched["BFS_HP_SHARE:lin"] = hp or _prior_business_obs("business-formation", "hp-share")
    gdp = fetched.get("GDP:lin")
    if gdp is None and api_key:
        try:
            gdp = fred.fetch_observations("GDP", api_key, 104)
        except Exception as exc:  # noqa: BLE001 - keep prior on failure
            print(f"WARN: GDP fetch failed ({exc}); keeping previous profit share", file=sys.stderr)
    share = util.pct_share(fetched.get("CP:lin"), gdp) if gdp else []
    fetched["CP_GDP_SHARE:lin"] = share or _prior_business_obs("business-profitability", "profit-share")


def refresh_business(dry_run):
    """Build + write the business (FRED) lenses. Returns an exit code (0 ok, non-zero error)."""
    api_key = None
    if dry_run:
        fetched = json.loads(BUSINESS_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.BUSINESS_LENSES, api_key)

    _inject_business_shares(fetched, api_key)

    ready = [lens for lens in config.BUSINESS_LENSES if lens_ready(lens, failed)]
    for lens in config.BUSINESS_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No business lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  BUSINESS_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all business data up to date.")
    return 0


def _inject_global(fetched, dry_run):
    """Populate the non-FRED global indicators (IMF WEO, NY Fed GSCPI, the two
    EPU files). Additive: each source is guarded individually, falling back to
    prior data so a single failed source never blanks the others. IMF actuals
    are truncated at the current year; next-year forecasts land in the
    late-binding imf.FORECASTS registry the narrative rules read at build time.

    In dry-run the fixture already carries every key; only the `_forecasts`
    side key needs lifting into the registry."""
    if dry_run:
        imf.FORECASTS.update(fetched.get("_forecasts", {}))
        return

    # Lens id by indicator, for prior-data fallback lookups.
    homes = {ind.id: (lens.id, ind) for lens in config.GLOBAL_LENSES
             for ind in lens.indicators}
    imf_inds = [ind for _, ind in homes.values() if ind.source == "imf"]

    # IMF WEO — one batched request for every country x indicator.
    try:
        countries = sorted({ind.imf_key.split(".")[0] for ind in imf_inds})
        indicators = sorted({ind.imf_key.split(".")[1] for ind in imf_inds})
        series = imf.weo_series(countries, indicators)
        for ind in imf_inds:
            actuals, forecast = imf.split_actuals(series.get(ind.imf_key, []))
            if not actuals:
                raise ValueError(f"empty WEO series {ind.imf_key}")
            fetched[ind.fetch_key] = actuals
            if forecast:
                imf.FORECASTS[ind.imf_key] = forecast
    except Exception as exc:  # noqa: BLE001 - keep prior on failure
        print(f"WARN: IMF WEO fetch failed ({exc}); keeping previous data", file=sys.stderr)
        for ind in imf_inds:
            fetched[ind.fetch_key] = _prior_obs(GLOBAL_OUT_DIR, homes[ind.id][0], ind.id)

    # NY Fed GSCPI
    try:
        rows = nyfed.gscpi()
        if not rows:
            raise ValueError("empty GSCPI series")
        fetched["GSCPI:lin"] = rows
    except Exception as exc:  # noqa: BLE001 - keep prior on failure
        print(f"WARN: GSCPI fetch failed ({exc}); keeping previous data", file=sys.stderr)
        fetched["GSCPI:lin"] = _prior_obs(GLOBAL_OUT_DIR, "global-trade-supply", "gscpi")

    # EPU — the two files are independent downloads, guarded individually.
    for key, fetch, ind_id in (("USEPU:lin", epu.us_epu, "us-epu"),
                               ("GEPU:lin", epu.global_epu, "gepu")):
        try:
            rows = fetch()
            if not rows:
                raise ValueError("empty EPU series")
            fetched[key] = rows
        except Exception as exc:  # noqa: BLE001 - keep prior on failure
            print(f"WARN: EPU fetch failed for {key} ({exc}); keeping previous data",
                  file=sys.stderr)
            fetched[key] = _prior_obs(GLOBAL_OUT_DIR, "global-uncertainty", ind_id)


def refresh_global(dry_run):
    """Build + write the Global Economy lenses (FRED + IMF + NY Fed + EPU).
    Returns an exit code (0 ok, non-zero error). The injected sources are
    additive — a failure falls back to prior data and never aborts the run."""
    if dry_run:
        fetched = json.loads(GLOBAL_FIXTURE.read_text(encoding="utf-8"))
        failed = set()
    else:
        api_key = os.environ.get("FRED_API_KEY")
        if not api_key:
            print("FRED_API_KEY not set", file=sys.stderr)
            return 1
        fetched, failed = fetch_all(config.GLOBAL_LENSES, api_key)

    _inject_global(fetched, dry_run)

    ready = [lens for lens in config.GLOBAL_LENSES if lens_ready(lens, failed)]
    for lens in config.GLOBAL_LENSES:
        if lens not in ready:
            print(f"SKIP: {lens.id} (a source series failed; keeping previous data)", file=sys.stderr)
    if not ready:
        print("No global lenses could be built", file=sys.stderr)
        return 2

    written = build.write_outputs([build.build_lens(lens, fetched) for lens in ready],
                                  GLOBAL_OUT_DIR)
    for path in written:
        print(f"Wrote {path}")
    if not written:
        print("No changes — all global data up to date.")
    return 0


def _load_brief_indices(dry_run):
    """Return {category: index_json}. Dry-run reads one fixture file; live reads
    each category's index.json from its out-dir, skipping any not yet present."""
    if dry_run:
        return json.loads(BRIEF_FIXTURE.read_text(encoding="utf-8"))
    indices = {}
    for category, out_dir in _brief_index_dirs().items():
        path = out_dir / "index.json"
        if path.exists():
            try:
                indices[category] = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
    return indices


def _load_prior_state():
    path = BRIEF_OUT_DIR / "_prior_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    return {}


def refresh_brief(dry_run):
    """Build + write the merged data/brief/today.json (the brief plus the
    absorbed State of Things: verdict, watching, pressure, category sentences)
    and _prior_state.json from the current per-category index.json files.
    Additive — never raises; a missing category is simply absent."""
    try:
        indices = _load_brief_indices(dry_run)
        today_json, new_state = today.build_today(
            indices, _load_prior_state(),
            open_predictions=_load_open_predictions())
        # Content-aware writes (skip when only the timestamp changed) keep the
        # workflow's "no data change -> no commit" path intact on quiet days.
        wrote = build.write_lens_file(BRIEF_OUT_DIR / "today.json", today_json)
        build.write_lens_file(BRIEF_OUT_DIR / "_prior_state.json", new_state)
        print(f"Wrote {BRIEF_OUT_DIR / 'today.json'}" if wrote
              else "No brief changes — Today's Brief is up to date.")
        # RSS: one item per day, rolling 30 days, regenerated only when the
        # brief changed (keeps the quiet-day "no data change -> no commit" path).
        # Guarded separately: a feed hiccup must not read as a brief failure.
        if wrote:
            try:
                items_path = BRIEF_OUT_DIR / "_feed_items.json"
                try:
                    existing = json.loads(items_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    existing = []
                items = feed.merge_items(existing, feed.build_item(today_json))
                items_path.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
                FEED_PATH.write_text(feed.render_feed(items) + "\n", encoding="utf-8")
                print(f"Wrote {FEED_PATH}")
            except Exception as exc:  # noqa: BLE001 - feed is additive
                print(f"WARN: feed build failed ({exc}); keeping previous feed.xml",
                      file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - never break the run on a brief failure
        print(f"WARN: brief build failed ({exc}); keeping previous brief", file=sys.stderr)


def _load_open_predictions():
    """Open predictions for the brief's watching block (None when the
    prediction pipeline hasn't run — the block is simply omitted)."""
    path = Path(__file__).resolve().parent.parent / "data" / "predictions" / "open.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("predictions", [])
        except (ValueError, OSError):
            pass
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Refresh dashboard data from public sources.")
    parser.add_argument("--dry-run", action="store_true", help="use fixture data, no network")
    parser.add_argument("--economic", action="store_true", help="refresh only the economic (FRED) lenses")
    parser.add_argument("--banking", action="store_true", help="refresh only the banking (FDIC) lenses")
    parser.add_argument("--markets", action="store_true", help="refresh only the markets lenses")
    parser.add_argument("--energy", action="store_true", help="refresh only the energy lenses")
    parser.add_argument("--housing", action="store_true", help="refresh only the housing lenses")
    parser.add_argument("--consumer", action="store_true", help="refresh only the consumer (FRED) lenses")
    # `global` is a Python keyword, so argparse needs an explicit dest.
    parser.add_argument("--global", dest="global_econ", action="store_true",
                        help="refresh only the Global Economy lenses")
    parser.add_argument("--business", action="store_true", help="refresh only the business (FRED) lenses")
    parser.add_argument("--brief", action="store_true",
                        help="rebuild only Today's Brief (incl. the merged verdict) from existing indices")
    # Deprecated alias (the State of Things merged into the brief, 2026-06-12).
    parser.add_argument("--state", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    # No source flag = refresh everything (handy for manual/local runs); each
    # flag scopes the run so a workflow can give each source its own cadence.
    any_flag = (args.economic or args.banking or args.markets or args.energy
                or args.housing or args.consumer or args.global_econ or args.business
                or args.brief or args.state)
    do_economic = args.economic or not any_flag
    do_banking = args.banking or not any_flag
    do_markets = args.markets or not any_flag
    do_energy = args.energy or not any_flag
    do_housing = args.housing or not any_flag
    do_consumer = args.consumer or not any_flag
    do_business = args.business or not any_flag
    do_global = args.global_econ or not any_flag
    if args.state:
        print("WARN: --state is deprecated; the brief pass now includes the verdict.",
              file=sys.stderr)
    do_brief = args.brief or args.state or not any_flag

    code = 0
    if do_economic:
        code = refresh_economic(args.dry_run)
        if code:
            return code
    if do_markets:
        mc = refresh_markets(args.dry_run)
        if mc:
            code = mc
    if do_energy:
        ec = refresh_energy(args.dry_run)
        if ec:
            code = ec
    if do_housing:
        hc = refresh_housing(args.dry_run)
        if hc:
            code = hc
    if do_consumer:
        cc = refresh_consumer(args.dry_run)
        if cc:
            code = cc
    if do_global:
        gc = refresh_global(args.dry_run)
        if gc:
            code = gc
    if do_business:
        bc = refresh_business(args.dry_run)
        if bc:
            code = bc
    if do_banking:
        refresh_banking(args.dry_run)
    if do_brief:
        refresh_brief(args.dry_run)
    return code


if __name__ == "__main__":
    sys.exit(main())

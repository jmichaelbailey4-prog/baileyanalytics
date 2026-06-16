"""CoinGecko API access — crypto market-structure data. No key (free public tier).

The free tier has no historical total-market-cap or dominance *series*, so the
large-vs-small rotation is built from per-coin market-cap history
(`/coins/{id}/market_chart`, 365 days free). BTC dominance comes from `/global`
as a current point and is accumulated daily by the caller.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.coingecko.com/api/v3"
_UA = "baileyanalytics/1.0 (+https://baileyanalytics.com)"

# Top stablecoins by id — excluded from the "small/mid-cap" basket (a price≈$1
# heuristic backstops anything not listed here).
STABLECOINS = {
    "tether", "usd-coin", "dai", "first-digital-usd", "usds", "ethena-usde",
    "binance-usd", "trueusd", "paxos-standard", "usdd", "frax", "gemini-dollar",
}


def _get(path, params, timeout):
    """GET a CoinGecko endpoint. Uses a free demo API key if COINGECKO_API_KEY is set
    (raises the rate limit and stabilizes it); otherwise the keyless public tier, which
    is aggressively rate-limited. Backs off and retries on HTTP 429."""
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": _UA}
    key = os.environ.get("COINGECKO_API_KEY")
    if key:
        headers["x-cg-demo-api-key"] = key
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            # Retry rate limits (429) and transient server errors (5xx) with a
            # bounded backoff; client errors (4xx) raise immediately.
            if exc.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise


def top_coins(n=10, timeout=15):
    """Top `n` non-stablecoin coins by market cap: [{'id','symbol','market_cap'}]."""
    rows = _get("/coins/markets",
                {"vs_currency": "usd", "order": "market_cap_desc",
                 "per_page": n + 10, "page": 1}, timeout)
    out = []
    for r in rows:
        if r.get("id") in STABLECOINS:
            continue
        price = r.get("current_price") or 0
        if 0.95 <= price <= 1.05:  # stablecoin heuristic backstop
            continue
        out.append({"id": r["id"], "symbol": r.get("symbol", ""),
                    "market_cap": r.get("market_cap") or 0})
        if len(out) >= n:
            break
    return out


def market_cap_history(coin_id, days=365, timeout=15):
    """Daily market-cap history for one coin: [{'date','value'}], oldest-first."""
    data = _get(f"/coins/{coin_id}/market_chart",
                {"vs_currency": "usd", "days": days, "interval": "daily"}, timeout)
    out = []
    for ms, cap in data.get("market_caps", []):
        d = time.strftime("%Y-%m-%d", time.gmtime(ms / 1000))
        out.append({"date": d, "value": cap})
    return out


def global_metrics(timeout=15):
    """Current global crypto metrics. Returns {'btc_dominance': float|None}."""
    data = _get("/global", {}, timeout).get("data", {})
    pct = data.get("market_cap_percentage", {}).get("btc")
    return {"btc_dominance": pct}


def basket_history(coin_histories):
    """Sum market caps by date across coins. Input: list of [{'date','value'}]."""
    totals = {}
    for hist in coin_histories:
        for pt in hist:
            totals[pt["date"]] = totals.get(pt["date"], 0.0) + (pt["value"] or 0.0)
    return [{"date": d, "value": totals[d]} for d in sorted(totals)]


def compute_rotation(large_basket, small_basket):
    """Small-vs-large relative performance, indexed to 100 at the first common date.

    Returns [{'date','value'}] where value = (small_idx / large_idx) * 100. Rising
    means the small/mid-cap basket is outperforming the large-cap basket.
    """
    large = {p["date"]: p["value"] for p in large_basket}
    small = {p["date"]: p["value"] for p in small_basket}
    dates = [d for d in sorted(set(large) & set(small)) if large[d] and small[d]]
    if not dates:
        return []
    l0, s0 = large[dates[0]], small[dates[0]]
    out = []
    for d in dates:
        l_idx = large[d] / l0 * 100
        s_idx = small[d] / s0 * 100
        out.append({"date": d, "value": round(s_idx / l_idx * 100, 2)})
    return out


def crypto_market_structure(timeout=15, throttle=2.5):
    """Fetch + compute today's rotation series and current BTC dominance.

    Returns {'rotation': [{date,value}], 'dominance_point': {date, value}}.
    The top two non-stablecoins (reliably BTC + ETH) form the large-cap basket;
    ranks 3-10 form the small/mid-cap basket.
    """
    import datetime
    coins = top_coins(10, timeout)
    histories = {}
    for c in coins:
        histories[c["id"]] = market_cap_history(c["id"], 365, timeout)
        time.sleep(throttle)
    large = basket_history([histories[c["id"]] for c in coins[:2]])
    small = basket_history([histories[c["id"]] for c in coins[2:10]])
    rotation = compute_rotation(large, small)
    dom = global_metrics(timeout)["btc_dominance"]
    today = datetime.date.today().isoformat()
    return {"rotation": rotation, "dominance_point": {"date": today, "value": dom}}

"""Band-governance tool: backtest the production severity rules against full history.

House convention (audit 2026-07-03): NO severity-band change ships without rerunning
this and comparing against the baseline run recorded in
docs/audits/2026-07-03-bands-backtest.md. It exercises the EXACT production rule
callables from lenses.config, so what it scores is what readers see.

Fetches full FRED history (cached), reconstructs each rule's status over time by
prefix evaluation (the exact production callables from lenses.config), and reports:
  * time share per status since a per-series start
  * recession warning record: for each NBER recession start, worst status in the
    prior 12 months; false-alarm months (elevated+ outside recession windows,
    with no recession starting within 18 months)
  * today's percentile vs full history
  * a cross-signal diffusion index (share of signals at watch+ / elevated+)
  * a probit yield-curve recession-probability model (12-month horizon)
  * proposed alert-tier tests for rules that currently cap at 'elevated'
Run:  python backtest_bands.py   (needs FRED_API_KEY; caches to ./cache_fred/)
"""
import argparse
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lenses import config, derive, fred, narrative, util  # noqa: E402

CACHE = pathlib.Path(tempfile.gettempdir()) / "ba_backtest_cache"
CACHE.mkdir(exist_ok=True)
KEY = os.environ["FRED_API_KEY"]

def fetch(series, units=None):
    tag = f"{series}_{units or 'lin'}.json"
    p = CACHE / tag
    if p.exists():
        return json.loads(p.read_text())
    obs = fred.fetch_observations(series, KEY, 100000, units)
    p.write_text(json.dumps(obs))
    return obs

# (name, series, units, derive_fn, rule, start_for_stats)
IND = {(l.id, i.id): i for c in config.CATEGORIES for l in c["lenses"] for i in l.indicators}
def R(lens, ind): return IND[(lens, ind)].rule

SIGNALS = [
    ("unemployment-trend", "UNRATE", None, None, R("job-market","unemployment"), "1960"),
    ("jobless-claims", "ICSA", None, None, R("recession-watch","jobless-claims"), "1990"),
    ("sahm", "SAHMREALTIME", None, None, R("recession-watch","sahm-rule"), "1960"),
    ("yield-curve", "T10Y2Y", None, None, R("recession-watch","yield-curve"), "1977"),
    ("cpi-yoy", "CPIAUCSL", "pc1", None, R("cost-of-living","cpi"), "1960"),
    ("fed-funds", "FEDFUNDS", None, None, R("cost-of-money","fed-funds"), "1960"),
    ("mortgage-rate", "MORTGAGE30US", None, None, R("housing-affordability","mortgage-rate"), "1972"),
    ("saving-rate", "PSAVERT", None, None, R("consumer-income-savings","saving-rate"), "1960"),
    ("debt-service", "TDSP", None, None, R("consumer-credit","debt-service"), "1980"),
    ("sentiment", "UMCSENT", None, None, R("consumer-sentiment","sentiment"), "1960"),
    ("infl-expect", "MICH", None, None, R("consumer-sentiment","inflation-expectations"), "1979"),
    ("months-supply", "MSACSR", None, None, R("housing-supply-construction","months-supply"), "1964"),
    ("mortgage-delinq", "DRSFRMACBS", None, None, R("housing-affordability","delinquency"), "1991"),
    ("card-delinq", "DRCCLACBS", None, None, R("consumer-credit","card-delinquency"), "1991"),
    ("biz-delinq", "DRBLACBS", None, None, R("business-credit","delinquency"), "1988"),
    ("lending-standards", "DRTSCILM", None, None, R("business-credit","lending-standards"), "1990"),
    ("baa-spread", "BAA10YM", None, None, R("business-credit","baa-spread"), "1960"),
    ("vix", "VIXCLS", None, None, R("market-risk-sentiment","vix"), "1990"),
    ("nfci", "NFCI", None, None, R("market-risk-sentiment","nfci"), "1972"),
    ("m2-yoy", "M2SL", "pc1", None, R("market-liquidity","m2-growth"), "1961"),
    ("debt-gdp", "GFDEGDQ188S", None, None, R("fiscal-health","debt-gdp"), "1967"),
    ("payrolls", "PAYEMS", None, derive.payroll_change, R("job-market","payrolls"), "1960"),
]

SEV = {"ok":0, "watch":1, "elevated":2, "alert":3}

def month_key(d): return d[:7]

def month_end_points(cleaned):
    """Last observation of each month: [(month, idx_into_cleaned)]."""
    out, cur = [], None
    for i, (d, _) in enumerate(cleaned):
        m = month_key(d)
        if cur is None or m != cur[0]:
            if cur: out.append(cur)
            cur = (m, i)
        else:
            cur = (m, i)
    if cur: out.append(cur)
    return out

def status_series(cleaned, rule):
    """[(month, status)] by prefix evaluation at each month-end."""
    out = []
    for m, i in month_end_points(cleaned):
        _, st = rule(cleaned[:i+1])
        out.append((m, st))
    return out

def load_usrec():
    obs = fetch("USREC")
    return {month_key(o["date"]): float(o["value"]) >= 0.5 for o in obs if o["value"] not in (None, ".")}

def rec_starts(usrec):
    months = sorted(usrec)
    starts = []
    for a, b in zip(months, months[1:]):
        if usrec[b] and not usrec[a]:
            starts.append(b)
    return starts

def months_between(a, b):
    ay, am = int(a[:4]), int(a[5:7]); by, bm = int(b[:4]), int(b[5:7])
    return (by - ay) * 12 + (bm - am)

def analyze(name, stat, usrec, starts, start_from):
    stat = [(m, s) for m, s in stat if m >= start_from and s in SEV]
    if not stat: return None
    n = len(stat)
    share = {k: sum(1 for _, s in stat if s == k) / n for k in SEV}
    by_m = dict(stat)
    covered = [s for s in starts if s >= stat[0][0] and s <= stat[-1][0]]
    warned = 0
    for s in covered:
        window = [by_m[m] for m in by_m if 0 < months_between(m, s) <= 12]
        if window and max(SEV[x] for x in window) >= 2:
            warned += 1
    # false alarms: elevated+ months, not in recession, no recession start within 18m
    fa = 0; el_months = 0
    last = stat[-1][0]
    for m, s in stat:
        if SEV[s] < 2 or usrec.get(m, False):
            continue
        el_months += 1
        if months_between(m, last) < 18:  # too recent to judge
            continue
        if not any(0 < months_between(m, r) <= 18 for r in starts):
            fa += 1
    return {"name": name, "n_months": n, "share": share, "recessions_covered": len(covered),
            "warned_12m": warned, "elevated_months_outside_rec": el_months, "false_alarm_months": fa}

def pctile(cleaned, v=None):
    vals = sorted(x for _, x in cleaned)
    v = cleaned[-1][1] if v is None else v
    import bisect
    return 100.0 * bisect.bisect_left(vals, v) / len(vals)

def main():
    usrec = load_usrec()
    starts = rec_starts(usrec)
    print(f"NBER recession starts on record: {starts}")
    results, stat_by_name, series_by_name = [], {}, {}
    for name, sid, units, dv, rule, start in SIGNALS:
        raw = fetch(sid, units)
        if dv: raw = dv(raw)
        cleaned = util.clean(raw)
        st = status_series(cleaned, rule)
        stat_by_name[name] = st
        series_by_name[name] = cleaned
        r = analyze(name, st, usrec, starts, start)
        if r: results.append(r)
    out = {"recession_starts": starts, "signals": results}

    # today's percentiles
    out["percentiles_today"] = {n: round(pctile(series_by_name[n]), 1) for n in series_by_name}

    # diffusion index (monthly share of signals at watch+/elevated+), 1990->
    months = sorted({m for st in stat_by_name.values() for m, _ in st if m >= "1990-01"})
    diff = []
    cur = {}
    idx = {n: 0 for n in stat_by_name}
    for m in months:
        for n, st in stat_by_name.items():
            while idx[n] < len(st) and st[idx[n]][0] <= m:
                cur[n] = st[idx[n]][1]; idx[n] += 1
        known = [s for s in cur.values() if s in SEV]
        if len(known) >= 8:
            diff.append({"m": m, "n": len(known),
                         "watch_plus": round(sum(1 for s in known if SEV[s] >= 1) / len(known), 3),
                         "elev_plus": round(sum(1 for s in known if SEV[s] >= 2) / len(known), 3)})
    out["diffusion"] = diff

    # proposed alert tiers (P2-02): how often would each have fired?
    def fired(name, edge, cmp="ge"):
        ser = series_by_name[name]
        pts = month_end_points(ser)
        hit = [ser[i][0][:7] for _, i in [(m, i) for m, i in pts]
               if (ser[i][1] >= edge if cmp == "ge" else ser[i][1] <= edge)]
        years = sorted({h[:4] for h in hit})
        return {"months": len(hit), "years": years}
    out["alert_tier_tests"] = {
        "vix>=40": fired("vix", 40), "vix>=35": fired("vix", 35),
        "nfci>=1.0": fired("nfci", 1.0), "nfci>=1.5": fired("nfci", 1.5),
        "claims>=400k(1990->)": {"months": sum(1 for d, v in series_by_name["jobless-claims"] if d >= "1990" and v >= 400000)//4,
                                  "years": sorted({d[:4] for d, v in series_by_name["jobless-claims"] if d >= "1990" and v >= 400000})},
        "baa>=3.5(exists)": fired("baa-spread", 3.5),
    }
    # banking baked-history alert tests
    bank = json.loads((pathlib.Path(__file__).resolve().parents[2]
                       / "data" / "banking" / "bank-asset-quality.json").read_text(encoding="utf-8"))
    for ind in bank["indicators"]:
        vals = [(o["date"], float(o["value"])) for o in ind["observations"]]
        if ind["id"] == "noncurrent":
            out["alert_tier_tests"]["noncurrent>=3.0"] = {"quarters": [d for d, v in vals if v >= 3.0]}
            out["alert_tier_tests"]["noncurrent>=4.0"] = {"quarters": [d for d, v in vals if v >= 4.0]}
        if ind["id"] == "charge-offs":
            out["alert_tier_tests"]["chargeoffs>=2.0"] = {"quarters": [d for d, v in vals if v >= 2.0]}
            out["alert_tier_tests"]["chargeoffs>=2.5"] = {"quarters": [d for d, v in vals if v >= 2.5]}

    # probit: P(recession within 12m) from T10Y2Y month-end level
    try:
        import numpy as np
        from statsmodels.discrete.discrete_model import Probit
        import statsmodels.api as sm
        yc = series_by_name["yield-curve"]
        pts = month_end_points(yc)
        rows = []
        for m, i in pts:
            fut = any(usrec.get(f"{(int(m[:4]) + (int(m[5:7]) + k - 1) // 12):04d}-{((int(m[5:7]) + k - 1) % 12 + 1):02d}", False)
                      for k in range(1, 13))
            rows.append((m, yc[i][1], 1.0 if fut else 0.0))
        rows = [r for r in rows if r[0] <= "2025-06"]  # need full 12m lookahead
        X = sm.add_constant(np.array([[r[1]] for r in rows]))
        y = np.array([r[2] for r in rows])
        fit = Probit(y, X).fit(disp=False)
        cur = float(fit.predict(sm.add_constant(np.array([[yc[-1][1]]]), has_constant="add"))[0])
        from statsmodels.tools.eval_measures import aic
        p = fit.predict(X)
        # simple AUC
        pos = p[y == 1]; neg = p[y == 0]
        auc = float(np.mean([(pos > n_).mean() for n_ in neg])) if len(pos) and len(neg) else None
        out["probit_yield_curve"] = {
            "n": len(rows), "coef_const": round(float(fit.params[0]), 3),
            "coef_spread": round(float(fit.params[1]), 3),
            "pseudo_r2": round(float(fit.prsquared), 3),
            "auc_in_sample": round(auc, 3) if auc else None,
            "p_recession_12m_today": round(cur, 3), "spread_today": yc[-1][1],
        }
    except Exception as e:
        out["probit_yield_curve"] = {"error": str(e)}

    # lead-lag on three relationship edges (quarterly alignment, pearson r at lags)
    def qmean(cleaned):
        agg = {}
        for d, v in cleaned:
            q = f"{d[:4]}Q{(int(d[5:7]) - 1)//3 + 1}"
            agg.setdefault(q, []).append(v)
        return {q: sum(v)/len(v) for q, v in agg.items()}
    def leadlag(a, b, lags=range(-8, 9)):
        import statistics as st
        qa, qb = qmean(a), qmean(b)
        qs = sorted(set(qa) & set(qb))
        best = []
        for lag in lags:  # positive lag: a leads b by `lag` quarters
            pairs = []
            for q in qs:
                yq, qq = int(q[:4]), int(q[5])
                tq = qq + lag; ty = yq + (tq - 1)//4; tq = (tq - 1) % 4 + 1
                t = f"{ty}Q{tq}"
                if t in qb: pairs.append((qa[q], qb[t]))
            if len(pairs) < 30: continue
            xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
            mx, my = st.mean(xs), st.mean(ys)
            sx, sy = st.pstdev(xs), st.pstdev(ys)
            if sx == 0 or sy == 0: continue
            r = sum((x-mx)*(y-my) for x, y in pairs) / (len(pairs)*sx*sy)
            best.append((lag, round(r, 3), len(pairs)))
        return best
    ll = {}
    ll["standards->biz_delinq"] = leadlag(series_by_name["lending-standards"], series_by_name["biz-delinq"])
    cs_yoy = util.clean(derive.yoy_pct(fetch("CSUSHPINSA")))
    fixhai = util.clean(fetch("FIXHAI"))
    ll["affordability->cs_yoy"] = leadlag(fixhai, cs_yoy)
    unrate_chg = [(d, v) for d, v in series_by_name["unemployment-trend"]]
    ll["curve->unrate"] = leadlag(series_by_name["yield-curve"], unrate_chg)
    out["leadlag"] = {k: sorted(v, key=lambda t: -abs(t[1]))[:3] for k, v in ll.items()}

    args = _parse_args()
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")
    for r in results:
        print(f"{r['name']:20s} warned {r['warned_12m']}/{r['recessions_covered']} recs; "
              f"elev+ share {r['share']['elevated']+r['share']['alert']:.0%}; "
              f"false-alarm months {r['false_alarm_months']}/{r['elevated_months_outside_rec']}")

def _parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=pathlib.Path,
                    default=pathlib.Path(tempfile.gettempdir()) / "backtest_results.json",
                    help="where to write the results JSON (an analysis artifact — "
                         "keep it out of data/)")
    return ap.parse_args()


if __name__ == "__main__":
    main()

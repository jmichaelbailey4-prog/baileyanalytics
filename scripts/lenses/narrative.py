"""Rule-based narrative engine. Pure functions of cleaned observations.

Each rule takes a chronological list of (date, float) tuples and returns
(text, status). Status is one of: ok, watch, elevated, alert, unknown.
"""

import datetime as _dt
import functools

from . import bands, util

_NO_DATA = ("Data unavailable.", "unknown")


def _iso_days_before(iso, days):
    """ISO date `days` calendar days before `iso`. Yield-curve dates are daily
    (YYYY-MM-DD); a bare YYYY-MM is padded defensively."""
    d = _dt.date.fromisoformat(iso if len(iso) == 10 else iso + "-01")
    return (d - _dt.timedelta(days=days)).isoformat()


def rule_yield_curve(obs):
    """T10Y2Y: inverted (<0) warns; a recent un-inversion warrants vigilance.

    The 'recent' window is date-based (~6 months), not a fixed point count, so the
    read is identical whether fed daily data (the lens) or a weekly-resampled series
    (the predictions runner). A positional obs[-126:] silently became ~2.4 years on
    weekly data, so an old inversion re-flagged a positive curve as 'watch' and the
    predict block contradicted the lens badge.
    """
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    cutoff = _iso_days_before(obs[-1][0], 183)  # ~6 months, by date
    recent = [val for d, val in obs if d >= cutoff]
    was_inverted = any(val < 0 for val in recent[:-1])
    if v < 0:
        return (
            f"The curve is inverted by {abs(v):.2f} points — a classic recession "
            "warning that has preceded every U.S. recession since the 1970s.",
            "elevated",
        )
    if was_inverted:
        return (
            f"The curve recently un-inverted to +{v:.2f} after an extended inversion. "
            "Recessions historically begin after the curve climbs back above zero — "
            "a reason for more vigilance, not less.",
            "watch",
        )
    return (
        f"The curve is positive (+{v:.2f}) with no recent inversion — "
        "no recession warning from the curve right now.",
        "ok",
    )


def rule_sahm(obs):
    """SAHMREALTIME: trips at 0.50; 0.35-0.50 is a warning band."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 0.50:
        return (
            f"The Sahm rule has triggered at {v:.2f}, historically consistent with "
            "a recession already underway.",
            "alert",
        )
    if v >= 0.35:
        return (
            f"The Sahm rule is at {v:.2f}, climbing toward its 0.50 recession "
            "trigger but not there yet.",
            "watch",
        )
    return (f"The Sahm rule is at {v:.2f}, well below its 0.50 recession trigger.", "ok")


def rule_claims(obs):
    """ICSA (weekly level): <250k low, 250-300k creeping, >=300k elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 250000:
        return (
            f"Initial jobless claims are low at {v:,.0f} — employers aren't "
            "shedding workers.",
            "ok",
        )
    if v < 300000:
        return (f"Jobless claims at {v:,.0f} are creeping up from their lows.", "watch")
    return (
        f"Jobless claims have risen to {v:,.0f}, a sign of accelerating layoffs.",
        "elevated",
    )


def rule_unemployment_trend(obs):
    """UNRATE: a rise of >=0.5pts above the trailing 12-month low is a warning."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    window = [val for _, val in obs[-12:]]
    low = min(window)
    delta = v - low
    if delta >= 0.5:
        return (
            f"Unemployment at {v:.1f}% is up {delta:.1f} points from its recent low — "
            "the kind of rise that has preceded past downturns.",
            "watch",
        )
    return (f"Unemployment is steady at {v:.1f}%, near its recent lows.", "ok")


def _value_year_ago(obs):
    """Value ~one year before the latest observation, or None if history is too short.

    Frequency-agnostic (ISO date strings compare correctly). Returns None when no
    observation is at least a year old, so callers can omit a year-over-year claim
    rather than compare against a misleadingly-recent baseline.
    """
    last_date = obs[-1][0]
    target = f"{int(last_date[:4]) - 1}{last_date[4:]}"
    result = None
    for d, val in obs:
        if d <= target:
            result = val
        else:
            break
    return result


def rule_fed_funds(obs):
    """FEDFUNDS: the policy-rate level and its ~12-month direction."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    status = "watch" if v >= 4.0 else "ok"
    prior = _value_year_ago(obs)
    if prior is None:
        return (f"The Fed's policy rate is {v:.2f}%.", status)
    delta = v - prior
    if delta >= 0.25:
        stance = "and still climbing as the Fed leans against inflation"
    elif delta <= -0.25:
        stance = "and easing as the Fed pivots toward cuts"
    else:
        stance = "holding roughly steady as the Fed waits for more data"
    return (f"The Fed's policy rate is {v:.2f}%, {stance}.", status)


def rule_rate_expectations(obs):
    """DGS2 minus the fed funds rate: the bond market's pricing of the Fed's
    next moves. Descriptive (info) — it carries no good/bad verdict, so it
    never drives the lens badge."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= -0.75:
        return (f"The 2-year yield sits {abs(v):.2f} points below the Fed's rate — "
                "markets are pricing meaningful rate cuts ahead.", "info")
    if v <= -0.25:
        return (f"The 2-year yield is {abs(v):.2f} points below the Fed's rate — "
                "markets lean toward rate cuts.", "info")
    if v < 0.25:
        return ("The 2-year yield is roughly in line with the Fed's rate — "
                "markets expect the Fed to hold near current levels.", "info")
    return (f"The 2-year yield is {v:.2f} points above the Fed's rate — "
            "markets are pricing rate hikes ahead.", "info")


def rule_mortgage(obs):
    """MORTGAGE30US level bands: <5.5 ok, 5.5-6.5 watch, 6.5-7.5 elevated, >=7.5 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 7.5:
        return (f"30-year mortgages are at {v:.2f}% — punishing rates that freeze out most buyers.", "alert")
    if v >= 6.5:
        return (f"30-year mortgages are at {v:.2f}% — high enough to keep affordability stretched.", "elevated")
    if v >= 5.5:
        return (f"30-year mortgages are at {v:.2f}% — above the comfort zone for most budgets.", "watch")
    return (f"30-year mortgages are at {v:.2f}% — moderate by recent standards.", "ok")


def rule_payrolls(obs):
    """Monthly change in nonfarm payrolls (jobs added or lost)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0:
        return (f"Employers cut {abs(v):,.0f} jobs last month — an outright contraction.", "alert")
    if v < 75000:
        return (f"Employers added just {v:,.0f} jobs last month — hiring has slowed sharply.", "watch")
    if v < 150000:
        return (f"Employers added {v:,.0f} jobs last month — a cooler but still-positive pace.", "watch")
    return (f"Employers added {v:,.0f} jobs last month — a healthy clip.", "ok")


def rule_job_openings(obs):
    """JTSJOL in millions: how hungry employers are to hire."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    status = "watch" if v < 7.5 else "ok"
    prior = _value_year_ago(obs)
    if prior is None:
        return (f"{v:.1f} million open jobs.", status)
    if v < prior - 0.3:
        trend = "easing as labor demand cools"
    elif v > prior + 0.3:
        trend = "rising as employers compete for workers"
    else:
        trend = "holding roughly steady"
    return (f"{v:.1f} million open jobs, {trend}.", status)


def rule_wage_growth(obs):
    """Average hourly earnings, year-over-year percent. In the job-market frame,
    strong pay is healthy and stalling pay signals a softening labor market — so
    this warns on the low side (the inflation angle is Cost of Living's Real Wages).
    >=3 ok, 2-3 watch, <2 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 2.0:
        return (f"Pay is up just {v:.1f}% from a year ago — wage growth has stalled, "
                "a sign of a softening job market.", "elevated")
    if v < 3.0:
        return (f"Pay is up {v:.1f}% from a year ago — cooling from its recent pace.", "watch")
    pace = "running ahead of recent inflation" if v >= 3.5 else "a solid pace"
    return (f"Pay is up {v:.1f}% from a year ago, {pace}.", "ok")


def restrictive_rate(label, watch, elevated):
    """Factory: one-sided 'cost of borrowing' severity for a market interest rate.
    Higher = costlier money — ok/watch/elevated, with no `alert` (an expensive rate
    isn't a crisis the way a default spike is). For the Cost-of-Money lens, where the
    whole curve being expensive is exactly the point. `label` reads as a noun
    ("The 10-year Treasury")."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= elevated:
            return (f"{label} yield is {v:.2f}% — restrictive borrowing costs "
                    "across the economy.", "elevated")
        if v >= watch:
            return (f"{label} yield is {v:.2f}% — above the comfortable range "
                    "for borrowers.", "watch")
        return (f"{label} yield is {v:.2f}% — moderate borrowing costs by recent "
                "standards.", "ok")
    _rule.band_spec = bands.BandSpec(kind="level", unit="%",
        edges=(watch, elevated), segments=("ok", "watch", "elevated"))
    _rule.band_tag = "restrictive_rate"
    return _rule


# --- Additional scored signals (score-explain-order, 2026-06-24) ---

def rule_auto_sales(obs):
    """Light-vehicle sales, millions at an annual rate. The classic big-ticket
    purchase — households delay it first when budgets tighten, so a low/falling
    pace reads as consumer-demand stress. >=15 ok, 13.5-15 watch, 12-13.5 elevated,
    <12 alert (2009 and 2020 troughs were ~9M)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 12:
        return (f"Vehicle sales have fallen to {v:.1f} million a year — big-ticket "
                "demand is collapsing.", "alert")
    if v < 13.5:
        return (f"Vehicle sales are running at {v:.1f} million a year — households are "
                "pulling back on big-ticket buys.", "elevated")
    if v < 15:
        return (f"Vehicle sales are at {v:.1f} million a year — softening from a "
                "healthy pace.", "watch")
    return (f"Vehicle sales are at {v:.1f} million a year — a healthy big-ticket pace.", "ok")


def rule_mortgage_debt_service(obs):
    """MDSP: mortgage payments as a share of disposable income (%), the mortgage-only
    companion to Consumer's total debt-service. Calibrated to its own history (since
    1980: ~4.8 low, ~6.1 median, ~7.2 in 2007, ~8.9 at the early-1980s peak): <6 ok,
    6-7 watch, 7-8 elevated, >=8 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 8:
        return (f"Mortgage payments eat {v:.1f}% of household income — near the "
                "early-1980s extreme.", "alert")
    if v >= 7:
        return (f"Mortgage payments take {v:.1f}% of household income — a heavy "
                "burden, around the 2007 peak.", "elevated")
    if v >= 6:
        return (f"Mortgage payments take {v:.1f}% of household income — a touch "
                "above the long-run norm.", "watch")
    return (f"Mortgage payments take {v:.1f}% of household income — a manageable, "
            "below-average burden.", "ok")


def rule_interest_burden(obs):
    """Federal interest payments as a share of TOTAL federal receipts (%) — how much
    of every revenue dollar goes to servicing the debt. Uses total receipts (incl.
    payroll taxes), the conventional ~20% figure — not tax-only receipts, which would
    overstate it. <10 ok, 10-15 watch, 15-22 elevated, >=22 alert; it has climbed to a
    modern record (~20%) as rates rose. (Record-high reads 'elevated'; 'alert' is
    reserved for a genuinely unprecedented level.)"""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 22:
        return (f"Interest eats {v:.0f} cents of every dollar of federal revenue — "
                "an extreme, unprecedented claim.", "alert")
    if v >= 15:
        return (f"Interest takes {v:.0f} cents of every dollar of federal revenue — "
                "a heavy, near-record claim that crowds out the budget.", "elevated")
    if v >= 10:
        return (f"Interest takes {v:.0f} cents of every dollar of federal revenue — "
                "a rising claim.", "watch")
    return (f"Interest takes {v:.0f} cents of every dollar of federal revenue — "
            "a manageable share.", "ok")


def rule_inflation(obs):
    """A year-over-year inflation rate (CPI/core/PCE) versus the Fed's ~2% goal."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 4.0:
        return (f"Running at {v:.1f}% a year — well above the Fed's 2% goal.", "elevated")
    if v >= 2.5:
        return (f"Running at {v:.1f}% a year — still above the Fed's 2% goal.", "watch")
    return (f"Running at {v:.1f}% a year — close to the Fed's 2% goal.", "ok")


def rule_real_wages(obs):
    """Inflation-adjusted average hourly earnings, year-over-year percent."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0:
        return (f"Down {abs(v):.1f}% from a year ago — pay isn't keeping up with prices.", "watch")
    return (f"Up {v:.1f}% from a year ago — paychecks are outpacing inflation.", "ok")


# --- Banking System Health rules (FDIC Call Report metrics) ---

def rule_noncurrent(obs):
    """Noncurrent loan rate (% of loans 90+ days late). <1 ok, 1-2 watch,
    2-3 elevated, >=3 alert (in the FDIC data window shown, 2006->, 3%+ occurred
    only in the 2009-2013 crisis aftermath; the early-1990s S&L era also ran
    above 3% — band backtest 2026-07-03)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 1.0:
        return (f"Just {v:.2f}% of loans are 90+ days past due — low by historical standards.", "ok")
    if v < 2.0:
        return (f"Noncurrent loans are at {v:.2f}%, creeping up off recent lows.", "watch")
    if v < 3.0:
        return (f"Noncurrent loans have climbed to {v:.2f}% — elevated and worth watching.", "elevated")
    return (f"Noncurrent loans have reached {v:.2f}% — financial-crisis territory.", "alert")


def rule_charge_offs(obs):
    """Net charge-off rate (% of loans). <0.6 ok, 0.6-1.2 watch, 1.2-2 elevated,
    >=2 alert (in the FDIC data window shown, 2006->, 2%+ occurred only in
    2009-2010 — band backtest 2026-07-03)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0.6:
        return (f"Banks are writing off {v:.2f}% of loans as losses — a benign level.", "ok")
    if v < 1.2:
        return (f"Loan losses are running at {v:.2f}%, above the calm-period norm.", "watch")
    if v < 2.0:
        return (f"Loan losses have reached {v:.2f}% — a meaningful drag on earnings.", "elevated")
    return (f"Loan losses have hit {v:.2f}% — write-offs at financial-crisis scale.", "alert")


def rule_cre_concentration(obs):
    """CRE loans as % of equity capital. >300 is the interagency 'concentration' flag."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 300:
        return (f"Commercial real estate equals {v:.0f}% of capital — above the supervisory concentration flag.", "elevated")
    if v >= 200:
        return (f"Commercial real estate is {v:.0f}% of capital — a notable concentration.", "watch")
    return (f"Commercial real estate is {v:.0f}% of capital — a manageable share.", "ok")


def rule_uninsured_share(obs):
    """Uninsured deposits as % of total deposits. Higher = more flight-prone."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 40:
        return (f"{v:.1f}% of deposits sit above the FDIC insurance cap — flight-prone if confidence cracks.", "watch")
    return (f"{v:.1f}% of deposits are uninsured — a moderate, manageable share.", "ok")


def rule_capital_ratio(obs):
    """Equity-to-assets (%). Banks historically run ~9-11%. >=9 ok, 7.5-9 watch, <7.5 thin."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 7.5:
        return (f"Equity is {v:.1f}% of assets — a thin capital cushion.", "elevated")
    if v < 9:
        return (f"Equity is {v:.1f}% of assets — adequate, but on the lighter side.", "watch")
    return (f"Equity is {v:.1f}% of assets — a healthy capital cushion.", "ok")


def rule_risk_based_capital(obs):
    """Total risk-based capital ratio (%). Regulators: >=10 well-capitalized, 8-10 adequate, <8 thin."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 10:
        return (f"The total risk-based capital ratio is {v:.1f}% — comfortably 'well-capitalized'.", "ok")
    if v >= 8:
        return (f"Risk-based capital is {v:.1f}% — adequate, but below the well-capitalized line.", "watch")
    return (f"Risk-based capital is {v:.1f}% — below regulatory minimums.", "elevated")


def rule_net_margin(obs):
    """Net interest income as % of assets (NIM proxy). Higher = healthier earnings."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 2.5:
        return (f"Net interest margin is {v:.2f}% — compressed, squeezing bank earnings.", "watch")
    return (f"Net interest margin is {v:.2f}% — a healthy spread on lending.", "ok")


def rule_roa(obs):
    """Return on assets (%). >=1.0 ok, 0.5-1.0 watch, 0-0.5 elevated, <0 alert
    (an industry-wide loss — seen only at the depth of the 2008-09 crisis)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 1.0:
        return (f"Banks earned {v:.2f}% on their assets — solid profitability.", "ok")
    if v >= 0.5:
        return (f"Return on assets is {v:.2f}% — subdued profitability.", "watch")
    if v >= 0:
        return (f"Return on assets is just {v:.2f}% — earnings are weak.", "elevated")
    return (f"Return on assets is {v:.2f}% — the banking industry is losing money.", "alert")


def rule_loans_deposits(obs):
    """Loans as % of deposits. >=90 stretched funding, else comfortable."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 90:
        return (f"Banks have lent out {v:.0f}% of deposits — funding is stretched.", "watch")
    return (f"Banks have lent out {v:.0f}% of deposits — comfortable funding headroom.", "ok")


# --- Markets & Financial Conditions rules ---

def rule_vix(obs):
    """CBOE VIX level. <20 calm, 20-30 nervous, 30-40 fearful, >=40 crisis-grade
    (daily closes at 40+ are rare and cluster around major market shocks —
    band backtest 2026-07-03; do NOT enumerate years: intra-month spikes make
    any exhaustive list falsifiable against the chart)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 20:
        return (f"The VIX is at {v:.1f} — markets are calm.", "ok")
    if v < 30:
        return (f"The VIX is at {v:.1f} — some nervousness, but not panic.", "watch")
    if v < 40:
        return (f"The VIX is at {v:.1f} — markets are fearful.", "elevated")
    return (f"The VIX is at {v:.1f} — panic levels seen only in genuine crises.", "alert")


def credit_spread(label, calm, stressed, crisis=None):
    """Factory: a credit-spread rule with its own calm/stressed thresholds (%).
    `crisis` (optional) adds an alert tier for spread levels reached historically
    only in severe credit-stress episodes (2008, 2011, early 2016, March 2020 for
    high-yield) — FRED's rolling API window can't chart that history, but the
    peaks are public record on FRED's own site."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v < calm:
            return (f"The {label} spread is {v:.2f}% — tight, signaling calm credit conditions.", "ok")
        if v < stressed:
            return (f"The {label} spread is {v:.2f}% — widening off its lows.", "watch")
        if crisis is None or v < crisis:
            return (f"The {label} spread is {v:.2f}% — wide, a sign of credit stress.", "elevated")
        return (f"The {label} spread is {v:.2f}% — blowout levels seen in past "
                "severe credit-stress episodes.", "alert")
    extra = () if crisis is None else (crisis,)
    _rule.band_spec = bands.BandSpec(kind="level", unit="%",
        edges=(calm, stressed) + extra,
        segments=("ok", "watch", "elevated") + (("alert",) if extra else ()))
    _rule.band_tag = "credit_spread"
    return _rule


def rule_financial_conditions(obs):
    """Chicago Fed NFCI. <=0 looser than average, 0-0.5 a touch tight, 0.5-1.0
    tight, >=1.0 crisis-grade (in the modern era, 1.0+ has printed only in
    2008-09 — band backtest 2026-07-03)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= 0:
        return (f"The NFCI is {v:.2f} — financial conditions are looser than average.", "ok")
    if v < 0.5:
        return (f"The NFCI is {v:.2f} — conditions a touch tighter than average.", "watch")
    if v < 1.0:
        return (f"The NFCI is {v:.2f} — financial conditions are tight.", "elevated")
    return (f"The NFCI is {v:.2f} — a squeeze on the scale of past financial crises.", "alert")


def market_level(label, up=2.0, down=-2.0):
    """Factory: a momentum rule for a price/level series. Reports the trailing
    ~12-month % change and returns status 'up' / 'down' / 'flat' (momentum, not
    severity — the lens-level badge for the scoreboard is neutral)."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.2f}.", "flat")
        pct = (v - prior) / abs(prior) * 100
        if pct >= up:
            return (f"{label} is up {pct:.0f}% over the past year, now {v:,.2f}.", "up")
        if pct <= down:
            return (f"{label} is down {abs(pct):.0f}% over the past year, now {v:,.2f}.", "down")
        return (f"{label} is little changed over the past year, now {v:,.2f}.", "flat")
    return _rule


def rule_crypto_rotation(obs):
    """Large-vs-small rotation index (base 100). Compares the latest value to ~90
    observations ago to read risk-on (alts outperforming) vs risk-off (flight to majors)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    base = obs[max(0, len(obs) - 90)][1] or v
    if v >= base * 1.03:
        return ("Small- and mid-cap coins are outperforming Bitcoin and Ether — a risk-on "
                "rotation into alts.", "info")
    if v <= base * 0.97:
        return ("Capital is rotating back toward Bitcoin and Ether — a risk-off tilt within "
                "crypto.", "info")
    return ("Large and small caps are moving roughly in step — no clear rotation.", "info")


def rule_btc_dominance(obs):
    """Bitcoin's share of total crypto market value (%)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    return (f"Bitcoin is {v:.0f}% of total crypto market value.", "info")


def rule_btc_eth_relative(obs):
    """BTC/ETH price ratio — which of the two majors is leading over the past year."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if prior is None or prior == 0:
        return (f"The Bitcoin/Ether ratio is {v:.2f}.", "info")
    if v >= prior * 1.05:
        return (f"Bitcoin has gained on Ether over the past year (ratio {v:.2f}).", "info")
    if v <= prior * 0.95:
        return (f"Ether has gained on Bitcoin over the past year (ratio {v:.2f}).", "info")
    return (f"Bitcoin and Ether have held their relative value (ratio {v:.2f}).", "info")


# --- Energy & Commodities rules ---

def consumer_cost(label, watch, elevated, alert):
    """Factory: consumer-cost severity from trailing-12-month % change. Rising fast
    means household stress; falling/flat is ok. Thresholds are YoY-% bands."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.2f}.", "ok")
        pct = (v - prior) / abs(prior) * 100
        if pct >= alert:
            return (f"{label} costs have surged {pct:.0f}% over the past year — acute pressure on households.", "alert")
        if pct >= elevated:
            return (f"{label} costs are up {pct:.0f}% over the past year — a real squeeze.", "elevated")
        if pct >= watch:
            return (f"{label} costs are up {pct:.0f}% over the past year — climbing.", "watch")
        if pct <= -watch:
            return (f"{label} costs have fallen {abs(pct):.0f}% over the past year — relief for households.", "ok")
        if pct >= 1:
            return (f"{label} costs are up {pct:.0f}% over the past year.", "ok")
        if pct <= -1:
            return (f"{label} costs are down {abs(pct):.0f}% over the past year.", "ok")
        return (f"{label} costs are roughly flat over the past year.", "ok")
    _rule.band_spec = bands.BandSpec(kind="yoy_computed", unit="%",
        edges=(watch, elevated, alert), segments=("ok", "watch", "elevated", "alert"))
    _rule.band_tag = "consumer_cost"
    return _rule


def energy_level(label, fmt="{:,.0f}"):
    """Descriptive `info`: latest level + trailing-12-month direction. No verdict.
    `fmt` formats the displayed level (e.g. "{:,.2f} million" for derived counts)."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        latest = fmt.format(v)
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {latest}.", "info")
        pct = (v - prior) / abs(prior) * 100
        if pct >= 3:
            return (f"{label} is up {pct:.0f}% from a year ago, now {latest}.", "info")
        if pct <= -3:
            return (f"{label} is down {abs(pct):.0f}% from a year ago, now {latest}.", "info")
        return (f"{label} is little changed from a year ago, now {latest}.", "info")
    return _rule


def yoy_band(label, watch, elevated, alert):
    """Factory: one-sided consumer-cost severity for a series that is ALREADY a
    year-over-year % rate (e.g. a `derive.yoy_pct` series). Same bands and tone
    as `consumer_cost`, but the latest value is the rate itself."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= alert:
            return (f"{label} costs are rising {v:.1f}% a year — acute pressure on households.", "alert")
        if v >= elevated:
            return (f"{label} costs are rising {v:.1f}% a year — a real squeeze.", "elevated")
        if v >= watch:
            return (f"{label} costs are rising {v:.1f}% a year — climbing.", "watch")
        if v <= -watch:
            return (f"{label} costs are falling {abs(v):.1f}% a year — relief for households.", "ok")
        if v >= 1:
            return (f"{label} costs are rising {v:.1f}% a year.", "ok")
        if v <= -1:
            return (f"{label} costs are falling {abs(v):.1f}% a year.", "ok")
        return (f"{label} costs are roughly flat versus a year ago ({v:+.1f}%).", "ok")
    _rule.band_spec = bands.BandSpec(kind="yoy", unit="%",
        edges=(watch, elevated, alert), segments=("ok", "watch", "elevated", "alert"))
    _rule.band_tag = "yoy_band"
    return _rule


def yoy_band_two_sided(label, hot, cold, verb="are"):
    """Factory: two-sided market-health severity for an already-YoY % series.
    Same bands and tone as `market_health`. Label reads as a plural subject
    ("Home prices"); pass verb="is" for singular ones ("Real spending")."""
    hot_w, hot_e, hot_a = hot
    cold_w, cold_e, cold_a = cold

    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= hot_a:
            return (f"{label} {verb} up {v:.1f}% from a year ago — overheating.", "alert")
        if v >= hot_e:
            return (f"{label} {verb} up {v:.1f}% from a year ago — running hot.", "elevated")
        if v >= hot_w:
            return (f"{label} {verb} up {v:.1f}% from a year ago — heating up.", "watch")
        if v <= cold_a:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — a deep freeze.", "alert")
        if v <= cold_e:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — cooling sharply.", "elevated")
        if v <= cold_w:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — cooling.", "watch")
        if v >= 1:
            return (f"{label} {verb} up {v:.1f}% from a year ago — a steady pace.", "ok")
        if v <= -1:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago.", "ok")
        return (f"{label} {verb} little changed from a year ago ({v:+.1f}%).", "ok")

    _rule.band_spec = bands.BandSpec(kind="yoy", unit="%",
        edges=(cold_a, cold_e, cold_w, hot_w, hot_e, hot_a),
        segments=("alert", "elevated", "watch", "ok", "watch", "elevated", "alert"))
    _rule.band_tag = "yoy_band_two_sided"
    return _rule


def yoy_info(label):
    """Descriptive `info` for an already-YoY % series. Label must read as a
    singular subject ("Owners' equivalent rent")."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= 0.5:
            return (f"{label} is rising {v:.1f}% a year.", "info")
        if v <= -0.5:
            return (f"{label} is falling {abs(v):.1f}% a year.", "info")
        return (f"{label} is roughly flat versus a year ago.", "info")
    return _rule


def generation_share(label):
    """Descriptive `info` for an electricity generation share (%) + its direction."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None:
            return (f"{label}: {v:.1f}% of U.S. electricity generation.", "info")
        delta = v - prior
        if delta >= 0.5:
            return (f"{label}: {v:.1f}% of U.S. electricity generation, up {delta:.1f} points over the past year.", "info")
        if delta <= -0.5:
            return (f"{label}: {v:.1f}% of U.S. electricity generation, down {abs(delta):.1f} points over the past year.", "info")
        return (f"{label}: {v:.1f}% of U.S. electricity generation, steady over the past year.", "info")
    return _rule


# --- Markets: Liquidity & the Fed ---

def rule_m2_growth(obs):
    """M2 year-over-year %. Very fast growth is historically inflationary; an
    outright contraction is rare and signals monetary squeeze.
    >=10 elevated, 7-10 watch, -1..7 ok, -3..-1 watch, <=-3 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 10:
        return (f"M2 is growing {v:.1f}% a year — unusually fast, and historically inflationary.", "elevated")
    if v >= 7:
        return (f"M2 is growing {v:.1f}% a year — on the fast side.", "watch")
    if v <= -3:
        return (f"M2 is shrinking {abs(v):.1f}% a year — a rare monetary contraction.", "elevated")
    if v <= -1:
        return (f"M2 is shrinking {abs(v):.1f}% a year — liquidity is being drained.", "watch")
    return (f"M2 is growing {v:.1f}% a year — a normal pace.", "ok")


# --- The Consumer rules ---

def consumer_delinquency(label, watch, elevated, alert):
    """Factory: delinquency-rate bands (%) with consumer-credit wording."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= alert:
            return (f"{label} delinquencies have hit {v:.1f}% — crisis-level consumer distress.", "alert")
        if v >= elevated:
            return (f"{label} delinquencies have climbed to {v:.1f}% — real borrower stress.", "elevated")
        if v >= watch:
            return (f"{label} delinquencies are at {v:.1f}%, creeping up off their lows.", "watch")
        return (f"{label} delinquencies are low at {v:.1f}% — borrowers are keeping up.", "ok")
    _rule.band_spec = bands.BandSpec(kind="level", unit="%",
        edges=(watch, elevated, alert), segments=("ok", "watch", "elevated", "alert"))
    _rule.band_tag = "consumer_delinquency"
    return _rule


def rule_revolving_credit(obs):
    """Revolving (credit-card) balances, year-over-year %. Fast growth means
    households are leaning on cards; shrinking balances mean paying down."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 12:
        return (f"Card balances are growing {v:.1f}% a year — households are leaning hard on credit.", "elevated")
    if v >= 8:
        return (f"Card balances are growing {v:.1f}% a year — faster than incomes.", "watch")
    if v <= -1:
        return (f"Card balances are shrinking {abs(v):.1f}% a year — households are paying down debt.", "ok")
    return (f"Card balances are growing {v:.1f}% a year — a sustainable pace.", "ok")


def rule_debt_service(obs):
    """TDSP: household debt service as % of disposable income.
    <10.5 ok, 10.5-12 watch, 12-13 elevated, >=13 alert (2007 peak ~13.2)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 13:
        return (f"Debt payments eat {v:.1f}% of household income — at the 2007 danger level.", "alert")
    if v >= 12:
        return (f"Debt payments eat {v:.1f}% of household income — a heavy and rising burden.", "elevated")
    if v >= 10.5:
        return (f"Debt payments take {v:.1f}% of household income — above the comfortable range.", "watch")
    return (f"Debt payments take {v:.1f}% of household income — a manageable burden.", "ok")


def rule_saving_rate(obs):
    """PSAVERT: personal saving rate (%). Low savings = no cushion when
    shocks hit. <3 elevated, 3-5 watch, >=5 ok."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 3:
        return (f"Households are saving just {v:.1f}% of income — almost no cushion left.", "elevated")
    if v < 5:
        return (f"The saving rate is {v:.1f}% — thinner than the historical norm.", "watch")
    return (f"Households are saving {v:.1f}% of income — a healthy cushion.", "ok")


def rule_real_income(obs):
    """Real disposable income, year-over-year %. Falling real income is the
    root of most consumer stress. <=-2 elevated, <0 watch, >=0 ok."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= -2:
        return (f"Real income is down {abs(v):.1f}% from a year ago — purchasing power is eroding fast.", "elevated")
    if v < 0:
        return (f"Real income is down {abs(v):.1f}% from a year ago — paychecks aren't keeping up.", "watch")
    return (f"Real income is up {v:.1f}% from a year ago — purchasing power is growing.", "ok")


def rule_sentiment(obs):
    """UMCSENT: U. Michigan consumer sentiment. Long-run range roughly 50-110
    (the mid-2022 trough was ~50). >=85 ok, 70-85 watch, 55-70 elevated, <55 alert.
    The alert read self-detects a fresh record low against the shown history, so
    the copy can never claim "near record lows" beside a chart printing below
    every prior point (that happened live in May 2026 at 44.8)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 55:
        prior = [val for _, val in obs[:-1]]
        if prior and v < min(prior):
            return (f"Consumer sentiment is {v:.0f} — a record low; households have "
                    "never been this pessimistic in the data shown.", "alert")
        if prior and v == min(prior):
            return (f"Consumer sentiment is {v:.0f} — matching its record low; "
                    "households are deeply pessimistic.", "alert")
        return (f"Consumer sentiment is {v:.0f} — near record lows; households are deeply pessimistic.", "alert")
    if v < 70:
        return (f"Consumer sentiment is {v:.0f} — recession-grade gloom.", "elevated")
    if v < 85:
        return (f"Consumer sentiment is {v:.0f} — downbeat but not despairing.", "watch")
    return (f"Consumer sentiment is {v:.0f} — households feel fine.", "ok")


def rule_inflation_expectations(obs):
    """MICH: 1-year-ahead inflation expectations (%). The Fed watches this for
    de-anchoring. <=3 ok, 3-4 watch, 4-5.5 elevated, >=5.5 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 5.5:
        return (f"Households expect {v:.1f}% inflation next year — expectations are de-anchoring.", "alert")
    if v >= 4:
        return (f"Households expect {v:.1f}% inflation next year — well above the Fed's comfort zone.", "elevated")
    if v > 3:
        return (f"Households expect {v:.1f}% inflation next year — a touch high.", "watch")
    return (f"Households expect {v:.1f}% inflation next year — expectations remain anchored.", "ok")


# --- Fiscal Health rules ---

def rule_debt_gdp(obs):
    """GFDEGDQ188S: federal debt as % of GDP. <90 ok, 90-110 watch,
    110-130 elevated, >=130 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 130:
        return (f"Federal debt is {v:.0f}% of GDP — uncharted territory for the U.S.", "alert")
    if v >= 110:
        return (f"Federal debt is {v:.0f}% of GDP — larger than the entire economy.", "elevated")
    if v >= 90:
        return (f"Federal debt is {v:.0f}% of GDP — high by historical standards.", "watch")
    return (f"Federal debt is {v:.0f}% of GDP — a manageable level.", "ok")


def rule_deficit_12m(obs):
    """Trailing-12-month deficit in $trillions (positive = deficit).
    <0.8 ok, 0.8-1.5 watch, 1.5-2.5 elevated, >=2.5 alert (COVID peak ~$3T)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 2.5:
        return (f"The U.S. has borrowed ${v:.1f} trillion over the past year — crisis-era scale.", "alert")
    if v >= 1.5:
        return (f"The U.S. has borrowed ${v:.1f} trillion over the past year — heavy borrowing for a growing economy.", "elevated")
    if v >= 0.8:
        return (f"The U.S. has borrowed ${v:.1f} trillion over the past year — a sizable structural deficit.", "watch")
    if v >= 0:
        return (f"The deficit is ${v:.1f} trillion over the past year — moderate by recent standards.", "ok")
    return (f"The government ran a ${abs(v):.1f} trillion surplus over the past year.", "ok")


# --- Housing & Real Estate rules ---

def market_health(label, hot, cold):
    """Factory: two-sided market-health severity from the trailing-12-month % change.
    `hot` and `cold` are (watch, elevated, alert) YoY-% thresholds — hot positive
    (overheating), cold negative (freezing). Both extremes raise severity."""
    hot_w, hot_e, hot_a = hot
    cold_w, cold_e, cold_a = cold

    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label}: latest reading {v:,.0f}.", "ok")
        pct = (v - prior) / abs(prior) * 100
        if pct >= hot_a:
            return (f"{label}: up {pct:.0f}% from a year ago — overheating.", "alert")
        if pct >= hot_e:
            return (f"{label}: up {pct:.0f}% from a year ago — running hot.", "elevated")
        if pct >= hot_w:
            return (f"{label}: up {pct:.0f}% from a year ago — heating up.", "watch")
        if pct <= cold_a:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — a deep freeze.", "alert")
        if pct <= cold_e:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — cooling sharply.", "elevated")
        if pct <= cold_w:
            return (f"{label}: down {abs(pct):.0f}% from a year ago — cooling.", "watch")
        if pct >= 1:
            return (f"{label}: up {pct:.0f}% from a year ago — a steady pace.", "ok")
        if pct <= -1:
            return (f"{label}: down {abs(pct):.0f}% from a year ago.", "ok")
        return (f"{label}: little changed from a year ago ({pct:+.0f}%).", "ok")

    _rule.band_spec = bands.BandSpec(kind="yoy_computed", unit="%",
        edges=(cold_a, cold_e, cold_w, hot_w, hot_e, hot_a),
        segments=("alert", "elevated", "watch", "ok", "watch", "elevated", "alert"))
    _rule.band_tag = "market_health"
    return _rule


def rule_affordability(obs):
    """FIXHAI: NAR affordability index. 100 = the median family barely qualifies
    for the median home. >=130 ok, 110-130 watch, 95-110 elevated, <95 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 130:
        return (f"The affordability index is {v:.0f} — the median family comfortably affords the median home.", "ok")
    if v >= 110:
        return (f"The affordability index is {v:.0f} — affordable, but with less cushion than usual.", "watch")
    if v >= 95:
        return (f"The affordability index is {v:.0f} — the median family barely qualifies for the median home.", "elevated")
    return (f"The affordability index is {v:.0f} — the median home is out of reach for the median family.", "alert")


def rule_mortgage_delinquency(obs):
    """DRSFRMACBS: % of bank single-family mortgages past due.
    <2 ok, 2-4 watch, 4-7 elevated, >=7 alert (2009 peak ~11)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 2:
        return (f"Just {v:.1f}% of mortgages are delinquent — homeowners are keeping up.", "ok")
    if v < 4:
        return (f"Mortgage delinquencies are at {v:.1f}% — creeping up off their lows.", "watch")
    if v < 7:
        return (f"Mortgage delinquencies have climbed to {v:.1f}% — real homeowner stress.", "elevated")
    return (f"Mortgage delinquencies are at {v:.1f}% — crisis-level homeowner distress.", "alert")


def rule_months_supply(obs):
    """MSACSR: months' supply of new houses. 4-6 balanced; low = tight (hot),
    high = glut (cold). <3 elevated, 3-4 watch, 4-6 ok, 6-8 watch, 8-10 elevated, >10 alert."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 3:
        return (f"Just {v:.1f} months of new-home supply — a tight market that props up prices.", "elevated")
    if v < 4:
        return (f"{v:.1f} months of new-home supply — on the tight side.", "watch")
    if v <= 6:
        return (f"{v:.1f} months of new-home supply — a balanced market.", "ok")
    if v <= 8:
        return (f"{v:.1f} months of new-home supply — inventory is building up.", "watch")
    if v <= 10:
        return (f"{v:.1f} months of new-home supply — a glut that pressures prices and builders.", "elevated")
    return (f"{v:.1f} months of new-home supply — a severe glut.", "alert")


def rule_rental_vacancy(obs):
    """RRVRUSQ156N: rental vacancy %. 6-8 healthy; low = rent pressure (hot),
    high = glut (cold). <5 elevated, 5-6 watch, 6-8 ok, 8-10 watch, >10 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 5:
        return (f"Rental vacancy is just {v:.1f}% — a tight market that pushes rents up.", "elevated")
    if v < 6:
        return (f"Rental vacancy is {v:.1f}% — on the tight side, supporting rent growth.", "watch")
    if v <= 8:
        return (f"Rental vacancy is {v:.1f}% — a healthy balance between renters and landlords.", "ok")
    if v <= 10:
        return (f"Rental vacancy is {v:.1f}% — loosening in renters' favor.", "watch")
    return (f"Rental vacancy is {v:.1f}% — a glut of empty rentals.", "elevated")


def level_points(label):
    """Descriptive `info` for a %-level series: latest value + ~12-month change in
    points. Label must read as a singular subject ("The homeownership rate")."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None:
            return (f"{label} is {v:.1f}%.", "info")
        delta = v - prior
        if delta >= 0.2:
            return (f"{label} is {v:.1f}%, up {delta:.1f} points from a year ago.", "info")
        if delta <= -0.2:
            return (f"{label} is {v:.1f}%, down {abs(delta):.1f} points from a year ago.", "info")
        return (f"{label} is {v:.1f}%, little changed from a year ago.", "info")
    return _rule


# --- Global Economy rules ---

# --- Corporate & Business Health rules ---

def yoy_contraction_band(label, watch, elevated, alert, verb="are"):
    """Factory: one-sided severity for an already-YoY % series where FALLING is
    the stress signal (profits, business applications, capex orders). Thresholds
    are YoY-% values, descending (e.g. 0, -5, -15). Label reads as a plural
    subject ("Corporate profits"); pass verb="is" for singular ones."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v <= alert:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — a severe contraction.", "alert")
        if v <= elevated:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — contracting sharply.", "elevated")
        if v < watch:
            return (f"{label} {verb} down {abs(v):.1f}% from a year ago — shrinking.", "watch")
        if v >= 1:
            return (f"{label} {verb} growing {v:.1f}% a year.", "ok")
        return (f"{label} {verb} roughly flat versus a year ago ({v:+.1f}%).", "ok")
    _rule.band_spec = bands.BandSpec(kind="yoy", unit="%",
        edges=tuple(sorted((watch, elevated, alert))),
        segments=("alert", "elevated", "watch", "ok"))
    _rule.band_tag = "yoy_contraction_band"
    return _rule


def rule_baa_spread(obs):
    """BAA10YM: Moody's Baa yield minus the 10-year Treasury, in points.
    <2.0 ok, 2.0-2.5 watch, 2.5-3.5 elevated, >=3.5 alert (2008 ~6, COVID ~3.5)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 3.5:
        return (f"The Baa spread is {v:.2f} points — crisis-grade pricing of corporate credit risk.", "alert")
    if v >= 2.5:
        return (f"The Baa spread is {v:.2f} points — wide, a sign of building credit stress.", "elevated")
    if v >= 2.0:
        return (f"The Baa spread is {v:.2f} points — drifting wider off its lows.", "watch")
    return (f"The Baa spread is {v:.2f} points — corporate credit is priced calm.", "ok")


def rule_lending_standards(obs):
    """DRTSCILM: net % of banks tightening C&I standards (SLOOS).
    <=0 ok, 0-20 watch, 20-50 elevated, >50 alert (2008 ~84, COVID ~71)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v > 50:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — a credit crunch.", "alert")
    if v >= 20:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — broad tightening, a classic late-cycle signal.", "elevated")
    if v > 0:
        return (f"A net {v:.0f}% of banks are tightening business-loan standards — mild tightening.", "watch")
    if v < 0:
        return (f"A net {abs(v):.0f}% of banks are easing business-loan standards — credit is getting easier.", "ok")
    return ("Banks are neither tightening nor easing business-loan standards on balance.", "ok")


def rule_business_delinquency(obs):
    """DRBLACBS: % of bank business loans past due.
    <1.5 ok, 1.5-2.5 watch, 2.5-4.0 elevated, >=4.0 alert (2009 peak ~4.4)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 4.0:
        return (f"Business-loan delinquencies are at {v:.2f}% — crisis-level borrower distress.", "alert")
    if v >= 2.5:
        return (f"Business-loan delinquencies have climbed to {v:.2f}% — real borrower stress.", "elevated")
    if v >= 1.5:
        return (f"Business-loan delinquencies are at {v:.2f}%, creeping up off their lows.", "watch")
    return (f"Just {v:.2f}% of business loans are delinquent — borrowers are keeping up.", "ok")


def rule_inventories_sales(obs):
    """ISRATIO: total-business inventories-to-sales ratio (months of sales).
    <1.40 ok, 1.40-1.50 watch, >=1.50 elevated (2008 peaked ~1.48, COVID ~1.74)."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 1.50:
        return (f"Inventories equal {v:.2f} months of sales — an overhang that typically forces production cuts.", "elevated")
    if v >= 1.40:
        return (f"Inventories equal {v:.2f} months of sales — stocks are building up.", "watch")
    return (f"Inventories equal {v:.2f} months of sales — lean and healthy.", "ok")


def rule_dollar_yoy(obs):
    """Broad dollar index, already YoY % (pc1). Two-sided: |YoY| <5 ok /
    5-9 watch / 9-12 elevated / >=12 alert. Both a surging and a sliding
    dollar raise severity; text is direction-aware."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    direction = "up" if v >= 0 else "down"
    mag = abs(v)
    if mag >= 12:
        return (f"The dollar is {direction} {mag:.1f}% against major currencies over the "
                "past year — a violent move that squeezes the global financial system.",
                "alert")
    if mag >= 9:
        return (f"The dollar is {direction} {mag:.1f}% against major currencies over the "
                "past year — a sharp run by historical standards.", "elevated")
    if mag >= 5:
        return (f"The dollar is {direction} {mag:.1f}% against major currencies over the "
                "past year — a sizable swing.", "watch")
    if mag >= 1:
        return (f"The dollar is {direction} {mag:.1f}% against major currencies over the "
                "past year — a normal drift.", "ok")
    return (f"The dollar is little changed against major currencies over the past year "
            f"({v:+.1f}%).", "ok")


def fx_yoy(label, weaker_when_up=False):
    """Factory: descriptive `info` read of a currency pair's ~12-month move.

    `weaker_when_up=True` for pairs quoted foreign-currency-per-USD (yen,
    yuan), where a rising rate means the foreign currency WEAKENED. The
    default suits USD-per-foreign quotes (euro), where up = stronger."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.2f} versus the dollar.", "info")
        pct = (v - prior) / abs(prior) * 100
        if weaker_when_up:
            pct = -pct
        if pct >= 1:
            return (f"{label} has strengthened {pct:.1f}% against the dollar over the "
                    "past year.", "info")
        if pct <= -1:
            return (f"{label} has weakened {abs(pct):.1f}% against the dollar over the "
                    "past year.", "info")
        return (f"{label} is little changed against the dollar over the past year.",
                "info")
    return _rule


def world_growth(forecast):
    """Factory: IMF world real-GDP growth (annual level). Bands: >=3.2 ok /
    2.5-3.2 watch / 2.0-2.5 elevated / <2.0 alert (sub-2% ≈ global recession).
    `forecast` is a zero-arg callable (imf.forecast_for) returning
    {"year","value"} or None; when present, the nearest forward IMF projection
    (normally the current year) is appended in prose — never charted or
    key-stat'ed."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        year, v = obs[-1]
        if v >= 3.2:
            text, status = (f"The world economy grew {v:.1f}% in {year} — around "
                            "its long-run trend.", "ok")
        elif v >= 2.5:
            text, status = (f"The world economy grew {v:.1f}% in {year} — below "
                            "its long-run trend.", "watch")
        elif v >= 2.0:
            text, status = (f"The world economy grew just {v:.1f}% in {year} — "
                            "near stall speed.", "elevated")
        elif v >= 0:
            text, status = (f"The world economy grew only {v:.1f}% in {year} — "
                            "global recession territory.", "alert")
        else:
            text, status = (f"The world economy shrank {abs(v):.1f}% in {year} — "
                            "a global recession.", "alert")
        f = forecast()
        if f:
            text += f" The IMF projects {f['value']:.1f}% for {f['year']}."
        return text, status
    _rule.band_spec = bands.BandSpec(kind="level", unit="%",
        edges=(2.0, 2.5, 3.2), segments=("alert", "elevated", "watch", "ok"))
    _rule.band_tag = "world_growth"
    return _rule


def annual_growth(label):
    """Factory: descriptive `info` read of an annual real-GDP growth series.
    Reports the latest year and the direction versus the prior year."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        year, v = obs[-1]
        if v < 0:
            text = f"{label} shrank {abs(v):.1f}% in {year}"
        else:
            text = f"{label} grew {v:.1f}% in {year}"
        if len(obs) >= 2:
            prior = obs[-2][1]
            if v < prior - 0.2:
                text += f", slowing from {prior:.1f}% the year before"
            elif v > prior + 0.2:
                text += f", up from {prior:.1f}% the year before"
            else:
                text += f", matching the year before"
        return text + ".", "info"
    return _rule


def rule_world_inflation(obs):
    """IMF world consumer-price inflation (annual level). Descriptive `info`
    with the direction versus the prior year."""
    if not obs:
        return _NO_DATA
    year, v = obs[-1]
    text = f"World consumer prices are rising {v:.1f}% in {year}"
    if len(obs) >= 2:
        prior = obs[-2][1]
        if v < prior - 0.2:
            text += f", easing from {prior:.1f}% the year before"
        elif v > prior + 0.2:
            text += f", up from {prior:.1f}% the year before"
        else:
            text += f", about the same as the year before"
    return text + ".", "info"


def rule_gscpi(obs):
    """NY Fed Global Supply Chain Pressure Index (σ from historical mean).
    <0.5 ok / 0.5-1.5 watch / 1.5-2.5 elevated / >=2.5 alert; negative =
    looser than normal (ok). COVID peaked near 4.5σ."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 2.5:
        return (f"Supply-chain pressure is {v:.1f}σ above normal — extreme disruption "
                "(the COVID peak was about 4.5σ).", "alert")
    if v >= 1.5:
        return (f"Supply-chain pressure is {v:.1f}σ above normal — real strain in "
                "global logistics.", "elevated")
    if v >= 0.5:
        return (f"Supply-chain pressure is {v:.1f}σ above normal — tighter than "
                "usual.", "watch")
    if v >= 0:
        return (f"Supply chains are running normally ({v:+.1f}σ from the historical "
                "mean).", "ok")
    return (f"Supply chains are running looser than normal ({v:.1f}σ) — no pressure.",
            "ok")


def rule_trade_deficit(obs):
    """U.S. goods & services trade gap in $B/month, presented as the size of
    the deficit (positive = deficit — the U.S. has run one every year since
    1976), so the hub's ▲/▼ delta reads intuitively: ▲ = deficit widening.
    Descriptive `info`: wider/narrower/about the same vs a year ago."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= 0:
        return (f"The U.S. is running a ${abs(v):.1f}B monthly trade surplus — rare in "
                "modern history.", "info")
    prior = _value_year_ago(obs)
    text = f"The U.S. trade deficit is ${v:.1f}B a month"
    if prior is not None and prior > 0:
        if v > prior * 1.05:
            text += ", wider than a year ago"
        elif v < prior * 0.95:
            text += ", narrower than a year ago"
        else:
            text += ", about the same as a year ago"
    return text + ".", "info"


def epu_band(label, cap=None):
    """Factory: Baker/Bloom/Davis Economic Policy Uncertainty level bands.
    Long-run norm ≈ 100: <120 ok / 120-200 watch / 200-300 elevated /
    >=300 alert. Label must read as a singular subject. `cap` (a status
    string) limits how far this indicator can push the lens badge — for
    laggy series (GEPU publishes ~6 months late) that should sanity-check
    the timelier lead indicator, not drive a months-stale alarm."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v >= 300:
            text, status = (f"{label} is at {v:.0f} — extreme by historical "
                            "standards (the long-run norm is about 100).", "alert")
        elif v >= 200:
            text, status = (f"{label} is at {v:.0f} — far above its long-run "
                            "norm of about 100.", "elevated")
        elif v >= 120:
            text, status = (f"{label} is at {v:.0f} — above its long-run norm "
                            "of about 100.", "watch")
        else:
            text, status = (f"{label} is at {v:.0f} — a normal level (the "
                            "long-run norm is about 100).", "ok")
        if cap and util.STATUS_ORDER.get(status, 0) > util.STATUS_ORDER[cap]:
            status = cap
        return text, status
    _rule.band_spec = bands.BandSpec(kind="level", unit="", value_format="thousands",
        edges=(120, 200, 300), segments=("ok", "watch", "elevated", "alert"),
        cap=cap or "")
    _rule.band_tag = "epu_band"
    return _rule


# --- Band descriptors for the bespoke severity rules (score-explain-order, 2026-06-26).
# The severity factories self-describe above (spec built from their args); these
# hand-listed specs duplicate each rule body's thresholds and are guarded structurally
# by test_bands.py, which feeds synthetic observations straddling every declared edge
# and asserts the live rule flips where the descriptor says. Edit a threshold without
# editing its spec here and the build turns red. Curated 'why' prose lives in
# reasons.BAND_WHY[band_tag] (band_tag == the rule's name).
def _bespoke(rule, **kw):
    rule.band_spec = bands.BandSpec(**kw)
    rule.band_tag = rule.__name__


_bespoke(rule_sahm, kind="level", unit="", edges=(0.35, 0.50),
         segments=("ok", "watch", "alert"))
_bespoke(rule_claims, kind="level", unit="", value_format="thousands",
         edges=(250000, 300000), segments=("ok", "watch", "elevated"))
_bespoke(rule_unemployment_trend, kind="delta_from_low", unit="pts", edges=(0.5,),
         segments=("ok", "watch"))
_bespoke(rule_fed_funds, kind="level", unit="%", edges=(4.0,), segments=("ok", "watch"))
_bespoke(rule_mortgage, kind="level", unit="%", edges=(5.5, 6.5, 7.5),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_payrolls, kind="level", unit="", value_format="thousands",
         edges=(0, 75000, 150000), segments=("alert", "watch", "watch", "ok"))
_bespoke(rule_job_openings, kind="level", unit="M", edges=(7.5,),
         segments=("watch", "ok"))
_bespoke(rule_wage_growth, kind="yoy", unit="%", edges=(2.0, 3.0),
         segments=("elevated", "watch", "ok"))
_bespoke(rule_auto_sales, kind="level", unit="M", edges=(12, 13.5, 15),
         segments=("alert", "elevated", "watch", "ok"))
_bespoke(rule_mortgage_debt_service, kind="level", unit="%", edges=(6, 7, 8),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_interest_burden, kind="level", unit="%", edges=(10, 15, 22),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_inflation, kind="yoy", unit="%", edges=(2.5, 4.0),
         segments=("ok", "watch", "elevated"))
_bespoke(rule_real_wages, kind="yoy", unit="%", edges=(0,), segments=("watch", "ok"))
_bespoke(rule_noncurrent, kind="level", unit="%", edges=(1, 2, 3),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_charge_offs, kind="level", unit="%", edges=(0.6, 1.2, 2.0),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_cre_concentration, kind="level", unit="%", edges=(200, 300),
         segments=("ok", "watch", "elevated"))
_bespoke(rule_uninsured_share, kind="level", unit="%", edges=(40,),
         segments=("ok", "watch"))
_bespoke(rule_capital_ratio, kind="level", unit="%", edges=(7.5, 9),
         segments=("elevated", "watch", "ok"))
_bespoke(rule_risk_based_capital, kind="level", unit="%", edges=(8, 10),
         segments=("elevated", "watch", "ok"))
_bespoke(rule_net_margin, kind="level", unit="%", edges=(2.5,),
         segments=("watch", "ok"))
_bespoke(rule_roa, kind="level", unit="%", edges=(0, 0.5, 1.0),
         segments=("alert", "elevated", "watch", "ok"))
_bespoke(rule_loans_deposits, kind="level", unit="%", edges=(90,),
         segments=("ok", "watch"))
_bespoke(rule_vix, kind="level", unit="", edges=(20, 30, 40),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_financial_conditions, kind="level", unit="", edges=(0, 0.5, 1.0),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_m2_growth, kind="yoy", unit="%", edges=(-3, -1, 7, 10),
         segments=("elevated", "watch", "ok", "watch", "elevated"))
_bespoke(rule_debt_service, kind="level", unit="%", edges=(10.5, 12, 13),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_saving_rate, kind="level", unit="%", edges=(3, 5),
         segments=("elevated", "watch", "ok"))
_bespoke(rule_real_income, kind="yoy", unit="%", edges=(-2, 0),
         segments=("elevated", "watch", "ok"))
_bespoke(rule_sentiment, kind="level", unit="", edges=(55, 70, 85),
         segments=("alert", "elevated", "watch", "ok"))
_bespoke(rule_inflation_expectations, kind="level", unit="%", edges=(3, 4, 5.5),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_revolving_credit, kind="yoy", unit="%", edges=(8, 12),
         segments=("ok", "watch", "elevated"))
_bespoke(rule_debt_gdp, kind="level", unit="%", edges=(90, 110, 130),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_deficit_12m, kind="level", unit="$T", edges=(0.8, 1.5, 2.5),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_affordability, kind="level", unit="", edges=(95, 110, 130),
         segments=("alert", "elevated", "watch", "ok"))
_bespoke(rule_mortgage_delinquency, kind="level", unit="%", edges=(2, 4, 7),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_months_supply, kind="level", unit="months", edges=(3, 4, 6, 8, 10),
         segments=("elevated", "watch", "ok", "watch", "elevated", "alert"))
_bespoke(rule_rental_vacancy, kind="level", unit="%", edges=(5, 6, 8, 10),
         segments=("elevated", "watch", "ok", "watch", "elevated"))
_bespoke(rule_baa_spread, kind="level", unit="%", edges=(2.0, 2.5, 3.5),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_lending_standards, kind="level", unit="%", edges=(0, 20, 50),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_business_delinquency, kind="level", unit="%", edges=(1.5, 2.5, 4.0),
         segments=("ok", "watch", "elevated", "alert"))
_bespoke(rule_inventories_sales, kind="level", unit="", edges=(1.40, 1.50),
         segments=("ok", "watch", "elevated"))
_bespoke(rule_dollar_yoy, kind="yoy", unit="%", edges=(-12, -9, -5, 5, 9, 12),
         segments=("alert", "elevated", "watch", "ok", "watch", "elevated", "alert"))
_bespoke(rule_gscpi, kind="level", unit="σ", edges=(0.5, 1.5, 2.5),
         segments=("ok", "watch", "elevated", "alert"))
# History-dependent (the un-inversion state depends on recent history, not just the
# latest value), so it is NOT a static single-axis band: prose-only on the methodology
# page, excluded from the edge-flip drift test.
# Vestigial bands (custom kind never renders edges/segments) — kept in the rule's true
# order anyway: below zero (inverted) is the elevated recession warning, not 'ok'.
_bespoke(rule_yield_curve, kind="custom", unit="%", edges=(0,),
         segments=("elevated", "ok"), probe=False)


HEADLINES = {
    "recession-watch": {
        "alert": "Recession signals are flashing red.",
        "elevated": "Recession risk is elevated — a key warning signal is flashing.",
        "watch": "No recession underway — but the warning lights are no longer all green.",
        "ok": "The economy looks steady — no major recession signals right now.",
        "unknown": "Some recession signals are temporarily unavailable.",
    },
    "cost-of-money": {
        "alert": "Borrowing costs are extreme — money is very expensive.",
        "elevated": "Borrowing costs are high and restrictive across the board.",
        "watch": "Borrowing is still expensive — rates remain elevated.",
        "ok": "Borrowing costs have eased back toward normal.",
        "unknown": "Some rate data is temporarily unavailable.",
    },
    "job-market": {
        "alert": "The job market is contracting — employers are cutting jobs.",
        "elevated": "The job market is weakening on several fronts.",
        "watch": "The job market is cooling — still solid, but losing momentum.",
        "ok": "The job market is healthy — hiring and pay are holding up.",
        "unknown": "Some labor-market data is temporarily unavailable.",
    },
    "cost-of-living": {
        "alert": "Inflation is severe — prices are rising fast.",
        "elevated": "Inflation is still hot — well above the Fed's target.",
        "watch": "Inflation has cooled but isn't beaten — still above target.",
        "ok": "Inflation is back near the Fed's target.",
        "unknown": "Some inflation data is temporarily unavailable.",
    },
    "fiscal-health": {
        "alert": "Fiscal stress is acute — debt, deficits, or interest costs are at extremes.",
        "elevated": "The U.S. is borrowing heavily — debt and interest costs are climbing.",
        "watch": "Deficits and debt are drifting higher — worth watching.",
        "ok": "Government finances are on a sustainable track.",
        "unknown": "Some fiscal data is temporarily unavailable.",
    },
    "bank-asset-quality": {
        "alert": "Loan losses are mounting — credit quality is deteriorating fast.",
        "elevated": "Problem loans are elevated across the system.",
        "watch": "Loan books are healthy overall, but problem loans are creeping up.",
        "ok": "Bank loan quality is strong — few loans are going bad.",
        "unknown": "Some asset-quality data is temporarily unavailable.",
    },
    "bank-profitability": {
        "alert": "Bank earnings are collapsing.",
        "elevated": "Bank profitability is under real pressure.",
        "watch": "Bank earnings are holding, but margins are tightening.",
        "ok": "Banks are solidly profitable.",
        "unknown": "Some profitability data is temporarily unavailable.",
    },
    "bank-capital-solvency": {
        "alert": "Bank capital is dangerously thin.",
        "elevated": "Capital cushions are thinner than supervisors prefer.",
        "watch": "Capital is adequate but worth watching.",
        "ok": "Banks are well-capitalized.",
        "unknown": "Some capital data is temporarily unavailable.",
    },
    "bank-concentrations-funding": {
        "alert": "Funding and concentration risks are acute.",
        "elevated": "Concentration or funding risk is elevated.",
        "watch": "Some concentration and funding risks are building.",
        "ok": "Funding is stable and concentrations are contained.",
        "unknown": "Some concentration/funding data is temporarily unavailable.",
    },
    "market-risk-sentiment": {
        "alert": "Markets are pricing acute stress.",
        "elevated": "Risk is elevated — volatility and credit spreads are climbing.",
        "watch": "A few cracks are showing — sentiment is no longer all calm.",
        "ok": "Markets are calm — volatility and credit stress are low.",
        "unknown": "Some risk indicators are temporarily unavailable.",
    },
    "market-scoreboard": {
        "neutral": "How the major asset classes are moving right now.",
    },
    "crypto-structure": {
        "neutral": "How capital is rotating across the crypto market.",
    },
    "market-liquidity": {
        "alert": "Monetary conditions are at an extreme — liquidity is the story.",
        "elevated": "Liquidity is moving sharply — the monetary backdrop is shifting.",
        "watch": "Liquidity is tightening at the margin — worth watching.",
        "ok": "Liquidity is ample — no monetary squeeze in sight.",
        "unknown": "Some liquidity data is temporarily unavailable.",
    },
    "consumer-spending": {
        "alert": "Consumer spending is at an extreme — demand is flashing red.",
        "elevated": "Consumer spending is under strain — demand is bending.",
        "watch": "Consumer spending is wobbling — still growing, but losing steam.",
        "ok": "Consumers are still spending at a healthy pace.",
        "unknown": "Some spending data is temporarily unavailable.",
    },
    "consumer-credit": {
        "alert": "Consumer credit is cracking — stress has reached crisis levels.",
        "elevated": "Consumer credit stress is real — late payments are climbing.",
        "watch": "Consumer credit bears watching — debt loads are creeping up.",
        "ok": "Consumer credit is healthy — households are keeping up with their debts.",
        "unknown": "Some credit data is temporarily unavailable.",
    },
    "consumer-income-savings": {
        "alert": "Household finances are in distress — incomes and savings are exhausted.",
        "elevated": "Household cushions are thin — savings or real incomes are stretched.",
        "watch": "Household finances are tightening — cushions are shrinking.",
        "ok": "Household finances are solid — incomes and savings are holding up.",
        "unknown": "Some income data is temporarily unavailable.",
    },
    "consumer-sentiment": {
        "alert": "Consumers are deeply pessimistic — sentiment is near record lows.",
        "elevated": "Consumer mood is grim — confidence is at recession levels.",
        "watch": "Consumers are uneasy — confidence is below normal.",
        "ok": "Consumers are confident — the mood is healthy.",
        "unknown": "Some sentiment data is temporarily unavailable.",
    },
    "energy-oil-fuels": {
        "alert": "Fuel costs are spiking — acute pressure at the pump.",
        "elevated": "Fuel costs are well above last year.",
        "watch": "Fuel costs are climbing.",
        "ok": "Fuel costs are stable or easing.",
        "unknown": "Some fuel data is temporarily unavailable.",
    },
    "energy-natural-gas": {
        "alert": "Natural gas costs are spiking.",
        "elevated": "Natural gas is well above last year.",
        "watch": "Natural gas costs are climbing.",
        "ok": "Natural gas costs are stable or easing.",
        "unknown": "Some natural-gas data is temporarily unavailable.",
    },
    "energy-electricity": {
        "alert": "Power bills are spiking.",
        "elevated": "Electricity prices are well above last year.",
        "watch": "Electricity prices are climbing.",
        "ok": "Power bills are steady.",
        "unknown": "Some electricity data is temporarily unavailable.",
    },
    "energy-commodities": {
        "alert": "Commodity costs are surging.",
        "elevated": "Commodity and food costs are well above last year.",
        "watch": "Commodity costs are climbing.",
        "ok": "Commodity costs are stable or easing.",
        "unknown": "Some commodity data is temporarily unavailable.",
    },
    "housing-home-prices": {
        "alert": "The housing market is flashing red — prices or sales are at an extreme.",
        "elevated": "The housing market is out of balance — prices or sales are under strain.",
        "watch": "The housing market is shifting — prices or sales are moving off balance.",
        "ok": "The housing market looks balanced — prices and sales are steady.",
        "unknown": "Some home-price data is temporarily unavailable.",
    },
    "housing-affordability": {
        "alert": "Buying a home is out of reach for the typical family.",
        "elevated": "Housing affordability is badly stretched.",
        "watch": "Housing affordability is tightening.",
        "ok": "Housing is broadly affordable for the typical family.",
        "unknown": "Some affordability data is temporarily unavailable.",
    },
    "housing-supply-construction": {
        "alert": "Housing supply is at an extreme — construction or inventory is flashing red.",
        "elevated": "Housing supply is out of balance — inventory or construction is strained.",
        "watch": "Housing supply is shifting — construction and inventory bear watching.",
        "ok": "Housing supply looks healthy — construction and inventory are in balance.",
        "unknown": "Some construction data is temporarily unavailable.",
    },
    "housing-rent-shelter": {
        "alert": "Rents are surging — acute pressure on renters.",
        "elevated": "Rents are rising fast and the rental market is strained.",
        "watch": "Rents are climbing — renters are feeling it.",
        "ok": "The rental market is balanced — rents are behaving.",
        "unknown": "Some rental data is temporarily unavailable.",
    },
    "business-profitability": {
        "alert": "Corporate profits are collapsing.",
        "elevated": "Corporate profits are contracting — earnings are under real pressure.",
        "watch": "Corporate profit growth is stalling.",
        "ok": "Corporate America is profitable — earnings are growing.",
        "unknown": "Some profit data is temporarily unavailable.",
    },
    "business-formation": {
        "alert": "Business formation has collapsed.",
        "elevated": "Business formation is contracting — fewer new firms are being started.",
        "watch": "Business formation is losing steam.",
        "ok": "New businesses are forming at a healthy clip.",
        "unknown": "Some formation data is temporarily unavailable.",
    },
    "business-investment": {
        "alert": "Business investment is collapsing — orders or sales are contracting hard.",
        "elevated": "Business investment is contracting.",
        "watch": "Business investment is wobbling — orders or sales are slipping.",
        "ok": "Businesses are investing — orders and sales are growing.",
        "unknown": "Some investment data is temporarily unavailable.",
    },
    "business-credit": {
        "alert": "Business credit is in crisis — lending is seizing up.",
        "elevated": "Business credit is tightening — stress is building.",
        "watch": "Business credit bears watching — conditions are tightening at the margin.",
        "ok": "Business credit is flowing — spreads and delinquencies are low.",
        "unknown": "Some business-credit data is temporarily unavailable.",
    },
    "global-dollar-currencies": {
        "alert": "The dollar is moving violently — a global financial squeeze.",
        "elevated": "The dollar is on a sharp run — global conditions are shifting fast.",
        "watch": "The dollar is swinging — a sizable move against world currencies.",
        "ok": "Currency markets are calm — the dollar is near where it was a year ago.",
        "unknown": "Some currency data is temporarily unavailable.",
    },
    "global-growth": {
        "alert": "The world economy is in recession territory.",
        "elevated": "Global growth is near stall speed.",
        "watch": "Global growth is running below trend.",
        "ok": "The world economy is growing around its long-run trend.",
        "unknown": "Some global growth data is temporarily unavailable.",
    },
    "global-trade-supply": {
        "alert": "Global trade is severely disrupted — supply chains or import costs are at extremes.",
        "elevated": "Global trade is under real strain — supply chains or import costs are stressed.",
        "watch": "Trade frictions are building — supply chains or import costs bear watching.",
        "ok": "Global trade is flowing normally — supply chains are running smoothly.",
        "unknown": "Some trade data is temporarily unavailable.",
    },
    "global-uncertainty": {
        "alert": "Policy uncertainty is extreme — governments themselves are the biggest risk in the outlook.",
        "elevated": "Policy uncertainty is high — what governments do next is a major source of risk.",
        "watch": "Policy uncertainty is above its historical norm.",
        "ok": "The policy backdrop is calm — uncertainty is at normal levels.",
        "unknown": "Some uncertainty data is temporarily unavailable.",
    },
}


NEUTRAL_LENSES = {"market-scoreboard", "crypto-structure"}

SEVERITY_TOKENS = {"ok", "watch", "elevated", "alert"}
MOMENTUM_TOKENS = {"up", "down", "flat"}


def _probe(direction):
    """A synthetic 40-year monthly series trending up (direction=1) or down (-1),
    with a wave, so a rule's bands are exercised across a wide value range."""
    return [(f"{1986 + i // 12:04d}-{1 + i % 12:02d}-01",
             100.0 + direction * i * 0.3 + (i % 7) * 0.3) for i in range(480)]


_PROBES = (_probe(1), _probe(-1))  # built once: rising, falling


@functools.lru_cache(maxsize=None)
def rule_kind(rule):
    """Classify a narrative rule by the status family it CAN emit: 'severity'
    (ok/watch/elevated/alert), 'momentum' (up/down/flat), 'info', or 'unknown'.

    Pure (no network — synthetic probes), so ordering and the 'why absent' notes can
    ask what a rule can do independent of today's value. Probed in BOTH directions
    and unioned, so a one-sided band that only warns on a fall (or a rise) still reads
    as severity. Cached per rule object (rules are module-level callables)."""
    kinds = set()
    for probe in _PROBES:
        try:
            _, status = rule(probe)
        except Exception:  # noqa: BLE001 - a crashing probe never blocks classification
            continue
        if status in SEVERITY_TOKENS:
            kinds.add("severity")
        elif status == "info":
            kinds.add("info")
        elif status in MOMENTUM_TOKENS:
            kinds.add("momentum")
    for kind in ("severity", "momentum", "info"):
        if kind in kinds:
            return kind
    return "unknown"


def synthesize(lens_id, statuses):
    """Combine indicator statuses into (headline_read, overall_status).

    Severity lenses aggregate to their worst status. NEUTRAL_LENSES (the markets
    scoreboard and crypto structure) carry no good/bad verdict, so they always
    report a fixed neutral headline + 'neutral' badge regardless of indicators."""
    if lens_id in NEUTRAL_LENSES:
        return HEADLINES.get(lens_id, {}).get("neutral", ""), "neutral"
    overall = util.status_max(statuses)
    headline = HEADLINES.get(lens_id, {}).get(overall, "")
    return headline, overall

"""Rule-based narrative engine. Pure functions of cleaned observations.

Each rule takes a chronological list of (date, float) tuples and returns
(text, status). Status is one of: ok, watch, elevated, alert, unknown.
"""

from . import util

_NO_DATA = ("Data unavailable.", "unknown")


def rule_yield_curve(obs):
    """T10Y2Y: inverted (<0) warns; a recent un-inversion warrants vigilance."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    recent = [val for _, val in obs[-126:]]  # ~6 months of daily data
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


def rule_rate_trend(obs):
    """Generic market-rate read: current level and ~12-month direction."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if prior is None:
        return (f"Now {v:.2f}%.", "ok")
    delta = v - prior
    if delta >= 0.1:
        move = f"up {delta:.2f} points over the past year"
    elif delta <= -0.1:
        move = f"down {abs(delta):.2f} points over the past year"
    else:
        move = "little changed over the past year"
    return (f"Now {v:.2f}%, {move}.", "ok")


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
    """Average hourly earnings, year-over-year percent."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    pace = "running ahead of recent inflation" if v >= 3.5 else "a modest pace"
    return (f"Pay is up {v:.1f}% from a year ago, {pace}.", "ok")


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
    """Noncurrent loan rate (% of loans 90+ days late). <1 ok, 1-2 watch, >=2 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 1.0:
        return (f"Just {v:.2f}% of loans are 90+ days past due — low by historical standards.", "ok")
    if v < 2.0:
        return (f"Noncurrent loans are at {v:.2f}%, creeping up off recent lows.", "watch")
    return (f"Noncurrent loans have climbed to {v:.2f}% — elevated and worth watching.", "elevated")


def rule_charge_offs(obs):
    """Net charge-off rate (% of loans). <0.6 ok, 0.6-1.2 watch, >=1.2 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 0.6:
        return (f"Banks are writing off {v:.2f}% of loans as losses — a benign level.", "ok")
    if v < 1.2:
        return (f"Loan losses are running at {v:.2f}%, above the calm-period norm.", "watch")
    return (f"Loan losses have reached {v:.2f}% — a meaningful drag on earnings.", "elevated")


def rule_coverage(obs):
    """Allowance coverage (allowance as % of noncurrent loans). Higher = safer."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 150:
        return (f"Reserves cover {v:.0f}% of problem loans — a comfortable cushion.", "ok")
    if v >= 100:
        return (f"Reserves cover {v:.0f}% of problem loans — adequate but not generous.", "watch")
    return (f"Reserves cover only {v:.0f}% of problem loans — a thin cushion.", "elevated")


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
    """Return on assets (%). >=1.0 ok, 0.5-1.0 watch, <0.5 elevated."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 1.0:
        return (f"Banks earned {v:.2f}% on their assets — solid profitability.", "ok")
    if v >= 0.5:
        return (f"Return on assets is {v:.2f}% — subdued profitability.", "watch")
    return (f"Return on assets is just {v:.2f}% — earnings are weak.", "elevated")


def rule_loans_deposits(obs):
    """Loans as % of deposits. >=90 stretched funding, else comfortable."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v >= 90:
        return (f"Banks have lent out {v:.0f}% of deposits — funding is stretched.", "watch")
    return (f"Banks have lent out {v:.0f}% of deposits — comfortable funding headroom.", "ok")


def rule_level_trend(obs):
    """Generic level metric ($000s) read as a year-over-year direction. Always 'ok' status."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    prior = _value_year_ago(obs)
    if prior is None or prior == 0:
        return (f"Latest reading: {v:,.0f}.", "ok")
    pct = (v - prior) / abs(prior) * 100
    if pct >= 5:
        return (f"Up {pct:.0f}% from a year ago.", "ok")
    if pct <= -5:
        return (f"Down {abs(pct):.0f}% from a year ago.", "ok")
    return ("Little changed from a year ago.", "ok")


# --- Markets & Financial Conditions rules ---

def rule_vix(obs):
    """CBOE VIX level. <20 calm, 20-30 nervous, >=30 fearful."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v < 20:
        return (f"The VIX is at {v:.1f} — markets are calm.", "ok")
    if v < 30:
        return (f"The VIX is at {v:.1f} — some nervousness, but not panic.", "watch")
    return (f"The VIX is at {v:.1f} — markets are fearful.", "elevated")


def credit_spread(label, calm, stressed):
    """Factory: a credit-spread rule with its own calm/stressed thresholds (%)."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        if v < calm:
            return (f"The {label} spread is {v:.2f}% — tight, signaling calm credit conditions.", "ok")
        if v < stressed:
            return (f"The {label} spread is {v:.2f}% — widening off its lows.", "watch")
        return (f"The {label} spread is {v:.2f}% — wide, a sign of credit stress.", "elevated")
    return _rule


def rule_financial_conditions(obs):
    """Chicago Fed NFCI. <=0 looser than average, 0-0.5 a touch tight, >=0.5 tight."""
    if not obs:
        return _NO_DATA
    v = obs[-1][1]
    if v <= 0:
        return (f"The NFCI is {v:.2f} — financial conditions are looser than average.", "ok")
    if v < 0.5:
        return (f"The NFCI is {v:.2f} — conditions a touch tighter than average.", "watch")
    return (f"The NFCI is {v:.2f} — financial conditions are tight.", "elevated")


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
        return (f"{label} costs are roughly flat over the past year.", "ok")
    return _rule


def energy_level(label):
    """Descriptive `info`: latest level + trailing-12-month direction. No verdict."""
    def _rule(obs):
        if not obs:
            return _NO_DATA
        v = obs[-1][1]
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return (f"{label} is at {v:,.0f}.", "info")
        pct = (v - prior) / abs(prior) * 100
        if pct >= 3:
            return (f"{label} is up {pct:.0f}% from a year ago, now {v:,.0f}.", "info")
        if pct <= -3:
            return (f"{label} is down {abs(pct):.0f}% from a year ago, now {v:,.0f}.", "info")
        return (f"{label} is little changed from a year ago, now {v:,.0f}.", "info")
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
        return (f"{label}: little changed from a year ago ({pct:+.0f}%).", "ok")

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


HEADLINES = {
    "recession-watch": {
        "alert": "Recession signals are flashing — multiple indicators have tripped.",
        "elevated": "Recession risk is elevated — the yield curve is warning.",
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
    "bank-asset-quality": {
        "alert": "Loan losses are mounting — credit quality is deteriorating fast.",
        "elevated": "Problem loans are elevated — commercial real estate is the pressure point.",
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
        "elevated": "The housing market is out of balance — prices and sales are under strain.",
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
}


NEUTRAL_LENSES = {"market-scoreboard", "crypto-structure"}


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

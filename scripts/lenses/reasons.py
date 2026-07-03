"""Reader-facing copy for *why a signal carries no score or no forecast*.

A small reusable set keyed by situation, assigned to indicators in config.py and
rendered near the badge / prediction slot (lens.js, predict.js, staticread.py).
This is reader prose — review it here. See the matrix in
docs/superpowers/specs/2026-06-24-score-explain-order-signals-design.md.
"""

# --- Why it isn't scored (no_severity_reason) ---
NEUTRAL_SCOREBOARD = ("Part of a neutral scoreboard — it shows which way the price is "
                      "moving, not whether that's good or bad.")
NEUTRAL_CRYPTO = ("A structural read on how money is rotating within crypto — not a "
                  "good-or-bad verdict.")
MARKET_PRICE = ("A market price has no inherent good-or-bad level — higher or lower "
                "isn't itself better or worse.")
PHYSICAL = ("A physical supply-and-demand reading, not a household cost — this lens's "
            "verdict comes from the price indicators.")
FED_PLUMBING = ("A descriptive level of the monetary plumbing — this lens's verdict is "
                "carried by M2 money-supply growth.")
RATE_EXPECTATIONS = ("Whether markets expect cuts or hikes isn't itself good or bad — "
                     "it's the bond market's forecast, shown for context.")
TRADE_DEFICIT = ("The U.S. has run a trade deficit every year since 1976 — the level "
                 "isn't good or bad on its own; what matters is the trend shown here.")
INTEREST_DOLLARS = ("The dollar interest bill climbs with the economy; the scored read is "
                    "interest as a share of revenue, alongside debt-to-GDP and the deficit.")
DEMOGRAPHIC_LEVEL = ("This level drifts with demographics — the job-market verdict is "
                     "carried by unemployment, payrolls, and job openings.")
LEVEL_CONTEXT = ("A descriptive level shown for context — neither a high nor a low "
                 "reading is simply good or bad.")
RAW_INVENTORY = ("Months' supply, which adjusts for the sales pace, carries this lens's "
                 "supply verdict; this is the raw count for context.")
CONTEXT_GROWTH = "Shown for context alongside this lens's lead growth reading."
AUTO_RATE = ("A retail borrowing rate shown for context — the scored consumer-stress "
             "reads here are delinquencies, balances, and debt service.")
QUITS = ("The quits rate tends to track workers' confidence in finding another job — "
         "shown for context; the verdict is carried by unemployment, payrolls, and "
         "openings.")
CONTEXT_DEMAND = ("Shown for context — a noisy global-demand pulse the lens's scored "
                  "indicators read more cleanly.")
SMALL_BUSINESS_NOISE = ("Shown for context — proprietors' income (which includes farm "
                        "income) is too volatile to score cleanly.")

# --- Why it isn't forecast (no_prediction_reason) ---
ANNUAL = ("This series updates only once or twice a year — too few data points to build "
          "an honest forecast range. (The IMF's own projection is noted in the read above.)")
COMPUTED_SHARE = ("This is computed from other series at refresh time, so there's no "
                  "single line to forecast directly.")
CRYPTO_HISTORY = ("We've only been recording this since the site launched — not yet enough "
                  "history to forecast honestly.")

# --- 'Why these bands' — the calibration note shown on the methodology page beneath
# each scored signal's scale (score-explain-order follow-up, 2026-06-26). Keyed by the
# rule's band_tag (factory name, or the bespoke rule's own name). The NUMBERS are guarded
# structurally by test_bands.py; only these WORDS need a human's eyes.
# CURATED — Michael reviews/fact-checks this block before it ships.
BAND_WHY = {
    # Factories
    "restrictive_rate": (
        "Scored by level: above the watch line a Treasury yield is pricier than the "
        "post-2010 norm for borrowers; above the elevated line it's broadly restrictive. "
        "There is no 'alert' here — an expensive rate is a drag, not a crisis the way a "
        "default spike is."),
    "consumer_cost": (
        "Scored on the trailing-12-month change, because what strains a household is how "
        "fast a cost is rising, not its dollar level. The bands reflect how volatile each "
        "fuel or power price normally is; a falling cost reads as relief (ok)."),
    "yoy_band": (
        "A cost already expressed as a year-over-year rate. Same logic as the fuel costs: "
        "faster annual increases mean more household strain; flat or falling is ok."),
    "yoy_band_two_sided": (
        "Scored on the year-over-year change, two-sided: both an overheating boom and a "
        "sharp contraction raise severity, because each is its own kind of instability. "
        "The quiet middle band is ok."),
    "market_health": (
        "Two-sided on the trailing-12-month change: a market running too hot (a bubble) "
        "and one freezing (a bust) are both unhealthy, so both raise severity. The calm "
        "middle is a balanced market."),
    "consumer_delinquency": (
        "Delinquency-rate levels, calibrated against history — bank credit-card "
        "delinquency peaked near 6.8% in 2009. Low and steady is ok; climbing toward "
        "past-crisis levels escalates."),
    "credit_spread": (
        "The extra yield investors demand over Treasuries. Tight spreads signal calm "
        "credit; the bands mark where spreads have historically started to price real "
        "default risk (the high-yield band sits wider than investment-grade because junk "
        "spreads are structurally larger). The alert line marks blowout levels reached "
        "historically only in severe credit-stress episodes — 2008, 2011, early 2016, "
        "and March 2020 for high-yield."),
    "yoy_contraction_band": (
        "Scored on the year-over-year change where FALLING is the stress signal — profits, "
        "new-business applications, capital-goods orders, sales. Growth is ok; the bands "
        "mark progressively deeper contractions."),
    "epu_band": (
        "The Baker/Bloom/Davis policy-uncertainty index, whose long-run norm is about 100, "
        "so the bands mark multiples of that norm. The global index (GEPU) is held to a "
        "'watch' ceiling here, because it publishes about six months late — too stale to "
        "drive a live alarm."),
    "world_growth": (
        "Annual world real-GDP growth, scored against its long-run trend of about 3.5%. "
        "Below roughly 2% is what economists call a global recession; the bands step down "
        "from trend toward that line."),

    # Bespoke rules
    "rule_yield_curve": (
        "Not a static level — the curve scores by state. An inversion (below zero) is a "
        "classic recession warning that preceded every U.S. recession since the 1970s; a "
        "recent un-inversion warrants vigilance, because recessions historically begin "
        "after the curve climbs back above zero; a positive curve with no recent inversion "
        "is the all-clear."),
    "rule_sahm": (
        "The Sahm rule trips at 0.50 — historically consistent with a recession already "
        "underway. 0.35–0.50 is the warning band as it climbs toward the trigger."),
    "rule_claims": (
        "Weekly initial jobless claims. Below ~250k, employers aren't shedding workers; "
        "250–300k is a creeping rise; above 300k points to accelerating layoffs."),
    "rule_unemployment_trend": (
        "Scored on the rise above the trailing-12-month low, not the raw level (the "
        "Sahm-style signal): a climb of 0.5 points or more off the recent low has preceded "
        "past downturns."),
    "rule_fed_funds": (
        "The Fed's policy rate. At or above 4% is a restrictive stance worth flagging; the "
        "read also notes the ~12-month direction."),
    "rule_mortgage": (
        "30-year mortgage-rate levels. Below ~5.5% is moderate by recent standards; the "
        "bands step up through where affordability gets stretched (6.5%) and where most "
        "buyers are frozen out (7.5%)."),
    "rule_payrolls": (
        "Monthly jobs added. Outright job losses are an alert; under ~75k and ~150k are "
        "slowing-but-positive paces; above that is a healthy clip."),
    "rule_job_openings": (
        "Job openings (JOLTS), in millions. Below ~7.5M flags cooling labor demand."),
    "rule_wage_growth": (
        "In the job-market frame, strong pay is healthy and stalling pay signals a "
        "softening labor market, so this warns on the LOW side: under 2% a year is stalled. "
        "(The inflation angle lives in Cost of Living's real wages.)"),
    "rule_auto_sales": (
        "Light-vehicle sales (annual-rate millions) — the big-ticket purchase households "
        "cut first. ~15M+ is healthy; the 2009 and 2020 troughs near 9M anchor the alert "
        "band."),
    "rule_mortgage_debt_service": (
        "Mortgage payments as a share of income, calibrated to its own history: median "
        "~6.1%, the 2007 peak ~7.2%, the early-1980s extreme ~8.9%."),
    "rule_interest_burden": (
        "Federal interest as a share of TOTAL receipts — the conventional ~20% figure. A "
        "record-high read prints 'elevated'; 'alert' is reserved for a genuinely "
        "unprecedented level above ~22%."),
    "rule_inflation": (
        "A year-over-year inflation rate (CPI, core, or PCE) against the Fed's 2% goal: "
        "near 2% is ok, 2.5–4% is still above target, 4%+ is hot."),
    "rule_real_wages": (
        "Inflation-adjusted pay. Below zero means paychecks aren't keeping up with prices "
        "(watch); positive is ok."),
    "rule_noncurrent": (
        "Loans 90+ days past due as a share of all loans. Under 1% is low by historical "
        "standards; 1–2% is creeping; above 2% is elevated; 3%+ marks crisis territory — "
        "in the two decades of data shown it occurred only in the 2009–2013 aftermath "
        "(the early-1990s S&L era also ran that high)."),
    "rule_charge_offs": (
        "Loans written off as losses. Under ~0.6% is benign; the bands mark where losses "
        "become a meaningful drag on earnings; in the two decades of data shown, 2%+ "
        "occurred only in 2009–2010."),
    "rule_cre_concentration": (
        "Commercial real estate as a share of bank capital. Above ~300% is the interagency "
        "supervisory concentration flag; ~200% is a notable build."),
    "rule_uninsured_share": (
        "Deposits above the $250k FDIC cap — the money most likely to flee in a panic, as "
        "at Silicon Valley Bank. Above ~40% is flight-prone."),
    "rule_capital_ratio": (
        "Equity-to-assets. Banks historically run ~9–11%; below 9% is on the lighter side, "
        "below 7.5% is a thin cushion."),
    "rule_risk_based_capital": (
        "The regulators' headline solvency gauge: 10%+ is 'well-capitalized', 8–10% "
        "adequate, below 8% under the minimum."),
    "rule_net_margin": (
        "Net interest margin. Below ~2.5% is a compressed spread that squeezes bank "
        "earnings."),
    "rule_roa": (
        "Return on assets. 1%+ is solid bank profitability; 0.5–1% is subdued; below 0.5% "
        "is weak; below zero the industry as a whole is losing money — seen only at the "
        "depth of 2008–09."),
    "rule_loans_deposits": (
        "Loans as a share of deposits. Above ~90% means the system's funding is stretched."),
    "rule_vix": (
        "The equity 'fear gauge'. Below 20 is calm; 20–30 is nervous; 30+ is fearful; "
        "40+ is panic — closes that high are rare, clustering around major market "
        "shocks like 1998, 2008–09, 2020, and spring 2025."),
    "rule_financial_conditions": (
        "The Chicago Fed NFCI, where zero is average. Positive means tighter (more "
        "stressed) than normal; 0.5+ is tight; 1.0+ has printed in the modern era "
        "only during 2008–09."),
    "rule_m2_growth": (
        "Money-supply growth, two-sided: double-digit growth is historically inflationary "
        "(2020–21), while an outright contraction is rare and signals a monetary squeeze "
        "(2022–23). The calm band is roughly -1% to 7%."),
    "rule_debt_service": (
        "Household debt payments as a share of income. Above ~10.5% is above the "
        "comfortable range; the 2007 danger level of ~13% anchors the alert band."),
    "rule_saving_rate": (
        "The personal saving rate — the household shock absorber. The historical norm is "
        "5–8%; below 5% is thin, below 3% is almost no cushion."),
    "rule_real_income": (
        "Inflation-adjusted disposable income, the root of most consumer stress. Below "
        "zero is a warning; a 2%+ annual drop erodes purchasing power fast."),
    "rule_sentiment": (
        "U. Michigan consumer sentiment, long-run range roughly 50–110. 85+ is fine; the "
        "bands step down through recession-grade gloom; readings below 55 have historically "
        "been record-territory lows."),
    "rule_inflation_expectations": (
        "One-year-ahead household inflation expectations, which the Fed watches for "
        "de-anchoring. Above ~3% is a touch high; 5.5%+ suggests expectations coming "
        "unmoored."),
    "rule_revolving_credit": (
        "Credit-card balance growth. Growing faster than incomes (8%+) means households "
        "are leaning on cards; shrinking balances mean paying down."),
    "rule_debt_gdp": (
        "Federal debt versus the size of the economy. It crossed 100% around 2013; the "
        "bands mark high (90%), larger-than-the-economy (110%), and uncharted (130%)."),
    "rule_deficit_12m": (
        "The trailing-12-month deficit in trillions. The bands rise from a sizable "
        "structural deficit through crisis-era scale — the COVID peak was about $3T."),
    "rule_affordability": (
        "The NAR affordability index, where 100 means the median family just barely "
        "affords the median home. Higher is better, so the bands are inverted: 130+ is "
        "comfortable, below 95 is out of reach."),
    "rule_mortgage_delinquency": (
        "Single-family mortgages past due at banks. Under 2% is healthy; the bands climb "
        "toward the 2009 crisis peak of about 11%."),
    "rule_months_supply": (
        "Months of new-home supply, two-sided: 4–6 months is balanced, under 3 is a tight "
        "market that props up prices, and 8+ is a glut that pressures builders."),
    "rule_rental_vacancy": (
        "Rental vacancy, two-sided: 6–8% is a healthy balance, low vacancy gives landlords "
        "pricing power (rent pressure), and high vacancy hands it back to renters."),
    "rule_baa_spread": (
        "Moody's Baa corporate yield over the 10-year Treasury — the price of ordinary "
        "corporate credit risk. Calm is under 2 points; 2008 peaked near 6, which anchors "
        "the alert band."),
    "rule_lending_standards": (
        "The net share of banks tightening business-loan standards (the Fed's loan-officer "
        "survey). Easing is ok; sustained tightening above ~20% is a classic late-cycle "
        "signal; 2008 hit about 84%."),
    "rule_business_delinquency": (
        "Business loans past due at banks. Under 1.5% is healthy; the bands climb toward "
        "the 2009 peak of about 4.4%."),
    "rule_inventories_sales": (
        "Inventories measured in months of sales. Above ~1.50 is an overhang that "
        "typically forces production cuts; 2008 peaked near 1.48, COVID near 1.74."),
    "rule_dollar_yoy": (
        "The broad dollar's year-over-year move, scored two-sided on magnitude: a surging "
        "dollar squeezes the world's dollar borrowers and a sliding one imports inflation, "
        "so both raise severity. Under ~5% is normal drift."),
    "rule_gscpi": (
        "The NY Fed supply-chain pressure index, in standard deviations from normal. "
        "Negative is looser than normal (ok); the bands climb toward extreme disruption "
        "(the COVID peak was about 4.5σ)."),
}

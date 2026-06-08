"""Lens configuration — the single source of truth for what gets built."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import derive, narrative

# Helper series fetched but not displayed directly.
USREC_KEY = "USREC:lin"
USREC_LIMIT = 240  # ~20 years of monthly data, enough to shade recent charts


@dataclass(frozen=True)
class Indicator:
    id: str
    title: str
    short: str            # compact label for hub key-stats
    unit: str
    color: str
    series_id: str
    limit: int
    rule: Callable        # (cleaned_obs) -> (text, status)
    context: str          # evergreen "what it is" copy
    units_transform: Optional[str] = None
    value_format: str = "decimal"  # "decimal" (2dp) | "thousands" (whole, comma-separated)
    derive: Optional[Callable] = None  # optional post-fetch transform of raw observations
    source: str = "fred"  # "fred" (fetched via fred.py) | "stooq" (injected by refresh_markets)

    @property
    def fetch_key(self):
        return f"{self.series_id}:{self.units_transform or 'lin'}"


@dataclass(frozen=True)
class Lens:
    id: str
    title: str
    accent: str
    indicators: list = field(default_factory=list)


RECESSION_WATCH = Lens(
    id="recession-watch",
    title="Recession Watch",
    accent="#F87171",
    indicators=[
        Indicator(
            id="yield-curve",
            title="Yield Curve · 10-Year minus 2-Year",
            short="Yield curve",
            unit="%",
            color="#F87171",
            series_id="T10Y2Y",
            limit=2600,  # ~10y daily
            rule=narrative.rule_yield_curve,
            context=(
                "The gap between 10-year and 2-year Treasury yields. When it goes "
                "negative (“inverts”), investors expect rate cuts ahead — and "
                "every U.S. recession since the 1970s was preceded by an inversion."
            ),
        ),
        Indicator(
            id="sahm-rule",
            title="Sahm Rule Recession Indicator",
            short="Sahm rule",
            unit="",
            color="#FBBF24",
            series_id="SAHMREALTIME",
            limit=240,
            rule=narrative.rule_sahm,
            context=(
                "A real-time recession alarm built from unemployment: it trips when the "
                "3-month average jobless rate rises 0.5 points above its prior-year low. "
                "It has flagged every recession since 1970 with almost no false alarms."
            ),
        ),
        Indicator(
            id="jobless-claims",
            title="Initial Jobless Claims · weekly",
            short="Jobless claims",
            unit="",
            color="#34D399",
            series_id="ICSA",
            limit=520,  # ~10y weekly
            rule=narrative.rule_claims,
            value_format="thousands",
            context=(
                "How many people filed for unemployment benefits last week — the "
                "freshest read on layoffs. A sustained climb is one of the earliest "
                "signs of a weakening economy."
            ),
        ),
        Indicator(
            id="unemployment",
            title="Unemployment Rate",
            short="Unemployment",
            unit="%",
            color="#38BDF8",
            series_id="UNRATE",
            limit=240,
            rule=narrative.rule_unemployment_trend,
            context=(
                "The share of the labor force without a job and looking. A steady, "
                "sustained rise off its lows is a hallmark of an economy tipping into "
                "recession."
            ),
        ),
    ],
)

COST_OF_MONEY = Lens(
    id="cost-of-money",
    title="The Cost of Money",
    accent="#34D399",
    indicators=[
        Indicator(
            id="fed-funds",
            title="Federal Funds Rate",
            short="Fed funds",
            unit="%",
            color="#34D399",
            series_id="FEDFUNDS",
            limit=240,
            rule=narrative.rule_fed_funds,
            context=(
                "The interest rate the Federal Reserve sets to steer the economy — the "
                "anchor for nearly every other rate, from savings accounts to business loans."
            ),
        ),
        Indicator(
            id="treasury-10y",
            title="10-Year Treasury Yield",
            short="10-year",
            unit="%",
            color="#38BDF8",
            series_id="DGS10",
            limit=2600,
            rule=narrative.rule_rate_trend,
            context=(
                "The yield on 10-year U.S. government debt — the benchmark that drives "
                "mortgage rates and long-term borrowing costs across the economy."
            ),
        ),
        Indicator(
            id="treasury-2y",
            title="2-Year Treasury Yield",
            short="2-year",
            unit="%",
            color="#A78BFA",
            series_id="DGS2",
            limit=2600,
            rule=narrative.rule_rate_trend,
            context=(
                "The yield on 2-year government debt — closely tied to where investors "
                "expect the Fed to set rates over the next couple of years."
            ),
        ),
        Indicator(
            id="mortgage-30y",
            title="30-Year Fixed Mortgage Rate",
            short="30-yr mortgage",
            unit="%",
            color="#FBBF24",
            series_id="MORTGAGE30US",
            limit=520,
            rule=narrative.rule_mortgage,
            context=(
                "The average rate on a 30-year fixed home loan — the single biggest driver "
                "of housing affordability for most buyers."
            ),
        ),
    ],
)

JOB_MARKET = Lens(
    id="job-market",
    title="The Job Market",
    accent="#38BDF8",
    indicators=[
        Indicator(
            id="unemployment",
            title="Unemployment Rate",
            short="Unemployment",
            unit="%",
            color="#38BDF8",
            series_id="UNRATE",
            limit=240,
            rule=narrative.rule_unemployment_trend,
            context=(
                "The share of the labor force without a job and actively looking — the "
                "single most-watched gauge of labor-market health."
            ),
        ),
        Indicator(
            id="payrolls",
            title="Nonfarm Payrolls · monthly change",
            short="Payrolls",
            unit="",
            color="#34D399",
            series_id="PAYEMS",
            limit=240,
            rule=narrative.rule_payrolls,
            derive=derive.payroll_change,
            value_format="thousands",
            context=(
                "How many jobs U.S. employers added (or cut) last month — the headline "
                "number markets and the Fed react to most."
            ),
        ),
        Indicator(
            id="job-openings",
            title="Job Openings (JOLTS)",
            short="Openings",
            unit="M",
            color="#A78BFA",
            series_id="JTSJOL",
            limit=240,
            rule=narrative.rule_job_openings,
            derive=derive.to_millions,
            context=(
                "The number of unfilled positions employers are trying to hire for — a "
                "direct read on how strong labor demand is."
            ),
        ),
        Indicator(
            id="wage-growth",
            title="Wage Growth · year-over-year",
            short="Wages",
            unit="%",
            color="#FBBF24",
            series_id="CES0500000003",
            units_transform="pc1",
            limit=240,
            rule=narrative.rule_wage_growth,
            context=(
                "How fast average hourly pay is rising versus a year ago. When it outpaces "
                "inflation, workers' buying power grows."
            ),
        ),
        Indicator(
            id="participation",
            title="Labor-Force Participation Rate",
            short="Participation",
            unit="%",
            color="#22D3EE",
            series_id="CIVPART",
            limit=240,
            rule=narrative.rule_rate_trend,
            context=(
                "The share of working-age adults either working or looking for work — how "
                "many people are in the labor force at all."
            ),
        ),
    ],
)

COST_OF_LIVING = Lens(
    id="cost-of-living",
    title="The Cost of Living",
    accent="#FBBF24",
    indicators=[
        Indicator(
            id="cpi",
            title="Inflation · CPI (year-over-year)",
            short="CPI",
            unit="%",
            color="#FBBF24",
            series_id="CPIAUCSL",
            units_transform="pc1",
            limit=240,
            rule=narrative.rule_inflation,
            context=(
                "The Consumer Price Index — the headline measure of how fast the prices "
                "households actually pay are rising versus a year ago."
            ),
        ),
        Indicator(
            id="core-cpi",
            title="Core CPI (year-over-year)",
            short="Core CPI",
            unit="%",
            color="#FB923C",
            series_id="CPILFESL",
            units_transform="pc1",
            limit=240,
            rule=narrative.rule_inflation,
            context=(
                "CPI excluding volatile food and energy. Because it strips out the noisiest "
                "prices, it's a better read on the economy's underlying inflation trend."
            ),
        ),
        Indicator(
            id="pce",
            title="PCE Inflation (year-over-year)",
            short="PCE",
            unit="%",
            color="#38BDF8",
            series_id="PCEPI",
            units_transform="pc1",
            limit=240,
            rule=narrative.rule_inflation,
            context=(
                "The Personal Consumption Expenditures price index — the inflation gauge "
                "the Federal Reserve watches most closely when setting interest rates."
            ),
        ),
        Indicator(
            id="real-wages",
            title="Real Wage Growth (year-over-year)",
            short="Real wages",
            unit="%",
            color="#34D399",
            series_id="LES1252881600Q",
            units_transform="pc1",
            limit=240,
            rule=narrative.rule_real_wages,
            context=(
                "The typical worker's weekly paycheck adjusted for inflation (real median "
                "earnings). When it rises, pay is outpacing prices; when it falls, the opposite."
            ),
        ),
    ],
)

LENSES = [RECESSION_WATCH, COST_OF_MONEY, JOB_MARKET, COST_OF_LIVING]


# ---------------------------------------------------------------------------
# Banking System Health (category #2) — sourced from the FDIC BankFind /financials
# endpoint (per-bank, quarterly). Design decisions verified live 2026-06-07:
#   * National series = quarterly aggregation across all banks (one fetch/quarter).
#     Charts, tiers, and spotlights all come from the SAME endpoint, so figures are
#     consistent and match the FDIC Quarterly Banking Profile.
#   * Prefer FDIC's per-bank RATIO fields (NCLNLSR, NTLNLSR, ROA, NIMY, LNLSDEPR,
#     RBCRWAJ) which are already annualized where relevant — loan/asset-weighted,
#     this gives the correct national rate with no YTD de-cumulation.
#   * Use sum-then-ratio only for reliable dollar fields (EQ/ASSET, DEPUNINS/DEP,
#     CRE/EQ). (NALTOT is null in /financials — never use it.)
# Each metric is a dict in one of two shapes, shared by indicators and tiers:
#   {"ratio_field": F, "weight_field": W}            -> weighted average of a ratio
#   {"numerator": [...], "denominator": [...], "scale": S}  -> sum-then-ratio
# ---------------------------------------------------------------------------

TIERS = [
    ("Community (<$10B)", 0, 10_000_000),
    ("Regional ($10B–$250B)", 10_000_000, 250_000_000),
    ("Large (>$250B)", 250_000_000, None),
]


@dataclass(frozen=True)
class BankingIndicator:
    id: str
    title: str
    short: str
    unit: str
    color: str
    metric: dict          # {"ratio_field","weight_field"} or {"numerator","denominator","scale"}
    rule: Callable
    context: str
    value_format: str = "decimal"
    source: str = "fdic"


@dataclass(frozen=True)
class BankingLens:
    id: str
    title: str
    accent: str
    indicators: list = field(default_factory=list)
    tier_metrics: list = field(default_factory=list)
    rankings: list = field(default_factory=list)


BANK_ASSET_QUALITY = BankingLens(
    id="bank-asset-quality",
    title="Asset Quality",
    accent="#FBBF24",
    indicators=[
        BankingIndicator(
            id="noncurrent", title="Noncurrent Loan Rate · loans 90+ days past due",
            short="Noncurrent", unit="%", color="#FBBF24",
            metric={"ratio_field": "NCLNLSR", "weight_field": "LNLSNET"},
            rule=narrative.rule_noncurrent,
            context=("The share of all bank loans that are 90+ days late or no longer "
                     "accruing interest — the broadest gauge of credit going bad."),
        ),
        BankingIndicator(
            id="charge-offs", title="Net Charge-Off Rate · annualized", short="Charge-offs",
            unit="%", color="#FB923C",
            metric={"ratio_field": "NTLNLSR", "weight_field": "LNLSNET"},
            rule=narrative.rule_charge_offs,
            context=("Loans banks have given up on and written off as losses, as a share "
                     "of total loans — money that's gone, not just late."),
        ),
    ],
    tier_metrics=[
        {"key": "noncurrent", "label": "Noncurrent", "ratio_field": "NCLNLSR",
         "weight_field": "LNLSNET", "rule": narrative.rule_noncurrent},
        {"key": "charge-offs", "label": "Charge-offs", "ratio_field": "NTLNLSR",
         "weight_field": "LNLSNET", "rule": narrative.rule_charge_offs},
    ],
    rankings=[
        {"title": "Highest commercial-real-estate delinquency",
         "subtitle": "banks over $1B in assets with a material CRE book", "metric_field": "NCRER",
         "asset_min": 1_000_000, "limit": 10, "value_label": "CRE delinq.",
         "unit": "%", "rule": narrative.rule_noncurrent,
         # Materiality: require >= $250M of CRE loans so tiny books can't post an
         # exploded ratio; cap at 20% as a backstop against idiosyncratic distress.
         "min_base_fields": ["LNRENRES", "LNREMULT"], "min_base": 250_000, "max_value": 20.0},
    ],
)

BANK_PROFITABILITY = BankingLens(
    id="bank-profitability",
    title="Profitability",
    accent="#34D399",
    indicators=[
        BankingIndicator(
            id="net-margin", title="Net Interest Margin · annualized", short="Margin",
            unit="%", color="#34D399",
            metric={"ratio_field": "NIMY", "weight_field": "ASSET"},
            rule=narrative.rule_net_margin,
            context=("The spread banks earn between what they make on loans and pay on "
                     "deposits, relative to assets — the core engine of bank earnings."),
        ),
        BankingIndicator(
            id="roa", title="Return on Assets · annualized", short="ROA",
            unit="%", color="#38BDF8",
            metric={"ratio_field": "ROA", "weight_field": "ASSET"},
            rule=narrative.rule_roa,
            context=("Industry profit measured against total assets — the standard "
                     "yardstick for how efficiently banks turn assets into earnings."),
        ),
    ],
    tier_metrics=[
        {"key": "roa", "label": "Return on assets", "ratio_field": "ROA",
         "weight_field": "ASSET", "rule": narrative.rule_roa},
    ],
    rankings=[
        {"title": "Strongest profitability · highest return on assets",
         "subtitle": "mainstream lenders over $1B in assets", "metric_field": "ROA",
         "asset_min": 1_000_000, "limit": 10, "value_label": "ROA",
         "unit": "%", "rule": narrative.rule_roa,
         # Highest-is-best; cap at 3% ROA to exclude specialty outfits whose structurally
         # huge ROA isn't a "best-run bank" signal. Plus two business-mix relevance gates
         # so the list reads as mainstream lenders, not niche charters (see
         # design-spotlight-mainstream-relevance): require a real loan book (loans >= 40%
         # of assets — drops trust/custody/HSA banks) and that it isn't a credit-card
         # monoline (credit cards <= 50% of loans — drops Synchrony-type issuers).
         "sort_order": "DESC", "max_value": 3.0,
         "ratio_filters": [
             {"num": ["LNLSNET"], "den": ["ASSET"], "min": 0.40},
             {"num": ["LNCRCD"], "den": ["LNLSNET"], "max": 0.50},
         ]},
    ],
)

BANK_CAPITAL = BankingLens(
    id="bank-capital-solvency",
    title="Capital & Solvency",
    accent="#38BDF8",
    indicators=[
        BankingIndicator(
            id="risk-based-capital", title="Total Risk-Based Capital Ratio", short="Risk-based capital",
            unit="%", color="#38BDF8",
            metric={"ratio_field": "RBCRWAJ", "weight_field": "ASSET"},
            rule=narrative.rule_risk_based_capital,
            context=("Capital measured against risk-weighted assets — the regulators' "
                     "headline solvency gauge. Banks are 'well-capitalized' above 10%."),
        ),
        BankingIndicator(
            id="equity-assets", title="Equity-to-Assets", short="Equity/assets",
            unit="%", color="#34D399",
            metric={"numerator": ["EQ"], "denominator": ["ASSET"], "scale": 100.0},
            rule=narrative.rule_capital_ratio,
            context=("Shareholder equity as a share of total assets — a simpler, "
                     "unweighted view of the cushion between losses and insolvency."),
        ),
    ],
    tier_metrics=[
        {"key": "risk-based", "label": "Risk-based cap.", "ratio_field": "RBCRWAJ",
         "weight_field": "ASSET", "rule": narrative.rule_risk_based_capital},
        {"key": "equity", "label": "Equity/assets", "numerator": ["EQ"],
         "denominator": ["ASSET"], "scale": 100.0, "rule": narrative.rule_capital_ratio},
    ],
    rankings=[
        # Spotlight uses equity-to-assets (EQV), not RBCRWAJ: smaller banks on the
        # Community Bank Leverage Ratio framework report RBCRWAJ as 0, which poisons a
        # lowest-RBC ranking. EQV is populated for every bank.
        {"title": "Thinnest capital cushion · equity-to-assets",
         "subtitle": "banks over $1B in assets", "metric_field": "EQV",
         "asset_min": 1_000_000, "limit": 10, "value_label": "Equity/assets",
         "unit": "%", "rule": narrative.rule_capital_ratio,
         "sort_order": "ASC", "min_value": 3.0},
    ],
)

BANK_CONCENTRATIONS = BankingLens(
    id="bank-concentrations-funding",
    title="Concentrations & Funding",
    accent="#A78BFA",
    indicators=[
        BankingIndicator(
            id="uninsured", title="Uninsured-Deposit Share", short="Uninsured dep.",
            unit="%", color="#FBBF24",
            metric={"numerator": ["DEPUNINS"], "denominator": ["DEP"], "scale": 100.0},
            rule=narrative.rule_uninsured_share,
            context=("The share of deposits above the $250k FDIC insurance cap — the "
                     "money most likely to flee in a panic, as it did at Silicon Valley Bank."),
        ),
        BankingIndicator(
            id="loans-deposits", title="Loans-to-Deposits", short="Loans/dep.",
            unit="%", color="#34D399",
            metric={"ratio_field": "LNLSDEPR", "weight_field": "DEP"},
            rule=narrative.rule_loans_deposits,
            context=("How much of deposits banks have lent out — a gauge of how "
                     "stretched the system's funding is."),
        ),
        BankingIndicator(
            id="cre-concentration", title="CRE Concentration · % of capital",
            short="CRE/capital", unit="%", color="#FB923C",
            metric={"numerator": ["LNRENRES", "LNREMULT"], "denominator": ["EQ"], "scale": 100.0},
            rule=narrative.rule_cre_concentration,
            context=("Commercial real-estate loans measured against capital. Above "
                     "~300% is the level bank supervisors flag as a concentration risk."),
        ),
    ],
    tier_metrics=[
        {"key": "uninsured", "label": "Uninsured dep.", "numerator": ["DEPUNINS"],
         "denominator": ["DEP"], "scale": 100.0, "rule": narrative.rule_uninsured_share},
        {"key": "loans-dep", "label": "Loans/dep.", "ratio_field": "LNLSDEPR",
         "weight_field": "DEP", "rule": narrative.rule_loans_deposits},
    ],
    rankings=[
        {"title": "Most stretched funding · loans-to-deposits",
         "subtitle": "banks over $1B in assets", "metric_field": "LNLSDEPR",
         "asset_min": 1_000_000, "limit": 10, "value_label": "Loans/dep.",
         "unit": "%", "rule": narrative.rule_loans_deposits,
         # Cap at 150%: above that is typically a non-deposit-funded niche/industrial
         # bank, not "stretched funding" in the systemic sense this lens is about.
         "max_value": 150.0},
    ],
)

BANKING_LENSES = [BANK_ASSET_QUALITY, BANK_PROFITABILITY, BANK_CAPITAL, BANK_CONCENTRATIONS]

CATEGORIES = [
    {"id": "economic", "title": "Economic Lenses", "lenses": LENSES, "out": "lenses",
     "back": "Economic Lenses",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed",
     "disclaimer": ""},
    {"id": "banking", "title": "Banking System Health", "lenses": BANKING_LENSES,
     "out": "banking", "back": "Banking System Health",
     "source_label": "FDIC, quarterly bank Call Reports",
     "disclaimer": ("Public regulatory data. Not investment advice and not a judgment "
                    "of any institution's solvency.")},
]


# ---------------------------------------------------------------------------
# Markets & Financial Conditions (category #3). Two FRED-sourced lenses reuse the
# economic Indicator/Lens pipeline unchanged; a third CoinGecko-sourced lens
# (crypto-structure) is built separately by refresh_lenses + build.build_crypto_lens.
# Rates are deliberately absent from the scoreboard — Cost of Money owns them.
# ---------------------------------------------------------------------------

MARKET_RISK_SENTIMENT = Lens(
    id="market-risk-sentiment",
    title="Risk Sentiment",
    accent="#FB7185",
    indicators=[
        Indicator(
            id="vix", title="Volatility · VIX", short="VIX", unit="", color="#FB7185",
            series_id="VIXCLS", limit=2600, rule=narrative.rule_vix,
            context=("The market's 'fear gauge' — the expected volatility of the S&P 500 "
                     "over the coming month. It spikes when investors are scared and falls when calm."),
        ),
        Indicator(
            id="hy-spread", title="High-Yield Credit Spread", short="HY spread", unit="%",
            color="#FB923C", series_id="BAMLH0A0HYM2", limit=2600,
            rule=narrative.credit_spread("high-yield", 4.0, 6.0),
            context=("The extra yield investors demand to hold risky 'junk' corporate bonds over "
                     "Treasuries. It widens when markets fear defaults — an early stress signal."),
        ),
        Indicator(
            id="ig-spread", title="Investment-Grade Credit Spread", short="IG spread", unit="%",
            color="#FBBF24", series_id="BAMLC0A0CM", limit=2600,
            rule=narrative.credit_spread("investment-grade", 1.5, 2.5),
            context=("The same risk premium for higher-quality corporate bonds. Because these "
                     "borrowers are safer, widening here signals stress reaching the core of credit."),
        ),
        Indicator(
            id="nfci", title="Financial Conditions · NFCI", short="NFCI", unit="", color="#38BDF8",
            series_id="NFCI", limit=520, rule=narrative.rule_financial_conditions,
            context=("The Chicago Fed's broad gauge of financial conditions across money, debt, and "
                     "equity markets. Zero is average; positive means tighter (more stressed) than normal."),
        ),
    ],
)

MARKET_SCOREBOARD = Lens(
    id="market-scoreboard",
    title="Asset-Class Scoreboard",
    accent="#22D3EE",
    indicators=[
        Indicator(
            id="sp500", title="S&P 500", short="S&P 500", unit="", color="#34D399",
            series_id="SP500", limit=2600, rule=narrative.market_level("The S&P 500", up=5, down=-5),
            value_format="thousands",
            context="The benchmark index of 500 large U.S. companies — the headline gauge of U.S. stocks.",
        ),
        Indicator(
            id="oil", title="Crude Oil · WTI", short="WTI oil", unit="", color="#FB923C",
            series_id="DCOILWTICO", limit=2600, rule=narrative.market_level("WTI crude", up=15, down=-15),
            context=("West Texas Intermediate, the U.S. benchmark oil price (dollars per barrel) — "
                     "a read on energy costs and global demand."),
        ),
        Indicator(
            id="gold", title="Gold", short="Gold", unit="", color="#FBBF24",
            series_id="XAUUSD", limit=2600, rule=narrative.market_level("Gold", up=10, down=-10),
            value_format="thousands", source="yahoo",
            context=("Gold (dollars per troy ounce) — the classic safe-haven asset investors "
                     "flee to in times of stress. Sourced from Yahoo Finance (COMEX futures)."),
        ),
        Indicator(
            id="dollar", title="U.S. Dollar · Broad Index", short="Dollar", unit="", color="#38BDF8",
            series_id="DTWEXBGS", limit=2600, rule=narrative.market_level("The dollar index", up=3, down=-3),
            context=("The trade-weighted value of the U.S. dollar against a broad basket of "
                     "currencies — a strong dollar makes imports cheaper and U.S. exports pricier."),
        ),
        Indicator(
            id="btc", title="Bitcoin", short="Bitcoin", unit="", color="#A78BFA",
            series_id="CBBTCUSD", limit=2600, rule=narrative.market_level("Bitcoin", up=25, down=-25),
            value_format="thousands",
            context=("The price of Bitcoin in U.S. dollars (Coinbase) — the largest cryptocurrency "
                     "and a barometer of risk appetite in digital assets."),
        ),
        Indicator(
            id="eth", title="Ethereum", short="Ethereum", unit="", color="#818CF8",
            series_id="CBETHUSD", limit=2600, rule=narrative.market_level("Ethereum", up=25, down=-25),
            value_format="thousands",
            context=("The price of Ether in U.S. dollars (Coinbase) — the second-largest "
                     "cryptocurrency and the backbone of most decentralized applications."),
        ),
    ],
)

MARKET_FRED_LENSES = [MARKET_RISK_SENTIMENT, MARKET_SCOREBOARD]

CATEGORIES.append(
    {"id": "markets", "title": "Markets & Financial Conditions", "lenses": MARKET_FRED_LENSES,
     "out": "markets", "back": "Markets & Financial Conditions",
     "source_label": "FRED (St. Louis Fed) and CoinGecko", "disclaimer": ""}
)

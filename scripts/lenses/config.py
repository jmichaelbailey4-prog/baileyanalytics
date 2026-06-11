"""Lens configuration — the single source of truth for what gets built."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import derive, imf, narrative

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
    source: str = "fred"  # "fred" | "yahoo" | "eia" | "computed" (non-FRED sources are injected by refresh_*)
    eia_route: str = ""             # EIA v2 route, e.g. "petroleum/pri/gnd" (empty = computed/injected)
    eia_facets: tuple = ()          # ((key, value), ...) -> facets[key][]=value
    eia_freq: str = ""              # "daily" | "weekly" | "monthly"
    eia_col: str = "value"          # data column to request/read
    imf_key: str = ""               # IMF WEO "COUNTRY.INDICATOR" (source == "imf" only)

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

FISCAL_HEALTH = Lens(
    id="fiscal-health",
    title="Fiscal Health",
    accent="#A78BFA",
    indicators=[
        Indicator(
            id="debt-gdp",
            title="Federal Debt · % of GDP",
            short="Debt/GDP",
            unit="%",
            color="#A78BFA",
            series_id="GFDEGDQ188S",
            limit=80,  # ~20y quarterly
            rule=narrative.rule_debt_gdp,
            context=(
                "Total federal debt measured against the size of the economy — the "
                "single most-cited gauge of fiscal sustainability. It crossed 100% "
                "around 2013 and has kept climbing."
            ),
        ),
        Indicator(
            id="deficit-12m",
            title="Federal Deficit · trailing 12 months",
            short="Deficit",
            unit="$T",
            color="#F87171",
            series_id="MTSDS133FMS",
            limit=252,  # ~21y monthly; the derive consumes 12 months per point
            rule=narrative.rule_deficit_12m,
            derive=derive.trailing_12m_deficit,
            context=(
                "How much the government borrowed over the past 12 months, from the "
                "monthly Treasury statement. The rolling year smooths out tax season "
                "— this is the number the 'deficit debate' is actually about."
            ),
        ),
        Indicator(
            id="interest-cost",
            title="Federal Interest Cost · annual rate",
            short="Interest cost",
            unit="$B",
            color="#FBBF24",
            series_id="A091RC1Q027SBEA",
            limit=80,
            value_format="thousands",
            rule=narrative.energy_level("The government's interest bill", fmt="${:,.0f} billion"),
            context=(
                "What the government pays per year to service its debt (quarterly, "
                "annualized). Rising rates turned this into one of the largest items "
                "in the federal budget — crowding out everything else."
            ),
        ),
        Indicator(
            id="receipts",
            title="Federal Receipts · year-over-year",
            short="Receipts",
            unit="%",
            color="#34D399",
            series_id="W006RC1Q027SBEA",
            limit=100,
            derive=derive.yoy_pct,
            rule=narrative.yoy_info("The federal tax take"),
            context=(
                "How fast federal tax revenue is growing versus a year ago. Healthy "
                "receipts growth shrinks the deficit without any policy change; "
                "shrinking receipts usually mean a weakening economy."
            ),
        ),
    ],
)

LENSES = [RECESSION_WATCH, COST_OF_MONEY, JOB_MARKET, COST_OF_LIVING, FISCAL_HEALTH]


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
            color="#FB923C", series_id="BAMLH0A0HYM2",
            limit=900,  # ICE BofA: FRED API only serves a rolling ~3y window
            rule=narrative.credit_spread("high-yield", 4.0, 6.0),
            context=("The extra yield investors demand to hold risky 'junk' corporate bonds over "
                     "Treasuries. It widens when markets fear defaults — an early stress signal. "
                     "Note: FRED serves only a rolling ~3-year window of this ICE BofA series, so "
                     "its chart history is shorter than the other indicators here."),
        ),
        Indicator(
            id="ig-spread", title="Investment-Grade Credit Spread", short="IG spread", unit="%",
            color="#FBBF24", series_id="BAMLC0A0CM",
            limit=900,  # ICE BofA: FRED API only serves a rolling ~3y window
            rule=narrative.credit_spread("investment-grade", 1.5, 2.5),
            context=("The same risk premium for higher-quality corporate bonds. Because these "
                     "borrowers are safer, widening here signals stress reaching the core of credit. "
                     "Note: FRED serves only a rolling ~3-year window of this ICE BofA series, so "
                     "its chart history is shorter than the other indicators here."),
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
            id="oil", title="Crude Oil · WTI", short="WTI oil", unit="$", color="#FB923C",
            series_id="DCOILWTICO", limit=2600, rule=narrative.market_level("WTI crude", up=15, down=-15),
            context=("West Texas Intermediate, the U.S. benchmark oil price (dollars per barrel) — "
                     "a read on energy costs and global demand."),
        ),
        Indicator(
            id="gold", title="Gold", short="Gold", unit="$", color="#FBBF24",
            series_id="XAUUSD", limit=2600, rule=narrative.market_level("Gold", up=10, down=-10),
            value_format="thousands", source="yahoo",
            context=("Gold (dollars per troy ounce) — the classic safe-haven asset investors "
                     "flee to in times of stress. Sourced from Yahoo Finance (COMEX futures)."),
        ),
        Indicator(
            id="btc", title="Bitcoin", short="Bitcoin", unit="$", color="#A78BFA",
            series_id="CBBTCUSD", limit=2600, rule=narrative.market_level("Bitcoin", up=25, down=-25),
            value_format="thousands",
            context=("The price of Bitcoin in U.S. dollars (Coinbase) — the largest cryptocurrency "
                     "and a barometer of risk appetite in digital assets."),
        ),
        Indicator(
            id="eth", title="Ethereum", short="Ethereum", unit="$", color="#818CF8",
            series_id="CBETHUSD", limit=2600, rule=narrative.market_level("Ethereum", up=25, down=-25),
            value_format="thousands",
            context=("The price of Ether in U.S. dollars (Coinbase) — the second-largest "
                     "cryptocurrency and the backbone of most decentralized applications."),
        ),
    ],
)

MARKET_LIQUIDITY = Lens(
    id="market-liquidity",
    title="Liquidity & the Fed",
    accent="#2DD4BF",
    indicators=[
        Indicator(
            id="m2-growth", title="M2 Money Supply · year-over-year", short="M2 growth",
            unit="%", color="#2DD4BF", series_id="M2SL", units_transform="pc1", limit=300,
            rule=narrative.rule_m2_growth,
            context=("How fast the broad money supply is growing versus a year ago. Double-digit "
                     "growth (2020-21) preceded the inflation surge; the 2022-23 contraction was "
                     "the first since the Great Depression."),
        ),
        Indicator(
            id="fed-balance-sheet", title="Fed Balance Sheet · total assets", short="Fed assets",
            unit="$T", color="#38BDF8", series_id="WALCL", limit=520,
            derive=derive.scaled(1_000_000, 2),
            rule=narrative.energy_level("The Fed's balance sheet", fmt="${:,.2f} trillion"),
            context=("Everything the Federal Reserve holds, in trillions. Rising means the Fed is "
                     "injecting liquidity (QE); falling means it's draining (QT) — the tide that "
                     "lifts or lowers all markets."),
        ),
        Indicator(
            id="bank-reserves", title="Bank Reserves at the Fed", short="Reserves",
            unit="$T", color="#34D399", series_id="WRESBAL", limit=520,
            derive=derive.scaled(1_000_000, 2),
            rule=narrative.energy_level("The level of bank reserves", fmt="${:,.2f} trillion"),
            context=("Cash banks park at the Fed — the system's core liquidity buffer. When QT "
                     "drains reserves too low, funding markets seize up (as in September 2019)."),
        ),
        Indicator(
            id="reverse-repo", title="Overnight Reverse Repo", short="Reverse repo",
            unit="$B", color="#A78BFA", series_id="RRPONTSYD", limit=1300,
            rule=narrative.energy_level("The overnight reverse-repo facility", fmt="${:,.1f} billion"),
            context=("Spare cash money-market funds park at the Fed overnight. It acts as the "
                     "system's overflow tank: a high balance means excess liquidity; near zero "
                     "means the buffer is spent and QT bites reserves directly."),
        ),
    ],
)

MARKET_FRED_LENSES = [MARKET_RISK_SENTIMENT, MARKET_SCOREBOARD, MARKET_LIQUIDITY]

CATEGORIES.append(
    {"id": "markets", "title": "Markets & Financial Conditions", "lenses": MARKET_FRED_LENSES,
     "out": "markets", "back": "Markets & Financial Conditions",
     "source_label": "FRED (St. Louis Fed) and CoinGecko", "disclaimer": ""}
)


# --- The Consumer (FRED) ---
# Household spending is ~68% of GDP; this category answers the question the
# price-pressure categories raise: are households cracking or absorbing it?

CONSUMER_SPENDING = Lens(
    id="consumer-spending", title="Spending", accent="#34D399",
    indicators=[
        Indicator(
            id="retail-sales", title="Retail Sales · year-over-year", short="Retail sales",
            unit="%", color="#34D399", series_id="RSAFS", units_transform="pc1", limit=240,
            rule=narrative.yoy_band_two_sided("Retail sales", hot=(8, 15, 25), cold=(-1, -4, -8)),
            context=("How fast retail and food-service sales are growing versus a year ago "
                     "(nominal — inflation is part of the number). A stall here is how consumer "
                     "recessions announce themselves."),
        ),
        Indicator(
            id="real-spending", title="Real Consumer Spending · year-over-year", short="Real spending",
            unit="%", color="#38BDF8", series_id="PCEC96", units_transform="pc1", limit=240,
            rule=narrative.yoy_band_two_sided("Real consumer spending", hot=(4, 6, 9),
                                              cold=(-0.5, -2, -4), verb="is"),
            context=("Total household consumption adjusted for inflation — the cleanest read on "
                     "whether people are actually buying more, or just paying more."),
        ),
        Indicator(
            id="auto-sales", title="Vehicle Sales · annual rate", short="Auto sales",
            unit="M", color="#FBBF24", series_id="TOTALSA", limit=240,
            rule=narrative.energy_level("The pace of vehicle sales", fmt="{:,.1f} million"),
            context=("Light-vehicle sales in millions at an annual rate — the classic big-ticket "
                     "purchase. Households delay new cars first when budgets tighten."),
        ),
    ],
)

CONSUMER_CREDIT = Lens(
    id="consumer-credit", title="Credit Stress", accent="#F87171",
    indicators=[
        Indicator(
            id="card-delinquency", title="Credit-Card Delinquency Rate", short="Card delinq.",
            unit="%", color="#F87171", series_id="DRCCLACBS", limit=80,
            rule=narrative.consumer_delinquency("Credit-card", 2.5, 4, 6),
            context=("The share of bank credit-card balances 30+ days past due (quarterly). "
                     "Cards go bad first — this is the earliest warning in consumer credit. "
                     "The 2009 peak was about 6.8%."),
        ),
        Indicator(
            id="consumer-delinquency", title="Consumer-Loan Delinquency Rate", short="Loan delinq.",
            unit="%", color="#FB923C", series_id="DRCLACBS", limit=80,
            rule=narrative.consumer_delinquency("Consumer-loan", 2.5, 3.5, 4.5),
            context=("Delinquency across all consumer loans at banks — cards, autos, and "
                     "personal loans together (quarterly)."),
        ),
        Indicator(
            id="revolving-credit", title="Card Balances · year-over-year", short="Card balances",
            unit="%", color="#A78BFA", series_id="REVOLSL", units_transform="pc1", limit=240,
            rule=narrative.rule_revolving_credit,
            context=("How fast revolving credit (mostly credit cards) is growing. Balances "
                     "growing much faster than incomes mean households are borrowing to keep up."),
        ),
        Indicator(
            id="debt-service", title="Household Debt Service · % of income", short="Debt service",
            unit="%", color="#FBBF24", series_id="TDSP", limit=80,
            rule=narrative.rule_debt_service,
            context=("All required debt payments — mortgage and consumer — as a share of "
                     "disposable income (quarterly). The 2007 peak was about 13%."),
        ),
    ],
)

CONSUMER_INCOME = Lens(
    id="consumer-income-savings", title="Income & Savings", accent="#FBBF24",
    indicators=[
        Indicator(
            id="saving-rate", title="Personal Saving Rate", short="Saving rate",
            unit="%", color="#FBBF24", series_id="PSAVERT", limit=240,
            rule=narrative.rule_saving_rate,
            context=("The share of after-tax income households save each month. A thin saving "
                     "rate means no shock absorber — the historical norm is 5-8%."),
        ),
        Indicator(
            id="real-income", title="Real Disposable Income · year-over-year", short="Real income",
            unit="%", color="#34D399", series_id="DSPIC96", units_transform="pc1", limit=240,
            rule=narrative.rule_real_income,
            context=("After-tax household income adjusted for inflation. When it falls, spending "
                     "can only be sustained by savings or debt — and both run out."),
        ),
        Indicator(
            id="net-worth", title="Household Net Worth · year-over-year", short="Net worth",
            unit="%", color="#38BDF8", series_id="BOGZ1FL192090005Q", units_transform="pc1", limit=80,
            rule=narrative.yoy_info("Household net worth"),
            context=("Everything households own minus everything they owe (quarterly). Driven by "
                     "home prices and markets — the wealth effect behind spending confidence."),
        ),
    ],
)

CONSUMER_SENTIMENT = Lens(
    id="consumer-sentiment", title="Sentiment & Expectations", accent="#38BDF8",
    indicators=[
        Indicator(
            id="sentiment", title="Consumer Sentiment (U. Michigan)", short="Sentiment",
            unit="", color="#38BDF8", series_id="UMCSENT", limit=240,
            rule=narrative.rule_sentiment,
            context=("The University of Michigan's monthly survey of how households feel about "
                     "their finances and the economy. Long-run range roughly 50-110; the 2022 "
                     "record low was about 50."),
        ),
        Indicator(
            id="inflation-expectations", title="Inflation Expectations · 1-year ahead", short="Inflation exp.",
            unit="%", color="#FBBF24", series_id="MICH", limit=240,
            rule=narrative.rule_inflation_expectations,
            context=("What households expect inflation to be over the next year, from the same "
                     "Michigan survey. The Fed watches this closely: once expectations de-anchor, "
                     "inflation feeds on itself."),
        ),
    ],
)

CONSUMER_LENSES = [CONSUMER_SPENDING, CONSUMER_CREDIT, CONSUMER_INCOME, CONSUMER_SENTIMENT]

CATEGORIES.append(
    {"id": "consumer", "title": "The Consumer", "lenses": CONSUMER_LENSES,
     "out": "consumer", "back": "The Consumer",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed", "disclaimer": ""}
)


# --- Energy & Commodities (EIA + FRED) ---

ENERGY_OIL_FUELS = Lens(
    id="energy-oil-fuels", title="Oil & Fuels", accent="#FB923C",
    indicators=[
        Indicator(
            id="gasoline", title="Retail Gasoline · Regular", short="Gasoline", unit="$",
            color="#FB923C", series_id="EMM_EPMR_PTE_NUS_DPG", limit=520,
            rule=narrative.consumer_cost("Gasoline", 10, 25, 40), value_format="decimal",
            source="eia", eia_route="petroleum/pri/gnd",
            eia_facets=(("series", "EMM_EPMR_PTE_NUS_DPG"),), eia_freq="weekly",
            context=("The U.S. average retail price for a gallon of regular gasoline — the "
                     "energy cost households feel most directly."),
        ),
        Indicator(
            id="diesel", title="Retail Diesel · On-Highway", short="Diesel", unit="$",
            color="#FBBF24", series_id="EMD_EPD2D_PTE_NUS_DPG", limit=520,
            rule=narrative.consumer_cost("Diesel", 10, 25, 40), value_format="decimal",
            source="eia", eia_route="petroleum/pri/gnd",
            eia_facets=(("series", "EMD_EPD2D_PTE_NUS_DPG"),), eia_freq="weekly",
            context=("The U.S. average on-highway diesel price — the fuel that moves freight, "
                     "so it feeds into the price of nearly everything."),
        ),
        Indicator(
            id="crude-production", title="U.S. Crude Oil Production", short="Crude output", unit="",
            color="#34D399", series_id="WCRFPUS2", limit=520,
            rule=narrative.energy_level("U.S. crude production"), value_format="thousands",
            source="eia", eia_route="petroleum/sum/sndw",
            eia_facets=(("series", "WCRFPUS2"),), eia_freq="weekly",
            context=("U.S. field production of crude oil (thousand barrels per day) — the supply "
                     "side that, with demand, sets the price of oil."),
        ),
        Indicator(
            id="crude-stocks", title="Crude Inventories · excl. SPR", short="Crude stocks", unit="",
            color="#38BDF8", series_id="WCESTUS1", limit=520,
            rule=narrative.energy_level("Crude inventories"), value_format="thousands",
            source="eia", eia_route="petroleum/stoc/wstk",
            eia_facets=(("series", "WCESTUS1"),), eia_freq="weekly",
            context=("Commercial crude oil inventories (thousand barrels, excluding the Strategic "
                     "Petroleum Reserve) — low stocks point to upward price pressure."),
        ),
    ],
)

ENERGY_NATURAL_GAS = Lens(
    id="energy-natural-gas", title="Natural Gas", accent="#60A5FA",
    indicators=[
        Indicator(
            id="henry-hub", title="Henry Hub Spot Price", short="Henry Hub", unit="$",
            color="#60A5FA", series_id="RNGWHHD", limit=900,
            rule=narrative.consumer_cost("Natural gas", 20, 50, 100), value_format="decimal",
            source="eia", eia_route="natural-gas/pri/fut",
            eia_facets=(("series", "RNGWHHD"),), eia_freq="daily",
            context=("The U.S. benchmark natural-gas price ($/MMBtu) — it drives home heating "
                     "bills and a large share of electricity generation cost."),
        ),
        Indicator(
            id="gas-storage", title="Working Gas in Storage · Lower 48", short="Gas storage", unit="Bcf",
            color="#38BDF8", series_id="NW2_EPG0_SWO_R48_BCF", limit=520,
            rule=narrative.energy_level("Gas in storage"), value_format="thousands",
            source="eia", eia_route="natural-gas/stor/wkly",
            eia_facets=(("series", "NW2_EPG0_SWO_R48_BCF"),), eia_freq="weekly",
            context=("Working natural gas held in underground storage (Bcf) — the cushion that "
                     "buffers winter demand; low storage means price risk."),
        ),
        Indicator(
            id="gas-production", title="U.S. Dry Gas Production", short="Gas output", unit="",
            color="#34D399", series_id="N9070US2", limit=240,
            rule=narrative.energy_level("Dry gas production"), value_format="thousands",
            source="eia", eia_route="natural-gas/prod/sum",
            eia_facets=(("series", "N9070US2"),), eia_freq="monthly",
            context=("U.S. dry natural-gas production — record output has reshaped both home "
                     "energy costs and the country's role as an exporter."),
        ),
        Indicator(
            id="lng-exports", title="U.S. LNG Exports", short="LNG exports", unit="",
            color="#A78BFA", series_id="N9133US2", limit=240,
            rule=narrative.energy_level("LNG exports"), value_format="thousands",
            source="eia", eia_route="natural-gas/move/expc",
            eia_facets=(("series", "N9133US2"),), eia_freq="monthly",
            context=("U.S. liquefied natural gas exports — a fast-growing link between domestic "
                     "gas prices and global demand."),
        ),
    ],
)

ENERGY_ELECTRICITY = Lens(
    id="energy-electricity", title="Electricity & the Grid", accent="#FBBF24",
    indicators=[
        Indicator(
            id="electricity-price", title="Retail Electricity · Residential", short="Power price", unit="¢/kWh",
            color="#FBBF24", series_id="ELEC_PRICE_RES_US", limit=240,
            rule=narrative.consumer_cost("Electricity", 5, 10, 20), value_format="decimal",
            source="eia", eia_route="electricity/retail-sales",
            eia_facets=(("sectorid", "RES"), ("stateid", "US")), eia_freq="monthly", eia_col="price",
            context=("The U.S. average residential electricity price (cents per kWh) — the power "
                     "bill households pay every month."),
        ),
        Indicator(
            id="renewables-share", title="Renewables · Share of Generation", short="Renewables", unit="%",
            color="#34D399", series_id="RENEW_SHARE", limit=240,
            rule=narrative.generation_share("Renewables"), value_format="decimal",
            source="eia",  # computed/injected (no eia_route)
            context=("The share of U.S. electricity generated from renewables (wind, solar, hydro, "
                     "and more) — the clearest single read on the energy transition."),
        ),
        Indicator(
            id="natgas-share", title="Natural Gas · Share of Generation", short="Gas share", unit="%",
            color="#60A5FA", series_id="NG_SHARE", limit=240,
            rule=narrative.generation_share("Natural gas"), value_format="decimal",
            source="eia",  # computed/injected
            context=("The share of U.S. electricity generated from natural gas — still the single "
                     "largest source, and the swing fuel that balances the grid."),
        ),
        Indicator(
            id="net-generation", title="Total Net Generation", short="Net generation", unit="",
            color="#38BDF8", series_id="NET_GEN_TOTAL", limit=240,
            rule=narrative.energy_level("Net generation"), value_format="thousands",
            source="eia",  # computed/injected (total from generation_mix)
            context=("Total U.S. net electricity generation (GWh) — a read on how much power the "
                     "economy is consuming."),
        ),
    ],
)

ENERGY_COMMODITIES = Lens(
    id="energy-commodities", title="Commodities & Materials", accent="#A3E635",
    indicators=[
        Indicator(
            id="food-index", title="Global Food Prices · year-over-year", short="Food", unit="%",
            color="#A3E635", series_id="PFOODINDEXM", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_band("Food", 5, 12, 25), value_format="decimal",
            context=("How fast the IMF's global food commodity index is rising versus a year "
                     "ago — the upstream driver of grocery inflation."),
        ),
        Indicator(
            id="copper", title="Copper · “Dr. Copper”", short="Copper", unit="$",
            color="#FB923C", series_id="PCOPPUSDM", limit=300,
            rule=narrative.energy_level("Copper"), value_format="thousands",
            context=("The global price of copper ($/metric ton) — nicknamed “Dr. Copper” "
                     "for its knack of signalling the direction of the global economy."),
        ),
        Indicator(
            id="broad-commodities", title="Broad Commodities · year-over-year", short="Commodities", unit="%",
            color="#38BDF8", series_id="PALLFNFINDEXM", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_info("The broad commodity index"), value_format="decimal",
            context=("How fast the IMF's all-commodity price index is rising versus a year ago "
                     "— a single gauge of raw-input cost pressure across the economy."),
        ),
    ],
)

ENERGY_EIA_LENSES = [ENERGY_OIL_FUELS, ENERGY_NATURAL_GAS, ENERGY_ELECTRICITY]
ENERGY_LENSES = ENERGY_EIA_LENSES + [ENERGY_COMMODITIES]

CATEGORIES.append(
    {"id": "energy", "title": "Energy & Commodities", "lenses": ENERGY_LENSES,
     "out": "energy", "back": "Energy & Commodities",
     "source_label": "U.S. Energy Information Administration (EIA) and FRED", "disclaimer": ""}
)


# --- Housing & Real Estate (FRED) ---

HOUSING_HOME_PRICES = Lens(
    id="housing-home-prices", title="Price Stability", accent="#F472B6",
    indicators=[
        Indicator(
            id="case-shiller", title="Case-Shiller Home Prices · year-over-year",
            short="Case-Shiller", unit="%", color="#F472B6",
            series_id="CSUSHPINSA", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_band_two_sided("Home prices", hot=(6, 10, 15), cold=(-2, -5, -10)),
            context=("How fast U.S. home prices are rising or falling versus a year ago, from "
                     "the S&P Case-Shiller national index — the most-watched measure of home "
                     "prices. Roughly 0-5% a year is normal; reported with a ~2-month lag."),
        ),
        Indicator(
            id="existing-home-sales", title="Existing-Home Sales · annual rate",
            short="Home sales", unit="M", color="#38BDF8",
            series_id="EXHOSLUSM495S", limit=240, derive=derive.units_to_millions,
            rule=narrative.market_health("Home sales", hot=(10, 20, 30), cold=(-10, -20, -30)),
            context=("How many existing homes are selling, in millions at an annual rate — the "
                     "market's pulse. A collapse in sales is how a housing freeze shows up first."),
        ),
        Indicator(
            id="median-price", title="Median Sales Price of Houses Sold",
            short="Median price", unit="$", color="#34D399",
            series_id="MSPUS", limit=80, value_format="thousands",
            rule=narrative.energy_level("The median sale price"),
            context=("The median price of homes actually sold (quarterly) — a dollars-and-cents "
                     "companion to the Case-Shiller index."),
        ),
    ],
)

HOUSING_AFFORDABILITY = Lens(
    id="housing-affordability", title="Affordability & Financing", accent="#FBBF24",
    indicators=[
        Indicator(
            id="affordability-index", title="Housing Affordability Index (NAR)",
            short="Affordability", unit="", color="#F472B6",
            series_id="FIXHAI", limit=240,
            rule=narrative.rule_affordability,
            context=("The National Association of Realtors index: 100 means the median-income "
                     "family can just barely afford the median home. Higher is better — "
                     "the historical norm is 130-180."),
        ),
        Indicator(
            id="debt-service", title="Mortgage Debt Service · % of income",
            short="Debt service", unit="%", color="#38BDF8",
            series_id="MDSP", limit=80,
            rule=narrative.level_points("The mortgage-payment share of disposable income"),
            context=("Mortgage payments as a share of household disposable income (quarterly) — "
                     "how heavy the aggregate mortgage burden actually is."),
        ),
        Indicator(
            id="delinquency", title="Mortgage Delinquency Rate · banks",
            short="Delinquency", unit="%", color="#F87171",
            series_id="DRSFRMACBS", limit=80,
            rule=narrative.rule_mortgage_delinquency,
            context=("The share of single-family mortgages at commercial banks that are past "
                     "due (quarterly) — where affordability stress turns into credit stress."),
        ),
        Indicator(
            id="mortgage-rate", title="30-Year Fixed Mortgage Rate",
            short="30-yr mortgage", unit="%", color="#FBBF24",
            series_id="MORTGAGE30US", limit=1040,
            rule=narrative.rule_mortgage,
            context=("The average rate on a 30-year fixed home loan — the input behind the "
                     "affordability squeeze above: it sets what a buyer can afford each month."),
        ),
    ],
)

HOUSING_SUPPLY_CONSTRUCTION = Lens(
    id="housing-supply-construction", title="Supply & Construction", accent="#34D399",
    indicators=[
        Indicator(
            id="months-supply", title="Months of New-Home Supply",
            short="Months' supply", unit="months", color="#FBBF24",
            series_id="MSACSR", limit=240,
            rule=narrative.rule_months_supply,
            context=("How many months it would take to sell every new home on the market at "
                     "the current sales pace. Roughly 4-6 months is balanced; more is a glut, "
                     "less is a squeeze."),
        ),
        Indicator(
            id="active-listings", title="Active Listings (Realtor.com) · millions",
            short="Listings", unit="M", color="#38BDF8",
            series_id="ACTLISCOUUS", limit=240, derive=derive.units_to_millions,
            rule=narrative.energy_level("The number of homes for sale", fmt="{:,.2f} million"),
            context=("Homes listed for sale nationwide, in millions (Realtor.com count, "
                     "since 2016) — the inventory buyers actually get to choose from."),
        ),
        Indicator(
            id="housing-starts", title="Housing Starts · thousands, annual rate",
            short="Starts", unit="", color="#34D399",
            series_id="HOUST", limit=240, value_format="thousands",
            rule=narrative.market_health("Homebuilding", hot=(20, 35, 50), cold=(-10, -20, -35)),
            context=("New homes started each month, in thousands of units at an annual rate "
                     "(1,465 means ~1.47 million homes/year) — the construction industry's "
                     "output, and a classic leading indicator."),
        ),
        Indicator(
            id="building-permits", title="Building Permits · thousands, annual rate",
            short="Permits", unit="", color="#A78BFA",
            series_id="PERMIT", limit=240, value_format="thousands",
            rule=narrative.market_health("Permitting", hot=(20, 35, 50), cold=(-10, -20, -35)),
            context=("Permits pulled for new housing units, in thousands at an annual rate — "
                     "the step before starts, so it leads the rest of the construction pipeline."),
        ),
    ],
)

HOUSING_RENT_SHELTER = Lens(
    id="housing-rent-shelter", title="Rent & Shelter", accent="#A78BFA",
    indicators=[
        Indicator(
            id="rent-cpi", title="Rent Inflation · CPI rent, year-over-year",
            short="Rent CPI", unit="%", color="#A78BFA",
            series_id="CUSR0000SEHA", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_band("Rent", 4, 6, 9),
            context=("How fast the rent tenants actually pay is rising versus a year ago, from "
                     "the rent component of the Consumer Price Index. It moves slowly but "
                     "relentlessly, and it is a third of core CPI."),
        ),
        Indicator(
            id="owners-equivalent-rent", title="Owners' Equivalent Rent · year-over-year",
            short="OER", unit="%", color="#38BDF8",
            series_id="CUSR0000SEHC", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_info("Owners' equivalent rent"),
            context=("How fast the implied rent on owner-occupied homes is rising — the largest "
                     "single component of the CPI, and the bridge between home prices and "
                     "inflation."),
        ),
        Indicator(
            id="rental-vacancy", title="Rental Vacancy Rate",
            short="Vacancy", unit="%", color="#34D399",
            series_id="RRVRUSQ156N", limit=80,
            rule=narrative.rule_rental_vacancy,
            context=("The share of rental units sitting empty (quarterly). Low vacancy gives "
                     "landlords pricing power; high vacancy hands it back to renters."),
        ),
        Indicator(
            id="homeownership", title="Homeownership Rate",
            short="Ownership", unit="%", color="#F472B6",
            series_id="RHORUSQ156N", limit=80,
            rule=narrative.level_points("The homeownership rate"),
            context=("The share of households that own their home (quarterly) — the long arc "
                     "of whether owning is gaining or losing ground versus renting."),
        ),
    ],
)

HOUSING_LENSES = [HOUSING_HOME_PRICES, HOUSING_AFFORDABILITY,
                  HOUSING_SUPPLY_CONSTRUCTION, HOUSING_RENT_SHELTER]

CATEGORIES.append(
    {"id": "housing", "title": "Housing & Real Estate", "lenses": HOUSING_LENSES,
     "out": "housing", "back": "Housing & Real Estate",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed", "disclaimer": ""}
)


# --- Global Economy (FRED + IMF WEO + NY Fed + policyuncertainty.com) ---
# Every other category is US-domestic; this one covers the world: the dollar,
# global growth, trade & supply chains, and policy uncertainty. The dollar
# index (DTWEXBGS) moved here from the Markets scoreboard — one home per number.

GLOBAL_DOLLAR_CURRENCIES = Lens(
    id="global-dollar-currencies", title="The Dollar & Currencies", accent="#38BDF8",
    indicators=[
        Indicator(
            id="dollar-yoy", title="Broad Dollar Index · year-over-year",
            short="Dollar YoY", unit="%", color="#38BDF8",
            series_id="DTWEXBGS", units_transform="pc1", limit=2600,
            rule=narrative.rule_dollar_yoy,
            context=("How fast the trade-weighted dollar is rising or falling versus a "
                     "year ago. Big moves in either direction are destabilizing: a "
                     "surging dollar squeezes the world's dollar borrowers and crushes "
                     "emerging markets; a sliding one imports inflation."),
        ),
        Indicator(
            id="euro", title="Euro · dollars per euro", short="Euro", unit="$",
            color="#34D399", series_id="DEXUSEU", limit=2600,
            rule=narrative.fx_yoy("The euro"),
            context=("How many dollars one euro buys. The world's second currency — "
                     "a rising number means a stronger euro (and a weaker dollar) — "
                     "and the cleanest mirror on dollar strength."),
        ),
        Indicator(
            id="yen", title="Japanese Yen · yen per dollar", short="Yen", unit="",
            color="#FB7185", series_id="DEXJPUS", limit=2600,
            rule=narrative.fx_yoy("The yen", weaker_when_up=True),
            context=("How many yen one dollar buys — a rising number means a WEAKER "
                     "yen. Japan's currency anchors Asia's funding markets; a violent "
                     "yen move tends to ripple through global markets."),
        ),
        Indicator(
            id="yuan", title="Chinese Yuan · yuan per dollar", short="Yuan", unit="",
            color="#FBBF24", series_id="DEXCHUS", limit=2600,
            rule=narrative.fx_yoy("The yuan", weaker_when_up=True),
            context=("How many yuan one dollar buys — a rising number means a WEAKER "
                     "yuan. Beijing manages this rate; a deliberate slide makes Chinese "
                     "exports cheaper and tends to escalate trade tensions."),
        ),
    ],
)

GLOBAL_GROWTH = Lens(
    id="global-growth", title="Global Growth", accent="#34D399",
    indicators=[
        Indicator(
            id="world-growth", title="World Real GDP Growth · annual",
            short="World growth", unit="%", color="#34D399",
            series_id="WEO_G001_NGDP_RPCH", limit=60,
            source="imf", imf_key="G001.NGDP_RPCH",
            rule=narrative.world_growth(imf.forecast_for("G001.NGDP_RPCH")),
            context=("The IMF's measure of how fast the whole world economy is growing "
                     "each year. The long-run trend is about 3.5%; below 2% is what "
                     "economists call a global recession — it has happened only a "
                     "handful of times since 1980."),
        ),
        Indicator(
            id="china-growth", title="China Real GDP Growth · annual",
            short="China", unit="%", color="#F87171",
            series_id="WEO_CHN_NGDP_RPCH", limit=60,
            source="imf", imf_key="CHN.NGDP_RPCH",
            rule=narrative.annual_growth("China's economy"),
            context=("China's annual growth rate (IMF WEO). The world's second-largest "
                     "economy and its biggest growth engine — China's slowdown from "
                     "double digits to under 5% reshapes demand for everything."),
        ),
        Indicator(
            id="euro-growth", title="Euro Area Real GDP Growth · annual",
            short="Euro area", unit="%", color="#38BDF8",
            series_id="WEO_G163_NGDP_RPCH", limit=60,
            source="imf", imf_key="G163.NGDP_RPCH",
            rule=narrative.annual_growth("The euro area's economy"),
            context=("The euro area's annual growth rate (IMF WEO) — the world's "
                     "third-largest economic bloc, and the one most exposed to energy "
                     "shocks and trade disruption."),
        ),
        Indicator(
            id="world-inflation", title="World Inflation · annual",
            short="World inflation", unit="%", color="#FBBF24",
            series_id="WEO_G001_PCPIPCH", limit=60,
            source="imf", imf_key="G001.PCPIPCH",
            rule=narrative.rule_world_inflation,
            context=("World consumer-price inflation (IMF WEO) — the global backdrop "
                     "behind every central bank's rate decisions. The pre-pandemic "
                     "norm was about 3-4%."),
        ),
        Indicator(
            id="ea-gdp-quarterly", title="Euro Area Real GDP · year-over-year",
            short="EA quarterly", unit="%", color="#A78BFA",
            series_id="CLVMEURSCAB1GQEA19", units_transform="pc1", limit=120,
            rule=narrative.yoy_info("Euro-area real GDP"),
            context=("The euro area's quarterly GDP versus a year earlier — the only "
                     "quarterly pulse in this lens, so it updates between the IMF's "
                     "April and October forecast rounds."),
        ),
    ],
)

GLOBAL_TRADE_SUPPLY = Lens(
    id="global-trade-supply", title="Trade & Supply Chain", accent="#FBBF24",
    indicators=[
        Indicator(
            id="gscpi", title="Global Supply Chain Pressure Index",
            short="Supply chain", unit="σ", color="#FBBF24",
            series_id="GSCPI", limit=400, source="nyfed",
            rule=narrative.rule_gscpi,
            context=("The NY Fed's gauge of global supply-chain strain — shipping "
                     "costs, delivery times, and backlogs rolled into one index, "
                     "measured in standard deviations from normal. The COVID logjam "
                     "peaked near 4.5σ; negative means looser than normal."),
        ),
        Indicator(
            id="trade-balance", title="U.S. Trade Deficit · goods & services",
            short="Trade deficit", unit="$B", color="#38BDF8",
            series_id="BOPGSTB", limit=300,
            derive=derive.scaled(-1000, 1),  # balance is negative; show deficit size
            rule=narrative.rule_trade_deficit,
            context=("How much more the U.S. imports than it exports, in billions per "
                     "month. The U.S. has run a deficit every year since 1976 — what "
                     "matters is whether it is widening or narrowing, and why."),
        ),
        Indicator(
            id="import-prices", title="Import Prices · year-over-year",
            short="Import prices", unit="%", color="#FB923C",
            series_id="IR", units_transform="pc1", limit=300,
            rule=narrative.yoy_band("Import", 4, 8, 12),
            context=("How fast the prices of everything the U.S. imports are rising "
                     "versus a year ago. Tariffs, a weaker dollar, and supply shocks "
                     "all show up here first — before they reach store shelves."),
        ),
        Indicator(
            id="china-exports", title="China Exports · year-over-year",
            short="China exports", unit="%", color="#F87171",
            series_id="XTEXVA01CNM667S", units_transform="pc1", limit=300,
            rule=narrative.yoy_info("China's export trade"),
            context=("The growth of China's exports versus a year ago — the single "
                     "best pulse on global goods demand, since China ships roughly "
                     "a seventh of the world's exports."),
        ),
    ],
)

GLOBAL_UNCERTAINTY = Lens(
    id="global-uncertainty", title="Uncertainty & Risk", accent="#A78BFA",
    indicators=[
        Indicator(
            id="us-epu", title="U.S. Economic Policy Uncertainty",
            short="US uncertainty", unit="", color="#A78BFA",
            series_id="USEPU", limit=1600, source="epu", value_format="thousands",
            rule=narrative.epu_band("U.S. policy uncertainty"),
            context=("The Baker/Bloom/Davis index of U.S. economic policy uncertainty, "
                     "built by counting newspaper coverage of policy-driven economic "
                     "uncertainty. The long-run norm is about 100; it spikes around "
                     "elections, debt-ceiling standoffs, trade wars, and crises."),
        ),
        Indicator(
            id="gepu", title="Global Economic Policy Uncertainty",
            short="Global uncertainty", unit="", color="#38BDF8",
            series_id="GEPU", limit=400, source="epu", value_format="thousands",
            rule=narrative.epu_band("Global policy uncertainty", cap="watch"),
            context=("The same newspaper-based uncertainty measure aggregated across "
                     "21 countries (GDP-weighted). Note: it publishes with a lag of "
                     "about six months, so it reads as a sanity check on the timelier "
                     "U.S. index above, not a live signal."),
        ),
    ],
)

GLOBAL_LENSES = [GLOBAL_DOLLAR_CURRENCIES, GLOBAL_GROWTH,
                 GLOBAL_TRADE_SUPPLY, GLOBAL_UNCERTAINTY]

CATEGORIES.append(
    {"id": "global", "title": "Global Economy", "lenses": GLOBAL_LENSES,
     "out": "global", "back": "Global Economy",
     "source_label": "FRED, IMF World Economic Outlook, NY Fed, and policyuncertainty.com",
     "disclaimer": ""}
)


# --- Corporate & Business Health (FRED) ---
# The "strategic" leg: are profits growing, are new firms forming, is capex
# expanding, is credit tightening? Pure FRED. Two cross-series shares
# (profits/GDP, high-propensity/total applications) are computed at refresh
# time via util.pct_share and injected under source="computed" fetch keys;
# GDP is fetched solely as a share denominator and gets no chart of its own.

BUSINESS_PROFITABILITY = Lens(
    id="business-profitability", title="Profitability", accent="#34D399",
    indicators=[
        Indicator(
            id="profit-growth", title="Corporate Profits · year-over-year",
            short="Profit growth", unit="%", color="#34D399",
            series_id="CP", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Corporate profits", 0, -5, -15),
            context=("How fast after-tax corporate profits are growing versus a year ago "
                     "(quarterly, all U.S. corporations — about $3.9 trillion a year). "
                     "Falling profits are how downturns reach hiring and investment."),
        ),
        Indicator(
            id="nonfinancial-profits", title="Nonfinancial Corporate Profits · year-over-year",
            short="Nonfin. profits", unit="%", color="#38BDF8",
            series_id="NFCPATAX", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_info("Nonfinancial corporate profit"),
            context=("The same after-tax profit growth for nonfinancial corporations only — "
                     "the 'Main Street corporates' read, with banks stripped out."),
        ),
        Indicator(
            id="profit-share", title="Corporate Profits · share of GDP",
            short="Profit share", unit="%", color="#A78BFA",
            series_id="CP_GDP_SHARE", limit=104, source="computed",
            rule=narrative.level_points("The corporate-profit share of GDP"),
            context=("After-tax corporate profits as a share of GDP — the closest public "
                     "proxy for economy-wide profit margins. The post-war norm is 5-7%; "
                     "the 2020s have run near record highs above 11%."),
        ),
        Indicator(
            id="proprietors-income", title="Proprietors' Income · year-over-year",
            short="Proprietors", unit="%", color="#FBBF24",
            series_id="PROPINC", limit=104, derive=derive.yoy_pct,
            rule=narrative.yoy_info("Proprietors' income"),
            context=("Income of unincorporated businesses — sole proprietors and "
                     "partnerships. The closest thing to a small-business earnings line."),
        ),
    ],
)

BUSINESS_FORMATION = Lens(
    id="business-formation", title="Business Formation", accent="#38BDF8",
    indicators=[
        Indicator(
            id="applications", title="Business Applications · year-over-year",
            short="Applications", unit="%", color="#38BDF8",
            series_id="BABATOTALSAUS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Business applications", 0, -5, -15),
            context=("How fast new business applications are growing versus a year ago "
                     "(Census Business Formation Statistics — roughly half a million "
                     "applications a month). Falling applications mean fading dynamism."),
        ),
        Indicator(
            id="high-propensity", title="High-Propensity Applications · year-over-year",
            short="High-propensity", unit="%", color="#A78BFA",
            series_id="BAHBATOTALSAUS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_info("High-propensity application volume"),
            context=("Growth in applications with characteristics that make them likely to "
                     "become employer businesses — the quality signal inside the headline count."),
        ),
        Indicator(
            id="hp-share", title="High-Propensity Share of Applications",
            short="HP share", unit="%", color="#FBBF24",
            series_id="BFS_HP_SHARE", limit=300, source="computed",
            rule=narrative.level_points("The high-propensity share of applications"),
            context=("What fraction of all business applications look likely to become "
                     "employers — formation quality over time. It ran near half before "
                     "the pandemic-era boom in solo ventures pushed it below a third."),
        ),
    ],
)

BUSINESS_INVESTMENT = Lens(
    id="business-investment", title="Investment & Activity", accent="#FBBF24",
    indicators=[
        Indicator(
            id="core-capex", title="Core Capital-Goods Orders · year-over-year",
            short="Core capex", unit="%", color="#FBBF24",
            series_id="NEWORDER", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Core capital-goods orders", 0, -3, -10),
            context=("Orders for nondefense capital goods excluding aircraft — the cleanest "
                     "monthly read on whether businesses are investing in equipment. "
                     "(Headline durable goods is skipped here: aircraft orders make it noise.)"),
        ),
        Indicator(
            id="real-sales", title="Real Business Sales · year-over-year",
            short="Real sales", unit="%", color="#34D399",
            series_id="CMRMTSPL", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_contraction_band("Real business sales", 0, -2, -6),
            context=("Real manufacturing and trade sales — total business volume adjusted "
                     "for inflation, one of the inputs NBER uses to date recessions."),
        ),
        Indicator(
            id="inventories-sales", title="Inventories-to-Sales Ratio",
            short="Inv./sales", unit="", color="#38BDF8",
            series_id="ISRATIO", limit=240,
            rule=narrative.rule_inventories_sales,
            context=("Total business inventories measured against a month of sales. Rising "
                     "means goods are piling up unsold — the overhang that precedes "
                     "production cuts. The COVID spike hit 1.74; 2008 peaked near 1.48."),
        ),
    ],
)

BUSINESS_CREDIT = Lens(
    id="business-credit", title="Credit & Stress", accent="#F87171",
    indicators=[
        Indicator(
            id="baa-spread", title="Baa Corporate Spread · over 10-Year Treasury",
            short="Baa spread", unit="%", color="#F87171",
            series_id="BAA10YM", limit=240,
            rule=narrative.rule_baa_spread,
            context=("The extra yield investors demand to hold Moody's Baa-rated corporate "
                     "bonds over 10-year Treasuries — the price of ordinary corporate credit "
                     "risk, with history back to 1953. 2008 peaked near 6 points. (A different "
                     "index family from the ICE BofA spreads on the Markets risk lens.)"),
        ),
        Indicator(
            id="lending-standards", title="Lending Standards · net % of banks tightening",
            short="Standards", unit="%", color="#FBBF24",
            series_id="DRTSCILM", limit=80,
            rule=narrative.rule_lending_standards,
            context=("From the Fed's quarterly loan-officer survey: the share of banks "
                     "tightening standards on commercial & industrial loans minus the share "
                     "easing. Sustained tightening above ~20% has preceded every modern recession."),
        ),
        Indicator(
            id="delinquency", title="Business-Loan Delinquency Rate",
            short="Delinquency", unit="%", color="#FB923C",
            series_id="DRBLACBS", limit=80,
            rule=narrative.rule_business_delinquency,
            context=("The share of commercial & industrial loans at banks that are past due "
                     "(quarterly) — where business credit stress stops being a forecast and "
                     "shows up as missed payments. The 2009 peak was about 4.4%."),
        ),
        Indicator(
            id="ci-loan-growth", title="C&I Loan Growth · year-over-year",
            short="C&I loans", unit="%", color="#A78BFA",
            series_id="BUSLOANS", limit=300, derive=derive.yoy_pct,
            rule=narrative.yoy_band_two_sided("C&I lending", hot=(10, 20, 30),
                                              cold=(-0.5, -5, -12), verb="is"),
            context=("How fast bank lending to businesses is growing. Outright contraction "
                     "is a credit squeeze; double-digit booms (2020 hit +30%) have their own "
                     "way of ending badly."),
        ),
    ],
)

BUSINESS_LENSES = [BUSINESS_PROFITABILITY, BUSINESS_FORMATION,
                   BUSINESS_INVESTMENT, BUSINESS_CREDIT]

CATEGORIES.append(
    {"id": "business", "title": "Corporate & Business Health", "lenses": BUSINESS_LENSES,
     "out": "business", "back": "Corporate & Business Health",
     "source_label": "Federal Reserve Economic Data (FRED), St. Louis Fed", "disclaimer": ""}
)

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
        Indicator(
            id="yield-curve",
            title="Yield Curve · 10-Year minus 2-Year",
            short="Yield curve",
            unit="%",
            color="#F87171",
            series_id="T10Y2Y",
            limit=2600,
            rule=narrative.rule_yield_curve,
            context=(
                "The gap between 10-year and 2-year Treasury yields. When it turns "
                "negative, short-term borrowing costs more than long-term — a sign markets "
                "expect the Fed to cut rates ahead."
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

LENSES = [RECESSION_WATCH, COST_OF_MONEY, JOB_MARKET]

"""Lens configuration — the single source of truth for what gets built."""

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import narrative

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

LENSES = [RECESSION_WATCH]

"""IMF World Economic Outlook via the SDMX 2.1 API — keyless annual macro data.

`https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO/{KEY}.{IND}.A` is the
only working public path (old dataservices.imf.org is dead; DataMapper is
Akamai-blocked). It returns StructureSpecific XML regardless of Accept headers:
Series elements carry COUNTRY/INDICATOR attributes, child Obs carry
TIME_PERIOD/OBS_VALUE. Countries and indicators batch with `+`.

WEO publishes projections years ahead — and its current-year value is itself
a projection for most of the year. Charts and key stats use actuals only
(<= the last completed year); `split_actuals` does the truncation and hands
back the nearest forward projection (normally the current year), which reaches
lens reads in prose via the late-binding `FORECASTS` registry (populated by
the injector at fetch time, read by narrative rules at build time through
`forecast_for`).
"""

import datetime
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://api.imf.org/external/sdmx/2.1/data/IMF.RES,WEO"

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Late-binding forecast registry: "COUNTRY.INDICATOR" -> {"year","value"}.
# refresh_lenses populates it after each IMF fetch; narrative rules read it
# through forecast_for() so config can be declared before any data exists.
FORECASTS = {}


def forecast_for(key):
    """Return a zero-arg callable that looks up the forecast for `key` lazily."""
    return lambda: FORECASTS.get(key)


def _local(tag):
    """Strip any XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


def parse_weo(xml_bytes):
    """Parse StructureSpecific WEO XML into {"COUNTRY.INDICATOR": [{'date','value'}]}.

    Observations are sorted oldest-first; values stay strings (FRED style).
    Tag matching is namespace-agnostic — the live payload namespaces Series/Obs
    under the dataset-specific structure namespace.
    """
    root = ET.fromstring(xml_bytes)
    series = {}
    for el in root.iter():
        if _local(el.tag) != "Series":
            continue
        country = el.get("COUNTRY")
        indicator = el.get("INDICATOR")
        if not country or not indicator:
            continue
        obs = []
        for child in el:
            if _local(child.tag) != "Obs":
                continue
            period = child.get("TIME_PERIOD")
            value = child.get("OBS_VALUE")
            if period is None or value is None:
                continue
            try:
                float(value)
            except ValueError:
                continue  # WEO uses 'n/a'/'--' for country gaps
            obs.append({"date": period, "value": value})
        obs.sort(key=lambda o: o["date"])
        series[f"{country}.{indicator}"] = obs
    return series


def split_actuals(obs, today=None):
    """Split annual obs into (actuals through the last completed year, nearest
    forward IMF projection).

    WEO's current-year value is itself a projection for most of the year, so
    actuals stop at `today.year - 1` — hub deltas and charts never include a
    projected point. The first observation after that (normally the current
    year) comes back as {"year","value"} for prose use; its value is a float
    so narrative rules can format it directly. Non-year periods and
    non-numeric values are skipped.
    """
    if today is None:
        today = datetime.date.today()
    last_actual = today.year - 1
    actuals, forecast = [], None
    for o in obs:  # oldest-first per parse_weo
        try:
            year = int(o["date"])
            value = float(o["value"])
        except (TypeError, ValueError):
            continue
        if year <= last_actual:
            actuals.append(o)
        elif forecast is None:
            forecast = {"year": o["date"], "value": value}
    return actuals, forecast


def weo_series(countries, indicators, start="1980", timeout=30):
    """Fetch batched WEO series: one request for all countries x indicators.

    Returns the parse_weo dict ({"COUNTRY.INDICATOR": obs}). Raises on network
    failure so the injector can keep prior data.
    """
    key = "+".join(countries)
    ind = "+".join(indicators)
    url = f"{BASE}/{key}.{ind}.A?startPeriod={start}"
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_weo(resp.read())

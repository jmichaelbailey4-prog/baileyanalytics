"""NY Fed Global Supply Chain Pressure Index (GSCPI) — keyless monthly CSV.

The file behind the official interactive
(`.../interactives/data/gscpi/gscpi_interactive_data.csv`) is a **vintage
matrix**: the header row is Excel serial numbers (one column per monthly
vintage), each data row is a `30-Sep-1997`-style month-end date followed by
that month's value as estimated at each vintage; cells not yet published are
`#N/A`. The current series is the LAST non-`#N/A` cell in each row.

Needs a browser-ish User-Agent. Do NOT use the site's .xlsx download — it is
secretly binary .xls (unparseable with stdlib).
"""

import csv
import io
import urllib.request

URL = ("https://www.newyorkfed.org/medialibrary/research/interactives/"
       "data/gscpi/gscpi_interactive_data.csv")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_NA = "#N/A"

# Explicit English month map — strptime's %b is locale-dependent and would
# yield zero rows on a non-English system.
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _month_key(raw):
    """'30-Sep-1997' -> '1997-09'; None for header/junk rows."""
    parts = raw.strip().split("-")
    if len(parts) != 3:
        return None
    day, mon, year = parts
    month = _MONTHS.get(mon[:3].lower())
    if month is None or not (day.isdigit() and year.isdigit() and len(year) == 4):
        return None
    return f"{int(year):04d}-{month:02d}"


def parse_gscpi(text):
    """Parse the vintage matrix into oldest-first [{'date': 'YYYY-MM', 'value'}].

    Takes the last non-#N/A column per row (the current vintage for that
    month); skips the Excel-serial header and any non-date rows. Values are
    formatted to 2dp strings (the index is in sigma units).
    """
    out = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        key = _month_key(row[0])
        if key is None:
            continue  # header / junk row
        value = None
        for cell in row[1:]:
            cell = cell.strip()
            if not cell or cell == _NA:
                continue
            try:
                value = float(cell)
            except ValueError:
                continue
        if value is None:
            continue
        out.append({"date": key, "value": f"{value:.2f}"})
    out.sort(key=lambda o: o["date"])
    return out


def gscpi(timeout=30):
    """Fetch the current GSCPI series. Raises on network failure so the
    injector can keep prior data."""
    req = urllib.request.Request(URL, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_gscpi(resp.read().decode("utf-8-sig"))

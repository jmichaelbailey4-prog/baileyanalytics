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
import datetime
import io
import urllib.request

URL = ("https://www.newyorkfed.org/medialibrary/research/interactives/"
       "data/gscpi/gscpi_interactive_data.csv")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_NA = "#N/A"


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
        try:
            d = datetime.datetime.strptime(row[0].strip(), "%d-%b-%Y")
        except ValueError:
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
        out.append({"date": d.strftime("%Y-%m"), "value": f"{value:.2f}"})
    out.sort(key=lambda o: o["date"])
    return out


def gscpi(timeout=30):
    """Fetch the current GSCPI series. Raises on network failure so the
    injector can keep prior data."""
    req = urllib.request.Request(URL, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_gscpi(resp.read().decode("utf-8-sig"))

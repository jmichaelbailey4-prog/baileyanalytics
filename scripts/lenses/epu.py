"""Baker/Bloom/Davis Economic Policy Uncertainty indices — keyless monthly xlsx.

policyuncertainty.com ships true OOXML xlsx (unlike the GPR index's binary
.xls), so a minimal stdlib reader (zipfile + xml.etree + sharedStrings) covers
it. Two files, two quirks each:

- US (`US_Policy_Uncertainty_Data.xlsx`): Year/Month/News_Based_Policy_Uncert_Index,
  rows NEWEST-FIRST, citation string in a trailer row.
- Global (`Global_Policy_Uncertainty_Data.xlsx`): Year/Month/GEPU_current/GEPU_ppp,
  ascending, citation trailer. We chart GEPU_current (the headline series).

Attribution to Baker, Bloom & Davis is required by the data's terms and lives
on the uncertainty lens page.
"""

import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

US_URL = "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx"
GLOBAL_URL = "https://www.policyuncertainty.com/media/Global_Policy_Uncertainty_Data.xlsx"

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col_index(ref):
    """'BC12' -> 0-based column index 54."""
    letters = re.match(r"[A-Z]+", ref).group(0)
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def read_rows(xlsx_bytes):
    """Read sheet1 of an xlsx as a list of rows (lists of cell values).

    Shared strings are resolved; numeric cells come back as strings of the raw
    stored value. Sparse cells are positioned by their cell reference.
    """
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sst.iter(f"{_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row_el in sheet.iter(f"{_NS}row"):
        row = []
        for c in row_el.iter(f"{_NS}c"):
            ref = c.get("r")
            idx = _col_index(ref) if ref else len(row)
            v = c.find(f"{_NS}v")
            if v is None or v.text is None:
                continue
            value = shared[int(v.text)] if c.get("t") == "s" else v.text
            while len(row) <= idx:
                row.append(None)
            row[idx] = value
        rows.append(row)
    return rows


def parse_epu(xlsx_bytes, value_header_prefixes):
    """Parse an EPU workbook into ascending [{'date': 'YYYY-MM', 'value'}].

    Columns are located by header text: Year, Month, and the first column whose
    header starts with any of `value_header_prefixes`. Non-numeric rows (the
    citation trailer) are skipped; values format to 2dp strings.
    """
    rows = read_rows(xlsx_bytes)
    if not rows:
        return []
    header = [str(h) if h is not None else "" for h in rows[0]]

    def find(pred):
        for i, h in enumerate(header):
            if pred(h):
                return i
        raise ValueError(f"column not found in header: {header}")

    yi = find(lambda h: h.strip().lower() == "year")
    mi = find(lambda h: h.strip().lower() == "month")
    vi = find(lambda h: any(h.strip().startswith(p) for p in value_header_prefixes))

    out = []
    for row in rows[1:]:
        try:
            year = int(float(row[yi]))
            month = int(float(row[mi]))
            value = float(row[vi])
        except (TypeError, ValueError, IndexError):
            continue  # citation trailer / junk
        out.append({"date": f"{year:04d}-{month:02d}", "value": f"{value:.2f}"})
    out.sort(key=lambda o: o["date"])
    return out


def _fetch(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def us_epu(timeout=30):
    """US news-based EPU, monthly, ascending. Raises on network failure."""
    return parse_epu(_fetch(US_URL, timeout), ("News_Based",))


def global_epu(timeout=30):
    """Global EPU (GEPU_current), monthly, ascending. Raises on failure."""
    return parse_epu(_fetch(GLOBAL_URL, timeout), ("GEPU_current",))

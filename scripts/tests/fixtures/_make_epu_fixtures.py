"""Throwaway generator for the EPU xlsx test fixtures (real OOXML, stdlib only).
Run once from anywhere; writes epu_us_sample.xlsx and epu_global_sample.xlsx
next to itself. Kept in-repo so fixtures can be regenerated if formats change.
"""
import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>"""


def col_letter(idx):
    s = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def build(path, rows):
    """rows: list of lists; str -> shared string cell, number -> numeric cell."""
    shared = []

    def s_idx(text):
        if text not in shared:
            shared.append(text)
        return shared.index(text)

    body = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, val in enumerate(row):
            if val is None:
                continue
            ref = f"{col_letter(c)}{r}"
            if isinstance(val, str):
                cells.append(f'<c r="{ref}" t="s"><v>{s_idx(val)}</v></c>')
            else:
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<sheetData>{"".join(body)}</sheetData></worksheet>')
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared)}" uniqueCount="{len(shared)}">'
           + "".join(f"<si><t>{t}</t></si>" for t in shared) + "</sst>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)


US_ROWS = [
    ["Year", "Month", "News_Based_Policy_Uncert_Index"],
    [2026, 5, 296.337],          # newest-first, like the live file
    [2026, 4, 412.5],
    [2026, 3, 388.21],
    [1985, 1, 99.16],
    ["Note: data based on Baker, Bloom and Davis (2016)."],
]

GEPU_ROWS = [
    ["Year", "Month", "GEPU_current", "GEPU_ppp"],
    [1997, 1, 88.3, 91.2],       # ascending, like the live file
    [2025, 10, 305.44, 312.6],
    [2025, 11, 371.32, 380.1],
    ["GEPU based on Davis (2016); see policyuncertainty.com."],
]

if __name__ == "__main__":
    build(HERE / "epu_us_sample.xlsx", US_ROWS)
    build(HERE / "epu_global_sample.xlsx", GEPU_ROWS)
    print("wrote fixtures")

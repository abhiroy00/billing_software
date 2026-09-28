"""Excel/CSV import helpers (Section 22): read outside data files into
plain row-dicts. Parsing lives here; row->service mapping + creation lives
in the controllers so validation stays in one place."""
from __future__ import annotations

import csv
from pathlib import Path

SUPPORTED_EXTENSIONS = (".xlsx", ".csv")


def normalize_header(value) -> str:
    return str(value or "").strip().lower()


def read_table_rows(path: str | Path) -> tuple[list[str], list[dict]]:
    """Returns (headers, rows). Rows are {normalized_header: value} dicts.
    Raises ValueError with a user-friendly message on any file problem."""
    path = Path(path)
    if not path.is_file():
        raise ValueError("File not found. Please choose a valid Excel or CSV file.")
    ext = path.suffix.lower()
    if ext == ".xlsx":
        return _read_xlsx(path)
    if ext == ".csv":
        return _read_csv(path)
    raise ValueError("Only .xlsx and .csv files are supported.")


def _read_xlsx(path: Path) -> tuple[list[str], list[dict]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.values)
    except Exception:
        raise ValueError("Could not read the Excel file. Is it a valid .xlsx file?")
    if not values:
        raise ValueError("The file is empty.")
    return _to_rows(values[0], values[1:])


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            values = list(csv.reader(fh))
    except Exception:
        raise ValueError("Could not read the CSV file.")
    if not values:
        raise ValueError("The file is empty.")
    return _to_rows(values[0], values[1:])


def _to_rows(header_row, data_rows) -> tuple[list[str], list[dict]]:
    headers = [normalize_header(h) for h in header_row]
    if not any(headers):
        raise ValueError("No header row found. First row must contain column names.")
    rows = []
    for record in data_rows:
        cells = list(record) + [None] * (len(headers) - len(record))
        item = {headers[i]: _clean(cells[i]) for i in range(len(headers)) if headers[i]}
        if any(v not in (None, "") for v in item.values()):
            rows.append(item)
    if not rows:
        raise ValueError("No data rows found below the header.")
    if len(rows) > 2000:
        raise ValueError("Too many rows (max 2000 per import). Split the file and try again.")
    return headers, rows


def _clean(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return value


def cell(row: dict, *names: str) -> str:
    """First non-empty value among candidate header names."""
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return value if isinstance(value, str) else str(value).strip()
    return ""


def write_template(path: str | Path, sheet_title: str, headers: list[str], sample: list) -> None:
    from utils.export_utils import write_excel_rows

    write_excel_rows(str(path), sheet_title, headers, [sample])

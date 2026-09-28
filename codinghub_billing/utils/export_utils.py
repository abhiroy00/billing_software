"""Shared Excel/CSV writers for report exports (Section 18/55). Every
report panel formats its own rows, then hands them here — no report-specific
export code duplicated across the GUI."""
from __future__ import annotations

import csv
from typing import Sequence


def write_excel_rows(path: str, sheet_title: str, headers: Sequence[str], rows: Sequence[Sequence]) -> None:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_title[:31]  # Excel sheet name limit
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))

    for column_cells in sheet.columns:
        length = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=0)
        sheet.column_dimensions[column_cells[0].column_letter].width = max(10, length + 2)

    workbook.save(path)


def write_csv_rows(path: str, headers: Sequence[str], rows: Sequence[Sequence]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)

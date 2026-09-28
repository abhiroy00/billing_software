"""GUI-facing layer over report_service (Section 18/50). Every function
returns a plain dict {summary, rows} — the GUI never queries the DB itself.
Excel/CSV export deferred to PDF is intentionally out of scope for this
pass; PDF report export will be added alongside invoice PDF generation."""
from __future__ import annotations

import logging
from datetime import date

from database.connection import get_session
from services import report_service
from utils.export_utils import write_csv_rows, write_excel_rows
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")


def _run(fn, *args, **kwargs) -> dict:
    with get_session() as session:
        result = fn(session, *args, **kwargs)
    return {"summary": result.summary, "rows": result.rows}


def sales_report(date_from: date, date_to: date, customer_id: int | None = None, status: str | None = None) -> dict:
    return _run(report_service.sales_report, date_from, date_to, customer_id=customer_id, status=status)


def payment_report(date_from: date, date_to: date, payment_mode: str | None = None) -> dict:
    return _run(report_service.payment_report, date_from, date_to, payment_mode=payment_mode)


def pending_payments_report(customer_id: int | None = None) -> dict:
    return _run(report_service.pending_payments_report, customer_id=customer_id)


def gst_report(date_from: date, date_to: date) -> dict:
    return _run(report_service.gst_report, date_from, date_to)


def expense_report(date_from: date, date_to: date, category_id: int | None = None) -> dict:
    return _run(report_service.expense_report, date_from, date_to, category_id=category_id)


def profit_summary(date_from: date, date_to: date) -> dict:
    return _run(report_service.profit_summary, date_from, date_to)


def _export(path: str, fmt: str, sheet_title: str, headers: list[str], rows: list[list]) -> tuple[bool, str]:
    try:
        if fmt == "csv":
            write_csv_rows(path, headers, rows)
        else:
            write_excel_rows(path, sheet_title, headers, rows)
        return True, ""
    except Exception:
        logger.exception("Failed to export %s report", sheet_title)
        return False, USER_FRIENDLY_MESSAGE


def export_sales_report(path: str, fmt: str, data: dict) -> tuple[bool, str]:
    headers = ["Invoice No", "Date", "Customer", "Amount", "Paid", "Due", "Status"]
    rows = [
        [r["invoice_number"], r["invoice_date"].strftime("%d-%m-%Y"), r["customer_name"],
         float(r["grand_total"]), float(r["paid_amount"]), float(r["due_amount"]), r["status"]]
        for r in data["rows"]
    ]
    return _export(path, fmt, "Sales Report", headers, rows)


def export_payment_report(path: str, fmt: str, data: dict) -> tuple[bool, str]:
    headers = ["Date", "Invoice No", "Customer", "Amount", "Mode", "Reference"]
    rows = [
        [r["payment_date"].strftime("%d-%m-%Y"), r["invoice_number"], r["customer_name"],
         float(r["amount"]), r["payment_mode"], r["reference_number"] or ""]
        for r in data["rows"]
    ]
    return _export(path, fmt, "Payment Report", headers, rows)


def export_pending_payments_report(path: str, fmt: str, data: dict) -> tuple[bool, str]:
    headers = ["Invoice No", "Date", "Customer", "Mobile", "Grand Total", "Paid", "Due", "Status"]
    rows = [
        [r["invoice_number"], r["invoice_date"].strftime("%d-%m-%Y"), r["customer_name"], r["customer_mobile"],
         float(r["grand_total"]), float(r["paid_amount"]), float(r["due_amount"]), r["status"]]
        for r in data["rows"]
    ]
    return _export(path, fmt, "Pending Payments", headers, rows)


def export_gst_report(path: str, fmt: str, data: dict) -> tuple[bool, str]:
    headers = ["Invoice No", "Date", "Customer", "GSTIN", "Taxable", "CGST", "SGST", "IGST", "Grand Total"]
    rows = [
        [r["invoice_number"], r["invoice_date"].strftime("%d-%m-%Y"), r["customer_name"], r["customer_gstin"],
         float(r["taxable_amount"]), float(r["cgst_total"]), float(r["sgst_total"]), float(r["igst_total"]),
         float(r["grand_total"])]
        for r in data["rows"]
    ]
    return _export(path, fmt, "GST Report", headers, rows)


def export_expense_report(path: str, fmt: str, data: dict) -> tuple[bool, str]:
    headers = ["Date", "Category", "Description", "Vendor", "Amount", "Mode"]
    rows = [
        [r["expense_date"].strftime("%d-%m-%Y"), r["category_name"], r["description"], r["vendor"],
         float(r["amount"]), r["payment_mode"]]
        for r in data["rows"]
    ]
    return _export(path, fmt, "Expense Report", headers, rows)

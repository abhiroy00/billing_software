"""GUI-facing layer over expense_service (Section 16)."""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from config import config
from database.connection import get_session
from services import auth_service, expense_service
from utils.file_utils import delete_file_safe, save_attachment
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

PAYMENT_MODES = expense_service.PAYMENT_MODES


def list_categories() -> list[dict]:
    with get_session() as session:
        return expense_service.list_categories(session)


def list_expenses(
    query: str = "",
    category_id: int | None = None,
    payment_mode: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    with get_session() as session:
        return expense_service.list_expenses(
            session, query=query, category_id=category_id, payment_mode=payment_mode, date_from=date_from, date_to=date_to
        )


def get_expense(expense_id: int) -> dict | None:
    with get_session() as session:
        return expense_service.get_expense_dict(session, expense_id)


def create_expense(data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            expense = expense_service.create_expense(session, auth_service.current_session.user_id, data)
        return True, "", expense
    except expense_service.ExpenseError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to create expense")
        return False, USER_FRIENDLY_MESSAGE, None


def update_expense(expense_id: int, data: dict) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            old = expense_service.get_expense_dict(session, expense_id)
            old_path = (old or {}).get("attachment_path")
            expense = expense_service.update_expense(session, auth_service.current_session.user_id, expense_id, data)
        # If the attachment was replaced/removed, delete the old file from disk.
        new_path = (data.get("attachment_path") if "attachment_path" in data else old_path)
        if old_path and old_path != new_path:
            delete_file_safe(old_path)
        return True, "", expense
    except expense_service.ExpenseError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to update expense")
        return False, USER_FRIENDLY_MESSAGE, None


def delete_expense(expense_id: int) -> tuple[bool, str]:
    try:
        with get_session() as session:
            old = expense_service.get_expense_dict(session, expense_id)
            old_path = (old or {}).get("attachment_path")
            expense_service.delete_expense(session, auth_service.current_session.user_id, expense_id)
        if old_path:
            delete_file_safe(old_path)
        return True, ""
    except expense_service.ExpenseError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to delete expense")
        return False, USER_FRIENDLY_MESSAGE


EXPENSE_TEMPLATE_HEADERS = ["Category*", "Description", "Amount (₹)*", "Date (DD-MM-YYYY)*", "Payment Mode", "Vendor", "Notes"]
_EXPENSE_TEMPLATE_SAMPLE = ["Rent", "Office rent", "15000", "01-09-2026", "Bank Transfer", "Landlord", "Demo row — delete before import"]


def expense_template_file(path: str) -> tuple[bool, str]:
    try:
        from utils import import_utils

        import_utils.write_template(path, "Expenses", EXPENSE_TEMPLATE_HEADERS, _EXPENSE_TEMPLATE_SAMPLE)
        return True, ""
    except Exception:
        logger.exception("Failed to write expense template")
        return False, USER_FRIENDLY_MESSAGE


def import_expenses(path: str) -> tuple[int, list[str]]:
    """Import expenses from .xlsx/.csv. Returns (imported_count, errors)."""
    from utils import import_utils
    from utils.formatters import parse_date

    try:
        _, rows = import_utils.read_table_rows(path)
    except ValueError as exc:
        return 0, [str(exc)]

    category_by_name = {c["name"].lower(): c["id"] for c in list_categories()}
    valid_categories = ", ".join(sorted(category_by_name)) or "—"
    imported = 0
    errors: list[str] = []
    for lineno, row in enumerate(rows, start=2):
        get = lambda *names: import_utils.cell(row, *names)  # noqa: E731
        category_name = get("category")
        category_id = category_by_name.get(category_name.lower()) if category_name else None
        if category_id is None:
            errors.append(f"Row {lineno}: unknown category '{category_name}'. Valid: {valid_categories}.")
            continue
        date_text = get("date (dd-mm-yyyy)*", "date (dd-mm-yyyy)", "date", "expense date")
        try:
            expense_date = parse_date(date_text) if date_text else None
        except Exception:
            errors.append(f"Row {lineno}: date must be DD-MM-YYYY.")
            continue
        data = {
            "category_id": category_id,
            "description": get("description"),
            "amount": get("amount (₹)*", "amount (₹)", "amount"),
            "expense_date": expense_date,
            "payment_mode": get("payment mode", "mode") or "Cash",
            "vendor": get("vendor"),
            "notes": get("notes"),
            "attachment_path": None,
        }
        success, message, _ = create_expense(data)
        if success:
            imported += 1
        else:
            errors.append(f"Row {lineno}: {message}")
        if len(errors) >= 20:
            errors.append("…stopping error list at 20, fix these and re-import the rest.")
            break
    return imported, errors


def attach_file(source_path: str) -> tuple[bool, str, str | None]:
    try:
        path = save_attachment(source_path, config.attachments_dir)
        return True, "", path
    except ValueError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to save attachment")
        return False, USER_FRIENDLY_MESSAGE, None


def remove_attachment(path: str | None) -> tuple[bool, str]:
    """Deletes the saved attachment file from disk.

    Used by the expense form's Remove/Delete button — the caller must
    also clear `attachment_path` on the expense (by saving with None).
    """
    try:
        if not path:
            return True, ""
        delete_file_safe(path)
        return True, ""
    except Exception:
        logger.exception("Failed to delete attachment")
        return False, USER_FRIENDLY_MESSAGE


def open_attachment(path: str) -> tuple[bool, str]:
    if not path or not Path(path).is_file():
        return False, "Attachment file not found."
    try:
        import subprocess
        import sys

        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 - opening a user-selected local file with its default app
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True, ""
    except Exception:
        logger.exception("Failed to open attachment")
        return False, USER_FRIENDLY_MESSAGE


def export_expenses_to_excel(
    path: str,
    query: str = "",
    category_id: int | None = None,
    payment_mode: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[bool, str]:
    try:
        from openpyxl import Workbook

        rows = list_expenses(query=query, category_id=category_id, payment_mode=payment_mode, date_from=date_from, date_to=date_to)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Expenses"
        sheet.append(["Date", "Category", "Description", "Vendor", "Amount", "Payment Mode"])
        for row in rows:
            sheet.append(
                [
                    row["expense_date"].strftime("%d-%m-%Y"),
                    row["category_name"],
                    row["description"],
                    row["vendor"],
                    float(row["amount"]),
                    row["payment_mode"],
                ]
            )
        for column_cells in sheet.columns:
            length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None)
            sheet.column_dimensions[column_cells[0].column_letter].width = max(10, length + 2)

        workbook.save(path)
        return True, ""
    except Exception:
        logger.exception("Failed to export expenses")
        return False, USER_FRIENDLY_MESSAGE

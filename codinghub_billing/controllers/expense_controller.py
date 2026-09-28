"""GUI-facing layer over expense_service (Section 16)."""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

from config import config
from database.connection import get_session
from services import auth_service, expense_service
from utils.file_utils import save_attachment
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
            expense = expense_service.update_expense(session, auth_service.current_session.user_id, expense_id, data)
        return True, "", expense
    except expense_service.ExpenseError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to update expense")
        return False, USER_FRIENDLY_MESSAGE, None


def delete_expense(expense_id: int) -> tuple[bool, str]:
    try:
        with get_session() as session:
            expense_service.delete_expense(session, auth_service.current_session.user_id, expense_id)
        return True, ""
    except expense_service.ExpenseError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to delete expense")
        return False, USER_FRIENDLY_MESSAGE


def attach_file(source_path: str) -> tuple[bool, str, str | None]:
    try:
        path = save_attachment(source_path, config.attachments_dir)
        return True, "", path
    except ValueError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to save attachment")
        return False, USER_FRIENDLY_MESSAGE, None


def open_attachment(path: str) -> tuple[bool, str]:
    if not path or not Path(path).is_file():
        return False, "Attachment file not found."
    try:
        os.startfile(path)  # noqa: S606 - opening a user-selected local file with its default app
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

"""GUI-facing layer over payment_service (Section 15/49)."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from database.connection import get_session
from services import auth_service, payment_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")

PAYMENT_MODES = payment_service.PAYMENT_MODES


def record_payment(
    invoice_id: int,
    amount: Decimal | str,
    payment_mode: str,
    payment_date: date,
    reference_number: str = "",
    notes: str = "",
) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            result = payment_service.record_payment(
                session,
                auth_service.current_session.user_id,
                invoice_id=invoice_id,
                amount=Decimal(str(amount)),
                payment_mode=payment_mode,
                payment_date=payment_date,
                reference_number=reference_number,
                notes=notes,
            )
        return True, "", result
    except payment_service.PaymentError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to record payment")
        return False, USER_FRIENDLY_MESSAGE, None


def list_payments(
    query: str = "", payment_mode: str | None = None, date_from: date | None = None, date_to: date | None = None
) -> list[dict]:
    with get_session() as session:
        return payment_service.list_all_payments(
            session, query=query, payment_mode=payment_mode, date_from=date_from, date_to=date_to
        )


def export_payments_to_excel(
    path: str, query: str = "", payment_mode: str | None = None, date_from: date | None = None, date_to: date | None = None
) -> tuple[bool, str]:
    try:
        from openpyxl import Workbook

        rows = list_payments(query=query, payment_mode=payment_mode, date_from=date_from, date_to=date_to)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Payments"
        sheet.append(["Date", "Invoice No", "Customer", "Amount", "Mode", "Reference"])
        for row in rows:
            sheet.append(
                [
                    row["payment_date"].strftime("%d-%m-%Y"),
                    row["invoice_number"],
                    row["customer_name"],
                    float(row["amount"]),
                    row["payment_mode"],
                    row["reference_number"] or "",
                ]
            )
        for column_cells in sheet.columns:
            length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None)
            sheet.column_dimensions[column_cells[0].column_letter].width = max(10, length + 2)

        workbook.save(path)
        return True, ""
    except Exception:
        logger.exception("Failed to export payments")
        return False, USER_FRIENDLY_MESSAGE

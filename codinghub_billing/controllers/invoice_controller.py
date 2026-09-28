"""GUI-facing layer over invoice_service (Section 13/14)."""
from __future__ import annotations

import logging
from datetime import date

from database.connection import get_session
from services import auth_service, invoice_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")


def peek_next_invoice_number() -> str:
    with get_session() as session:
        return invoice_service.peek_next_invoice_number(session)


def build_invoice_preview(customer_id: int, items: list[dict]) -> tuple[dict | None, str]:
    try:
        with get_session() as session:
            return invoice_service.build_invoice_preview(session, customer_id, items), ""
    except invoice_service.InvoiceError as exc:
        return None, str(exc)


def create_invoice(
    customer_id: int,
    items: list[dict],
    invoice_date: date,
    notes: str = "",
    initial_payment: dict | None = None,
) -> tuple[bool, str, dict | None]:
    try:
        with get_session() as session:
            detail = invoice_service.create_invoice(
                session,
                auth_service.current_session.user_id,
                customer_id=customer_id,
                items=items,
                invoice_date=invoice_date,
                notes=notes,
                initial_payment=initial_payment,
            )
        return True, "", detail
    except invoice_service.InvoiceError as exc:
        return False, str(exc), None
    except Exception:
        logger.exception("Failed to create invoice")
        return False, USER_FRIENDLY_MESSAGE, None


def list_invoices(
    query: str = "", status: str | None = None, date_from: date | None = None, date_to: date | None = None
) -> list[dict]:
    with get_session() as session:
        return invoice_service.list_invoices(session, query=query, status=status, date_from=date_from, date_to=date_to)


def get_invoice_detail(invoice_id: int) -> tuple[dict | None, str]:
    try:
        with get_session() as session:
            return invoice_service.get_invoice_detail(session, invoice_id), ""
    except invoice_service.InvoiceError as exc:
        return None, str(exc)


def cancel_invoice(invoice_id: int) -> tuple[bool, str]:
    try:
        with get_session() as session:
            invoice_service.cancel_invoice(session, auth_service.current_session.user_id, invoice_id)
        return True, ""
    except invoice_service.InvoiceError as exc:
        return False, str(exc)
    except Exception:
        logger.exception("Failed to cancel invoice")
        return False, USER_FRIENDLY_MESSAGE

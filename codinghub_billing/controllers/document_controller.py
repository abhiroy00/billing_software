"""GUI-facing layer over pdf_service (Section 21): fetches invoice detail
+ business/invoice settings, renders the PDF, writes it to disk."""
from __future__ import annotations

import logging
from pathlib import Path

from config import config
from controllers import invoice_controller
from database.connection import get_session
from services import pdf_service, settings_service
from utils.logger import USER_FRIENDLY_MESSAGE

logger = logging.getLogger("codinghub")


def _settings_bundle() -> tuple[dict, dict]:
    with get_session() as session:
        business = settings_service.get_business_settings(session)
        invoice_settings = settings_service.get_invoice_settings(session)
        business_dict = {
            "business_name": business.business_name,
            "address": business.address,
            "phone": business.phone,
            "email": business.email,
            "gstin": business.gstin,
            "pan": business.pan,
            "state": business.state,
            "logo_path": business.logo_path,
        }
        invoice_dict = {
            "prefix": invoice_settings.prefix,
            "terms": invoice_settings.terms,
            "footer_text": invoice_settings.footer_text,
            "signature_path": invoice_settings.signature_path,
        }
    return business_dict, invoice_dict


def default_invoice_path(invoice_number: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in invoice_number)
    return config.invoice_dir / f"Invoice-{safe}.pdf"


def default_receipt_path(receipt_no: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in receipt_no)
    return config.invoice_dir / f"Receipt-{safe}.pdf"


def generate_invoice_pdf(invoice_id: int, dest_path: str | Path) -> tuple[bool, str, Path | None]:
    try:
        detail, error = invoice_controller.get_invoice_detail(invoice_id)
        if detail is None:
            return False, error or "Invoice not found.", None
        business, invoice_settings = _settings_bundle()
        pdf_bytes = pdf_service.build_invoice_pdf(detail, business, invoice_settings)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf_bytes)
        return True, "", dest
    except Exception:
        logger.exception("Failed to generate invoice PDF")
        return False, USER_FRIENDLY_MESSAGE, None


def generate_receipt_pdf(
    invoice_id: int, dest_path: str | Path, payment_id: int | None = None
) -> tuple[bool, str, Path | None]:
    """Receipt for one payment (latest payment when payment_id is None)."""
    try:
        detail, error = invoice_controller.get_invoice_detail(invoice_id)
        if detail is None:
            return False, error or "Invoice not found.", None
        payments = detail["payments"]
        if not payments:
            return False, "No payments recorded on this invoice yet.", None
        payment = next((p for p in payments if p["id"] == payment_id), None) if payment_id else None
        if payment is None:
            payment = max(payments, key=lambda p: (p["payment_date"], p["id"]))
        business, invoice_settings = _settings_bundle()
        pdf_bytes = pdf_service.build_receipt_pdf(detail, payment, business, invoice_settings)
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pdf_bytes)
        return True, "", dest
    except Exception:
        logger.exception("Failed to generate receipt PDF")
        return False, USER_FRIENDLY_MESSAGE, None


def suggest_receipt_path(invoice_id: int, payment_id: int | None = None) -> Path:
    detail, _ = invoice_controller.get_invoice_detail(invoice_id)
    prefix = "CH"
    if detail:
        with get_session() as session:
            prefix = settings_service.get_invoice_settings(session).prefix or "CH"
        payments = detail["payments"]
        payment = next((p for p in payments if p["id"] == payment_id), None) if payment_id else None
        if payment is None and payments:
            payment = max(payments, key=lambda p: (p["payment_date"], p["id"]))
        if payment:
            return default_receipt_path(pdf_service.receipt_number(prefix, payment["payment_date"], payment["id"]))
    return config.invoice_dir / "Receipt.pdf"


def open_file(path: Path) -> tuple[bool, str]:
    """Open a file with the OS default app (best-effort, never raises)."""
    import os
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True, ""
    except Exception:
        logger.exception("Failed to open file")
        return False, USER_FRIENDLY_MESSAGE

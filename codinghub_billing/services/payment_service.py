"""Payment recording (Section 15/49). Every payment is linked to an
invoice; recording one always recalculates the invoice's paid/due/status
here — the GUI never edits those columns directly."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from database.models.payment import Payment
from database.repositories.invoice_repository import InvoiceRepository
from database.repositories.payment_repository import PaymentRepository
from services import audit_service

PAYMENT_MODES = ["Cash", "UPI", "Bank Transfer", "Card", "Cheque", "Other"]


class PaymentError(Exception):
    pass


def record_payment(
    session: Session,
    user_id: int | None,
    invoice_id: int,
    amount: Decimal,
    payment_mode: str,
    payment_date: date,
    reference_number: str = "",
    notes: str = "",
) -> dict:
    from services.invoice_service import recalculate_status

    invoice_repo = InvoiceRepository(session)
    invoice = invoice_repo.get(invoice_id)
    if invoice is None:
        raise PaymentError("Invoice not found.")
    if invoice.status == "CANCELLED":
        raise PaymentError("Cannot record a payment against a cancelled invoice.")

    amount = Decimal(str(amount))
    if amount <= 0:
        raise PaymentError("Payment amount must be greater than zero.")

    due_amount = Decimal(str(invoice.due_amount))
    if amount > due_amount:
        raise PaymentError(
            f"Payment amount (₹{amount}) cannot exceed the outstanding due amount (₹{due_amount})."
        )

    payment = Payment(
        invoice_id=invoice_id,
        customer_id=invoice.customer_id,
        amount=amount,
        payment_mode=payment_mode,
        payment_date=payment_date,
        reference_number=reference_number,
        notes=notes,
        received_by=user_id,
    )
    PaymentRepository(session).add(payment)

    invoice.paid_amount = Decimal(str(invoice.paid_amount)) + amount
    invoice.due_amount = Decimal(str(invoice.grand_total)) - Decimal(str(invoice.paid_amount))
    recalculate_status(invoice)
    session.flush()

    audit_service.log(
        session, user_id, "create", entity_type="payment", entity_id=payment.id,
        description=f"Recorded payment of {amount} for invoice {invoice.invoice_number}",
    )

    return {
        "id": payment.id,
        "invoice_id": invoice_id,
        "amount": amount,
        "payment_mode": payment_mode,
        "payment_date": payment_date,
        "invoice_status": invoice.status,
        "invoice_due_amount": Decimal(str(invoice.due_amount)),
    }


def list_payments(session: Session, invoice_id: int) -> list[dict]:
    payments = PaymentRepository(session).list_for_invoice(invoice_id)
    return [
        {
            "id": p.id,
            "amount": Decimal(str(p.amount)),
            "payment_mode": p.payment_mode,
            "payment_date": p.payment_date,
            "reference_number": p.reference_number,
        }
        for p in payments
    ]


def list_all_payments(
    session: Session,
    query: str = "",
    payment_mode: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    rows = PaymentRepository(session).search(query=query, payment_mode=payment_mode, date_from=date_from, date_to=date_to)
    return [
        {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "invoice_number": invoice_number,
            "customer_name": customer_name,
            "amount": Decimal(str(p.amount)),
            "payment_mode": p.payment_mode,
            "payment_date": p.payment_date,
            "reference_number": p.reference_number,
        }
        for p, invoice_number, customer_name in rows
    ]

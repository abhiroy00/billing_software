"""Invoice / billing business logic (Section 13/14/31). Invoice totals are
always computed here from real line items — the GUI only ever sends raw
item inputs (course, quantity, rate, discount) and displays back whatever
this service computes. Never trust a total coming from the GUI."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.models.invoice import Invoice, InvoiceItem
from database.repositories.invoice_repository import InvoiceRepository
from database.repositories.payment_repository import PaymentRepository
from services import gst_service, settings_service

STATUS_PENDING = "PENDING"
STATUS_PARTIAL = "PARTIAL"
STATUS_PAID = "PAID"
STATUS_CANCELLED = "CANCELLED"


class InvoiceError(Exception):
    pass


def _determine_status(paid_amount: Decimal, grand_total: Decimal) -> str:
    if paid_amount <= 0:
        return STATUS_PENDING
    if paid_amount >= grand_total:
        return STATUS_PAID
    return STATUS_PARTIAL


def peek_next_invoice_number(session: Session, invoice_date: date | None = None) -> str:
    settings = settings_service.get_invoice_settings(session)
    year = (invoice_date or date.today()).year
    return f"{settings.prefix}-{year}-{settings.next_number:06d}"


def _generate_invoice_number(session: Session, invoice_date: date) -> str:
    settings = settings_service.get_invoice_settings(session)
    number = f"{settings.prefix}-{invoice_date.year}-{settings.next_number:06d}"
    settings.next_number += 1
    session.flush()
    return number


def _validate_items(items: list[dict]) -> list[str]:
    if not items:
        return ["At least one item is required."]
    errors = []
    for i, item in enumerate(items, start=1):
        try:
            quantity = Decimal(str(item.get("quantity", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            discount = Decimal(str(item.get("discount", 0)))
        except Exception:
            errors.append(f"Item {i}: quantity/rate/discount must be numeric.")
            continue
        if not item.get("item_name"):
            errors.append(f"Item {i}: a course/product must be selected.")
        if quantity <= 0:
            errors.append(f"Item {i}: quantity must be greater than zero.")
        if rate < 0:
            errors.append(f"Item {i}: rate cannot be negative.")
        if discount < 0:
            errors.append(f"Item {i}: discount cannot be negative.")
        if discount > rate * quantity:
            errors.append(f"Item {i}: discount cannot exceed the item amount.")
    return errors


def build_invoice_preview(session: Session, customer_id: int, items: list[dict]) -> dict:
    """Computes tax breakdown for the GUI to display live, without saving
    anything. Raises InvoiceError on invalid input."""
    errors = _validate_items(items)
    if errors:
        raise InvoiceError(" ".join(errors))

    customer = session.get(Customer, customer_id)
    if customer is None:
        raise InvoiceError("Customer not found.")

    business = settings_service.get_business_settings(session)
    tax_type = gst_service.determine_tax_type(business.state, customer.state)

    computed_items = []
    for item in items:
        calc = gst_service.calculate_line_item(
            rate=Decimal(str(item["rate"])),
            quantity=Decimal(str(item["quantity"])),
            discount=Decimal(str(item.get("discount", 0))),
            # Tax fixed at 0% — item se aaya tax ignore karo.
            tax_percentage=Decimal("0"),
            tax_type=tax_type,
        )
        computed_items.append(
            {
                **item,
                "tax_percentage": Decimal("0"),
                "taxable_amount": calc.taxable_amount,
                "cgst_amount": calc.cgst_amount,
                "sgst_amount": calc.sgst_amount,
                "igst_amount": calc.igst_amount,
                "total_amount": calc.total_amount,
            }
        )

    totals = gst_service.calculate_invoice_totals(computed_items)
    return {"tax_type": tax_type, "items": computed_items, "totals": totals}


def create_invoice(
    session: Session,
    user_id: int | None,
    customer_id: int,
    items: list[dict],
    invoice_date: date,
    notes: str = "",
    initial_payment: dict | None = None,
) -> dict:
    preview = build_invoice_preview(session, customer_id, items)
    customer = session.get(Customer, customer_id)
    totals = preview["totals"]

    invoice_number = _generate_invoice_number(session, invoice_date)

    invoice = Invoice(
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        customer_id=customer_id,
        billing_address=customer.address or "",
        customer_gstin=customer.gstin,
        subtotal=totals.subtotal,
        discount_total=totals.discount_total,
        cgst_total=totals.cgst_total,
        sgst_total=totals.sgst_total,
        igst_total=totals.igst_total,
        round_off=totals.round_off,
        grand_total=totals.grand_total,
        paid_amount=Decimal("0.00"),
        due_amount=totals.grand_total,
        notes=notes,
        status=STATUS_PENDING,
        created_by=user_id,
    )
    session.add(invoice)
    session.flush()

    for item in preview["items"]:
        session.add(
            InvoiceItem(
                invoice_id=invoice.id,
                course_id=item.get("course_id"),
                item_name=item["item_name"],
                quantity=Decimal(str(item["quantity"])),
                rate=Decimal(str(item["rate"])),
                discount=Decimal(str(item.get("discount", 0))),
                tax_percentage=Decimal(str(item.get("tax_percentage", 0))),
                taxable_amount=item["taxable_amount"],
                cgst_amount=item["cgst_amount"],
                sgst_amount=item["sgst_amount"],
                igst_amount=item["igst_amount"],
                total_amount=item["total_amount"],
            )
        )
    session.flush()

    if initial_payment and Decimal(str(initial_payment.get("amount", 0))) > 0:
        from services import payment_service

        payment_service.record_payment(
            session,
            user_id,
            invoice_id=invoice.id,
            amount=Decimal(str(initial_payment["amount"])),
            payment_mode=initial_payment.get("payment_mode", "Cash"),
            payment_date=initial_payment.get("payment_date", invoice_date),
            reference_number=initial_payment.get("reference_number", ""),
            notes=initial_payment.get("notes", ""),
        )

    return get_invoice_detail(session, invoice.id)


def list_invoices(
    session: Session, query: str = "", status: str | None = None, date_from: date | None = None, date_to: date | None = None
) -> list[dict]:
    rows = InvoiceRepository(session).search(query=query, status=status, date_from=date_from, date_to=date_to)
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "customer_id": inv.customer_id,
            "customer_name": customer_name,
            "grand_total": Decimal(str(inv.grand_total)),
            "paid_amount": Decimal(str(inv.paid_amount)),
            "due_amount": Decimal(str(inv.due_amount)),
            "status": inv.status,
        }
        for inv, customer_name in rows
    ]


def get_invoice_detail(session: Session, invoice_id: int) -> dict:
    invoice = InvoiceRepository(session).get(invoice_id)
    if invoice is None:
        raise InvoiceError("Invoice not found.")

    customer = session.get(Customer, invoice.customer_id)

    item_rows = session.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
    ).scalars().all()
    items = [
        {
            "id": item.id,
            "item_name": item.item_name,
            "quantity": Decimal(str(item.quantity)),
            "rate": Decimal(str(item.rate)),
            "discount": Decimal(str(item.discount)),
            "tax_percentage": Decimal(str(item.tax_percentage)),
            "taxable_amount": Decimal(str(item.taxable_amount)),
            "cgst_amount": Decimal(str(item.cgst_amount)),
            "sgst_amount": Decimal(str(item.sgst_amount)),
            "igst_amount": Decimal(str(item.igst_amount)),
            "total_amount": Decimal(str(item.total_amount)),
        }
        for item in item_rows
    ]

    payments = PaymentRepository(session).list_for_invoice(invoice_id)
    payment_rows = [
        {
            "id": p.id,
            "amount": Decimal(str(p.amount)),
            "payment_mode": p.payment_mode,
            "payment_date": p.payment_date,
            "reference_number": p.reference_number,
        }
        for p in payments
    ]

    return {
        "invoice": {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "customer_id": invoice.customer_id,
            "customer_name": customer.name if customer else "",
            "customer_mobile": customer.mobile if customer else "",
            "billing_address": invoice.billing_address,
            "customer_gstin": invoice.customer_gstin,
            "subtotal": Decimal(str(invoice.subtotal)),
            "discount_total": Decimal(str(invoice.discount_total)),
            "cgst_total": Decimal(str(invoice.cgst_total)),
            "sgst_total": Decimal(str(invoice.sgst_total)),
            "igst_total": Decimal(str(invoice.igst_total)),
            "round_off": Decimal(str(invoice.round_off)),
            "grand_total": Decimal(str(invoice.grand_total)),
            "paid_amount": Decimal(str(invoice.paid_amount)),
            "due_amount": Decimal(str(invoice.due_amount)),
            "notes": invoice.notes,
            "status": invoice.status,
        },
        "items": items,
        "payments": payment_rows,
    }


def cancel_invoice(session: Session, user_id: int | None, invoice_id: int) -> None:
    invoice = InvoiceRepository(session).get(invoice_id)
    if invoice is None:
        raise InvoiceError("Invoice not found.")
    if invoice.status == STATUS_CANCELLED:
        raise InvoiceError("This invoice is already cancelled.")
    if Decimal(str(invoice.paid_amount)) > 0:
        raise InvoiceError("This invoice has recorded payments and cannot be cancelled. Refund the payments first.")

    invoice.status = STATUS_CANCELLED
    session.flush()


def recalculate_status(invoice: Invoice) -> None:
    invoice.status = _determine_status(Decimal(str(invoice.paid_amount)), Decimal(str(invoice.grand_total)))

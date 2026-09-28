"""Reports (Section 18): every figure here is a real aggregate query
against Invoice/Payment/Expense — never a GUI-side computation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.models.expense import Expense, ExpenseCategory
from database.models.invoice import Invoice
from database.models.payment import Payment

CANCELLED = "CANCELLED"


def _d(value) -> Decimal:
    return Decimal(str(value))


@dataclass
class ReportResult:
    summary: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)


def sales_report(
    session: Session, date_from: date, date_to: date, customer_id: int | None = None, status: str | None = None
) -> ReportResult:
    stmt = (
        select(Invoice, Customer.name)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to)
    )
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if status and status != "All":
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())

    rows = []
    total_sales = total_collected = total_due = Decimal("0")
    counted_invoices = 0
    for invoice, customer_name in session.execute(stmt).all():
        rows.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "customer_name": customer_name,
                "grand_total": _d(invoice.grand_total),
                "paid_amount": _d(invoice.paid_amount),
                "due_amount": _d(invoice.due_amount),
                "status": invoice.status,
            }
        )
        if invoice.status != CANCELLED:
            total_sales += _d(invoice.grand_total)
            total_collected += _d(invoice.paid_amount)
            total_due += _d(invoice.due_amount)
            counted_invoices += 1

    average_invoice_value = (total_sales / counted_invoices) if counted_invoices else Decimal("0")
    return ReportResult(
        summary={
            "total_invoices": counted_invoices,
            "total_sales": total_sales,
            "total_collected": total_collected,
            "total_due": total_due,
            "average_invoice_value": average_invoice_value,
        },
        rows=rows,
    )


def payment_report(
    session: Session, date_from: date, date_to: date, payment_mode: str | None = None
) -> ReportResult:
    stmt = (
        select(Payment, Invoice.invoice_number, Customer.name)
        .join(Invoice, Invoice.id == Payment.invoice_id)
        .join(Customer, Customer.id == Payment.customer_id)
        .where(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
    )
    if payment_mode and payment_mode != "All":
        stmt = stmt.where(Payment.payment_mode == payment_mode)
    stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())

    rows = []
    total_collected = Decimal("0")
    by_mode: dict[str, Decimal] = {}
    for payment, invoice_number, customer_name in session.execute(stmt).all():
        amount = _d(payment.amount)
        rows.append(
            {
                "id": payment.id,
                "payment_date": payment.payment_date,
                "invoice_number": invoice_number,
                "customer_name": customer_name,
                "amount": amount,
                "payment_mode": payment.payment_mode,
                "reference_number": payment.reference_number,
            }
        )
        total_collected += amount
        by_mode[payment.payment_mode] = by_mode.get(payment.payment_mode, Decimal("0")) + amount

    return ReportResult(
        summary={
            "total_collected": total_collected,
            "total_transactions": len(rows),
            "by_mode": by_mode,
        },
        rows=rows,
    )


def pending_payments_report(session: Session, customer_id: int | None = None) -> ReportResult:
    stmt = (
        select(Invoice, Customer.name, Customer.mobile)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.due_amount > 0, Invoice.status != CANCELLED)
    )
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    stmt = stmt.order_by(Invoice.due_amount.desc())

    rows = []
    total_outstanding = Decimal("0")
    customer_ids = set()
    for invoice, customer_name, customer_mobile in session.execute(stmt).all():
        due = _d(invoice.due_amount)
        rows.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "customer_name": customer_name,
                "customer_mobile": customer_mobile,
                "grand_total": _d(invoice.grand_total),
                "paid_amount": _d(invoice.paid_amount),
                "due_amount": due,
                "status": invoice.status,
            }
        )
        total_outstanding += due
        customer_ids.add(invoice.customer_id)

    return ReportResult(
        summary={
            "total_outstanding": total_outstanding,
            "total_pending_invoices": len(rows),
            "customers_with_dues": len(customer_ids),
        },
        rows=rows,
    )


def gst_report(session: Session, date_from: date, date_to: date) -> ReportResult:
    stmt = (
        select(Invoice, Customer.name)
        .join(Customer, Customer.id == Invoice.customer_id)
        .where(Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to, Invoice.status != CANCELLED)
        .order_by(Invoice.invoice_date.desc())
    )

    rows = []
    taxable_total = cgst_total = sgst_total = igst_total = grand_total_sum = Decimal("0")
    for invoice, customer_name in session.execute(stmt).all():
        taxable = _d(invoice.subtotal) - _d(invoice.discount_total)
        rows.append(
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date,
                "customer_name": customer_name,
                "customer_gstin": invoice.customer_gstin or "",
                "taxable_amount": taxable,
                "cgst_total": _d(invoice.cgst_total),
                "sgst_total": _d(invoice.sgst_total),
                "igst_total": _d(invoice.igst_total),
                "grand_total": _d(invoice.grand_total),
            }
        )
        taxable_total += taxable
        cgst_total += _d(invoice.cgst_total)
        sgst_total += _d(invoice.sgst_total)
        igst_total += _d(invoice.igst_total)
        grand_total_sum += _d(invoice.grand_total)

    return ReportResult(
        summary={
            "taxable_total": taxable_total,
            "cgst_total": cgst_total,
            "sgst_total": sgst_total,
            "igst_total": igst_total,
            "total_tax": cgst_total + sgst_total + igst_total,
            "grand_total": grand_total_sum,
        },
        rows=rows,
    )


def expense_report(
    session: Session, date_from: date, date_to: date, category_id: int | None = None
) -> ReportResult:
    stmt = (
        select(Expense, ExpenseCategory.name)
        .join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
        .where(Expense.expense_date >= date_from, Expense.expense_date <= date_to)
    )
    if category_id:
        stmt = stmt.where(Expense.category_id == category_id)
    stmt = stmt.order_by(Expense.expense_date.desc())

    rows = []
    total_expenses = Decimal("0")
    by_category: dict[str, Decimal] = {}
    for expense, category_name in session.execute(stmt).all():
        amount = _d(expense.amount)
        rows.append(
            {
                "id": expense.id,
                "expense_date": expense.expense_date,
                "category_name": category_name,
                "description": expense.description,
                "vendor": expense.vendor,
                "amount": amount,
                "payment_mode": expense.payment_mode,
            }
        )
        total_expenses += amount
        by_category[category_name] = by_category.get(category_name, Decimal("0")) + amount

    return ReportResult(
        summary={"total_expenses": total_expenses, "total_count": len(rows), "by_category": by_category},
        rows=rows,
    )


def profit_summary(session: Session, date_from: date, date_to: date) -> ReportResult:
    revenue_collected = _d(
        session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.payment_date >= date_from, Payment.payment_date <= date_to
            )
        ).scalar_one()
    )
    total_expenses = _d(
        session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.expense_date >= date_from, Expense.expense_date <= date_to
            )
        ).scalar_one()
    )
    invoiced_sales = _d(
        session.execute(
            select(func.coalesce(func.sum(Invoice.grand_total), 0)).where(
                Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to, Invoice.status != CANCELLED
            )
        ).scalar_one()
    )

    return ReportResult(
        summary={
            "invoiced_sales": invoiced_sales,
            "revenue_collected": revenue_collected,
            "total_expenses": total_expenses,
            "net_profit": revenue_collected - total_expenses,
        },
        rows=[],
    )

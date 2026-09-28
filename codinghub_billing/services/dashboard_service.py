"""Dashboard KPI + chart aggregation (Section 10). Every number here comes
from a real SQLAlchemy query against Invoice/Payment/Customer/Expense — the
GUI never computes totals itself."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.models.expense import Expense
from database.models.invoice import Invoice
from database.models.payment import Payment

RANGE_TODAY = "today"
RANGE_WEEK = "week"
RANGE_MONTH = "month"
RANGE_YEAR = "year"
RANGE_CUSTOM = "custom"


def resolve_range(range_key: str, custom_from: date | None = None, custom_to: date | None = None) -> tuple[date, date]:
    today = date.today()
    if range_key == RANGE_TODAY:
        return today, today
    if range_key == RANGE_WEEK:
        return today - timedelta(days=today.weekday()), today
    if range_key == RANGE_MONTH:
        return today.replace(day=1), today
    if range_key == RANGE_YEAR:
        return today.replace(month=1, day=1), today
    if range_key == RANGE_CUSTOM:
        if custom_from is None or custom_to is None:
            raise ValueError("Custom range requires both a from-date and a to-date.")
        return custom_from, custom_to
    raise ValueError(f"Unknown date range: {range_key}")


@dataclass
class DashboardKpis:
    today_revenue: Decimal = Decimal("0")
    month_revenue: Decimal = Decimal("0")
    pending_payments: Decimal = Decimal("0")
    total_customers: int = 0


@dataclass
class DashboardOverview:
    kpis: DashboardKpis = field(default_factory=DashboardKpis)
    recent_invoices: list[dict] = field(default_factory=list)
    recent_payments: list[dict] = field(default_factory=list)
    recent_expenses: list[dict] = field(default_factory=list)
    top_courses: list[tuple[str, Decimal]] = field(default_factory=list)
    monthly_revenue: list[tuple[str, Decimal]] = field(default_factory=list)
    payment_mode_breakdown: list[tuple[str, Decimal]] = field(default_factory=list)
    outstanding_dues: Decimal = Decimal("0")


def _sum(session: Session, column, *filters) -> Decimal:
    stmt = select(func.coalesce(func.sum(column), 0)).where(*filters)
    result = session.execute(stmt).scalar_one()
    return Decimal(str(result))


def get_kpis(session: Session) -> DashboardKpis:
    today = date.today()
    month_start = today.replace(day=1)

    today_revenue = _sum(session, Payment.amount, Payment.payment_date == today)
    month_revenue = _sum(session, Payment.amount, Payment.payment_date >= month_start, Payment.payment_date <= today)
    pending_payments = _sum(session, Invoice.due_amount, Invoice.due_amount > 0)
    total_customers = session.execute(select(func.count(Customer.id))).scalar_one()

    return DashboardKpis(
        today_revenue=today_revenue,
        month_revenue=month_revenue,
        pending_payments=pending_payments,
        total_customers=total_customers,
    )


def get_recent_invoices(session: Session, limit: int = 5) -> list[dict]:
    stmt = select(Invoice).order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "invoice_number": r.invoice_number,
            "invoice_date": r.invoice_date,
            "customer_id": r.customer_id,
            "grand_total": Decimal(str(r.grand_total)),
            "due_amount": Decimal(str(r.due_amount)),
            "status": r.status,
        }
        for r in rows
    ]


def get_recent_payments(session: Session, limit: int = 5) -> list[dict]:
    stmt = select(Payment).order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "invoice_id": r.invoice_id,
            "customer_id": r.customer_id,
            "amount": Decimal(str(r.amount)),
            "payment_mode": r.payment_mode,
            "payment_date": r.payment_date,
        }
        for r in rows
    ]


def get_recent_expenses(session: Session, limit: int = 5) -> list[dict]:
    stmt = select(Expense).order_by(Expense.expense_date.desc(), Expense.id.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "description": r.description,
            "amount": Decimal(str(r.amount)),
            "expense_date": r.expense_date,
            "payment_mode": r.payment_mode,
            "vendor": r.vendor,
        }
        for r in rows
    ]


def get_top_courses(session: Session, date_from: date, date_to: date, limit: int = 5) -> list[tuple[str, Decimal]]:
    from database.models.invoice import InvoiceItem

    stmt = (
        select(InvoiceItem.item_name, func.coalesce(func.sum(InvoiceItem.total_amount), 0))
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(Invoice.invoice_date >= date_from, Invoice.invoice_date <= date_to)
        .group_by(InvoiceItem.item_name)
        .order_by(func.sum(InvoiceItem.total_amount).desc())
        .limit(limit)
    )
    return [(name, Decimal(str(total))) for name, total in session.execute(stmt).all()]


def get_monthly_revenue(session: Session, date_from: date, date_to: date) -> list[tuple[str, Decimal]]:
    month_expr = func.strftime("%Y-%m", Payment.payment_date)
    stmt = (
        select(month_expr, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
        .group_by(month_expr)
        .order_by(month_expr)
    )
    return [(month, Decimal(str(total))) for month, total in session.execute(stmt).all()]


def get_payment_mode_breakdown(session: Session, date_from: date, date_to: date) -> list[tuple[str, Decimal]]:
    stmt = (
        select(Payment.payment_mode, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.payment_date >= date_from, Payment.payment_date <= date_to)
        .group_by(Payment.payment_mode)
        .order_by(func.sum(Payment.amount).desc())
    )
    return [(mode, Decimal(str(total))) for mode, total in session.execute(stmt).all()]


def get_outstanding_dues(session: Session) -> Decimal:
    return _sum(session, Invoice.due_amount, Invoice.due_amount > 0)


def get_overview(session: Session, date_from: date, date_to: date) -> DashboardOverview:
    return DashboardOverview(
        kpis=get_kpis(session),
        recent_invoices=get_recent_invoices(session),
        recent_payments=get_recent_payments(session),
        recent_expenses=get_recent_expenses(session),
        top_courses=get_top_courses(session, date_from, date_to),
        monthly_revenue=get_monthly_revenue(session, date_from, date_to),
        payment_mode_breakdown=get_payment_mode_breakdown(session, date_from, date_to),
        outstanding_dues=get_outstanding_dues(session),
    )

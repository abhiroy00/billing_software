from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.models.invoice import Invoice
from database.models.payment import Payment
from database.repositories.base_repository import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: Session):
        super().__init__(session, Payment)

    def list_for_invoice(self, invoice_id: int) -> list[Payment]:
        stmt = select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.payment_date.desc())
        return list(self.session.execute(stmt).scalars().all())

    def total_paid_for_invoice(self, invoice_id: int) -> Decimal:
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.invoice_id == invoice_id)
        return Decimal(str(self.session.execute(stmt).scalar_one()))

    def delete_for_invoice(self, invoice_id: int) -> None:
        self.session.execute(delete(Payment).where(Payment.invoice_id == invoice_id))

    def search(
        self,
        query: str = "",
        payment_mode: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[tuple[Payment, str, str]]:
        stmt = (
            select(Payment, Invoice.invoice_number, Customer.name)
            .join(Invoice, Invoice.id == Payment.invoice_id)
            .join(Customer, Customer.id == Payment.customer_id)
        )
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Invoice.invoice_number.ilike(like), Customer.name.ilike(like)))
        if payment_mode and payment_mode != "All":
            stmt = stmt.where(Payment.payment_mode == payment_mode)
        if date_from:
            stmt = stmt.where(Payment.payment_date >= date_from)
        if date_to:
            stmt = stmt.where(Payment.payment_date <= date_to)
        stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())
        return list(self.session.execute(stmt).all())

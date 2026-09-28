from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.models.invoice import Invoice
from database.repositories.base_repository import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    def __init__(self, session: Session):
        super().__init__(session, Invoice)

    def get_by_number(self, invoice_number: str) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.invoice_number == invoice_number)
        return self.session.execute(stmt).scalar_one_or_none()

    def search(
        self,
        query: str = "",
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[tuple[Invoice, str]]:
        stmt = select(Invoice, Customer.name).join(Customer, Customer.id == Invoice.customer_id)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Invoice.invoice_number.ilike(like), Customer.name.ilike(like)))
        if status and status != "All":
            stmt = stmt.where(Invoice.status == status)
        if date_from:
            stmt = stmt.where(Invoice.invoice_date >= date_from)
        if date_to:
            stmt = stmt.where(Invoice.invoice_date <= date_to)
        stmt = stmt.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
        return list(self.session.execute(stmt).all())

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from database.models.customer import Customer
from database.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: Session):
        super().__init__(session, Customer)

    def get_by_code(self, customer_code: str) -> Customer | None:
        stmt = select(Customer).where(Customer.customer_code == customer_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def count(self) -> int:
        return self.session.execute(select(func.count(Customer.id))).scalar_one()

    def search(self, query: str = "", status: str | None = None) -> list[Customer]:
        stmt = select(Customer)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(like),
                    Customer.mobile.ilike(like),
                    Customer.email.ilike(like),
                    Customer.student_id.ilike(like),
                    Customer.customer_code.ilike(like),
                )
            )
        if status and status != "All":
            stmt = stmt.where(Customer.status == status)
        stmt = stmt.order_by(Customer.name)
        return list(self.session.execute(stmt).scalars().all())

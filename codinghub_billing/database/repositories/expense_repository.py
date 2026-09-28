from __future__ import annotations

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from database.models.expense import Expense, ExpenseCategory
from database.repositories.base_repository import BaseRepository


class ExpenseCategoryRepository(BaseRepository[ExpenseCategory]):
    def __init__(self, session: Session):
        super().__init__(session, ExpenseCategory)

    def get_by_name(self, name: str) -> ExpenseCategory | None:
        stmt = select(ExpenseCategory).where(ExpenseCategory.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[ExpenseCategory]:
        stmt = select(ExpenseCategory).order_by(ExpenseCategory.name)
        return list(self.session.execute(stmt).scalars().all())


class ExpenseRepository(BaseRepository[Expense]):
    def __init__(self, session: Session):
        super().__init__(session, Expense)

    def search(
        self,
        query: str = "",
        category_id: int | None = None,
        payment_mode: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[tuple[Expense, str]]:
        stmt = select(Expense, ExpenseCategory.name).join(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
        if query:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(Expense.description.ilike(like), Expense.vendor.ilike(like)))
        if category_id:
            stmt = stmt.where(Expense.category_id == category_id)
        if payment_mode and payment_mode != "All":
            stmt = stmt.where(Expense.payment_mode == payment_mode)
        if date_from:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to:
            stmt = stmt.where(Expense.expense_date <= date_to)
        stmt = stmt.order_by(Expense.expense_date.desc(), Expense.id.desc())
        return list(self.session.execute(stmt).all())

"""Expense / ExpenseCategory models (Section 16)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class ExpenseCategory(Base, TimestampMixin):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)

    expenses: Mapped[list["Expense"]] = relationship(back_populates="category")


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("expense_categories.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="Cash")
    vendor: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    category: Mapped["ExpenseCategory"] = relationship(back_populates="expenses")

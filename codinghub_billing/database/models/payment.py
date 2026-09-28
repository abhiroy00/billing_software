"""Payment model (Section 15)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="Cash")
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

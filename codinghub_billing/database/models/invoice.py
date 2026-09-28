"""Invoice / InvoiceItem models (Section 13/14)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    billing_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cgst_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sgst_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igst_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    round_off: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    due_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    payment_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="Cash")
    notes: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), nullable=True)

    item_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=1)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")

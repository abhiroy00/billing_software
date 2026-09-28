"""Course / Product model (Section 12)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gst_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    duration: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Active")
